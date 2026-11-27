# Gap closure status (2026-11-27)

Honest status of the release-blocking gap table.

| Gap | Made OK in-repo? | Evidence / residual |
|-----|------------------|---------------------|
| PR #426 CI green | **In progress** | Contract tests fixed (`FakeConn.is_closed()` method). Await Actions on tip SHA. |
| 0112→0128 Neon rehearsal | **Not yet** | Requires Neon secrets + successful workflow run; script/contract present. |
| Live 85-rule parity DB+API | **Release-path** | Controlled release runs `tools/audit_production_release_parity.py`; static parity on PR. |
| Dual production deploy paths | **Mitigated** | `deploy-vercel-backend.yml` bound to `environment: production` (approval gate). Prefer `production-release.yml` as authority. |
| Human approval / override audit gate | **Partial** | `tests/unit/test_human_approval_audit_contract.py` + RescueAuditLog surface. Full decision-path CI still thin. |
| AuthZ matrix + observability + E2E | **Not fully** | Existing company-access / RLS tests; E2E and full matrix still open. |
| Security closure live gate | **Document closed** | Item 4 CLOSED via LICENSE + `docs/DEPENDENCY_LICENSE_POLICY.md`. Live pip-audit still runs at release. |

**Production remains HOLD** until CI green + successful isolated Neon rehearsal on the exact release SHA.
