# Spec 03: Data Model & Domain Model -- Specification Context

## Feature Description

Rewrite the `Docs/Project Blueprint/Data Model & Domain Model.md`
document to reflect the acopio de granos vertical pivot. The current
document (v0.3) describes a generic retail ERP with Product, Customer,
Supplier, SaleOrder, PurchaseOrder models. The new document must
define the complete grain domain model with AI-ready data architecture.

The rewritten document is the SINGLE SOURCE OF TRUTH for all Django
models. Every implementation spec (09-12+) derives its model
definitions from this document.

## Current State (what exists)

The existing Data Model doc (v0.3) contains:
- "Ironclad" design manifesto (Principles 1-4) — PRESERVE
- ERD with generic ERP entities — REPLACE with grain domain
- Tenant/Branch/Role/AppUser — PRESERVE (infrastructure)
- Product/ProductCategory/StockMovement — ADAPT for dual inventory
- Customer/SaleOrder/SaleOrderItem — PRESERVE for service invoicing (facturacion to producers) + ADD new grain domain models alongside (Romaneo, ProducerAccount, LiquidacionPrimaria are new, not replacements of SaleOrder)
- Supplier/PurchaseOrder/GoodsReceipt — ADAPT for agronomia input procurement (reuse existing models, extend Product with batch/lot/expiration)
- Comprobante/AlicIva/Tributo — PRESERVE + extend for WSLPG
- SyncSession/PendingOperation — PRESERVE
- RLS policies reference — UPDATE

## Research Inputs

### RAG Queries (run these FIRST — do NOT read full research files)

Use the RAG pipeline to gather domain knowledge. Run these queries
BEFORE reading any research files directly:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

Queries to run:
- "romaneo data fields capture ERP weight quality"
- "merma calculation formula sequential zarandeo secado"
- "grain quality parameters humidity peso hectolitrico"
- "producer current account balance grain kilogram"
- "WSLPG Form 1116-C XML field types lengths"
- "storage unit silo celda capacity tracking"
- "campaign year management grain segregation"
- "AI ready data model grain ERP training features"
- "tolerance tables bonification rebaja grain"
- "chart of accounts acopio inventory valuation"

### Source Documents (for reference — prefer RAG results above)

Only read specific sections if RAG results are insufficient:

| Doc ID | Relevant Sections |
|--------|------------------|
| 8.3 | Header/Identification, Volumetric Data, Quality Metrics, Deductions |
| 8.1 | Grain codes, humidity bases, quality params per grain, grade definitions |
| 8.4 | WSLPG XML field types, lengths, precision, mandatory/optional |
| 2.1 | Paso 1-10 (romaneo workflow, data capture points) |
| 2.5 | Merma formulas, tolerance tables per grain |
| 2.3 | Account structure, movement types, canje mechanics |
| 2.2 | Quality parameters per grain, grade definitions |
| 2.6 | Campaign lifecycle, data segregation |
| 7.1 | Inventory valuation, account structure |
| 9.1 | Data requirements per AI feature |

### Critical Domain Facts

- Merma calculation order: peso_neto_bruto -> (-zarandeo) -> (-secado) -> (-manipuleo) -> (-volatil) = peso_neto_conforme
- 5 main grains with TWO distinct humidity values each:
  - Humedad base (commercialization standard): trigo 14.0%, maiz 14.5%, soja 13.5%, girasol 11.0%, sorgo 15.0%
  - Hf (merma secado formula): trigo 13.5%, maiz 13.5%, soja 13.0%, girasol 10.5%, sorgo 13.5%
  - CRITICAL: the secado formula `%S = (Hi - Hf) / (100 - Hf)` uses Hf, NOT Humedad base. Using wrong value yields ~168 kg error per 30,000 kg truck.
- Romaneo is IMMUTABLE after CONFIRMED status (like Comprobante pattern)
- Producer accounts have 3 dimensions: kg per grain type, ARS, USD
- Tolerance tables are VERSIONED (change yearly, old romaneos reference old version)
- Every measurement field needs a timestamp for AI behavioral analytics
- Vehicle plates (patente_chasis, patente_acoplado) must be tracked across romaneos for fraud detection baselines
- Decimal precision: ALL weight AND monetary fields use DECIMAL(17,3) consistent with existing Comprobante pattern (Constitution Principle I). WSLPG XML serialization handles any precision adaptation at the API layer, not the model layer.
- Campaign format: "YYYY/YY" = "2024/25", "2025/26" (7 chars, starts April, ends March)
- Manipuleo fixed values: trigo 0.10%, maiz 0.25%, soja 0.25%, girasol 0.20%, sorgo 0.25%
- Volatil fixed values: cereales (trigo/maiz/sorgo) 0.30%, oleaginosas (soja/girasol) 0.50%
- WSLPG constraint: a single Form 1116-C/B CANNOT cover multiple grain types — one liquidation = one grain type (codGrano at root level). Software must generate separate XML payloads per grain type.
- WSLPG numbering: compound key (puntoEmision + numeroOrden) — query `consultarUltimoNroOrden` before generating new
- Chart of accounts distinction: own grain (1.3.XX Bienes de cambio) vs third-party grain (8.1.XX Cuentas de orden — off-balance-sheet). Only purchased grain appears as asset.
- Tolerance tables source: Cámara Arbitral de Cereales de Rosario via SAGPyA/SENASA resolutions. Cereals use Grado 1/2/3; oleaginosas use progressive rebaja % per point above tolerance.
- ERP must capture per-romaneo: grado assigned, bonificación/rebaja %, each excess-tolerance detail (rubro, % exceso, % descuento), total factor (Factor 100 ± adjustments)
- QualityAnalysis required fields per grain: humedad (%), materias_extranas (%), granos_danados (%), granos_quebrados (%), peso_hectolitrico (kg/hl, cereals only), proteina (%, trigo only), granos_verdes (%, soja), granos_ardidos (%), cuerpos_extranos (%)
- AccountMovement transaction types (8, authoritative per PRD v1.0 §4.4): CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION
- Key WSLPG XML field names for LiquidacionPrimaria mapping: nroOrden, cuitComprador, codGrano, campania, codGrado, pesoNetoGranos, precioReferencia, importeBruto, importeNeto, alicuotaIva, importeIva, retenciones (array: codRetencion, importeRetencion)
- Romaneo must have 2 patente fields: patente_chasis (truck) and patente_acoplado (trailer) — both required for fraud detection baselines

## Requirements

### Functional Requirements

FR-001: Define all grain domain models (GrainType, Campaign, QualityParameter, ToleranceTable, MermaTable, Romaneo, QualityAnalysis, MermaCalculation, StorageUnit, GrainLot, GrainMovement)
FR-002: Define producer account models (ProducerAccount, AccountMovement) with 8 transaction types (CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION) and partial fijacion tracking (remaining unfixed kg balance per CEG)
FR-003: Define reference data versioning pattern (valid_from, valid_to on tolerance/merma tables)
FR-004: Preserve existing infrastructure models (Tenant, Branch, Role, AppUser, TenantBoundModel)
FR-005: Adapt existing inventory models for agronomia (Product gets batch/lot, expiration)
FR-006: Preserve existing facturacion models (Comprobante) + define LiquidacionPrimaria
FR-007: Define dual inventory architecture (grain continuous vs discrete SKU)
FR-008: All grain domain models inherit TenantBoundModel
FR-009: All weight AND monetary fields use DECIMAL(17,3) consistent with existing Comprobante pattern. WSLPG XML precision differences are handled at the API serialization layer, not the model layer. Percentage fields use DECIMAL(5,2).
FR-010: Every model includes created_at, updated_at, created_by (AI-ready provenance)
FR-011: Romaneo model captures ALL intermediate calculation steps (not just final result)
FR-012: Quality analysis stores raw measurements alongside derived grades
FR-013: MermaCalculation is a separate immutable record linked to Romaneo
FR-014: Reference data (tolerance tables, merma formulas) is version-controlled
FR-015: ERD diagrams use Mermaid syntax for all entity relationships
FR-016: Cross-module links documented (Romaneo -> ProducerAccount credit, Romaneo -> StorageUnit assignment)
FR-017: RLS policy templates for new tables
FR-018: LiquidacionPrimaria enforces single-grain-type constraint (1 form = 1 codGrano) per WSLPG schema
FR-019: WSLPG field mapping table with explicit XML element names, types, max_digits, and mandatory/optional
FR-020: Distinguish own grain (balance-sheet asset) vs third-party grain (off-balance-sheet cuentas de orden) in ProducerAccount/GrainMovement
FR-021: CPE/CTG model linked to Romaneo (1:1) with lifecycle state tracking per WSCPE methods
FR-022: WeighbridgeCalibration model (calibration_date, technician, reference_weight, deviation, next_due_date, scale FK)
FR-023: FijacionRecord model linked to CEG (partial fijacion: pizarra_price, kg_fixed, remaining_unfixed_kg, LPG FK)
FR-024: CanjeOperation model with dual document streams (LPG FK for grain + Comprobante FK for inputs), canje_total/parcial flag
FR-025: CampanaConfig model (campaign_code YYYY/YY, start_date, end_date, is_active, per-tenant)
FR-026: Romaneo must include patente_chasis AND patente_acoplado as separate fields
FR-027: Romaneo must include 6 named timestamps: ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara
FR-028: Romaneo must include operator_id and laboratorista_id FKs to AppUser
FR-029: FR-001 through FR-028 collectively supersede all 11 entities from spec-02 data-model.md. The spec-03 entity set is authoritative.

### Non-Functional Requirements

NF-001: AI-ready — every model captures enough metadata for ML training
NF-002: Temporal precision — 6 timestamps per romaneo (entrada, pesada_bruta, calado, analisis, descarga, tara)
NF-003: Vehicle tracking — patente fields for fraud detection baselines
NF-004: Operator tracking — operator and laboratorista FKs for behavioral analytics
NF-005: Device tracking — device_id for offline provenance
NF-006: Calculation provenance — every derived field traces to its inputs

## Target Document Structure

```
1. Metadata
2. Design Manifesto "Ironclad" (preserve + extend for AI-ready)
   2.1 Principles (add: "AI-Ready Data Architecture")
3. ERD — Global View (new grain domain + dual inventory)
4. Core Infrastructure (Tenant, Branch, AppUser — preserve)
5. Grain Domain
   5.1 Reference Data (GrainType, Campaign, QualityParameter)
   5.2 Tolerance & Merma Tables (versioned)
   5.3 Romaneo (complete field spec, workflow states)
   5.4 Quality Analysis (per-romaneo lab results)
   5.5 Merma Calculation (immutable calculation record)
   5.6 Storage (StorageUnit, GrainLot, GrainMovement)
6. Producer Accounts
   6.1 ProducerAccount (multi-dimensional balance)
   6.2 AccountMovement (all transaction types)
7. Agronomia / Discrete Inventory
   7.1 Product (adapted: +batch, +lot, +expiration)
   7.2 StockMovement (preserved for SKU inventory)
8. Facturacion
   8.1 Comprobante (preserved for service invoices)
   8.2 LiquidacionPrimaria (NEW — Form 1116-C)
   8.3 WSLPG field mapping
9. Sync (preserved)
10. Cross-Module Links
11. RLS Policies
12. AI-Ready Data Architecture
    12.1 4-Layer data strategy
    12.2 Feature store readiness
    12.3 Training data generation from operational data
```

## Acceptance Criteria

AC-01: Every model has explicit field definitions (name, type, max_digits, null, default, help_text)
AC-02: Every model inherits TenantBoundModel (except Tenant, Branch)
AC-03: Romaneo model has >= 30 fields covering all measurement, temporal, operational, and vehicle data
AC-04: QualityAnalysis captures all grain-specific params from research doc 8.1
AC-05: MermaCalculation records formula, inputs, parameters, and output (calculation provenance)
AC-06: ToleranceTable and MermaTable have valid_from/valid_to versioning
AC-07: ProducerAccount supports 3 balance dimensions (grain kg per type, ARS, USD)
AC-08: ERD diagrams render correctly in Mermaid
AC-09: All cross-module FKs documented with ON DELETE behavior
AC-10: AI-ready section explains which fields serve as ML features and for which AI capability
AC-11: Document is self-consistent (no field name mismatches between ERD and field tables)

## Dependencies

- Depends on: spec-01 (Vision — market context), spec-02 (PRD — functional requirements)
- Blocks: spec-05 (HLD), spec-06 (API Design), spec-09 through spec-12 (all impl specs)
- References: existing `Docs/Project Blueprint/Data Model & Domain Model.md` (v0.3)
