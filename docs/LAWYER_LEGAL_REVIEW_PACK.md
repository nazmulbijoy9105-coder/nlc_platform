# NLC Platform — Lawyer Legal Review Pack

**Status:** PENDING LEGAL REVIEW  
**Engine Version:** 2.1  
**Rule Count:** 75 active rules  
**Date Prepared:** 2026-10-01

## Documents for Review

| Document | Purpose |
|----------|---------|
| docs/LEGAL_BASIS_MATRIX.md | Full rule-to-statute mapping (UNVERIFIED) |
| app/rule_engine/engine.py | Rule implementation with statutory_basis strings |
| scripts/seed_rules.py | Seed data with rule definitions |
| alembic/versions/0002_seed_ilrmf_rules.py | Original 30 rules |
| alembic/versions/0015_add_extended_legal_rules.py | 10 extended rules |
| alembic/versions/0013_add_bankruptcy_labour_rules.py | 6 bankruptcy/labour rules |

## Key Discrepancies to Resolve

| Rule | Engine Says | Seed Says | Question |
|------|------------|-----------|----------|
| AGM-003 | Section 85, 21 clear days | Section 86 | Which section governs AGM notice? |
| AR-001 | Section 36, 21 days | Section 190, 30 days | Which section + deadline? |
| DIR-001 | Section 92, 14 days | Section 115, 30 days | Which section + deadline? |
| VAT-003 | "After September" cutoff | VAT Act 2012 | Verify exact cutoff date |
| DEF-002 | Section 447, Tk 10,000 fine | - | Verify exact penalty amount |

## Statutory Instruments Referenced

1. Companies Act 1994 (Bangladesh) — 65 rules
2. Bankruptcy Act 1997 (Bangladesh) — 3 rules
3. Labour Act 2006 (Bangladesh) — 3 rules
4. BSEC Corporate Governance Code 2023 — 4 rules
5. Income Tax Act 2023 (Bangladesh) — 4 rules
6. Value Added Tax Act 2012 (Bangladesh) — 2 rules
7. Foreign Exchange Regulation Act 1947 — 1 rule
8. Stamp Act 1899 — 1 rule
9. City Corporation Ordinance 1983 / Pourashava Act 2009 — 2 rules
10. BIDA Foreign Investment Act 1980 — 2 rules

## Reviewer

- Name: [TO BE ASSIGNED]
- Qualification: Bangladesh-qualified lawyer
- Date Started: [TO BE SET]
- Date Completed: [TO BE SET]
- Sign-off: [ ] All 75 rule citations verified against primary sources

## Limitation

The engine-derived rules and LEGAL_BASIS_MATRIX.md must be treated as material
for lawyer verification, not as proof of legal validity. Until verified,
the platform carries the disclaimer: "Automated compliance screening. Not legal
advice. Consult your legal counsel."
