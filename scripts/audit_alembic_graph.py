"""Produce a complete, read-only inventory and integrity audit of the Alembic DAG.

This validates repository migration metadata and script inventory only. It does
not connect to a database, prove that migrations execute, compare production
schema, or certify data preservation. Those require isolated restore and live
database release gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _parents(revision: Any) -> tuple[str, ...]:
    return _as_tuple(revision.down_revision)


def _dependencies(revision: Any) -> tuple[str, ...]:
    return _as_tuple(revision.dependencies)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_report(root: Path) -> dict[str, Any]:
    config = Config(str(root / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    revisions = list(script.walk_revisions())
    revision_ids = [item.revision for item in revisions]
    known_ids = set(revision_ids)

    if len(known_ids) != len(revision_ids):
        raise RuntimeError("Duplicate Alembic revision IDs detected.")

    heads = tuple(script.get_heads())
    bases = tuple(script.get_bases())
    if len(heads) != 1:
        raise RuntimeError(f"Expected exactly one Alembic head; found {heads!r}.")
    if len(bases) != 1:
        raise RuntimeError(f"Expected exactly one Alembic base; found {bases!r}.")

    missing: list[dict[str, str]] = []
    for item in revisions:
        for relation, targets in (
            ("down_revision", _parents(item)),
            ("depends_on", _dependencies(item)),
        ):
            for target in targets:
                if target not in known_ids:
                    missing.append(
                        {"revision": item.revision, "relation": relation, "target": target}
                    )
    if missing:
        raise RuntimeError(f"Missing revision references: {missing!r}")

    # Confirm every discovered revision belongs to the single head's ancestry
    # or explicit dependency graph; this catches detached/orphaned revisions.
    by_id = {item.revision: item for item in revisions}
    reachable: set[str] = set()
    pending = [heads[0]]
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        item = by_id[current]
        pending.extend(_parents(item))
        pending.extend(_dependencies(item))
    unreachable = sorted(known_ids - reachable)
    if unreachable:
        raise RuntimeError(f"Unreachable/orphan Alembic revisions: {unreachable!r}")

    versions_dir = Path(script.dir) / "versions"
    migration_files = sorted(
        path for path in versions_dir.rglob("*.py")
        if path.name != "__init__.py"
    )
    loaded_paths = {
        Path(item.path).resolve()
        for item in revisions
        if getattr(item, "path", None)
    }
    unrecognized_files = sorted(
        str(path.relative_to(root))
        for path in migration_files
        if path.resolve() not in loaded_paths
    )
    if unrecognized_files:
        raise RuntimeError(
            "Python files exist under alembic/versions but are not loaded "
            f"as Alembic revisions: {unrecognized_files!r}"
        )

    ordered = list(reversed(revisions))
    inventory = []
    for item in ordered:
        path = Path(item.path).resolve()
        inventory.append(
            {
                "revision": item.revision,
                "down_revision": list(_parents(item)),
                "depends_on": list(_dependencies(item)),
                "branch_labels": list(_as_tuple(item.branch_labels)),
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path),
            }
        )

    merges = [
        entry for entry in inventory if len(entry["down_revision"]) > 1
    ]
    return {
        "audit": "alembic-revision-source-integrity",
        "database_checked": False,
        "production_schema_checked": False,
        "base": bases[0],
        "head": heads[0],
        "revision_count": len(inventory),
        "migration_file_count": len(migration_files),
        "merge_revision_count": len(merges),
        "unreachable_revisions": unreachable,
        "unrecognized_migration_files": unrecognized_files,
        "revisions": inventory,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit and inventory every Alembic revision in this repository."
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for a machine-readable full migration inventory.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    report = build_report(root)

    print(f"ALEMBIC_BASE: {report['base']}")
    print(f"ALEMBIC_HEAD: {report['head']}")
    print(f"ALEMBIC_REVISION_COUNT: {report['revision_count']}")
    print(f"ALEMBIC_MIGRATION_FILE_COUNT: {report['migration_file_count']}")
    print(f"ALEMBIC_MERGE_REVISION_COUNT: {report['merge_revision_count']}")
    print("COMPLETE_ALEMBIC_MIGRATION_INVENTORY:")
    for item in report["revisions"]:
        parents = ", ".join(item["down_revision"]) or "BASE"
        dependencies = ", ".join(item["depends_on"]) or "-"
        print(
            f"  {item['revision']} <- {parents} "
            f"(depends_on={dependencies}; sha256={item['sha256']})"
        )

    if args.json_output:
        output = args.json_output
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"ALEMBIC_JSON_REPORT: {output.relative_to(root)}")

    print(
        "Alembic source inventory and revision graph audit passed. "
        "Database execution and production parity remain separate gates."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
