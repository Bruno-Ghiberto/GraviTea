-- ============================================================
-- Row Level Security (RLS) Policies for Ventas Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for sales tables.
-- All three ventas tables have tenant_id and get direct RLS policies.
-- ============================================================

-- ============================================================
-- Customer Table RLS
-- ============================================================

ALTER TABLE ventas_customer ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas_customer FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS customer_tenant_isolation ON ventas_customer;
CREATE POLICY customer_tenant_isolation ON ventas_customer
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY customer_tenant_isolation ON ventas_customer IS
'Ensures customers are only visible/modifiable within their tenant context.';

-- ============================================================
-- SaleOrder Table RLS
-- ============================================================

ALTER TABLE ventas_saleorder ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas_saleorder FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS saleorder_tenant_isolation ON ventas_saleorder;
CREATE POLICY saleorder_tenant_isolation ON ventas_saleorder
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY saleorder_tenant_isolation ON ventas_saleorder IS
'Ensures sale orders are only visible/modifiable within their tenant context.';

-- ============================================================
-- SaleOrderItem Table RLS
-- ============================================================

ALTER TABLE ventas_saleorderitem ENABLE ROW LEVEL SECURITY;
ALTER TABLE ventas_saleorderitem FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS saleorderitem_tenant_isolation ON ventas_saleorderitem;
CREATE POLICY saleorderitem_tenant_isolation ON ventas_saleorderitem
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY saleorderitem_tenant_isolation ON ventas_saleorderitem IS
'Ensures sale order items are only visible/modifiable within their tenant context.';

-- ============================================================
-- Grant permissions to app role for ventas tables
-- ============================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ventas_customer TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ventas_saleorder TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ventas_saleorderitem TO gravitea_app;

-- ============================================================
-- Verification Query for Ventas Tables
-- ============================================================

-- SELECT
--     t.tablename,
--     c.relrowsecurity AS rowsecurity,
--     c.relforcerowsecurity AS forcerowsecurity
-- FROM pg_tables t
-- JOIN pg_class c ON c.relname = t.tablename
-- JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.schemaname
-- WHERE t.schemaname = 'public'
-- AND t.tablename IN (
--     'ventas_customer',
--     'ventas_saleorder',
--     'ventas_saleorderitem'
-- )
-- ORDER BY t.tablename;
