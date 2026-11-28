# AGM branch validation — 28 November 2026

**Branch:** `fix/agm-first-event-deadline-provenance-20261128`  
**PR:** #448 (draft; based on `test/agm001-deterministic-deadlines-20261127`)  
**Purpose:** record the AGM evidence, rescue, publication, snapshot-version and legal-source checks.  
**Release status:** NOT APPROVED. This is an engineering validation record, not a legal opinion or release authorization.

## Changes made on this branch

1. **Structured CompanyFact intake**
   - The existing document-backed CompanyFact endpoint now has a dedicated typed path for `agm_court_order_evidence` and `agm_court_order_lawyer_decision`.
   - Court-order authentication fields cannot be self-asserted at intake; the fact remains unverified until a separate reviewer verifies it.
   - Verification requires a non-UNKNOWN operative status and rejects verification by the source-document uploader.
   - Lawyer-decision verification requires the verifying user to be the separately recorded qualification verifier, distinct from the lawyer decision-maker.
   - The generic user-asserted/scalar fact path remains unable to accept structured reviewer/system fields.

2. **Operative-order freshness**
   - `agm_court_order_evidence` has a 30-day freshness window for the operative-status check.
   - The observation date is reset to the Bangladesh business date when the independent reviewer verifies the order status. The court order itself does not automatically expire; the current status check must be refreshed.
   - `APPEALED`, `STAYED`, and `SUPERSEDED` states continue to require a reference and remain routed through lawyer review; no order grants automatic compliance or score uplift.

3. **Rescue-path consistency**
   - Manual rescue evaluation now overlays the latest non-rejected CompanyFact versions onto the same CompanyProfile fields as ordinary compliance evaluation.
   - It supplies `verified_fact_keys` and `verified_fact_context` from fresh, authorized-document-backed, independently verified facts before evaluating the rescue sequence.
   - The rescue route continues to bind the exact active catalogue and block unresolved catalogue identity conflicts.

4. **AGM history and deadline anchor**
   - A verified AGM-history record's `last_agm_date` is accepted as the subsequent-AGM anchor even when the separate first-event fields are absent.
   - An unverified first date without a verified history remains UNKNOWN / NOT_EVALUATED; it is not promoted into a statutory event.
   - The history summary no longer crashes on legacy in-memory records that omit `financial_year`; duplicate persisted financial-year cycles remain a fail-closed condition.

5. **Score withholding and snapshot version**
   - Existing persistence controls continue to store a null score, `NOT_EVALUATED` risk band and `NOT_RELEASED` status when the release gate is closed, evidence is insufficient, or score-blocking catalogue conflicts exist.
   - Rescue-plan score and risk-band fields remain null / `NOT_EVALUATED` when the evaluation score is withheld.
   - Withheld per-run snapshots now retain `engine_version`, `rjsc_scope_version`, `scoring_spec_version`, and `ilrmf_version` alongside the withheld status/reason. These fields are part of the hashed `score_breakdown_snapshot`.

## Snapshot-version validation

The per-evaluation `ComplianceEvaluationRun` is the authoritative immutable run record. It stores the engine version, score hash, rule-outcome hash/snapshot, fact-provenance snapshot and score-breakdown snapshot. Released snapshots already carry engine, RJSC scope, scoring-spec and ILRMF versions. The withheld-snapshot branch previously omitted those version identifiers; that gap is corrected above.

**Remaining limitation:** monthly `ComplianceScoreHistory` stores `engine_version` but does not have dedicated columns for RJSC scope, scoring-spec, ILRMF or catalogue snapshot version. The per-run record is version-complete, but a standalone monthly-history export cannot independently identify all those versions without joining to the authoritative per-run record. Decide whether that is acceptable for the product contract; if not, add a forward-only migration and extend the monthly-history hash/validator rather than silently changing existing hashes.

## Legal-source parity validation — AGM-001 / AGM-002

- The runtime engine and `scripts/seed_rules.py` both use the candidate citation **Section 81(1), Companies Act 1994 (Bangladesh)** and the same 18-calendar-month / calendar-year / 15-month / Registrar-extension propositions.
- `canonical_architecture/statutory_rules.py` also records Section 81(1) for both rules, with `ProvisionStatus.RECONCILE`, `NOT_EVALUATED`, zero score impact and documentary evidence required.
- The legal basis matrix now records the same subsection citation, explicitly labelled as a candidate and not counsel-approved.
- The official Laws of Bangladesh text currently published for the Act states the annual Gregorian-calendar-year requirement, the maximum 15-month interval, the first-AGM 18-month proviso (including the incorporation-year / following-year relief), and the Registrar extension limit/application window. This supports the text-level comparison, not a complete legal opinion or rule approval.

**Open legal-source blockers:**
- The rule workpack records no independently counsel-approved rules and marks amendment chronology / operative intervals unresolved.
- The exceptions register is not exhaustive; the rule's first-AGM proviso and Registrar extension are represented in the candidate requirement, but a full counsel-reviewed exceptions/relief matrix is still required.
- Confirm the exact current English translation against the official Bengali text and the complete Gazette/amendment/commencement/savings chain.
- Confirm company-class applicability and whether any special class-specific provisions or relief alter the general rule.
- Obtain a dated, signed, independent Bangladesh-qualified counsel disposition for AGM-001 and AGM-002. No automated test substitutes for this review.

## CI evidence and release boundary

The prior CI run on `ca1d292c0217500b889399e240f562a4bbebf596` passed legal engine assurance and security-closure structure, but general CI failed in unit tests. The failures exposed:
- a legacy test-fixture compatibility error in AGM history summary (fixed);
- a verified-history / first-event precedence bug that incorrectly emitted an AGM-002 UNKNOWN finding despite a verified `last_agm_date` (fixed).

The next full CI and legal-assurance runs must pass on the final branch head after these changes. Do not treat a queued run or a pass on an earlier SHA as validation of a later commit.

**No production migration, deployment, legal approval, scoring allowlist promotion, or score-release gate change is authorized by this document.** Keep PR #448 and consolidated PR #449 in draft until exact-head checks and independent legal review are complete.


## Exact-head CI follow-up — 28 November 2026

Latest reviewed branch head: `2db774108a3058d1ccb82ae13c7c6cd2d2435fcb`.

GitHub created these pull-request workflow runs for that exact head:
- CI: `46129625976` and `46129624876`
- Legal engine assurance: `46129625970` and `46129624885`
- Security closure structure: `46129626042` and `46129624907`

At the time of this update, every job in these runs remains **QUEUED**. No result is claimed for unit tests, integration tests, lint, Docker runtime smoke, catalogue parity, scope isolation, withheld publication, provenance integrity, or closure structure. The combined commit-status endpoint returned no status entries. A queued run is not a pass.

The exact-head checks must finish before this branch can be considered technically validated. If GitHub Actions remains queued, investigate runner availability/queue health; do not bypass required checks or infer success from the earlier SHA.

## Integration-test failure and targeted correction — 28 November 2026

The queued CI run later completed on code head `2db774108a3058d1ccb82ae13c7c6cd2d2435fcb`. Its integration suite had one failure: `TestCompanies.test_manual_evaluation_and_customer_views_withhold_unreleased_score` still asserted the pre-versioned withheld-snapshot shape. The implementation now correctly includes `engine_version`, `rjsc_scope_version`, `scoring_spec_version` and `ilrmf_version`; the stale test assertion has been updated to require those fields.

- Test-only correction commit: `b09af2494241fc8a66014700be6d2c73e38a0318`.
- The other completed checks on the prior code head passed: lint, unit tests, Docker runtime smoke, RJSC scope isolation, legal-rule catalogue parity, fail-closed publication, score-provenance integrity and security-closure structure.
- The `legal-engine-p0` job remained queued at last inspection.
- No workflow run or combined status was yet returned for `b09af2494241fc8a66014700be6d2c73e38a0318`. The correction is therefore **not yet re-tested** and must not be described as passing.

The expected versioned withheld-snapshot metadata is now part of the integration contract. Keep the release gate closed; do not change the legal allowlist or production state to make this test pass.

## Second withheld-snapshot assertion correction — 28 November 2026

A subsequent integration run exposed the same stale six-field expectation in `tests/integration/test_services.py::TestComplianceService::test_evaluate_company_full_pipeline`. The test fixture supplies `test-engine-v1` and `test-ilrmf-v1`; the assertion now checks those fixture values plus the canonical RJSC scope and scoring-spec versions.

- Test correction commit: `858a5f0cd57d26b356a9f1189d2e41e18d8442f9`.
- Follow-up import correction: `199534f99f41e960c909d0f630f9b5f59d83ecdb`; the RJSC scope version is imported from its canonical registry module, not from the service module's function-local namespace.
- Exact-head CI for the latest correction has not yet reported a run at the time of this update. This is a test expectation update only; no score-release setting or production control was changed.
