"""Preserve rescue audit evidence when a rescue plan is deleted.

Revision ID: 0065_rescue_audit_log_restrict_delete
Revises: 0064_financial_review_actor_binding
"""
from alembic import op

revision = "0065_rescue_audit_log_restrict_delete"
down_revision = "0064_financial_review_actor_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0038 originally used ON DELETE CASCADE. That allowed deleting a rescue
    # plan to erase its audit evidence even when the audit table itself was
    # append-only. Replace the FK with RESTRICT so the evidence survives.
    op.execute("""
        DO $migration$
        DECLARE
            plan_attnum smallint;
            old_constraint text;
        BEGIN
            SELECT attnum
              INTO plan_attnum
              FROM pg_attribute
             WHERE attrelid = 'public.rescue_audit_log'::regclass
               AND attname = 'rescue_plan_id'
               AND NOT attisdropped;

            IF plan_attnum IS NULL THEN
                RAISE EXCEPTION 'rescue_audit_log.rescue_plan_id is missing';
            END IF;

            SELECT conname
              INTO old_constraint
              FROM pg_constraint
             WHERE conrelid = 'public.rescue_audit_log'::regclass
               AND confrelid = 'public.rescue_plans'::regclass
               AND contype = 'f'
               AND conkey = ARRAY[plan_attnum]::smallint[];

            IF old_constraint IS NULL THEN
                RAISE EXCEPTION
                    'Expected rescue_audit_log -> rescue_plans foreign key is missing';
            END IF;

            EXECUTE format(
                'ALTER TABLE public.rescue_audit_log DROP CONSTRAINT %I',
                old_constraint
            );
            EXECUTE '
                ALTER TABLE public.rescue_audit_log
                ADD CONSTRAINT rescue_audit_log_plan_restrict_fk
                FOREIGN KEY (rescue_plan_id)
                REFERENCES public.rescue_plans(id)
                ON DELETE RESTRICT
                NOT VALID
            ';
            EXECUTE '
                ALTER TABLE public.rescue_audit_log
                VALIDATE CONSTRAINT rescue_audit_log_plan_restrict_fk
            ';
        END
        $migration$;
    """)


def downgrade() -> None:
    # Forward-only: restoring ON DELETE CASCADE would make audit evidence
    # deletable through parent-row deletion.
    pass
