# Legal-engine assurance (P0)

This document separates the **legal-engine assurance chain** from the
**infrastructure release chain**. Both must pass before a production legal
score can be trusted.

Workflow: `.github/workflows/legal-engine-assurance.yml`

## P0 controls and required evidence

| Missing control | Why it matters | Required evidence | Automated today |
|-----------------|----------------|-------------------|-----------------|
| **85-rule catalogue integrity** | Deploy is meaningless if live rules differ from the approved catalogue | Exact parity across source, database, evaluator, and API | **Static** engine↔seed ID parity + six-state funnel on every PR; **live** DB/API parity remains release/post-deploy (`audit_rule_parity.py` without `--no-db`/`--no-api`, `production-parity.yml`) |
| **RJSC scope isolation** | Non-RJSC obligations must not move a released RJSC score or risk band | Inject all OUT_OF_SCOPE rules without changing score, band, or score hash | `tests/unit/test_rjsc_scope_registry.py` (26 OUT_OF_SCOPE injections) |
| **Score provenance and reproducibility** | A company must reconstruct why it received a score | Score hash, rule versions, source evidence, snapshot date, engine version | `tests/unit/test_evaluation_integrity.py`, score-hash helpers, rule outcome ledger tests |
| **Fail-closed publication gate** | Incomplete, stale, or unverified evaluation must not publish a misleading score | Withheld / NOT_EVALUATED under every blocking condition | `tests/unit/test_not_evaluated_score_visibility.py`, release switches in engine/API |
| **Human approval and override audit** | AI drafts must not silently become approved legal decisions | Approval identity, timestamp, original recommendation, override reason, immutable history | **Partial** — model/service audit trails exist; dedicated approval-path CI gate still required |
| **End-to-end legal workflow** | Registration → profile → evaluation → review → approval → filing → calendar | Product-level E2E against staging/production-like env | **Not automated** in this repo’s Actions (frontend/API E2E follow-up) |

## Independence rule

Infrastructure may be green (CI, migrations, deploy hooks) while legal-engine
assurance is red, and the reverse. A production release that publishes RJSC
scores requires **both** chains green on the **same** commit SHA.

## Recommended required checks on `main`

1. `Legal engine assurance` / `legal-engine-p0` (aggregate; requires all four P0 jobs)
2. Existing `CI` unit + integration
3. Security closure structure
4. Post-deploy: production parity + readonly tenant smoke (controlled release path)

The aggregate job is the single branch-protection check to require. It fails if
catalogue parity, RJSC scope isolation, score provenance, or fail-closed
publication is failed, skipped, or cancelled. The deployment workflows also
wait for a successful `push` assurance run for the exact commit SHA before
any migration or deployment step.

## Follow-ups (not in this workflow)

1. Human legal-approval CI: assert every published counsel-facing decision row
   carries actor, timestamp, prior recommendation, and non-empty override reason
   when recommendation ≠ decision.
2. Frontend/backend Playwright (or equivalent) journey for the full legal workflow.
3. Make live multi-source rule parity (DB + API) a hard step of controlled
   production release, retaining the JSON report as release evidence.
