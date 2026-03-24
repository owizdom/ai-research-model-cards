"""Add external eval sources table and FK on eval_results

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_eval_sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String, unique=True, nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("url", sa.String, nullable=False),
        sa.Column("fetch_method", sa.String, nullable=False),
        sa.Column("fetch_config", sa.JSON),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column(
        "eval_results",
        sa.Column(
            "external_source_id",
            sa.Integer,
            sa.ForeignKey("external_eval_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("eval_results", "external_source_id")
    op.drop_table("external_eval_sources")
