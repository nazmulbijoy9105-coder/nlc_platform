# NLC technical release acceptance matrix — 10 November 2026

## Purpose and release boundary

This document tracks the technical implementation of scoring interfaces, compliance reports, rescue workflows, dashboard integration, audit evidence and release controls. It does not approve any Bangladesh legal rule, enable statutory scoring, certify a company, or authorize a production migration or deployment.

The production-facing legal release remains fail-closed until the independently approved rule corpus and release evidence are present. The technical work must remain useful in evidence-review mode without presenting provisional engine output as a legal conclusion.

## Component matrix

| Component | Current implementation | Technical acceptance evidence | Release condition |
|---|---|---|---|
| Rule evaluation and scoring | `app/rule_engine/engine.py`; `app/services/compliance_service.py` | Rule applicability/evidence states, global release switch, exact rule allowlist, category caps, BLACK override allowlist, deterministic evaluation snapshots | Never score a rule outside the approved allowlist; unknown or missing evidence is not a violation |
| Score API and history | `app/api/companies.py`; `ComplianceService.get_score_history` | API serializers redact score/risk fields when unreleased; score history preserves null / NOT_EVALUATED semantics | No cached legacy score or risk band may leak while release is closed |
| PDF reports | `app/services/pdf_report_service.py`; `tests/unit/test_pdf_report_service.py`; `tests/unit/test_report_reconciliation.py` | Endpoint and HTML-builder release checks; snapshot-to-company reconciliation; engine version and score hash; escaped content and restricted asset loading; renderer smoke tests | Score-bearing PDF only when release is active and the latest evaluation snapshot reconciles exactly |
| Rescue lifecycle | `app/api/rescue.py`; `app/services/rescue_service.py`; `tests/unit/test_rescue_engagement_contract.py`; `tests/unit/test_rescue_lifecycle_coverage.py` | Creation, retrieval, update and engagement routes check legal release; service layer independently checks release; active-plan deduplication; tenant and entitlement checks; rescue audit log | No RED/BLACK legal rescue workflow from unreleased or unapproved findings |
| Dashboard | `app/services/compliance_service.py:get_dashboard_kpis`; `app/api/companies.py`; frontend PR #51 | Evidence-review mode avoids legal risk aggregates; assigned-staff scoping tests; frontend distinguishes legal hold from ordinary service error | Switch to statutory risk dashboard only when the global gate and approved rule corpus are both valid |
| Audit trail | `ComplianceEvaluationRun`, `ComplianceScoreHistory`, `rescue_audit_log`, activity logs | Per-evaluation hash and previous-hash linkage; immutable snapshot of flags and score breakdown; actor-attributed rescue actions; hash-chain tests | Report and rescue actions must point to one completed evaluation snapshot, actor and engine version |
| Notifications and deadlines | Notification service, worker filters, calendar release gate | Unapproved rule alerts are suppressed; deadline/calendar API is separately gated | Do not send statutory alerts or expose deadlines from unapproved rules |
| Runtime and data integrity | Alembic migrations, PostgreSQL RLS integration suite, Docker runtime smoke | Single-head/fresh-upgrade tests, tenant-isolation tests, unique active-flag constraint, runtime image checks | Production migration requires backup/restore proof, role preflight, exact target DB verification and approved deployment window |

## Additional regression coverage in this change

- The PostgreSQL API integration suite now checks that existing rescue-plan detail reads, step mutations and engagement creation all return the legal-release hold while release is closed.
- Existing coverage already checks rescue creation, active-plan retrieval and portfolio listing under the closed gate.
- PDF tests cover closed-gate withholding, stale-data suppression, score/snapshot mismatch and missing authoritative snapshots.
- Dashboard tests cover evidence-review mode and legal-staff assignment scope.
- Hash-chain tests cover score and risk-band tampering.

## Release invariants

1. `LEGAL_SCORE_RELEASED` remains false unless the complete release policy is satisfied.
2. `VERIFIED_RULE_IDS` remains empty until each rule has a documented independent legal disposition.
3. `LEGAL_CALENDAR_RELEASED` remains false until the calendar rule corpus is validated.
4. A candidate severity or internal review signal must not become a customer-facing RED/BLACK legal classification.
5. Missing evidence is UNKNOWN, not proof of absence.
6. PDF generation must fail closed on missing, stale, malformed or mismatched evaluation snapshots.
7. Rescue plan creation, read, update, reevaluation and commercial engagement routes must all enforce the same legal release boundary.
8. Every score-bearing output must be traceable to its evaluation ID, engine version, snapshot hash, timestamp and company.
9. No production data, schema, credentials, environment variables, or deployment state is changed by this technical-readiness branch.

## Production rollout blockers to resolve separately

- Reconfirm the exact production database used by Render; do not assume the Neon rehearsal branch is the live target.
- Complete a restorable production backup and restore rehearsal.
- Resolve the database-role membership and credential preflight findings through an authorized DBA; do not weaken migration preflight.
- Verify the complete migration chain through revision `0089_unique_active_compliance_flags` against the exact production-derived rehearsal database.
- Provision and verify dedicated worker/Beat services and broker credentials before enabling background jobs.
- Confirm the frontend dashboard legal-hold changes are merged and tested on the current mainline.
- Obtain the required independent legal validation before changing any legal release gate.

## CI acceptance commands

```bash
python -m pytest tests/unit -q
python -m pytest tests/integration -q --tb=short
python -m mypy app
ruff check app tests
docker build --target runtime -t nlc-runtime-smoke .
```

The GitHub Actions workflow remains the authoritative CI result. A local command list in this document is not evidence that a check passed.
