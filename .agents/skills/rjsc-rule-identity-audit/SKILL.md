---
name: rjsc-rule-identity-audit
description: Audit the identity, source mapping and runtime parity of NLC legal rules. Use for the 85-rule catalogue, canonical IDs, legacy aliases, duplicate detection, source-to-rule traceability and rule registry reconciliation.
---

# RJSC rule identity audit

## Objective
Establish whether each rule identity is consistently represented across canonical registry, typed rules, legacy rules, seed data, database records, API responses, evaluation and reports. Identity consistency does not establish legal correctness.

## Required method
1. Obtain a frozen commit SHA and a read-only inventory of every rule population.
2. Build the union of identities; never assume either typed or legacy population is authoritative.
3. Map canonical ID, historical IDs/aliases, runtime IDs, source IDs and database primary keys.
4. Detect collisions, duplicate semantic rules, orphan rules, missing aliases, many-to-one and one-to-many mappings.
5. Compare legal proposition, trigger, company applicability, exceptions, evidence contract, consequence, effective dates and evaluation semantics.
6. Trace each identity through seed/import, registry, engine, API, tenant snapshot, PDF/report and audit history.
7. Verify deterministic behavior with fixtures and property tests. Record test command, commit, environment and result.
8. Separate identity defects from legal interpretation defects and implementation defects.

## Required output
One row per canonical identity with:
canonical_id | aliases | typed_runtime_id | legacy_runtime_id | source_ref | applicability | exceptions | evidence_contract | legal_consequence | seed_status | DB_status | evaluator_status | report_status | defect_class | evidence | owner | disposition

Also report total populations, reconciliation arithmetic, unmatched records, collisions and limitations.

## Acceptance gates
- No unexplained identity collision or silent overwrite.
- Every alias resolves to exactly one canonical identity.
- All populations reconcile with explicit inactive/historical status.
- Runtime and report traces are demonstrated, not inferred from catalogue counts.
- Any unresolved identity remains explicitly unresolved.

## Prohibitions
Do not declare all rules legally verified, applicable to every private company, or production-ready because counts match. Do not delete historical identities to make parity pass. Do not auto-correct a legal proposition without counsel-approved evidence.
