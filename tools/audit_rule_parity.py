#!/usr/bin/env python3
"""NLC Canonical Rule Parity Audit — reads from actual sources, not grep."""
import ast
import os
import re
import sys
from pathlib import Path


def get_engine_rules():
    """AST-parse engine.py for rule_id= keyword arguments."""
    source = Path("app/rule_engine/engine.py").read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword):
            if node.arg == "rule_id" and isinstance(node.value, ast.Constant):
                v = node.value.value
                if isinstance(v, str) and re.match(r'^[A-Z]{2,12}-\d{3}$', v):
                    ids.add(v)
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "rule_id":
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        v = node.value.value
                        if re.match(r'^[A-Z]{2,12}-\d{3}$', v):
                            ids.add(v)
    return ids


def get_seed_rules():
    """AST-parse seed_rules.py for rule_id in dict literals."""
    p = Path("scripts/seed_rules.py")
    if not p.exists():
        return set()
    tree = ast.parse(p.read_text(encoding="utf-8", errors="ignore"))
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values, strict=False):
                if isinstance(k, ast.Constant) and k.value == "rule_id":
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        ids.add(v.value)
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
        async def q():
            conn = await asyncpg.connect(db_url)
            rows = await conn.fetch("SELECT rule_id FROM legal_rules WHERE is_active = true")
            await conn.close()
            return {r["rule_id"] for r in rows}
        return asyncio.run(q())
    except Exception as e:
        print(f"  DB: {e}")
        return None


def get_api_rules():
    base = os.environ.get("API_URL", "https://nlc-platform.onrender.com")
    try:
        import json
        import urllib.request
        resp = urllib.request.urlopen(f"{base}/api/v1/rules")
        return {r["rule_id"] for r in json.loads(resp.read())}
    except Exception as e:
        print(f"  API: {e}")
        return None


def main():
    use_db = "--no-db" not in sys.argv
    print(f"\n{'='*70}")
    print(f"  NLC — Canonical Rule Parity Audit")
    print(f"{'='*70}")

    engine = get_engine_rules()
    seed = get_seed_rules()
    print(f"\n  [1] ENGINE (AST parse): {len(engine)} rules")
    print(f"  [2] SEED   (AST parse): {len(seed)} rules")

    db = get_db_rules() if use_db else None
    if db is not None:
        print(f"  [3] DB     (SELECT):    {len(db)} active rules")
    api = get_api_rules()
    if api is not None:
        print(f"  [4] API    (HTTP GET):  {len(api)} rules")

    sources = {"ENGINE": engine, "SEED": seed}
    if db is not None:
        sources["DB"] = db
    if api is not None:
        sources["API"] = api

    all_rules = set()
    for rs in sources.values():
        all_rules |= rs

    common = all_rules.copy()
    for rs in sources.values():
        common &= rs

    print(f"\n{'='*70}")
    print(f"  PARITY: {len(common)}/{len(all_rules)} rules in all sources")
    print(f"{'='*70}")

    if len(common) == len(all_rules):
        print(f"\n  ✓ ALL SOURCES AGREE\n")
    else:
        print(f"\n  ✗ PARITY GAPS:\n")
        for name, rs in sources.items():
            missing = all_rules - rs
            extra = rs - common
            if missing:
                print(f"  {name} MISSING: {sorted(missing)}")
            if extra:
                print(f"  {name} EXTRA:  {sorted(extra)}")
        print()

    print(f"  {'Rule ID':<12} |", end="")
    for n in sources:
        print(f" {n:<8}|", end="")
    print()
    print(f"  {'-'*12}|" + "|".join(["-"*9+"|" for _ in sources]))
    for r in sorted(all_rules):
        print(f"  {r:<12} |", end="")
        for _n, rs in sources.items():
            print(f"  {'Y' if r in rs else '-':<7}|", end="")
        print()

    print(f"\n  Engine={len(engine)}  Seed={len(seed)}", end="")
    if db is not None:
        print(f"  DB={len(db)}", end="")
    if api is not None:
        print(f"  API={len(api)}", end="")
    print()
    return 0 if len(common) == len(all_rules) else 1


if __name__ == "__main__":
    sys.exit(main())
