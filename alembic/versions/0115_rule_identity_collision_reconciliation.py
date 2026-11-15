"""Preserve legacy rule identities and restore canonical INC-001 identity.

Revision ID: 0115_rule_identity_collision_reconciliation
Revises: 0114_annual_return_filing_status_provenance

This migration changes only the current legal_rules registry row. It never
rewrites historical findings or claims that an ID alone proves attribution.
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

INC001_CANONICAL = {
    "rule_name": "MoA/AoA Registration Status Requires Verification",
    "rule_type": "DEADLINE",
    "statutory_basis": "Section 23, Companies Act 1994 (Bangladesh)",
    "description": (
        "MoA/AoA registration is governed by section 23. Non-production in NLC "
        "records is not proof of non-registration or invalidity; verify the RJSC "
        "registration record, certified copies, incorporation date and amendments."
    ),
    "rule_condition": {
        "check_fn": "check_inc_001",
        "trigger": (
            "moa_aoa_verified == True AND moa_aoa_evidence_ref IS NOT NULL "
            "AND moa_aoa_filed == False"
        ),
        "data_points": [
            "moa_aoa_filed",
            "moa_aoa_verified",
            "moa_aoa_evidence_ref",
            "rjsc_registry_search_result",
        ],
    },
    "revenue_tier": "STRUCTURED_REGULARIZATION",
    "default_severity": "NOT_EVALUATED",
    "score_impact": 0,
    "is_black_override": False,
    "is_active": True,
    "verification_status": "PENDING",
}

REQUIRED_RULE_COLUMNS = {
    "rule_id", "rule_name", "rule_type", "statutory_basis", "description",
    "rule_condition", "revenue_tier", "default_severity", "score_impact",
    "is_black_override", "is_active", "verification_status",
    "verification_notes", "updated_at",
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
    bind.execute(
        sa.text("""
            INSERT INTO public.legal_rule_identity_archive
                (legacy_identity_key, legacy_rule_id, original_payload,
                 disposition, historical_resolution, captured_at)
            VALUES (:key, :id, CAST(:payload AS jsonb), :disposition,
                    'AMBIGUOUS_UNLESS_HISTORICAL_SNAPSHOT_BINDS_DEFINITION',
                    now())
            ON CONFLICT (legacy_identity_key) DO NOTHING
        """),
        {
            "key": identity_key,
            "id": rule_id,
            "payload": json.dumps(row["payload"], default=str),
            "disposition": disposition,
        },
    )
    return row["payload"]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "legal_rules" not in inspector.get_table_names(schema="public"):
        raise RuntimeError("identity reconciliation requires public.legal_rules")

    available_columns = {
        column["name"]
        for column in inspector.get_columns("legal_rules", schema="public")
    }
    missing_columns = sorted(REQUIRED_RULE_COLUMNS - available_columns)
    if missing_columns:
        raise RuntimeError(
            "legal_rules schema is not compatible with identity reconciliation; "
            f"missing columns: {missing_columns!r}"
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

    # FK references are a hard stop. Non-FK/JSON references are inventoried
    # separately by scripts/audit_rule_historical_attribution.py; they are
    # never rewritten by this migration.
    fk_rows = bind.execute(sa.text("""
        SELECT tc.table_schema, tc.table_name, kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name=kcu.constraint_name
         AND tc.constraint_schema=kcu.constraint_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name=tc.constraint_name
         AND ccu.constraint_schema=tc.constraint_schema
        WHERE tc.constraint_type='FOREIGN KEY'
          AND ccu.table_schema='public'
          AND ccu.table_name='legal_rules'
          AND ccu.column_name='rule_id'
    """)).mappings().all()
    if fk_rows:
        raise RuntimeError(
            "Refusing rule identity rewrite while FK dependants exist: "
            + repr([dict(row) for row in fk_rows])
        )

    current = bind.execute(sa.text("""
        SELECT rule_name, rule_type, statutory_basis, description,
               rule_condition, revenue_tier, default_severity, score_impact,
               is_black_override, is_active, verification_status
        FROM public.legal_rules WHERE rule_id='INC-001'
    """)).mappings().first()

    if current is not None:
        condition = current["rule_condition"] or {}
        is_legacy = (
            current["rule_name"] == "Certificate of Incorporation Not Obtained"
            and current["statutory_basis"]
                == "Section 9, Companies Act 1994 (Bangladesh)"
            and condition.get("trigger") == "certificate_obtained == False"
        )
        is_canonical = all(
            current[field] == INC001_CANONICAL[field]
            for field in (
                "rule_name", "rule_type", "statutory_basis", "description",
                "rule_condition", "revenue_tier", "default_severity",
                "score_impact", "is_black_override", "is_active",
                "verification_status",
            )
        )
        if is_legacy:
            _archive(
                bind, "INC-001", "legacy:INC-001:companies-act-section-9",
                "PRESERVED_LEGACY_IDENTITY",
            )
            bind.execute(sa.text("""
                UPDATE public.legal_rules
                SET rule_name=:name, rule_type=:type, statutory_basis=:basis,
                    description=:description,
                    rule_condition=CAST(:condition AS jsonb),
                    revenue_tier=:revenue_tier,
                    default_severity='NOT_EVALUATED', score_impact=0,
                    is_black_override=false, is_active=true,
                    verification_status='PENDING',
                    verification_notes=COALESCE(verification_notes, '') ||
                      CASE WHEN COALESCE(verification_notes, '')='' THEN '' ELSE E'\\n' END ||
                      'Canonical identity restored from seed. Prior section-9 identity archived; historical findings remain unresolved until independently attributed.',
                    updated_at=now()
                WHERE rule_id='INC-001'
            """), {
                "name": INC001_CANONICAL["rule_name"],
                "type": INC001_CANONICAL["rule_type"],
                "basis": INC001_CANONICAL["statutory_basis"],
                "description": INC001_CANONICAL["description"],
                "condition": json.dumps(INC001_CANONICAL["rule_condition"]),
                "revenue_tier": INC001_CANONICAL["revenue_tier"],
            })
        elif not is_canonical:
            raise RuntimeError(
                "INC-001 has an unrecognized or partially canonical identity; "
                "refusing overwrite: " + repr(dict(current))
            )

    legacy_002 = bind.execute(sa.text("""
        SELECT rule_name, statutory_basis, rule_condition
        FROM public.legal_rules WHERE rule_id='INC-002'
    """)).mappings().first()
    if legacy_002 is not None:
        condition_002 = legacy_002["rule_condition"] or {}
        if (
            legacy_002["rule_name"] != "Memorandum and Articles Not Filed"
            or legacy_002["statutory_basis"]
                != "Section 11, Companies Act 1994 (Bangladesh)"
            or not isinstance(condition_002, dict)
            or not condition_002
        ):
            raise RuntimeError(
                "INC-002 has an unrecognized or incomplete identity; "
                "refusing retirement: " + repr(dict(legacy_002))
            )
        _archive(
            bind, "INC-002", "legacy:INC-002:companies-act-section-11",
            "RETIRED_LEGACY_IDENTITY",
        )
        bind.execute(sa.text("""
            UPDATE public.legal_rules
            SET is_active=false, verification_status='PENDING',
                verification_notes=COALESCE(verification_notes, '') ||
                  CASE WHEN COALESCE(verification_notes, '')='' THEN '' ELSE E'\\n' END ||
                  'Retired legacy identity; preserved for audit and not part of canonical 85. ID must never be reused.',
                updated_at=now()
            WHERE rule_id='INC-002'
        """))

    if current is None:
        raise RuntimeError(
            "INC-001 missing; restore canonical row through reviewed seed "
            "reconciliation first"
        )


def downgrade():
    # Forward-only: restoring a colliding legacy primary identity is unsafe.
    pass
