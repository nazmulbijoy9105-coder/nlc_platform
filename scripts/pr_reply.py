import json
import sys

import httpx

OWNER = "nazmulbijoy9105-coder"
REPO = "nlc_platform"
PR = 422

# comment_id -> reply body (all commit refs verified in git log; line refs
# verified by grep against current HEAD 48154c72)
REPLIES = {
    # cubic P1: paused switch vs registry-integrity failure (engine.py:4496)
    4686107032: (
        "Fixed in 48154c72.\n\n"
        "`_build_rescue_dispositions` now distinguishes the two fail-closed causes of "
        "`legal_score_is_released() == False`:\n\n"
        "- **Paused release switch** → a confirmed step stays `ACTION_REQUIRED / "
        "CONFIRMED_RESCUE_STEP` (approved contract, unchanged).\n"
        "- **Registry-integrity failure** → a new gate returns `BLOCKED / "
        "REGISTRY_INTEGRITY_FAILURE` instead of authorizing the step.\n\n"
        "The new `rescue_registry_integrity_failure()` requires exact scope parity "
        "(`assert_rjsc_scope_parity(STATUTORY_RULE_REGISTRY)`) and validates that every "
        "rule id referenced for authorization — flag rule ids plus each rescue step's "
        "`related_rules` — is a valid production registry id (production id = valid id, "
        "for all referenced ids). Integrity is checked once per disposition build and "
        "blocks authorization independently of the release switch.\n\n"
        "Verified locally:\n"
        "- Production registry holds 85 rule ids / 85 rescue mappings; every "
        "`related_rules` entry resolves to a production id, so the healthy path is unchanged.\n"
        "- New `tests/unit/test_rescue_registry_integrity_gate.py`: parity failure → "
        "BLOCKED; paused switch → ACTION_REQUIRED; unknown rule id in `related_rules` → BLOCKED.\n"
        "- `test_rescue_sequence_parity.py`: 37 passed (approved contract unchanged).\n"
        "- Targeted run `tests/unit -k \"rescue or disposition or legal_score or canonical "
        "or scoring or band\"`: 397 passed / 6 pre-existing collection errors vs 394 passed / "
        "the same 6 errors on the parent commit — the only delta is the 3 new tests. No new "
        "ruff findings (the single I001 import-sort finding is identical on the parent)."
    ),
    # sourcery: concurrent completions lose progress (update_step)
    4683432520: (
        "Addressed on this branch in 958c3d26: step updates serialize on the plan row — "
        "`select(RescuePlan.id) … with_for_update()` at app/services/rescue_service.py:465 — "
        "and progress is recalculated after the lock is held, so concurrent completions of "
        "different steps can no longer each overwrite the plan count with their own view."
    ),
    # sourcery: PDFs display a missing score
    4683432432: (
        "Addressed in 2d6387b8: the renderer emits a `NOT EVALUATED` label when "
        "`initial_score` is None (app/services/pdf_report_service.py:249) instead of "
        "interpolating `None/100`."
    ),
    # sourcery: unentitled companies get workflows
    4683432300: (
        "Addressed in ab20467b, with entitlement-lookup failure handling in 2e217c76: "
        "automatic plan creation checks the `corporate_rescue` entitlement via "
        "`SubscriptionService.has_entitlement` before inspecting or replacing any active "
        "plan (app/services/compliance_service.py:918–928), matching the rescue API path."
    ),
    # sourcery: older evaluations replace newer workflows
    4683432491: (
        "Addressed in eaf5bd28: the per-company lock is acquired before evaluation inputs "
        "are read, so an older evaluation can no longer take the lock after a newer "
        "evaluation committed and overwrite its workflow with stale findings (lock-ordering "
        "note at app/services/compliance_service.py:527)."
    ),
    # sourcery: concurrent requests create duplicate workflows
    4683432469: (
        "Addressed by migration 0127 (`alembic/versions/0127_one_active_rescue_plan_per_company.py`, "
        "unique index at lines 46–50) mirrored in the model (app/models/rescue.py:50,53): "
        "one-active-plan-per-company is now enforced in the database, and plan creation is "
        "serialized under the company/plan locks. ddf454a6 additionally locks rescue plans "
        "during the index migration."
    ),
    # sourcery: created workflows hidden from callers
    4683432451: (
        "Addressed in a7e135e3: evaluation results report the eligible rescue sequence and "
        "workflow status independently of score publication "
        "(app/services/compliance_service.py:101–102, 374–382)."
    ),
    # sourcery: conflicting evaluations start workflows
    4683432340: (
        "Addressed in 3a836a34 (with e3a3ce5c): automatic plan creation is rejected whenever "
        "score-blocking catalogue identity conflicts exist, even when an unrelated rescue "
        "sequence remains (identity-mismatch handling at app/services/compliance_service.py:119–125)."
    ),
    # sourcery: failed generation commits an incomplete plan
    4683432511: (
        "Addressed in 91e85764 and 3c944d84: workflow generation runs inside a savepoint "
        "(`db.begin_nested()` at app/services/compliance_service.py:971 and "
        "app/services/rescue_service.py:210), so a generation failure rolls back the partial "
        "plan/step/task writes instead of committing an incomplete active plan."
    ),
    # sourcery: withheld scores appear on plans
    4683432365: (
        "Addressed in d484f041 (defaulting in fded1606): plan generation receives the "
        "evaluation's score-publication status (`score_withheld`, app/services/rescue_service.py:45–49, "
        "180, 220) and copies score and risk-band values only when that evaluation's score is "
        "publishable (rescue_service.py:78)."
    ),
}


def main() -> int:
    token = sys.argv[1]
    with httpx.Client(base_url="https://api.github.com") as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }
        ok, fail = 0, 0
        for comment_id, body in REPLIES.items():
            resp = client.post(
                f"/repos/{OWNER}/{REPO}/pulls/{PR}/comments",
                headers=headers,
                json={"body": body, "in_reply_to": comment_id},
            )
            if resp.status_code == 201:
                ok += 1
                print(f"replied to {comment_id} -> id {resp.json()['id']}")
            else:
                fail += 1
                print(f"FAILED {comment_id}: {resp.status_code} {resp.text[:200]}")
        print(f"done: {ok} replied, {fail} failed")
        return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
