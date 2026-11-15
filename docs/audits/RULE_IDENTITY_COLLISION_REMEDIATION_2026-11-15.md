# Rule Identity Collision Remediation — 2026-11-15

## Scope

This change addresses the two identity collisions confirmed by the read-only
Neon audit inventory. It does not revise statutory interpretations.

| Identity | Legacy meaning | Disposition |
|---|---|---|
| INC-001 | Certificate of Incorporation Not Obtained; Companies Act 1994, s.9 | Preserve exact legacy payload under a namespaced legacy key; restore canonical seed identity for MoA/AoA registration verification, s.23 |
| INC-002 | Memorandum and Articles Not Filed; Companies Act 1994, s.11 | Preserve exact legacy payload under a namespaced legacy key; retain row inactive and never reuse the ID |

## Safety properties

- Migration 0112 is forward-only and chained after 0111.
- It archives the full legal_rules row before any mutation.
- It only transforms exact known legacy definitions; unknown variants abort.
- It checks for foreign-key dependants and aborts if any exist.
- It does not delete rule rows or rewrite historical evaluation snapshots.
- Unbound historical snapshots remain ambiguous. They must not be replayed as
  the new canonical INC-001 merely because the visible ID is the same.
- Canonical INC-001 remains NOT_EVALUATED, zero score impact, no BLACK override,
  and PENDING verification. No statutory conclusion is promoted.

## Operational boundary

The migration has not been applied to Neon or Render. The read-only audit role
cannot inspect underlying application tables or establish every non-FK
reference. CI, a full-privilege schema/dependency preflight, isolated restore
rehearsal, and verification of the actual Render database target are required
before deployment. The migration itself repeats the FK preflight and fails
closed.

## Acceptance criteria

1. The archive contains the exact pre-migration INC-001 and INC-002 payloads.
2. Active canonical IDs equal the 85-rule engine/seed/registry set.
3. INC-002 is inactive and remains queryable in the archive.
4. INC-001 active row matches the canonical seed definition.
5. No historical outcome snapshot is rewritten or silently reinterpreted.
6. The migration has been tested on an isolated restored database before
   production rollout.