"""harden company_user_access with RLS

Revision ID: 0025_harden_access_table_rls
Revises: 0024_harden_tenant_rls
Create Date: 2026-10-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0025_harden_access_table_rls'
down_revision = '0024_harden_tenant_rls'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable RLS on the access control table
    op.execute("ALTER TABLE company_user_access ENABLE ROW LEVEL SECURITY;")
    
    # Drop existing policy if any
    op.execute("DROP POLICY IF EXISTS company_user_access_policy ON company_user_access;")
    
    # Create policy: Admins see all, users only see rows where they are the user_id
    op.execute("""
        CREATE POLICY company_user_access_policy ON company_user_access
        USING (
            current_setting('app.current_user_id', TRUE) = 'ADMIN'
            OR user_id = current_setting('app.current_user_id', TRUE)::uuid
        )
        WITH CHECK (
            current_setting('app.current_user_id', TRUE) = 'ADMIN'
            OR user_id = current_setting('app.current_user_id', TRUE)::uuid
        );
    """)

def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS company_user_access_policy ON company_user_access;")
    op.execute("ALTER TABLE company_user_access DISABLE ROW LEVEL SECURITY;")
