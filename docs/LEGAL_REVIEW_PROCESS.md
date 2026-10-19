# Annual Legal Citation Review Process

## Purpose

This document defines the yearly process for verifying all statutory citations in the NLC Platform rule engine against the authoritative source texts of Bangladesh corporate law.

## Scope

The review covers citations from:

| Law | Rules | Source |
|-----|-------|--------|
| Companies Act 1994 | INC, AGM, AUD, AR, DIR, TR, SH, CAP, REG, OFF, ESC, DEF, BOD, ACC, MEM, TL | bdlaws.minlaw.gov.bd/act-788.html |
| VAT Act 2012 | VAT-002, VAT-003 | bdlaws.minlaw.gov.bd |
| Income Tax Act 2023 | TAX-001-004 | bdlaws.minlaw.gov.bd |
| Bangladesh Labour Act 2006 | LBR-001-003 | bdlaws.minlaw.gov.bd |
| Bankruptcy Act 1997 / Liquidation Act 2018 | BNK-001-003 | bdlaws.minlaw.gov.bd |
| Foreign Exchange Regulation Act 1947 | FX-001 | bdlaws.minlaw.gov.bd |
| BSEC Corporate Governance Code 2023 | BSEC-001-004 | bsec.gov.bd |
| City Corporation Ordinance 1983 | TL-001-002 | Local government law |

## Verification Status

Each rule in the legal_rules table has a verification_status field:

| Status | Meaning | Action |
|--------|---------|--------|
| VERIFIED | Citation confirmed against primary source by a lawyer | No action needed |
| PENDING | Citation not yet verified (default for new rules) | Schedule for next review |
| DISPUTED | Citation confirmed wrong, correction pending | Fix before next release |

## Annual Review Schedule

### January - Plan
1. Export current citation inventory from database
2. Identify rules with PENDING or DISPUTED status
3. Identify any new rules added since last review
4. Compile full text of all relevant laws from bdlaws.minlaw.gov.bd

### February-March - Review
1. Engage a Bangladesh corporate lawyer for the review
2. Provide the lawyer with the citation inventory and full law texts
3. Lawyer reviews each rule citation against the primary source
4. Lawyer updates verification_status to VERIFIED or DISPUTED

### April - Implement
1. Apply any corrections from the review
2. Run python scripts/check_rule_verification.py to verify no regressions
3. Deploy corrected citations
4. Generate updated LEGAL_BASIS_MATRIX.md from the database

## Per-Claim Verification

Each rule makes up to four distinct claims that must be verified independently:

| Claim | Example | Verification method |
|-------|---------|-------------------|
| Section | Section 210(1) | Check section exists and covers the topic |
| Deadline | within 30 days | Read the full section text for the deadline |
| Penalty | 200 Taka/day | Read the penalty subsection |
| Applicability | all companies vs listed only | Check if the section applies to private/public/all |

A rule is VERIFIED only when all four claims are confirmed.

## CI Check

The CI pipeline (scripts/check_rule_verification.py) enforces:
- New rules (in engine.py but not in seed_rules.py) are blocked
- Regressions (VERIFIED to PENDING/DISPUTED) are blocked
- Existing PENDING rules are NOT blocked (that would fail every release)

## Key Lessons from the 2026 Audit

1. Secondary sources are not enough. Always verify against the official gazette (bdlaws.minlaw.gov.bd).
2. Section existence must be confirmed. The Act has 404 sections. Citing Section 447 (which does not exist) was caught only by checking the Act header.
3. Deadlines and penalties must be verified separately from section existence.
4. Applicability matters. BOD-001 may only bind listed companies.
5. Single source of truth. The verification_status field on legal_rules is authoritative.
6. Date fields need is None, not is False. None means not set for date fields.

## Source Documents

| Document | Location | Purpose |
|----------|----------|---------|
| Companies Act 1994 (Bangladesh) | bdlaws.minlaw.gov.bd/act-788.html | Primary source for corporate law citations |
| Issue 6 Legal Citation Audit | docs/audit/issue-6-legal-citation-audit.md | Latest audit findings |
| Citation Tracking CSV | docs/audit/issue-6-citation-tracking.csv | Per-rule verification status |

---

**Last review:** October 2026 (initial audit)
**Next review:** January 2027 (annual cycle begins)
**Version:** 1.0
