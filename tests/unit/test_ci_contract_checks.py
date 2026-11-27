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
    del schema["paths"]["/api/v1/auth/refresh"]
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


def test_psfl_and_unlicense_are_explicitly_approved():
    from scripts.check_dependency_licenses import is_approved

    assert normalize("Python Software Foundation License") in APPROVED_ALIASES
    assert is_approved("Python Software Foundation License")
    assert is_approved("Unlicense")
    assert normalize("MIT License") in APPROVED_ALIASES

def test_production_image_and_license_sbom_use_runtime_requirements():
    from pathlib import Path

    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    license_workflow = Path(".github/workflows/license-policy.yml").read_text(encoding="utf-8")
    sbom_workflow = Path(".github/workflows/sbom.yml").read_text(encoding="utf-8")
    runtime_requirements = Path("requirements-runtime.txt").read_text(encoding="utf-8")

    assert "COPY requirements-runtime.txt ." in dockerfile
    assert "-r requirements-runtime.txt" in dockerfile
    assert ".venv-app/bin/python -m pip install -r requirements-runtime.txt" in license_workflow
    assert "cyclonedx-py requirements requirements-runtime.txt" in sbom_workflow
    assert "pytest==" not in runtime_requirements
    assert "ruff==" not in runtime_requirements
    assert "mypy==" not in runtime_requirements
    assert "pip_audit==" not in runtime_requirements

def test_dependency_license_expression_parser_preserves_fail_closed_policy():
    from scripts.check_dependency_licenses import is_approved

    assert is_approved("Apache-2.0 OR BSD-3-Clause")
    assert is_approved("Apache-2.0 AND BSD-2-Clause")
    assert is_approved("MIT OR (Apache-2.0 AND BSD-3-Clause)")
    assert is_approved("Python Software Foundation License")
    assert is_approved("BSD-2-Clause AND Unlicense AND MIT")
    assert is_approved("3-Clause BSD License")
    assert is_approved("The Unlicense (Unlicense)")
    assert is_approved("ISC License (ISCL)")
    assert is_approved("Apache Software License; BSD License")
    assert is_approved("Apache Software License; MIT License")
    assert not is_approved("MPL-2.0 AND (Apache-2.0 OR MIT)")
    assert not is_approved("MIT OR GPL-3.0-only")
    assert not is_approved("Apache-2.0 OR (MIT AND GPL-3.0-only)")
    assert not is_approved("(MIT OR GPL-3.0-only) AND BSD-3-Clause")
    assert not is_approved("MIT AND Python-2.0")
    assert not is_approved("UNKNOWN")
    assert not is_approved("MIT OR")
