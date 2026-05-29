"""benchmark_definitions.policy_note — plain-language paper-style block

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-29

Adds a nullable JSON column on benchmark_definitions to hold the
EvaluationCards-style Policy Note block (Figure 3 of the NeurIPS 2026
EvalCards paper): measures / caveat / intended_for / how_to_read + topic
tags + source links. Nullable so existing rows stay valid; the API + UI
render gracefully when absent. Populated from YAML via seed_db.
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "benchmark_definitions",
        sa.Column("policy_note", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("benchmark_definitions", "policy_note")
