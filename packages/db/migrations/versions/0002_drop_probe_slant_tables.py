"""Drop probe, slant, and ai_model tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-24
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop in FK-dependency order
    op.drop_index("ix_slant_scores_model_probe", table_name="slant_scores", if_exists=True)
    op.drop_table("slant_scores")

    op.drop_index("ix_probe_responses_model_probe", table_name="probe_responses", if_exists=True)
    op.drop_index("ix_probe_responses_recorded_at", table_name="probe_responses", if_exists=True)
    op.drop_table("probe_responses")

    op.drop_table("probe_runs")
    op.drop_table("probe_definitions")

    op.drop_index("ix_ai_models_slug", table_name="ai_models", if_exists=True)
    op.drop_index("ix_ai_models_provider", table_name="ai_models", if_exists=True)
    op.drop_table("ai_models")


def downgrade() -> None:
    pass  # One-way migration — bias features removed permanently
