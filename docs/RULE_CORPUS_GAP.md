
> **Historical snapshot — superseded (10 November 2026).** The September 2026 75-engine/46-seed gap is not the current catalogue status. The latest recorded comparison is 85 engine / 85 seed / 85 API / 75 production DB; see [STATUS_AND_GAP_REGISTER_2026-11-10.md](STATUS_AND_GAP_REGISTER_2026-11-10.md). Do not use the old 29-rule gap as a current task list.

# Rule Corpus Gap Report
Date: 2026-09-29
Branch: fix/legal-engine-audit-corrections

## Summary
- engine.py active flags : 75
- seed_rules.py entries  : 46
- Gap                    : 29 rules exist only in the live engine

## Rules present only in engine.py
AGM-007, AUD-005, BNK-001, BNK-002, BNK-003,
BSEC-001, BSEC-002, BSEC-003, BSEC-004,
CHG-001, DEF-001, DEF-002, DIR-005, DIR-006,
ESC-004, ESC-005, FX-001, LBR-001, LBR-002, LBR-003,
STR-001, STR-002, STR-003, TAX-003, TAX-004,
TL-001, TL-002, VAT-002, VAT-003

## Action Required
These rules are executed by the engine but are not yet registered in the seed / database layer.
Next task: extract metadata from engine.py and add them to scripts/seed_rules.py
so that the rules API and admin UI stay in sync.
