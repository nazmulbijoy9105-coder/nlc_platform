#!/usr/bin/env python3
"""
Master verification orchestrator for the NLC platform audit.

Runs every static verification script from the trusted scripts directory,
collects each JSON report, and produces a consolidated master report.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


SCRIPTS = [
    "verify_rls.py",
    "verify_tenant_isolation.py",
    "verify_transfer_mapping.py",
    "verify_rule_integrity.py",
    "verify_rescue_lifecycle.py",
    "verify_rjsc_api.py",
    "verify_db_ops.py",
    "verify_commercial.py",
    "verify_historical.py",
]


def run_script(script_path: Path, repo: Path, output_dir: Path) -> dict:
    """Run one allow-listed verification script and return its report."""
    trusted_scripts_dir = Path(__file__).resolve().parent
    resolved_script = script_path.resolve()
    if resolved_script.parent != trusted_scripts_dir or resolved_script.name not in SCRIPTS:
        return {
            "script": script_path.name,
            "ok": False,
            "stderr": "Refusing to execute a script outside the allow-listed scripts directory.",
            "stdout_tail": "",
        }
    if not resolved_script.is_file():
        return {
            "script": resolved_script.name,
            "ok": False,
            "stderr": "Verification script does not exist.",
            "stdout_tail": "",
        }

    output_file = output_dir / f"{resolved_script.stem}_report.json"
    if output_file.is_symlink():
        return {
            "script": resolved_script.name,
            "ok": False,
            "stderr": f"Refusing to write report to symlinked path: {output_file}",
            "stdout_tail": "",
        }
    args = [
        sys.executable,
        str(resolved_script),
        str(repo.resolve()),
        "--output",
        str(output_file),
    ]
    try:
        proc = subprocess.run(
            args,
            shell=False,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            close_fds=True,
            check=False,
        )
        ok = proc.returncode in (0, 1)  # 1 means findings exist; execution succeeded.
        if not ok:
            return {
                "script": resolved_script.name,
                "ok": False,
                "stderr": proc.stderr[-2000:],
                "stdout_tail": proc.stdout[-2000:],
            }
        try:
            report = json.loads(output_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {
                "script": resolved_script.name,
                "ok": False,
                "stderr": f"Could not parse output JSON: {exc}",
                "stdout_tail": proc.stdout[-2000:],
            }
        return {
            "script": resolved_script.name,
            "ok": True,
            "report": report,
            "stdout_tail": proc.stdout[-1500:],
        }
    except UnicodeDecodeError as exc:
        return {
            "script": resolved_script.name,
            "ok": False,
            "stderr": f"Could not decode verification subprocess output as text: {exc}",
            "stdout_tail": "",
        }
    except subprocess.TimeoutExpired:
        return {
            "script": resolved_script.name,
            "ok": False,
            "stderr": "TIMEOUT after 120s",
            "stdout_tail": "",
        }
    except OSError as exc:
        return {
            "script": resolved_script.name,
            "ok": False,
            "stderr": str(exc),
            "stdout_tail": "",
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo", help="Path to the nlc_platform repository root.")
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL URL for verify_rls.py runtime checks.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent),
        help="Where JSON reports are written.",
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"ERROR: repo directory does not exist: {repo}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_json = out_dir / "all_findings.json"
    out_summary = out_dir / "all_findings_summary.txt"
    for report_path in (out_json, out_summary):
        if report_path.is_symlink():
            print(
                f"ERROR: refusing to write report to symlinked path: {report_path}",
                file=sys.stderr,
            )
            return 2

    print("=== NLC Platform Master Verification ===")
    print(f"Repo: {repo}")
    print(f"Output dir: {out_dir}\n")

    results = []
    scripts_dir = Path(__file__).resolve().parent
    for script_name in SCRIPTS:
        script_path = scripts_dir / script_name
        if not script_path.is_file():
            print(f"[SKIP] {script_name}: not found at {script_path}")
            continue
        print(f"[RUN ] {script_name}")
        result = run_script(script_path, repo, out_dir)
        results.append(result)
        status = "OK" if result.get("ok") else "FAIL"
        findings = result.get("report", {}).get("findings", []) if result.get("ok") else []
        fail = sum(1 for finding in findings if finding.get("severity") == "FAIL")
        warn = sum(1 for finding in findings if finding.get("severity") == "WARN")
        print(f"      -> {status}  (FAIL={fail}  WARN={warn})")
        if not result.get("ok"):
            tail = result.get("stderr") or result.get("stdout_tail") or ""
            print(f"      stderr/tail: {tail[-400:]}")

    all_findings = []
    for result in results:
        if not result.get("ok"):
            continue
        for finding in result["report"].get("findings", []):
            finding["_source_script"] = result["script"]
            all_findings.append(finding)

    by_check: dict[str, list[dict]] = {}
    for finding in all_findings:
        by_check.setdefault(finding["check_id"], []).append(finding)

    generated_at = datetime.now().astimezone().isoformat()
    consolidated = {
        "generated_at": generated_at,
        "repo": str(repo),
        "total_findings": len(all_findings),
        "fail_count": sum(1 for finding in all_findings if finding.get("severity") == "FAIL"),
        "warn_count": sum(1 for finding in all_findings if finding.get("severity") == "WARN"),
        "info_count": sum(1 for finding in all_findings if finding.get("severity") == "INFO"),
        "by_check": {
            check_id: {
                "count": len(rows),
                "fail": sum(1 for row in rows if row.get("severity") == "FAIL"),
                "warn": sum(1 for row in rows if row.get("severity") == "WARN"),
                "info": sum(1 for row in rows if row.get("severity") == "INFO"),
            }
            for check_id, rows in sorted(by_check.items())
        },
        "findings": all_findings,
    }

    out_json.write_text(json.dumps(consolidated, indent=2), encoding="utf-8")

    with out_summary.open("w", encoding="utf-8") as summary_file:
        summary_file.write(
            f"NLC Platform Master Verification -- {generated_at}\n"
            f"Repo: {repo}\n\n"
            f"Total findings: {consolidated['total_findings']}  "
            f"(FAIL={consolidated['fail_count']}  "
            f"WARN={consolidated['warn_count']}  "
            f"INFO={consolidated['info_count']})\n\n"
            "Per-check breakdown:\n"
        )
        for check_id, stats in consolidated["by_check"].items():
            summary_file.write(
                f"  {check_id:20s}  FAIL={stats['fail']:3d}  "
                f"WARN={stats['warn']:3d}  INFO={stats['info']:3d}  "
                f"total={stats['count']:3d}\n"
            )
        summary_file.write("\nCritical findings (FAIL):\n")
        for finding in all_findings:
            if finding.get("severity") != "FAIL":
                continue
            summary_file.write(
                f"  [{finding.get('_source_script', '?')}] "
                f"{finding['check_id']}  {finding.get('file', '?')}:"
                f"{finding.get('line', 0)}  {finding['detail']}\n"
            )
            if finding.get("suggested_fix"):
                summary_file.write(f"      FIX: {finding['suggested_fix']}\n")

    print(f"\nConsolidated JSON: {out_json}")
    print(f"Human summary:    {out_summary}\n")
    print(
        f"Total findings: {consolidated['total_findings']}  "
        f"FAIL={consolidated['fail_count']}  "
        f"WARN={consolidated['warn_count']}  "
        f"INFO={consolidated['info_count']}"
    )
    return 0 if consolidated["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
