-- 001_readonly_role.sql — create the read-only role mcp-postgres-sheets connects as.
--
-- This role is the MAIN safety guarantee: even if every other layer failed, it can only read
-- the schemas you grant here. Run it as a database owner or superuser with psql:
--
--   psql "$ADMIN_DATABASE_URL" \
--     -v ro_user=mcp_readonly -v ro_password='choose-a-long-random-password' \
--     -v schema=public -f deploy/sql/001_readonly_role.sql
--
-- Repeat the GRANT block for each schema you list in ALLOWED_SCHEMAS.
-- Idempotent: safe to run again (it re-applies grants and settings).

\set ON_ERROR_STOP on

SELECT format('CREATE ROLE %I LOGIN', :'ro_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'ro_user')
\gexec

-- No superuser, no DDL, no replication, no inherited privileges.
ALTER ROLE :"ro_user" WITH LOGIN PASSWORD :'ro_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS NOINHERIT
    CONNECTION LIMIT 20;

-- Defence in depth: every session starts read-only with a timeout, even outside the server.
ALTER ROLE :"ro_user" SET default_transaction_read_only = on;
ALTER ROLE :"ro_user" SET statement_timeout = '5s';
ALTER ROLE :"ro_user" SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE :"ro_user" SET search_path = :"schema";

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'ro_user')
\gexec

-- Read access to one schema. Nothing else: no INSERT/UPDATE/DELETE/TRUNCATE, no CREATE.
GRANT USAGE ON SCHEMA :"schema" TO :"ro_user";
GRANT SELECT ON ALL TABLES IN SCHEMA :"schema" TO :"ro_user";
-- Tables created later in this schema (by the role running this script) are readable too.
ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema" GRANT SELECT ON TABLES TO :"ro_user";

-- Nobody but owners may create objects in the schema (PostgreSQL < 15 allowed this for PUBLIC).
REVOKE CREATE ON SCHEMA :"schema" FROM PUBLIC;
