"""Validate the stable client-facing OpenAPI contract and export the schema."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.main import app


REQUIRED_PREFIXES = (
    "/api/v1/health",
    "/api/v1/auth",
    "/api/v1/companies",
    "/api/v1/rules",
)
# These are concrete client-facing operations, not broad path-name hints.
REQUIRED_OPERATIONS = {
    ("/api/v1/health", "get"): False,
    ("/api/v1/auth/login", "post"): True,
    ("/api/v1/auth/refresh", "post"): True,
    ("/api/v1/companies", "get"): True,
    ("/api/v1/rules", "get"): True,
}


def _canonical_path(path: str) -> str:
    return path.rstrip("/") or "/"


def _has_success_json_schema(operation: dict[str, Any]) -> bool:
    responses = operation.get("responses") or {}
    for status, response in responses.items():
        if not (str(status).startswith("2") or str(status).lower() == "default"):
            continue
        content = (response or {}).get("content") or {}
        for media_type, media in content.items():
            if media_type == "application/json" or media_type.endswith("+json"):
                schema = (media or {}).get("schema")
                if isinstance(schema, dict) and schema:
                    return True
    return False


def validate_schema(schema: dict[str, Any]) -> None:
    raw_paths = schema.get("paths") or {}
    paths = {_canonical_path(path): operations for path, operations in raw_paths.items()}

    missing_prefixes = []
    for prefix in REQUIRED_PREFIXES:
        if not any(
            path == prefix or path.startswith(prefix + "/")
            for path in paths
        ):
            missing_prefixes.append(prefix)
    if missing_prefixes:
        raise SystemExit(
            "Required API path prefixes missing at segment boundaries: "
            + ", ".join(missing_prefixes)
        )

    missing_operations = []
    missing_schemas = []
    for (path, method), requires_schema in REQUIRED_OPERATIONS.items():
        operation = (paths.get(path) or {}).get(method)
        if not isinstance(operation, dict):
            missing_operations.append(f"{method.upper()} {path}")
            continue
        if requires_schema and not _has_success_json_schema(operation):
            missing_schemas.append(f"{method.upper()} {path}")
    if missing_operations or missing_schemas:
        problems = []
        if missing_operations:
            problems.append("missing client operations: " + ", ".join(missing_operations))
        if missing_schemas:
            problems.append("missing successful JSON response schemas: " + ", ".join(missing_schemas))
        raise SystemExit("OpenAPI client contract failed: " + "; ".join(problems))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    schema = app.openapi()
    if not isinstance(schema, dict) or not schema.get("openapi"):
        raise SystemExit("OpenAPI schema or version missing")
    validate_schema(schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"OpenAPI client contract OK: {len(schema.get('paths') or {})} paths; "
        f"{len(REQUIRED_OPERATIONS)} required operations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
