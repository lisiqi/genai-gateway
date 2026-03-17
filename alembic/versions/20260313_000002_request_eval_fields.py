"""Add request-time evaluation fields."""

from alembic import op
import sqlalchemy as sa


revision = "20260313_000002"
down_revision = "20260312_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("query_logs", sa.Column("model_name", sa.String(length=100), nullable=True))
    op.add_column("query_logs", sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))

    op.add_column("evaluations", sa.Column("latency_ms", sa.Float(), nullable=False, server_default=sa.text("0")))
    op.add_column("evaluations", sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("evaluations", sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("evaluations", sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.alter_column("query_logs", "retrieved_chunk_ids", server_default=None)
    op.alter_column("evaluations", "latency_ms", server_default=None)
    op.alter_column("evaluations", "prompt_tokens", server_default=None)
    op.alter_column("evaluations", "completion_tokens", server_default=None)
    op.alter_column("evaluations", "total_tokens", server_default=None)


def downgrade() -> None:
    op.drop_column("evaluations", "total_tokens")
    op.drop_column("evaluations", "completion_tokens")
    op.drop_column("evaluations", "prompt_tokens")
    op.drop_column("evaluations", "latency_ms")

    op.drop_column("query_logs", "retrieved_chunk_ids")
    op.drop_column("query_logs", "model_name")
