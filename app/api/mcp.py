"""Read-only Model Context Protocol endpoint for NLC.

Implements the MCP Streamable HTTP JSON-RPC surface without introducing a
second legal-rules engine. All requests use the existing JWT/user dependency.
Only the existing public legal-rule catalogue is exposed in this first slice.
"""
from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_catalog_db, get_current_user
from app.models.user import User
from app.services.rules_service import RulesService

logger = structlog.get_logger(__name__)
router = APIRouter()
SUPPORTED_PROTOCOL_VERSIONS = {"2025-06-18", "2025-11-25"}
DEFAULT_PROTOCOL_VERSION = "2025-11-25"
MAX_RULE_LIMIT = 100

TOOLS = [
    {
        "name": "nlc.list_rules",
        "description": (
            "List NLC legal-rule catalogue metadata. Catalogue membership, "
            "activation or a stored citation does not establish legal correctness, "
            "company-specific applicability or approval for statutory scoring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "is_active": {"type": "boolean", "description": "Optional active-state filter."},
                "rule_type": {"type": "string", "maxLength": 80},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_RULE_LIMIT},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "nlc.get_rule",
        "description": (
            "Retrieve one exact rule by its current runtime rule ID. Returns stored "
            "metadata and review status, not a legal opinion or verification."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string", "minLength": 1, "maxLength": 80},
            },
            "required": ["rule_id"],
            "additionalProperties": False,
        },
    },
]


def _rpc_error(request_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        },
        headers={"Cache-Control": "no-store"},
    )


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _rule_payload(rule: Any) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "rule_name": rule.rule_name,
        "rule_type": str(_enum_value(rule.rule_type)),
        "statutory_basis": rule.statutory_basis,
        "description": rule.description,
        "verification_status": str(_enum_value(rule.verification_status)),
        "statutory_effective_date": (
            rule.statutory_effective_date.isoformat()
            if rule.statutory_effective_date else None
        ),
        "is_active": bool(rule.is_active),
        "rule_version": rule.rule_version,
        "score_impact": int(rule.score_impact or 0),
        "disclaimer": (
            "Stored catalogue metadata is not independent legal verification, "
            "company-specific applicability analysis, or authority to release a score."
        ),
    }


def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, default=str)}],
        "isError": is_error,
    }


async def _call_tool(name: str, arguments: Any, db: AsyncSession) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        return _tool_result({"error": "Tool arguments must be a JSON object."}, is_error=True)

    service = RulesService(db)
    if name == "nlc.list_rules":
        allowed = {"is_active", "rule_type", "limit"}
        if set(arguments) - allowed:
            return _tool_result({"error": "Unsupported argument."}, is_error=True)
        is_active = arguments.get("is_active")
        rule_type = arguments.get("rule_type")
        limit = arguments.get("limit", MAX_RULE_LIMIT)
        if is_active is not None and not isinstance(is_active, bool):
            return _tool_result({"error": "is_active must be boolean."}, is_error=True)
        if rule_type is not None and (
            not isinstance(rule_type, str) or len(rule_type) > 80
        ):
            return _tool_result({"error": "rule_type must be a string of at most 80 characters."}, is_error=True)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RULE_LIMIT:
            return _tool_result({"error": f"limit must be an integer between 1 and {MAX_RULE_LIMIT}."}, is_error=True)
        rules = await service.get_all(is_active=is_active, rule_type=rule_type)
        total = len(rules)
        payload = [_rule_payload(rule) for rule in rules[:limit]]
        return _tool_result({
            "items": payload,
            "returned": len(payload),
            "total_matching": total,
            "truncated": total > len(payload),
        })

    if name == "nlc.get_rule":
        if set(arguments) != {"rule_id"}:
            return _tool_result({"error": "Exactly one rule_id argument is required."}, is_error=True)
        rule_id = arguments["rule_id"]
        if not isinstance(rule_id, str) or not rule_id.strip() or len(rule_id) > 80:
            return _tool_result({"error": "rule_id must be a non-empty string of at most 80 characters."}, is_error=True)
        rule = await service.get_by_rule_id(rule_id.strip())
        if rule is None:
            return _tool_result({"error": "Rule not found."}, is_error=True)
        return _tool_result(_rule_payload(rule))

    return _tool_result({"error": "Unknown tool."}, is_error=True)


@router.post("/mcp", include_in_schema=True, tags=["MCP"])
async def mcp_streamable_http(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_catalog_db),
):
    """Handle stateless JSON-RPC MCP requests over Streamable HTTP."""
    request_id: Any = None
    try:
        payload = await request.json()
    except Exception:
        return _rpc_error(None, -32700, "Parse error.")

    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return _rpc_error(None, -32600, "Invalid Request.")

    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    if not isinstance(method, str) or not isinstance(params, dict):
        return _rpc_error(request_id, -32600, "Invalid Request.")

    # MCP notifications have no JSON-RPC id and must not receive a response body.
    if method == "notifications/initialized" and request_id is None:
        return Response(status_code=202, headers={"Cache-Control": "no-store"})

    if method != "initialize":
        protocol_version = request.headers.get("MCP-Protocol-Version")
        if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            return _rpc_error(request_id, -32600, "Missing or unsupported MCP-Protocol-Version.")

    if method == "initialize":
        requested = params.get("protocolVersion", DEFAULT_PROTOCOL_VERSION)
        negotiated = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        result = {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "nlc-legal-engineering", "version": "0.1.0"},
            "instructions": (
                "Read-only NLC legal-rule catalogue access. Do not treat catalogue "
                "metadata as legal verification, applicability or score-release approval."
            ),
        }
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "result": result},
            headers={"MCP-Protocol-Version": negotiated, "Cache-Control": "no-store"},
        )

    if method == "ping":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "result": {}},
            headers={"Cache-Control": "no-store"},
        )

    if method == "tools/list":
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}},
            headers={"Cache-Control": "no-store"},
        )

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            return _rpc_error(request_id, -32602, "Tool name is required.")
        try:
            result = await _call_tool(name, arguments, db)
        except Exception as exc:
            logger.error(
                "mcp_tool_failed",
                tool=name,
                user_id=str(getattr(current_user, "id", "unknown")),
                request_id=getattr(request.state, "request_id", None),
                error_type=type(exc).__name__,
            )
            result = _tool_result(
                {"error": "Tool execution failed. Contact NLC support with the request ID."},
                is_error=True,
            )
        logger.info(
            "mcp_tool_called",
            tool=name,
            user_id=str(getattr(current_user, "id", "unknown")),
            request_id=getattr(request.state, "request_id", None),
            outcome="error" if result.get("isError") else "success",
        )
        return JSONResponse(
            {"jsonrpc": "2.0", "id": request_id, "result": result},
            headers={"Cache-Control": "no-store"},
        )

    if method.startswith("notifications/") or method == "notifications/cancelled":
        return Response(status_code=202, headers={"Cache-Control": "no-store"})

    return _rpc_error(request_id, -32601, "Method not found.")


@router.get("/mcp", include_in_schema=False)
async def mcp_get_not_supported():
    # This stateless server does not provide server-initiated event streams.
    return Response(status_code=405, headers={"Allow": "POST"})
