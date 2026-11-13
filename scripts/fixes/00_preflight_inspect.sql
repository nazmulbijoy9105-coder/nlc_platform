-- ============================================================================
-- NLC Platform — P0 Fix #00 (v3): PRE-FLIGHT INSPECTION (READ-ONLY)
-- File: scripts/fixes/00_preflight_inspect.sql
--
-- Run this FIRST in the Neon SQL Editor before running 01_migration_identity.sql.
-- 100% read-only — no CREATE, no ALTER, no GRANT.
--
-- v3 ADDITIONS:
--   - Section 1b: BYPASSRLS flag for every nlc_* role (must be false for
--     nlc_migration_user after 01_... runs)
--   - Section 3b: migration-object ownership summary — how many public-schema
--     objects are still owned by neondb_owner vs nlc_migration_owner vs others
--   - Section 11: current RLS bypass status across all roles
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. All nlc_* and neondb_owner roles — full attribute set
-- ---------------------------------------------------------------------------
SELECT
    rolname              AS role_name,
    rolcanlogin          AS can_login,
    rolsuper             AS is_superuser,
    rolcreaterole        AS can_create_role,
    rolcreatedb          AS can_create_db,
    rolinherit           AS inherits_privs,
    rolbypassrls         AS bypasses_rls,
    rolconnlimit         AS conn_limit
FROM pg_roles
WHERE rolname IN ('neondb_owner', 'nlc_app_role', 'nlc_app',
                  'nlc_migration_user', 'nlc_migration_owner')
   OR rolname LIKE 'nlc_%'
ORDER BY rolname;

-- ---------------------------------------------------------------------------
-- 1b. BYPASSRLS audit — any role with BYPASSRLS is a security concern
-- ---------------------------------------------------------------------------
SELECT
    rolname,
    rolbypassrls AS bypasses_rls,
    rolcanlogin  AS can_login,
    rolsuper     AS is_superuser
FROM pg_roles
WHERE rolbypassrls = true
  AND rolname NOT IN ('neondb_owner')   -- neondb_owner is expected to have it
ORDER BY rolname;
-- After 01_...sql runs, nlc_migration_user must NOT appear here.
-- If nlc_migration_user appears here BEFORE 01_...sql, that confirms the
-- audit finding: "nlc_migration_user still has BYPASSRLS".

-- ---------------------------------------------------------------------------
-- 2. Role memberships (who can SET ROLE to whom)
-- ---------------------------------------------------------------------------
SELECT
    r_role.rolname  AS granted_role,
    r_member.rolname AS member_role,
    m.admin_option  AS with_admin_option
FROM pg_auth_members m
JOIN pg_roles r_role   ON r_role.oid = m.roleid
JOIN pg_roles r_member ON r_member.oid = m.member
WHERE r_role.rolname LIKE 'nlc_%'
   OR r_role.rolname = 'neondb_owner'
   OR r_member.rolname LIKE 'nlc_%'
ORDER BY granted_role, member_role;

-- ---------------------------------------------------------------------------
-- 3. Who owns each table/sequence/view/function in public schema
-- ---------------------------------------------------------------------------
SELECT
    n.nspname        AS schema,
    c.relname        AS object,
    c.relkind,       -- r = table, S = sequence, f = function, v = view, m = matview
    r.rolname        AS current_owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r     ON r.oid = c.relowner
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'S', 'v', 'm', 'f')
ORDER BY c.relkind, c.relname;

-- ---------------------------------------------------------------------------
-- 3b. Migration-object ownership SUMMARY
-- ---------------------------------------------------------------------------
SELECT
    r.rolname AS owner,
    c.relkind AS object_type,
    COUNT(*)  AS object_count
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r     ON r.oid = c.relowner
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'S', 'v', 'm', 'f')
GROUP BY r.rolname, c.relkind
ORDER BY r.rolname, c.relkind;
-- EXPECTED BEFORE 01_...sql: neondb_owner owns most/all objects.
-- EXPECTED AFTER 01_...sql:  nlc_migration_owner owns all objects.

-- ---------------------------------------------------------------------------
-- 4. Schema-level privileges on public
-- ---------------------------------------------------------------------------
SELECT
    grantee,
    privilege_type,
    is_grantable
FROM information_schema.role_schema_grants
WHERE schema_name = 'public'
ORDER BY grantee, privilege_type;

-- ---------------------------------------------------------------------------
-- 5. Table-level privileges for nlc_app_role
-- ---------------------------------------------------------------------------
SELECT
    table_name,
    grantee,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privs
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND grantee IN ('nlc_app_role', 'nlc_app', 'PUBLIC')
GROUP BY table_name, grantee
ORDER BY table_name, grantee;

-- ---------------------------------------------------------------------------
-- 6. RLS status on every public-schema table (ENABLE + FORCE?)
-- ---------------------------------------------------------------------------
SELECT
    c.relname        AS table_name,
    c.relrowsecurity AS rls_enabled,
    c.relforcerowsecurity AS rls_forced,
    r.rolname        AS owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r     ON r.oid = c.relowner
WHERE n.nspname = 'public'
  AND c.relkind = 'r'
ORDER BY c.relname;

-- ---------------------------------------------------------------------------
-- 7. alembic_version specifically
-- ---------------------------------------------------------------------------
SELECT
    c.relname,
    c.relrowsecurity  AS rls_enabled,
    c.relforcerowsecurity AS rls_forced,
    r.rolname         AS owner
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_roles r     ON r.oid = c.relowner
WHERE n.nspname = 'public'
  AND c.relname = 'alembic_version';

-- ---------------------------------------------------------------------------
-- 8. Default privileges currently configured
-- ---------------------------------------------------------------------------
SELECT
    pg_get_userbyid(d.defaclrole)    AS creator_role,
    n.nspname                        AS schema,
    d.defaclobjtype                  AS object_type,
    pg_get_userbyid(a.grantee)       AS grantee,
    a.privilege_type
FROM pg_default_acl d
JOIN pg_namespace n ON n.oid = d.defaclnamespace
JOIN LATERAL aclexplode(d.defaclacl) a ON true
WHERE n.nspname = 'public'
ORDER BY creator_role, object_type, grantee;

-- ---------------------------------------------------------------------------
-- 9. Current Alembic revision
-- ---------------------------------------------------------------------------
SELECT version_num FROM alembic_version;

-- ---------------------------------------------------------------------------
-- 10. Confirm which role the Neon SQL Editor is connected as
-- ---------------------------------------------------------------------------
SELECT
    current_user,
    session_user,
    current_database(),
    current_setting('role') AS current_role_setting;

-- ---------------------------------------------------------------------------
-- 11. Comprehensive BYPASSRLS + role attribute matrix (final security view)
-- ---------------------------------------------------------------------------
SELECT
    rolname,
    CASE WHEN rolsuper THEN 'YES' ELSE 'no' END AS superuser,
    CASE WHEN rolbypassrls THEN 'YES' ELSE 'no' END AS bypass_rls,
    CASE WHEN rolcanlogin THEN 'YES' ELSE 'no' END AS can_login,
    CASE WHEN rolinherit THEN 'YES' ELSE 'no' END AS inherits
FROM pg_roles
WHERE rolname LIKE 'nlc_%' OR rolname = 'neondb_owner'
ORDER BY rolname;

-- ===========================================================================
-- INSPECTION COMPLETE
-- Before running 01_migration_identity.sql, verify:
--   (a) Section 10: you are connected as neondb_owner
--   (b) Section 1:  nlc_app_role exists (01_... will fail if not)
--   (c) Section 1b: nlc_migration_user (if it exists) has BYPASSRLS = true
--       — this confirms the audit finding and 01_... will revoke it
--   (d) Section 3b: neondb_owner owns most objects — 01_... Step 4 will
--       transfer ownership to nlc_migration_owner
--   (e) Section 7:  alembic_version RLS is ENABLE + FORCE
-- ===========================================================================
