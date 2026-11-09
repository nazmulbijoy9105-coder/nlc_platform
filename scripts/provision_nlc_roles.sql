-- Out-of-band role attribute reconciliation for NLC.
-- Run with an authorised Neon database administrator before Alembic migrations:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/provision_nlc_roles.sql
-- This script intentionally does not create roles, set passwords, or grant
-- memberships. Credentials and role creation remain controlled separately.

DO $provision_preflight$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
        RAISE EXCEPTION 'nlc_app_role is missing; create it through the authorised Neon role-management path first';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_ci_audit_role') THEN
        RAISE EXCEPTION 'nlc_ci_audit_role is missing; create it through the authorised Neon role-management path first';
    END IF;
END
$provision_preflight$;

ALTER ROLE nlc_app_role
    WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
         NOINHERIT NOREPLICATION NOBYPASSRLS;

ALTER ROLE nlc_ci_audit_role
    WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
         NOINHERIT NOREPLICATION NOBYPASSRLS;
