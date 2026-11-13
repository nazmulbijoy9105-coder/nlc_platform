-- NLC Platform — migration identity provisioning and reviewed ownership transfer
-- Run once as neondb_owner on an isolated restored branch first.
-- Do not run against production until the full restored-branch rehearsal passes.
--
-- Contract:
--   nlc_app_role         LOGIN, NOINHERIT, NOBYPASSRLS; runtime grants unchanged.
--   nlc_migration_user   LOGIN, NOINHERIT, NOBYPASSRLS; no direct DDL.
--   nlc_migration_owner  NOLOGIN, NOINHERIT, BYPASSRLS; owns migration objects.
--   nlc_migration_user may SET ROLE to owner, but does not inherit its grants.
--
-- Passwords are intentionally NOT embedded in this file. Provision/reset the
-- nlc_migration_user password through Neon and store its direct URL only as a
-- GitHub Actions secret. Never place it in Render's APP_DATABASE_URL.
--
-- This script preserves existing explicit runtime ACLs and all RLS policies.
-- It does not grant blanket runtime DELETE, does not disable RLS, and does not
-- create replacement evidence tables.

DO $roles$
BEGIN
  IF current_user <> 'neondb_owner' THEN
    RAISE EXCEPTION 'Run as neondb_owner; observed %', current_user;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nlc_app_role') THEN
    RAISE EXCEPTION 'nlc_app_role is missing; refusing migration identity provisioning';
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nlc_migration_owner') THEN
    EXECUTE 'CREATE ROLE nlc_migration_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT BYPASSRLS NOREPLICATION';
  END IF;
  IF (SELECT rolsuper FROM pg_roles WHERE rolname='nlc_migration_owner') THEN
    RAISE EXCEPTION 'nlc_migration_owner is SUPERUSER; only a superuser DBA may correct this role';
  END IF;
  ALTER ROLE nlc_migration_owner NOLOGIN NOCREATEDB NOCREATEROLE NOINHERIT BYPASSRLS NOREPLICATION;

  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='nlc_migration_user') THEN
    EXECUTE 'CREATE ROLE nlc_migration_user LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION CONNECTION LIMIT 5';
  END IF;
  IF (SELECT rolsuper FROM pg_roles WHERE rolname='nlc_migration_user') THEN
    RAISE EXCEPTION 'nlc_migration_user is SUPERUSER; only a superuser DBA may correct this role';
  END IF;
  ALTER ROLE nlc_migration_user LOGIN NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION CONNECTION LIMIT 5;
END
$roles$;

-- Exactly one non-admin, non-inheriting SET membership for the migration login.
GRANT nlc_migration_owner TO nlc_migration_user
  WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;

-- Temporary SET membership lets the current object owner transfer objects.
-- This grant is revoked after the transfer; the provider-managed cloud_admin
-- membership, if present, is not modified.
GRANT nlc_migration_owner TO neondb_owner
  WITH INHERIT FALSE, SET TRUE;

DO $privileges$
DECLARE schema_name text;
BEGIN
  EXECUTE format('GRANT CREATE ON DATABASE %I TO nlc_migration_owner', current_database());

  FOREACH schema_name IN ARRAY ARRAY['public','nlc_private','audit'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname=schema_name) THEN
      IF schema_name = 'nlc_private' THEN
        -- At the supported 0042 starting revision this schema is expected to
        -- be absent; migration 0050 creates it. Pre-create it with the intended
        -- owner so the ownership transfer is valid before Alembic starts.
        EXECUTE 'CREATE SCHEMA nlc_private AUTHORIZATION nlc_migration_owner';
      ELSE
        RAISE EXCEPTION 'Required migration schema % is missing; refusing partial transfer', schema_name;
      END IF;
    END IF;
    EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO nlc_migration_owner', schema_name);
  END LOOP;
END
$privileges$;

-- Transfer tables first: table-owned serial/identity sequences follow their
-- table. Indexes, constraints, triggers and table row types follow ownership.
DO $transfer$
DECLARE obj record;
BEGIN
  FOR obj IN
    SELECT n.nspname AS schema_name, c.relname AS object_name
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND c.relkind IN ('r','p')
       AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     ORDER BY n.nspname,c.relname
  LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO nlc_migration_owner', obj.schema_name, obj.object_name);
  END LOOP;

  FOR obj IN
    SELECT n.nspname AS schema_name,c.relname AS object_name,c.relkind
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND c.relkind IN ('v','m','f')
       AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     ORDER BY n.nspname,c.relname
  LOOP
    IF obj.relkind='v' THEN
      EXECUTE format('ALTER VIEW %I.%I OWNER TO nlc_migration_owner',obj.schema_name,obj.object_name);
    ELSIF obj.relkind='m' THEN
      EXECUTE format('ALTER MATERIALIZED VIEW %I.%I OWNER TO nlc_migration_owner',obj.schema_name,obj.object_name);
    ELSE
      EXECUTE format('ALTER FOREIGN TABLE %I.%I OWNER TO nlc_migration_owner',obj.schema_name,obj.object_name);
    END IF;
  END LOOP;

  FOR obj IN
    SELECT n.nspname AS schema_name,p.proname AS object_name,p.oid,p.prokind
      FROM pg_proc p
      JOIN pg_namespace n ON n.oid=p.pronamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND p.proowner <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
       AND p.prokind IN ('f','p')
       AND NOT EXISTS (
         SELECT 1 FROM pg_depend d
          WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid
            AND d.refclassid='pg_extension'::regclass AND d.deptype='e'
       )
     ORDER BY n.nspname,p.proname,p.oid
  LOOP
    IF obj.prokind='p' THEN
      EXECUTE format('ALTER PROCEDURE %I.%I(%s) OWNER TO nlc_migration_owner',
        obj.schema_name,obj.object_name,pg_get_function_identity_arguments(obj.oid));
    ELSE
      EXECUTE format('ALTER FUNCTION %I.%I(%s) OWNER TO nlc_migration_owner',
        obj.schema_name,obj.object_name,pg_get_function_identity_arguments(obj.oid));
    END IF;
  END LOOP;

  -- User-defined enums, domains, ranges, multiranges and standalone composites.
  -- Table row types are excluded because ALTER TABLE transfers them.
  FOR obj IN
    SELECT n.nspname AS schema_name,t.typname AS object_name,t.oid
      FROM pg_type t
      JOIN pg_namespace n ON n.oid=t.typnamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND t.typowner <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
       AND t.typtype IN ('e','d','r','m','c')
       AND NOT EXISTS (
         SELECT 1 FROM pg_depend d
          WHERE d.classid='pg_type'::regclass AND d.objid=t.oid
            AND d.refclassid='pg_extension'::regclass AND d.deptype='e'
       )
       AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype=t.oid)
     ORDER BY n.nspname,t.typname
  LOOP
    EXECUTE format('ALTER TYPE %I.%I OWNER TO nlc_migration_owner',obj.schema_name,obj.object_name);
  END LOOP;

  -- Only standalone sequences remain; table-owned sequences moved with tables.
  FOR obj IN
    SELECT n.nspname AS schema_name,c.relname AS object_name
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND c.relkind='S'
       AND c.relowner <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
       AND NOT EXISTS (
         SELECT 1 FROM pg_depend d
          WHERE d.classid='pg_class'::regclass AND d.objid=c.oid
            AND d.refclassid='pg_class'::regclass AND d.deptype IN ('a','i')
       )
     ORDER BY n.nspname,c.relname
  LOOP
    EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO nlc_migration_owner',obj.schema_name,obj.object_name);
  END LOOP;
END
$transfer$;

-- The migration login can inspect the catalogue but cannot perform DDL until
-- env.py issues SET ROLE nlc_migration_owner inside Alembic's own connection.
SET ROLE nlc_migration_owner;
-- Neon-created read_write roles may start with broad direct DML grants.
-- Strip those grants: the login must use SET ROLE for migration DDL/DML.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public, nlc_private, audit FROM nlc_migration_user;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public, nlc_private, audit FROM nlc_migration_user;
REVOKE CREATE ON SCHEMA public, nlc_private, audit FROM nlc_migration_user;
GRANT USAGE ON SCHEMA public, nlc_private, audit TO nlc_migration_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public, nlc_private, audit TO nlc_migration_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public, nlc_private, audit TO nlc_migration_user;

-- Future public objects receive only non-destructive runtime DML by default.
-- DELETE remains an explicit per-table grant and is not granted to PUBLIC.
ALTER DEFAULT PRIVILEGES FOR ROLE nlc_migration_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE ON TABLES TO nlc_app_role;
ALTER DEFAULT PRIVILEGES FOR ROLE nlc_migration_owner IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO nlc_app_role;
-- The restored 0042 branch predates migration 0050's public-schema lockdown.
-- Apply the runtime no-CREATE boundary now; this is required for safe replay.
REVOKE CREATE ON SCHEMA public FROM PUBLIC, nlc_app_role;
RESET ROLE;

-- Remove only the temporary membership granted by this script.
REVOKE nlc_migration_owner FROM neondb_owner;

-- Fail closed on final ownership, role attributes, membership and RLS metadata.
DO $final$
DECLARE
  owner_tables integer;
  stray_relations integer;
  stray_functions integer;
  stray_types integer;
  app_create boolean;
  version_rls boolean;
  version_force boolean;
BEGIN
  IF (SELECT rolcanlogin OR rolsuper OR NOT rolbypassrls OR rolinherit
        FROM pg_roles WHERE rolname='nlc_migration_owner') THEN
    RAISE EXCEPTION 'nlc_migration_owner role attributes do not match contract';
  END IF;
  IF (SELECT NOT rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole
             OR rolbypassrls OR rolinherit
        FROM pg_roles WHERE rolname='nlc_migration_user') THEN
    RAISE EXCEPTION 'nlc_migration_user role attributes do not match contract';
  END IF;

  SELECT count(*) INTO owner_tables
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='public' AND c.relkind IN ('r','p')
     AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner');
  SELECT count(*) INTO stray_relations
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND c.relkind IN ('r','p','v','m','S','f','i','I')
     AND c.relowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner');
  SELECT count(*) INTO stray_functions
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND p.proowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass
       AND d.objid=p.oid AND d.refclassid='pg_extension'::regclass AND d.deptype='e');
  SELECT count(*) INTO stray_types
    FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND t.typtype IN ('e','d','c','r','m')
     AND t.typowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_type'::regclass
       AND d.objid=t.oid AND d.refclassid='pg_extension'::regclass AND d.deptype='e')
     AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype=t.oid);

  SELECT has_schema_privilege('nlc_app_role','public','CREATE') INTO app_create;
  SELECT relrowsecurity,relforcerowsecurity INTO version_rls,version_force
    FROM pg_class WHERE oid=to_regclass('public.alembic_version');

  IF owner_tables=0 OR stray_relations<>0 OR stray_functions<>0 OR stray_types<>0 THEN
    RAISE EXCEPTION 'Ownership transfer incomplete: public tables %, relation gaps %, function gaps %, type gaps %',
      owner_tables,stray_relations,stray_functions,stray_types;
  END IF;
  IF app_create THEN
    RAISE EXCEPTION 'nlc_app_role has CREATE on public';
  END IF;
  IF version_rls IS DISTINCT FROM true OR version_force IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'alembic_version must retain ENABLE + FORCE RLS';
  END IF;
END
$final$;

SELECT
  (SELECT rolcanlogin FROM pg_roles WHERE rolname='nlc_migration_owner') AS owner_can_login,
  (SELECT rolbypassrls FROM pg_roles WHERE rolname='nlc_migration_owner') AS owner_bypassrls,
  (SELECT rolcanlogin FROM pg_roles WHERE rolname='nlc_migration_user') AS migration_user_can_login,
  (SELECT rolbypassrls FROM pg_roles WHERE rolname='nlc_migration_user') AS migration_user_bypassrls,
  (SELECT count(*) FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid
     JOIN pg_roles u ON u.oid=m.member
    WHERE g.rolname='nlc_migration_owner' AND u.rolname='nlc_migration_user'
      AND NOT m.admin_option AND NOT m.inherit_option AND m.set_option) AS set_only_membership,
  (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname='public' AND c.relkind IN ('r','p')
      AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')) AS public_tables_owned,
  (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname IN ('public','nlc_private','audit')
      AND c.relkind IN ('r','p','v','m','S','f','i','I')
      AND c.relowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')) AS relation_ownership_gaps,
  has_schema_privilege('nlc_app_role','public','CREATE') AS app_can_create_public;
