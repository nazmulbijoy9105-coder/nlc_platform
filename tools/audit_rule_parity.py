#!/usr/bin/env python3
"""Canonical rule parity audit.

Static CI mode compares the engine and seed registry only. Live DB/API sources
are included when requested and are mandatory if selected: an unavailable
source is an audit failure, never silently removed from the comparison.
"""
import argparse
import ast
import os
import re
import sys
from pathlib import Path


def get_engine_rules():
    source = Path("app/rule_engine/engine.py").read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "rule_id" and isinstance(node.value, ast.Constant):
            value = node.value.value
            if isinstance(value, str) and re.match(r"^[A-Z]{2,12}-\d{3}$", value):
                ids.add(value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "rule_id" and isinstance(node.value, ast.Constant):
                    value = node.value.value
                    if isinstance(value, str) and re.match(r"^[A-Z]{2,12}-\d{3}$", value):
                        ids.add(value)
    return ids


def get_seed_rules():
    path = Path("scripts/seed_rules.py")
    if not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "rule_id" and isinstance(value, ast.Constant):
                    ids.add(value.value)
    return ids


def get_db_rules():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or "dummy" in db_url:
        return None
    try:
        import asyncio
        import asyncpg
        if "+asyncpg" in db_url:
            db_url = db_url.replace("+asyncpg", "")
        async def query():
            connection = await asyncpg.connect(db_url)
            try:
                rows = await connection.fetch("SELECT rule_id FROM legal_rules WHERE is_active = true")
                return {row["rule_id"] for row in rows}
            finally:
                await connection.close()
        return asyncio.run(query())
    except Exception as exc:
        print(f"  DB ERROR: {exc}")
        return None


def get_api_rules():
    base = os.environ.get("API_URL", "https://nlc-platform.onrender.com")
    try:
        import json
        import urllib.request
        with urllib.request.urlopen(f"{base}/api/v1/rules?is_active=true", timeout=15) as response:
            payload = json.loads(response.read())
        return {row["rule_id"] for row in payload}
    except Exception as exc:
        print(f"  API ERROR: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true", help="exclude live database; static audit only")
    parser.add_argument("--no-api", action="store_true", help="exclude live API; static audit only")
    args = parser.parse_args()

    engine = get_engine_rules()
    seed = get_seed_rules()
    print(f"ENGINE (AST): {len(engine)} rules")
    print(f"SEED   (AST): {len(seed)} rules")

    sources = {"ENGINE": engine, "SEED": seed}
    unavailable = []

    if not args.no_db:
        db = get_db_rules()
        if db is None:
            unavailable.append("DB")
        else:
            sources["DB"] = db
            print(f"DB     (live): {len(db)} rules")

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

    if unavailable:
        print(f"AUDIT INCOMPLETE: required source(s) unavailable: {', '.join(unavailable)}")
        return 2
    if len(common) != len(all_rules):
        print("PARITY FAILED")
        return 1

    audit_kind = "STATIC ENGINE/SEED" if args.no_db and args.no_api else "MULTI-SOURCE"
    print(f"{audit_kind} PARITY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
