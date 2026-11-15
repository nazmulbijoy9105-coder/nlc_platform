"""Read-only SQLAlchemy mapper relationship/loading audit.

Reports ORM relationship metadata and loading risks. It does not query or
mutate application data and does not change loader strategies.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import app.models  # noqa: F401 — register every mapped class
from sqlalchemy.orm import configure_mappers

from app.models.database import Base


def build_report() -> dict[str, Any]:
    configure_mappers()
    relationships: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []

    for mapper in sorted(Base.registry.mappers, key=lambda item: item.class_.__name__):
        for rel in sorted(mapper.relationships, key=lambda item: item.key):
            target = rel.mapper.class_.__name__
            lazy = str(rel.lazy)
            item = {
                "model": mapper.class_.__name__,
                "relationship": rel.key,
                "target": target,
                "direction": str(rel.direction),
                "uselist": bool(rel.uselist),
                "lazy": lazy,
                "back_populates": rel.back_populates,
                "viewonly": bool(rel.viewonly),
                "cascade": str(rel.cascade),
                "foreign_key_columns": sorted(
                    f"{column.table.name}.{column.name}"
                    for column in rel.local_columns
                ),
            }
            relationships.append(item)

            if lazy == "select":
                warnings.append({
                    "code": "ASYNC_LAZY_LOAD_RISK",
                    "model": mapper.class_.__name__,
                    "relationship": rel.key,
                    "detail": "Default select loading may trigger implicit async IO/MissingGreenlet.",
                })
            elif lazy == "selectin" and rel.uselist:
                warnings.append({
                    "code": "IMPLICIT_COLLECTION_EAGER_LOAD",
                    "model": mapper.class_.__name__,
                    "relationship": rel.key,
                    "detail": "Collection is select-in loaded by default; broad parent queries may fan out.",
                })
            elif lazy == "raise":
                warnings.append({
                    "code": "EXPLICIT_LOADER_REQUIRED",
                    "model": mapper.class_.__name__,
                    "relationship": rel.key,
                    "detail": "Access requires an explicit eager-loader option.",
                })

            if rel.back_populates:
                counterpart = rel.mapper.relationships.get(rel.back_populates)
                if counterpart is None or counterpart.back_populates != rel.key:
                    warnings.append({
                        "code": "BACK_POPULATES_MISMATCH",
                        "model": mapper.class_.__name__,
                        "relationship": rel.key,
                        "detail": f"Expected reciprocal {target}.{rel.back_populates} -> {rel.key}.",
                    })

    lazy_counts = Counter(item["lazy"] for item in relationships)
    warning_counts = Counter(item["code"] for item in warnings)
    return {
        "audit": "sqlalchemy-relationship-loading",
        "read_only": True,
        "mapped_models": len({item["model"] for item in relationships}),
        "relationship_count": len(relationships),
        "loader_strategy_counts": dict(sorted(lazy_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "relationships": relationships,
        "warnings": warnings,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_output:
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
