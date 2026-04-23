"""document_summaries — Claude-written chaptered summary per version

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-23

Stores a 1500-2000 word prose summary of each document version, organized
into 6-8 chapters. Generated once per (version, content_hash) tuple by a
background script using Claude Sonnet 4.6. Cached in the DB so the API
serves it synchronously without invoking Claude on every page load.
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_version_id",
            sa.Integer,
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_hash", sa.String(12), nullable=False),
        sa.Column("model_used", sa.String, nullable=False),
        sa.Column("chapters", sa.JSON, nullable=False),
        sa.Column("total_words", sa.Integer, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("error", sa.Text),
    )
    op.create_index(
        "ix_document_summaries_version",
        "document_summaries",
        ["document_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_summaries_version", table_name="document_summaries")
    op.drop_table("document_summaries")
