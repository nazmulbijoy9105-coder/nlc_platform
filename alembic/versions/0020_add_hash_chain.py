"""Add hash chain columns to compliance_score_history

Revision ID: 0020_add_hash_chain
Revises: 0019_add_rjsc_forms
"""
from alembic import op

revision = '0020_add_hash_chain'
down_revision = '0019_add_rjsc_forms'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("ALTER TABLE compliance_score_history ADD COLUMN IF NOT EXISTS previous_hash VARCHAR(64)")
    op.execute("ALTER TABLE compliance_score_history ADD COLUMN IF NOT EXISTS current_hash VARCHAR(64)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_score_hash ON compliance_score_history(current_hash)")

def downgrade():
    op.execute("ALTER TABLE compliance_score_history DROP COLUMN IF EXISTS previous_hash")
    op.execute("ALTER TABLE compliance_score_history DROP COLUMN IF EXISTS current_hash")
