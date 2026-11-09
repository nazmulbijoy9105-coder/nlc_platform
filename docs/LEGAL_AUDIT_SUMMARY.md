
> **Historical snapshot — superseded for current release status (10 November 2026).** The statement “Engineering / rule-parity: GO” is not a production-release approval. Current status is in [STATUS_AND_GAP_REGISTER_2026-11-10.md](STATUS_AND_GAP_REGISTER_2026-11-10.md). The current legal approval register has zero approved rule IDs; statutory scoring remains NOT RELEASED. Retain this file for audit history; do not rely on its historical verification counts as current approval.

# Legal Audit Summary – ILRMF Engine

**Date:** 2026-11-02  
**Branch / HEAD:** main @ 2ef5e99 (production-gate audit)  
**Rule corpus:** **85** ILRMF rules (Engine ↔ Seed parity confirmed)

## Current Status (Production Gate)

| Item | Status |
|------|--------|
| Engine rule count | 85 |
| Seed / DB seed parity | Pass (`tools/audit_rule_parity.py --no-db`, `scripts/check_rule_verification.py`) |
| Statutory basis present on flags/rules | Yes |
| Legal Basis Matrix | `docs/LEGAL_BASIS_MATRIX.md` |
| Audit artefacts | `legal_audit/` (multiple runs 2026-10-30) |
| Independent Bangladesh company-law lawyer review of full 85-rule corpus | **Still outstanding** (recommended before high-stakes production use) |

## Completed (historical + recent)

1. ANNUAL_RETURN_DEADLINE_DAYS corrected (Section 36 / Schedule X).
2. Statutory basis AR-001–004 updated away from obsolete Section 119.
3. seed_rules.py kept in lockstep with engine (now 85 = 85) on rule IDs; statutory text sync still required for DEF-001 / AUD-001 / REG-002.
4. NOT_EVALUATED risk band and coverage gating.
5. Multiple citation / deadline fixes (e.g. REG-002, AUD-001, AGM minutes Section 89).
6. Rule parity and verification gates wired into CI.
7. Score history append-only + hash-chain considerations for legal defensibility.
8. Disclaimer (“not legal advice”) on API responses.
9. DEF-001 engine logic uses Section 94 with structured grounds and evidence requirement (seed still stale — Section 297).
10. AUD-001 engine uses calendar-month semantics per Section 210(6).
11. REG-002 engine distinguishes internal registers (Sec 34/89/174) from RJSC filing (Sec 115).

## Remaining / Recommended

- Independent Bangladesh company-law counsel review of the **full 85-rule** corpus (statutory basis, deadlines, score impacts, BLACK override logic).
- Sync `scripts/seed_rules.py` statutory_basis / descriptions for DEF-001, AUD-001, REG-002 to match engine.
- Confirm AGM notice period decision (14 vs 21 clear days) against current practice.
- Peripheral modules (BSEC, Labour, Tax, FX, Banking) labelled or hardened as “screening only” where not core Companies Act 1994.
- Keep `LEGAL_RECONCILIATION_CHECKLIST.csv` and lawyer review pack updated after any rule change.

## Sign-off

Engineering / rule-parity: **GO** for production candidate.  
Legal / lawyer: **PENDING** independent review of 85-rule set.

---
*Previous summary (2026-09-29) referenced 75 rules; corpus has since expanded and been reconciled to 85.*
