# NLC Legal Review — Pending Citation Questions

## Purpose

This document lists the 3 remaining statutory citation questions that
require verification by a Bangladesh-qualified corporate lawyer. All
other 82 rules have been verified against the Companies Act 1994
(Bangladesh) PDF (402 sections, 90 pages, 2008 text).

## Questions for Lawyer Review

### 1. AUD-001: First Auditor Appointment — Section 210(6) vs 210(1)

**Current engine citation:** Section 210(6), Companies Act 1994
**Canonical citation:** Section 210(1), Companies Act 1994

**Question:** Which subsection of Section 210 governs the first auditor
appointment deadline (30 days from incorporation)?

**Context from Act PDF:**
- S210 = "Appointment and remuneration of auditors"
- S210(1): "Every company shall, at each annual general meeting, appoint
  an auditor or auditors to hold office from the conclusion of that
  meeting until the conclusion of the next annual general meeting..."
- The PDF text for S210 is truncated — subsections beyond (1) are not
  visible in the machine-extracted text

**What the engine checks:** First auditor not appointed within 30 days
(1 month) of incorporation. The engine uses `Section 210(6)` as the
statutory basis, implying a subsection (6) exists about first auditor
appointment by the Board within 30 days.

**What needs verification:**
- Does Section 210(6) exist in the Companies Act 1994?
- If so, does it specify a 30-day deadline for first auditor appointment?
- If not, which subsection governs this deadline?
- Is the 30-day (1 month) deadline correct?

**Impact:** AUD-001 is currently NOT in `VERIFIED_RULE_IDS` — it generates
flags but does not affect the compliance score. Once verified, it should
be added to the verified set.

---

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

### 4. AUD-002: Audit Not Completed Before AGM — Section 183 vs Section 151

**Current engine citation:** Section 183
**Engine description text:** "Section 151: AGM procedurally defective"

**Issue:** The statutory_basis says Section 183 (Annual balance sheet)
but the description text says "Section 151". S151 = Return as to
allotment (wrong concept). The description text should say "Section 183".

**Status:** Description text mismatch — basis is likely correct.
**Fix needed:** Update description text from "Section 151" to "Section 183".

### 5. AUD-003: AGM Held Without Completed Audit — Sections 151, 210

**Current engine citation:** Sections 151, 210

**Issue:** S151 = Return as to allotment (wrong concept for audit at AGM).
The correct sections are likely S183 (Annual balance sheet) and S210
(Appointment and remuneration of auditors).

**Status:** Needs verification — S151 may be incorrect.

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
| `FIRST_AUDITOR_DEADLINE_DAYS` | 30 | S210(6)? | ⚠️ Needs verification |
| `ANNUAL_RETURN_DEADLINE_DAYS` | 21 | S36 | ✅ Verified |

---

## Summary

| # | Rule | Question | Impact if wrong |
|---|---|---|---|
| 1 | AUD-001 | Does S210(6) exist? 30-day deadline? | First auditor check disabled |
| 2 | SH-001 | S151 vs S50 for allotment returns? | Allotment check disabled |
| 3 | SH-002 | S158 vs S46 for certificate issuance? | Certificate check disabled |
| 4 | AUD-002 | Description says S151, should be S183? | Description text mismatch |
| 5 | AUD-003 | S151 included — correct for audit? | May need section update |
| 6 | Deadlines | 4 constants need verification | Score accuracy affected |

All 5 items above are currently excluded from the authoritative compliance
score via the `VERIFIED_RULE_IDS` production gate. They generate flags but
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
