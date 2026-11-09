"""Quarantine unapproved legal rules and reconcile confirmed share-rule metadata drift.

Revision ID: 0090_rule_registry_drift_quarantine
Revises: 0089_unique_active_compliance_flags

This forward-only migration preserves the full before/after definition of every
legal_rules row in an append-only audit table. It does not confer legal approval.
Migrations 0002 and 0003 remain immutable historical records.
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0090_rule_registry_drift_quarantine"
down_revision = "0089_unique_active_compliance_flags"
branch_labels = None
depends_on = None

AUDIT_TABLE = "legal_rule_reconciliation_audit"
CHANGE_REASON = (
    "0090 fail-closed legal registry reconciliation: quarantine all unapproved "
    "catalogue rows and correct confirmed SH-001/SH-002 database metadata drift "
    "to the maintained engine/seed catalogue. This is technical metadata "
    "reconciliation only, not independent statutory approval."
)

SHARE_RULE_FIXES = {
    "SH-001": {
        "rule_name": "Share Allotment Not Filed — Form XV",
        "statutory_basis": "Section 151, Companies Act 1994 (Bangladesh)",
        "description": (
            "Section 151 requires a company having share capital to file the "
            "return of allotment and prescribed supporting documents within "
            "60 days after allotment, subject to any Registrar extension "
            "granted under the section."
        ),
        "rule_condition": {
            "check_fn": "check_sh_001",
            "trigger": (
                "last_allotment_date IS NOT NULL AND form_xv_filed == False "
                "AND days_since_allotment > 60"
            ),
            "data_points": ["last_allotment_date", "form_xv_filed"],
        },
    },
    "SH-002": {
        "rule_name": "Share Certificates Not Issued Within 90 Days",
        "statutory_basis": "Section 158, Companies Act 1994 (Bangladesh)",
        "description": (
            "Section 158 requires share certificates within 90 days after "
            "allotment or registration of transfer. This rule currently "
            "models allotment date only; transfer-registration events must "
            "be added before complete coverage can be claimed."
        ),
        "rule_condition": {
            "check_fn": "check_sh_002",
            "trigger": (
                "share_certificates_issued == False AND "
                "last_allotment_date IS NOT NULL AND days_since_allotment > 90"
            ),
            "data_points": ["share_certificates_issued", "last_allotment_date"],
        },
    },
}


def _next_version(current: str | None) -> str:
    value = current or "1.0"
    try:
        major, minor = value.split(".", 1)
        return f"{major}.{int(minor) + 1}"
    except (TypeError, ValueError):
        return "1.1"


def upgrade() -> None:
    bind = op.get_bind()

    # Fail before creating objects or changing rows if this is not the expected
    # schema/release chain. In particular, never silently skip a missing rule.
    required_columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("legal_rules", schema="public")
    }
    required = {
        "rule_id", "rule_name", "statutory_basis", "description",
        "rule_condition", "default_severity", "score_impact",
        "is_black_override", "verification_status", "verified_by",
        "verified_at", "rule_version", "is_active", "updated_at",
    }
    missing = sorted(required - required_columns)
    if missing:
        raise RuntimeError(
            "0090 legal-rule reconciliation preflight failed; missing columns: "
            + ", ".join(missing)
        )

    missing_helpers = bind.execute(
        sa.text(
            "SELECT to_regprocedure('public.nlc_current_user_is_finance_staff()')"
        )
    ).scalar_one()
    if missing_helpers is None:
        raise RuntimeError(
            "0090 requires signed-identity RLS helper "
            "public.nlc_current_user_is_finance_staff()"
        )

    not_evaluated_exists = bind.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1
            FROM pg_type t
            JOIN pg_enum e ON e.enumtypid = t.oid
            JOIN pg_namespace n ON n.oid = t.typnamespace
            WHERE n.nspname = 'public'
              AND t.typname = 'severity_level'
              AND e.enumlabel = 'NOT_EVALUATED'
        )
    """)).scalar_one()
    if not not_evaluated_exists:
        raise RuntimeError(
            "0090 requires public.severity_level.NOT_EVALUATED; refusing "
            "to coerce unapproved rules into a scored severity"
        )

    rows = bind.execute(sa.text("""
        SELECT rule_id, rule_version, to_jsonb(legal_rules) AS before_definition
        FROM public.legal_rules
        ORDER BY rule_id
    """)).mappings().all()
    present_ids = {row["rule_id"] for row in rows}
    missing_share_rules = sorted(set(SHARE_RULE_FIXES) - present_ids)
    if missing_share_rules:
        raise RuntimeError(
            "0090 requires both confirmed drift rows; missing: "
            + ", ".join(missing_share_rules)
        )
    if len(rows) < 85:
        raise RuntimeError(
            f"0090 expected at least 85 legal_rules rows, found {len(rows)}"
        )

    op.create_table(
        AUDIT_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rule_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("migration_revision", sa.String(length=80), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_identifier", sa.String(length=120), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("before_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="public",
    )

    # The audit record is readable only through signed finance-staff identity.
    # Application runtime receives SELECT only; mutation is prohibited by both
    # grants and a database trigger. Migration-owner writes bypass RLS.
    op.execute(
        f"ALTER TABLE public.{AUDIT_TABLE} ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        f"ALTER TABLE public.{AUDIT_TABLE} FORCE ROW LEVEL SECURITY"
    )
    op.execute(f"""
        CREATE POLICY legal_rule_reconciliation_audit_finance_read
        ON public.{AUDIT_TABLE}
        FOR SELECT
        USING (public.nlc_current_user_is_finance_staff())
    """)
    op.execute(f"REVOKE ALL ON TABLE public.{AUDIT_TABLE} FROM PUBLIC")
    op.execute(f"GRANT SELECT ON TABLE public.{AUDIT_TABLE} TO nlc_app_role")

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_rule_reconciliation_audit_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'legal_rule_reconciliation_audit is append-only';
        END;
        $function$
    """)
    op.execute(f"""
        CREATE TRIGGER {AUDIT_TABLE}_reject_update_delete
        BEFORE UPDATE OR DELETE ON public.{AUDIT_TABLE}
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_reject_rule_reconciliation_audit_mutation()
    """)
    op.execute(f"""
        CREATE TRIGGER {AUDIT_TABLE}_reject_truncate
        BEFORE TRUNCATE ON public.{AUDIT_TABLE}
        FOR EACH STATEMENT
        EXECUTE FUNCTION public.nlc_reject_rule_reconciliation_audit_mutation()
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "public.nlc_reject_rule_reconciliation_audit_mutation() FROM PUBLIC"
    )

    for row in rows:
        rule_id = row["rule_id"]
        updates = SHARE_RULE_FIXES.get(rule_id, {})
        next_version = _next_version(row["rule_version"])

        bind.execute(
            sa.text("""
                UPDATE public.legal_rules
                SET
                    rule_name = COALESCE(:rule_name, rule_name),
                    statutory_basis = COALESCE(:statutory_basis, statutory_basis),
                    description = COALESCE(:description, description),
                    rule_condition = COALESCE(
                        CAST(:rule_condition AS jsonb), rule_condition
                    ),
                    default_severity = 'NOT_EVALUATED'::public.severity_level,
                    score_impact = 0,
                    is_black_override = FALSE,
                    verification_status = 'PENDING',
                    verified_by = NULL,
                    verified_at = NULL,
                    rule_version = :rule_version,
                    updated_at = :updated_at
                WHERE rule_id = :rule_id
            """),
            {
                "rule_id": rule_id,
                "rule_name": updates.get("rule_name"),
                "statutory_basis": updates.get("statutory_basis"),
                "description": updates.get("description"),
                "rule_condition": (
                    json.dumps(updates["rule_condition"])
                    if "rule_condition" in updates else None
                ),
                "rule_version": next_version,
                "updated_at": datetime.now(UTC),
            },
        )
        after = bind.execute(
            sa.text("""
                SELECT to_jsonb(legal_rules)
                FROM public.legal_rules
                WHERE rule_id = :rule_id
            """),
            {"rule_id": rule_id},
        ).scalar_one()

        bind.execute(
            sa.text(f"""
                INSERT INTO public.{AUDIT_TABLE} (
                    id, rule_id, migration_revision, actor_type,
                    actor_identifier, change_reason,
                    before_definition, after_definition
                ) VALUES (
                    :id, :rule_id, :migration_revision, 'ALEMBIC_MIGRATION',
                    :actor_identifier, :change_reason,
                    CAST(:before_definition AS jsonb),
                    CAST(:after_definition AS jsonb)
                )
            """),
            {
                "id": uuid.uuid4(),
                "rule_id": rule_id,
                "migration_revision": revision,
                "actor_identifier": revision,
                "change_reason": CHANGE_REASON,
                "before_definition": json.dumps(
                    row["before_definition"], default=str
                ),
                "after_definition": json.dumps(after, default=str),
            },
        )


def downgrade() -> None:
    # Forward-only: reverting would restore unapproved scoring/BLACK metadata
    # and erase the audit provenance of the registry quarantine.
    pass
