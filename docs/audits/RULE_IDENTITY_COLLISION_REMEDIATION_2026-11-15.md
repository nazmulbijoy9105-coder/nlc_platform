# Rule Identity Collision Remediation — 2026-11-15

## Scope

This patch addresses two confirmed rule-ID collisions, historical-reference
inventory, and SQLAlchemy relationship-loading observability. It does not
revise statutory interpretations or claim historical attribution.

| Identity | Existing legacy meaning | Safe disposition |
|---|---|---|
| INC-001 | Certificate of Incorporation Not Obtained; Companies Act 1994, s.9 | Archive exact payload and quarantine the existing row without changing its identity or statutory meaning |
| INC-002 | Memorandum and Articles Not Filed; Companies Act 1994, s.11 | Archive exact payload and quarantine the existing row; never reuse the ID |

## Why the first migration approach was rejected

The earlier migration attempted to replace the INC-001 definition in place.
CI exposed five FK dependants: `legal_rule_versions.rule_id`,
`compliance_flags.rule_id`, `legal_rule_source_mappings.rule_id`,
`legal_deadline_definitions.rule_id`, and
`legal_rule_release_events.rule_id`.

Those are real historical relationships, not disposable blockers. Removing the
FK guard and rewriting the row would silently change what those records appear
to reference. This patch therefore preserves the legacy row's rule ID, name,
statutory basis and condition. It archives the exact payload and changes only
the operational quarantine fields: inactive, NOT_EVALUATED, zero score impact,
no BLACK override, and PENDING verification.

Canonical INC-001 cannot be activated under the same ID until a separately
reviewed migration can preserve the existing foreign-key and non-FK reference
semantics. Do not seed over or overwrite this row.

## Historical attribution

`scripts/audit_rule_historical_attribution.py` scans public-schema text,
character, JSON, JSONB and array columns for INC-001 and INC-002. It reports
record locators without exporting row contents. Each hit remains
`UNATTRIBUTED`: a rule-ID match alone does not bind the exact historical
definition, evaluator build, timestamp, input facts, evidence or integrity
proof.

Required future outcomes: `ATTRIBUTED`, `PARTIALLY_ATTRIBUTED`,
`AMBIGUOUS`, `UNATTRIBUTED`. No automatic promotion is implemented.

## SQLAlchemy relationship audit

`scripts/audit_orm_relationship_loading.py` imports the complete ORM registry,
runs `configure_mappers()`, and reports every relationship's target,
direction, cardinality, loader strategy, back-populates, view-only state,
cascade and local FK columns. It flags:

- `ASYNC_LAZY_LOAD_RISK`: implicit lazy SELECT may cause MissingGreenlet.
- `IMPLICIT_COLLECTION_EAGER_LOAD`: default select-in collections may fan out.
- `EXPLICIT_LOADER_REQUIRED`: relationship is configured with lazy=raise.
- `BACK_POPULATES_MISMATCH`: reciprocal ORM mapping is inconsistent.

This is an inventory and regression guard, not a claim that every runtime
service query has been optimized. Query-callsite profiling and per-endpoint
loader plans remain separate verification work.

Run:

```bash
python scripts/audit_orm_relationship_loading.py --json-output artifacts/orm-relationship-loading.json
```

## Safety properties

- Migration 0115 follows the existing 0114 revision.
- Existing FK relationships remain attached to the unchanged legacy identity.
- No historical findings, flags, version rows, source mappings, deadline
  definitions, release events or evaluation snapshots are rewritten/deleted.
- INC-001 and INC-002 are quarantined from scoring rather than relabelled.
- No counsel allowlist is introduced into scoring.
- Historical reference and ORM audits are read-only.

## Release gates

1. Full Alembic DAG and fresh PostgreSQL upgrades pass.
2. Migration is rehearsed on an isolated restore containing the five FK relationships.
3. Historical reference inventory is run against the actual restored runtime schema.
4. Every candidate reference is reviewed; no finding is attributed from ID alone.
5. ORM relationship inventory is reviewed alongside service query callsites and endpoint query-count tests.
6. Canonical 85-rule manifest, engine and database parity are reconciled without overwriting the quarantined legacy identity.

No Neon or Render database has been changed. This PR is not approval to run a
production migration and does not claim that historical attribution is complete.
