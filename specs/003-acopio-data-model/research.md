# Research: Acopio Data Model & Domain Model

**Branch**: `003-acopio-data-model` | **Date**: 2026-03-16
**Phase**: 0 — Pre-design domain fact consolidation
**Status**: Complete — no NEEDS CLARIFICATION items remain

---

## Domain Decisions

### D-001: MermaTable Entity Scope

**Decision**: MermaTable holds per-grain zarandeo thresholds only (materias_extranas % ranges → %zarandeo deduction). It does NOT hold manipuleo or volatil values.

**Rationale**: Manipuleo and volatil are fixed regulatory constants that have never changed since publication. They belong on GrainType as static constants. MermaTable is versioned (valid_from/valid_to) because the Cámara Arbitral de Cereales periodically updates zarandeo schedules in response to harvest quality variability.

**Alternatives considered**: (a) Merge all merma parameters into GrainType — rejected because zarandeo thresholds ARE versioned (regulatory updates); (b) Full MermaTable with all four parameters — rejected because manipuleo/volatil are never updated and would create unnecessary versioning overhead.

---

### D-002: QualityParameter Not a Separate Entity

**Decision**: No `QualityParameter` model. Quality measurement fields are defined inline in `QualityAnalysis` with grain-type conditionality captured in `help_text`.

**Rationale**: The 9 quality measurement parameters (humedad, materias_extranas, granos_dañados, granos_quebrados, peso_hectolitrico, proteina, granos_verdes, granos_ardidos, cuerpos_extranos) are a fixed, well-known set per Argentine grain trade regulations. A lookup table adds no value — it would be queried on every QualityAnalysis read without enabling any flexibility. Grain-type conditionality (peso_hectolitrico for cereals only, proteina for trigo only, granos_verdes for soja only) is handled at the application validation layer.

**Alternatives considered**: Standalone QualityParameter entity with FK from QualityAnalysis — rejected as over-engineering for a fixed parameter set.

---

### D-003: WeighbridgeDevice as Separate Entity

**Decision**: `WeighbridgeDevice` is a separate entity (name, serial_number, branch FK, is_active, interface_type, connection_address). `WeighbridgeCalibration.device FK` → `WeighbridgeDevice`.

**Rationale**: A weighbridge is a distinct physical asset that accumulates multiple calibration records over its lifetime. Pointing directly to Branch would prevent multi-scale branches and lose serial/certificate traceability required for regulatory audits (calibration records must be traceable to a specific device). One branch may have a primary and secondary scale for redundancy.

**Alternatives considered**: (a) FK to Branch — rejected (no device traceability); (b) FK to StorageUnit — rejected (weighbridge is not a storage unit).

---

### D-004: ToleranceTable is Global (Not Per-Tenant)

**Decision**: ToleranceTable and MermaTable are GLOBAL reference tables — no tenant FK. All tenants share the same regulated versions from Cámara Arbitral de Cereales.

**Rationale**: Tolerance tables are issued by the Cámara Arbitral de Cereales de la Bolsa de Comercio de Rosario via SAGPyA/SENASA resolutions. They are legally binding and apply uniformly to all market participants. Custom tenant overrides would violate regulatory compliance.

**Alternatives considered**: Per-tenant tolerance overrides — rejected because tolerance tables are regulatory (not configurable), and divergence from official tables would expose tenants to legal/commercial dispute risk.

---

### D-005: Posición Consolidada is Derived, Not Stored

**Decision**: No `PosicionConsolidada` model. The cross-plant consolidated view is computed on-demand by aggregating per-plant `ProducerAccount` balances for the same producer CUIT across all plants of the same tenant.

**Rationale**: Storing an aggregate would introduce consistency risk (aggregate can diverge from source data). SQL aggregation over a bounded dataset (typically 1–5 plants per tenant, 200–2000 producers) is fast enough for real-time display. Storing it would require invalidation triggers on every AccountMovement.

**Alternatives considered**: Materialized view (PostgreSQL) — deferred to implementation phase (spec-09+) as an optimization if query profiling shows need.

---

### D-007: ON DELETE CASCADE for 1:1 Satellite Entities (Constitution Exception)

**Decision**: Three entities use `ON DELETE CASCADE` (not `RESTRICT/PROTECT`) for their FK to Romaneo: `CPE`, `QualityAnalysis`, `MermaCalculation`. Several nullable assignment fields use `SET_NULL`.

**Rationale**: Constitution P-I states "ON DELETE RESTRICT on all foreign keys" as the default. These are documented exceptions:
- **CASCADE** — `CPE`, `QualityAnalysis`, `MermaCalculation` are 1:1 satellite records that have no meaning without their parent Romaneo. If a Romaneo is deleted (only possible before CONFORME state), its satellites must be cleaned up atomically. Orphan satellite rows would be unreachable data. This matches the same pattern used for `AlicIva`, `Tributo`, `CbteAsoc → Comprobante` in the existing facturacion module.
- **SET_NULL** — `Romaneo.weighbridge_device`, `Romaneo.storage_unit`, `Romaneo.grain_lot` are nullable assignment fields. Deleting a device or storage unit must not cascade to delete historical romaneos.

**Alternatives considered**: RESTRICT on all FKs — rejected for satellites because it would prevent deletion of any romaneo (even pre-confirmation drafts) once a QualityAnalysis or CPE was created, making the UI unusable during data-entry correction. Triggers for cleanup — rejected as more complex than CASCADE with no benefit.

**How to apply**: Implementation specs MUST document this exception in migration comments. Any new satellite 1:1 entity of a ledger model may use CASCADE with explicit justification.

---

### D-006: GrainType is Global (Not Per-Tenant)

**Decision**: `GrainType` has no tenant FK. Grain type definitions (codes, names, humidity values, merma constants) are global reference data derived from ARCA species codes and SAGPyA/SENASA regulations.

**Rationale**: The 5 main grains (trigo, maiz, soja, girasol, sorgo) and their regulatory constants are identical for all Argentine acopiadores. Tenant-specific grain types do not exist in the regulated market.

---

## Critical Domain Facts

### Hf vs Humedad Base (CRITICAL — ~168 kg/truck error if confused)

The secado merma formula uses Hf (formula humidity), NOT Humedad base (commercialization standard):

| Grain | Humedad Base (commercialization) | Hf (secado formula) | Diff |
|-------|----------------------------------|---------------------|------|
| Trigo | 14.0% | 13.5% | 0.5% |
| Maiz | 14.5% | 13.5% | 1.0% |
| Soja | 13.5% | 13.0% | 0.5% |
| Girasol | 11.0% | 10.5% | 0.5% |
| Sorgo | 15.0% | 13.5% | 1.5% |

Formula: `%S = (Hi − Hf) / (100 − Hf) × 100` where Hi = measured humidity, Hf = GrainType.hf_secado_pct

If Hi ≤ Hf: secado_pct = 0 (no drying deduction applies).

### Sequential Merma Formula

```
Step 1: Peso_post_zarandeo  = peso_neto_bruto × (1 − zarandeo_pct/100)
Step 2: Peso_post_secado    = peso_post_zarandeo × (1 − secado_pct/100)
Step 3: Peso_post_manipuleo = peso_post_secado × (1 − manipuleo_pct/100)
Step 4: Peso_final          = peso_post_manipuleo × (1 − volatil_pct/100)
```

Fixed values per grain (from GrainType, not MermaTable):
- Manipuleo: trigo 0.10%, maiz 0.25%, soja 0.25%, girasol 0.20%, sorgo 0.25%
- Volátil: cereales (trigo/maiz/sorgo) 0.30%, oleaginosas (soja/girasol) 0.50%

Zarandeo comes from MermaTable lookup by (grain_type, materias_extranas_pct) at active version on ts_entrada.

### AccountMovement Transaction Types (Authoritative)

8 types per PRD v1.0 §4.4:
1. `CEG_DEPOSIT` — grain deposit from romaneo (credit grain kg sub-ledger)
2. `LPG_SALE` — grain sold via LiquidacionPrimaria (debit grain kg, credit ARS)
3. `FIJACION` — price crystallization for "a fijar" grain (updates monetary sub-ledger)
4. `RETIRO` — physical grain withdrawal (debit grain kg)
5. `SERVICE_CHARGE` — storage/conditioning fee (debit ARS or grain kg)
6. `CANJE_GRAIN_DEBIT` — grain debited for canje exchange (debit grain kg)
7. `CANJE_INPUT_CREDIT` — inputs credited from canje (debit ARS for input invoice)
8. `RETENTION_DEDUCTION` — tax retention applied at LPG (debit ARS)

### WSLPG Key Fields (Form 1116-C / Liquidación Primaria)

Mandatory XML elements:
- `tipo_reg` (String, 1 char) — record type identifier
- `puntoEmision` (Integer, 4 digits) — registered point of sale
- `numeroOrden` (Integer, 8 digits) — sequential, must be lastAuthorized+1
- `fechaEmision` (Date, YYYY-MM-DD) — fiscal date
- `codTipoOperacion` (Enum, 2 digits) — 01=Compra/Venta, 02=Consignación
- `cuitComprador` (String, 11 digits) — buyer CUIT
- `codGrano` (Integer, 2 digits) — grain type at ROOT level (single-grain-type constraint)
- `campania` (Integer, 4 digits) — campaign in YYZZ format (e.g., 2425)
- `codGrado` (Integer, 2 digits) — optional — quality grade code
- `pesoNetoGranos` (Integer, kg) — net weight of grain
- `precioReferencia` (Decimal) — reference price per tonne
- `importeBruto` (Decimal) — gross amount
- `importeNeto` (Decimal) — net amount after deductions
- `alicuotaIva` (Decimal) — VAT rate (10.5% for grain)
- `importeIva` (Decimal) — VAT amount
- `retenciones` (Array) — array of {codRetencion, importeRetencion}

CRITICAL constraint: One Form 1116-C = ONE grain type only. Separate XML submission per grain type required.

### Grading Systems by Grain Type

- **Cereals** (trigo, maiz, sorgo): Grado 1 / Grado 2 / Grado 3 / Fuera de Estándar
  - Grado 1: Bonificación 1.0–1.5% (varies by grain)
  - Grado 2: No adjustment (reference grade)
  - Grado 3: Rebaja 1.0–1.5% (varies by grain)
- **Oleaginosas** (soja, girasol): Progressive rebaja % per point above tolerance per parameter
  - Soja example: materias_extranas > 1% → rebaja 1%/point up to 3%, then 1.5%/point above 3%

### Campaign Format

Format: `YYYY/YY` — 7 characters. Examples: "2024/25", "2025/26".
Starts: April 1st of opening year. Ends: March 31st of closing year.
WSLPG XML uses 4-digit format: "2425" (not "2024/25").
CampanaConfig.campaign_code stores the human-readable "YYYY/YY" format.

### CPE Lifecycle (WSCPE methods)

```
Activa → confirmarArriboCPE → Arribo_Confirmado
Arribo_Confirmado → descargadoDestinoCPE → Descargada
Descargada → confirmacionDefinitivaCPEAutomotor → Confirmada_Definitiva
```

CPE validity: 5-day window from issuance. Store-and-forward required for offline operations.

---

## Research Sources

| Decision | RAG Source |
|----------|-----------|
| D-001 MermaTable | `2.1 Day-to-Day Operations` (Paso 5) + `2.2 Grain Quality Management Standards` |
| D-002 QualityParameter | `8.1 Grain Types and Quality Parameter Reference Data` |
| D-004 ToleranceTable global | `2.1` (Paso 5 — "Cámara Arbitral de Cereales... SAGPyA/SENASA resolutions") |
| Domain facts | `2.3 Producer Current Accounts`, `8.4 Form 1116 B-C Field Structure`, `5.1 WSLPG Technical API` |
