"""Add reranker metadata to query logs."""

from alembic import op
import sqlalchemy as sa


revision = "20260318_000006"
down_revision = "20260317_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("query_logs", sa.Column("reranker_type", sa.String(length=50), nullable=True))
    op.add_column("query_logs", sa.Column("reranker_model", sa.String(length=150), nullable=True))
    op.add_column("query_logs", sa.Column("reranker_top_k", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_logs", "reranker_top_k")
    op.drop_column("query_logs", "reranker_model")
    op.drop_column("query_logs", "reranker_type")
