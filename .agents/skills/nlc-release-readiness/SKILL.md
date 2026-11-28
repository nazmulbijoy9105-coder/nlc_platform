---
name: nlc-release-readiness
description: Conduct evidence-based technical, legal-governance, security and operational release checks for NLC. Use before enabling statutory scoring, publishing compliance scores, deploying or changing legal rule behavior.
---

# NLC release readiness

## Objective
Determine whether a specific commit and runtime are safe to release for a precisely defined capability. Passing CI alone is insufficient.

## Required scope
Commit SHA; deployment environment; database identity and migration head; enabled product capabilities; legal rule release state; tenant/security boundaries; integrations; rollback plan.

## Gates
1. **Build and tests:** reproducible commands, results, coverage and known failures.
2. **Runtime identity:** deployed commit, health, environment, database/project/branch identity and migration state.
3. **Security:** authentication/authorization, tenant isolation, RLS, secrets, rate limits, audit logging and negative tests.
4. **Data integrity:** migrations, backup/restore rehearsal, constraints, idempotency and historical records.
5. **Legal governance:** source mapping, applicability, effective dates, exceptions, counsel approval and versioned release decision.
6. **Scoring semantics:** unknown facts remain unknown; no unsupported deductions; score explanation and reproducibility.
7. **Reports and APIs:** tenant-scoped data, consistent score basis, disclosures and export parity.
8. **Operations:** monitoring, alerts, incident response, rollback and operator runbook.

## Verdict
Use PASS, FAIL, BLOCKED or NOT_TESTED per gate. State exact evidence and tested commit. Distinguish capability-specific release from whole-product readiness. Do not infer production readiness from a green CI badge.

## Hard stops
No statutory scoring release without an explicit, auditable legal governance decision. No production write or destructive migration during an audit. No fabricated runtime evidence. Unresolved P0 security, data-integrity or legal-basis defects block the affected capability.
