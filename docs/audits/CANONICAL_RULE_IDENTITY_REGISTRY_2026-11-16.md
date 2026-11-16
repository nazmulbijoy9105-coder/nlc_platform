# Canonical Rule Identity Registry — Architecture Decision and Migration Gate

**Date:** 16 November 2026  
**Repository baseline:** `e9f04947af8c26b1b87e82c9953f041c20b03e88` (merge of PR #341)  
**Branch:** `feat/canonical-rule-identity-registry-2026-11-16`  
**Status:** Architecture approved for implementation planning; data migration NOT approved or performed.  
**Scope:** Identity only. This document does not approve legal propositions, evaluator behavior, scoring, or production data changes.

## 1. Decision

Every legally distinct compliance obligation must receive its own permanent canonical identity. Existing textual rule IDs remain preserved as historical aliases; they are not renamed, deleted, recycled, or silently reassigned.

Use an opaque UUID as the immutable machine identity. A human-readable label may be added for display, but must not encode a statutory section or other mutable legal proposition. Legal sources, provisions, effective periods, evaluator versions, and rule revisions are separate records linked to the identity.

Canonical identity is not the same as:
- a rule's current display name;
- a statutory citation or section number;
- a particular legal revision;
- an evaluator implementation or Python function;
- a product scoring approval; or
- independent counsel verification.

One identity represents one legally distinct obligation. A statutory amendment may create a new revision of that obligation; a genuinely distinct duty receives a different identity. A split or merger requires an explicit, approved, append-only identity decision.

## 2. Evidence inspected

The following repository artifacts were inspected at the baseline above:

- `app/models/rules.py`: `LegalRule.rule_id` is unique text; `LegalRuleVersion.rule_id` references it. Existing `LegalRuleVersion` snapshots are not an immutable, effective-dated legal-rule revision model.
- `app/models/compliance.py`: `ComplianceFlag.rule_id` is stored as text alongside `rule_version`, statutory basis and finding detail. The ORM model does not itself provide a canonical identity FK.
- `app/models/legal_provenance.py`: source mappings, deadline definitions and release events reference `legal_rules.rule_id`.
- `app/models/rescue_audit_log.py` and migration history: rescue audit records also retain textual rule IDs.
- `scripts/seed_rules.py`: 85 unique seed rule IDs.
- `tools/audit_rule_parity.py`: compares engine, seed, database and API rule identifiers and selected metadata fields.
- `docs/audits/ILRMF_85_RULE_MASTER_RECONCILIATION_2026-11-15.md`: reports 85 seed IDs, 86 database inventory rows, 85 canonical seed IDs present, and one extra database-only `INC-002`.
- `docs/release/PRODUCTION_RULE_METADATA_AUDIT_2026-11-12.md` and its CSV artifacts: 269 active metadata mismatches across 85 IDs, plus the historical identity difference; the separate disposition file is not a canonical identity approval.
- `docs/legal/legal_approval_register.yaml`: all 85 entries remain `REVIEW_REQUIRED`; independent counsel approval is not established.

A read-only Neon audit transaction was run on project `rapid-bonus-26545234`, branch `br-purple-fog-aodj8s04`, database `neondb`, as `nlc_ci_audit_role`. The transaction explicitly set `READ ONLY`. The role has SELECT access to the audit inventory view, not to `public.compliance_flags`; therefore historical finding-level attribution was not inspected and must not be inferred.

## 3. Confirmed identity collision and unresolved legacy ID

### 3.1 `INC-001` is a direct semantic collision

The inspected seed definition describes:

- Seed/engine ID: `INC-001`
- Name: “MoA/AoA Registration Status Requires Verification”
- Cited provision: Companies Act 1994, section 23.

The inspected production audit inventory row describes:

- Database ID: `INC-001`
- Name: “Certificate of Incorporation Not Obtained”
- Cited provision: Companies Act 1994, section 9.

These are not established as equivalent obligations. They must not share one canonical identity merely because the same text identifier was used. The database catalogue row and the seed/engine proposition require separate candidate canonical identities, subject to source and evaluator review.

**Critical historical constraint:** existing findings may store only `rule_id = 'INC-001'`. The available read-only audit role cannot inspect those rows or prove whether each finding originated from the seed/engine proposition or the database catalogue definition. Therefore, no historical `INC-001` finding may be automatically assigned to either candidate identity. Keep its raw historical ID and mark canonical resolution `AMBIGUOUS` until finding-level evidence uniquely resolves it.

### 3.2 Database-only `INC-002`

The production inventory contains an additional row:

- ID: `INC-002`
- Name: “Memorandum and Articles Not Filed”
- Cited provision: Companies Act 1994, section 11
- Inventory state observed: active; verification status `ACTIVE`.

This ID is absent from the 85-rule seed. Its active database status is not proof of independent counsel approval. Treat it as a separate unresolved legacy obligation candidate; do not merge it with section 9 or section 23 obligations, and do not silently include it in the 85-rule catalogue. Its legal proposition, scope, effective history, and historical references require separate review.

### 3.3 Remaining 84 seed IDs

The reconciliation audit reports broad field-level differences between seed and production metadata. Text differences are not proof of identity collisions, and exact ID matches are not proof of legal equivalence. Until rule-by-rule semantic review is complete, preserve each source definition and classify identity equivalence as `UNRESOLVED`; do not bulk-merge or bulk-rekey.

## 4. Target data model

Implement these additive, append-only identity structures in a later migration:

### `legal_rule_identities`

- `id UUID PRIMARY KEY`: permanent canonical identity.
- `jurisdiction`: e.g. `BD`.
- `obligation_key`: optional stable human-readable label, unique and immutable once published.
- `identity_status`: `ACTIVE`, `RETIRED`, `QUARANTINED`.
- `created_at`, `created_by`, `creation_basis`.

Do not derive the UUID from a section number, rule name, seed order, or mutable definition.

### `legal_rule_aliases`

- `id UUID PRIMARY KEY`.
- `canonical_rule_id UUID REFERENCES legal_rule_identities(id)`.
- `source_namespace`: e.g. `engine-v2.2`, `seed-commit:<sha>`, `production-catalogue:<snapshot>`, or a named import/source system.
- `historical_rule_id`: exact original string, preserved byte-for-byte after agreed normalization policy.
- `valid_from`, `valid_to`: optional temporal scope of that alias mapping.
- `resolution_status`: `RESOLVED`, `AMBIGUOUS`, `UNRESOLVED`, `RETIRED`.
- `mapping_basis`, `evidence_ref`, `evidence_hash`.
- `approved_by`, `approved_at`.

An alias is unique within its source namespace and applicable validity interval. A single historical text ID may map to different canonical identities in different source namespaces or time intervals. Ambiguous mappings must remain ambiguous; never choose the first row returned.

### `legal_rule_revisions`

- `id UUID PRIMARY KEY`.
- `canonical_rule_id UUID REFERENCES legal_rule_identities(id)`.
- `revision_number`, `effective_from`, `effective_to`.
- `legal_source_revision_id` and exact provision mapping.
- `definition_json` and immutable definition hash.
- `evaluator_name`, `evaluator_version`, evaluator artifact/commit hash.
- `approval_state`, `approval_evidence`, `created_at`.

Use exclusion/uniqueness constraints to prevent overlapping effective intervals for the same identity and revision-selection scope, while supporting legally valid concurrent jurisdiction/company-class scopes where needed. Revision immutability must be enforced at the database boundary.

### Historical finding resolution

Do not overwrite `compliance_flags.rule_id`. Add a nullable canonical FK only after the identity registry exists, or use a separate append-only `finding_rule_identity_resolutions` table containing:

- finding ID and original `rule_id`;
- canonical identity, if resolved;
- source namespace / evaluator build / rule revision context;
- resolution state and rationale;
- evidence hash and reviewer approval;
- timestamp and superseding resolution reference.

Only uniquely supported mappings may be backfilled. An unresolved or ambiguous historical finding remains queryable with its raw ID and must not be silently included in canonical aggregates.

## 5. Alias resolution contract

Resolution input must include more than a bare string whenever collision is possible:

`(source_namespace, historical_rule_id, effective_date, source/evaluator context)`

Resolver outcomes:

- `RESOLVED`: exactly one approved identity matches the full context.
- `AMBIGUOUS`: more than one candidate remains.
- `UNRESOLVED`: no approved mapping exists.
- `RETIRED`: alias is known but no longer valid for new use.

No fallback to name similarity, section similarity, insertion order, current active status, or a “closest” ID. An `AMBIGUOUS` or `UNRESOLVED` result must block canonical scoring attribution and remain visible for human review.

## 6. Migration sequence — no production write authorized

1. **Complete inventory:** read-only enumerate every rule-ID occurrence and FK/dependency across all schemas, findings, evaluation runs, evidence, rescue logs, versions, release events, source mappings, deadlines, APIs, PDFs, exports, caches and archived snapshots.
2. **Preserve evidence:** export immutable, hashed snapshots with exact environment, database branch, query, role and timestamp. Obtain authorized finding-level access through a dedicated read-only audit projection; do not broaden the current audit role casually.
3. **Build collision matrix:** classify each source namespace + historical ID as same obligation, distinct obligation, temporal successor, split, merge, or unresolved. Include counts of historical findings per candidate.
4. **Approve identity decisions:** product-owner approval for product identity; independent Bangladesh counsel approval for legal equivalence/proposition. These are separate approvals.
5. **Add identity tables:** additive migration only; no rename, deletion, alias overwrite, score change or rule-definition update.
6. **Link catalogue and revisions:** create identities and revisions from approved manifests; preserve original catalogue row IDs and snapshots.
7. **Dual-write / dual-read:** engine and API emit canonical identity plus original historical ID; legacy consumers continue to receive the original field during compatibility period.
8. **Resolve historical findings:** backfill only uniquely proven records; quarantine ambiguous records without changing their historical content.
9. **Prove parity and replay:** compare counts, FK coverage, alias uniqueness, identity resolution, score outputs and historical replay before/after.
10. **Release:** only after exact-head CI, migration restore rehearsal, application compatibility, tenant RLS, audit-role checks and rollback evidence pass.

## 7. Required tests and release gates

- Every legally distinct obligation has exactly one canonical UUID.
- No canonical identity is assigned to two distinct obligations.
- Aliases are preserved and namespace-scoped; ambiguous duplicates are representable but cannot resolve silently.
- No alias can be reused for a different obligation without a superseding, audited decision.
- Existing historical `rule_id`, finding IDs, timestamps, evidence snapshots, scores and hashes remain unchanged.
- All FK dependencies and non-FK textual references are inventoried.
- Historical replay reproduces prior outputs using the original evaluator/revision context; unresolved historical identity does not fabricate a replay.
- Effective-date selection is deterministic and rejects overlapping or missing revision intervals.
- Tenant RLS and least-privilege audit projections prevent cross-tenant exposure.
- No identity migration changes legal verification status, product scoring approval, scoring configuration or statutory conclusions.
- Production parity is measured against the exact target branch and database; CI-only success is insufficient.

## 8. Current disposition

| Item | Finding | Disposition |
|---|---|---|
| 85 seed IDs | Unique textual IDs | Candidate inventory only; identity assignment requires proposition-level review |
| Production `INC-001` | Section 9 certificate obligation | Distinct candidate from seed `INC-001`; historical mapping ambiguous |
| Seed/engine `INC-001` | Section 23 MoA/AoA registration verification | Distinct candidate; historical mapping ambiguous |
| Production `INC-002` | Section 11 MoA/AoA filing obligation | Extra legacy candidate; legal status unresolved |
| Other 84 seed IDs | Metadata divergence exists | Do not infer identity merges from text diffs |
| Historical finding attribution | Finding table not accessible to audit role | BLOCKED pending authorized read-only finding inventory |
| Immutable effective-dated revision model | Not established in inspected ORM | Required separate implementation |
| Legal approval | All 85 entries `REVIEW_REQUIRED` in inspected register | No counsel sign-off claimed |

**Decision:** proceed with the identity registry design and collision inventory. Do not execute a data migration, alter production rows, change evaluator IDs, or promote legal/scoring status until the finding-level inventory and rule-by-rule identity decisions are approved.


## 9. Engineering implementation added to PR #344

The branch now contains an additive first implementation:

- `app/models/rules.py`: ORM models `LegalRuleIdentity`, `LegalRuleAlias`, and `LegalRuleRevision`.
- `app/models/__init__.py`: exports the three new models for metadata registration.
- `alembic/versions/0114_canonical_rule_identity_registry.py`: additive migration chained after `0113_score_history_append_only`; creates the three registry tables, UUID keys, foreign keys, status/validity checks, uniqueness constraints, lookup indexes and database-level UPDATE/DELETE rejection.
- `tests/unit/test_canonical_rule_identity_models.py`: structural tests for UUID identity, namespace-scoped alias collision representation, effective dates, evaluator separation and `lazy="raise"` relationships.

The migration deliberately creates **zero identity or alias rows**. It does not backfill any of the 85 seed IDs, the production-only `INC-002`, or any historical finding. Existing `legal_rules.rule_id`, `legal_rule_versions.rule_id`, compliance findings, source mappings and rescue audit records remain untouched.

### 9.1 Known implementation limitations — must be resolved before production use

1. The registry tables are not yet wired into the runtime alias resolver, API, evaluator, evidence records or historical replay.
2. No identity lifecycle/supersession event table exists yet. The initial identity, alias and revision rows are immutable; retirement/correction must be represented by append-only events before lifecycle operations are enabled.
3. Effective interval overlap is not yet prevented by a database exclusion constraint. The current check only rejects an inverted interval; overlapping revisions must be rejected by a later constraint/resolver and test before date-selected evaluation is enabled.
4. No tenant-facing or application-role grants/RLS policies are added. The registry remains unavailable to application code until a least-privilege access design is reviewed.
5. The migration and tests have not yet been run in CI or against an isolated PostgreSQL restore. No migration success is claimed.
6. Model metadata/migration parity and exact Alembic single-head status still require CI verification.

**Status:** schema foundation only, pending CI and independent review. This is not a production-ready identity resolver or approved legal catalogue.
