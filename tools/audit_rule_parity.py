#!/usr/bin/env python3
"""Canonical rule registry parity audit.

Static CI mode compares the engine and full seed definitions. Live mode also
compares the active database inventory and API IDs. The DB inventory comes
from a least-privilege audit view, not the separate independently-VERIFIED
legal-release view. Missing requested sources are audit failures.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

DB_PARITY_FIELDS = (
    "rule_name",
    "rule_type",
    "statutory_basis",
    "description",
    "rule_condition",
    "default_severity",
    "score_impact",
    "revenue_tier",
    "is_black_override",
)
KNOWN_INACTIVE_LEGACY_RULE_IDS = {"INC-002"}


def get_engine_rules():
    source = Path("app/rule_engine/engine.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    tree = ast.parse(source)
    ids = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.keyword)
            and node.arg == "rule_id"
            and isinstance(node.value, ast.Constant)
        ):
            value = node.value.value
            if isinstance(value, str) and re.match(r"^[A-Z]{2,12}-\d{3}$", value):
                ids.add(value)
        if (
            isinstance(node, ast.Tuple)
            and node.elts
            and isinstance(node.elts[0], ast.Constant)
        ):
            value = node.elts[0].value
            if isinstance(value, str) and re.match(r"^[A-Z]{2,12}-\d{3}$", value):
                ids.add(value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "rule_id"
                    and isinstance(node.value, ast.Constant)
                ):
                    value = node.value.value
                    if isinstance(value, str) and re.match(r"^[A-Z]{2,12}-\d{3}$", value):
                        ids.add(value)
    return ids


def get_seed_rule_definitions():
    """Read the literal ILRMF_RULES source as data without importing its writer."""
    path = Path("scripts/seed_rules.py")
    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "ILRMF_RULES"
        ):
            rows = ast.literal_eval(node.value)
            if not isinstance(rows, list):
                raise ValueError("ILRMF_RULES must be a literal list")
            definitions = {}
            for row in rows:
                if not isinstance(row, dict) or not isinstance(row.get("rule_id"), str):
                    raise ValueError("ILRMF_RULES contains a malformed definition")
                rule_id = row["rule_id"]
                if rule_id in definitions:
                    raise ValueError(f"Duplicate seed rule ID: {rule_id}")
                definitions[rule_id] = row
            return definitions
    raise ValueError("ILRMF_RULES literal assignment was not found")


def get_seed_rules():
    return set(get_seed_rule_definitions())


def _decode_jsonb(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def get_db_rule_inventory():
    """Read the full safe audit projection; never use verified-only IDs as catalogue IDs."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "dummy" in db_url:
        return None
    try:
        import asyncio
        import asyncpg

        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        if db_url.startswith("postgres://"):
            db_url = "postgresql://" + db_url[len("postgres://"):]

        async def query():
            connection = await asyncpg.connect(db_url)
            try:
                rows = await connection.fetch(
                    """
                    SELECT
                        rule_id, rule_name, rule_type, statutory_basis, description,
                        rule_condition, default_severity, score_impact, revenue_tier,
                        is_black_override, rule_version, is_active, verification_status
                    FROM audit.legal_rule_registry_inventory
                    ORDER BY rule_id
                    """
                )
                inventory = {}
                for row in rows:
                    item = dict(row)
                    item["rule_condition"] = _decode_jsonb(item["rule_condition"])
                    rule_id = item["rule_id"]
                    if rule_id in inventory:
                        raise ValueError(f"Duplicate database rule ID: {rule_id}")
                    inventory[rule_id] = item
                return inventory

            finally:
                await connection.close()

        return asyncio.run(query())
    except Exception as exc:
        print(f"  DB ERROR: {exc}")
        return None


def get_db_rules():
    """Compatibility helper returning active catalogue IDs."""
    inventory = get_db_rule_inventory()
    if inventory is None:
        return None
    return {
        rule_id
        for rule_id, row in inventory.items()
        if row.get("is_active") is True
    }


def get_api_rules():
    base = os.environ.get("API_URL", "").rstrip("/")
    if not base:
        print("  API SKIPPED: set API_URL only for post-deploy live API verification")
        return None
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"{base}/api/v1/rules?is_active=true", timeout=15
        ) as response:
            payload = json.loads(response.read())
        return {row["rule_id"] for row in payload}
    except Exception as exc:
        print(f"  API ERROR: {exc}")
        return None


def _canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def _sha256(value):
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def compare_database_metadata(seed_definitions, inventory):
    mismatches = []
    active = {
        rule_id: row
        for rule_id, row in inventory.items()
        if row.get("is_active") is True
    }
    inactive_ids = {
        rule_id
        for rule_id, row in inventory.items()
        if row.get("is_active") is not True
    }

    for rule_id in sorted(set(seed_definitions) & set(active)):
        seed = seed_definitions[rule_id]
        row = active[rule_id]
        for field in DB_PARITY_FIELDS:
            if _canonical_json(seed.get(field)) != _canonical_json(row.get(field)):
                mismatches.append({
                    "rule_id": rule_id,
                    "field": field,
                    "seed": seed.get(field),
                    "database": row.get(field),
                })

    if inactive_ids != KNOWN_INACTIVE_LEGACY_RULE_IDS:
        mismatches.append({
            "rule_id": "(inactive_inventory)",
            "field": "inactive_legacy_rule_ids",
            "seed": sorted(KNOWN_INACTIVE_LEGACY_RULE_IDS),
            "database": sorted(inactive_ids),
        })

    for rule_id, row in sorted(inventory.items()):
        if (
            row.get("default_severity") != "NOT_EVALUATED"
            or row.get("score_impact") != 0
            or row.get("is_black_override") is not False
        ):
            mismatches.append({
                "rule_id": rule_id,
                "field": "fail_closed_database_state",
                "expected": {
                    "default_severity": "NOT_EVALUATED",
                    "score_impact": 0,
                    "is_black_override": False,
                },
                "database": {
                    "default_severity": row.get("default_severity"),
                    "score_impact": row.get("score_impact"),
                    "is_black_override": row.get("is_black_override"),
                },
            })

    seed_projection = {
        rule_id: {field: seed_definitions[rule_id].get(field) for field in DB_PARITY_FIELDS}
        for rule_id in sorted(seed_definitions)
    }
    database_projection = {
        rule_id: {field: active[rule_id].get(field) for field in DB_PARITY_FIELDS}
        for rule_id in sorted(active)
    }
    return {
        "mismatches": mismatches,
        "active_count": len(active),
        "inactive_ids": sorted(inactive_ids),
        "seed_manifest_sha256": _sha256(seed_projection),
        "database_active_manifest_sha256": _sha256(database_projection),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true", help="exclude live database; static audit only")
    parser.add_argument("--no-api", action="store_true", help="exclude live API; static audit only")
    parser.add_argument("--report-json", help="write a machine-readable audit report to this path")
    args = parser.parse_args()

    engine = get_engine_rules()
    seed_definitions = get_seed_rule_definitions()
    seed = set(seed_definitions)
    seed_manifest_sha256 = _sha256({
        rule_id: seed_definitions[rule_id] for rule_id in sorted(seed_definitions)
    })
    print(f"ENGINE (AST): {len(engine)} rules")
    print(f"SEED   (AST): {len(seed)} rules")
    print(f"SEED_MANIFEST_SHA256: {seed_manifest_sha256}")

    sources = {"ENGINE": engine, "SEED": seed}
    unavailable = []
    db_inventory = None
    metadata_result = None

    if not args.no_db:
        db_inventory = get_db_rule_inventory()
        if db_inventory is None:
            unavailable.append("DB")
        else:
            db_ids = {
                rule_id for rule_id, row in db_inventory.items()
                if row.get("is_active") is True
            }
            sources["DB"] = db_ids
            print(
                f"DB     (live): {len(db_ids)} active / "
                f"{len(db_inventory)} total catalogue rows"
            )
            metadata_result = compare_database_metadata(seed_definitions, db_inventory)
            print(
                "DB_ACTIVE_MANIFEST_SHA256: "
                f"{metadata_result['database_active_manifest_sha256']}"
            )
            if metadata_result["mismatches"]:
                print(
                    "DB METADATA MISMATCHES: "
                    f"{len(metadata_result['mismatches'])}"
                )
                for mismatch in metadata_result["mismatches"][:100]:
                    print(f"  {json.dumps(mismatch, ensure_ascii=False, sort_keys=True)}")
            else:
                print("DB FULL-DEFINITION PARITY: PASSED")

    if not args.no_api:
        api = get_api_rules()
        if api is None:
            unavailable.append("API")
        else:
            sources["API"] = api
            print(f"API    (live): {len(api)} rules")

    all_rules = set().union(*sources.values())
    common = set.intersection(*(set(rule_ids) for rule_ids in sources.values()))
    print(f"PARITY: {len(common)}/{len(all_rules)} rules shared by {', '.join(sources)}")

    for name, rule_ids in sources.items():
        missing = all_rules - rule_ids
        if missing:
            print(f"{name} MISSING: {sorted(missing)}")

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "commit_sha": os.environ.get("GITHUB_SHA"),
        "sources": {name: sorted(ids) for name, ids in sources.items()},
        "unavailable_sources": unavailable,
        "seed_manifest_sha256": seed_manifest_sha256,
        "database_metadata": metadata_result,
        "id_parity_passed": len(common) == len(all_rules),
        "metadata_parity_passed": (
            metadata_result is None or not metadata_result["mismatches"]
        ),
    }
    if args.report_json:
        report_path = Path(args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"PARITY_REPORT: {report_path}")

    if unavailable:
        print(f"AUDIT INCOMPLETE: required source(s) unavailable: {', '.join(unavailable)}")
        return 2
    if len(common) != len(all_rules):
        print("PARITY FAILED")
        return 1
    if metadata_result is not None and metadata_result["mismatches"]:
        print("FULL-DEFINITION PARITY FAILED")
        return 1

    audit_kind = "STATIC ENGINE/SEED" if args.no_db and args.no_api else "MULTI-SOURCE"
    print(f"{audit_kind} PARITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
