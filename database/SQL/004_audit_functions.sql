-- ============================================================
-- Audit Trail Functions for Gravitea ERP
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Database-level audit trail for compliance and security
-- Captures all changes to sensitive tables
-- Execute: psql -U postgres -d gravitea -f 004_audit_functions.sql
-- Requires: 000_init_database.sql + Django migrations + 002_rls_policies.sql
-- IDEMPOTENT: Safe to run multiple times without errors.
-- ============================================================

-- ============================================================
-- Create Audit Log Table (if not exists)
-- ============================================================
-- This table is NOT managed by Django (no model). It is a raw SQL
-- table used exclusively by the audit_trigger_function() below.

CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    table_name      VARCHAR(100) NOT NULL,
    record_id       UUID NOT NULL,
    operation       VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_values      JSONB,
    new_values      JSONB,
    changed_fields  TEXT[],
    user_id         UUID,
    user_email      VARCHAR(255),
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_log_tenant_table ON audit_log (tenant_id, table_name, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_record ON audit_log (tenant_id, record_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log (tenant_id, user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);

-- ============================================================
-- RLS for Audit Log
-- ============================================================

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS audit_log_tenant_isolation ON audit_log;
CREATE POLICY audit_log_tenant_isolation ON audit_log
    USING (tenant_id = get_current_tenant_id());

COMMENT ON TABLE audit_log IS
'Immutable audit trail for all changes to tenant-bound tables.
Captures who, what, when, and from where for compliance.';

-- ============================================================
-- Helper Function: Get Current User Context
-- ============================================================

CREATE OR REPLACE FUNCTION get_current_user_context()
RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        'user_id', NULLIF(current_setting('app.current_user_id', true), ''),
        'user_email', NULLIF(current_setting('app.current_user_email', true), ''),
        'ip_address', NULLIF(current_setting('app.client_ip', true), ''),
        'user_agent', NULLIF(current_setting('app.user_agent', true), '')
    );
EXCEPTION
    WHEN OTHERS THEN
        RETURN '{}'::jsonb;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================
-- Generic Audit Trigger Function
-- ============================================================

CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_tenant_id UUID;
    v_user_context JSONB;
    v_old_values JSONB;
    v_new_values JSONB;
    v_changed_fields TEXT[];
    v_record_id UUID;
    v_key TEXT;
BEGIN
    -- Get user context
    v_user_context := get_current_user_context();

    -- Determine tenant_id and record_id based on operation
    IF TG_OP = 'DELETE' THEN
        v_tenant_id := OLD.tenant_id;
        v_record_id := OLD.id;
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
        v_changed_fields := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_tenant_id := NEW.tenant_id;
        v_record_id := NEW.id;
        v_old_values := NULL;
        v_new_values := to_jsonb(NEW);
        v_changed_fields := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_tenant_id := NEW.tenant_id;
        v_record_id := NEW.id;
        v_old_values := to_jsonb(OLD);
        v_new_values := to_jsonb(NEW);

        -- Calculate changed fields
        v_changed_fields := ARRAY(
            SELECT key
            FROM jsonb_each(to_jsonb(OLD)) old_fields
            JOIN jsonb_each(to_jsonb(NEW)) new_fields USING (key)
            WHERE old_fields.value IS DISTINCT FROM new_fields.value
        );

        -- Skip if no actual changes
        IF array_length(v_changed_fields, 1) IS NULL THEN
            RETURN NEW;
        END IF;
    END IF;

    -- Insert audit record
    INSERT INTO audit_log (
        tenant_id,
        table_name,
        record_id,
        operation,
        old_values,
        new_values,
        changed_fields,
        user_id,
        user_email,
        ip_address,
        user_agent
    ) VALUES (
        v_tenant_id,
        TG_TABLE_NAME,
        v_record_id,
        TG_OP,
        v_old_values,
        v_new_values,
        v_changed_fields,
        (v_user_context->>'user_id')::UUID,
        v_user_context->>'user_email',
        (v_user_context->>'ip_address')::INET,
        v_user_context->>'user_agent'
    );

    -- Return appropriate record
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION audit_trigger_function() IS
'Generic audit trigger function that captures all changes to a table.
Automatically extracts tenant_id, record_id, and changed fields.';

-- ============================================================
-- Apply Audit Triggers to Sensitive Tables
-- ============================================================

-- Role table audit
DROP TRIGGER IF EXISTS trg_audit_role ON role;
CREATE TRIGGER trg_audit_role
    AFTER INSERT OR UPDATE OR DELETE ON role
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- AppUser table audit
DROP TRIGGER IF EXISTS trg_audit_app_user ON app_user;
CREATE TRIGGER trg_audit_app_user
    AFTER INSERT OR UPDATE OR DELETE ON app_user
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Product table audit
DROP TRIGGER IF EXISTS trg_audit_product ON product;
CREATE TRIGGER trg_audit_product
    AFTER INSERT OR UPDATE OR DELETE ON product
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Stock Movement table audit (INSERT only, no UPDATE/DELETE allowed)
DROP TRIGGER IF EXISTS trg_audit_stock_movement ON stock_movement;
CREATE TRIGGER trg_audit_stock_movement
    AFTER INSERT ON stock_movement
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- ============================================================
-- Additional Audit Triggers for Sensitive Tables
-- ============================================================

-- Customer table audit (contains PII)
DROP TRIGGER IF EXISTS trg_audit_customer ON customer;
CREATE TRIGGER trg_audit_customer
    AFTER INSERT OR UPDATE OR DELETE ON customer
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Supplier table audit (contains PII)
DROP TRIGGER IF EXISTS trg_audit_supplier ON supplier;
CREATE TRIGGER trg_audit_supplier
    AFTER INSERT OR UPDATE OR DELETE ON supplier
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Sale table audit (financial transactions)
DROP TRIGGER IF EXISTS trg_audit_sale ON sale;
CREATE TRIGGER trg_audit_sale
    AFTER INSERT OR UPDATE OR DELETE ON sale
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Payment table audit (sensitive financial data)
DROP TRIGGER IF EXISTS trg_audit_payment ON payment;
CREATE TRIGGER trg_audit_payment
    AFTER INSERT OR UPDATE OR DELETE ON payment
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Purchase Order table audit (financial transactions)
DROP TRIGGER IF EXISTS trg_audit_purchase_order ON purchase_order;
CREATE TRIGGER trg_audit_purchase_order
    AFTER INSERT OR UPDATE OR DELETE ON purchase_order
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Sync Session table audit (security-relevant)
DROP TRIGGER IF EXISTS trg_audit_sync_session ON sync_session;
CREATE TRIGGER trg_audit_sync_session
    AFTER INSERT OR UPDATE OR DELETE ON sync_session
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Pending Operation table audit (sync operations)
DROP TRIGGER IF EXISTS trg_audit_pending_operation ON pending_operation;
CREATE TRIGGER trg_audit_pending_operation
    AFTER INSERT OR UPDATE OR DELETE ON pending_operation
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Branch table audit (organizational changes)
DROP TRIGGER IF EXISTS trg_audit_branch ON branch;
CREATE TRIGGER trg_audit_branch
    AFTER INSERT OR UPDATE OR DELETE ON branch
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- Price List table audit (pricing changes)
DROP TRIGGER IF EXISTS trg_audit_price_list ON price_list;
CREATE TRIGGER trg_audit_price_list
    AFTER INSERT OR UPDATE OR DELETE ON price_list
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_function();

-- ============================================================
-- Audit Query Functions
-- ============================================================

CREATE OR REPLACE FUNCTION get_audit_history(
    p_tenant_id UUID,
    p_table_name VARCHAR(100) DEFAULT NULL,
    p_record_id UUID DEFAULT NULL,
    p_start_date TIMESTAMPTZ DEFAULT NULL,
    p_end_date TIMESTAMPTZ DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    id BIGINT,
    table_name VARCHAR(100),
    record_id UUID,
    operation VARCHAR(10),
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    user_email VARCHAR(255),
    ip_address INET,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        al.id,
        al.table_name,
        al.record_id,
        al.operation,
        al.old_values,
        al.new_values,
        al.changed_fields,
        al.user_email,
        al.ip_address,
        al.created_at
    FROM audit_log al
    WHERE al.tenant_id = p_tenant_id
      AND (p_table_name IS NULL OR al.table_name = p_table_name)
      AND (p_record_id IS NULL OR al.record_id = p_record_id)
      AND (p_start_date IS NULL OR al.created_at >= p_start_date)
      AND (p_end_date IS NULL OR al.created_at <= p_end_date)
    ORDER BY al.created_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

COMMENT ON FUNCTION get_audit_history(UUID, VARCHAR, UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTEGER) IS
'Retrieves audit history for a tenant with optional filters.
Use for compliance reporting and security investigations.';

-- ============================================================
-- Grant Permissions
-- ============================================================

GRANT SELECT ON audit_log TO gravitea_app;
GRANT INSERT ON audit_log TO gravitea_app;
GRANT USAGE, SELECT ON audit_log_id_seq TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_current_user_context() TO gravitea_app;
GRANT EXECUTE ON FUNCTION audit_trigger_function() TO gravitea_app;
GRANT EXECUTE ON FUNCTION get_audit_history(UUID, VARCHAR, UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTEGER) TO gravitea_app;
