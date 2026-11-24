"""Restore 85-ID catalogue parity without activating legal scoring.

Revision ID: 0124_restore_85_rule_catalogue_parity
Revises: 0123_seed_quarantined_rule_identity_candidates

This migration makes every maintained rule ID visible as an active catalogue
and assessment row. It deliberately does not invent independent counsel
verification or statutory evidence. Product scoring eligibility is controlled
by the engine allowlists and remains separate from verification.
"""
from alembic import op
import sqlalchemy as sa

revision = "0124_restore_85_rule_catalogue_parity"
down_revision = "0123_seed_quarantined_rule_identity_candidates"
branch_labels = None
depends_on = None

EXPECTED_RULE_IDS = (
    "ACC-001", "ACC-002", "ACC-003",
    "AGM-001", "AGM-002", "AGM-003", "AGM-004", "AGM-005", "AGM-006",
    "AGM-007", "AR-001", "AR-002", "AR-003", "AR-004",
    "AUD-001", "AUD-002", "AUD-003", "AUD-004", "AUD-005",
    "BNK-001", "BNK-002", "BNK-003",
    "BOD-001", "BOD-002", "BOD-003",
    "BSEC-001", "BSEC-002", "BSEC-003", "BSEC-004",
    "CAP-001", "CAP-002", "CAP-003", "CAP-004",
    "CHG-001", "DEF-001", "DEF-002",
    "DIR-001", "DIR-002", "DIR-003", "DIR-004", "DIR-005", "DIR-006",
    "DIR-007", "DIR-008", "DIR-010",
    "ESC-001", "ESC-002", "ESC-003", "ESC-004", "ESC-005",
    "FX-001",
    "INC-001", "INC-003", "INC-004", "INC-005", "INC-006", "INC-007",
    "LBR-001", "LBR-002", "LBR-003",
    "MEM-001", "OFF-001", "REG-001", "REG-002", "REG-003",
    "SH-001", "SH-002", "SH-003",
    "STR-001", "STR-002", "STR-003",
    "TAX-001", "TAX-002", "TAX-003", "TAX-004",
    "TL-001", "TL-002",
    "TR-001", "TR-002", "TR-003", "TR-004", "TR-005", "TR-006",
    "VAT-002", "VAT-003",
)


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("""
        SELECT rule_id
          FROM public.legal_rules
         ORDER BY rule_id
    """)).scalars().all()
    actual = set(rows)
    expected = set(EXPECTED_RULE_IDS)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected not in ([], ["INC-002"]):
        raise RuntimeError(
            "0124 refuses database parity drift: "
            f"actual={len(actual)}, missing={missing!r}, unexpected={unexpected!r}"
        )

    if "INC-002" in unexpected:
        bind.execute(sa.text("""
            UPDATE public.legal_rules
               SET is_active = FALSE,
                   default_severity = 'NOT_EVALUATED',
                   score_impact = 0,
                   is_black_override = FALSE,
                   verification_status = 'PENDING',
                   updated_at = now()
             WHERE rule_id = 'INC-002'
        """))

    op.execute("""
        UPDATE public.legal_rules
           SET is_active = TRUE,
               updated_at = now()
         WHERE rule_id IN (
            'ACC-001','ACC-002','ACC-003',
            'AGM-001','AGM-002','AGM-003','AGM-004','AGM-005','AGM-006','AGM-007',
            'AR-001','AR-002','AR-003','AR-004',
            'AUD-001','AUD-002','AUD-003','AUD-004','AUD-005',
            'BNK-001','BNK-002','BNK-003',
            'BOD-001','BOD-002','BOD-003',
            'BSEC-001','BSEC-002','BSEC-003','BSEC-004',
            'CAP-001','CAP-002','CAP-003','CAP-004',
            'CHG-001','DEF-001','DEF-002',
            'DIR-001','DIR-002','DIR-003','DIR-004','DIR-005','DIR-006','DIR-007','DIR-008','DIR-010',
            'ESC-001','ESC-002','ESC-003','ESC-004','ESC-005','FX-001',
            'INC-001','INC-003','INC-004','INC-005','INC-006','INC-007',
            'LBR-001','LBR-002','LBR-003','MEM-001','OFF-001',
            'REG-001','REG-002','REG-003',
            'SH-001','SH-002','SH-003',
            'STR-001','STR-002','STR-003',
            'TAX-001','TAX-002','TAX-003','TAX-004',
            'TL-001','TL-002',
            'TR-001','TR-002','TR-003','TR-004','TR-005','TR-006',
            'VAT-002','VAT-003'
         )
    """)

    op.execute("""
        DO $validate$
        DECLARE
            active_count bigint;
        BEGIN
            SELECT count(*) INTO active_count
              FROM public.legal_rules
             WHERE is_active IS TRUE;
            IF active_count <> 85 THEN
                RAISE EXCEPTION 'Expected 85 active catalogue rows, found %', active_count;
            END IF;
        END
        $validate$
    """)


def downgrade() -> None:
    raise RuntimeError(
        "0124 is forward-only: the 85-ID catalogue parity record must not "
        "be removed or selectively deactivated."
    )
