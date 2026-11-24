"""Pin the alembic MIGRATION_ONLY_TABLES allowlist against repo source.

`alembic check` / autogenerate must never propose dropping tables that
migrations create without an ORM model (quarantine snapshots, RLS key
material, append-only audit ledgers, verification event logs). env.py
filters those via MIGRATION_ONLY_TABLES; this test recomputes the
migration-only set directly from the migrations and models source and
fails when the allowlist drifts from reality.

Contract (all DB-free):
  1. every table created by alembic/versions/*.py and absent from
     app.models Base.metadata is exactly MIGRATION_ONLY_TABLES;
  2. the allowlist never names a modeled table;
  3. every modeled table is created by some migration;
  4. include_object() from env.py actually filters allowlisted reflected
     tables and keeps everything else visible to the diff.

Source-derived detection covers:
  - op.create_table("<literal>", ...) and op.create_table(<CONSTANT>, ...)
    with the constant resolved from the same migration module
  - raw CREATE TABLE / CREATE TABLE IF NOT EXISTS statements in
    op.execute() strings (f-string templates with interpolated names
    cannot be detected statically and will fail loudly if they introduce
    a new model-free table — recompute the allowlist by hand then).
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENV_PY = REPO / "alembic" / "env.py"
VERSIONS = REPO / "alembic" / "versions"

sys.path.insert(0, str(REPO))


# ── env.py: allowlist + include_object behavior ───────────────────────
def _load_env_module_contract() -> tuple[frozenset[str], object]:
    src = ENV_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)

    allowlist: frozenset[str] | None = None
    include_object_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            getattr(t, "id", None) == "MIGRATION_ONLY_TABLES" for t in node.targets
        ):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", "") == "frozenset":
                value = value.args[0]
            allowlist = frozenset(ast.literal_eval(value))
        if isinstance(node, (ast.FunctionDef,)) and node.name == "include_object":
            include_object_node = node
    if allowlist is None or not isinstance(allowlist, frozenset):
        raise AssertionError("MIGRATION_ONLY_TABLES frozenset not found in alembic/env.py")
    if include_object_node is None:
        raise AssertionError("include_object() not found in alembic/env.py")

    segment = ast.get_source_segment(src, include_object_node)
    namespace: dict[str, object] = {"MIGRATION_ONLY_TABLES": allowlist}
    exec(compile(segment, str(ENV_PY), "exec"), namespace)
    return allowlist, namespace["include_object"]


ALLOWLIST, _INCLUDE_OBJECT = _load_env_module_contract()


# ── migrations: tables created by op.create_table / raw CREATE TABLE ──
def _created_tables_from_migrations() -> tuple[dict[str, list[str]], list[str], list[str]]:
    op_names: dict[str, list[str]] = {}
    raw_names: set[str] = set()
    unresolved: list[str] = []

    raw_create_re = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
        r"(?:\"?[A-Za-z0-9_]+\"?\.)?\"?([A-Za-z0-9_]+)\"?",
        re.IGNORECASE,
    )

    for path in sorted(VERSIONS.glob("*.py")):
        src = path.read_text(encoding="utf-8")
        rel = path.name
        tree = ast.parse(src)

        # module-level string constants (e.g. AUDIT_TABLE = "legal_rule_reconciliation_audit")
        constants: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        constants[t.id] = node.value.value

        def _first_arg_name(call: ast.Call) -> str | None:
            if not call.args:
                return None
            arg = call.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
            if isinstance(arg, ast.Name):
                if arg.id in constants:
                    return constants[arg.id]
                unresolved.append(f"{rel}: op.create_table({arg.id}) — constant not found")
                return None
            unresolved.append(f"{rel}: op.create_table() first arg is {type(arg).__name__}")
            return None

        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "create_table"
            ):
                name = _first_arg_name(node)
                if name:
                    op_names.setdefault(name, []).append(rel)

        for match in raw_create_re.finditer(src):
            raw_names.add(match.group(1))

    return op_names, sorted(raw_names), unresolved


OP_CREATED, RAW_CREATED, UNRESOLVED = _created_tables_from_migrations()
ALL_CREATED = set(OP_CREATED) | set(RAW_CREATED)


# ── models: Base.metadata tables ──────────────────────────────────────
def _model_tables() -> set[str]:
    from app.models import Base  # conftest guarantees DATABASE_URL is set

    return set(Base.metadata.tables.keys())


MODEL_TABLES = _model_tables()


# ── contract tests ────────────────────────────────────────────────────
def test_allowlist_names_are_real_migration_created_tables():
    unknown = ALLOWLIST - ALL_CREATED
    assert not unknown, (
        "MIGRATION_ONLY_TABLES names tables no migration creates: "
        f"{sorted(unknown)}"
    )


def test_migration_only_tables_match_allowlist():
    drift = ALL_CREATED - MODEL_TABLES
    assert drift == set(ALLOWLIST), (
        "Migration-only table drift mismatch.\n"
        f"  created by migrations but not modeled: {sorted(drift)}\n"
        f"  allowlisted in alembic/env.py:          {sorted(ALLOWLIST)}\n"
        "Update MIGRATION_ONLY_TABLES in the same PR if a new model-free "
        "migration table was added intentionally."
    )


def test_allowlist_never_names_a_modeled_table():
    overlap = ALLOWLIST & MODEL_TABLES
    assert not overlap, (
        "MIGRATION_ONLY_TABLES must never contain a modeled table "
        f"(would hide real model drift): {sorted(overlap)}"
    )


def test_every_modeled_table_is_created_by_a_migration():
    orphans = MODEL_TABLES - ALL_CREATED
    assert not orphans, (
        "Modeled tables no migration creates (would be missing on a "
        f"fresh database): {sorted(orphans)}"
    )


def test_include_object_filters_only_allowlisted_reflected_tables():
    # allowlisted + reflected + not modeled -> filtered out of the diff
    for name in sorted(ALLOWLIST):
        assert _INCLUDE_OBJECT(None, name, "table", True, None) is False, name
    # reflected table NOT allowlisted stays visible (check stays meaningful)
    assert _INCLUDE_OBJECT(None, "brand_new_unlisted_table", "table", True, None) is True
    # metadata-side additions are never filtered by the allowlist branch
    assert _INCLUDE_OBJECT(None, "users", "table", False, None) is True
    # existing vw_ view rule still applies
    assert _INCLUDE_OBJECT(None, "vw_repair_aggregate", "table", True, None) is False


def test_no_unresolved_dynamic_create_table_calls():
    assert not UNRESOLVED, (
        "op.create_table() calls with names this contract cannot resolve "
        "statically (add them to MIGRATION_ONLY_TABLES explicitly if the "
        f"table is intentionally model-free): {UNRESOLVED}"
    )
