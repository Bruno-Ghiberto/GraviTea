-- ============================================================
-- Row Level Security (RLS) Policies for Reportes Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for reportes tables.
-- All three reportes tables have tenant_id and get direct RLS policies.
-- ============================================================

-- ============================================================
-- ReportDefinition Table RLS
-- ============================================================

ALTER TABLE reportes_reportdefinition ENABLE ROW LEVEL SECURITY;
ALTER TABLE reportes_reportdefinition FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS reportdefinition_tenant_isolation ON reportes_reportdefinition;
CREATE POLICY reportdefinition_tenant_isolation ON reportes_reportdefinition
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY reportdefinition_tenant_isolation ON reportes_reportdefinition IS
'Ensures report definitions are only visible/modifiable within their tenant context.';

-- ============================================================
-- SavedReport Table RLS
-- ============================================================

ALTER TABLE reportes_savedreport ENABLE ROW LEVEL SECURITY;
ALTER TABLE reportes_savedreport FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS savedreport_tenant_isolation ON reportes_savedreport;
CREATE POLICY savedreport_tenant_isolation ON reportes_savedreport
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY savedreport_tenant_isolation ON reportes_savedreport IS
'Ensures saved reports are only visible/modifiable within their tenant context.';

-- ============================================================
-- ExportJob Table RLS
-- ============================================================

ALTER TABLE reportes_exportjob ENABLE ROW LEVEL SECURITY;
ALTER TABLE reportes_exportjob FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS exportjob_tenant_isolation ON reportes_exportjob;
CREATE POLICY exportjob_tenant_isolation ON reportes_exportjob
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY exportjob_tenant_isolation ON reportes_exportjob IS
'Ensures export jobs are only visible/modifiable within their tenant context.';

-- ============================================================
-- Grant permissions to app role for reportes tables
-- ============================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON reportes_reportdefinition TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON reportes_savedreport TO gravitea_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON reportes_exportjob TO gravitea_app;

-- ============================================================
-- Verification Query for Reportes Tables
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
--     'reportes_reportdefinition',
--     'reportes_savedreport',
--     'reportes_exportjob'
-- )
-- ORDER BY t.tablename;
