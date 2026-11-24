"""Reconcile the known AGM-001 legacy citation with the canonical registry.

Revision ID: 0125_reconcile_agm001_catalogue_identity
Revises: 0124_restore_85_rule_catalogue_parity

Only the exact, fingerprinted 0026 AGM-001 row may be normalized. Its full
pre-image is archived before changing statutory_basis; conflicting definitions
are rejected rather than silently overwritten.
"""
import hashlib
import json

import sqlalchemy as sa
from alembic import op

revision = "0125_reconcile_agm001_catalogue_identity"
down_revision = "0124_restore_85_rule_catalogue_parity"
branch_labels = None
depends_on = None

RULE_ID = "AGM-001"
LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
LEGACY_NAME = "First AGM Default"
LEGACY_TYPE = "DEADLINE"
LEGACY_DESCRIPTION = (
    "First AGM not held within 18 months (548 days) of incorporation. "
    "Section 81 is mandatory; no waiver for private companies. "
    "Default counts from day after deadline."
)
LEGACY_CONDITION = {
    "check_fn": "check_agm_001",
    "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
    "trigger": "first_agm_held == False AND days_since_incorporation > 548",
}
ARCHIVE_KEY = "legacy:AGM-001:pre-0125-statutory-basis"
ARCHIVE_TABLE = "legal_rule_identity_archive"


def _fail(message: str, row=None) -> None:
    detail = f"; observed={dict(row)!r}" if row is not None else ""
    raise RuntimeError(f"0125 AGM-001 reconciliation refused: {message}{detail}")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "legal_rules" not in inspector.get_table_names(schema="public"):
        _fail("public.legal_rules is missing")
    if ARCHIVE_TABLE not in inspector.get_table_names(schema="public"):
        _fail("public.legal_rule_identity_archive is missing")

    archive_columns = {
        column["name"]
        for column in inspector.get_columns(ARCHIVE_TABLE, schema="public")
    }
    required_archive_columns = {
        "legacy_identity_key",
        "legacy_rule_id",
        "original_payload",
        "payload_sha256",
        "disposition",
        "historical_resolution",
        "captured_at",
    }
    missing_archive_columns = sorted(required_archive_columns - archive_columns)
    if missing_archive_columns:
        _fail(f"archive schema is incompatible; missing {missing_archive_columns!r}")

    row = bind.execute(
        sa.text(
            """
            SELECT
                to_jsonb(r) AS payload,
                r.rule_name,
                r.rule_type::text AS rule_type,
                r.statutory_basis,
                r.description,
                r.rule_condition,
                r.is_active
            FROM public.legal_rules AS r
            WHERE r.rule_id = :rule_id
            """
        ),
        {"rule_id": RULE_ID},
    ).mappings().one_or_none()

    if row is None:
        _fail("the migrated AGM-001 catalogue row is missing")
    if row["is_active"] is not True:
        _fail("AGM-001 is not active after 0124; refusing to reactivate it", row)

    # Fingerprint the complete known legacy legal definition from migration 0026.
    # This migration changes no name, condition, description, severity, or score.
    observed_definition = {
        "rule_name": row["rule_name"],
        "rule_type": row["rule_type"],
        "description": row["description"],
        "rule_condition": row["rule_condition"],
    }
    expected_definition = {
        "rule_name": LEGACY_NAME,
        "rule_type": LEGACY_TYPE,
        "description": LEGACY_DESCRIPTION,
        "rule_condition": LEGACY_CONDITION,
    }
    if observed_definition != expected_definition:
        _fail(
            "AGM-001 no longer matches the exact known 0026 legacy definition; "
            "manual/legal review is required before any reconciliation",
            observed_definition,
        )

    existing_archive = bind.execute(
        sa.text(
            f"""
            SELECT legacy_rule_id, payload_sha256, disposition,
                   historical_resolution
            FROM public.{ARCHIVE_TABLE}
            WHERE legacy_identity_key = :archive_key
            """
        ),
        {"archive_key": ARCHIVE_KEY},
    ).mappings().one_or_none()

    if row["statutory_basis"] == CANONICAL_BASIS:
        if existing_archive is None:
            _fail(
                "AGM-001 is already canonical but has no archived before-image; "
                "refusing to accept an unattributed manual rewrite",
                row,
            )
        if (
            existing_archive["legacy_rule_id"] != RULE_ID
            or existing_archive["disposition"] != "CANONICAL_BASIS_RECONCILIATION"
            or existing_archive["historical_resolution"]
            != "UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW"
            or not existing_archive["payload_sha256"]
        ):
            _fail("the existing AGM-001 archive record is inconsistent", existing_archive)
        return

    if row["statutory_basis"] != LEGACY_BASIS:
        _fail(
            "statutory_basis is neither the exact known legacy value nor the "
            "canonical registry value; refusing to overwrite a conflicting definition",
            row,
        )
    if existing_archive is not None:
        _fail(
            "an archive record already exists while the catalogue still has the "
            "legacy basis; refusing duplicate or inconsistent history",
            existing_archive,
        )

    # Preserve the complete row before-image and its deterministic digest.
    payload = json.dumps(
        row["payload"],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    payload_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    bind.execute(
        sa.text(
            f"""
            INSERT INTO public.{ARCHIVE_TABLE}
                (legacy_identity_key, legacy_rule_id, original_payload,
                 payload_sha256, disposition, historical_resolution, captured_at)
            VALUES
                (:archive_key, :rule_id, CAST(:payload AS jsonb), :payload_sha256,
                 'CANONICAL_BASIS_RECONCILIATION',
                 'UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW', now())
            """
        ),
        {
            "archive_key": ARCHIVE_KEY,
            "rule_id": RULE_ID,
            "payload": payload,
            "payload_sha256": payload_sha256,
        },
    )

    # Conditional update: only the exact known legacy citation can be changed.
    result = bind.execute(
        sa.text(
            """
            UPDATE public.legal_rules
               SET statutory_basis = :canonical_basis,
                   updated_at = now()
             WHERE rule_id = :rule_id
               AND is_active IS TRUE
               AND statutory_basis = :legacy_basis
            """
        ),
        {
            "canonical_basis": CANONICAL_BASIS,
            "rule_id": RULE_ID,
            "legacy_basis": LEGACY_BASIS,
        },
    )
    if result.rowcount != 1:
        _fail(f"expected exactly one conditional AGM-001 update, got {result.rowcount}")

    reconciled_basis = bind.execute(
        sa.text(
            "SELECT statutory_basis FROM public.legal_rules WHERE rule_id = :rule_id"
        ),
        {"rule_id": RULE_ID},
    ).scalar_one()
    if reconciled_basis != CANONICAL_BASIS:
        _fail(f"post-update basis is not canonical: {reconciled_basis!r}")


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: restoring the legacy AGM-001 citation requires "
        "a separately reviewed, evidence-backed migration."
    )
