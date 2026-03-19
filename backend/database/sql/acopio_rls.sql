-- ============================================================
-- Row Level Security (RLS) Policies for Acopio Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for CampanaConfig.
-- Global tables (GrainType, ToleranceTable, MermaTable) do NOT
-- receive RLS policies per ADR-010/NF-010-010.
-- ============================================================

-- ============================================================
-- CampanaConfig Table RLS
-- ============================================================

ALTER TABLE acopio_campanaconfig ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_campanaconfig FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS campanaconfig_tenant_isolation ON acopio_campanaconfig;
CREATE POLICY campanaconfig_tenant_isolation ON acopio_campanaconfig
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY campanaconfig_tenant_isolation ON acopio_campanaconfig IS
'Ensures campaign configs are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_campanaconfig TO gravitea_app;
