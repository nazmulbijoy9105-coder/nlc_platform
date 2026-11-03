# NLC Legal Review — Pending Citation and Applicability Questions

## Purpose

This document records specific statutory citation, interpretation and
applicability questions for review by a Bangladesh-qualified corporate
lawyer. It is not a blanket certification that every other active rule is
legally verified. The canonical registry's RECONCILE/PENDING status remains
authoritative; no rule may enter VERIFIED_RULE_IDS without documented
independent counsel approval.

## Questions for Lawyer Review

### 0. AGM-005: AGM Quorum — Section 85(2)(b) and current Articles

**Current engine citation:** Section 85(2)(b), Companies Act 1994 (Bangladesh)

**Current implementation:** The evaluator requires verified current-Articles provenance, member-register evidence and attendance evidence. For a private company with no Articles variation, the statutory default is two members where total membership is up to six and three where it exceeds six. A verified Articles-specific quorum takes precedence. Missing or incomplete provenance produces UNKNOWN / NOT_EVALUATED with zero score impact.

**Counsel verification required:**
- Confirm the current official text and application of Section 85(2)(b), including the company-category and membership thresholds.
- Confirm the interaction between the statutory default and the company's current registered Articles, including amendments and any relevant meeting-specific provisions.
- Confirm the evidence needed to establish the total membership, members personally present, and the operative Articles.
- Confirm whether any additional statutory or Articles-based exception affects the calculation.

**Status:** PENDING. AGM-005 has been removed from VERIFIED_RULE_IDS; it may generate an informational finding only and must not affect the authoritative score until counsel approval.

### 1. AUD-001: First Auditor Appointment — Section 210(6)

**Current engine and canonical citation:** Section 210(6), Companies Act 1994 (Bangladesh)

**Current implementation:** The Board's first-auditor appointment date is compared with one calendar month from registration. This is calendar-month arithmetic, not a fixed 30-day interval. A Boolean appointment status without the effective appointment date is NOT_EVALUATED. Appointment-date evidence stored on Audit records is passed into the deterministic evaluator.

**Counsel verification required:**
- Confirm the authoritative text of Section 210(6), its effective version and that it imposes the first-auditor appointment duty on the Board.
- Confirm the statutory starting date is the date of registration and the correct calendar-month computation.
- Distinguish the Board's first-appointment duty under Section 210(6) from the auditor's separate Registrar-filing duty under Section 210(2).
- Confirm the evidence needed to establish the appointment resolution and its effective date.

**Status:** Implementation patched; statutory provenance remains RECONCILE and AUD-001 remains outside VERIFIED_RULE_IDS until counsel approval.
### 2. SH-001: Share Allotment Return — Section 151 vs Section 50

**Current engine citation:** Section 151, Companies Act 1994
**Current canonical citation:** Section 50, Companies Act 1994

**Question:** Which section governs the share allotment return filing
deadline (60 days)?

**Context from Act PDF:**
- S151 = "Return as to allotment" — "Where a company having a share
  capital makes any allotment of its shares, the company shall within
  sixty days thereafter, file with Registrar the following documents..."
- S50 = "Entries in register when share-warrant issued" — about share
  warrants, NOT allotment returns

**Engine's position:** Section 151 (Return as to allotment, 60-day deadline)
**Canonical's position:** Section 50 (Share warrant entries)

**Assessment:** The engine appears CORRECT — S151 is about allotment
returns with a 60-day filing deadline. S50 is about share warrant
register entries, which is a different concept entirely. However, the
canonical architecture was never updated.

**What needs verification:**
- Confirm that Section 151 is the correct provision for allotment returns
- Confirm the 60-day filing deadline
- Verify that Section 50 does NOT apply to allotment returns

**Impact:** SH-001 is currently NOT in `VERIFIED_RULE_IDS`. Once verified,
it should be added and the canonical updated from S50 → S151.

---

### 3. SH-002: Share Certificate Issuance — Section 158 vs Section 46

**Current engine citation:** Section 158, Companies Act 1994
**Current canonical citation:** Section 46, Companies Act 1994

**Question:** Which section governs the share certificate issuance
deadline (60 days / 2 months)?

**Context from Act PDF:**
- S158 = "Limitation of time for issue of certificates" — the PDF text
  is truncated but the title clearly relates to certificate issuance
  deadlines
- S46 = "Issue of share warrants to bearer" — about share warrants
  (bearer instruments), NOT share certificates

**Engine's position:** Section 158 (Limitation of time for issue of certificates)
**Canonical's position:** Section 46 (Issue of share warrants to bearer)

**Assessment:** The engine appears CORRECT — S158 is about certificate
issuance time limits. S46 is about share warrants, which are bearer
instruments — a different concept from registered share certificates.

**What needs verification:**
- Confirm that Section 158 is the correct provision for certificate issuance
- Confirm the 60-day (2 month) deadline
- Verify that Section 46 does NOT apply to share certificate issuance

**Impact:** SH-002 is currently NOT in `VERIFIED_RULE_IDS`. Once verified,
it should be added and the canonical updated from S46 → S158.

---

## Additional Items for Legal Review

### 4. AUD-002: Audit Not Completed Before AGM — Section 183

**Current engine citation and description:** Section 183, Companies Act 1994 (Bangladesh).

**Current implementation:** A pre-AGM warning is raised when the scheduled AGM is within the statutory notice window and verified audit-completion evidence is absent. The evaluator does not presume that AGM resolutions are automatically invalid.

**Counsel verification required:** Confirm the applicable Section 183 duties, required accounts and evidence, and the proper interaction with the AGM timetable.

**Status:** Engine, seed and canonical citation/trigger are aligned on the review branch. Independent counsel verification remains pending.

### 5. AUD-003: AGM Held Without Completed Audit — Case-Specific Legal Review

**Current engine/canonical candidate basis:** Sections 183 and 210, Companies Act 1994 (Bangladesh).

**Current implementation:** A verified record that an AGM was held without a completed audit creates a NOT_EVALUATED / REQUIRES_LAWYER_JUDGMENT finding with zero score impact. The engine does not presume that the AGM or its resolutions are automatically invalid and does not trigger BLACK or Corporate Rescue solely from this fact.

**Counsel verification required:**
- Confirm the applicable duties under Sections 183 and 210 for the relevant company, accounts and auditor facts.
- Determine whether any specific statutory consequence follows from the actual meeting record and accounts.
- Confirm whether additional provisions, Articles or case-specific facts change the analysis.

**Status:** PENDING. AUD-003 is not a BLACK override and is excluded from authoritative scoring until counsel approves a precise, testable legal proposition.

### 6. Deadline Constants

The following deadline constants in the engine need verification against
the current gazetted Act text:

| Constant | Engine value | Act PDF section | Status |
|---|---|---|---|
| `FIRST_AGM_DEADLINE_DAYS` | 548 (18 months) | S81 | ✅ Verified |
| `SUBSEQUENT_AGM_DEADLINE_DAYS` | 456 (15 months) | S81 | ✅ Verified |
| `REGISTERED_OFFICE_DEADLINE_DAYS` | 28 | S77(2) | ✅ Verified |
| `CHARGE_REGISTRATION_DEADLINE_DAYS` | 21 | S159(1) | ⚠️ Needs verification |
| `SHARE_CERTIFICATE_DEADLINE_DAYS` | 90 | S158 | ⚠️ Needs verification |
| `SPECIAL_RESOLUTION_DEADLINE_DAYS` | 15 | S88 | ⚠️ Needs verification |
| AUD-001 deadline | One calendar month | S210(6) | ⚠️ Counsel source verification pending |
| `ANNUAL_RETURN_DEADLINE_DAYS` | 21 | S36 | ✅ Verified |

---

## Summary

| # | Rule | Question | Impact if wrong |
|---|---|---|---|
| 1 | AUD-001 | Confirm the authoritative text and application of Section 210(6): Board appointment within one calendar month of registration, calculated by calendar month. | Evaluator now requires appointment-date evidence; counsel approval remains pending |
| 2 | SH-001 | S151 vs S50 for allotment returns? | Allotment check disabled |
| 3 | SH-002 | S158 vs S46 for certificate issuance? | Certificate check disabled |
| 4 | AUD-002 | Description says S151, should be S183? | Description text mismatch |
| 5 | AUD-003 | S151 included — correct for audit? | May need section update |
| 6 | Deadlines | 4 constants need verification | Score accuracy affected |

The listed rules remain outside the authoritative score unless and until their individual verification status and allowlist membership are approved. AGM-005 is explicitly excluded pending counsel review. They generate flags but
do not lower the score. Once a lawyer verifies the correct citations,
the rules can be added to `VERIFIED_RULE_IDS` and begin contributing to
the authoritative compliance score.

---

## Lawyer Review Process

1. Review each question against the current gazetted Companies Act 1994
   (Bangladesh), including any 2020 or 2026 amendments
2. For each question, provide:
   - The correct section number and subsection
   - The correct deadline (if applicable)
   - Whether the engine's current citation is correct
   - Any exceptions or conditions that modify the rule
3. Sign off on the verified rules using the `verification_status` field
   in the `legal_rules` database table (set to `VERIFIED`)
4. Once verified, add the rule ID to `VERIFIED_RULE_IDS` in
   `app/rule_engine/engine.py`

---

*Generated by NLC Platform Audit — 30 October 2026*
*Source: Companies Act 1994 (Bangladesh), 2008 text, 402 sections*
