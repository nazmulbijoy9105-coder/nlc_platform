"""Re-quarantine the legacy INC-001 catalogue row after 0124 reactivation.

Revision ID: 0125_requarantine_legacy_inc001_catalogue_row
Revises: 0124_restore_85_rule_catalogue_parity

0124 restored catalogue visibility by activating all 85 IDs, but that also
reactivated the legacy Section 9 INC-001 row quarantined by 0115. The canonical
engine's INC-001 is a distinct Section 23 verification concept. This migration
restores the 0115 quarantine without changing the legacy definition, primary
key, child rows, findings, evidence, or historical references.
"""
from alembic import op
import sqlalchemy as sa

revision = "0125_requarantine_legacy_inc001_catalogue_row"
down_revision = "0124_restore_85_rule_catalogue_parity"
branch_labels = None
depends_on = None

LEGACY_IDENTITY_KEY = "legacy:INC-001:preserved-original-definition"
ALLOWED_LEGACY_FINGERPRINTS = {
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
    (
        "Memorandum and Articles Not Filed",
        "Section 11, Companies Act 1994 (Bangladesh)",
        "moa_aoa_filed == False",
    ),
}


def upgrade() -> None:
    bind = op.get_bind()

    # The immutable 0115 archive is the authority for the legacy row's
    # pre-quarantine payload. Never infer identity from rule_id alone.
    archived = bind.execute(
        sa.text("""
            SELECT original_payload
              FROM public.legal_rule_identity_archive
             WHERE legacy_identity_key = :identity_key
        """),
        {"identity_key": LEGACY_IDENTITY_KEY},
    ).mappings().one_or_none()
    if archived is None:
        raise RuntimeError(
            "0125 refuses to proceed: the immutable 0115 INC-001 archive is missing"
        )

    archive_payload = archived["original_payload"]
    archived_condition = archive_payload.get("rule_condition") or {}
    archived_fingerprint = (
        archive_payload.get("rule_name"),
        archive_payload.get("statutory_basis"),
        archived_condition.get("trigger"),
    )
    if (
        archive_payload.get("rule_id") != "INC-001"
        or archived_fingerprint not in ALLOWED_LEGACY_FINGERPRINTS
    ):
        raise RuntimeError(
            "0125 refuses to proceed: the immutable archive does not match an "
            "explicitly accepted 0115 legacy INC-001 fingerprint"
        )

    current = bind.execute(
        sa.text("""
            SELECT id, rule_id, rule_name, statutory_basis, rule_condition,
                   default_severity::text AS default_severity,
                   score_impact, is_black_override, is_active,
                   verification_status::text AS verification_status
              FROM public.legal_rules
             WHERE rule_id = 'INC-001'
             FOR UPDATE
        """)
    ).mappings().one_or_none()
    if current is None:
        raise RuntimeError("0125 refuses to proceed: legal_rules INC-001 is missing")

    current_condition = current["rule_condition"] or {}
    current_fingerprint = (
        current["rule_name"],
        current["statutory_basis"],
        current_condition.get("trigger"),
    )
    if (
        current_fingerprint != archived_fingerprint
        or current_condition != archived_condition
        or current["default_severity"] != "NOT_EVALUATED"
        or current["score_impact"] != 0
        or current["is_black_override"] is not False
        or current["verification_status"] != "PENDING"
    ):
        raise RuntimeError(
            "0125 refuses to mutate an INC-001 row whose definition or release "
            "controls differ from the archived legacy Section 9 identity"
        )

    if current["is_active"] is True:
        bind.execute(
            sa.text("""
                UPDATE public.legal_rules
                   SET is_active = FALSE,
                       updated_at = now()
                 WHERE id = :row_id
                   AND rule_id = 'INC-001'
                   AND is_active IS TRUE
            """),
            {"row_id": current["id"]},
        )

    final_active = bind.execute(
        sa.text("""
            SELECT is_active
              FROM public.legal_rules
             WHERE id = :row_id
        """),
        {"row_id": current["id"]},
    ).scalar_one()
    if final_active is not False:
        raise RuntimeError("0125 failed to restore legacy INC-001 quarantine")


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: do not reactivate the legacy INC-001 identity. "
        "A future canonical Section 23 release requires a distinct, approved "
        "identity and effective-dated legal revision."
    )
