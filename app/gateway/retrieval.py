"""Database-backed retrieval orchestration for the gateway MVP."""

from app.config.settings import get_settings
from database.repositories import EmbeddingConfigurationMismatchError, RetrievalRepository
from database.session import SessionLocal
from providers.embeddings import get_embedding_provider


class RetrievalService:
    """pgvector-backed retrieval layer."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_provider = get_embedding_provider()

    def retrieve(self, question: str, task: str, top_k: int | None = None) -> list[dict]:
        """Return the top-k similar chunks for the configured task."""
        k = top_k or self.settings.retrieval_top_k
        active_embedding_config = self.embedding_provider.embedding_config()
        with SessionLocal() as session:
            repository = RetrievalRepository(session)
            repository.validate_embedding_config(
                task=task,
                active_embedding_config=active_embedding_config,
            )
            query_embedding = self.embedding_provider.embed_text(question)
            return repository.search_chunks(
                task=task,
                query_embedding=query_embedding,
                limit=k,
            )
