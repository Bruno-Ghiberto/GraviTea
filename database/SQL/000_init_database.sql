-- ============================================================
-- Gravitea ERP - Database Initialization
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Create database, roles, and extensions
-- Execute FIRST as superuser: psql -U postgres -f 000_init_database.sql
-- IDEMPOTENT: Safe to run multiple times without errors.
-- ============================================================

-- ============================================================
-- 1) Create Database (if not exists)
-- ============================================================
-- Note: In Docker, the database is created automatically via POSTGRES_DB env var.
-- The following is commented out for docker-entrypoint-initdb.d compatibility.
--
-- CREATE DATABASE gravitea
--     WITH
--     OWNER = postgres
--     ENCODING = 'UTF8'
--     LC_COLLATE = 'en_US.UTF-8'
--     LC_CTYPE = 'en_US.UTF-8'
--     TEMPLATE = template0
--     CONNECTION LIMIT = -1;

-- ============================================================
-- 2) Connect to gravitea database
-- ============================================================
-- \c gravitea

-- ============================================================
-- 3) Extensions
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid(), encryption functions

-- ============================================================
-- 4) Application Roles
-- ============================================================

-- Admin role: Bypasses RLS for migrations and admin tasks
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gravitea_admin') THEN
        CREATE ROLE gravitea_admin NOLOGIN BYPASSRLS;
        COMMENT ON ROLE gravitea_admin IS
        'Admin role that bypasses RLS. Use for migrations and admin tasks only.';
    END IF;
END
$$;

-- Application role: Subject to RLS policies
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gravitea_app') THEN
        CREATE ROLE gravitea_app NOLOGIN;
        COMMENT ON ROLE gravitea_app IS
        'Application role for normal operations. Subject to RLS policies.';
    END IF;
END
$$;

-- ============================================================
-- 5) Application User (for Django connection)
-- ============================================================
-- Create a login user that inherits from gravitea_app

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'gravitea_user') THEN
        CREATE ROLE gravitea_user WITH LOGIN PASSWORD 'CHANGE_ME_IN_PRODUCTION';
        COMMENT ON ROLE gravitea_user IS
        'Login user for Django application. Inherits gravitea_app role.';
    END IF;
END
$$;

-- Grant role membership outside IF block so it re-applies even if role already exists
-- (e.g. if grant was revoked manually). GRANT is naturally idempotent in PostgreSQL.
GRANT gravitea_app TO gravitea_user;

-- ============================================================
-- 6) Schema Permissions
-- ============================================================
GRANT USAGE ON SCHEMA public TO gravitea_app;
GRANT USAGE ON SCHEMA public TO gravitea_admin;

-- ============================================================
-- 7) Default Privileges for Future Objects
-- ============================================================
-- Ensure gravitea_app can access tables created by migrations
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO gravitea_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO gravitea_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO gravitea_app;

-- ============================================================
-- 8) Session Variable Helper
-- ============================================================
-- These session variables are used by RLS policies and audit triggers

-- Database comment (uses dynamic SQL to work with any database name)
DO $$
BEGIN
    EXECUTE format('COMMENT ON DATABASE %I IS %L',
        current_database(),
        'Gravitea ERP Database - Multi-tenant ERP for hardware stores.

Session Variables (set by application):
  - app.current_tenant_id: UUID of current tenant for RLS
  - app.current_user_id: UUID of authenticated user
  - app.current_user_email: Email of authenticated user
  - app.client_ip: Client IP address for audit
  - app.user_agent: Client user agent for audit

Example usage:
  SET app.current_tenant_id = ''uuid-here'';
  SELECT * FROM product; -- Only returns tenant products');
END
$$;

-- ============================================================
-- Execution Order for Full Setup
-- ============================================================
/*
Run scripts in this order:

1. 000_init_database.sql          - This file (roles, extensions, permissions)
2. Django migrations              - Tables and ENUM types (python manage.py migrate)
3. 002_rls_policies.sql           - Row Level Security policies
4. 003_stock_functions.sql        - Stock management triggers/functions
5. 004_audit_functions.sql        - Audit trail triggers/functions
6. 005_hardening_constraints.sql  - CHECK constraints and FK indexes

NOTE: 001_schema_reference.sql is a REFERENCE ONLY copy of the schema.
Django migrations are the single source of truth for table definitions (R5).
SQL scripts own: RLS policies, triggers, functions, roles, and extensions.

Example (bootstrap.sh automates this):
  psql -U postgres -f 000_init_database.sql
  python manage.py migrate
  psql -U postgres -d gravitea -f 002_rls_policies.sql
  psql -U postgres -d gravitea -f 003_stock_functions.sql
  psql -U postgres -d gravitea -f 004_audit_functions.sql
  psql -U postgres -d gravitea -f 005_hardening_constraints.sql
*/

-- ============================================================
-- Verification
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'Database initialization complete.';
    RAISE NOTICE 'Roles created: gravitea_admin, gravitea_app, gravitea_user';
    RAISE NOTICE 'Extensions: pgcrypto';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run Django migrations (python manage.py migrate)';
END
$$;
