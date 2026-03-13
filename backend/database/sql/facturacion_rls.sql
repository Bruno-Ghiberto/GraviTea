-- ============================================================
-- Row Level Security (RLS) Policies for Facturacion Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for electronic invoicing tables.
-- Tables with tenant_id get direct RLS policies.
-- AlicIva, Tributo, CbteAsoc use FK-subquery RLS via Comprobante.tenant_id.
-- ============================================================

-- ============================================================
-- ARCACredential Table RLS
-- ============================================================

ALTER TABLE facturacion_arcacredential ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_arcacredential FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS arcacredential_tenant_isolation ON facturacion_arcacredential;
CREATE POLICY arcacredential_tenant_isolation ON facturacion_arcacredential
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY arcacredential_tenant_isolation ON facturacion_arcacredential IS
'Ensures ARCA credentials are only visible/modifiable within their tenant context.';

-- ============================================================
-- PuntoDeVenta Table RLS
-- ============================================================

ALTER TABLE facturacion_puntodeventa ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_puntodeventa FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS puntodeventa_tenant_isolation ON facturacion_puntodeventa;
CREATE POLICY puntodeventa_tenant_isolation ON facturacion_puntodeventa
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY puntodeventa_tenant_isolation ON facturacion_puntodeventa IS
'Ensures puntos de venta are only visible/modifiable within their tenant context.';

-- ============================================================
-- Comprobante Table RLS
-- ============================================================

ALTER TABLE facturacion_comprobante ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_comprobante FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS comprobante_tenant_isolation ON facturacion_comprobante;
CREATE POLICY comprobante_tenant_isolation ON facturacion_comprobante
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY comprobante_tenant_isolation ON facturacion_comprobante IS
'Ensures comprobantes are only visible/modifiable within their tenant context.';

-- ============================================================
-- CAEA Table RLS
-- ============================================================

ALTER TABLE facturacion_caea ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_caea FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS caea_tenant_isolation ON facturacion_caea;
CREATE POLICY caea_tenant_isolation ON facturacion_caea
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY caea_tenant_isolation ON facturacion_caea IS
'Ensures CAEA records are only visible/modifiable within their tenant context.';

-- ============================================================
-- AlicIva Table RLS (FK → Comprobante)
-- ============================================================

ALTER TABLE facturacion_aliciva ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_aliciva FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS aliciva_tenant_isolation ON facturacion_aliciva;
CREATE POLICY aliciva_tenant_isolation ON facturacion_aliciva
    USING (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid))
    WITH CHECK (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid));

COMMENT ON POLICY aliciva_tenant_isolation ON facturacion_aliciva IS
'Ensures AlicIva records are only visible/modifiable within their tenant context via comprobante relationship.';

-- ============================================================
-- Tributo Table RLS (FK → Comprobante)
-- ============================================================

ALTER TABLE facturacion_tributo ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_tributo FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tributo_tenant_isolation ON facturacion_tributo;
CREATE POLICY tributo_tenant_isolation ON facturacion_tributo
    USING (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid))
    WITH CHECK (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid));

COMMENT ON POLICY tributo_tenant_isolation ON facturacion_tributo IS
'Ensures Tributo records are only visible/modifiable within their tenant context via comprobante relationship.';

-- ============================================================
-- CbteAsoc Table RLS (FK → Comprobante)
-- ============================================================

ALTER TABLE facturacion_cbteasoc ENABLE ROW LEVEL SECURITY;
ALTER TABLE facturacion_cbteasoc FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS cbteasoc_tenant_isolation ON facturacion_cbteasoc;
CREATE POLICY cbteasoc_tenant_isolation ON facturacion_cbteasoc
    USING (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid))
    WITH CHECK (comprobante_id IN (SELECT id FROM facturacion_comprobante WHERE tenant_id = current_setting('app.current_tenant_id')::uuid));

COMMENT ON POLICY cbteasoc_tenant_isolation ON facturacion_cbteasoc IS
'Ensures CbteAsoc records are only visible/modifiable within their tenant context via comprobante relationship.';

-- ============================================================
-- Grant permissions to app role for facturacion tables
-- ============================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_arcacredential TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_puntodeventa TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_comprobante TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_aliciva TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_tributo TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_cbteasoc TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON facturacion_caea TO gravitea_app;

-- ============================================================
-- Verification Query for Facturacion Tables
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
--     'facturacion_arcacredential',
--     'facturacion_puntodeventa',
--     'facturacion_comprobante',
--     'facturacion_caea',
--     'facturacion_aliciva',
--     'facturacion_tributo',
--     'facturacion_cbteasoc'
-- )
-- ORDER BY t.tablename;
