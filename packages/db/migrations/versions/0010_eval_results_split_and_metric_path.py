"""eval_results.split + eval_results.metric_path — Phase 5 hierarchy

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-29

Adds two nullable text columns on eval_results to carry the EvaluationCards
paper's Section 3.2 hierarchy below the benchmark level:

  `split`        — sub-task / domain within a benchmark
                   (e.g. "magnification" within long_form_biological_risk,
                    "ambiguous" / "disambiguated" within BBQ,
                    "verified" within swe_bench)

  `metric_path`  — scoring rule applied to a benchmark
                   (e.g. "accuracy" vs "cot_correct" on MMLU-Pro,
                    "pass_at_1" vs "pass_at_10" on HumanEval)

Both nullable so existing rows roll forward without backfill; the variant
parser populates them where the legacy variant string has parseable info.
Indexed for the divergence GROUP BY full-path query.
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_results", sa.Column("split", sa.String, nullable=True))
    op.add_column("eval_results", sa.Column("metric_path", sa.String, nullable=True))
    op.create_index("ix_eval_results_split", "eval_results", ["split"])
    op.create_index("ix_eval_results_metric_path", "eval_results", ["metric_path"])


def downgrade() -> None:
    op.drop_index("ix_eval_results_metric_path", table_name="eval_results")
    op.drop_index("ix_eval_results_split", table_name="eval_results")
    op.drop_column("eval_results", "metric_path")
    op.drop_column("eval_results", "split")
