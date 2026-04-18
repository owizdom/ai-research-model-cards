"""Sprint 2 eval_results: state + structured variant columns

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-18

Adds five columns that let each extracted row carry explicit credibility
metadata (Sprint 2 goal: "every extracted number has a credibility score
attached"):

- state VARCHAR ∈ {scored, mentioned, cited} — whether the benchmark was
  actually measured, named-but-not-run, or only cited as reference.
- shot_count INT | null — 0 for zero-shot, 5 for 5-shot, etc.
- method TEXT | null — CoT, self-consistency, RAG, extended-thinking,
  majority-voting, none.
- language TEXT | null — for multilingual benchmarks, the evaluation
  language or "Average". "English" if explicitly English-only.
- training_state TEXT | null — pretrained, instruction-tuned, RLHF, base.
- extraction_protocol_version INT — 1 for Sprint-1-era rows,
  2 for post-Sprint-2 rows. Enables filtering old/new data in the UI.

Also adds benchmark_definitions.parent_slug for temporal/variant chains
(mmlu → mmlu_redux, swe_bench → swe_bench_verified, etc.).
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # score becomes nullable — mentioned/cited rows don't have a number.
    op.alter_column("eval_results", "score", nullable=True)

    # Eval_results — Sprint 2 structured columns
    op.add_column("eval_results", sa.Column("state", sa.String, nullable=True))
    op.add_column("eval_results", sa.Column("shot_count", sa.Integer, nullable=True))
    op.add_column("eval_results", sa.Column("method", sa.String, nullable=True))
    op.add_column("eval_results", sa.Column("language", sa.String, nullable=True))
    op.add_column("eval_results", sa.Column("training_state", sa.String, nullable=True))
    op.add_column(
        "eval_results",
        sa.Column("extraction_protocol_version", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index("ix_eval_results_state", "eval_results", ["state"])
    op.create_index("ix_eval_results_protocol", "eval_results", ["extraction_protocol_version"])

    # Benchmark definitions — parent for version chains
    op.add_column("benchmark_definitions", sa.Column("parent_slug", sa.String, nullable=True))
    op.add_column(
        "benchmark_definitions",
        sa.Column("industry_domain", sa.String, nullable=True),
    )  # idempotent — already added via scripts/industry_mapping.sql
    op.create_index("ix_benchmark_definitions_parent", "benchmark_definitions", ["parent_slug"])

    # Backfill existing rows: state='scored' (all Sprint 1 rows are scored)
    op.execute("UPDATE eval_results SET state = 'scored' WHERE state IS NULL AND score IS NOT NULL")

    # Unique constraint now includes extraction_protocol_version so v1 and
    # v2 rows for the same (doc, gen, bench, variant, model) coexist.
    op.drop_constraint("uq_eval_result", "eval_results", type_="unique")
    op.create_unique_constraint(
        "uq_eval_result", "eval_results",
        ["document_version_id", "generation_id", "benchmark_id", "variant",
         "model_name", "extraction_protocol_version"],
    )


def downgrade() -> None:
    op.drop_index("ix_benchmark_definitions_parent", table_name="benchmark_definitions")
    op.drop_column("benchmark_definitions", "industry_domain")
    op.drop_column("benchmark_definitions", "parent_slug")
    op.drop_index("ix_eval_results_protocol", table_name="eval_results")
    op.drop_index("ix_eval_results_state", table_name="eval_results")
    op.drop_column("eval_results", "extraction_protocol_version")
    op.drop_column("eval_results", "training_state")
    op.drop_column("eval_results", "language")
    op.drop_column("eval_results", "method")
    op.drop_column("eval_results", "shot_count")
    op.drop_column("eval_results", "state")
