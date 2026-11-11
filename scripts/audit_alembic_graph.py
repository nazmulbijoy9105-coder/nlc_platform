"""Audit the complete Alembic revision DAG using Alembic's revision map.

This is a read-only source audit: it does not connect to a database or mutate
schema state. CI separately rehearses upgrades against disposable PostgreSQL
databases.
"""
from __future__ import annotations

from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory


def parents_for(revision) -> tuple[str, ...]:
    down_revision = revision.down_revision
    if down_revision is None:
        return ()
    if isinstance(down_revision, str):
        return (down_revision,)
    return tuple(down_revision)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    heads = tuple(script.get_heads())
    bases = tuple(script.get_bases())
    if len(heads) != 1:
        raise SystemExit(
            f"Expected exactly one Alembic head; found {len(heads)}: {heads}"
        )

    # Alembic builds this traversal from its computed revision map. A missing
    # parent, duplicate revision ID, or cycle is rejected while loading/walking.
    revisions = list(script.walk_revisions())
    revision_ids = [revision.revision for revision in revisions]
    known_ids = set(revision_ids)
    if len(known_ids) != len(revision_ids):
        raise SystemExit("Duplicate Alembic revision IDs detected.")

    missing = [
        (revision.revision, parent)
        for revision in revisions
        for parent in parents_for(revision)
        if parent not in known_ids
    ]
    if missing:
        raise SystemExit(f"Missing Alembic parent revisions: {missing}")

    merge_revisions = [
        (revision.revision, parents_for(revision))
        for revision in revisions
        if len(parents_for(revision)) > 1
    ]

    print(f"ALEMBIC_BASES: {', '.join(bases) or '(none)'}")
    print(f"ALEMBIC_HEADS: {', '.join(heads)}")
    print(f"ALEMBIC_REVISION_COUNT: {len(revisions)}")
    print(f"ALEMBIC_MERGE_COUNT: {len(merge_revisions)}")
    print("ALEMBIC_REVISION_DAG (revision <- parent revisions):")
    for revision in reversed(revisions):
        parents = parents_for(revision)
        parent_text = ", ".join(parents) if parents else "BASE"
        print(f"  {revision.revision} <- {parent_text}")

    print("ALEMBIC_MERGE_REVISIONS:")
    for revision_id, parents in merge_revisions:
        print(f"  {revision_id} <- {', '.join(parents)}")

    print("Alembic revision DAG audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
