"""Fix 27 statutory citation errors against verified Companies Act 1994 text

Revision: 0030_fix_citation_errors
Revises: 0029_fix_inc001_inc002_identities

Cross-referenced all engine citations against the actual BD Companies Act 1994
text (Act No. 18 of 1994, 404 sections). Found 27 citation errors where the
engine cited the wrong section number.

Key corrections:
- INC-001/002: Section 11 → 23 (registration of MoA/AoA)
- AGM-005/006: Section 83 → 89 (minutes of proceedings)
- CAP-003: Section 100 → 59 (reduction of share capital)
- DIR-001..004: Section 92 → 115 (register of directors, 14-day filing)
- DIR-005/006: Section 97/98 → 130 (disclosure of interest)
- SH-001: Section 50 → 151 (return as to allotment, 60 days)
- SH-002: Section 46 → 158 (issue of certificates, 90 days)
- TR-001/003/005: Section 108/47 → 38 (transfer of shares)
- ESC-001/002: Section 304 → 346 (strike off defunct company)
- ESC-004: Section 196 → 286 (voluntary winding up)
- ESC-005: Section 199 → 195 (investigation of affairs)
- DEF-002: Section 447 → 397 (penalty for false statement — Section 447 doesn't exist, Act has 404 sections)

Deadline corrections:
- SH-001 allotment filing: 30 → 60 days (Section 151)
- SH-002 share certificates: 60 → 90 days (Section 158)
"""
from alembic import op

revision = '0030_fix_citation_errors'
down_revision = '0029_fix_inc001_inc002_identities'
branch_labels = None
depends_on = None

FIXES = [
    ("INC-001", "Section 23, Companies Act 1994 (Bangladesh)"),
    ("INC-002", "Section 23, Companies Act 1994 (Bangladesh)"),
    ("INC-004", "Section 53, Companies Act 1994 (Bangladesh)"),
    ("AGM-005", "Section 89, Companies Act 1994 (Bangladesh)"),
    ("AGM-006", "Section 89, Companies Act 1994 (Bangladesh)"),
    ("AGM-007", "Section 85, Companies Act 1994 (Bangladesh)"),
    ("CAP-001", "Section 53, Companies Act 1994 (Bangladesh)"),
    ("CAP-003", "Section 59, Companies Act 1994 (Bangladesh)"),
    ("DIR-001", "Section 115, Companies Act 1994 (Bangladesh)"),
    ("DIR-002", "Section 115, Companies Act 1994 (Bangladesh)"),
    ("DIR-003", "Section 115, Companies Act 1994 (Bangladesh)"),
    ("DIR-004", "Section 115, Companies Act 1994 (Bangladesh)"),
    ("DIR-005", "Section 130, Companies Act 1994 (Bangladesh)"),
    ("DIR-006", "Section 130, Companies Act 1994 (Bangladesh)"),
    ("SH-001", "Section 151, Companies Act 1994 (Bangladesh)"),
    ("SH-002", "Section 158, Companies Act 1994 (Bangladesh)"),
    ("SH-003", "Section 56, Companies Act 1994 (Bangladesh)"),
    ("TR-001", "Section 38, Companies Act 1994 (Bangladesh)"),
    ("TR-003", "Section 38; AoA, Companies Act 1994 (Bangladesh)"),
    ("TR-005", "Section 38; AoA, Companies Act 1994 (Bangladesh)"),
    ("ESC-001", "Section 346, Companies Act 1994 (Bangladesh)"),
    ("ESC-002", "Section 346, Companies Act 1994 (Bangladesh)"),
    ("ESC-003", "Sections 81, 115, 36, 346 (aggregate), Companies Act 1994 (Bangladesh)"),
    ("ESC-004", "Section 286, Companies Act 1994 (Bangladesh)"),
    ("ESC-005", "Section 195, Companies Act 1994 (Bangladesh)"),
    ("DEF-002", "Section 397, Companies Act 1994 (Bangladesh)"),
]


def upgrade():
    for rule_id, basis in FIXES:
        basis_escaped = basis.replace("'", "''")
        op.execute(
            f"UPDATE legal_rules SET statutory_basis = '{basis_escaped}' "
            f"WHERE rule_id = '{rule_id}';"
        )


def downgrade():
    pass
