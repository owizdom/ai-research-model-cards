"""Add model_name to eval_results and include it in the unique constraint

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-17

Rationale: papers like Meta's Llama 3.1 report benchmarks for 8B/70B/405B
all at once. With the prior unique constraint on
(document_version_id, generation_id, benchmark_id, variant), only the
first size survived — the other two were silently rejected. Adding
model_name to the key preserves per-size rows.
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eval_results",
        sa.Column("model_name", sa.String, nullable=True),
    )

    # Backfill model_name from the existing JSON blob.
    op.execute(
        "UPDATE eval_results "
        "SET model_name = score_details->>'model_name' "
        "WHERE model_name IS NULL AND score_details IS NOT NULL"
    )

    op.drop_constraint("uq_eval_result", "eval_results", type_="unique")
    op.create_unique_constraint(
        "uq_eval_result",
        "eval_results",
        ["document_version_id", "generation_id", "benchmark_id", "variant", "model_name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_eval_result", "eval_results", type_="unique")
    op.create_unique_constraint(
        "uq_eval_result",
        "eval_results",
        ["document_version_id", "generation_id", "benchmark_id", "variant"],
    )
    op.drop_column("eval_results", "model_name")
