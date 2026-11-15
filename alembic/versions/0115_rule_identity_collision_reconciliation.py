"""Quarantine colliding legacy identities without rewriting their meaning.

Revision ID: 0115_rule_identity_collision_reconciliation
Revises: 0114_annual_return_filing_status_provenance

Historical FK dependants intentionally remain attached to the unchanged
legacy legal_rules rows. Canonical INC-001 activation is deferred until a
separate, evidence-backed identity/revision migration can preserve all links.
"""
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
    payload = json.dumps(row["payload"], sort_keys=True, default=str)
    bind.execute(
        sa.text("""
            INSERT INTO public.legal_rule_identity_archive
                (legacy_identity_key, legacy_rule_id, original_payload,
                 disposition, historical_resolution, captured_at)
            VALUES (:key, :id, CAST(:payload AS jsonb), :disposition,
                    'UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW', now())
            ON CONFLICT (legacy_identity_key) DO NOTHING
        """),
        {
            "key": identity_key,
            "id": rule_id,
            "payload": payload,
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
        sa.Column("disposition", sa.String(64), nullable=False),
        sa.Column("historical_resolution", sa.String(96), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        schema="public",
    )

    inc001 = bind.execute(sa.text("""
        SELECT rule_name, statutory_basis, rule_condition
        FROM public.legal_rules WHERE rule_id='INC-001'
    """)).mappings().first()
    if inc001 is None:
        raise RuntimeError("INC-001 missing; refusing automatic identity creation")

    condition = inc001["rule_condition"] or {}
    legacy_inc001 = (
        inc001["rule_name"] == "Certificate of Incorporation Not Obtained"
        and inc001["statutory_basis"]
            == "Section 9, Companies Act 1994 (Bangladesh)"
        and isinstance(condition, dict)
        and condition.get("trigger") == "certificate_obtained == False"
    )
    if not legacy_inc001:
        raise RuntimeError(
            "INC-001 is not the exact reviewed legacy fingerprint; "
            "refusing mutation: " + repr(dict(inc001))
        )

    _archive(
        bind, "INC-001", "legacy:INC-001:companies-act-section-9",
        "QUARANTINED_LEGACY_IDENTITY",
    )
    _quarantine(
        bind, "INC-001",
        "Legacy section-9 identity quarantined. Canonical seed meaning is not "
        "bound to this row. Historical references remain attached to the "
        "unchanged legacy identity pending record-level attribution.",
    )

    inc002 = bind.execute(sa.text("""
        SELECT rule_name, statutory_basis, rule_condition
        FROM public.legal_rules WHERE rule_id='INC-002'
    """)).mappings().first()
    if inc002 is not None:
        condition_002 = inc002["rule_condition"]
        if (
            inc002["rule_name"] != "Memorandum and Articles Not Filed"
            or inc002["statutory_basis"]
                != "Section 11, Companies Act 1994 (Bangladesh)"
            or not isinstance(condition_002, dict)
            or not condition_002
        ):
            raise RuntimeError(
                "INC-002 is not the reviewed legacy fingerprint; "
                "refusing retirement: " + repr(dict(inc002))
            )
        _archive(
            bind, "INC-002", "legacy:INC-002:companies-act-section-11",
            "QUARANTINED_LEGACY_IDENTITY",
        )
        _quarantine(
            bind, "INC-002",
            "Legacy section-11 identity quarantined and excluded from the "
            "canonical 85-rule manifest. ID is reserved and must never be reused.",
        )


def downgrade():
    # Forward-only: restoring a previously active colliding rule could
    # reintroduce unsupported scoring. Restore requires a reviewed procedure.
    pass
