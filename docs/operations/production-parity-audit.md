# Production Rule-Parity Audit Credential

The live rule-parity workflow must not use the production owner credential or the
runtime application credential. It requires a dedicated read-only Neon role
scoped only to the isolated `audit` schema created by migration 0049.

## Provision after migration 0049 is applied to production

1. In Neon, create a PostgreSQL role named `nlc_ci_audit_role`.
2. Set access to **read-only**.
3. Scope the role to database `neondb` and schema `audit` only.
4. Retrieve its connection URI and save it as the GitHub Actions secret
   `NLC_PRODUCTION_DATABASE_URL` in the `nlc_platform` repository.
5. Do not grant this role access to the `public` schema or tenant tables.

The view `audit.active_legal_rule_ids` exposes only active legal rule IDs. The
CI script compares that set with the public `/api/v1/rules?is_active=true`
endpoint.

## Verify least privilege

Using the new role, these checks must pass:

```sql
SELECT current_user, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = current_user;

SELECT count(*) FROM audit.active_legal_rule_ids;
```

Expected: `rolsuper = false`, `rolbypassrls = false`, and the view returns the
active rule count.

This query must fail with a permission error:

```sql
SELECT count(*) FROM public.companies;
```

Never use the owner URL or the runtime `nlc_app_role` URL as the CI parity
credential. The owner credential can bypass RLS; the runtime role has broader
application permissions than this audit requires.
