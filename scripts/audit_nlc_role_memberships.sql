-- Recurring audit of role memberships involving NLC runtime identities.
-- GitHub Actions uses NEON_API_KEY to request a direct, branch-pinned
-- nlc_ci_audit_role connection URI from the Neon API.
-- The caller must enforce default_transaction_read_only=on; this script
-- independently refuses to run unless the active transaction is read-only.

DO $membership_audit$
DECLARE
    app_role pg_roles%ROWTYPE;
    audit_role pg_roles%ROWTYPE;
BEGIN
    IF current_setting('transaction_read_only') <> 'on' THEN
        RAISE EXCEPTION
            'NLC role membership audit refused: transaction_read_only must be on';
    END IF;

    IF current_setting('server_version_num')::int < 160000 THEN
        RAISE EXCEPTION
            'NLC role membership audit requires PostgreSQL 16+ (pg_auth_members.inherit_option/set_option)';
    END IF;

    SELECT * INTO app_role FROM pg_roles WHERE rolname = 'nlc_app_role';
    SELECT * INTO audit_role FROM pg_roles WHERE rolname = 'nlc_ci_audit_role';

    IF app_role.rolname IS NULL OR audit_role.rolname IS NULL THEN
        RAISE EXCEPTION 'Required NLC runtime/audit role is missing';
    END IF;

    IF app_role.rolsuper OR app_role.rolbypassrls
       OR app_role.rolcreaterole OR app_role.rolcreatedb
       OR app_role.rolreplication THEN
        RAISE EXCEPTION
            'NLC application role has a prohibited elevated role attribute';
    END IF;

    IF audit_role.rolsuper OR audit_role.rolbypassrls
       OR audit_role.rolcreaterole OR audit_role.rolcreatedb
       OR audit_role.rolreplication OR audit_role.rolinherit
       OR NOT audit_role.rolcanlogin THEN
        RAISE EXCEPTION
            'NLC audit role is not configured as a non-inheriting, least-privilege login';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM pg_auth_members membership
          JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
          JOIN pg_roles member_role ON member_role.oid = membership.member
          JOIN pg_roles grantor_role ON grantor_role.oid = membership.grantor
         WHERE (
                member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
             OR granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
         )
           AND NOT (
                member_role.rolname = 'neondb_owner'
            AND granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
            AND grantor_role.rolname = 'cloud_admin'
            AND membership.admin_option IS TRUE
            AND membership.inherit_option IS FALSE
            AND membership.set_option IS FALSE
           )
    ) THEN
        RAISE EXCEPTION
            'NLC role membership audit failed: an unapproved membership exists';
    END IF;
END
$membership_audit$;
