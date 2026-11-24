"""Reconcile the known AGM-001 legacy citation spelling to the canonical registry.

Revision ID: 0125_reconcile_agm001_catalogue_identity
Revises: 0124_restore_85_rule_catalogue_parity

Only the exact legacy Section 81 citation emitted by migration 0026 is eligible.
The full pre-change row is captured in the append-only identity archive. Any
other basis or inactive/missing row stops the migration; no legal verification
or statutory conclusion is implied by this technical identity reconciliation.
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
ARCHIVE_KEY = "legacy:AGM-001:section-81-to-81-1:0125"


def upgrade() -> None:
    bind = op.get_bind()

    row = bind.execute(
        sa.text(
            "SELECT to_jsonb(r) AS payload "
            "FROM public.legal_rules AS r "
            "WHERE r.rule_id = :rule_id "
            "FOR UPDATE"
        ),
        {"rule_id": RULE_ID},
    ).mappings().first()
    if row is None:
        raise RuntimeError(
            "0125 requires the migrated AGM-001 catalogue row; refusing to seed "
            "or infer a replacement identity."
        )

    payload = row["payload"]
    current_basis = payload.get("statutory_basis")
    if payload.get("is_active") is not True:
        raise RuntimeError(
            "0125 requires active AGM-001; refusing to reactivate an inactive rule."
        )
    if current_basis == CANONICAL_BASIS:
        return
    if current_basis != LEGACY_BASIS:
        raise RuntimeError(
            "0125 found an unrecognized AGM-001 statutory basis; refusing to "
            f"overwrite a conflicting legal definition: {current_basis!r}"
        )

    serialized = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    )
    payload_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # The archive is FORCE-RLS and append-only. Permit this exact migration
    # principal to append the before-image; runtime and audit roles remain denied.
    op.execute("""
        DO $policy$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'nlc_migration_owner'
            ) THEN
                RAISE EXCEPTION
                    '0125 requires the dedicated nlc_migration_owner role';
            END IF;
            EXECUTE 'DROP POLICY IF EXISTS legal_rule_identity_archive_migration_insert '
                || 'ON public.legal_rule_identity_archive';
            EXECUTE 'CREATE POLICY legal_rule_identity_archive_migration_insert '
                || 'ON public.legal_rule_identity_archive FOR INSERT TO nlc_migration_owner '
                || 'WITH CHECK (current_user = ''nlc_migration_owner'')';
        END
        $policy$
    """)

    bind.execute(
        sa.text("""
            INSERT INTO public.legal_rule_identity_archive (
                legacy_identity_key,
                legacy_rule_id,
                original_payload,
                payload_sha256,
                disposition,
                historical_resolution,
                captured_at
            )
            VALUES (
                :archive_key,
                :rule_id,
                CAST(:payload AS jsonb),
                :payload_sha256,
                'CANONICAL_BASIS_RECONCILIATION',
                'UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW',
                now()
            )
        """),
        {
            "archive_key": ARCHIVE_KEY,
            "rule_id": RULE_ID,
            "payload": serialized,
            "payload_sha256": payload_sha256,
        },
    )

    # 0115 grants the dedicated migration login a narrowly scoped bypass of
    # the legal_rules version-snapshot trigger. No application principal does.
    bind.execute(
        sa.text("""
            UPDATE public.legal_rules
               SET statutory_basis = :canonical_basis,
                   updated_at = now()
             WHERE rule_id = :rule_id
               AND is_active IS TRUE
               AND statutory_basis = :legacy_basis
        """),
        {
            "canonical_basis": CANONICAL_BASIS,
            "rule_id": RULE_ID,
            "legacy_basis": LEGACY_BASIS,
        },
    )
    updated = bind.execute(
        sa.text("""
            SELECT statutory_basis
              FROM public.legal_rules
             WHERE rule_id = :rule_id
        """),
        {"rule_id": RULE_ID},
    ).scalar_one_or_none()
    if updated != CANONICAL_BASIS:
        raise RuntimeError(
            "0125 AGM-001 reconciliation did not produce the canonical registry basis."
        )


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: restoring the legacy AGM-001 citation would "
        "reintroduce catalogue/evaluator identity drift."
    )
