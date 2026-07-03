"""add description and optional_placeholders

Revision ID: 0009
Revises: 0008_seed_document_templates
Create Date: 2026-07-04 04:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '0009_add_template_cols'
down_revision = '0008_seed_document_templates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ai_prompt_templates',
        sa.Column('description', sa.Text(), nullable=True)
    )
    op.add_column(
        'ai_prompt_templates',
        sa.Column('optional_placeholders', JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ai_prompt_templates', 'optional_placeholders')
    op.drop_column('ai_prompt_templates', 'description')