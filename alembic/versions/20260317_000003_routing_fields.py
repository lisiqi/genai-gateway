"""Add routing fields to query logs."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_000003"
down_revision = "20260313_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_logs",
        sa.Column("quality_mode", sa.String(length=50), nullable=False, server_default="default"),
    )
    op.add_column("query_logs", sa.Column("selected_provider", sa.String(length=50), nullable=True))
    op.add_column(
        "query_logs",
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("query_logs", sa.Column("fallback_provider", sa.String(length=50), nullable=True))
    op.add_column("query_logs", sa.Column("fallback_model", sa.String(length=100), nullable=True))
    op.add_column("query_logs", sa.Column("routing_reason", sa.Text(), nullable=True))

    op.alter_column("query_logs", "quality_mode", server_default=None)
    op.alter_column("query_logs", "fallback_used", server_default=None)


def downgrade() -> None:
    op.drop_column("query_logs", "routing_reason")
    op.drop_column("query_logs", "fallback_model")
    op.drop_column("query_logs", "fallback_provider")
    op.drop_column("query_logs", "fallback_used")
    op.drop_column("query_logs", "selected_provider")
    op.drop_column("query_logs", "quality_mode")
