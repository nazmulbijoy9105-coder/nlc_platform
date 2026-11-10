# Engineering hardening plan

Baseline: main at 3c4bf02f541a67cb8270e8cc86640117bfded289 (2026-11-10).

## 1. Modularization

Observed large modules:
- app/rule_engine/engine.py (~204,656 bytes)
- app/services/company_service.py (~65,152 bytes)
- app/services/compliance_service.py (~44,335 bytes)
- app/services/subscription_service.py (~39,280 bytes)
- app/services/pdf_report_service.py (~30,533 bytes)

Refactoring rules:
- Preserve public imports, service constructors, API schemas, persisted score snapshots, and rule IDs during extraction.
- Extract cohesive pure functions and domain policies before moving orchestration or database transaction boundaries.
- Keep scoring, applicability/evidence resolution, rescue mapping, audit serialization, and BLACK override authorization as separately testable responsibilities.
- Do not change scoring semantics or the product-controlled scoring allowlist as part of structural refactoring.
- Require characterization/parity tests before and after each extraction; compare score, risk band, deductions, rule findings, rescue steps, and audit payloads.
- Move one bounded responsibility per PR; avoid a single large rewrite.

Initial extraction candidates (subject to call-graph and import-cycle review):
1. Rule catalogue and scoring constants.
2. Evidence/applicability normalization.
3. Rule evaluation and finding construction.
4. Score aggregation and risk-band calculation.
5. Rescue mapping and step generation.
6. Audit/snapshot serialization.

## 2. Dependency security and reproducibility

Current observations:
- requirements.txt is a large pinned requirements file.
- No separate requirements.lock exists at baseline.
- requirements.txt contains duplicate APScheduler declarations and comments documenting deferred Starlette and ecdsa vulnerability remediation.
- Dockerfile installs requirements.txt directly and upgrades pip to a fixed older version.

Required work:
- Generate a hash-verified lock from the actual supported Python 3.11 environment; do not hand-edit transitive pins.
- Separate runtime dependencies from development/test/security tooling.
- Run pip-audit against the resolved production dependency graph and produce machine-readable results.
- Prioritize reachable runtime vulnerabilities; verify upstream fixed versions and compatibility before upgrades.
- Replace vulnerable cryptographic/authentication dependencies only with an explicit migration plan and auth regression tests.
- Build Docker images from the same locked runtime dependency set used in deployment.
- Keep the lock generation reproducible and fail CI when manifests and lock drift.

No dependency version is upgraded by this baseline document. In particular, do not claim the documented Starlette or ecdsa findings are fixed until the resolved graph is audited and regression tests pass.

## 3. Coverage and CI verification

Existing pyproject.toml declares coverage fail_under=70, but baseline CI does not invoke pytest with coverage. First measure actual coverage and publish the report as an artifact. Set a ratcheting threshold only after a stable baseline is captured.

Priority coverage areas:
- Rule applicability and evidence states.
- Product scoring allowlist and score aggregation.
- BLACK override authorization and risk-band precedence.
- Rescue eligibility, generation, and engagement separation.
- Tenant isolation, RLS identity, and actor binding.
- API authorization and dashboard score/KPI consistency.

CI verification should include:
- Unit and integration suites.
- Coverage report and ratcheting threshold.
- Ruff and mypy on changed modules, then expand scope.
- Rule engine/seed/API parity.
- Alembic single-head and fresh-database migration rehearsals.
- Dependency lock consistency and pip-audit.
- Secret scanning and Docker runtime smoke.

## Delivery sequence

1. Capture baseline coverage, dependency audit, import graph, and module responsibility map.
2. Add the lock-generation and vulnerability-remediation workflow.
3. Extract one rule-engine responsibility with parity tests.
4. Extract one large-service responsibility with transaction-boundary tests.
5. Raise coverage thresholds incrementally and make verification checks required.

All changes must preserve product-controlled scoring release behavior, tenant isolation, and production authorization boundaries.
