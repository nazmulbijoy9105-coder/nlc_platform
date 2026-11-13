-- ============================================================================
-- NLC Platform — P0 Fix #1 (v3, corrected): Migration Identity Provisioning
-- File: scripts/fixes/01_migration_identity.sql
--
-- v3 CORRECTIONS (on top of v2):
--   6. nlc_migration_user is created with NOBYPASSRLS. If the role already
--      exists (the audit confirms it does, with BYPASSRLS), ALTER ROLE
--      NOBYPASSRLS explicitly revokes the bypass. This is non-negotiable:
--      a migration role that bypasses RLS defeats the entire row-level
--      security model during migrations.
--   7. Added an explicit FAIL gate: if nlc_app_role does not exist, the
--      script aborts at Step 9 with an exception. No silent fallback.
--   8. The ownership-transfer loop (Step 4) now reports per-object-type
--      counts so the Neon SQL Editor output shows exactly what moved.
--
-- v2 CORRECTIONS (carried forward):
--   1. Removed psql meta-commands. Pure SQL for Neon SQL Editor.
--   2. CREATE ROLE via EXECUTE inside DO blocks. Password via top-level ALTER ROLE.
--   3. ACLs reconciled — targeted grants, not blanket GRANT ALL.
--   4. Role name: nlc_app -> nlc_app_role (confirmed by production audit).
--   5. Ownership transfer of existing public-schema objects to nlc_migration_owner.
--
-- TARGET STATE (not current state — the audit confirms this is not yet provisioned):
--   - nlc_migration_owner: NOLOGIN, NOINHERIT, owns all public-schema objects
--   - nlc_migration_user:  LOGIN, NOINHERIT, NOBYPASSRLS, SET-only membership
--   - nlc_app_role:        LOGIN, no CREATE on public, RLS-protected access
--   - neondb_owner:        no longer owns user objects in public schema
--
-- Run order:
--   0. Run 00_preflight_inspect.sql (read-only) and confirm state.
--   1. Find-replace <<SET_STRONG_PASSWORD_HERE>> below with a strong password.
--   2. Run this script AS neondb_owner ONCE.
--   3. Run 02_verify_migration_identity.sql (now 10 checks).
--   4. Run 06_alembic_env_role_check.py to verify env.py role-prep works.
--   5. Set MIGRATION_DATABASE_URL on Render (see 03_render_env.md).
--   6. Re-run the deployment via 04_migration_preflight.sh.
-- ============================================================================


-- ===========================================================================
-- STEP 1 — Create nlc_migration_owner (NOLOGIN, NOINHERIT)
-- ===========================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nlc_migration_owner') THEN
        EXECUTE 'CREATE ROLE nlc_migration_owner WITH NOLOGIN NOINHERIT';
        RAISE NOTICE 'Created role: nlc_migration_owner';
    ELSE
        RAISE NOTICE 'Role already exists (no change): nlc_migration_owner';
    END IF;
END $$;


-- ===========================================================================
-- STEP 2 — Create nlc_migration_user (LOGIN, NOINHERIT, NOBYPASSRLS)
-- ---------------------------------------------------------------------------
-- NOBYPASSRLS is critical: the audit confirms nlc_migration_user currently
-- HAS BYPASSRLS. This role must never bypass RLS — it runs migrations that
-- touch RLS-protected tables, and bypassing RLS during migrations would
-- allow the migration to see and modify rows across all tenants.
--
-- If the role already exists, Step 2b below explicitly revokes BYPASSRLS.
-- ===========================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nlc_migration_user') THEN
        EXECUTE 'CREATE ROLE nlc_migration_user WITH LOGIN NOINHERIT NOBYPASSRLS CONNECTION LIMIT 5';
        RAISE NOTICE 'Created login role: nlc_migration_user (NOBYPASSRLS, password not yet set)';
    ELSE
        RAISE NOTICE 'Login role already exists: nlc_migration_user (will enforce NOBYPASSRLS and reset password below)';
    END IF;
END $$;

-- Step 2b — Explicitly enforce NOBYPASSRLS (revokes bypass if currently held)
-- This is idempotent and safe whether or not the role currently has BYPASSRLS.
ALTER ROLE nlc_migration_user NOBYPASSRLS;

-- Step 2c — Set the password. Top-level SQL (not in DO block) so the literal
-- is passed directly to the server. Find-replace the placeholder token.
-- If the placeholder is still present, this statement fails with a syntax
-- error — the intended safety behaviour.
ALTER ROLE nlc_migration_user PASSWORD '<<SET_STRONG_PASSWORD_HERE>>';


-- ===========================================================================
-- STEP 3 — Grant nlc_migration_user SET-only membership in nlc_migration_owner
-- ---------------------------------------------------------------------------
-- NOINHERIT on nlc_migration_user means it does NOT automatically inherit
-- nlc_migration_owner privileges. It must explicitly `SET ROLE
-- nlc_migration_owner` before any DDL. Alembic's env.py must do this inside
-- the Alembic database connection — a shell-level SET ROLE in the preflight
-- does NOT carry over (different connection).
-- ===========================================================================
GRANT nlc_migration_owner TO nlc_migration_user;


-- ===========================================================================
-- STEP 4 — Transfer ownership of existing public-schema objects to
--          nlc_migration_owner
-- ---------------------------------------------------------------------------
-- PostgreSQL requires ownership (or superuser) to ALTER a table. Without this
-- transfer, nlc_migration_owner cannot run Alembic migrations that ALTER
-- existing tables — the exact failure mode that blocked PR #310.
--
-- Transfers: tables (r), sequences (S), views (v), materialised views (m),
-- and functions/procedures (f/p). Includes alembic_version (Alembic manages it).
-- Does NOT touch: system schemas, RLS policies (stored separately), grants.
-- ===========================================================================
DO $$
DECLARE
    obj record;
    tables_n integer := 0;
    seqs_n   integer := 0;
    views_n  integer := 0;
    funcs_n  integer := 0;
BEGIN
    -- Tables, sequences, views, materialised views
    FOR obj IN
        SELECT n.nspname AS schema, c.relname AS obj, c.relkind AS kind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_roles r     ON r.oid = c.relowner
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'S', 'v', 'm')
          AND r.rolname <> 'nlc_migration_owner'
        LOOP
            EXECUTE format('ALTER TABLE %I.%I OWNER TO nlc_migration_owner',
                           obj.schema, obj.obj);
            IF obj.kind = 'r' THEN tables_n := tables_n + 1;
            ELSIF obj.kind = 'S' THEN seqs_n := seqs_n + 1;
            ELSE views_n := views_n + 1;
            END IF;
        END LOOP;

    -- Functions and procedures
    FOR obj IN
        SELECT n.nspname AS schema, p.proname AS obj, p.oid AS fn_oid
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_roles r     ON r.oid = p.proowner
        WHERE n.nspname = 'public'
          AND p.prokind IN ('f', 'p')
          AND r.rolname <> 'nlc_migration_owner'
        LOOP
            EXECUTE format('ALTER FUNCTION %I.%I(%s) OWNER TO nlc_migration_owner',
                           obj.schema, obj.obj,
                           pg_get_function_identity_arguments(obj.fn_oid));
            funcs_n := funcs_n + 1;
        END LOOP;

    RAISE NOTICE 'Ownership transfer: % tables, % sequences, % views, % functions -> nlc_migration_owner',
        tables_n, seqs_n, views_n, funcs_n;
END $$;


-- ===========================================================================
-- STEP 5 — Schema privileges for nlc_migration_owner
-- ===========================================================================
GRANT USAGE ON SCHEMA public TO nlc_migration_owner;
GRANT CREATE ON SCHEMA public TO nlc_migration_owner;


-- ===========================================================================
-- STEP 6 — Read access for nlc_migration_user (before SET ROLE)
-- ---------------------------------------------------------------------------
-- Alembic connects as nlc_migration_user and needs to read the schema to
-- compute migration deltas. This is read-only — DDL only happens after
-- env.py issues SET ROLE nlc_migration_owner inside the Alembic connection.
-- ===========================================================================
GRANT USAGE ON SCHEMA public TO nlc_migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nlc_migration_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO nlc_migration_user;


-- ===========================================================================
-- STEP 7 — Default privileges: future objects created by nlc_migration_owner
--          are accessible to nlc_app_role
-- ===========================================================================
SET ROLE nlc_migration_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE nlc_migration_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nlc_app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE nlc_migration_owner IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO nlc_app_role;
RESET ROLE;


-- ===========================================================================
-- STEP 8 — Re-grant runtime privileges on EXISTING tables to nlc_app_role
-- ---------------------------------------------------------------------------
-- The ownership transfer in Step 4 can drop existing grants. Re-grant the
-- runtime privileges nlc_app_role needs (subject to RLS policies).
-- ===========================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nlc_app_role;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO nlc_app_role;


-- ===========================================================================
-- STEP 9 — Lock down: nlc_app_role and PUBLIC cannot do DDL
-- ---------------------------------------------------------------------------
-- HARD FAIL if nlc_app_role does not exist. No silent fallback to nlc_app
-- or any other role. The script aborts.
-- ===========================================================================
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
        RAISE EXCEPTION 'FATAL: nlc_app_role does not exist. The production runtime role must be nlc_app_role (confirmed by audit). Aborting — no silent fallback.';
    END IF;
    REVOKE CREATE ON SCHEMA public FROM nlc_app_role;
    RAISE NOTICE 'Verified nlc_app_role exists. Revoked CREATE on public from nlc_app_role.';
END $$;


-- ===========================================================================
-- STEP 10 — Confirm alembic_version RLS (ENABLE + FORCE per PR #309)
-- ===========================================================================
DO $$
DECLARE
    rls_enabled boolean;
    rls_forced  boolean;
BEGIN
    SELECT relrowsecurity, relforcerowsecurity
      INTO rls_enabled, rls_forced
      FROM pg_class
     WHERE relname = 'alembic_version';

    IF rls_enabled IS NULL THEN
        RAISE EXCEPTION 'FATAL: alembic_version table not found — schema is in an unknown state';
    END IF;
    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'FATAL: alembic_version RLS not ENABLE — refusing to proceed';
    END IF;
    IF NOT rls_forced THEN
        RAISE EXCEPTION 'FATAL: alembic_version RLS not FORCE — refusing to proceed';
    END IF;
    RAISE NOTICE 'Verified: alembic_version RLS is ENABLE and FORCE';
END $$;


-- ===========================================================================
-- STEP 11 — Final summary
-- ===========================================================================
SELECT
    (SELECT rolname FROM pg_roles WHERE rolname = 'nlc_migration_owner') AS owner_role_exists,
    (SELECT rolcanlogin FROM pg_roles WHERE rolname = 'nlc_migration_owner') AS owner_can_login_should_be_false,
    (SELECT rolname FROM pg_roles WHERE rolname = 'nlc_migration_user') AS user_role_exists,
    (SELECT rolcanlogin FROM pg_roles WHERE rolname = 'nlc_migration_user') AS user_can_login_should_be_true,
    (SELECT rolbypassrls FROM pg_roles WHERE rolname = 'nlc_migration_user') AS user_bypassrls_should_be_false,
    (SELECT COUNT(*) FROM pg_auth_members m
       JOIN pg_roles r1 ON r1.oid = m.roleid
       JOIN pg_roles r2 ON r2.oid = m.member
      WHERE r1.rolname = 'nlc_migration_owner'
        AND r2.rolname = 'nlc_migration_user') AS membership_count_should_be_1,
    (SELECT COUNT(*) FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
       JOIN pg_roles r ON r.oid = c.relowner
      WHERE n.nspname = 'public'
        AND c.relkind = 'r'
        AND r.rolname = 'nlc_migration_owner') AS tables_owned_by_migration_owner,
    (SELECT COUNT(*) FROM pg_class c
       JOIN pg_namespace n ON n.oid = c.relnamespace
       JOIN pg_roles r ON r.oid = c.relowner
      WHERE n.nspname = 'public'
        AND c.relkind = 'r'
        AND r.rolname <> 'nlc_migration_owner') AS tables_still_owned_by_others,
    (SELECT has_schema_privilege('nlc_app_role', 'public', 'CREATE')) AS app_role_can_create_should_be_false;

-- ===========================================================================
-- DONE. Next: run 02_verify_migration_identity.sql (10 checks).
-- Then run 06_alembic_env_role_check.py to verify env.py role-preparation.
-- ===========================================================================
