#!/usr/bin/env python3
"""
NEUM LEX COUNSEL
Canonical Legal Compliance Corpus Builder + Repository Forensic Auditor

PURPOSE
-------
1. Discover ALL rule IDs actually present in the repository.
2. Discover statutory references, sections, rescue IDs and R-invariants.
3. Discover rule IDs mentioned in migrations/history/tests/docs.
4. Detect duplicate/case-collision files.
5. Detect Python package/module collisions.
6. Run Git integrity checks.
7. Build a NON-AUTHORITATIVE canonical inventory.

IMPORTANT
---------
This script NEVER invents a statutory section.

Every discovered rule starts with:

    provision_status = "RECONCILE"

A rule may become VERIFIED only after a separate legal-source
reconciliation process.

The script intentionally fails the production gate when fewer than
75 distinct statutory/product rule IDs are discovered. It does NOT
manufacture placeholder rules to reach 75.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.cwd().resolve()

OUTPUT_DIR = ROOT / "canonical_architecture" / "generated"

MIN_EXPECTED_RULES = 75

RULE_RE = re.compile(
    r"\b("
    r"INC|AUD|AGM|AR|DIR|SH|TR|REG|OFF|CAP|CHG|"
    r"TAX|VAT|DEF|ESC|STR|TL|LBR|BNK|"
    r"ENV|LIC|IP|SEC|LAB|INS|IMP|EXP"
    r")-\d{3}\b",
    re.IGNORECASE,
)

RESCUE_RE = re.compile(
    r"\b[A-Z][A-Z0-9_]*-RESCUE-\d{3}\b"
)

INVARIANT_RE = re.compile(
    r"\bR-\d{3}\b"
)

SECTION_RE = re.compile(
    r"\b(?:section|sec\.?|§)\s*"
    r"(\d+[A-Za-z]?(?:\(\d+\))?(?:\([a-z]+\))?)",
    re.IGNORECASE,
)

SOURCE_EXTENSIONS = {
    ".py", ".pyi", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".md", ".txt", ".sql",
}

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


def run(
    *args: str,
    check: bool = False,
) -> tuple[int, str, str]:
    proc = subprocess.run(
        list(args),
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding='utf-8',
        errors='ignore',
    )

    if check and proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n"
            f"{proc.stdout}\n{proc.stderr}"
        )

    return proc.returncode, proc.stdout, proc.stderr


def git(*args: str, check: bool = False) -> tuple[int, str, str]:
    return run("git", *args, check=check)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


def iter_source_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue

        yield path


def collect_rule_mentions() -> dict[str, dict[str, Any]]:
    rules: dict[str, dict[str, Any]] = {}

    for path in iter_source_files():
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            continue

        found = {
            m.group(0).upper()
            for m in RULE_RE.finditer(text)
        }

        sections = sorted(
            {
                m.group(1)
                for m in SECTION_RE.finditer(text)
            }
        )

        rescues = sorted(
            {
                m.group(0).upper()
                for m in RESCUE_RE.finditer(text)
            }
        )

        invariants = sorted(
            {
                m.group(0).upper()
                for m in INVARIANT_RE.finditer(text)
            }
        )

        for rule_id in found:
            entry = rules.setdefault(
                rule_id,
                {
                    "rule_id": rule_id,
                    "mentions": [],
                    "candidate_sections": set(),
                    "rescue_ids": set(),
                    "invariants": set(),
                },
            )

            entry["mentions"].append(rel(path))
            entry["candidate_sections"].update(sections)
            entry["rescue_ids"].update(rescues)
            entry["invariants"].update(invariants)

    for entry in rules.values():
        entry["mentions"] = sorted(set(entry["mentions"]))
        entry["candidate_sections"] = sorted(
            entry["candidate_sections"]
        )
        entry["rescue_ids"] = sorted(
            entry["rescue_ids"]
        )
        entry["invariants"] = sorted(
            entry["invariants"]
        )

    return dict(sorted(rules.items()))


def collect_git_rule_history(rule_ids: list[str]) -> dict[str, list[str]]:
    """
    Determine which rule IDs appear in Git history.

    This is useful for finding rules that were removed from current
    source but still exist historically.
    """
    history: dict[str, list[str]] = defaultdict(list)

    rc, commits, _ = git(
        "rev-list",
        "--all",
        "--max-count=5000",
    )

    if rc != 0:
        return {}

    commit_list = commits.splitlines()

    for rule_id in rule_ids:
        rc, out, _ = git(
            "log",
            "--all",
            "--oneline",
            "--decorate=short",
            "-S",
            rule_id,
            "--",
        )

        if rc == 0 and out.strip():
            history[rule_id] = out.splitlines()

    return dict(history)


def collect_all_historical_rule_ids() -> dict[str, list[str]]:
    """
    Search Git's complete reachable commit history for rule IDs.

    This catches rules removed from the current working tree.
    """
    rc, out, err = git(
        "grep",
        "-I",
        "-h",
        "-E",
        r"(INC|AUD|AGM|AR|DIR|SH|TR|REG|OFF|CAP|CHG|TAX|VAT|"
        r"DEF|ESC|STR|TL|LBR|BNK|ENV|LIC|IP|SEC|LAB|INS|IMP|EXP)-[0-9]{3}",
        "$(git rev-list --all)",
    )

    # The above cannot safely expand shell syntax because subprocess
    # does not invoke a shell. Use git log instead.
    del rc, out, err

    rc, commits, _ = git("rev-list", "--all")

    if rc != 0:
        return {}

    historical: dict[str, list[str]] = defaultdict(list)

    for commit in commits.splitlines():
        rc, text, _ = git(
            "show",
            "--format=",
            "--no-ext-diff",
            "--unified=0",
            commit,
        )

        if rc != 0:
            continue

        if text is None: continue
    if not text: continue
    for match in RULE_RE.finditer(text):
            historical[
                match.group(0).upper()
            ].append(commit)

    return {
        rule_id: sorted(set(commits))
        for rule_id, commits in historical.items()
    }


def git_state() -> dict[str, Any]:
    result: dict[str, Any] = {}

    _, result["status"], _ = git("status", "--short", "--branch")
    _, result["branch"], _ = git("branch", "--show-current")
    _, result["head"], _ = git("rev-parse", "HEAD")
    _, result["origin_head"], _ = git(
        "rev-parse",
        "origin/audit/legal-compliance",
    )

    checks = {}

    for name, args in {
        "fsck_full": ("fsck", "--full"),
        "fsck_full_no_reflogs": (
            "fsck",
            "--full",
            "--no-reflogs",
        ),
        "index_refresh": (
            "update-index",
            "--refresh",
        ),
        "unmerged_files": (
            "diff",
            "--name-only",
            "--diff-filter=U",
        ),
        "untracked": (
            "ls-files",
            "--others",
            "--exclude-standard",
        ),
    }.items():
        rc, stdout, stderr = git(*args)

        checks[name] = {
            "return_code": rc,
            "stdout": stdout,
            "stderr": stderr,
        }

    result["checks"] = checks

    return result


def duplicate_case_paths() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        groups[rel(path).lower()].append(rel(path))

    return {
        key: sorted(values)
        for key, values in groups.items()
        if len(values) > 1
    }


def python_module_collisions() -> dict[str, list[str]]:
    """
    Detect files that can create ambiguous Python imports on Windows,
    e.g.:

        app/worker.py
        app/worker/__init__.py

    """
    collisions: dict[str, list[str]] = defaultdict(list)

    for path in ROOT.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue

        relative = path.relative_to(ROOT)
        parts = list(relative.parts)

        if parts[-1] == "__init__.py":
            module = ".".join(parts[:-1])
        else:
            module = ".".join(parts)[:-3]

        collisions[module.lower()].append(rel(path))

    return {
        module: sorted(paths)
        for module, paths in collisions.items()
        if len(paths) > 1
    }


def inventory_git_files() -> list[str]:
    rc, stdout, _ = git(
        "ls-files",
        "-z",
    )

    if rc != 0:
        return []

    return sorted(
        p for p in stdout.split("\0")
        if p
    )


def build_matrix(rules: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build a machine-readable canonical skeleton.

    No legal section is frozen here.
    """
    matrix = []

    for rule_id, raw in rules.items():
        prefix = rule_id.split("-")[0]

        matrix.append(
            {
                "rule_id": rule_id,

                "domain": prefix,

                "legal_source": {
                    "statute": None,
                    "provision": None,
                    "subsection": None,
                    "rule_or_schedule": None,
                    "effective_from": None,
                    "effective_to": None,
                    "source_url": None,
                    "source_hash": None,
                },

                "provision_status": "RECONCILE",

                "classification": {
                    "provision_type": None,
                    "obligation_type": None,
                    "mandatory": None,
                },

                "requirement": {
                    "title": None,
                    "description": None,
                    "obligated_party": None,
                },

                "applicability": {
                    "entity_types": [],
                    "conditions": [],
                    "exclusions": [],
                    "unknown_conditions": [],
                },

                "exceptions": [],

                "evidence": {
                    "required": [],
                    "verification_method": None,
                },

                "evaluation_states": [
                    "COMPLIANT",
                    "NON_COMPLIANT",
                    "UNKNOWN",
                    "NOT_APPLICABLE",
                    "CONDITIONAL",
                    "CONTRADICTORY",
                ],

                "severity": None,
                "score_impact": None,

                "rescue": {
                    "rescue_id": (
                        f"{prefix}-RESCUE-"
                        f"{rule_id.split('-')[1]}"
                    ),
                    "trigger_states": [],
                    "objective": None,
                    "prerequisites": [],
                    "steps": [],
                    "dependencies": [],
                    "authority": None,
                    "required_documents": [],
                    "filing_required": None,
                    "deadline_basis": None,
                    "verification_required": True,
                    "closure_condition": None,
                },

                "service": {
                    "service_id": None,
                    "human_approval_required": True,
                },

                "notifications": [],

                "re_evaluation": {
                    "triggers": [
                        "NEW_EVIDENCE",
                        "FILING_ACKNOWLEDGEMENT",
                        "AUTHORITY_VERIFICATION",
                    ],
                    "targeted_only": True,
                },

                "product_invariants": sorted(
                    raw["invariants"]
                ),

                "repository_evidence": {
                    "current_mentions": raw["mentions"],
                    "candidate_sections": raw[
                        "candidate_sections"
                    ],
                    "candidate_rescues": raw[
                        "rescue_ids"
                    ],
                },
            }
        )

    return matrix


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
            default=list,
        ),
        encoding="utf-8",
    )


def write_csv(path: Path, matrix: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "rule_id",
        "domain",
        "provision_status",
        "statute",
        "provision",
        "requirement",
        "rescue_id",
        "service_id",
        "severity",
        "score_impact",
        "invariants",
        "source_files",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
        )

        writer.writeheader()

        for item in matrix:
            writer.writerow(
                {
                    "rule_id": item["rule_id"],
                    "domain": item["domain"],
                    "provision_status": item[
                        "provision_status"
                    ],
                    "statute": (
                        item["legal_source"]["statute"]
                        or ""
                    ),
                    "provision": (
                        item["legal_source"]["provision"]
                        or ""
                    ),
                    "requirement": (
                        item["requirement"]["title"]
                        or ""
                    ),
                    "rescue_id": item["rescue"][
                        "rescue_id"
                    ],
                    "service_id": (
                        item["service"]["service_id"]
                        or ""
                    ),
                    "severity": item["severity"] or "",
                    "score_impact": (
                        item["score_impact"]
                        if item["score_impact"] is not None
                        else ""
                    ),
                    "invariants": ",".join(
                        item["product_invariants"]
                    ),
                    "source_files": "|".join(
                        item["repository_evidence"][
                            "current_mentions"
                        ]
                    ),
                }
            )


def main() -> int:
    print("=" * 80)
    print("NLC — CANONICAL LEGAL COMPLIANCE CORPUS BUILDER")
    print("=" * 80)

    print(f"ROOT: {ROOT}")

    if not (ROOT / ".git").exists():
        print("FATAL: .git not found.")
        print(
            "Run this script from "
            "/f/NLC_RECOVERY_CLONES/nlc_platform_clean"
        )
        return 2

    print("\n=== GIT STATE ===")

    git_info = git_state()

    print(
        "BRANCH:",
        git_info.get("branch", "").strip(),
    )

    print(
        "HEAD:",
        git_info.get("head", "").strip(),
    )

    print("\n=== RULE DISCOVERY ===")

    rules = collect_rule_mentions()

    print(
        "CURRENT DISTINCT RULE IDS:",
        len(rules),
    )

    for rule_id in rules:
        print(" ", rule_id)

    historical = collect_all_historical_rule_ids()

    historical_only = sorted(
        set(historical) - set(rules)
    )

    print(
        "\nHISTORICAL RULE IDS NOT CURRENTLY PRESENT:",
        len(historical_only),
    )

    for rule_id in historical_only:
        print(" ", rule_id)

    print("\n=== PYTHON MODULE COLLISIONS ===")

    module_collisions = python_module_collisions()

    if module_collisions:
        for module, paths in module_collisions.items():
            print("COLLISION:", module)
            for path in paths:
                print("   ", path)
    else:
        print("NONE")

    print("\n=== CASE-COLLISION FILES ===")

    case_collisions = duplicate_case_paths()

    if case_collisions:
        for key, paths in case_collisions.items():
            print("CASE COLLISION:", key)
            for path in paths:
                print("   ", path)
    else:
        print("NONE")

    print("\n=== GIT INTEGRITY ===")

    for name, result in git_info["checks"].items():
        print(
            f"{name}: exit={result['return_code']}"
        )

        output = (
            result["stdout"] + result["stderr"]
        ).strip()

        if output:
            print(output[:5000])

    print("\n=== BUILD CANONICAL SKELETON ===")

    matrix = build_matrix(rules)

    write_json(
        OUTPUT_DIR / "canonical_rule_inventory.json",
        matrix,
    )

    write_csv(
        OUTPUT_DIR / "canonical_rule_inventory.csv",
        matrix,
    )

    write_json(
        OUTPUT_DIR / "repository_forensic_report.json",
        {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),

            "repository_root": str(ROOT),

            "git": git_info,

            "current_rule_count": len(rules),

            "current_rule_ids": sorted(rules),

            "historical_only_rule_ids": historical_only,

            "historical_rule_commits": historical,

            "python_module_collisions":
                module_collisions,

            "case_collisions":
                case_collisions,

            "minimum_expected_rules":
                MIN_EXPECTED_RULES,

            "production_ready":
                (
                    len(rules) >= MIN_EXPECTED_RULES
                    and not module_collisions
                    and not case_collisions
                ),
        },
    )

    print(
        "\nGenerated:",
        rel(
            OUTPUT_DIR /
            "canonical_rule_inventory.json"
        ),
    )

    print(
        "Generated:",
        rel(
            OUTPUT_DIR /
            "canonical_rule_inventory.csv"
        ),
    )

    print(
        "Generated:",
        rel(
            OUTPUT_DIR /
            "repository_forensic_report.json"
        ),
    )

    print("\n=== PRODUCTION GATE ===")

    if len(rules) < MIN_EXPECTED_RULES:
        print(
            f"FAIL: only {len(rules)} current rules discovered."
        )
        print(
            f"Minimum target is {MIN_EXPECTED_RULES}."
        )
        print(
            "DO NOT manufacture missing rules."
        )
        print(
            "Recover/reconcile them from migrations,"
            " history, legal source inventory, and"
            " applicable-domain analysis."
        )
        return 10

    if module_collisions:
        print(
            "FAIL: Python module/import collisions detected."
        )
        return 11

    if case_collisions:
        print(
            "FAIL: case-sensitive path collisions detected."
        )
        return 12

    print("PASS: repository-derived rule corpus >= 75.")
    print(
        "NOTE: legal provisions are still RECONCILE "
        "until independently verified."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
