#!/usr/bin/env python3
"""
RULE-001 through RULE-010 -- Rule evaluation & evidence integrity audit.

Static analyzer for the NLC platform's rule_engine and rule registry. Flags
semantic gaps that would let "missing data" be confused with "verified absent"
or "contradictory evidence".

Findings emitted (one or more per check):
    RULE-001  Empty director data collapses to count=0
    RULE-002  Null auditor information treated inconsistently across layers
    RULE-003  UNKNOWN / CONTRADICTORY / NOT_APPLICABLE / VERIFIED_ABSENT need
              consistent semantics -- checks for enum presence + score impact = 0
              for non-NON_COMPLIANT states
    RULE-004  Rule applicability/exceptions evaluated before scoring/escalation
    RULE-005  Missing evidence becoming confirmed statutory breach
    RULE-006  Multiple rule registries / legacy corpora disagree
    RULE-007  Canonical rule registry authority -- engine/seed/API/historical
              identity reconciliation
    RULE-008  Historical rule versions remain reproducible
    RULE-009  Score hash captures evidence + version info
    RULE-010  Statutory references -- flags `TBD`/`RECONCILE` provision_status

Usage:
    python scripts/verify_rule_integrity.py /path/to/nlc_platform_clean
"""
from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse
import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Finding:
    check_id: str
    file: str
    line: int
    severity: str
    detail: str
    suggested_fix: str = ""


def collect_python_files(repo_root: Path) -> list[Path]:
    targets = []
    for sub in ("app", "canonical_architecture", "tests"):
        d = repo_root / sub
        if d.exists():
            targets.extend(p for p in d.rglob("*.py"))
    return sorted(targets)


def check_rule_001(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-001: empty director data collapses to count=0 -- INC-003 fires BLACK."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    if not engine.exists():
        findings.append(Finding("RULE-001", "?", 0, "WARN",
                                "engine.py not found; cannot verify empty-director handling."))
        return
    text = engine.read_text(encoding="utf-8", errors="ignore")
    # INC-003 should distinguish "no directors in NLC records" from "verified absence".
    inc003_lines = [i + 1 for i, ln in enumerate(text.splitlines())
                    if "INC-003" in ln or "inc003" in ln.lower()]
    has_verify_note = "verification" in text.lower() and ("absence" in text.lower() or "verify" in text.lower())
    # The latest paste shows: "Director records require verification - absence in NLC database
    # does not confirm actual absence." -- so the description was patched. But the score path
    # still treats count=0 as BLACK.
    if 'current_director_count == 0' in text or 'current_director_count) == 0' in text or 'not current_director_count' in text:
        if not has_verify_note:
            findings.append(Finding(
                "RULE-001", str(engine), 0, "FAIL",
                "INC-003 uses count==0 to fire BLACK without verifying actual absence from RJSC.",
                "Either (a) introduce a separate `directors_verified: bool` field that must be True "
                "before count=0 can fire BLACK, or (b) reclassify count=0 cases as UNKNOWN until "
                "verified.",
            ))
        else:
            findings.append(Finding(
                "RULE-001", str(engine), 0, "WARN",
                "INC-003 description acknowledges verification need, but score path still treats "
                "count=0 as BLACK. Description is documentation, not behaviour. CONFIRM at runtime.",
                "Add a unit test where `directors_verified=False` produces UNKNOWN (not BLACK) "
                "and only when `directors_verified=True` does count=0 fire BLACK.",
            ))


def check_rule_002(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-002: null auditor info -- check engine vs service handling."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    if not engine.exists():
        return
    text = engine.read_text(encoding="utf-8", errors="ignore")
    # look for AUD-001 / AUD-002 references and how null auditor data is consumed
    aud_lines = [i + 1 for i, ln in enumerate(text.splitlines())
                 if "auditor" in ln.lower() and ("None" in ln or "not " in ln or "if " in ln)]
    if aud_lines:
        # check if any of them collapse to a boolean
        collapse_re = re.compile(r"bool\s*\(\s*[^)]*auditor|if\s+.*auditor.*:\s*$", re.I | re.M)
        for ln_no in aud_lines[:5]:
            line = text.splitlines()[ln_no - 1]
            if collapse_re.search(line):
                findings.append(Finding(
                    "RULE-002", str(engine), ln_no, "WARN",
                    f"Auditor field treated as truthy/falsy without distinguishing None vs empty list: {line.strip()}",
                    "Use a 3-valued enum (PRESENT/ABSENT/UNKNOWN) instead of bool().",
                ))


def check_rule_003(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-003: ensure RuleState enum has UNKNOWN/CONTRADICTORY/NOT_APPLICABLE/VERIFIED_ABSENT."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    canonical = repo_root / "canonical_architecture" / "statutory_rules.py"
    for path in (engine, canonical):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # find RuleState class definition
        m = re.search(r"class\s+RuleState[^:]*:\s*\n([\s\S]*?)(?=\nclass|\Z)", text)
        if not m:
            continue
        body = m.group(1)
        members = re.findall(r"^[\s]*(\w+)\s*=", body, re.M)
        required = {"UNKNOWN", "CONTRADICTORY", "NOT_APPLICABLE", "VERIFIED_ABSENT", "NON_COMPLIANT", "COMPLIANT"}
        missing = required - set(members)
        if missing:
            findings.append(Finding(
                "RULE-003", str(path), 0, "FAIL",
                f"RuleState enum in {path.name} missing members: {sorted(missing)}",
                "Add the missing enum members and update engine code to treat each distinctly.",
            ))
        else:
            findings.append(Finding(
                "RULE-003", str(path), 0, "INFO",
                f"RuleState enum in {path.name} has all required members.",
            ))
    # Now check scoring: only NON_COMPLIANT should add to score
    if engine.exists():
        text = engine.read_text(encoding="utf-8", errors="ignore")
        # Score loop should filter f.state == RuleState.NON_COMPLIANT
        score_loops = re.findall(r"sum\([^)]*for[^)]*in[^)]*\)", text)
        bad_loops = [s for s in score_loops if "RuleState.NON_COMPLIANT" not in s and "f.state" not in s]
        if bad_loops:
            findings.append(Finding(
                "RULE-003", str(engine), 0, "WARN",
                f"{len(bad_loops)} score-accumulation loop(s) do not filter state == NON_COMPLIANT: "
                f"{bad_loops[:3]}",
                "Add `if f.state == RuleState.NON_COMPLIANT` filter to every deduction sum.",
            ))


def check_rule_004(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-004: applicability/exceptions evaluated before scoring."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    if not engine.exists():
        return
    text = engine.read_text(encoding="utf-8", errors="ignore")
    # Look for applicability/exception checks
    has_applicability = "applicability" in text.lower() or "is_applicable" in text.lower()
    has_exceptions = "exception" in text.lower() or "exempt" in text.lower()
    if not has_applicability and not has_exceptions:
        findings.append(Finding(
            "RULE-004", str(engine), 0, "WARN",
            "Engine has no visible applicability/exception handling. Some rules apply only to "
            "private companies (e.g. BOD-001) or only when there is share capital (e.g. SH-*).",
            "Add an applicability pre-check that runs BEFORE any rule fires; "
            "skip rules whose applicability predicate returns False.",
        ))
    # also check that scoring is done AFTER rule evaluation
    if "evaluate" in text and "score" in text:
        # ensure _calculate_score is called after evaluate() in main entry
        if text.find("_calculate_score") < text.find("def evaluate"):
            findings.append(Finding(
                "RULE-004", str(engine), 0, "WARN",
                "_calculate_score appears in source BEFORE evaluate(); verify that runtime order "
                "is correct (evaluate-then-score), not the reverse.",
            ))


def check_rule_005(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-005: missing evidence must not become confirmed statutory breach."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    if not engine.exists():
        return
    text = engine.read_text(encoding="utf-8", errors="ignore")
    # Heuristic: look for `if not <field>:` followed by NON_COMPLIANT
    pattern = re.compile(r"if\s+not\s+(\w+)\s*:[^\n]*\n\s*[^\n]*?NON_COMPLIANT", re.M)
    for m in pattern.finditer(text):
        lineno = text[:m.start()].count("\n") + 1
        findings.append(Finding(
            "RULE-005", str(engine), lineno, "WARN",
            f"`if not {m.group(1)}` followed by NON_COMPLIANT may treat missing evidence as a "
            f"breach: {m.group(0)[:120]}",
            "Distinguish: missing -> UNKNOWN (0 pts); verified absent -> VERIFIED_ABSENT (0 pts); "
            "confirmed violation -> NON_COMPLIANT (full pts).",
        ))


def check_rule_006(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-006: multiple rule registries -- check engine, canonical, API, seed."""
    registries = []
    candidates = [
        repo_root / "app" / "rule_engine" / "engine.py",
        repo_root / "canonical_architecture" / "statutory_rules.py",
        repo_root / "app" / "services" / "rules_service.py",
        repo_root / "app" / "models" / "rules.py",
        repo_root / "canonical_architecture" / "evaluator.py",
    ]
    for p in candidates:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        rule_ids = set(re.findall(r'["\']([A-Z]{2,4}-\d{3})["\']', text))
        if rule_ids:
            registries.append((p, rule_ids))
    if len(registries) < 2:
        findings.append(Finding(
            "RULE-006", "?", 0, "WARN",
            f"Only {len(registries)} rule corpus source(s) detected -- cannot check parity.",
        ))
        return
    # Compare every pair
    for i in range(len(registries)):
        for j in range(i + 1, len(registries)):
            (p1, r1), (p2, r2) = registries[i], registries[j]
            only_in_1 = r1 - r2
            only_in_2 = r2 - r1
            if only_in_1 or only_in_2:
                findings.append(Finding(
                    "RULE-006", f"{p1.name} <-> {p2.name}", 0, "WARN",
                    f"Rule ID sets differ. Only in {p1.name}: {sorted(only_in_1)[:10]}. "
                    f"Only in {p2.name}: {sorted(only_in_2)[:10]}.",
                    "Reconcile by making canonical_architecture/statutory_rules.py the single "
                    "source of truth; have the engine and API load from it.",
                ))


def check_rule_007(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-007: canonical rule registry authority -- explicit single source."""
    canonical = repo_root / "canonical_architecture" / "statutory_rules.py"
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    if not (canonical.exists() and engine.exists()):
        return
    canonical_text = canonical.read_text(encoding="utf-8", errors="ignore")
    engine_text = engine.read_text(encoding="utf-8", errors="ignore")
    # Check whether engine imports from canonical or hardcodes
    if "from canonical_architecture" in engine_text or "canonical_architecture.statutory_rules" in engine_text:
        findings.append(Finding(
            "RULE-007", str(engine), 0, "PASS",
            "Engine imports rule definitions from canonical_architecture.",
        ))
    else:
        findings.append(Finding(
            "RULE-007", str(engine), 0, "WARN",
            "Engine does not import rule definitions from canonical_architecture. Rule IDs and "
            "severity appear to be hardcoded in engine.py -- risk of drift.",
            "Replace hardcoded severity/score_impact in engine with a lookup into the canonical "
            "registry, so any future rule change requires updating one place.",
        ))


def check_rule_008(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-008: historical rule versions remain reproducible after rule changes."""
    # Heuristic: check for a RuleVersion table or rule_version_id column
    models_dir = repo_root / "app" / "models"
    if not models_dir.exists():
        findings.append(Finding("RULE-008", "?", 0, "WARN", "No app/models dir; cannot check."))
        return
    found_version_field = False
    for p in models_dir.rglob("*.py"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "rule_version" in text.lower() or "version_id" in text.lower() or "engine_version" in text.lower():
            found_version_field = True
            findings.append(Finding(
                "RULE-008", str(p), 0, "INFO",
                f"Found version field reference in {p.name}.",
            ))
            break
    if not found_version_field:
        findings.append(Finding(
            "RULE-008", str(models_dir), 0, "WARN",
            "No rule_version / engine_version column visible in models. Past evaluations cannot "
            "be reproduced against the rule definitions in force at the time of evaluation.",
            "Add `rule_engine_version: str` and `rule_registry_hash: str` columns to compliance_score; "
            "record both on every score write.",
        ))


def check_rule_009(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-009: score hash captures enough evidence + version info."""
    engine = repo_root / "app" / "rule_engine" / "engine.py"
    score_model = repo_root / "app" / "models" / "compliance.py"
    if not engine.exists():
        return
    text = engine.read_text(encoding="utf-8", errors="ignore")
    # look for hash / sha / digest / fingerprint
    has_hash = re.search(r"score_hash|score_fingerprint|sha256|hashlib\.|digest\(", text)
    if not has_hash:
        findings.append(Finding(
            "RULE-009", str(engine), 0, "FAIL",
            "No score hash computation in engine. Materially different evaluations cannot be "
            "distinguished.",
            "Compute `score_hash = sha256((rule_id,state,severity,rule_version) for each flag)`. "
            "Persist alongside the score so any flag change is detectable.",
        ))
        return
    # If hash exists, check what goes into it
    start = max(0, has_hash.start() - 800)
    end = min(len(text), has_hash.end() + 800)
    snippet = text[start:end]
    required_inputs = ["rule_id", "state", "severity"]
    missing_inputs = [k for k in required_inputs if k not in snippet]
    if missing_inputs:
        findings.append(Finding(
            "RULE-009", str(engine), 0, "WARN",
            f"Score hash exists but does not appear to include: {missing_inputs}. Materially "
            f"different evaluations may hash the same.",
            f"Add {missing_inputs} to the hash input.",
        ))


def check_rule_010(repo_root: Path, findings: list[Finding]) -> None:
    """RULE-010: statutory references -- flag TBD/RECONCILE provision_status."""
    canonical = repo_root / "canonical_architecture" / "statutory_rules.py"
    if not canonical.exists():
        return
    text = canonical.read_text(encoding="utf-8", errors="ignore")
    # Find TBD or RECONCILE in provision_status or provision field
    tbd_lines = [i + 1 for i, ln in enumerate(text.splitlines())
                 if "TBD" in ln or "RECONCILE" in ln or '"provision": "TBD"' in ln]
    if tbd_lines:
        findings.append(Finding(
            "RULE-010", str(canonical), tbd_lines[0], "WARN",
            f"{len(tbd_lines)} rule(s) have provision_status = RECONCILE or provision = TBD. "
            f"Statutory references are not yet validated against actual law. "
            f"First occurrence at line {tbd_lines[0]}.",
            "Engage qualified Bangladesh corporate counsel to validate each `law` field against "
            "the current Companies Act 1994 (and amendments). Mark each as PROVISION_VERIFIED "
            "only after review.",
        ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repo root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/rule_integrity_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Rule Integrity Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_rule_001(repo_root, findings)
    check_rule_002(repo_root, findings)
    check_rule_003(repo_root, findings)
    check_rule_004(repo_root, findings)
    check_rule_005(repo_root, findings)
    check_rule_006(repo_root, findings)
    check_rule_007(repo_root, findings)
    check_rule_008(repo_root, findings)
    check_rule_009(repo_root, findings)
    check_rule_010(repo_root, findings)

    by_check: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_check[f.check_id].append(f)

    print(f"=== SUMMARY ===")
    for cid in sorted(by_check):
        rows = by_check[cid]
        fail = sum(1 for r in rows if r.severity == "FAIL")
        warn = sum(1 for r in rows if r.severity == "WARN")
        info = sum(1 for r in rows if r.severity == "INFO")
        print(f"  {cid}: FAIL={fail} WARN={warn} INFO={info}")
    print()

    for cid in sorted(by_check):
        print(f"--- {cid} ---")
        for r in by_check[cid]:
            marker = {"FAIL": "XX", "WARN": "!!", "INFO": "--", "PASS": "OK"}.get(r.severity, "??")
            print(f"[{marker}] {r.file}:{r.line}  {r.detail}")
            if r.suggested_fix:
                print(f"      -> FIX: {r.suggested_fix}")
        print()

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo": str(repo_root),
        "findings": [asdict(f) for f in findings],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"JSON report: {args.output}")

    fail_total = sum(1 for f in findings if f.severity == "FAIL")
    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())