-- ============================================================
-- Row Level Security (RLS) Policies for Cuentas Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for ProducerAccount
-- and AccountMovement tables.
-- ============================================================

-- ============================================================
-- ProducerAccount Table RLS
-- ============================================================

ALTER TABLE cuentas_produceraccount ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_produceraccount FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS produceraccount_tenant_isolation ON cuentas_produceraccount;
CREATE POLICY produceraccount_tenant_isolation ON cuentas_produceraccount
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY produceraccount_tenant_isolation ON cuentas_produceraccount IS
'Ensures producer accounts are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON cuentas_produceraccount TO gravitea_app;

-- ============================================================
-- AccountMovement Table RLS — IMMUTABLE
-- ============================================================

ALTER TABLE cuentas_accountmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_accountmovement FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS accountmovement_tenant_isolation ON cuentas_accountmovement;
CREATE POLICY accountmovement_tenant_isolation ON cuentas_accountmovement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY accountmovement_tenant_isolation ON cuentas_accountmovement IS
'Ensures account movements are only visible/insertable within their tenant context.';

GRANT SELECT, INSERT ON cuentas_accountmovement TO gravitea_app;
-- NOTE: No UPDATE or DELETE grant — immutable table
