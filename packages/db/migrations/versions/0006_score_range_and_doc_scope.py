"""Add score_min/score_max to benchmark_definitions + doc_scope to documents

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-17

score_min/score_max: required for input validation. Claude occasionally
hallucinates out-of-range scores (e.g. MMLU = 150). The extractor will
reject scores outside [min, max] when defined.

doc_scope: classifies documents by role (capability_paper, safety_paper,
technical_paper, model_card, system_card, policy_doc, license,
usage_policy, constitution). Surfaces "why 0 benchmarks" — a policy doc
is expected to have none. Populated from doc_type + title heuristics on
migration; new sources can set explicitly via the collector registry.
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) score range on benchmark definitions (idempotent — may already exist)
    op.execute(
        "ALTER TABLE benchmark_definitions ADD COLUMN IF NOT EXISTS score_min DOUBLE PRECISION"
    )
    op.execute(
        "ALTER TABLE benchmark_definitions ADD COLUMN IF NOT EXISTS score_max DOUBLE PRECISION"
    )

    # 2) doc_scope on documents
    op.add_column(
        "documents",
        sa.Column("doc_scope", sa.String, nullable=True),
    )
    op.create_index("ix_documents_doc_scope", "documents", ["doc_scope"])

    # 3) Backfill doc_scope from doc_type + title heuristics. Keep simple and
    #    safe — treat unknowns as NULL so they're visible and fixable.
    op.execute("""
        UPDATE documents SET doc_scope = CASE
          WHEN doc_type = 'system_card' THEN 'system_card'
          WHEN doc_type = 'technical_paper' THEN 'technical_paper'
          WHEN doc_type = 'model_card' AND title ILIKE '%system card%' THEN 'system_card'
          WHEN doc_type = 'model_card' AND title ILIKE '%technical report%' THEN 'technical_paper'
          WHEN doc_type = 'model_card' AND title ILIKE '%paper%' THEN 'technical_paper'
          WHEN doc_type = 'model_card' THEN 'model_card'
          WHEN doc_type = 'usage_policy' THEN 'usage_policy'
          WHEN doc_type = 'constitution' THEN 'constitution'
          WHEN doc_type = 'license' THEN 'license'
          ELSE NULL
        END
    """)


def downgrade() -> None:
    op.drop_index("ix_documents_doc_scope", table_name="documents")
    op.drop_column("documents", "doc_scope")
    op.execute("ALTER TABLE benchmark_definitions DROP COLUMN IF EXISTS score_max")
    op.execute("ALTER TABLE benchmark_definitions DROP COLUMN IF EXISTS score_min")
