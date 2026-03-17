"""Add tracing and cost detail fields."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_000005"
down_revision = "20260317_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_logs",
        sa.Column("trace_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "evaluations",
        sa.Column("input_cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "evaluations",
        sa.Column("output_cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("evaluations", sa.Column("pricing_source", sa.Text(), nullable=True))
    op.add_column(
        "evaluations",
        sa.Column("cost_is_estimated", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.alter_column("query_logs", "trace_json", server_default=None)
    op.alter_column("evaluations", "input_cost_usd", server_default=None)
    op.alter_column("evaluations", "output_cost_usd", server_default=None)
    op.alter_column("evaluations", "cost_is_estimated", server_default=None)


def downgrade() -> None:
    op.drop_column("evaluations", "cost_is_estimated")
    op.drop_column("evaluations", "pricing_source")
    op.drop_column("evaluations", "output_cost_usd")
    op.drop_column("evaluations", "input_cost_usd")
    op.drop_column("query_logs", "trace_json")
