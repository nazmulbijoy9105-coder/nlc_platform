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
# Stable fields consumed by the web client. Removing or renaming one requires
# an intentional frontend/API contract update in the same release train.
REQUIRED_RESPONSE_FIELDS = {
    ("/api/v1/auth/login", "post"): {
        "access_token", "token_type", "user", "requires_2fa",
    },
    ("/api/v1/auth/refresh", "post"): {
        "access_token", "token_type",
    },
    ("/api/v1/companies", "get"): {
        "id", "name", "registration_number", "compliance_score",
        "evaluation_status", "screening_only", "legal_advice",
    },
    ("/api/v1/rules", "get"): {
        "rule_id", "statutory_basis", "product_scoring_enabled",
        "verification_status",
    },
}


def _canonical_path(path: str) -> str:
    return path.rstrip("/") or "/"


def _success_json_schema(operation: dict[str, Any]) -> dict[str, Any] | None:
    responses = operation.get("responses") or {}
    for status, response in responses.items():
        # A default response may describe an error; only a 2xx response proves
        # the successful client response contract exists.
        if not str(status).startswith("2"):
            continue
        content = (response or {}).get("content") or {}
        for media_type, media in content.items():
            if media_type == "application/json" or media_type.endswith("+json"):
                schema = (media or {}).get("schema")
                if isinstance(schema, dict) and schema:
                    return schema
    return None


def _resolve_response_object(
    schema: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a response object or array item through local OpenAPI refs."""
    current = schema
    if current.get("type") == "array":
        current = current.get("items") or {}
    ref = current.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", 1)[-1]
        current = (components.get("schemas") or {}).get(name) or {}
    return current


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
    missing_fields = []
    components = schema.get("components") or {}
    for (path, method), requires_schema in REQUIRED_OPERATIONS.items():
        operation = (paths.get(path) or {}).get(method)
        if not isinstance(operation, dict):
            missing_operations.append(f"{method.upper()} {path}")
            continue
        if not requires_schema:
            continue
        response_schema = _success_json_schema(operation)
        if response_schema is None:
            missing_schemas.append(f"{method.upper()} {path}")
            continue
        expected_fields = REQUIRED_RESPONSE_FIELDS.get((path, method), set())
        response_object = _resolve_response_object(response_schema, components)
        actual_fields = set((response_object.get("properties") or {}).keys())
        absent = sorted(expected_fields - actual_fields)
        if absent:
            missing_fields.append(f"{method.upper()} {path}: {absent!r}")

    if missing_operations or missing_schemas or missing_fields:
        problems = []
        if missing_operations:
            problems.append("missing client operations: " + ", ".join(missing_operations))
        if missing_schemas:
            problems.append("missing successful JSON response schemas: " + ", ".join(missing_schemas))
        if missing_fields:
            problems.append("missing client response fields: " + "; ".join(missing_fields))
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
