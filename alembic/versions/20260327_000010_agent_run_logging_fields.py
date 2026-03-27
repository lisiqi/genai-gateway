"""Add agent runtime logging fields to query logs."""

from alembic import op
import sqlalchemy as sa


revision = "20260327_000010"
down_revision = "20260326_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_logs",
        sa.Column("request_kind", sa.String(length=30), nullable=False, server_default="query"),
    )
    op.add_column("query_logs", sa.Column("agent_run_id", sa.String(length=100), nullable=True))
    op.add_column("query_logs", sa.Column("agent_task_type", sa.String(length=50), nullable=True))
    op.add_column("query_logs", sa.Column("instruction", sa.Text(), nullable=True))
    op.add_column("query_logs", sa.Column("agent_status", sa.String(length=30), nullable=True))
    op.add_column("query_logs", sa.Column("agent_stop_reason", sa.Text(), nullable=True))
    op.add_column("query_logs", sa.Column("agent_step_count", sa.Integer(), nullable=True))
    op.add_column("query_logs", sa.Column("agent_report_json", sa.JSON(), nullable=True))
    op.create_index("ix_query_logs_request_kind", "query_logs", ["request_kind"], unique=False)
    op.create_index("ix_query_logs_agent_run_id", "query_logs", ["agent_run_id"], unique=False)
    op.alter_column("query_logs", "request_kind", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_query_logs_agent_run_id", table_name="query_logs")
    op.drop_index("ix_query_logs_request_kind", table_name="query_logs")
    op.drop_column("query_logs", "agent_report_json")
    op.drop_column("query_logs", "agent_step_count")
    op.drop_column("query_logs", "agent_stop_reason")
    op.drop_column("query_logs", "agent_status")
    op.drop_column("query_logs", "instruction")
    op.drop_column("query_logs", "agent_task_type")
    op.drop_column("query_logs", "agent_run_id")
    op.drop_column("query_logs", "request_kind")
