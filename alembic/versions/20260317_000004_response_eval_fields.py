"""Add richer response evaluation fields."""

from alembic import op
import sqlalchemy as sa


revision = "20260317_000004"
down_revision = "20260317_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluations",
        sa.Column("answer_relevance_score", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "evaluations",
        sa.Column("citation_score", sa.Float(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "evaluations",
        sa.Column("completeness_score", sa.Float(), nullable=False, server_default=sa.text("0")),
    )

    op.alter_column("evaluations", "answer_relevance_score", server_default=None)
    op.alter_column("evaluations", "citation_score", server_default=None)
    op.alter_column("evaluations", "completeness_score", server_default=None)


def downgrade() -> None:
    op.drop_column("evaluations", "completeness_score")
    op.drop_column("evaluations", "citation_score")
    op.drop_column("evaluations", "answer_relevance_score")
