# NLC controlled statutory release plan

**Status:** IN PROGRESS — ALL CUSTOMER-FACING STATUTORY GATES CLOSED  
**Date:** 2026-11-10  
**Related attestation:** `docs/legal/attestations/NLC-LA-2026-11-10-001.md`

## Governing principle

The reviewer self-attestation is recorded as an assertion by Md. Nazmul Islam, Advocate, Supreme Court of Bangladesh. The platform must not represent it as an independent review, cryptographic signature, or verification of identity. It is a reviewer-authority record, not a blanket switch that makes unimplemented legal logic safe.

## Workstreams and release criteria

### A. Rule scoring (86 rule records)

- [ ] For every rule ID, record exact primary legal source, instrument, section/rule/form, amendment(s), official publication/source URL or archive reference, and effective-from/effective-to dates.
- [ ] Record jurisdiction, entity/taxpayer scope, applicability predicates, exclusions, exceptions, grace periods, extensions and transitional provisions.
- [ ] Define required facts and admissible evidence; distinguish UNKNOWN, DISPUTED, NOT_APPLICABLE, REQUIRES_LAWYER_JUDGMENT and VERIFIED_ABSENT.
- [ ] Record the named reviewer disposition per rule and link it to the attestation record; no bulk approval by implication.
- [ ] Add rule-specific tests for positive, negative, boundary, exception, missing-evidence and effective-date cases.
- [ ] Generate an immutable versioned approval manifest and verify exact parity against engine, seed and API registries.
- [ ] Keep score impact zero and release allowlist empty for any incomplete, disputed or expired rule.

### B. Legal calendar and deadlines

- [ ] Create a versioned event catalogue with the statutory trigger, responsible person, applicability, exact source, effective dates and computation convention.
- [ ] Implement date calculations with company-specific facts, clear-day rules, holidays/closures, extensions, weekends, leap years, financial-year boundaries and transitional law where applicable.
- [ ] Store source/version and trigger evidence with every generated event.
- [ ] Do not generate a statutory deadline when trigger facts or legal applicability are UNKNOWN or DISPUTED.
- [ ] Implement regression tests for each event type and boundary case.
- [ ] Penalties remain disabled until amount/range, liable person, trigger, cap, temporal version and scope are separately verified and tested.

### C. Rescue release

- [ ] Rescue eligibility must consume only released, evidence-supported findings.
- [ ] Define permitted actions, prohibited automatic actions, human approval points, company/role scope and idempotency.
- [ ] No rescue plan, task, engagement, filing, notification or BLACK override may be created solely from provisional or UNKNOWN data.
- [ ] Test direct service calls, API routes, background jobs, replay, retries, stale evidence and tenant isolation.
- [ ] Human review and explicit customer authorization remain required for external/legal acts.

### D. Technical release controls

- [ ] Keep all three production gates closed until A, B and C are complete.
- [ ] Require a versioned manifest hash, migration rehearsal, rollback/forward-fix plan, audit event and post-deploy read-only verification.
- [ ] CI must assert that incomplete or expired approvals fail closed.
- [ ] Verify scoring, calendar, penalty, rescue, notifications and dashboards independently.
- [ ] Deploy only after the release candidate passes CI and a separately authorized production change window.

## Current verified state

- Approval register: `approved_rule_ids: []`.
- Production database (Neon, branch `br-purple-fog-aodj8s04`, database `neondb`): 86 legal rule rows, all `PENDING`, `NOT_EVALUATED`, score impact 0, no BLACK override.
- Engine: `VERIFIED_RULE_IDS = frozenset()`; `LEGAL_SCORE_RELEASED = False`.
- Calendar: `LEGAL_CALENDAR_RELEASED = False`; event and penalty allowlists empty; generator currently returns no statutory events.
- Rescue service: rejects plan generation while scoring is unreleased.
- Therefore this plan does not authorize production activation. It establishes the controlled work needed before activation can be considered.

## Acceptance boundary

A successful CI run proves implementation and regression behavior only. It does not prove that a statutory proposition is legally correct. Production activation requires a completed source-level manifest, reviewer dispositions, implementation, tests, migration rehearsal and explicit release authorization recorded against the exact release commit.
