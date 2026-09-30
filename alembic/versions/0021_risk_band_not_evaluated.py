"""add NOT_EVALUATED to risk_band enum"""
from alembic import op

revision = "0021_risk_band_not_evaluated"
down_revision = "0020_add_hash_chain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE risk_band ADD VALUE IF NOT EXISTS 'NOT_EVALUATED'")


def downgrade() -> None:
    pass  # Postgres cannot drop an enum value
