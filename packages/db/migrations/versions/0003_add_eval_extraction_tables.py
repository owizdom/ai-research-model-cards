"""Add eval extraction tables: model_families, model_generations, benchmark_definitions, eval_results, extraction_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_families",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("lab_id", sa.Integer, sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("slug", sa.String, unique=True, nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "model_generations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("family_id", sa.Integer, sa.ForeignKey("model_families.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id", ondelete="SET NULL"), index=True),
        sa.Column("slug", sa.String, unique=True, nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("version_label", sa.String),
        sa.Column("release_date", sa.Date),
        sa.Column("parameter_count", sa.String),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "benchmark_definitions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String, unique=True, nullable=False, index=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("category", sa.String, nullable=False, index=True),
        sa.Column("description", sa.Text),
        sa.Column("metric_name", sa.String),
        sa.Column("metric_unit", sa.String),
        sa.Column("higher_is_better", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("source_url", sa.String),
        sa.Column("aliases", sa.JSON),
    )

    op.create_table(
        "eval_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_version_id", sa.Integer, sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("generation_id", sa.Integer, sa.ForeignKey("model_generations.id", ondelete="SET NULL")),
        sa.Column("benchmark_id", sa.Integer, sa.ForeignKey("benchmark_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("variant", sa.String, nullable=False, server_default="default"),
        sa.Column("score_details", sa.JSON),
        sa.Column("extraction_confidence", sa.Float),
        sa.Column("is_self_reported", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("source_type", sa.String, nullable=False, server_default="model_card"),
        sa.Column("extracted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("document_version_id", "generation_id", "benchmark_id", "variant", name="uq_eval_result"),
        sa.Index("ix_eval_results_benchmark", "benchmark_id"),
        sa.Index("ix_eval_results_generation", "generation_id"),
        sa.Index("ix_eval_results_version", "document_version_id"),
    )

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_version_id", sa.Integer, sa.ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("model_used", sa.String, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String, nullable=False, server_default="running"),
        sa.Column("evals_extracted", sa.Integer),
        sa.Column("raw_output", sa.Text),
        sa.Column("error", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("extraction_runs")
    op.drop_table("eval_results")
    op.drop_table("benchmark_definitions")
    op.drop_table("model_generations")
    op.drop_table("model_families")
