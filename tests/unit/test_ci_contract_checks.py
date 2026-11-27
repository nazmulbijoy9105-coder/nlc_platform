from __future__ import annotations

import pytest

from scripts.check_dependency_licenses import APPROVED_ALIASES, normalize
from scripts.check_openapi_contract import (
    REQUIRED_OPERATIONS,
    REQUIRED_RESPONSE_FIELDS,
    validate_schema,
)


def _valid_openapi() -> dict:
    paths = {}
    components = {"schemas": {}}
    for (path, method), requires_schema in REQUIRED_OPERATIONS.items():
        operation = {"responses": {"200": {"description": "OK"}}}
        if requires_schema:
            schema_name = f"Contract{len(components['schemas'])}"
            operation["responses"]["200"]["content"] = {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                }
            }
            components["schemas"][schema_name] = {
                "type": "object",
                "properties": {
                    field: {"type": "string"}
                    for field in REQUIRED_RESPONSE_FIELDS.get((path, method), set())
                },
            }
        paths[path] = {method: operation}
    return {
        "openapi": "3.1.0",
        "paths": paths,
        "components": components,
    }


def test_openapi_contract_accepts_required_operations_and_response_schemas():
    validate_schema(_valid_openapi())


def test_openapi_prefix_cannot_be_satisfied_by_unrelated_substring():
    schema = _valid_openapi()
    del schema["paths"]["/api/v1/auth/login"]
    schema["paths"]["/unrelated/api/v1/auth/login"] = {
        "post": {"responses": {"200": {"description": "not the auth route"}}}
    }
    with pytest.raises(SystemExit, match="path prefixes missing|missing client operations"):
        validate_schema(schema)


def test_openapi_contract_rejects_missing_client_response_schema():
    schema = _valid_openapi()
    schema["paths"]["/api/v1/companies"]["get"]["responses"] = {
        "200": {"description": "schema removed"}
    }
    with pytest.raises(SystemExit, match="response schemas"):
        validate_schema(schema)


def test_openapi_contract_rejects_removed_client_response_field():
    schema = _valid_openapi()
    ref = schema["paths"]["/api/v1/rules"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"]
    component = ref.rsplit("/", 1)[-1]
    del schema["components"]["schemas"][component]["properties"]["rule_id"]
    with pytest.raises(SystemExit, match="response fields"):
        validate_schema(schema)


def test_psfl_is_not_implicitly_approved():
    assert normalize("PSF License") not in APPROVED_ALIASES
    assert normalize("MIT License") in APPROVED_ALIASES
