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

-- ============================================================
-- Romaneo Table RLS
-- ============================================================

ALTER TABLE acopio_romaneo ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_romaneo FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS romaneo_tenant_isolation ON acopio_romaneo;
CREATE POLICY romaneo_tenant_isolation ON acopio_romaneo
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY romaneo_tenant_isolation ON acopio_romaneo IS
'Ensures romaneos are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_romaneo TO gravitea_app;

-- ============================================================
-- QualityAnalysis Table RLS
-- ============================================================

ALTER TABLE acopio_qualityanalysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_qualityanalysis FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS qualityanalysis_tenant_isolation ON acopio_qualityanalysis;
CREATE POLICY qualityanalysis_tenant_isolation ON acopio_qualityanalysis
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY qualityanalysis_tenant_isolation ON acopio_qualityanalysis IS
'Ensures quality analyses are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_qualityanalysis TO gravitea_app;

-- ============================================================
-- MermaCalculation Table RLS
-- ============================================================

ALTER TABLE acopio_mermacalculation ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_mermacalculation FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mermacalculation_tenant_isolation ON acopio_mermacalculation;
CREATE POLICY mermacalculation_tenant_isolation ON acopio_mermacalculation
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY mermacalculation_tenant_isolation ON acopio_mermacalculation IS
'Ensures merma calculations are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_mermacalculation TO gravitea_app;
