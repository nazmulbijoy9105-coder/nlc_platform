# Production E2E closure checklist

Use this after the product release candidate is on `main`. Product-owner attestation and product scoring release are not independent legal/source verification. `VERIFIED_RULE_IDS` currently represents the owner-attested product inventory and must not be cited as proof of signed counsel review; record independent counsel/source verification separately when it exists.  
**Do not mark an item done without command output, SHA, and timestamp.**

## 1. Deploy alignment
- [ ] Note git SHA on `main`
- [ ] Confirm CI completed successfully for the current `main` SHA; the GitHub Actions deploy hook runs only after CI success (native Render autoDeploy remains disabled)
- [ ] Confirm Render deployment ID and deployed commit SHA correspond to the successful CI-tested `main` revision
- [ ] Confirm `/api/v1/health/live` and `/api/v1/health/ready`
- [ ] Confirm Vercel deployment SHA for `nlc_frontend`

## 2. Rule catalogue parity (75 → 85)
Read-only first:
```bash
python tools/audit_rule_parity.py
# or production-parity workflow
```
Expected: engine 85, seed 85, DB active catalogue aligned; legacy `INC-002` not active.
If migration `0049` / `0090` not applied, apply only via Alembic on a reviewed change window — no hand INSERT to force parity.

## 3. Evidence tables
```sql
SELECT tablename FROM pg_tables
WHERE schemaname='public'
  AND tablename IN ('webhook_endpoints','webhook_deliveries','rescue_audit_log');
```
If missing: follow `BACKUP_DISASTER_RECOVERY.md` — restore to disposable Neon branch first; do not create empty tables and call it recovery.

## 4. RLS + app role
```bash
psql "$DATABASE_URL" -f scripts/provision_nlc_roles.sql
psql "$DATABASE_URL" -f scripts/audit_nlc_role_memberships.sql
APP_DATABASE_URL=... python verify_rls.py
APP_DATABASE_URL=... python verify_tenant_isolation.py
```

## 5. Isolated restore rehearsal
```bash
python3 scripts/verify_backup.py ./nlc-postgres-....dump
# restore only to disposable branch URL
```
Record archive checksum, row counts for evidence tables, Alembic revision, RLS results.

## 6. Score path smoke
- Evaluate a company with known-good profile → `final_score` + `category_deductions`
- Company with sparse data → UNKNOWN flags, coverage messaging, no false “fully compliant” claim
- Frontend shows category deductions (not summed module scores)

## 7. Explicit non-claims
- Product score is not a Bangladesh legal certificate
- Input coverage is not % of rules verified
- Git green is not production restore proof
