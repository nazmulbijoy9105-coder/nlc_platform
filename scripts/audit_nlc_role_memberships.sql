-- Recurring audit of role memberships involving NLC runtime identities.
-- Configure NEON_ROLE_AUDIT_DATABASE_URL as a protected GitHub Actions secret.
-- This is read-only and must connect to the intended Neon branch/database.

DO $membership_audit$
BEGIN
    IF current_setting('server_version_num')::int < 160000 THEN
        RAISE EXCEPTION
            'NLC role membership audit requires PostgreSQL 16+ (pg_auth_members.inherit_option/set_option)';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role')
       OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_ci_audit_role') THEN
        RAISE EXCEPTION 'Required NLC runtime role is missing';
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
