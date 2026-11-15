# Rule Identity Collision Remediation — 2026-11-15

## Scope

This patch addresses two confirmed identity collisions and adds a read-only
inventory tool for historical references. It does not revise statutory
interpretations or claim historical attribution.

| Identity | Legacy meaning | Disposition |
|---|---|---|
| INC-001 | Certificate of Incorporation Not Obtained; Companies Act 1994, s.9 | Preserve exact legacy payload under a namespaced legacy key; restore canonical seed identity for MoA/AoA registration verification, s.23 |
| INC-002 | Memorandum and Articles Not Filed; Companies Act 1994, s.11 | Preserve exact legacy payload under a namespaced legacy key; retain row inactive and never reuse the ID |

## Migration graph correction

The first draft used revision ID 0112, which collided with the existing
`0112_runtime_acl_and_alembic_rls` migration. The remediation migration is
therefore assigned revision `0115_rule_identity_collision_reconciliation`
after `0114_annual_return_filing_status_provenance`. The migration graph must
still pass the repository's complete DAG audit and isolated PostgreSQL upgrade
checks before merge.

## Historical attribution is separate

Archiving a rule definition is not proof that any historical finding was
generated under that definition. Rule-ID matches alone are insufficient.

The read-only tool
`scripts/audit_rule_historical_attribution.py` scans public-schema text,
character, JSON, JSONB and array columns for references to INC-001 and INC-002.
It reports table/column/primary-key locators without exporting row contents.
Tables without primary keys use an ephemeral CTID locator and are explicitly
reported. The script requires
`NLC_HISTORICAL_AUDIT_DATABASE_URL`, starts a read-only transaction, and
intentionally does not fall back to `DATABASE_URL`.

Every discovered reference is classified `UNATTRIBUTED`. That is deliberate:
the scan establishes presence, not the exact immutable rule definition,
evaluator build, evaluation inputs or evidence. A later controlled review may
upgrade a record only when all required links are independently supported.

Required attribution evidence:

- Exact rule definition/revision active at evaluation time.
- Evaluator implementation/version (and deployed code identity).
- Evaluation timestamp and applicable legal/source version.
- Input facts and their provenance.
- Finding payload and evidence references.
- Integrity evidence binding the record to its evaluation.

Allowed outcomes for a future attribution register are
`ATTRIBUTED`, `PARTIALLY_ATTRIBUTED`, `AMBIGUOUS` and `UNATTRIBUTED`.
No automatic transition is implemented by this patch.

## Safety properties

- Migration 0115 is forward-only and follows the current 0114 head.
- It checks required `legal_rules` columns before mutation.
- It archives the complete pre-migration legal_rules payload.
- It rejects unknown/partially canonical INC-001 states and incomplete INC-002
  states rather than guessing.
- It checks FK dependants and aborts if any exist.
- It does not update/delete historical findings, flags or evaluation snapshots.
- The read-only historical reference scan never changes database state.
- Canonical INC-001 remains NOT_EVALUATED, zero score impact, no BLACK override,
  and PENDING verification. No statutory conclusion is promoted.

## Operational boundary

No Neon or Render database has been changed by this patch. The actual Render
runtime database target, complete non-FK reference inventory, isolated restore
rehearsal, and historical attribution review remain outstanding.

## Acceptance criteria

1. The Alembic graph has one unique head and no duplicate revision IDs.
2. The archive contains the exact pre-migration INC-001 and INC-002 payloads.
3. Active canonical IDs reconcile across engine, seed, registry and database.
4. INC-002 is inactive and remains queryable in the archive.
5. INC-001 matches the complete canonical seed fingerprint.
6. Historical references are inventoried without changing their source records.
7. No historical finding is attributed from its rule ID alone.
8. The migration has passed isolated restore and fresh PostgreSQL upgrades.
