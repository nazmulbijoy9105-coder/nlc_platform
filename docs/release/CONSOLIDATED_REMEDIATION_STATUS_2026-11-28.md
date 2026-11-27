# Consolidated release remediation — 28 November 2026

**Repository:** `nazmulbijoy9105-coder/nlc_platform`  
**Inspected main baseline:** `6ecef366122868f7cf49a451ddc99be2cfcded49`  
**Branch:** `fix/consolidated-release-remediation-20261128`  
**Disposition:** Draft remediation. No production database, Render service, score-release setting, legal approval register, or `VERIFIED_RULE_IDS` were changed.

This document distinguishes observed CI evidence from unresolved implementation work. A passing integration job is not a substitute for a passing unit suite, a legal review, or a production parity check.

## Remediation matrix

| Workstream | Observed blocker | Required remediation / acceptance evidence | Status |
|---|---|---|---|
| AGM-001 / #441 | Unit test `test_first_agm_date_requires_source_reviewer_and_verification_time` fails because subsequent-deadline components are `None` for a fixture with incomplete AGM-history provenance. | Correct the fixture only if the underlying history is genuinely complete; otherwise keep UNKNOWN. Add paired positive and negative tests proving a complete history passes and incomplete history remains unevaluated. Re-run the complete unit suite. | OPEN |
| Court-order evidence / #441 | Review findings identify missing structured CompanyFact intake, expiry of still-operative order evidence, missing order facts in rescue evaluation, numeric score leakage, dropped review flags, reviewer qualification gaps, and insufficient order-specific decision binding. | Validate structured facts at ingestion; preserve operative order blocking until status is verified; make rescue and compliance share the same verified facts; withhold both numeric score and band; persist canonical rule basis; bind counsel identity, decision and effective period to the specific order. Add endpoint, persistence and rescue integration tests. | OPEN |
| AGM history / #441 | Review findings identify unbound first-AGM date overlays, duplicate meeting inflation and unrecognized AGM types being silently excluded. | Derive dates from a unique, verified AGM event; enforce company/year uniqueness transactionally; reject unknown types at writes and make history UNKNOWN on legacy unknown types. Add concurrency and provenance tests. | OPEN |
| Snapshot provenance / #441 | Review finding reports catalogue rule version being persisted as evaluator version. | Persist evaluator version from the evaluation output; persist catalogue version separately; add snapshot round-trip assertions. | OPEN |
| Source register / #441 | Markdown candidate sources and JSON workpack are not synchronised for BSEC-001–004. | Synchronise candidate anchors and all inventory counts; add deterministic Markdown/JSON parity test. Keep all 85 rules NOT_VALIDATED until primary sources are captured, hashed and independently reviewed. | OPEN |
| First-AGM fallback / #448 | Mypy reports `app/rule_engine/engine.py:1619: Incompatible types in assignment (date | None -> date)`. | Use an explicitly nullable local for the selected AGM date, narrow it before date arithmetic, and retain UNKNOWN when no verified event date exists. Add mypy and deadline boundary tests. | OPEN |
| Workflow YAML / #442 | Existing structure check can accept duplicate mapping keys or a non-mapping `jobs` value. | Strictly reject duplicate YAML keys and require a non-empty top-level jobs mapping. This branch adds the validator and tests; GitHub Actions must pass it on the PR head. | PATCHED IN THIS BRANCH; CI PENDING |
| Migration rehearsal / #442 | Neon rehearsal job failed on the inspected head. | Keep G2 checks on isolated PostgreSQL; use Neon only for a separately approved production rehearsal. Capture the exact failing step output and prove migration target identity, forward-only upgrade and cleanup. | OPEN |
| G2 / #444 | Isolated PostgreSQL integration checks passed, but unit tests failed on the inspected head. | Fix the specific unit failures, rerun all jobs, and require zero skipped mandatory checks. | OPEN |
| Dependency security / #436 | PyPI and OSV scans passed; resolved-version verification failed. Dependency license policy also failed. | Inspect the uploaded audit evidence; correct the resolver/version assertion without suppressing advisories. Review each dependency license against an explicit approved policy; unresolved items remain OPEN. | OPEN |

## Exact CI observations

- PR #441 head: `8f74067d7a4a599f2ba6ceb2c6d66aa4363a6a0f`; unit failure at `tests/unit/test_agm_first_event_provenance.py:77`. Integration tests, lint and Docker runtime smoke passed on that run.
- PR #448 head: `26e0996629410781715d589a2aede5d4fb493b9f`; mypy failed at `engine.py:1619`. Integration tests, lint and Docker runtime smoke passed on that run.
- PR #436 head: `c3afc4d03d6ab0a5e3c494ded5da208b8c42543a`; PyPI and OSV audit commands passed; the resolved-version verification step failed. License-policy workflow also failed.
- PR #442 head: `b7496615481e858b83efe07ea1d048f8921b306c`; Neon migration rehearsal failed. Its workflow parser check also needs duplicate-key and mapping-type enforcement.
- PR #444 head: `7e8e6f96ac9a9a5ac527179099877036c40e3190`; isolated PostgreSQL integration, lint and Docker runtime smoke passed; unit tests failed.

These are historical run results for the stated SHAs, not fresh results for this branch or current main.

## Legal and scoring release controls

1. No candidate source, AI review, code review, migration, or passing test is represented as Bangladesh-qualified counsel approval.
2. Keep the 85-rule source-validation register at NOT_VALIDATED until each primary source and applicable amendment is captured, hashed, mapped to the exact proposition and independently reviewed.
3. Keep `VERIFIED_RULE_IDS` and the legal approval register unchanged.
4. Keep `LEGAL_SCORE_RELEASED` closed unless a separately authorized release decision exists.
5. An unresolved court order, disputed date, unknown AGM type or conflicting evidence must not be converted into a breach, waiver, BLACK override, rescue entitlement, or published numeric score by inference.
6. RJSC scoring remains limited to the versioned RJSC scope. Out-of-scope obligations must not influence an RJSC result.

## Verification required before merge

- [ ] Current-main rebase/synchronization completed without dropping main-only commits.
- [ ] Workflow YAML validator unit tests pass.
- [ ] All 85 catalogue identities and RJSC scope injection tests pass.
- [ ] AGM event provenance, duplicate-cycle, unknown-type and deadline boundary tests pass.
- [ ] Court-order endpoint, status freshness, rescue-path and score-withholding tests pass.
- [ ] Finding snapshots preserve both evaluator and catalogue versions distinctly.
- [ ] Markdown/JSON source inventory parity passes.
- [ ] Dependency vulnerability and license-policy checks pass without policy weakening.
- [ ] Full CI passes on the exact proposed merge SHA.
- [ ] Independent legal review remains separately documented.

**Current conclusion:** this branch contributes a concrete workflow-YAML hardening patch and regression tests. It does not claim to close the AGM/court-order, migration, dependency, G2, legal-source or production-release blockers. No production release is authorized by this report.
