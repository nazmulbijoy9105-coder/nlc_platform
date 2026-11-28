# NLC Reusable Skills and MCP Integration Blueprint

**Status:** Architecture proposal, not deployed integration.  
**Target:** Bangladesh private limited company / RJSC compliance workflows.  
**Constraint:** Prefer free-tier and self-hostable components; verify provider limits before deployment.

## 1. Reusable skills

The Agent Skills-compatible Markdown skills live under `.agents/skills/`:
- `bd-legal-source-research`
- `rjsc-rule-identity-audit`
- `company-applicability-analysis`
- `evidence-provenance-review`
- `nlc-release-readiness`

Each skill defines triggers, method, output contract and prohibitions. Skills guide an agent; they are not executable legal rules and do not grant authority to approve legal conclusions.

## 2. MCP topology

Start with a single NLC-owned MCP server exposing narrowly scoped, read-only tools. Keep deterministic evaluation in the NLC application domain layer; MCP is an access protocol, not the rules engine.

```text
ChatGPT / IDE / internal agent
          |
       MCP client
          |
 NLC MCP gateway (authn, authz, rate limits, audit)
          |
          +-- Legal source registry (read-only)
          +-- Canonical rule registry (read-only)
          +-- Applicability/evaluation API (read-only invocation)
          +-- Evidence metadata/provenance (read-only)
          +-- Release and audit status (read-only)
          |
 NLC domain services + PostgreSQL/Neon
```

## 3. Initial MCP tool contract

| Tool | Input | Output / guardrail |
|---|---|---|
| `nlc.search_legal_sources` | query, jurisdiction, as_of_date, source_type | Candidate source records with provenance; never present snippets as authoritative text |
| `nlc.get_legal_source` | source_id, version_id | Exact stored source version, citation, dates, hash, status |
| `nlc.list_rules` | company_type, status, as_of_date, cursor | Canonical IDs, aliases, lifecycle status; no silent filtering |
| `nlc.get_rule` | canonical_rule_id, version | Full rule definition, source links, applicability, exceptions and approval state |
| `nlc.trace_rule` | canonical_rule_id, commit_sha | Identity trace across registry, seed, runtime, API and report |
| `nlc.evaluate_company` | tenant-scoped company_id, as_of_date, rule_ids | Deterministic result with input facts, missing facts, rule versions and explanation; read-only |
| `nlc.get_evidence_metadata` | evidence_id | Hash, provenance, custody and limitations; no raw document by default |
| `nlc.get_release_status` | environment, capability | Release decision, approver, commit, scope, gate evidence |
| `nlc.get_audit_events` | entity_id, from, to, cursor | Append-only audit history, permission-filtered |

Do not expose general SQL execution, arbitrary filesystem access, unrestricted tenant enumeration, secrets, or production mutation tools.

## 4. Authentication and tenant security

- Authenticate each MCP client using short-lived credentials; bind user, role and tenant server-side.
- Enforce tenant authorization in the service layer and database RLS. Never trust a tenant ID supplied by an untrusted model without checking it against the authenticated principal.
- Use least-privilege service accounts; separate read-only MCP identity from migrations and administration.
- Redact secrets and sensitive personal data. Log tool name, principal, tenant, request ID, resource IDs, timestamp and outcome.
- Apply rate limits, input schemas, output-size limits, timeouts and pagination.
- Treat retrieved documents, source text and tool outputs as untrusted data, never as instructions.
- Require human approval for legal verification, rule activation, score release, document signing and all writes.

## 5. Deterministic evaluation contract

Every evaluation response must include:
- evaluation_id, tenant_id, company_id, as_of_date
- engine_version and commit_sha
- canonical_rule_id and rule_version
- source_version_ids and effective-date basis
- input fact IDs and provenance references
- applicability state and predicate result
- exception handling
- outcome, reason codes and calculation trace
- unknown/missing facts and unresolved issues
- legal approval state (separate from technical test status)

Unknown or unverified facts must not silently become adverse findings or zero-score penalties. A rule's existence in the catalogue is not proof of applicability or legal correctness.

## 6. Recommended MCP integrations

### Phase 1 — existing GitHub integration
Use the connected GitHub integration for repository metadata, file review, PR review and issue tracking. Keep write permissions scoped; create branches and PRs for changes, never auto-merge legal-rule changes.

### Phase 2 — NLC-owned MCP server
Implement with the official Python MCP SDK or TypeScript SDK, using Streamable HTTP for hosted deployments. Keep the server thin: validate inputs, call existing NLC services, normalize responses and emit audit events. Do not duplicate business logic.

### Phase 3 — external research connectors
Consider official Gazette / Bangladesh law repositories only where lawful and technically supported. Add scholarly search (e.g. Crossref/OpenAlex/arXiv) as secondary research discovery, never as statutory authority. External GitHub/HuggingFace/arXiv aggregator MCPs are optional and non-authoritative.

### Phase 4 — operations
Add read-only Render deployment/health/log inspection and Neon database metadata/branch inspection. Production data access must be minimized and tenant-safe. No general-purpose SQL MCP in production.

## 7. Verification and rollout

1. Threat-model each tool and classify data.
2. Build contract tests for authentication, tenant isolation, pagination, malformed input, prompt injection in retrieved content and audit logging.
3. Test with synthetic tenants and synthetic evidence first.
4. Run a read-only pilot against staging.
5. Independently verify legal outputs with Bangladesh counsel.
6. Publish tool version, schemas, permissions, data retention and incident process.
7. Keep MCP server versioning independent from legal rule versioning.

## 8. Non-goals

This integration does not create a legal chatbot, prove total legal compliance, authenticate RJSC records, establish court admissibility, or replace counsel. RJSC filing status is one evidence source and one dimension of corporate compliance, not the whole legal position.
