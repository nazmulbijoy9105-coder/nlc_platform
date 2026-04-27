"""Seed all 30 ILRMF rules into legal_rules

NEUM LEX COUNSEL — Database Migration
Revision:  0002
Previous:  0001

Seeds the legal_rules table with all 30 ILRMF rules.
These rules are the core IP of the platform.
Every rule includes: rule_id, statutory_basis, score_impact,
severity, revenue_tier, is_black_override, version.

AI Constitution Article 1: Only Super Admin may modify rules.
This migration is read-only after initial seeding.
Changes to rules must go through a new migration (never edit this one).

Release Governance Protocol: Rule changes require:
  - change_reason documenting legal basis
  - legal_rule_versions entry with previous definition
  - Super Admin approval
"""
from typing import Sequence, Union
from datetime import date

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Rule definitions — all 30 ILRMF rules ────────────────────────────
# Format: (rule_id, rule_name, rule_type, statutory_basis, description,
#           default_severity, score_impact, revenue_tier, is_black_override)
ILRMF_RULES = [

    # ── AGM RULES (6) ─────────────────────────────────────────────
    (
        "AGM-001",
        "First AGM Default",
        "AGM",
        "Section 81, Companies Act 1994 (Bangladesh)",
        "First AGM not held within 18 months (548 days) of incorporation. "
        "Section 81 requires the first AGM within 18 months of incorporation "
        "or 9 months after the financial year end, whichever is earlier.",
        "RED", 25, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "AGM-002",
        "Subsequent AGM Default",
        "AGM",
        "Section 81, Companies Act 1994 (Bangladesh)",
        "Subsequent AGM not held within 15 months (456 days) of the previous AGM, "
        "or within 6 months (182 days) of the financial year end. "
        "Section 81 requires AGMs at intervals of not more than 15 months.",
        "YELLOW", 20, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "AGM-003",
        "AGM Notice Defective",
        "AGM",
        "Section 86, Companies Act 1994 (Bangladesh)",
        "AGM notice sent with fewer than 21 clear days before the meeting. "
        "Section 86 requires a minimum of 21 clear days written notice to all members.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "AGM-004",
        "AGM Notice Missing",
        "AGM",
        "Section 86, Companies Act 1994 (Bangladesh)",
        "No written notice sent to members before AGM. "
        "Section 86 requires written notice specifying time, place, and agenda.",
        "RED", 20, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "AGM-005",
        "AGM Quorum Not Met",
        "AGM",
        "Section 83, Companies Act 1994 (Bangladesh)",
        "AGM held without meeting quorum requirements. "
        "Section 83: minimum 2 members present in person for private companies.",
        "YELLOW", 15, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "AGM-006",
        "Auditor Not Reappointed at AGM",
        "AGM",
        "Section 210, Companies Act 1994 (Bangladesh)",
        "Retiring auditor not reappointed and no new auditor appointed at AGM. "
        "Section 210 requires appointment or reappointment of auditor at each AGM.",
        "YELLOW", 15, "COMPLIANCE_PACKAGE", False,
    ),

    # ── AUDIT RULES (3) ───────────────────────────────────────────
    (
        "AUD-001",
        "Audit Not Complete Before AGM",
        "AUDIT",
        "Section 210, Companies Act 1994 (Bangladesh)",
        "Annual audit not completed before the AGM was held. "
        "Audited accounts must be presented at AGM under Section 210.",
        "RED", 20, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "AUD-002",
        "First Auditor Not Appointed",
        "AUDIT",
        "Section 210, Companies Act 1994 (Bangladesh)",
        "First auditor not appointed within 30 days of incorporation. "
        "Section 210: first auditor must be appointed by the Board within 30 days.",
        "YELLOW", 15, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "AUD-003",
        "AGM Held Without Completed Audit — BLACK OVERRIDE",
        "AUDIT",
        "Section 210, Companies Act 1994 (Bangladesh)",
        "AGM was held and recorded as complete, but no audit had been completed or signed. "
        "This is a fundamental statutory breach. AGM proceedings may be invalid. "
        "BLACK OVERRIDE: forces company score to BLACK band regardless of all other scores.",
        "BLACK", 25, "CORPORATE_RESCUE", True,
    ),

    # ── ANNUAL RETURN RULES (4) ───────────────────────────────────
    (
        "AR-001",
        "Annual Return Default",
        "RETURN",
        "Section 190, Companies Act 1994 (Bangladesh)",
        "Annual return not filed with RJSC within 30 days of AGM. "
        "Section 190 requires filing within 30 days of the date of AGM.",
        "YELLOW", 20, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "AR-002",
        "Annual Return 2-Year Backlog",
        "RETURN",
        "Section 190, Companies Act 1994 (Bangladesh)",
        "Annual returns unfiled for 2 or more consecutive years. "
        "Multi-year default significantly increases RJSC enforcement risk.",
        "RED", 20, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "AR-003",
        "Annual Return 3-Year Backlog — BLACK ESCALATION",
        "RETURN",
        "Sections 190, 396, Companies Act 1994 (Bangladesh)",
        "Annual returns unfiled for 3 or more consecutive years. "
        "RJSC strike-off risk is high. Section 396 permits striking off "
        "companies not filing returns. Triggers escalation to BLACK.",
        "BLACK", 20, "CORPORATE_RESCUE", False,
    ),
    (
        "AR-004",
        "Annual Return Filed But Incomplete",
        "RETURN",
        "Section 190, Companies Act 1994 (Bangladesh)",
        "Annual return filed with RJSC but missing required attachments "
        "(audited accounts, list of directors, list of shareholders). "
        "Incomplete filing does not satisfy Section 190 requirements.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),

    # ── DIRECTOR RULES (4) ────────────────────────────────────────
    (
        "DIR-001",
        "Director Appointment Not Filed",
        "DIRECTOR",
        "Section 115, Companies Act 1994 (Bangladesh)",
        "Director appointment not filed with RJSC within 30 days. "
        "Section 115 requires filing Form XII within 30 days of appointment.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "DIR-002",
        "Director Resignation Not Filed",
        "DIRECTOR",
        "Section 115, Companies Act 1994 (Bangladesh)",
        "Director resignation or removal not filed with RJSC within 30 days. "
        "Section 115 requires filing Form XII within 30 days of any change.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "DIR-003",
        "Major Director Irregularity — Over 1 Year Unfiled",
        "DIRECTOR",
        "Section 115, Companies Act 1994 (Bangladesh)",
        "Director change (appointment or departure) unfiled for more than 1 year. "
        "Prolonged non-filing creates personal liability risk for all directors.",
        "RED", 15, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "DIR-004",
        "Departed Director Still Shown as Active",
        "DIRECTOR",
        "Section 115, Companies Act 1994 (Bangladesh)",
        "A director who has departed (resigned, removed, or deceased) is still "
        "recorded as active with RJSC. The departed director may retain personal "
        "liability for company obligations incurred after their actual departure.",
        "RED", 15, "STRUCTURED_REGULARIZATION", False,
    ),

    # ── SHAREHOLDER RULES (1) ─────────────────────────────────────
    (
        "SH-001",
        "Shareholder Change Not Filed",
        "DIRECTOR",
        "Section 190, Companies Act 1994 (Bangladesh)",
        "Change in shareholding not reflected in annual return filed with RJSC. "
        "Annual return must include updated list of members and shareholding.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),

    # ── TRANSFER RULES (6) ────────────────────────────────────────
    (
        "TR-001",
        "No Share Transfer Instrument",
        "TRANSFER",
        "Section 82, Companies Act 1994 (Bangladesh)",
        "Share transfer completed without a properly executed transfer instrument "
        "(Form 117). Section 82 requires a proper instrument of transfer "
        "executed by both transferor and transferee.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "TR-002",
        "Stamp Duty Not Paid on Transfer",
        "TRANSFER",
        "Stamp Act 1899 (Bangladesh), Section 82 Companies Act 1994",
        "Share transfer instrument executed without payment of applicable stamp duty. "
        "Unstamped transfer instrument is inadmissible as evidence and may be void.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "TR-003",
        "No Board Approval for Share Transfer",
        "TRANSFER",
        "Articles of Association, Companies Act 1994 (Bangladesh)",
        "Share transfer completed without obtaining board approval as required "
        "by the Articles of Association. Most private company AoAs require "
        "board approval before share transfers are registered.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "TR-004",
        "Register of Members Not Updated After Transfer",
        "TRANSFER",
        "Section 34, Companies Act 1994 (Bangladesh)",
        "Share transfer not recorded in the Register of Members within 2 months "
        "of lodgement. Section 34 requires the register to reflect all transfers.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "TR-005",
        "Share Transfer Violates AoA Restriction — BLACK OVERRIDE",
        "TRANSFER",
        "Articles of Association, Companies Act 1994 (Bangladesh)",
        "Share transfer executed in breach of transfer restriction in Articles of "
        "Association (pre-emption rights, board approval requirements, permitted "
        "transferee classes). Such transfer may be void and unenforceable. "
        "BLACK OVERRIDE: forces company score to BLACK band.",
        "BLACK", 25, "CORPORATE_RESCUE", True,
    ),
    (
        "TR-006",
        "Composite Irregular Transfer",
        "TRANSFER",
        "Multiple sections, Companies Act 1994 (Bangladesh)",
        "Share transfer has multiple concurrent irregularities (TR-001 through TR-005). "
        "Composite irregularity compounds legal risk significantly.",
        "RED", 20, "STRUCTURED_REGULARIZATION", False,
    ),

    # ── REGISTER RULES (2) ────────────────────────────────────────
    (
        "REG-001",
        "Statutory Registers Incomplete",
        "REGISTER",
        "Sections 34, 115, 148, Companies Act 1994 (Bangladesh)",
        "One or more of the 6 mandatory statutory registers are not maintained: "
        "Register of Members, Register of Directors, Register of Charges, "
        "Register of Debenture Holders, Register of Contracts, Minutes Book. "
        "Failure to maintain is a continuing offence under the Act.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "REG-002",
        "Share Certificate Not Issued Within Deadline",
        "REGISTER",
        "Section 82, Companies Act 1994 (Bangladesh)",
        "Share certificate not issued within 2 months of allotment or 1 month "
        "of lodgement of transfer. Section 82 requires timely certificate issuance.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "REG-004",
        "Statutory Register Core Maintenance",
        "REGISTER",
        "Section 26, Companies Act 1994 (Bangladesh)",
        "Core statutory registers (Members, Directors, Charges) must be maintained. "
        "Failure to maintain core registers is a high-risk statutory default.",
        "RED", 15, "STRUCTURED_REGULARIZATION", False,
    ),

    # ── OFFICE RULES (1) ──────────────────────────────────────────
    (
        "OFF-001",
        "Registered Office Change Not Filed",
        "REGISTER",
        "Section 77, Companies Act 1994 (Bangladesh)",
        "Change of registered office address not notified to RJSC within 30 days. "
        "Section 77 requires filing of Form XIV within 30 days of any change.",
        "YELLOW", 5, "COMPLIANCE_PACKAGE", False,
    ),

    # ── CAPITAL RULES (2) ─────────────────────────────────────────
    (
        "CAP-001",
        "Capital Alteration Without Board Resolution",
        "CASCADE",
        "Section 54, Companies Act 1994 (Bangladesh)",
        "Alteration to authorized or paid-up capital without a proper board "
        "or shareholder resolution. Section 54 requires specific resolutions "
        "and filing with RJSC.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),
    (
        "CAP-002",
        "Charge Not Filed with RJSC",
        "CASCADE",
        "Section 107, Companies Act 1994 (Bangladesh)",
        "Charge (mortgage, debenture, or other security) created on company "
        "assets not filed with RJSC within 30 days. Section 107: unregistered "
        "charge is void against liquidator and creditors.",
        "YELLOW", 10, "COMPLIANCE_PACKAGE", False,
    ),

    # ── ESCALATION RULES (3) ──────────────────────────────────────
    (
        "ESC-001",
        "Strike-Off Risk Elevated",
        "ESCALATION",
        "Section 396, Companies Act 1994 (Bangladesh)",
        "Company shows pattern consistent with RJSC strike-off criteria: "
        "multiple years of missed filings, no evidence of trading, or "
        "cumulative RED flags across multiple modules. Proactive action required.",
        "RED", 20, "STRUCTURED_REGULARIZATION", False,
    ),
    (
        "ESC-002",
        "Strike-Off Imminent — BLACK OVERRIDE",
        "ESCALATION",
        "Section 396, Companies Act 1994 (Bangladesh)",
        "Company is at immediate risk of RJSC strike-off action. "
        "Section 396 criteria met: 3+ years of non-filing, RJSC notice received, "
        "or company showing in RJSC strike-off list. Immediate rescue required. "
        "BLACK OVERRIDE: forces company score to BLACK band.",
        "BLACK", 30, "CORPORATE_RESCUE", True,
    ),
    (
        "ESC-003",
        "Corporate Rescue Mandatory — BLACK OVERRIDE",
        "ESCALATION",
        "Multiple sections, Companies Act 1994 (Bangladesh)",
        "Cumulative severity across all modules requires mandatory rescue intervention. "
        "Score has dropped below 30 (BLACK band) due to multi-module defaults. "
        "8-step rescue sequence must be initiated immediately. "
        "BLACK OVERRIDE: forces and maintains BLACK band.",
        "BLACK", 30, "CORPORATE_RESCUE", True,
    ),
]


def upgrade() -> None:
    conn = op.get_bind()

    # Get or create a placeholder super admin for seeding
    # In production, this will be replaced by the actual SUPER_ADMIN user ID
    # The seed_super_admin_id is a well-known UUID used only for seeded data
    seed_super_admin_id = "00000000-0000-0000-0000-000000000001"

    # Insert ILRMF rules
    for (rule_id, rule_name, rule_type, statutory_basis, description,
         severity, score_impact, revenue_tier, is_black_override) in ILRMF_RULES:

        conn.execute(sa.text("""
            INSERT INTO legal_rules (
                id, rule_id, rule_name, rule_type,
                statutory_basis, description,
                default_severity, score_impact, revenue_tier,
                is_black_override, rule_version, is_active,
                created_at, updated_at
            ) VALUES (
                uuid_generate_v4(),
                :rule_id, :rule_name, CAST(:rule_type AS rule_type),
                :statutory_basis, :description,
                CAST(:severity AS severity_level),
                :score_impact,
                CAST(:revenue_tier AS revenue_tier),
                :is_black_override, '1.0', TRUE,
                NOW(), NOW()
            )
            ON CONFLICT (rule_id) DO NOTHING;
        """), {
            "rule_id":           rule_id,
            "rule_name":         rule_name,
            "rule_type":         rule_type,
            "statutory_basis":   statutory_basis,
            "description":       description,
            "severity":          severity,
            "score_impact":      score_impact,
            "revenue_tier":      revenue_tier,
            "is_black_override": is_black_override,
        })

    # Verify all rules inserted (33 rules: 30 base + ESC-003 + REG-003 + cascade rules)
    result = conn.execute(sa.text("SELECT COUNT(*) FROM legal_rules")).scalar()
    assert result >= 33, f"Expected at least 33 rules, got {result}"


def downgrade() -> None:
    """Remove all seeded ILRMF rules."""
    conn = op.get_bind()
    rule_ids = [r[0] for r in ILRMF_RULES]
    conn.execute(
        sa.text("DELETE FROM legal_rules WHERE rule_id = ANY(:ids)"),
        {"ids": rule_ids}
    )
