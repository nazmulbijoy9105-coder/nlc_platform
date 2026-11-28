# NLC MCP server — implementation and integration guide

**Implementation:** authenticated, stateless, read-only MCP Streamable HTTP endpoint.  
**Endpoint:** `POST https://<NLC_API_HOST>/api/v1/mcp`  
**Protocol baseline:** MCP 2025-11-25.  
**Status:** first engineering slice; not production-certified.

## Implemented tools

| Tool | Inputs | Behavior |
|---|---|---|
| `nlc.list_rules` | optional `is_active`, `rule_type`, `limit` (1–100) | Reads rule catalogue via existing `RulesService` and catalogue DB context |
| `nlc.get_rule` | exact `rule_id` | Reads one rule by exact runtime ID |

Responses disclose stored verification status and state that catalogue metadata is not independent legal verification, applicability analysis or score-release approval.

## Authentication

Every request is protected by the existing NLC `get_current_user` dependency. Clients must send a valid NLC access JWT:

```http
Authorization: Bearer <NLC_ACCESS_TOKEN>
Content-Type: application/json
Accept: application/json, text/event-stream
```

For requests after `initialize`, also send:

```http
MCP-Protocol-Version: 2025-11-25
```

Use short-lived access tokens and the existing refresh/login workflow. Do not put tokens in source code, URLs, query parameters, logs or MCP tool arguments. This first slice does not implement OAuth discovery, dynamic client registration, refresh tokens, or per-tool delegated scopes. Use only trusted MCP clients.

## Initialize example

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-11-25",
    "capabilities": {},
    "clientInfo": {"name": "nlc-client", "version": "1.0.0"}
  }
}
```

Then send `notifications/initialized`, followed by `tools/list` or `tools/call`. The endpoint is stateless; no MCP session ID is issued. GET event streams are not provided. Tool calls are read-only.

## Example tool call

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "nlc.get_rule",
    "arguments": {"rule_id": "AGM-001"}
  }
}
```

## Security and data boundaries

- Reuses NLC JWT verification, active-user lookup and database role consistency checks.
- Uses the existing read-only catalogue database dependency; it does not accept a caller-supplied tenant or execute arbitrary SQL.
- Does not expose company records, evidence files, raw database access, legal-source uploads, rule mutations, score release, or deployment controls.
- Logs tool name, user ID, request ID and outcome; does not log bearer tokens or raw tool arguments.
- Tool outputs are untrusted data. A client must not treat returned text as executable instructions.
- Unknown rule IDs return a bounded tool error; unexpected exceptions return a generic error with request correlation.
- The MCP route is subject to the API's global request-ID, access-log and security-header middleware.

## Tests

Run the focused contract tests:

```bash
pytest -q tests/unit/test_mcp_protocol.py
```

Then run the repository's normal checks:

```bash
ruff check app/api/mcp.py tests/unit/test_mcp_protocol.py
mypy app/api/mcp.py
pytest -q tests/unit/test_main.py tests/unit/test_mcp_protocol.py
```

These tests are committed but have not been executed in this remote-edit session. CI results must be checked before merge.

## Not implemented yet

1. Legal source registry search and immutable source-version retrieval.
2. Canonical rule alias/identity tracing across seed, DB, engine, API and reports.
3. Company-specific applicability analysis and deterministic evaluation invocation.
4. Evidence metadata/provenance and chain-of-custody read APIs.
5. Release governance and audit-event read APIs.
6. OAuth/OIDC client identity, scopes and per-tool authorization.
7. MCP Inspector interoperability and external-client integration test.
8. Deployment, runtime health and database identity verification.

Do not add these tools until the corresponding service contracts and authorization rules are verified. The MCP server is an access layer, not a second implementation of legal rules. Bangladesh counsel approval remains outside the MCP server.
