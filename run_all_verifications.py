#!/usr/bin/env python3
"""
Master verification orchestrator for the NLC platform audit.

Runs every static verification script in /home/z/my-project/scripts/ in
sequence, collects each JSON report, and produces a single consolidated
master report.

Usage:
    python scripts/run_all_verifications.py /path/to/nlc_platform_clean

Output:
    /home/z/my-project/scripts/all_findings.json          -- consolidated
    /home/z/my-project/scripts/all_findings_summary.txt   -- human-readable
"""
from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPTS = [
    "verify_rls.py",                  # SEC-001/002/DB-001 (needs DB URL, will fail w/o it but reports gracefully)
    "verify_tenant_isolation.py",    # SEC-003~012
    "verify_transfer_mapping.py",     # TR-007~012
    "verify_rule_integrity.py",      # RULE-001~010
    "verify_rescue_lifecycle.py",     # RES-001~009, RES-010~017
    "verify_rjsc_api.py",             # RJSC-001~006, API-001/002, UI-001
    "verify_db_ops.py",              # DB-001~003, OPS-001~006
    "verify_commercial.py",          # COM-001~007
    "verify_historical.py",          # HIST-* items
]


def run_script(script_path: Path, repo: Path, output_dir: Path) -> dict:
    """Run one verification script, return its report dict."""
    output_file = output_dir / (script_path.stem + "_report.json")
    args = [sys.executable, str(script_path), str(repo),
            "--output", str(output_file)]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=120)
        ok = proc.returncode in (0, 1)  # 1 means findings exist, but script worked
        if not ok:
            return {"script": script_path.name, "ok": False,
                    "stderr": proc.stderr[-2000:], "stdout_tail": proc.stdout[-2000:]}
        try:
            report = json.loads(output_file.read_text())
        except Exception as exc:
            return {"script": script_path.name, "ok": False,
                    "stderr": f"Could not parse output JSON: {exc}",
                    "stdout_tail": proc.stdout[-2000:]}
        return {"script": script_path.name, "ok": True, "report": report,
                "stdout_tail": proc.stdout[-1500:]}
    except subprocess.TimeoutExpired:
        return {"script": script_path.name, "ok": False,
                "stderr": "TIMEOUT after 120s",
                "stdout_tail": ""}
    except Exception as exc:
        return {"script": script_path.name, "ok": False,
                "stderr": str(exc), "stdout_tail": ""}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--database-url", help="Optional PostgreSQL URL for verify_rls.py runtime checks.")
    p.add_argument("--output-dir", default="/home/z/my-project/scripts",
                   help="Where JSON reports are written.")
    args = p.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        print(f"ERROR: repo path does not exist: {repo}", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== NLC Platform Master Verification ===")
    print(f"Repo: {repo}")
    print(f"Output dir: {out_dir}")
    print()

    results = []
    scripts_dir = Path("/home/z/my-project/scripts")
    for script_name in SCRIPTS:
        script_path = scripts_dir / script_name
        if not script_path.exists():
            print(f"[SKIP] {script_name}: not found at {script_path}")
            continue
        print(f"[RUN ] {script_name}")
        result = run_script(script_path, repo, out_dir)
        results.append(result)
        status = "OK" if result.get("ok") else "FAIL"
        findings = result.get("report", {}).get("findings", []) if result.get("ok") else []
        fail = sum(1 for f in findings if f.get("severity") == "FAIL")
        warn = sum(1 for f in findings if f.get("severity") == "WARN")
        print(f"      -> {status}  (FAIL={fail}  WARN={warn})")
        if not result.get("ok"):
            tail = result.get("stderr") or result.get("stdout_tail") or ""
            print(f"      stderr/tail: {tail[-400:]}")

    # Consolidated report
    all_findings = []
    for r in results:
        if not r.get("ok"):
            continue
        for f in r["report"].get("findings", []):
            f["_source_script"] = r["script"]
            all_findings.append(f)

    by_check: dict[str, list[dict]] = {}
    for f in all_findings:
        by_check.setdefault(f["check_id"], []).append(f)

    consolidated = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo": str(repo),
        "total_findings": len(all_findings),
        "fail_count": sum(1 for f in all_findings if f.get("severity") == "FAIL"),
        "warn_count": sum(1 for f in all_findings if f.get("severity") == "WARN"),
        "info_count": sum(1 for f in all_findings if f.get("severity") == "INFO"),
        "by_check": {cid: {"count": len(rows),
                            "fail": sum(1 for r in rows if r.get("severity") == "FAIL"),
                            "warn": sum(1 for r in rows if r.get("severity") == "WARN"),
                            "info": sum(1 for r in rows if r.get("severity") == "INFO")}
                     for cid, rows in sorted(by_check.items())},
        "findings": all_findings,
    }

    out_json = out_dir / "all_findings.json"
    out_json.write_text(json.dumps(consolidated, indent=2))

    out_summary = out_dir / "all_findings_summary.txt"
    with out_summary.open("w") as fh:
        fh.write(f"NLC Platform Master Verification -- {consolidated['generated_at']}\n")
        fh.write(f"Repo: {repo}\n\n")
        fh.write(f"Total findings: {consolidated['total_findings']}  "
                 f"(FAIL={consolidated['fail_count']}  "
                 f"WARN={consolidated['warn_count']}  "
                 f"INFO={consolidated['info_count']})\n\n")
        fh.write("Per-check breakdown:\n")
        for cid, stats in consolidated["by_check"].items():
            fh.write(f"  {cid:20s}  FAIL={stats['fail']:3d}  WARN={stats['warn']:3d}  "
                     f"INFO={stats['info']:3d}  total={stats['count']:3d}\n")
        fh.write("\n")
        fh.write("Critical findings (FAIL):\n")
        for f in all_findings:
            if f.get("severity") != "FAIL":
                continue
            fh.write(f"  [{f.get('_source_script', '?')}] {f['check_id']}  "
                     f"{f.get('file', '?')}:{f.get('line', 0)}  {f['detail']}\n")
            if f.get("suggested_fix"):
                fh.write(f"      FIX: {f['suggested_fix']}\n")

    print()
    print(f"Consolidated JSON: {out_json}")
    print(f"Human summary:    {out_summary}")
    print()
    print(f"Total findings: {consolidated['total_findings']}  "
          f"FAIL={consolidated['fail_count']}  "
          f"WARN={consolidated['warn_count']}  "
          f"INFO={consolidated['info_count']}")
    return 0 if consolidated["fail_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())