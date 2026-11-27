# RJSC authority evidence capture and legal verification protocol

**Status:** Working procedure — not a legal opinion, statutory interpretation, or approval.
**Register:** `NLC_RJSC_59_authority_evidence_register_2026-11-27.csv` (59-rule working register).
**Rule catalogue:** 85 canonical NLC rules. The 59-row authority register is a partial evidence workpaper, not a substitute for the full catalogue or scope register.

## 1. Non-negotiable status separation

The register records evidence collection, technical comparison, legal review, and counsel disposition as separate activities. A source URL, section excerpt, RJSC form, repository match, passing test, or reviewer note does not by itself establish that a rule is legally verified.

Until the required review is complete:
- Keep every unresolved rule at `NOT_VERIFIED`.
- Keep `exact_provision_verified` blank and `counsel_disposition_status` at `NOT_APPROVED`.
- Do not populate reviewer identity, enrolment, or review dates unless the named reviewer actually performed and recorded the review.
- Do not set a rule to `verified`, include it in `VERIFIED_RULE_IDS`, or treat it as legally approved merely because an official source was located.
- Keep product scoring/release gates independent of evidence-workpaper status.

## 2. Source hierarchy

For each rule, collect evidence in this order and record the exact source:
1. Official Gazette / promulgated Act / SRO / statutory instrument, including the relevant commencement or amendment notification.
2. Official consolidated statutory text published by the Government of Bangladesh (for navigation and cross-checking; retain the underlying Gazette evidence for amendments where available).
3. Official RJSC forms, notices, circulars, and filing instructions as administrative corroboration only. An administrative form does not amend an Act.
4. Other government sources only where they establish a specific factual point (for example, an official index of SROs). Record when the underlying instrument itself was not obtained.
5. Secondary commentary may identify issues or locate sources but must not be treated as primary authority.

A source URL is a locator, not an archived evidentiary copy.

## 3. Immutable source capture

For every relied-on source:
- Save the complete source document or a clearly delimited official extract, including title page, relevant provision, schedules, signature/seal and Gazette metadata where present.
- Record issuing authority, instrument number, enactment/publication date, commencement date, effective date, language, URL, access timestamp (Asia/Dhaka), and the precise pages/sections relied upon.
- Preserve the original downloaded bytes without editing. Store a separate OCR/text extraction if needed; never replace the original with OCR.
- Calculate SHA-256 over the exact archived bytes. Record filename, byte size, hash, capture operator, capture timestamp, and storage location in the evidence index.
- If a source is unavailable, record the attempted URL, date, failure, and next retrieval action. Do not substitute an unofficial mirror without marking it as secondary.
- Re-capture changed URLs or updated consolidated texts as new evidence versions. Never overwrite a prior capture.

Suggested evidence path: `docs/legal-evidence/rjsc/<rule_id>/<instrument-id>/<capture-date>/`. Keep sensitive personal information out of public repository evidence; redact only in a derivative copy and retain an access-controlled original where lawful.

## 4. Rule-level legal verification record

For each of the 59 rows, the reviewer must complete a separate determination covering:

### A. Identity and scope
- Exact rule ID, title, legal obligation, regulated entity, event trigger, filing/record-keeping duty, and intended consequence.
- Whether the duty is within RJSC/company-law scope or is a separate tax, labour, securities, banking, foreign-exchange, stamp, or other regime.
- Whether the recorded instrument and provision actually create the stated duty.
- Any overlap, duplication, or conflict with another rule.

### B. Exact provision
- Exact section, subsection, paragraph, schedule/article, proviso, explanation, and cross-reference.
- Quoted source text in the original language, with a faithful translation where required.
- Whether the provision is mandatory, conditional, discretionary, or subject to Articles, exemptions, thresholds, or Registrar/court action.
- Distinguish the legal obligation from NLC's operational interpretation and product policy.

### C. Temporal validity and amendments
- Enactment, publication, commencement, amendment, repeal, substitution, and transitional provisions.
- Every relevant amendment instrument and the exact provision it changes.
- Effective-from / effective-to dates at rule level, with evidence for each boundary.
- Whether the current consolidated text reflects all applicable amendments as of the review cut-off.
- Any unresolved Gazette, commencement, translation, or retrospective-effect question.

### D. Rule logic and evidence requirements
- Statutory trigger and the event date from which time runs.
- Calendar-day, working-day, calendar-month, or year computation as supported by the law; do not infer a statutory computation convention where the text is silent.
- Exceptions, extensions, cures, court/Registrar discretion, and evidential prerequisites.
- Distinguish statutory deadlines from internal NLC risk thresholds, grace periods, and RED/BLACK policy.
- State what evidence proves the facts and what evidence is insufficient.

### E. Technical mapping
- Compare the verified legal obligation with catalogue, seed, evaluator, persisted rule identity, scope registry, rescue disposition, and UI labels.
- Record exact repository commit and file/line references, engine version, and test IDs.
- Identify any difference between the statute and product behaviour. A code match is not legal validation; a legal determination does not prove implementation correctness.

## 5. Independent review and disposition

Each rule requires:
1. A first legal reviewer who records name, professional enrolment/qualification, date, source references, reasoning, and unresolved questions.
2. A second independent reviewer who checks the primary sources and first review, records their own identity and date, and either concurs or explains disagreement.
3. Counsel disposition by an authorised legal decision-maker: `APPROVED`, `REJECTED`, or `DEFERRED`, with reasons, scope, effective period, and signature/approval evidence.

No reviewer or counsel identity may be fabricated or inferred from a GitHub account. If independent review is not available, keep the rule pending. A technical maintainer cannot self-certify legal approval merely by merging a PR.

## 6. Discrepancy handling

Create a durable discrepancy record for each mismatch among:
- the uploaded authority register;
- the official statutory text and amendment instruments;
- the 85-rule canonical catalogue;
- evaluator implementation and tests;
- RJSC scope decisions; and
- persisted production rule identity.

Classify each discrepancy as source/identity, provision, amendment, scope, interpretation, temporal calculation, evidence, or implementation. Record owner, blocking status, affected rules, remediation, and closure evidence. Do not silently rewrite the register to match the code or the code to match an unreviewed register.

## 7. Release and scoring safeguards

- Evidence discovery and technical tests must not mutate legal approval fields.
- `pending_review` and unresolved identity conflicts remain non-scoreable where the existing release contract requires it.
- Keep RJSC obligations separate from non-RJSC obligations. An out-of-scope rule must not change RJSC score, risk band, rescue trigger, or release decision.
- Preserve fail-closed behaviour for missing facts, missing evidence, ambiguous dates, unresolved authority, and catalogue identity conflicts.
- Do not use statutory citations as a proxy for proof that a filing occurred.
- Do not describe a passing test suite as proof that a statutory interpretation is correct.

## 8. Current workpaper limitations (27 November 2026)

The 59-rule working register contains source-location and comparison observations, not completed legal verification. Its current controls intentionally leave all 59 rules `NOT_VERIFIED`; exact-provision verification is blank; reviewer and second-reviewer fields are blank; counsel disposition is `NOT_APPROVED`; amendment review remains `OPEN_NOT_EXHAUSTIVE`; and source archive hashes are blank.

The register therefore must not be presented as a verified authority schedule or used to authorise scoring/release. The next evidence tasks are to archive primary Gazette/Act/SRO copies, resolve the recorded provision and repository discrepancies, complete rule-level amendment histories, obtain independent legal reviews, and obtain explicit counsel dispositions.

## 9. Suggested acceptance checklist

- [ ] 59 rows retained; no silent deletion or renumbering.
- [ ] Every relied-on source has an immutable capture and SHA-256.
- [ ] Exact operative provision and original-language text recorded per rule.
- [ ] Commencement and amendment history evidenced, not assumed.
- [ ] Rule-level operative periods and transitional provisions reviewed.
- [ ] RJSC scope distinguished from other statutory regimes.
- [ ] Repository mapping and discrepancies recorded against a pinned commit.
- [ ] First and second independent legal reviews completed.
- [ ] Counsel disposition explicitly recorded for each rule.
- [ ] Technical tests demonstrate scope isolation, fail-closed handling, and no approval-state mutation.
- [ ] Release governance separately authorises any production scoring use.

**This protocol does not itself verify, approve, interpret, or release any rule.**
