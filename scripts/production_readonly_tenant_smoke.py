#!/usr/bin/env python3
"""Read-only production tenant and six-state smoke test.

No writes are performed. Configure the required bearer tokens as GitHub
repository secrets and company UUIDs as repository variables before dispatch.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from typing import Any


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required smoke configuration is missing: {name}")
    return value


def company_id(name: str) -> str:
    value = required(name)
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a UUID") from exc


def get_json(base_url: str, path: str, token: str | None = None) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        headers=headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Production API request failed: {exc.reason}") from exc

    if not raw:
        return status, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Non-JSON response for {path} (HTTP {status})") from exc


def expect_status(label: str, status: int, accepted: set[int]) -> None:
    if status not in accepted:
        raise RuntimeError(f"{label}: expected HTTP {sorted(accepted)}, received {status}")
    print(f"PASS {label}: HTTP {status}")


def verify_authorized_company(
    *,
    base_url: str,
    label: str,
    token: str,
    allowed_company: str,
    denied_company: str,
) -> None:
    company_path = f"/api/v1/companies/{allowed_company}"
    status, _ = get_json(base_url, company_path, token)
    expect_status(f"{label} allowed company", status, {200})

    coverage_path = f"{company_path}/rule-coverage"
    status, coverage = get_json(base_url, coverage_path, token)
    expect_status(f"{label} allowed six-state report", status, {200})
    if not isinstance(coverage, dict) or not isinstance(coverage.get("report"), dict):
        raise RuntimeError(f"{label}: rule-coverage response is missing its report")
    report = coverage["report"]
    summary = report.get("summary") or {}
    if report.get("validation_status") != "PASS":
        raise RuntimeError(f"{label}: six-state report invariants did not pass")
    if summary.get("registered") != 85 or summary.get("implemented") != 85:
        raise RuntimeError(
            f"{label}: canonical registry/engine parity is not 85/85 "
            f"(registered={summary.get('registered')}, implemented={summary.get('implemented')})"
        )
    if summary.get("active") != 84:
        raise RuntimeError(
            f"{label}: expected 84 active canonical rules with INC-001 held, "
            f"received active={summary.get('active')}"
        )
    states = report.get("states") or {}
    registered_ids = states.get("registered")
    implemented_ids = states.get("implemented")
    if not isinstance(registered_ids, list) or not isinstance(implemented_ids, list):
        raise RuntimeError(f"{label}: report omitted canonical registered/implemented ID lists")
    if len(registered_ids) != 85 or set(registered_ids) != set(implemented_ids):
        raise RuntimeError(f"{label}: the 85 canonical IDs do not exactly match engine implementations")
    active_ids = states.get("active")
    if not isinstance(active_ids, list) or len(active_ids) != 84 or "INC-001" in set(active_ids):
        raise RuntimeError(f"{label}: active IDs must contain exactly 84 entries and exclude held INC-001")
    if report.get("validation_violations") != []:
        raise RuntimeError(f"{label}: six-state report contains structural violations")
    active_ids = states.get("active")
    applicable_ids = states.get("applicable")
    evaluated_ids = states.get("evaluated")
    if active_ids is not None and not set(active_ids).issubset(set(implemented_ids)):
        raise RuntimeError(f"{label}: active IDs exceed the implemented set")
    if applicable_ids is not None and (
        active_ids is None or not set(applicable_ids).issubset(set(active_ids))
    ):
        raise RuntimeError(f"{label}: applicable IDs exceed the active set")
    if evaluated_ids is not None and (
        applicable_ids is None or not set(evaluated_ids).issubset(set(applicable_ids))
    ):
        raise RuntimeError(f"{label}: evaluated IDs exceed the applicable set")
    applicability_summary = report.get("applicability_summary")
    if applicability_summary is not None:
        expected_states = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
        if set(applicability_summary) != expected_states:
            raise RuntimeError(f"{label}: applicability report omitted a six-state value")
        if sum(applicability_summary.values()) != 84:
            raise RuntimeError(f"{label}: applicability counts do not reconcile to 84 active rules")
    elif summary.get("applicable") is not None or summary.get("evaluated") is not None:
        raise RuntimeError(f"{label}: run-scoped counts exist without applicability-state detail")
    print(
        f"PASS {label} six-state parity: "
        f"registered={summary['registered']}, implemented={summary['implemented']}, "
        f"active={summary.get('active')}, applicable={summary.get('applicable')}, "
        f"evaluated={summary.get('evaluated')}"
    )

    runs_path = f"{company_path}/evaluation-runs"
    status, runs = get_json(base_url, runs_path, token)
    expect_status(f"{label} allowed evaluation history", status, {200})
    if not isinstance(runs, dict) or not isinstance(runs.get("items"), list):
        raise RuntimeError(f"{label}: evaluation-runs response is malformed")
    for item in runs["items"]:
        if "rule_outcomes_snapshot" in item or "fact_provenance_snapshot" in item:
            raise RuntimeError(f"{label}: raw evidence snapshot was exposed by the history index")
        if item.get("canonical_rule_count") != 85:
            raise RuntimeError(f"{label}: evaluation history did not use the 85-rule canonical registry")
        missing_ids = item.get("missing_canonical_rule_ids")
        unmapped_ids = item.get("unmapped_outcome_rule_ids")
        if not isinstance(missing_ids, list) or not isinstance(unmapped_ids, list):
            raise RuntimeError(f"{label}: history omitted canonical ID reconciliation metadata")
        if missing_ids or unmapped_ids:
            print(
                f"REVIEW {label} historical run {item.get('evaluation_run_id')} "
                f"preserves missing={missing_ids[:5]} and legacy_extra={unmapped_ids[:5]}"
            )
    print(f"PASS {label} evaluation history: {len(runs['items'])} metadata-only run(s)")

    denied_path = f"/api/v1/companies/{denied_company}"
    status, _ = get_json(base_url, denied_path, token)
    expect_status(f"{label} cross-tenant company denial", status, {403, 404})

    denied_coverage_path = f"{denied_path}/rule-coverage"
    status, _ = get_json(base_url, denied_coverage_path, token)
    expect_status(f"{label} cross-tenant coverage denial", status, {403, 404})

    denied_runs_path = f"{denied_path}/evaluation-runs"
    status, _ = get_json(base_url, denied_runs_path, token)
    expect_status(f"{label} cross-tenant history denial", status, {403, 404})


def main() -> int:
    base_url = os.getenv(
        "NLC_PROD_API_BASE_URL",
        "https://nlc-platform.onrender.com",
    ).strip()
    client_token = required("NLC_PROD_CLIENT_BEARER")
    staff_token = required("NLC_PROD_STAFF_BEARER")
    admin_token = required("NLC_PROD_SUPER_ADMIN_BEARER")

    client_company = company_id("NLC_PROD_CLIENT_COMPANY_ID")
    client_foreign = company_id("NLC_PROD_CLIENT_FOREIGN_COMPANY_ID")
    staff_company = company_id("NLC_PROD_STAFF_COMPANY_ID")
    staff_unassigned = company_id("NLC_PROD_STAFF_UNASSIGNED_COMPANY_ID")
    historical_company = company_id("NLC_PROD_HISTORICAL_COMPANY_ID")

    status, readiness = get_json(base_url, "/api/v1/health/ready")
    expect_status("production readiness", status, {200})
    if not isinstance(readiness, dict):
        raise RuntimeError("Production readiness response is malformed")
    print("PASS production readiness endpoint returned a structured health response")

    # Unauthenticated requests must not obtain even a company summary.
    status, _ = get_json(base_url, f"/api/v1/companies/{client_company}")
    expect_status("unauthenticated company request", status, {401})

    verify_authorized_company(
        base_url=base_url,
        label="CLIENT_VIEW_ONLY",
        token=client_token,
        allowed_company=client_company,
        denied_company=client_foreign,
    )
    verify_authorized_company(
        base_url=base_url,
        label="LEGAL_STAFF",
        token=staff_token,
        allowed_company=staff_company,
        denied_company=staff_unassigned,
    )

    # A SUPER_ADMIN must be able to read both test tenants, but only through
    # the authenticated API; this remains a GET-only test.
    for company in sorted({client_company, staff_company, historical_company}):
        status, _ = get_json(base_url, f"/api/v1/companies/{company}", admin_token)
        expect_status("SUPER_ADMIN company access", status, {200})
        status, coverage = get_json(
            base_url, f"/api/v1/companies/{company}/rule-coverage", admin_token
        )
        expect_status("SUPER_ADMIN six-state report", status, {200})
        if not isinstance(coverage, dict) or coverage.get("report", {}).get("validation_status") != "PASS":
            raise RuntimeError("SUPER_ADMIN six-state report invariants did not pass")
        status, runs = get_json(
            base_url, f"/api/v1/companies/{company}/evaluation-runs", admin_token
        )
        expect_status("SUPER_ADMIN evaluation history", status, {200})
        if not isinstance(runs, dict) or not isinstance(runs.get("items"), list):
            raise RuntimeError("SUPER_ADMIN evaluation history response is malformed")

    # Verify the selected company's live six-state funnel for its 15 November run.
    status, historical_coverage = get_json(
        base_url, f"/api/v1/companies/{historical_company}/rule-coverage", admin_token
    )
    expect_status("SUPER_ADMIN selected historical six-state report", status, {200})
    historical_report = (
        historical_coverage.get("report")
        if isinstance(historical_coverage, dict) else None
    )
    historical_summary = (historical_report or {}).get("summary") or {}
    if (
        historical_summary.get("registered") != 85
        or historical_summary.get("implemented") != 85
        or historical_summary.get("active") != 84
        or historical_summary.get("applicable") != 0
        or historical_summary.get("evaluated") != 0
    ):
        raise RuntimeError(
            f"15 November live funnel mismatch: {historical_summary}"
        )
    if (historical_report or {}).get("applicability_summary") != {
        "APPLICABLE": 0, "NOT_APPLICABLE": 0, "UNKNOWN": 84
    }:
        raise RuntimeError("15 November live funnel must preserve 84 UNKNOWN active-rule applicability states")

    # Reconcile the specific 15 November run against the monthly score history
    # without rewriting the November 9 NOT_RELEASED snapshot.
    status, history = get_json(
        base_url, f"/api/v1/companies/{historical_company}/evaluation-runs?limit=60", admin_token
    )
    expect_status("SUPER_ADMIN selected historical evaluation", status, {200})
    if not isinstance(history, dict) or not isinstance(history.get("items"), list):
        raise RuntimeError("Selected historical evaluation history response is malformed")
    target_run_id = "3150a0df-de28-4dd3-ab97-6bb16e1d7683"
    run = next(
        (item for item in history.get("items", []) if item.get("evaluation_run_id") == target_run_id),
        None,
    )
    if run is None:
        raise RuntimeError("15 November 2026 historical evaluation is absent from the per-run history")
    expected_run = {
        "evaluation_status": "COMPLETED",
        "rule_catalogue_count": 86,
        "rule_outcomes_count": 86,
        "canonical_rule_count": 85,
        "missing_canonical_rule_ids": [],
        "unmapped_outcome_rule_ids": ["INC-002"],
        "fact_provenance_count": 1,
        "fact_provenance_record_type_counts": {"UNATTRIBUTED_PROFILE_FIELDS": 1},
        "unattributed_profile_record_count": 1,
        "evidence_reference_count": 0,
        "evidence_reference_present": False,
        "score_hash": "6c2f654c5abd5367e28fe9297952aef8c80a6e287598472c5f6e1a06e2faa103",
        "rule_outcomes_hash": "68cb2708a67d5aa8f5472e07cfd5033df9877cbcd69869edd081c43724aa1b1c",
        "applicability_state_counts": {"UNKNOWN": 86},
    }
    for key, expected in expected_run.items():
        if run.get(key) != expected:
            raise RuntimeError(f"15 November evaluation mismatch for {key}: {run.get(key)!r}")
    status, score_history = get_json(
        base_url, f"/api/v1/companies/{historical_company}/score-history", admin_token
    )
    expect_status("SUPER_ADMIN monthly score history", status, {200})
    november_snapshot = next(
        (item for item in score_history if str(item.get("snapshot_month", "")).startswith("2026-11")),
        None,
    )
    if november_snapshot is None:
        raise RuntimeError("November monthly score-history row is absent")
    if november_snapshot.get("score") is not None or november_snapshot.get("evaluation_status") != "NOT_EVALUATED":
        raise RuntimeError("15 November run must not overwrite the 9 November NOT_RELEASED monthly snapshot")

    print("PASS production read-only tenant matrix and 15 November historical reconciliation; no mutations were issued")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI must print a concise failure reason.
        print(f"FAIL production read-only tenant smoke: {exc}", file=sys.stderr)
        raise SystemExit(1)
