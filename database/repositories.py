"""Repository helpers for document ingestion and retrieval."""

from __future__ import annotations

from sqlalchemy import Select, cast, func, literal, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from database.models import Document, DocumentChunk


class EmbeddingConfigurationMismatchError(RuntimeError):
    """Raised when retrieval embeddings do not match the ingested corpus."""


class DocumentRepository:
    """Persistence operations for documents and document chunks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_source_path(self, source_path: str) -> Document | None:
        """Fetch a document by its unique source path."""
        stmt: Select[tuple[Document]] = select(Document).where(Document.source_path == source_path)
        return self.session.execute(stmt).scalar_one_or_none()

    def replace_document(
        self,
        *,
        task: str,
        title: str,
        source_path: str,
        document_type: str | None,
        metadata_json: dict,
        chunks: list[dict],
    ) -> Document:
        """Replace one document and its chunks atomically."""
        existing = self.get_by_source_path(source_path)
        if existing is not None:
            self.session.delete(existing)
            self.session.flush()

        document = Document(
            task=task,
            title=title,
            source_path=source_path,
            document_type=document_type,
            metadata_json=metadata_json,
        )
        self.session.add(document)
        self.session.flush()

        for chunk in chunks:
            self.session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["content"],
                    token_count=chunk.get("token_count"),
                    metadata_json=chunk.get("metadata_json", {}),
                    embedding=chunk.get("embedding"),
                )
            )

        self.session.commit()
        self.session.refresh(document)
        return document


class RetrievalRepository:
    """Database-backed dense and lexical search over stored chunks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_task_embedding_configs(self, *, task: str) -> list[dict]:
        """Return distinct embedding configs stored for documents in a task corpus."""
        stmt = select(Document.metadata_json).where(Document.task == task)
        rows = self.session.execute(stmt).scalars().all()

        configs: list[dict] = []
        seen: set[tuple] = set()
        for metadata_json in rows:
            if not metadata_json:
                continue
            embedding_config = metadata_json.get("embedding_config")
            if not embedding_config:
                continue
            key = (
                embedding_config.get("provider"),
                embedding_config.get("model"),
                embedding_config.get("dimensions"),
            )
            if key in seen:
                continue
            seen.add(key)
            configs.append(embedding_config)
        return configs

    def validate_embedding_config(
        self,
        *,
        task: str,
        active_embedding_config: dict[str, str | int],
    ) -> None:
        """Ensure the active embedding config matches the stored task corpus."""
        stored_configs = self.get_task_embedding_configs(task=task)
        if not stored_configs:
            return

        if len(stored_configs) > 1:
            raise EmbeddingConfigurationMismatchError(
                f"Multiple embedding configurations detected for task '{task}': {stored_configs}. "
                "Re-ingest the corpus so a single embedding configuration is used."
            )

        stored_config = stored_configs[0]
        if stored_config != active_embedding_config:
            raise EmbeddingConfigurationMismatchError(
                f"Embedding configuration mismatch for task '{task}'. "
                f"Stored corpus uses {stored_config}, active provider uses {active_embedding_config}. "
                "Re-ingest documents before querying."
            )

    def search_dense_chunks(
        self,
        *,
        task: str,
        query_embedding: list[float],
        limit: int,
    ) -> list[dict]:
        """Search chunks by cosine distance using pgvector."""
        score_expr = (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score")
        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.metadata_json,
                Document.source_path,
                Document.title,
                score_expr,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.task == task)
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )

        rows = self.session.execute(stmt).all()
        return self._rows_to_chunks(rows, score_key="dense_score", source_label="dense")

    def search_lexical_chunks(
        self,
        *,
        task: str,
        query_text: str | None,
        article_number: str | None = None,
        clause_number: str | None = None,
        limit: int,
    ) -> list[dict]:
        """Search chunks with Postgres full-text search."""
        metadata_jsonb = cast(DocumentChunk.metadata_json, JSONB)
        score_expr = literal(0.0).label("score")
        stmt = (
            select(
                DocumentChunk.id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.metadata_json,
                Document.source_path,
                Document.title,
                score_expr,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.task == task)
        )

        if article_number:
            stmt = stmt.where(metadata_jsonb.contains({"article_number": str(article_number)}))
        if clause_number:
            stmt = stmt.where(metadata_jsonb.contains({"clause_number": [int(clause_number)]}))

        if query_text:
            tsvector = func.to_tsvector("english", DocumentChunk.content)
            tsquery = func.to_tsquery("english", query_text)
            score_expr = func.ts_rank_cd(tsvector, tsquery).label("score")
            stmt = stmt.with_only_columns(
                DocumentChunk.id,
                DocumentChunk.chunk_index,
                DocumentChunk.content,
                DocumentChunk.metadata_json,
                Document.source_path,
                Document.title,
                score_expr,
            ).where(tsvector.op("@@")(tsquery))
            stmt = stmt.order_by(score_expr.desc(), DocumentChunk.id.asc())
        else:
            stmt = stmt.order_by(DocumentChunk.chunk_index.asc(), DocumentChunk.id.asc())

        stmt = stmt.limit(limit)

        rows = self.session.execute(stmt).all()
        return self._rows_to_chunks(rows, score_key="lexical_score", source_label="lexical")

    @staticmethod
    def _rows_to_chunks(rows: list, *, score_key: str, source_label: str) -> list[dict]:
        """Normalize SQL rows into the shared chunk response shape."""
        chunks: list[dict] = []
        for row in rows:
            chunk = {
                "chunk_id": f"{row.source_path}::chunk::{row.chunk_index}",
                "source": row.source_path,
                "content": row.content,
                "score": float(row.score) if row.score is not None else None,
                score_key: float(row.score) if row.score is not None else None,
                "title": row.title,
                "chunk_index": row.chunk_index,
                "metadata": row.metadata_json or {},
                "retrieval_sources": [source_label],
            }
            chunks.append(chunk)
        return chunks
