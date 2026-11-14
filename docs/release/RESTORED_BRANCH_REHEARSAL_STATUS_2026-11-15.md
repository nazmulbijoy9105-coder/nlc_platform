# Restored Neon Branch — Rehearsal Readiness Status

**Read-only recheck:** 15 November 2026  
**Project:** `rapid-bonus-26545234`  
**Restored branch:** `br-little-cake-aovrrz0y`  
**Production branch:** `br-purple-fog-aodj8s04`  
**Database:** `neondb`

## 1. Restored branch, before migration

| Item | Observed |
|---|---:|
| Alembic revision | `0042_dedup_key` |
| Companies | 23 |
| Users | 13 |
| Compliance flags | 434 |
| Score-history rows | 51 |
| Legal-rule rows | 75 |
| `webhook_endpoints` | Present; 10 columns; 0 rows |
| `webhook_deliveries` | Present; 13 columns; 0 rows |
| `rescue_audit_log` | Present; 12 columns; 0 rows |

All three historical tables are owned by `nlc_migration_owner`, with RLS enabled and forced. Their comments explicitly identify them as **schema-only reconstructions with historical rows unrecovered**.

The original 0037/0038 indexes were present:
- `webhook_endpoints`: primary key, `idx_webhook_endpoints_user`, `idx_webhook_endpoints_active`
- `webhook_deliveries`: primary key, `idx_webhook_deliveries_endpoint`, `idx_webhook_deliveries_pending`, `idx_webhook_deliveries_retry`
- `rescue_audit_log`: primary key, `ix_rescue_audit_log_plan_id`, `ix_rescue_audit_log_actor_id`, `ix_rescue_audit_log_finding_id`, `ix_rescue_audit_log_created_at`

Foreign-key delete actions match the original 0037/0038 semantics: webhook endpoint/user and delivery/endpoint use CASCADE; rescue plan uses CASCADE; finding uses SET NULL; actor user uses RESTRICT.

The NLC application role has no SELECT/INSERT/UPDATE/DELETE grants on these three historical evidence tables at the 0042 restore point. This is consistent with the 0037/0038 migration intent to keep these tables closed until signed RLS policies are installed later.

## 2. Production branch, read-only comparison

| Item | Observed |
|---|---:|
| Alembic revision | `0112_runtime_acl_and_alembic_rls` |
| Companies | 23 |
| Users | 13 |
| Compliance flags | 549 |
| Score-history rows | 74 |
| Legal-rule rows | 86 |
| `webhook_endpoints` | 0 rows; schema-only reconstruction |
| `webhook_deliveries` | 0 rows; schema-only reconstruction |
| `rescue_audit_log` | 0 rows; schema-only reconstruction |

The repository migration head is `0114_annual_return_filing_status_provenance`. Production is therefore two revisions behind the repository head. No production migration is authorised by this status note.

## 3. Rehearsal-script correction

The rehearsal script previously pinned its expected head to `0112_runtime_acl_and_alembic_rls`, which no longer matches the repository's single Alembic head. The PR updates it to `0114_annual_return_filing_status_provenance` and adds a regression test that compares:
1. the rehearsal expected head with the actual Alembic graph head; and
2. the rehearsal's 0042 preflight column set with `alembic/env.py`'s historical-evidence guard.

The 0042 schema preflight must reflect the original 0037/0038 shape. In particular, `webhook_deliveries.updated_at` is **not** present in migration 0037; migration 0044 adds it after the historical-schema guard has passed. The 0042 preflight must not require a post-0044 column.

## 4. What is and is not proven

**Proven by read-only inspection:**
- The restored branch remains at 0042.
- The three 0037/0038 tables and their original indexes/FK actions now exist on the restore branch.
- They are empty schema-only reconstructions, not recovered historical data.
- The same three tables are empty schema-only reconstructions on production.
- Runtime app role has no direct grants on those evidence tables at the restore point.
- Production is at 0112 while the repository head is 0114.

**Not yet proven:**
- Alembic upgrade from this exact restored Neon branch through 0114.
- Post-upgrade row-count preservation and final schema/role/RLS audit on the restored branch.
- Render currently uses the intended `nlc_app_role` database identity.
- Historical webhook deliveries, endpoint configuration or rescue audit rows can be recovered from an external backup.

The empty schema-only tables must never be interpreted as proof that no webhook or rescue events occurred. Historical records can only be restored from a verified backup/archive; a migration cannot recreate missing evidence.

## 5. Controlled next step

After the PR containing the rehearsal-script correction passes CI, manually run the existing GitHub Actions workflow **Neon restored snapshot rehearsal**:

`https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/workflows/neon-restored-snapshot-rehearsal.yml`

The workflow is pinned to the restored branch and requires the restored migration URL, app-role URL and RLS HMAC secret. It migrates only the restored branch, records before/after row counts, audits role/RLS/view/evidence-table state and tests app-role spoof resistance. It must return PASS before any production migration is considered.

**No Alembic migration was executed against the restored or production branch during this read-only recheck.**
