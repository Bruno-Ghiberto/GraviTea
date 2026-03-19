# Spec 10: Romaneo Core -- Feature Specification Context

## Feature Description

Implement the romaneo workflow — the heart of the acopio ERP. This spec
creates the Django models, Rust calculation engines, DRF serializers,
views, and tests for grain reception (romaneo), quality analysis, and
merma calculations.

The romaneo is the atomic operational unit: every truck arrival produces
exactly one romaneo that captures weighing, quality analysis, merma
deductions, and the final peso neto conforme. This spec implements the
complete workflow from truck arrival to finalized romaneo.

## Research Inputs

### Must-Read

- `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md`
  Sections: Paso 1-7 (arrival, weighing, sampling, analysis, grading, tara, merma)

- `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md`
  Full document. Field-by-field spec for romaneo data structure.

- `Docs/Researches/Markdown/2.5 Merma (Grain Loss) Calculations and Tolerance Tables.md`
  Full document. Sequential merma formulas with worked examples.

- `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md`
  Full document. Quality parameters, grade determination, bonification/rebaja.

### RAG Queries

- "romaneo workflow steps truck arrival to finalized"
- "merma calculation formula zarandeo secado manipuleo volatil"
- "quality analysis parameters humidity peso hectolitrico"
- "grain grading grade 1 2 3 fuera de estandar"

### Critical Domain Facts

- Romaneo status lifecycle: BORRADOR -> CONFIRMADO -> LIQUIDADO
- Romaneo is IMMUTABLE after CONFIRMADO (same pattern as Comprobante)
- Merma order: peso_neto_bruto -> (-zarandeo) -> (-secado) -> (-manipuleo) -> (-volatil) = peso_neto_conforme
- Merma de secado formula: merma_pct = 100 * (Hi - Hf) / (100 - Hf) where Hi=initial humidity, Hf=base humidity
- Merma volatil: cereals 0.3%, oleaginosas 0.5%
- Merma manipuleo: trigo 0.10%, maiz/soja 0.25%, girasol 0.20%
- All weight fields: DecimalField(max_digits=11, decimal_places=3)
- All percentage fields: DecimalField(max_digits=5, decimal_places=2)

## Requirements

### Functional Requirements

FR-001: Romaneo model with all fields from spec-03 data model
FR-002: QualityAnalysis model linked to Romaneo (one-to-one)
FR-003: MermaCalculation model linked to Romaneo (one-to-one, immutable)
FR-004: Romaneo status lifecycle: BORRADOR -> CONFIRMADO -> LIQUIDADO
FR-005: CONFIRMADO/LIQUIDADO romaneos are immutable (save raises ValueError)
FR-006: Rust merma engine (merma.rs) — sequential calculation with full provenance
FR-007: Rust grading engine (grading.rs) — grade determination against tolerance tables
FR-008: DRF serializers for Romaneo, QualityAnalysis, MermaCalculation
FR-009: DRF viewsets with romaneo workflow actions (create, add_quality, calculate_merma, confirm)
FR-010: On confirmation: auto-credit producer account (via spec-12 integration point)
FR-011: On confirmation: auto-assign storage unit (via spec-11 integration point)
FR-012: All models inherit TenantBoundModel with IDOR validation

### Non-Functional Requirements

NF-001: Rust merma calculation < 1ms per romaneo
NF-002: Merma results match manual calculation to 3 decimal places
NF-003: All 5 grain types supported with correct tolerance tables
NF-004: Offline-capable: merma engine runs locally via Rust FFI

## Key Technical Details

### Rust Merma Engine (merma.rs)

```rust
/// Sequential merma calculation with full provenance
pub struct MermaInput {
    pub peso_neto_bruto: Decimal,
    pub humedad_pct: Decimal,
    pub humedad_base: Decimal,
    pub zarandeo_pct: Decimal,
    pub zarandeo_tolerancia: Decimal,
    pub merma_volatil_pct: Decimal,
    pub merma_manipuleo_pct: Decimal,
}

pub struct MermaResult {
    pub peso_post_zarandeo: Decimal,
    pub merma_zarandeo_kg: Decimal,
    pub peso_post_secado: Decimal,
    pub merma_secado_kg: Decimal,
    pub merma_secado_pct: Decimal,
    pub peso_post_manipuleo: Decimal,
    pub merma_manipuleo_kg: Decimal,
    pub peso_neto_conforme: Decimal,
    pub merma_volatil_kg: Decimal,
    pub merma_total_kg: Decimal,
    pub factor_total: Decimal,
}
```

### Romaneo Workflow Actions (views.py)

```
POST   /api/acopio/romaneos/              -> create (BORRADOR)
PATCH  /api/acopio/romaneos/{id}/          -> update (only BORRADOR)
POST   /api/acopio/romaneos/{id}/quality/  -> add quality analysis
POST   /api/acopio/romaneos/{id}/merma/    -> calculate merma (Rust)
POST   /api/acopio/romaneos/{id}/confirm/  -> confirm (BORRADOR -> CONFIRMADO)
GET    /api/acopio/romaneos/               -> list (filtered by campaign, grain, date)
GET    /api/acopio/romaneos/{id}/          -> detail with quality + merma
```

## Dependencies

- Depends on: spec-03 (Data Model), spec-09 (Grain Reference Data — needs GrainType, ToleranceTable)
- Blocks: spec-12 (Producer Accounts — romaneo confirmation credits account)
- Integrates with: spec-11 (Storage — romaneo confirmation assigns silo)
- Uses: existing Rust crate `rust/gravitea-core/` (extend with merma.rs, grading.rs)
- Uses: existing TenantBoundModel, immutable ledger pattern from apps/core

## Acceptance Criteria

AC-01: Romaneo CRUD with status lifecycle enforcement
AC-02: Quality analysis stores all grain-specific parameters
AC-03: Merma calculation via Rust returns correct results for all 5 grains
AC-04: Merma results include full provenance (every intermediate step)
AC-05: CONFIRMADO romaneos cannot be modified or deleted
AC-06: API endpoints follow DRF conventions with proper permissions
AC-07: All models pass TenantBoundModel IDOR validation
AC-08: Unit tests cover merma calculation for each grain type
AC-09: Integration test: full romaneo workflow from create to confirm
AC-10: Rust merma engine exposed via PyO3 and callable from Django
