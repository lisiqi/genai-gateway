"""Add a ParadeDB pg_search BM25 index for lexical retrieval (ADR 014).

Requires the ParadeDB image (or another Postgres with the `pg_search`
extension available). The BM25 index is only used when
`RETRIEVAL_LEXICAL_BACKEND=bm25`; the Postgres FTS GIN index remains the
default lexical path.
"""

from alembic import op


revision = "20260701_000011"
down_revision = "20260327_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
    # key_field must be the chunk primary key and the first indexed column.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_bm25
        ON document_chunks
        USING bm25 (id, content)
        WITH (key_field = 'id')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_bm25")
