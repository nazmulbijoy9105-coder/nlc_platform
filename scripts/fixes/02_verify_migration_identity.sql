-- ============================================================================
-- NLC Platform — P0 Fix #2 (v3): Verify Migration Identity — 10 hard gates
-- File: scripts/fixes/02_verify_migration_identity.sql
--
-- v3 ADDITIONS (on top of v2's 8 checks):
--   Check 9 — nlc_migration_user must NOT have BYPASSRLS (rolbypassrls = false)
--   Check 10 — neondb_owner must NOT own any migration-managed table
--              (confirms the ownership transfer in 01_ Step 4 actually happened)
--
-- Every check RAISES EXCEPTION on failure. The script aborts at the first
-- failure. This is the gate the preflight (04_...) calls before running
-- Alembic — if any check fails, the deployment STOPS. No fallback.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Check 1 — Both roles exist
-- ---------------------------------------------------------------------------
DO $$
DECLARE n integer;
BEGIN
    SELECT COUNT(*) INTO n
    FROM pg_roles
    WHERE rolname IN ('nlc_migration_owner', 'nlc_migration_user');
    IF n <> 2 THEN
        RAISE EXCEPTION 'FAIL [1/10]: Expected 2 roles, found %. Run 01_migration_identity.sql first.', n;
    END IF;
    RAISE NOTICE 'PASS [1/10]: Both roles exist';
END $$;

-- ---------------------------------------------------------------------------
-- Check 2 — nlc_migration_owner is NOLOGIN
-- ---------------------------------------------------------------------------
DO $$
DECLARE can_login boolean;
BEGIN
    SELECT rolcanlogin INTO can_login FROM pg_roles WHERE rolname = 'nlc_migration_owner';
    IF can_login IS NULL THEN
        RAISE EXCEPTION 'FAIL [2/10]: nlc_migration_owner role not found';
    END IF;
    IF can_login THEN
        RAISE EXCEPTION 'FAIL [2/10]: nlc_migration_owner has LOGIN — must be NOLOGIN';
    END IF;
    RAISE NOTICE 'PASS [2/10]: nlc_migration_owner is NOLOGIN';
END $$;

-- ---------------------------------------------------------------------------
-- Check 3 — nlc_migration_user is LOGIN + NOINHERIT
-- ---------------------------------------------------------------------------
DO $$
DECLARE can_login boolean; inherits boolean;
BEGIN
    SELECT rolcanlogin, rolinherit INTO can_login, inherits
    FROM pg_roles WHERE rolname = 'nlc_migration_user';
    IF can_login IS NULL THEN
        RAISE EXCEPTION 'FAIL [3/10]: nlc_migration_user role not found';
    END IF;
    IF NOT can_login THEN
        RAISE EXCEPTION 'FAIL [3/10]: nlc_migration_user is NOLOGIN — must have LOGIN';
    END IF;
    IF inherits THEN
        RAISE EXCEPTION 'FAIL [3/10]: nlc_migration_user has INHERIT — must be NOINHERIT (SET-only)';
    END IF;
    RAISE NOTICE 'PASS [3/10]: nlc_migration_user is LOGIN + NOINHERIT';
END $$;

-- ---------------------------------------------------------------------------
-- Check 4 — Membership: nlc_migration_user is a member of nlc_migration_owner
-- ---------------------------------------------------------------------------
DO $$
DECLARE n integer;
BEGIN
    SELECT COUNT(*) INTO n
    FROM pg_auth_members m
    JOIN pg_roles r1 ON r1.oid = m.roleid
    JOIN pg_roles r2 ON r2.oid = m.member
    WHERE r1.rolname = 'nlc_migration_owner'
      AND r2.rolname = 'nlc_migration_user';
    IF n <> 1 THEN
        RAISE EXCEPTION 'FAIL [4/10]: membership grant missing (found %, expected 1)', n;
    END IF;
    RAISE NOTICE 'PASS [4/10]: nlc_migration_user is a member of nlc_migration_owner (SET-only via NOINHERIT)';
END $$;

-- ---------------------------------------------------------------------------
-- Check 5 — nlc_app_role has NO CREATE on public schema
-- ---------------------------------------------------------------------------
DO $$
DECLARE can_create boolean;
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
        RAISE EXCEPTION 'FAIL [5/10]: nlc_app_role does not exist — the production runtime role is absent. Aborting.';
    END IF;
    SELECT has_schema_privilege('nlc_app_role', 'public', 'CREATE') INTO can_create;
    IF can_create THEN
        RAISE EXCEPTION 'FAIL [5/10]: nlc_app_role still has CREATE on public — runtime role can do DDL';
    END IF;
    RAISE NOTICE 'PASS [5/10]: nlc_app_role has no CREATE on public';
END $$;

-- ---------------------------------------------------------------------------
-- Check 6 — alembic_version RLS is ENABLE + FORCE
-- ---------------------------------------------------------------------------
DO $$
DECLARE e boolean; f boolean;
BEGIN
    SELECT relrowsecurity, relforcerowsecurity INTO e, f
    FROM pg_class WHERE relname = 'alembic_version';
    IF e IS NULL THEN
        RAISE EXCEPTION 'FAIL [6/10]: alembic_version table not found';
    END IF;
    IF NOT e THEN
        RAISE EXCEPTION 'FAIL [6/10]: alembic_version RLS not ENABLE';
    END IF;
    IF NOT f THEN
        RAISE EXCEPTION 'FAIL [6/10]: alembic_version RLS not FORCE';
    END IF;
    RAISE NOTICE 'PASS [6/10]: alembic_version RLS is ENABLE + FORCE';
END $$;

-- ---------------------------------------------------------------------------
-- Check 7 — nlc_migration_user can SELECT all public tables
-- ---------------------------------------------------------------------------
DO $$
DECLARE missing text;
BEGIN
    SELECT string_agg(t.relname, ', ')
      INTO missing
      FROM pg_class t
      JOIN pg_namespace n ON n.oid = t.relnamespace
     WHERE n.nspname = 'public'
       AND t.relkind = 'r'
       AND NOT has_table_privilege('nlc_migration_user', t.oid, 'SELECT');
    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'FAIL [7/10]: nlc_migration_user lacks SELECT on: %', missing;
    END IF;
    RAISE NOTICE 'PASS [7/10]: nlc_migration_user can SELECT all public tables';
END $$;

-- ---------------------------------------------------------------------------
-- Check 8 — Every public-schema table is owned by nlc_migration_owner
-- ---------------------------------------------------------------------------
DO $$
DECLARE strays text; stray_count integer;
BEGIN
    SELECT string_agg(c.relname, ', ' ORDER BY c.relname),
           COUNT(*)
      INTO strays, stray_count
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_roles r ON r.oid = c.relowner
     WHERE n.nspname = 'public'
       AND c.relkind = 'r'
       AND r.rolname <> 'nlc_migration_owner';

    IF stray_count > 0 THEN
        RAISE EXCEPTION 'FAIL [8/10]: % tables not owned by nlc_migration_owner: %', stray_count, strays;
    END IF;
    RAISE NOTICE 'PASS [8/10]: All public-schema tables owned by nlc_migration_owner';
END $$;

-- ---------------------------------------------------------------------------
-- Check 9 — nlc_migration_user must NOT have BYPASSRLS
-- ---------------------------------------------------------------------------
DO $$
DECLARE bypass boolean;
BEGIN
    SELECT rolbypassrls INTO bypass
    FROM pg_roles WHERE rolname = 'nlc_migration_user';
    IF bypass IS NULL THEN
        RAISE EXCEPTION 'FAIL [9/10]: nlc_migration_user role not found';
    END IF;
    IF bypass THEN
        RAISE EXCEPTION 'FAIL [9/10]: nlc_migration_user has BYPASSRLS — must be NOBYPASSRLS. A migration role that bypasses RLS defeats row-level security during migrations. Run 01_...sql Step 2b (ALTER ROLE NOBYPASSRLS).';
    END IF;
    RAISE NOTICE 'PASS [9/10]: nlc_migration_user does NOT have BYPASSRLS';
END $$;

-- ---------------------------------------------------------------------------
-- Check 10 — neondb_owner no longer owns any migration-managed table
--            (confirms the ownership transfer happened)
-- ---------------------------------------------------------------------------
DO $$
DECLARE neon_owned text; neon_count integer;
BEGIN
    SELECT string_agg(c.relname, ', ' ORDER BY c.relname),
           COUNT(*)
      INTO neon_owned, neon_count
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      JOIN pg_roles r ON r.oid = c.relowner
     WHERE n.nspname = 'public'
       AND c.relkind = 'r'
       AND r.rolname = 'neondb_owner';

    IF neon_count > 0 THEN
        RAISE EXCEPTION 'FAIL [10/10]: neondb_owner still owns % public-schema tables: %. The ownership transfer in 01_ Step 4 did not complete.', neon_count, neon_owned;
    END IF;
    RAISE NOTICE 'PASS [10/10]: neondb_owner owns no public-schema tables (ownership transferred to nlc_migration_owner)';
END $$;

-- ---------------------------------------------------------------------------
-- Final summary
-- ---------------------------------------------------------------------------
SELECT
    '1. nlc_migration_owner exists' AS check,
    EXISTS(SELECT FROM pg_roles WHERE rolname = 'nlc_migration_owner') AS pass
UNION ALL SELECT
    '2. nlc_migration_owner is NOLOGIN',
    NOT (SELECT rolcanlogin FROM pg_roles WHERE rolname = 'nlc_migration_owner')
UNION ALL SELECT
    '3. nlc_migration_user is LOGIN + NOINHERIT',
    (SELECT rolcanlogin AND NOT rolinherit FROM pg_roles WHERE rolname = 'nlc_migration_user')
UNION ALL SELECT
    '4. membership granted (SET-only)',
    EXISTS(SELECT FROM pg_auth_members m
           JOIN pg_roles r1 ON r1.oid = m.roleid
           JOIN pg_roles r2 ON r2.oid = m.member
           WHERE r1.rolname = 'nlc_migration_owner' AND r2.rolname = 'nlc_migration_user')
UNION ALL SELECT
    '5. nlc_app_role exists + no CREATE on public',
    EXISTS(SELECT FROM pg_roles WHERE rolname = 'nlc_app_role')
    AND NOT has_schema_privilege('nlc_app_role', 'public', 'CREATE')
UNION ALL SELECT
    '6. alembic_version RLS ENABLE + FORCE',
    (SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE relname = 'alembic_version')
UNION ALL SELECT
    '7. nlc_migration_user can SELECT all public tables',
    NOT EXISTS(SELECT FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = 'public' AND c.relkind = 'r'
                 AND NOT has_table_privilege('nlc_migration_user', c.oid, 'SELECT'))
UNION ALL SELECT
    '8. all public tables owned by nlc_migration_owner',
    NOT EXISTS(SELECT FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               JOIN pg_roles r ON r.oid = c.relowner
               WHERE n.nspname = 'public' AND c.relkind = 'r'
                 AND r.rolname <> 'nlc_migration_owner')
UNION ALL SELECT
    '9. nlc_migration_user does NOT have BYPASSRLS',
    NOT (SELECT rolbypassrls FROM pg_roles WHERE rolname = 'nlc_migration_user')
UNION ALL SELECT
    '10. neondb_owner owns no public-schema tables',
    NOT EXISTS(SELECT FROM pg_class c
               JOIN pg_namespace n ON n.oid = c.relnamespace
               JOIN pg_roles r ON r.oid = c.relowner
               WHERE n.nspname = 'public' AND c.relkind = 'r'
                 AND r.rolname = 'neondb_owner');

DO $$ BEGIN RAISE NOTICE '=== All 10 checks passed. Migration identity is correctly provisioned. ==='; END $$;
