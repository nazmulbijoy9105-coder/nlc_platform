# NLC Platform — Lawyer Legal Review Pack

**Purpose:** This document contains all legal references, statutory citations, and rule definitions
for review by a Bangladesh-qualified lawyer before commercial launch.

**Status:** PENDING LEGAL REVIEW

## What Needs Review

1. **75 Rules** — Each rule's statutory_basis, deadline, and penalty text
2. **Section References** — Verify all "Section XX" references against actual gazetted text
3. **Deadlines** — Confirm 14-day vs 30-day filing periods, 18-month AGM deadline, etc.
4. **Severity Assignments** — Confirm BLACK/RED/YELLOW severity is appropriate
5. **VAT-003** — "After September" cutoff date — verify against VAT Act 2012
6. **Section 447** — Penalty wording for DEF-002 — verify exact fine amount

## Key Discrepancies to Resolve

| Issue | Engine Says | Seed Says | Needs Lawyer |
|-------|------------|-----------|--------------|
| AGM-003 notice | Section 85, 21 clear days | Section 86 | Which section? |
| AR-001 deadline | Section 36, 21 days | Section 190, 30 days | Which is correct? |
| DIR-001 filing | Section 92, 14 days | Section 115, 30 days | Which section + deadline? |
| AGM-006 minutes | Section 83 | Section 83 | Confirm |

## Documents to Review
- docs/LEGAL_BASIS_MATRIX.md — Full rule-to-statute mapping
- app/rule_engine/engine.py — Rule implementation with statutory_basis strings
- scripts/seed_rules.py — Seed data with rule definitions
- alembic/versions/0002_seed_ilrmf_rules.py — Original 30 rules
- alembic/versions/0015_add_extended_legal_rules.py — 10 extended rules
- alembic/versions/0013_add_bankruptcy_labour_rules.py — 6 bankruptcy/labour rules

## Reviewer
- Name: [TO BE ASSIGNED]
- Date: [TO BE SET]
- Sign-off: [ ] All 75 rule citations verified against primary sources
