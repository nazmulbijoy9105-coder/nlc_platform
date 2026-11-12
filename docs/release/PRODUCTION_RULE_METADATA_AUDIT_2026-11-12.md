# Production rule metadata mismatch audit — 12 November 2026

**Repository baseline:** `main` at `95223789e7ecf581ff514d2e49ce9db76daab4cb`  
**Database:** Neon project `rapid-bonus-26545234`, branch `br-purple-fog-aodj8s04`, database `neondb`  
**Database role:** `nlc_ci_audit_role`; transaction started with `SET TRANSACTION READ ONLY`  
**Production Alembic revision:** `0110_legal_provenance_acl` (previously verified)  
**Canonical seed file:** `scripts/seed_rules.py`  
**Comparison fields:** same nine fields as `tools/audit_rule_parity.py::DB_PARITY_FIELDS`.

## Result

- Parsed seed definitions: **85**
- Database rows: **86**
- Active database rows: **85**
- Inactive historical rows: **INC-002**
- Active rule metadata mismatches across the 85 active IDs: **269**
- Additional historical identity difference: **1** (`INC-002` is inactive in DB and intentionally absent from the 85-rule seed)
- Database verification status: **all 86 rows PENDING**
- Fail-closed score state: **all rows NOT_EVALUATED / 0 / no BLACK override**

## Mismatches by field

| Field | Count |
|---|---:|
| `statutory_basis` | 69 |
| `description` | 77 |
| `rule_condition` | 59 |
| `rule_name` | 43 |
| `revenue_tier` | 9 |
| `rule_type` | 12 |
| `seed_definition` | 1 |
| **Total** | **270** |

## Interpretation

This is a field-level comparison report, not a legal opinion and not a canonical-source decision. The seed and production definitions diverge in names, statutory bases, descriptions, evaluator conditions, rule types and revenue tiers. Some differences may be intentional hardening or historical database evolution; others are likely metadata drift or legal-citation defects. Do not overwrite either side wholesale.

The CSV records each differing value exactly as observed. A reviewer must assign a disposition per row/field:
- `KEEP_SEED`
- `KEEP_DATABASE`
- `REWRITE_WITH_SOURCE`
- `REQUIRES_PRODUCT_OWNER_DECISION`

Where the disposition is `REWRITE_WITH_SOURCE`, include official source URI, source version, provision citation, effective interval and rationale in the follow-up manifest. A parity match alone does not establish legal correctness or independent counsel verification.

## Safety constraints

- Preserve the 85 active identities and inactive historical `INC-002`.
- Do not modify the product-owner release ledger or legal verification state.
- Do not change production rows or run migrations from this audit.
- Keep all production score fields fail-closed until the separate approved release semantics authorize them.
- Any eventual metadata correction must be a forward-only Alembic migration with exact-head CI, idempotency tests, historical identity preservation and production parity evidence.

## Artifact

See [production_rule_metadata_mismatches_2026-11-12.csv](./production_rule_metadata_mismatches_2026-11-12.csv) for all 270 field-level differences.
