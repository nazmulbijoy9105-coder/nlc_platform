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
- Database: 86 unique active IDs; one extra legacy INC-002. All 85 canonical seed IDs are present, but ID presence is not definition parity.
- All 85 seed IDs are present in the database; field-level differences are recorded row by row. Exact string comparison found: 45 name mismatches, 12 rule-type mismatches, 69 statutory-basis mismatches, 57 trigger mismatches; 78 of 85 canonical IDs differ in at least one of those four fields. Exact string difference is a triage signal, not by itself proof of legal non-equivalence.
- Legal approval remains pending for all 85 canonical rules.
- Live DB version labels: 1.1 = 60 rows; 2.1 = 20 rows (including the database-only INC-002); 2.2 = 6 rows. These labels are not authoritative legal revision identities.
- Verification statuses: 85 canonical rows are PENDING; the extra database-only INC-002 is ACTIVE. The repository parity script declares INC-002 a known inactive legacy ID, so the live `is_active=true` value conflicts with that repository expectation.
- Live DB NULL conditions: 23 rows (17 at DB label 1.1 and 6 at 2.2); no statutory-basis fields are null in the audit projection.
- The database-only INC-002 is currently active with verification_status ACTIVE; this is not counsel approval and its section 11 proposition is not part of the 85-rule canonical seed.
- At least one direct identity collision is visible: database INC-001 is "Certificate of Incorporation Not Obtained" (section 9), while seed INC-001 is "MoA/AoA Registration Status Requires Verification" (section 23). Do not merge, overwrite or re-key these without an identity and historical-reference plan.
- A NULL live DB condition is not cured by a non-NULL seed condition; each must be explicitly classified and resolved. The 23 affected database IDs are AGM-007, AUD-005, BNK-001, BNK-002, BNK-003, BSEC-001, BSEC-002, BSEC-003, BSEC-004, CHG-001, DEF-001, DEF-002, DIR-006, ESC-004, ESC-005, FX-001, LBR-001, LBR-002, LBR-003, STR-001, STR-002, STR-003 and TL-002.
- No authoritative immutable, effective-dated LegalRuleRevision model is established by the inspected architecture. LegalRuleVersion snapshots are historical audit snapshots; current LegalRule rows remain mutable.
- Keep independent counsel verification separate from the scoring gate as instructed; preserve evidence provenance, fact verification, identity controls, human review and product-policy override governance.

## Fields and gates
- seed_*: canonical bootstrap source at pinned commit.
- db_*: least-privilege live inventory projection.
- *_match: exact comparison only, not legal equivalence.
- effective_dated_immutable_rule_revision and source_revision_bound_to_rule_revision: unproven until revision-specific model and FK chain are demonstrated.
- The seed `check_fn` strings are metadata labels, not proof of callable engine functions. `tools/engine_introspection.py` is designed to exercise engine profiles and extract actual emitted rule IDs, but this audit did not execute that runtime introspection; therefore evaluator-to-rule semantic coverage remains OPEN.
- Before statutory scoring: source/amendment chain; effective-date selection; applicability/exceptions; evidence/fact contract; deterministic evaluator tests; historical replay; counsel sign-off.