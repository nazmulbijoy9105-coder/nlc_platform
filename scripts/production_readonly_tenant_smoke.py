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
    for company in (client_company, staff_company):
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

    print("PASS production read-only tenant matrix completed; no mutations were issued")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI must print a concise failure reason.
        print(f"FAIL production read-only tenant smoke: {exc}", file=sys.stderr)
        raise SystemExit(1)
