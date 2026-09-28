# Legal Audit Summary – ILRMF Engine
Date: 2026-09-29
Branch: fix/legal-engine-audit-corrections

## Completed
1. ANNUAL_RETURN_DEADLINE_DAYS: 30 → 21 (Companies Act 1994, Section 36 – Schedule X)
2. Statutory basis AR-001–004: Section 119 → Section 36
3. seed_rules.py fully synced with engine (75 = 75)
4. All remaining Section 119 references removed
5. Legal Basis Matrix created (docs/LEGAL_BASIS_MATRIX.md)

## Remaining (not blocking merge of this branch)
- Independent Bangladesh company-law review of all 75 rules
- AGM notice period decision (14 vs 21 clear days)
- Hardening / labelling of peripheral modules (BSEC, Labour, Tax, FX, Banking)
