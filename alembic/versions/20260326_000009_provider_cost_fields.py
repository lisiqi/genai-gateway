"""Add provider-reported cost fields for evaluations."""

from alembic import op
import sqlalchemy as sa


revision = "20260326_000009"
down_revision = "20260326_000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluations", sa.Column("provider_reported_cost_usd", sa.Float(), nullable=True))
    op.add_column("evaluations", sa.Column("provider_generation_id", sa.String(length=200), nullable=True))
    op.add_column("evaluations", sa.Column("provider_usage_source", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluations", "provider_usage_source")
    op.drop_column("evaluations", "provider_generation_id")
    op.drop_column("evaluations", "provider_reported_cost_usd")
