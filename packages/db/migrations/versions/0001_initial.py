"""Initial schema with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('labs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('website', sa.String()),
        sa.Column('color_hex', sa.String()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('taxonomy_categories',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('taxonomy_categories.id')),
        sa.Column('description', sa.Text()),
        sa.Column('keywords', sa.ARRAY(sa.String())),
        sa.Column('embedding', Vector(768)),
    )

    op.create_table('documents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lab_id', sa.Integer(), sa.ForeignKey('labs.id', ondelete='SET NULL')),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('doc_type', sa.String(), nullable=False),
        sa.Column('source_url', sa.String()),
        sa.Column('is_tracked', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_documents_lab_id', 'documents', ['lab_id'])
    op.create_index('ix_documents_doc_type', 'documents', ['doc_type'])

    op.create_table('probe_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('probe_key', sa.String(), nullable=False, unique=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('subcategory', sa.String()),
        sa.Column('expected_behavior', sa.String()),
        sa.Column('notes', sa.Text()),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
    )

    op.create_table('probe_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('triggered_by', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('probe_count', sa.Integer()),
        sa.Column('model_count', sa.Integer()),
        sa.Column('status', sa.String(), server_default='running', nullable=False),
    )

    op.create_table('document_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('document_id', sa.Integer(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_date', sa.Date(), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('word_count', sa.Integer()),
        sa.Column('wayback_url', sa.String()),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('embedding', Vector(768)),
        sa.UniqueConstraint('document_id', 'content_hash', name='uq_document_version_hash'),
    )
    op.create_index('ix_document_versions_document_date', 'document_versions', ['document_id', 'version_date'])

    op.create_table('probe_responses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_id', sa.Integer(), sa.ForeignKey('probe_runs.id', ondelete='SET NULL')),
        sa.Column('probe_id', sa.Integer(), sa.ForeignKey('probe_definitions.id', ondelete='SET NULL')),
        sa.Column('model_slug', sa.String(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('prompt_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text()),
        sa.Column('error', sa.Text()),
        sa.Column('prompt_tokens', sa.Integer()),
        sa.Column('completion_tokens', sa.Integer()),
        sa.Column('latency_ms', sa.Integer()),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('embedding', Vector(768)),
    )
    op.create_index('ix_probe_responses_model_probe', 'probe_responses', ['model_slug', 'probe_id'])
    op.create_index('ix_probe_responses_recorded_at', 'probe_responses', ['recorded_at'])

    op.create_table('document_taxonomy_mappings',
        sa.Column('document_version_id', sa.Integer(), sa.ForeignKey('document_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('taxonomy_category_id', sa.Integer(), sa.ForeignKey('taxonomy_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Float()),
        sa.Column('is_covered', sa.Boolean()),
        sa.Column('coverage_depth', sa.String()),
        sa.PrimaryKeyConstraint('document_version_id', 'taxonomy_category_id'),
    )
    op.create_index('ix_dtm_category_covered', 'document_taxonomy_mappings', ['taxonomy_category_id', 'is_covered'])

    op.create_table('slant_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('response_id', sa.Integer(), sa.ForeignKey('probe_responses.id', ondelete='CASCADE'), unique=True),
        sa.Column('model_slug', sa.String(), nullable=False),
        sa.Column('probe_id', sa.Integer()),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('liberal_anchor_sim', sa.Float()),
        sa.Column('conservative_anchor_sim', sa.Float()),
        sa.Column('neutral_anchor_sim', sa.Float()),
        sa.Column('embedding_slant', sa.Float()),
        sa.Column('moral_foundations_care', sa.Float()),
        sa.Column('moral_foundations_fairness', sa.Float()),
        sa.Column('moral_foundations_loyalty', sa.Float()),
        sa.Column('moral_foundations_authority', sa.Float()),
        sa.Column('moral_foundations_purity', sa.Float()),
        sa.Column('political_valence', sa.Float()),
        sa.Column('composite_slant', sa.Float()),
        sa.Column('confidence', sa.Float()),
    )
    op.create_index('ix_slant_scores_model_probe', 'slant_scores', ['model_slug', 'probe_id'])

    op.create_table('ai_models',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('litellm_id', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    )
    op.create_index('ix_ai_models_slug', 'ai_models', ['slug'])
    op.create_index('ix_ai_models_provider', 'ai_models', ['provider'])


def downgrade() -> None:
    op.drop_table('slant_scores')
    op.drop_table('document_taxonomy_mappings')
    op.drop_table('probe_responses')
    op.drop_table('document_versions')
    op.drop_table('probe_runs')
    op.drop_table('probe_definitions')
    op.drop_table('documents')
    op.drop_table('taxonomy_categories')
    op.drop_table('ai_models')
    op.drop_table('labs')
    op.execute("DROP EXTENSION IF EXISTS vector")
