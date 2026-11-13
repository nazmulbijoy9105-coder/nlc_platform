-- NLC Platform — migration identity verification (hard gates)
-- Run after 01_migration_identity.sql using the DBA connection.
-- Every failed condition raises an exception; no fallback is permitted.

DO $check$
DECLARE
  n integer;
  can_login boolean;
  can_inherit boolean;
  bypass boolean;
  is_superuser boolean;
  member_count integer;
  missing_tables text;
  relation_gaps integer;
  function_gaps integer;
  type_gaps integer;
  version_rls boolean;
  version_force boolean;
BEGIN
  -- 1. Required roles exist.
  SELECT count(*) INTO n FROM pg_roles
   WHERE rolname IN ('nlc_app_role','nlc_migration_user','nlc_migration_owner');
  IF n<>3 THEN RAISE EXCEPTION 'FAIL [1]: expected three roles, found %',n; END IF;

  -- 2. Owner is NOLOGIN, non-superuser, and BYPASSRLS; it is never a login.
  SELECT rolcanlogin,rolsuper,rolbypassrls
    INTO can_login,is_superuser,bypass
    FROM pg_roles WHERE rolname='nlc_migration_owner';
  IF can_login OR is_superuser OR NOT bypass THEN
    RAISE EXCEPTION 'FAIL [2]: migration owner must be NOLOGIN, NOSUPERUSER, BYPASSRLS';
  END IF;

  -- 3. Migration login is LOGIN, NOINHERIT, NOBYPASSRLS, non-superuser.
  SELECT rolcanlogin,rolinherit,rolbypassrls,rolsuper
    INTO can_login,can_inherit,bypass,is_superuser
    FROM pg_roles WHERE rolname='nlc_migration_user';
  IF NOT can_login OR can_inherit OR bypass OR is_superuser THEN
    RAISE EXCEPTION 'FAIL [3]: migration login role attributes are unsafe';
  END IF;

  -- 4. Exactly one non-admin, non-inheriting SET membership.
  SELECT count(*) INTO member_count
    FROM pg_auth_members m
    JOIN pg_roles owner_role ON owner_role.oid=m.roleid
    JOIN pg_roles login_role ON login_role.oid=m.member
   WHERE owner_role.rolname='nlc_migration_owner'
     AND login_role.rolname='nlc_migration_user';
  IF member_count<>1 OR EXISTS (
    SELECT 1
      FROM pg_auth_members m
      JOIN pg_roles owner_role ON owner_role.oid=m.roleid
      JOIN pg_roles login_role ON login_role.oid=m.member
     WHERE owner_role.rolname='nlc_migration_owner'
       AND login_role.rolname='nlc_migration_user'
       AND (m.admin_option OR m.inherit_option OR NOT m.set_option)
  ) THEN
    RAISE EXCEPTION 'FAIL [4]: expected exactly one non-admin, non-inheriting SET-only membership; found %',member_count;
  END IF;

  -- 5. Runtime role is restricted; neither runtime nor migration LOGIN has DDL.
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles
     WHERE rolname='nlc_app_role' AND rolcanlogin
       AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
       AND NOT rolinherit AND NOT rolbypassrls AND NOT rolreplication
  ) OR has_schema_privilege('nlc_app_role','public','CREATE')
    OR has_database_privilege('nlc_migration_user',current_database(),'CREATE')
    OR has_schema_privilege('nlc_migration_user','public','CREATE')
    OR has_schema_privilege('nlc_migration_user','nlc_private','CREATE')
    OR has_schema_privilege('nlc_migration_user','audit','CREATE') THEN
    RAISE EXCEPTION 'FAIL [5]: runtime/migration login role attributes or direct DDL grants are unsafe';
  END IF;

  -- 6. Alembic metadata remains RLS-protected and owned by migration owner.
  SELECT relrowsecurity,relforcerowsecurity
    INTO version_rls,version_force
    FROM pg_class WHERE oid=to_regclass('public.alembic_version');
  IF version_rls IS DISTINCT FROM true OR version_force IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'FAIL [6]: alembic_version must have ENABLE + FORCE RLS';
  END IF;
  IF (SELECT relowner FROM pg_class WHERE oid=to_regclass('public.alembic_version'))
       <> (SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner') THEN
    RAISE EXCEPTION 'FAIL [6]: alembic_version is not owned by nlc_migration_owner';
  END IF;
  IF has_table_privilege('nlc_app_role','public.alembic_version','SELECT')
     OR has_table_privilege('nlc_app_role','public.alembic_version','INSERT')
     OR has_table_privilege('nlc_app_role','public.alembic_version','UPDATE')
     OR has_table_privilege('nlc_app_role','public.alembic_version','DELETE')
     OR has_table_privilege('nlc_app_role','public.alembic_version','TRUNCATE') THEN
    RAISE EXCEPTION 'FAIL [6]: runtime role must have no privileges on alembic_version';
  END IF;

  -- 7. Migration login can inspect all migration-managed tables.
  SELECT string_agg(format('%I.%I',n.nspname,c.relname),', ')
    INTO missing_tables
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND c.relkind IN ('r','p','v','m')
     AND NOT has_table_privilege('nlc_migration_user',c.oid,'SELECT');
  IF missing_tables IS NOT NULL THEN
    RAISE EXCEPTION 'FAIL [7]: migration login lacks SELECT on %',missing_tables;
  END IF;
  IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    WHERE n.nspname IN ('public','nlc_private','audit')
      AND CASE WHEN c.relkind='S'
        THEN NOT has_sequence_privilege('nlc_migration_user',format('%I.%I',n.nspname,c.relname),'SELECT')
        ELSE false END
  ) THEN
    RAISE EXCEPTION 'FAIL [7]: migration login lacks SELECT on one or more migration sequences';
  END IF;

  -- 8. Every migration-managed relation, function and custom type is owned
  -- by nlc_migration_owner; this includes alembic_version and its indexes.
  SELECT count(*) INTO relation_gaps
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND c.relkind IN ('r','p','v','m','S','f','i','I')
     AND c.relowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner');
  SELECT count(*) INTO function_gaps
    FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND p.proowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_proc'::regclass
       AND d.objid=p.oid AND d.refclassid='pg_extension'::regclass AND d.deptype='e');
  SELECT count(*) INTO type_gaps
    FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
   WHERE n.nspname IN ('public','nlc_private','audit')
     AND t.typtype IN ('e','d','c','r','m')
     AND t.typowner<>(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
     AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_type'::regclass
       AND d.objid=t.oid AND d.refclassid='pg_extension'::regclass AND d.deptype='e')
     AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype=t.oid);
  IF relation_gaps<>0 OR function_gaps<>0 OR type_gaps<>0 THEN
    RAISE EXCEPTION 'FAIL [8]: ownership gaps: relations %, functions %, types %',
      relation_gaps,function_gaps,type_gaps;
  END IF;

  -- 9. The migration login itself never bypasses RLS.
  IF (SELECT rolbypassrls FROM pg_roles WHERE rolname='nlc_migration_user') THEN
    RAISE EXCEPTION 'FAIL [9]: nlc_migration_user must be NOBYPASSRLS';
  END IF;

  -- 10. No migration-managed objects remain owned by neondb_owner.
  IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
     WHERE n.nspname IN ('public','nlc_private','audit')
       AND c.relkind IN ('r','p','v','m','S','f','i','I')
       AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname='neondb_owner')
  ) THEN
    RAISE EXCEPTION 'FAIL [10]: neondb_owner still owns migration-managed relations';
  END IF;

  -- 11. Future migrations must not grant destructive DELETE by default.
  IF EXISTS (
    SELECT 1 FROM pg_default_acl d
    CROSS JOIN LATERAL aclexplode(d.defaclacl) a
    WHERE d.defaclrole=(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
      AND d.defaclnamespace IN (0,(SELECT oid FROM pg_namespace WHERE nspname='public'))
      AND d.defaclobjtype='r'
      AND a.grantee IN (0,(SELECT oid FROM pg_roles WHERE rolname='nlc_app_role'))
      AND a.privilege_type='DELETE'
  ) THEN
    RAISE EXCEPTION 'FAIL [11]: default DELETE privilege exists for PUBLIC or nlc_app_role';
  END IF;
END
$check$;

SELECT
  'owner_no_login_bypassrls' AS check_name,
  (NOT rolcanlogin AND NOT rolsuper AND rolbypassrls) AS passed
FROM pg_roles WHERE rolname='nlc_migration_owner'
UNION ALL
SELECT 'migration_login_noinherit_nobypass',
  (rolcanlogin AND NOT rolinherit AND NOT rolbypassrls AND NOT rolsuper)
FROM pg_roles WHERE rolname='nlc_migration_user'
UNION ALL
SELECT 'app_role_no_create',
  (NOT has_schema_privilege('nlc_app_role','public','CREATE'))
UNION ALL
SELECT 'alembic_version_owner_and_rls',
  EXISTS(SELECT 1 FROM pg_class c WHERE c.oid=to_regclass('public.alembic_version')
    AND c.relowner=(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
    AND c.relrowsecurity AND c.relforcerowsecurity)
UNION ALL
SELECT 'no_default_delete_grants',
  NOT EXISTS(SELECT 1 FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a
    WHERE d.defaclrole=(SELECT oid FROM pg_roles WHERE rolname='nlc_migration_owner')
      AND d.defaclnamespace IN (0,(SELECT oid FROM pg_namespace WHERE nspname='public'))
      AND d.defaclobjtype='r'
      AND a.grantee IN (0,(SELECT oid FROM pg_roles WHERE rolname='nlc_app_role'))
      AND a.privilege_type='DELETE');
