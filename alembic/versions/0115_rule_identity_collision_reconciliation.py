"""Quarantine colliding legacy identities without rewriting their meaning.

Revision ID: 0115_rule_identity_collision_reconciliation
Revises: 0114_annual_return_filing_status_provenance

Historical FK dependants intentionally remain attached to the unchanged
legacy legal_rules rows. Canonical INC-001 activation is deferred until a
separate, evidence-backed identity/revision migration can preserve all links.
"""
import hashlib
import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0115_rule_identity_collision_reconciliation"
down_revision = "0114_annual_return_filing_status_provenance"
branch_labels = None
depends_on = None

ARCHIVE_TABLE = "legal_rule_identity_archive"
REQUIRED_RULE_COLUMNS = {
    "rule_id", "rule_name", "statutory_basis", "rule_condition",
    "default_severity", "score_impact", "is_black_override",
    "is_active", "verification_status", "verification_notes", "updated_at",
}

# Fingerprints are accepted only to quarantine an existing legacy row.
# They do not establish legal equivalence, approval, or historical attribution.
# The first tuple for each ID is the currently observed production/restore
# definition (INC-001 s9; INC-002 s11). The Section 23 variants are retained
# only for databases that genuinely carry the post-0030 migration-chain rows.
INC001_LEGACY_FINGERPRINTS = (
    (
        "Certificate of Incorporation Not Obtained",
        "Section 9, Companies Act 1994 (Bangladesh)",
        "certificate_obtained == False",
    ),
    (
        "Memorandum and Articles Not Filed",
        "Section 23, Companies Act 1994 (Bangladesh)",
        "moa_aoa_filed == False",
    ),
    # Observed legacy hybrid: Section 11 identity fields from the
    # historical INC-001 catalogue row, with the later-populated
    # moa_aoa_filed trigger. Accepted ONLY for archive/quarantine.
    (
        "Memorandum and Articles Not Filed",
        "Section 11, Companies Act 1994 (Bangladesh)",
        "moa_aoa_filed == False",
    ),
)
INC002_LEGACY_FINGERPRINTS = (
    (
        "Memorandum and Articles Not Filed",
        "Section 11, Companies Act 1994 (Bangladesh)",
        "moa_filed == False OR aoa_filed == False",
    ),
    (
        "Form III Not Filed",
        "Section 23, Companies Act 1994 (Bangladesh)",
        "paid_up_capital_bdt > 0 AND form_iii_filed == False AND days_since_incorporation > 28",
    ),
)


def _archive(bind, rule_id, identity_key, disposition):
    row = bind.execute(
        sa.text(
            "SELECT to_jsonb(r) AS payload FROM public.legal_rules r "
            "WHERE rule_id=:id"
        ),
        {"id": rule_id},
    ).mappings().first()
    if row is None:
        return None

    payload = json.dumps(
        row["payload"], sort_keys=True, separators=(",", ":"), default=str
    )
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    bind.execute(
        sa.text("""
            INSERT INTO public.legal_rule_identity_archive
                (legacy_identity_key, legacy_rule_id, original_payload,
                 payload_sha256, disposition, historical_resolution, captured_at)
            VALUES (:key, :id, CAST(:payload AS jsonb), :payload_sha256,
                    :disposition,
                    'UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW', now())
        """),
        {
            "key": identity_key,
            "id": rule_id,
            "payload": payload,
            "payload_sha256": payload_sha256,
            "disposition": disposition,
        },
    )
    return row["payload"]


def _quarantine(bind, rule_id, note):
    # Deliberately do not alter rule_id, name, statutory basis, condition,
    # version, source mappings, or any historical child rows.
    bind.execute(sa.text("""
        UPDATE public.legal_rules
        SET is_active=false,
            default_severity='NOT_EVALUATED',
            score_impact=0,
            is_black_override=false,
            verification_status='PENDING',
            verification_notes=COALESCE(verification_notes, '') ||
              CASE WHEN COALESCE(verification_notes, '')='' THEN '' ELSE E'\\n' END ||
              :note,
            updated_at=now()
        WHERE rule_id=:rule_id
    """), {"rule_id": rule_id, "note": note})


def _matches_legacy(row, fingerprints):
    condition = row["rule_condition"] or {}
    if not isinstance(condition, dict):
        return False
    return any(
        row["rule_name"] == name
        and row["statutory_basis"] == basis
        and condition.get("trigger") == trigger
        for name, basis, trigger in fingerprints
    )


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "legal_rules" not in inspector.get_table_names(schema="public"):
        raise RuntimeError("identity reconciliation requires public.legal_rules")

    available = {
        column["name"]
        for column in inspector.get_columns("legal_rules", schema="public")
    }
    missing = sorted(REQUIRED_RULE_COLUMNS - available)
    if missing:
        raise RuntimeError(
            "legal_rules schema is incompatible; missing columns: "
            + repr(missing)
        )

    op.create_table(
        ARCHIVE_TABLE,
        sa.Column("legacy_identity_key", sa.String(160), primary_key=True),
        sa.Column("legacy_rule_id", sa.String(32), nullable=False, index=True),
        sa.Column(
            "original_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("disposition", sa.String(64), nullable=False),
        sa.Column("historical_resolution", sa.String(96), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )

    inc001 = bind.execute(sa.text("""
        SELECT rule_name, statutory_basis, rule_condition
        FROM public.legal_rules WHERE rule_id='INC-001'
    """)).mappings().first()
    if inc001 is None or not _matches_legacy(inc001, INC001_LEGACY_FINGERPRINTS):
        raise RuntimeError(
            "INC-001 does not match an explicitly quarantinable legacy fingerprint; "
            "refusing mutation: " + repr(dict(inc001) if inc001 else None)
        )

    _archive(
        bind, "INC-001", "legacy:INC-001:preserved-original-definition",
        "QUARANTINED_LEGACY_IDENTITY",
    )
    _quarantine(
        bind, "INC-001",
        "Legacy INC-001 identity quarantined. canonical Section 23 seed meaning is not "
        "bound to this row. Historical references remain attached to the "
        "unchanged legacy identity pending record-level attribution.",
    )

    inc002 = bind.execute(sa.text("""
        SELECT rule_name, statutory_basis, rule_condition
        FROM public.legal_rules WHERE rule_id='INC-002'
    """)).mappings().first()
    if inc002 is not None:
        if not _matches_legacy(inc002, INC002_LEGACY_FINGERPRINTS):
            raise RuntimeError(
                "INC-002 does not match an explicitly quarantinable legacy fingerprint; "
                "refusing retirement: " + repr(dict(inc002))
            )
        _archive(
            bind, "INC-002", "legacy:INC-002:preserved-original-definition",
            "QUARANTINED_LEGACY_IDENTITY",
        )
        _quarantine(
            bind, "INC-002",
            "Legacy INC-002 identity quarantined and excluded from the "
            "canonical 85-rule manifest. This is not a legal conclusion; ID is reserved and must never be reused.",
        )


    # Apply access restrictions only after the migration transaction has
    # captured and quarantined the exact rows. FORCE RLS with no policy would
    # otherwise block this migration's own archive INSERT on owner roles.
    # This archive contains identity evidence. Force RLS and deny runtime/audit
    # access after the migration's archive writes are complete.
    op.execute(f"ALTER TABLE public.{ARCHIVE_TABLE} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE public.{ARCHIVE_TABLE} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"REVOKE ALL PRIVILEGES ON TABLE public.{ARCHIVE_TABLE} "
        "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
    )
    op.execute("""
        CREATE FUNCTION public.prevent_legacy_rule_identity_archive_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $fn$
        BEGIN
            RAISE EXCEPTION 'legal_rule_identity_archive is append-only: % is forbidden',
                TG_OP USING ERRCODE = '55000';
        END;
        $fn$
    """)
    op.execute(
        f"CREATE TRIGGER trg_{ARCHIVE_TABLE}_append_only "
        f"BEFORE UPDATE OR DELETE ON public.{ARCHIVE_TABLE} "
        "FOR EACH ROW EXECUTE FUNCTION public.prevent_legacy_rule_identity_archive_mutation()"
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.prevent_legacy_rule_identity_archive_mutation() "
        "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
    )

def downgrade():
    # Forward-only: restoring a quarantined identity requires a reviewed migration.
    raise RuntimeError(
        "0115 is forward-only: restoring quarantined legacy rules requires "
        "a separately reviewed, evidence-backed procedure."
    )
