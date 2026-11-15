# NLC ILRMF 85-Rule Master Reconciliation

Audit baseline: backend main at 986e3b47da9b14b94bbd86279190301248839661 (merged PR #340).
Engine/ILRMF version in engine.py: 2.2.
Seed identities: 85; unique: 85.
Read-only database inventory rows: 86; unique: 86.
Database IDs not in seed: INC-002.
All seeded IDs present in database: true.

## Interpretation
- This is a full row-level reconciliation of the 85 canonical seed IDs against the least-privilege database audit projection. It is not a legal opinion or proof that every evaluator is correct.
- Database version labels are retained as found; they are not treated as immutable legal-rule revisions.
- ACTIVE is not equivalent to legally approved.
- Legal approval register: all 85 entries remain REVIEW_REQUIRED. Product-owner approval is separate and does not substitute for independent Bangladesh counsel validation.
- Source revision and effective-dated rule revision are marked unproven unless bound to the specific immutable rule revision. Existing LegalSource/version metadata alone is insufficient.
- The database-only legacy ID is reported separately rather than silently added to the canonical 85.
- The database query used role nlc_ci_audit_role on branch br-purple-fog-aodj8s04; no owner/RLS bypass was attempted.

## Catalogue-level findings
- Seed: 85 unique canonical rule IDs.
- Database: 86 unique active IDs; one extra legacy INC-002.
- All 85 seed IDs are present in the database; field-level differences are recorded row by row.
- Legal approval remains pending for all 85 canonical rules.
- A NULL live DB condition is not cured by a non-NULL seed condition; each must be explicitly classified and resolved.
- No authoritative immutable, effective-dated LegalRuleRevision model is established by the inspected architecture. LegalRuleVersion snapshots are historical audit snapshots; current LegalRule rows remain mutable.
- Keep independent counsel verification separate from the scoring gate as instructed; preserve evidence provenance, fact verification, identity controls, human review and product-policy override governance.

## Fields and gates
- seed_*: canonical bootstrap source at pinned commit.
- db_*: least-privilege live inventory projection.
- *_match: exact comparison only, not legal equivalence.
- effective_dated_immutable_rule_revision and source_revision_bound_to_rule_revision: unproven until revision-specific model and FK chain are demonstrated.
- Before statutory scoring: source/amendment chain; effective-date selection; applicability/exceptions; evidence/fact contract; deterministic evaluator tests; historical replay; counsel sign-off.