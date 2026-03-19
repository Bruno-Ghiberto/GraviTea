---
spec: "011"
name: "Romaneo Core"
type: Implementation
branch: 011-romaneo-core
created: 2026-03-19
depends_on: [spec-10]
blocks: [spec-12, spec-13]
deliverable: "backend/apps/acopio/ models/views + rust/gravitea-core/src/merma.rs"
qdrant_collections: [acopio_research, arca_dev_guides]
agents: [A1, A2, A3, A4, A5, A6]
---

# Spec-11: Romaneo Core -- Specification Context

## Feature Description

Implement the romaneo (grain reception document) lifecycle and its satellite
entities -- the central transactional workflow of the acopio operation. This spec
creates the following deliverables within the existing `backend/apps/acopio/`
application (established by spec-10):

1. **Romaneo model** -- the 31-field, 7-group grain reception document with a
   6-state state machine (PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO ->
   CONFORME -> CERRADO). Immutable after CONFORME (same pattern as
   `Comprobante` in AUTORIZADO state).
2. **QualityAnalysis model** -- one-to-one satellite of Romaneo capturing 9+
   quality parameters from the grain sample (humidity, foreign matter, damaged
   grains, broken grains, hectolitre weight, protein, green grains, heat-damaged
   grains, foreign bodies).
3. **MermaCalculation model** -- one-to-one immutable satellite storing the
   sequential merma formula result with all inputs, intermediate values, and
   final conforming weight for full audit reconstruction.
4. **Rust merma engine** (`rust/gravitea-core/src/merma.rs`) -- the sequential
   merma calculation (zarandeo -> secado -> manipuleo -> volatil) implemented in
   Rust with PyO3 bindings, following the Circular CAC 10/86 formula. Exposed as
   `calculate_merma()` to Python.
5. **DRF serializers and viewsets** implementing REST API Design v1.0 Section 5
   -- romaneo CRUD, 6 state transition action endpoints, quality analysis
   nested endpoints, and merma preview endpoint.
6. **Test suite** covering models, state machine transitions, merma calculation
   correctness, API endpoints, immutability enforcement, and tenant isolation.

This builds directly on spec-10's reference data models (GrainType, ToleranceTable,
MermaTable, CampanaConfig) which provide the lookup tables consumed by the merma
engine and quality grading logic.

---

## Current State

### What Exists (from spec-10)

- `backend/apps/acopio/` -- Django app registered in `INSTALLED_APPS` with URL
  routing at `/api/v1/acopio/`.
- `backend/apps/acopio/models/grain_type.py` -- `GrainType` (GLOBAL). Fields
  include `hf_secado_pct`, `manipuleo_fijo_pct`, `volatil_fijo_pct`,
  `grading_system`. These are direct inputs to the merma engine.
- `backend/apps/acopio/models/tolerance_table.py` -- `ToleranceTable` (GLOBAL).
  Quality parameter tolerance thresholds per grain type and grade, with temporal
  versioning (`valid_from`/`valid_to`).
- `backend/apps/acopio/models/merma_table.py` -- `MermaTable` (GLOBAL). Zarandeo
  deduction bands per grain type with temporal versioning.
- `backend/apps/acopio/models/campana_config.py` -- `CampanaConfig`
  (TenantBound). Per-tenant campaign year config with `wslpg_code` property.
- `backend/apps/acopio/serializers/reference_data.py` -- 4 serializers.
- `backend/apps/acopio/views/reference_data.py` -- 4 viewsets (GrainType,
  CampanaConfig, ToleranceTable, MermaTable).
- `backend/apps/acopio/pagination.py` -- `ReferenceDataPagination` (page-number).
- `backend/apps/acopio/urls.py` -- DRF router with 4 registered viewsets.
- `backend/apps/core/models/mixins.py` -- `TenantBoundModel` (lines 28-137),
  `TimestampedModel`, `SoftDeleteModel` abstract base classes.
- `backend/apps/core/managers/tenant_bound.py` -- `TenantBoundManager` with
  fail-closed tenant filtering and `AllObjectsManager`.
- `backend/apps/inventario/models.py` -- `StockMovement` (lines 470-675)
  demonstrates the immutable ledger pattern that Romaneo must follow.
- `rust/gravitea-core/src/` -- existing Rust modules: `arca.rs`, `compute.rs`,
  `crypto.rs`, `decimal_utils.rs`, `errors.rs`, `export.rs`, `observability.rs`,
  `security.rs`, `sync.rs`, `validation.rs`. No `merma.rs` exists yet.
- `rust/gravitea-core/src/lib.rs` -- PyO3 module registration pattern. New
  `merma.rs` functions must be registered here.
- `rust/gravitea-core/Cargo.toml` -- `rust_decimal` and `rust_decimal_macros`
  already available (required for merma precision).

### What Needs Creating

- `backend/apps/acopio/models/romaneo.py` -- Romaneo model (31 fields, 7 groups).
- `backend/apps/acopio/models/quality_analysis.py` -- QualityAnalysis model.
- `backend/apps/acopio/models/merma_calculation.py` -- MermaCalculation model.
- `backend/apps/acopio/serializers/romaneo.py` -- Romaneo, QualityAnalysis,
  MermaCalculation serializers.
- `backend/apps/acopio/views/romaneo.py` -- RomaneoViewSet with 6 state
  transition action endpoints, QualityAnalysis nested viewset.
- Updated `backend/apps/acopio/urls.py` -- register romaneo routes.
- Updated `backend/apps/acopio/models/__init__.py` -- re-export new models.
- `rust/gravitea-core/src/merma.rs` -- Rust merma calculation engine.
- Updated `rust/gravitea-core/src/lib.rs` -- register merma PyO3 exports.
- Database migration `0002_romaneo_core.py`.
- Test files for all new code.

---

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

```bash
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
    -q "romaneo peso bruto tara neto conforme" \
    -q "merma zarandeo secado manipuleo volatil" \
    -q "quality grading grade 1 2 3 fuera estandar" \
    -q "romaneo workflow steps truck arrival weighbridge" \
    -q "romaneo data fields ERP capture" \
    -q "merma calculation formula sequential" \
    -q "grain quality parameters humidity moisture foreign matter" \
    -q "CTG carta de porte electronica romaneo link" \
    -q "WSCPE confirmarDescargaCPE descarga romaneo" \
    -q "grain grading bonificacion rebaja tolerance" \
    -q "romaneo reception document structure fields" \
    -q "acopiador daily operations truck queue reception" \
    -o Docs/RAG_results/spec-11 -l 5
```

### Source Documents (for reference only -- prefer RAG)

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Research 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | Pasos 1-8 reception workflow, merma calculation order, grading |
| Research 2.2 | `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md` | Per-grain grade tables, bonificacion/rebaja values, tolerance tables |
| Research 2.5 | `Docs/Researches/Markdown/2.5 Merma (Grain Loss) Calculations and Tolerance Tables.md` | Sequential merma formula, secado Hf values, zarandeo bands, pseudocode |
| Research 8.3 | `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md` | Romaneo document structure, 5 groups, legal framework, CTG/CPE link |
| Research 8.2 | `Docs/Researches/Markdown/8.2 CTG Document Structure and State Machine.md` | CPE lifecycle phases, confirmarArriboCPE, confirmarDescargaCPE |
| Research 3.1 | `Docs/Researches/Markdown/3.1 Weighbridge Integration Standards.md` | Two-weighing procedure, RS-232/Modbus protocol |

### Blueprint References

| Doc | Path | Relevant Sections |
|-----|------|-------------------|
| Data Model v1.0 | `Docs/Project Blueprint/Data Model & Domain Model.md` | Section 5.3 (Romaneo -- 31 fields, state machine), 5.4 (QualityAnalysis), 5.5 (MermaCalculation -- formula + fields), 5.3.1 (CertificadoDepositoCereal) |
| REST API Design v1.0 | `Docs/Project Blueprint/REST API Design.md` | Section 5 (Romaneo API -- 5.1-5.8), Section 6 (Quality Analysis API -- 6.1-6.4) |
| HLD v1.0 | `Docs/Project Blueprint/High-Level Design (HLD).md` | Section 9.1 (Romaneo Reception Flow -- 10-step sequence diagram) |
| ADR v1.0 | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-014 (MermaTable Scope), ADR-015 (QualityParameter Inline), ADR-016 (WeighbridgeDevice), ADR-017 (Grade Fields on Romaneo), ADR-030 (Store-and-Forward Queue), ADR-031 (Rust/PyO3 Boundary -- merma as CPU-bound), ADR-032 (Weighbridge Architecture), ADR-034 (Provenance Fields), ADR-035 (Measurement-Timestamp Pairing) |
| SRS v1.0 | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | SRS-RE01 through SRS-RE11 (Reception), SRS-CA01 through SRS-CA06 (Quality Analysis), SRS-PF01 (Romaneo save latency) |
| ARCA Guide | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | Section 5 (WSCPE -- confirmarArriboCPE, confirmarDescargaCPE), Section 5.7 (XML field catalog) |

### Critical Domain Facts

#### Romaneo Workflow (10-Step Reception Flow)

The romaneo is the central grain reception document. Per HLD Section 9.1, the
canonical reception flow is:

1. **Arrival** -- truck positions on scale; gross weight reading begins.
2. **Peso bruto captured** -- weighbridge sends reading via RS-232/Modbus.
3. **Calado sampling** -- physical grain probe taken from truck.
4. **QualityAnalysis created** -- 9 quality parameters recorded by lab.
5. **Merma calculation** -- `calculate_merma(quality_params, tables)` via
   Rust/PyO3 FFI.
6. **Grade assignment** -- `grado_asignado`, `bonificacion_rebaja_pct` set.
7. **Unload grain** -- truck dumps cargo; tare weight reading begins.
8. **Tare captured** -- empty truck weighed.
9. **Net weight calculation** -- (bruto - tara) x merma_factor.
10. **Romaneo issuance** -- boleta + silo credit + account credit; CPE
    confirmation queued via ADR-030.

#### Romaneo State Machine

```
PENDIENTE --> EN_PROCESO   : confirmarArriboCPE (ARCA WSCPE async)
EN_PROCESO --> PESADO      : peso_bruto captured
PESADO --> ANALIZADO       : QualityAnalysis completed
ANALIZADO --> CONFORME     : MermaCalculation completed + operator confirms
                             === IMMUTABILITY GATE ===
CONFORME --> CERRADO       : confirmarDescargaCPE + confirmacionDefinitivaCPEAutomotor (async x2)
```

Romaneo is IMMUTABLE after status = CONFORME. Same pattern as `Comprobante` in
AUTORIZADO state. No field changes permitted.

#### Weight Calculation

- **Peso bruto (gross)** -- combined mass of vehicle + fuel + driver + cargo.
- **Tara (tare)** -- mass of empty vehicle after unloading.
- **Peso neto bruto** = peso_bruto - tara (raw physical net weight).
- **Peso neto conforme** = peso_neto_bruto x combined_merma_factor (final
  commercial weight after all deductions).

The Peso Neto Conforme is the legally binding weight credited to the producer's
Cuenta Corriente Granaria and used for the Liquidacion Primaria de Granos
(Research 8.3).

#### Sequential Merma Formula (Circular CAC 10/86, Res. JNG 22027/81)

The merma calculation is applied in strict sequential order. Each step operates
on the result of the previous step, NOT on the original weight:

```
Step 1 -- Zarandeo:    peso_post_zarandeo  = peso_neto_bruto * (1 - %Z / 100)
Step 2 -- Secado:      peso_post_secado    = peso_post_zarandeo * (1 - %S / 100)
Step 3 -- Manipuleo:   peso_post_manipuleo = peso_post_secado * (1 - %M / 100)
Step 4 -- Volatil:     peso_final          = peso_post_manipuleo * (1 - %V / 100)
```

**Zarandeo (%Z):**
- Looked up from MermaTable based on `materias_extranas_pct`.
- Only applied if materias_extranas > tolerance threshold.
- If materias_extranas <= tolerance, %Z = 0.

**Secado (%S):**
```
%S = (Hi - Hf) / (100 - Hf) * 100

where:
  Hi = QualityAnalysis.humedad_pct           (measured sample moisture)
  Hf = GrainType.hf_secado_pct              (REGULATORY FINAL MOISTURE)
```

CRITICAL: Hf = GrainType.hf_secado_pct, NOT humedad_base_pct.
Example for trigo: Hf=13.5%, base=14.0%. Using base instead of Hf yields
approximately 168 kg error per 30-tonne truck.

If Hi <= Hf: secado_pct = 0.00 (no drying deduction applied).

**Manipuleo (%M):**
- Fixed value from `GrainType.manipuleo_fijo_pct`.
- Only applied if secado was applied (if merma_secado > 0).
- Per-grain fixed values: trigo 0.10%, maiz/soja 0.25%, girasol 0.20%, sorgo
  0.25%, cebada forrajera 0.20% (Research 2.1, 2.5).

**Volatil (%V):**
- Fixed value from `GrainType.volatil_fijo_pct`.
- Always applied as the final step.
- Cereals (trigo, maiz, avena, cebada, centeno, sorgo): 0.3% (per ADR-014).
- Oleaginosas (soja, girasol, lino, colza): 0.5%.
- Established by Resolucion ex-JNG 22027/81, Articulo 5 (Research 2.5).
- NOTE: The original JNG resolution groups sorgo with oleaginosas at 0.5%, but
  ADR-014 reclassifies sorgo as a cereal at 0.30% based on current Camara
  Arbitral practice. Follow ADR-014 for implementation.

**Combined merma factor:**
```
total_factor = (1 - %Z/100) * (1 - %S/100) * (1 - %M/100) * (1 - %V/100)
peso_final = peso_neto_bruto * total_factor
total_merma_kg = peso_neto_bruto - peso_final
```

#### Quality Grading System

Two distinct systems (per GrainType.grading_system field):

**GRADO system (cereals: trigo, maiz, sorgo):**

| Grain | Grado 1 | Grado 2 | Grado 3 |
|-------|---------|---------|---------|
| Trigo pan | +1.5% bonificacion | 0% | -1.0% rebaja |
| Maiz | +1.0% bonificacion | 0% | -1.5% rebaja |
| Sorgo | +1.0% bonificacion | 0% | -1.5% rebaja |

Grade assignment is based on comparison of quality parameters against
ToleranceTable thresholds. Grado 1 = all parameters below best thresholds.
Grado 3 = any parameter exceeds worst thresholds. "Fuera de Estandar" = outside
all grade tolerances (Research 2.1, 2.2).

**TOLERANCE system (oleaginosas: soja, girasol):**
- No grades 1/2/3. `grado_asignado = 0` by convention (ADR-017).
- Progressive rebaja per percentage point above tolerance threshold.
- Soja: materias extranas > 1% generates 1% rebaja per point up to 3%, then
  1.5% per point above 3% (Research 2.1).

#### QualityAnalysis Parameters

Per ADR-015, quality parameters are inline fields on QualityAnalysis, NOT a
separate entity. All grains share common parameters; some are grain-specific:

**Common parameters (all grains):**
- `humedad_pct` -- moisture %, input to secado formula (Hi).
- `materias_extranas_pct` -- foreign matter %, drives zarandeo lookup.
- `granos_danados_pct` -- damaged grains %.
- `granos_quebrados_pct` -- broken grains %.
- `granos_ardidos_pct` -- heat-damaged grains %.
- `cuerpos_extranos_pct` -- foreign bodies %.

**Grain-specific parameters (nullable, set based on grain type):**
- `peso_hectolitrico_kg` -- hectolitre weight, cereals only (trigo, maiz, sorgo).
- `proteina_pct` -- protein %, trigo only.
- `granos_verdes_pct` -- green grains %, soja only.

#### CTG / CPE Integration

Each romaneo is linked to a Carta de Porte Electronica (CPE) via `cpe_numero`.
The CTG (Codigo de Trazabilidad de Granos) is assigned by ARCA when
`confirmarArriboCPE` is called.

Per ADR-030, WSCPE calls are asynchronous via store-and-forward queue:
- `confirmarArriboCPE` -- enqueued at PENDIENTE -> EN_PROCESO transition.
  Returns HTTP 202. Romaneo state advances immediately regardless of
  connectivity.
- `confirmarDescargaCPE` / `confirmacionDefinitivaCPEAutomotor` -- enqueued at
  CONFORME -> CERRADO transition. Returns HTTP 202.

Queue ordering is critical: `confirmarArriboCPE` must always precede
`confirmarDescargaCPE` for the same CPE (ARCA Guide Section 5).

NOTE: The actual WSCPE client and PendingOperation model are NOT created in this
spec. Spec-11 only queues the operation conceptually -- the WSCPE integration is
a future spec. The romaneo state transitions proceed regardless of WSCPE
queue state.

#### Tolerance Table Versioning at Romaneo Time

Per Data Model v1.0 Section 5.2: the ToleranceTable and MermaTable version in
effect at `Romaneo.ts_entrada` (local creation timestamp) is used, even if the
romaneo is synced days later.

- `QualityAnalysis.tolerance_table_version` FK stores the exact version used.
- `MermaCalculation.merma_table_version` FK stores the exact MermaTable version.
- A romaneo can NEVER retroactively change its grade due to a table update.

---

## Functional Requirements

### FR-011-001: Romaneo Model (TenantBound, 31 Fields, 7 Groups)

Implement `Romaneo` model inheriting `TenantBoundModel`. 31 fields across 7
groups as specified in Data Model v1.0 Section 5.3:

**Group 1 -- Identification:**

| Field | Django Type | Precision | Null | Default | Description |
|-------|-------------|-----------|------|---------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 | -- |
| `tenant` | ForeignKey(Tenant) PROTECT | -- | No | -- | Owning tenant |
| `romaneo_number` | CharField | max_length=20 | No | -- | Auto-generated sequential per branch |
| `status` | CharField choices | -- | No | PENDIENTE | 6-state: PENDIENTE, EN_PROCESO, PESADO, ANALIZADO, CONFORME, CERRADO |
| `grain_type` | ForeignKey(GrainType) PROTECT | -- | No | -- | Grain species received |
| `campaign` | ForeignKey(CampanaConfig) PROTECT | -- | No | -- | Active campaign at reception |
| `branch` | ForeignKey(Branch) PROTECT | -- | No | -- | Receiving plant |

**Group 2 -- Timestamps (ADR-035):**

| Field | Django Type | Null | Description |
|-------|-------------|------|-------------|
| `ts_entrada` | DateTimeField | No | Arrival timestamp (used for tolerance table version lookup) |
| `ts_pesada_bruta` | DateTimeField | Yes | Gross weight capture timestamp |
| `ts_calado` | DateTimeField | Yes | Sampling timestamp |
| `ts_analisis` | DateTimeField | Yes | Quality analysis completion timestamp |
| `ts_descarga` | DateTimeField | Yes | Unloading/discharge timestamp |
| `ts_tara` | DateTimeField | Yes | Tare weight capture timestamp |

**Group 3 -- Vehicle:**

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `patente_chasis` | CharField | max_length=15 | No | Truck chassis plate |
| `patente_acoplado` | CharField | max_length=15 | Yes | Trailer plate (NULL for single-unit) |
| `driver_name` | CharField | max_length=200 | No | Driver full name |
| `driver_dni` | CharField | max_length=20 | No | Driver DNI |

**Group 4 -- Weight:**

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `peso_bruto_kg` | DecimalField | (17,3) | Yes | Gross weight from weighbridge |
| `tara_kg` | DecimalField | (17,3) | Yes | Tare weight |
| `peso_neto_bruto_kg` | DecimalField | (17,3) | Yes | Computed: peso_bruto - tara |
| `weighbridge_device` | ForeignKey(WeighbridgeDevice) SET_NULL | -- | Yes | Device used for weighing |

NOTE: `weighbridge_device` FK references a WeighbridgeDevice model per ADR-016.
WeighbridgeDevice is NOT created in spec-11 -- use a nullable FK with a string
reference to `"gravitea_acopio.WeighbridgeDevice"` that will be resolved when the
model is created in a later spec. Alternatively, spec-11 may create a minimal
WeighbridgeDevice stub model if the migration requires a concrete target. The
implementation agent should decide based on migration feasibility.

**Group 5 -- CPE / Origin:**

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `cpe_numero` | CharField | max_length=20 | No | Carta de Porte Electronica number |
| `ctg_codigo` | CharField | max_length=20 | Yes | CTG code (assigned by ARCA at confirmarArribo) |
| `producer_cuit` | CharField | max_length=13 | No | Depositing producer CUIT |
| `origin_locality` | CharField | max_length=200 | No | Field/establishment origin locality |

**Group 6 -- Storage Assignment (future spec FKs):**

| Field | Django Type | Null | Description |
|-------|-------------|------|-------------|
| `storage_unit` | ForeignKey(StorageUnit) SET_NULL | Yes | Assigned silo/bin (set at discharge) |
| `grain_lot` | ForeignKey(GrainLot) SET_NULL | Yes | Lot membership (set at CONFORME) |

NOTE: StorageUnit and GrainLot are spec-12 models. Use nullable string-based FK
references (`"gravitea_acopio.StorageUnit"`, `"gravitea_acopio.GrainLot"`) or
omit these FKs and add them in spec-12 via a later migration. The implementation
agent should decide based on migration strategy.

**Group 7 -- Operators & Quality Outcome (ADR-034):**

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `operator_id` | ForeignKey(AppUser) PROTECT | -- | No | Responsible operator |
| `laboratorista_id` | ForeignKey(AppUser) SET_NULL | -- | Yes | Lab analyst (NULL if external) |
| `device_id` | CharField | max_length=100 | Yes | Device that captured this romaneo |
| `grado_asignado` | IntegerField | -- | Yes | Assigned grade (1/2/3 cereals; 0 oleaginosas; NULL before analysis) |
| `bonificacion_rebaja_pct` | DecimalField | (5,2) | Yes | Net price adjustment % |
| `tolerance_table_version` | ForeignKey(ToleranceTable) PROTECT | -- | Yes | Exact tolerance version used |
| `peso_neto_conforme_kg` | DecimalField | (17,3) | Yes | Final net weight after all merma deductions |

Total fields: 31.

### FR-011-002: Romaneo State Machine with Immutability Gate

Implement the 6-state state machine in the `save()` method:

- **Valid transitions**: PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO ->
  CONFORME -> CERRADO. Strictly linear; no skip transitions.
- **Immutability gate at CONFORME**: once status reaches CONFORME, no field
  changes are permitted. `save()` must raise `ValueError` on any field
  modification attempt. Only status transition to CERRADO is allowed.
- `PATCH` requests on CONFORME or CERRADO romaneos must return HTTP 409
  with error type `romaneo_immutable`.
- Out-of-sequence state transitions must return HTTP 409 with error type
  `invalid_state_transition`, including `current_status` and
  `attempted_transition` extension fields.

Follow the same immutability pattern as `StockMovement.save()` in
`backend/apps/inventario/models.py` lines 620-675.

### FR-011-003: QualityAnalysis Model (TenantBound, 1:1 Romaneo)

Implement `QualityAnalysis` as one-to-one satellite of Romaneo, per Data Model
v1.0 Section 5.4. Inherits `TenantBoundModel`.

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 |
| `romaneo` | OneToOneField(Romaneo) CASCADE | -- | No | Parent romaneo |
| `humedad_pct` | DecimalField | (5,2) | No | Hi -- moisture input to secado formula |
| `materias_extranas_pct` | DecimalField | (5,2) | No | Drives zarandeo lookup |
| `granos_danados_pct` | DecimalField | (5,2) | No | Damaged grains % |
| `granos_quebrados_pct` | DecimalField | (5,2) | No | Broken grains % |
| `peso_hectolitrico_kg` | DecimalField | (5,2) | Yes | Hectolitre weight -- cereals only |
| `proteina_pct` | DecimalField | (5,2) | Yes | Protein % -- trigo only |
| `granos_verdes_pct` | DecimalField | (5,2) | Yes | Green grains % -- soja only |
| `granos_ardidos_pct` | DecimalField | (5,2) | No | Heat-damaged grains % |
| `cuerpos_extranos_pct` | DecimalField | (5,2) | No | Foreign bodies % |
| `analysis_timestamp` | DateTimeField | -- | No | When sample was analysed |
| `sample_reference` | CharField | max_length=50 | Yes | Lab sample reference number |

### FR-011-004: MermaCalculation Model (TenantBound, 1:1 Romaneo, Immutable)

Implement `MermaCalculation` as one-to-one immutable satellite of Romaneo, per
Data Model v1.0 Section 5.5. Inherits `TenantBoundModel`. Created once when
Romaneo reaches CONFORME. Never updated.

| Field | Django Type | Precision | Null | Description |
|-------|-------------|-----------|------|-------------|
| `id` | UUIDField PK | -- | No | uuid4 |
| `romaneo` | OneToOneField(Romaneo) CASCADE | -- | No | Parent romaneo |
| `merma_table_version` | ForeignKey(MermaTable) PROTECT | -- | No | Exact MermaTable version used |
| `peso_neto_bruto_input_kg` | DecimalField | (17,3) | No | Input: snapshot of Romaneo.peso_neto_bruto_kg |
| `hi_input_pct` | DecimalField | (5,2) | No | Input: QualityAnalysis.humedad_pct (Hi) |
| `hf_used_pct` | DecimalField | (5,2) | No | Snapshot of GrainType.hf_secado_pct |
| `materias_extranas_input_pct` | DecimalField | (5,2) | No | Input: QualityAnalysis.materias_extranas_pct |
| `zarandeo_pct` | DecimalField | (5,2) | No | Looked up from MermaTable |
| `secado_pct` | DecimalField | (5,2) | No | Computed: 0.00 if Hi <= Hf |
| `manipuleo_pct` | DecimalField | (5,2) | No | Snapshot of GrainType.manipuleo_fijo_pct |
| `volatil_pct` | DecimalField | (5,2) | No | Snapshot of GrainType.volatil_fijo_pct |
| `peso_post_zarandeo_kg` | DecimalField | (17,3) | No | Intermediate: after zarandeo |
| `peso_post_secado_kg` | DecimalField | (17,3) | No | Intermediate: after secado |
| `peso_post_manipuleo_kg` | DecimalField | (17,3) | No | Intermediate: after manipuleo |
| `peso_final_kg` | DecimalField | (17,3) | No | Final conforming weight |
| `total_merma_kg` | DecimalField | (17,3) | No | peso_neto_bruto - peso_final |
| `total_factor_pct` | DecimalField | (7,4) | No | Combined factor |
| `calculated_at` | DateTimeField | -- | No | auto_now_add -- immutable timestamp |
| `calculated_by` | ForeignKey(AppUser) PROTECT | -- | No | Operator who triggered calculation |

Immutability enforcement: `save()` must raise `ValueError` if the record already
exists (no updates allowed). `delete()` must raise `ValueError`.

### FR-011-005: Rust Merma Engine (`merma.rs`)

Create `rust/gravitea-core/src/merma.rs` implementing the sequential merma
calculation in Rust with PyO3 bindings.

**Function signature:**

```rust
#[pyfunction]
fn calculate_merma(input_json: &str) -> PyResult<String>
```

**Input JSON schema:**

```json
{
  "peso_neto_bruto_kg": "30000.000",
  "humedad_pct": "15.2",
  "hf_secado_pct": "13.5",
  "materias_extranas_pct": "1.8",
  "zarandeo_deduction_pct": "1.00",
  "manipuleo_fijo_pct": "0.25",
  "volatil_fijo_pct": "0.30"
}
```

**Output JSON schema:**

```json
{
  "zarandeo_pct": "1.00",
  "secado_pct": "1.97",
  "manipuleo_pct": "0.25",
  "volatil_pct": "0.30",
  "peso_post_zarandeo_kg": "29700.000",
  "peso_post_secado_kg": "29116.301",
  "peso_post_manipuleo_kg": "29043.510",
  "peso_final_kg": "28956.379",
  "total_merma_kg": "1043.621",
  "total_factor_pct": "0.9652"
}
```

**Calculation rules:**
1. Parse all inputs as `Decimal` (via `rust_decimal`).
2. Apply zarandeo: `peso_post_zarandeo = peso_neto_bruto * (1 - zarandeo_pct / 100)`.
3. Compute secado: if `humedad_pct > hf_secado_pct`, then
   `secado_pct = (humedad_pct - hf_secado_pct) / (100 - hf_secado_pct) * 100`;
   else `secado_pct = 0`.
4. Apply secado: `peso_post_secado = peso_post_zarandeo * (1 - secado_pct / 100)`.
5. Apply manipuleo: if `secado_pct > 0`, then
   `peso_post_manipuleo = peso_post_secado * (1 - manipuleo_pct / 100)`;
   else `peso_post_manipuleo = peso_post_secado`.
6. Apply volatil: `peso_final = peso_post_manipuleo * (1 - volatil_pct / 100)`.
7. Compute `total_merma_kg = peso_neto_bruto - peso_final`.
8. Compute `total_factor_pct = peso_final / peso_neto_bruto`.
9. Return all intermediate and final values as string-encoded decimals.

**Error handling:**
- Invalid JSON: return `GraviteaError::InvalidInput`.
- Negative weights: return `GraviteaError::InvalidInput`.
- Percentages outside 0-100: return `GraviteaError::InvalidInput`.

**PyO3 registration in `lib.rs`:**
```rust
#[pymodule_export]
use super::merma::calculate_merma;
```

Follow the existing pattern in `compute.rs` for serde deserialization and
`decimal_utils` for precision handling.

### FR-011-006: Romaneo API Endpoints

Implement REST API endpoints per REST API Design v1.0 Section 5:

**CRUD endpoints:**
- `POST /api/v1/acopio/romaneos/` -- create romaneo in PENDIENTE status.
- `GET /api/v1/acopio/romaneos/` -- list romaneos (page-number paginated,
  tenant-filtered). Support `?ordering=-ts_entrada,romaneo_number`.
- `GET /api/v1/acopio/romaneos/{id}/` -- retrieve single romaneo with nested
  `quality_analysis` and `merma_calculation` when present.
- `PATCH /api/v1/acopio/romaneos/{id}/` -- update editable fields. Guard:
  only PENDIENTE or EN_PROCESO. Return 409 for CONFORME/CERRADO.

**State transition action endpoints (all POST, nested under member):**
- `POST .../romaneos/{id}/confirmar-arribo/` -- PENDIENTE -> EN_PROCESO.
  Returns 202 Accepted (async WSCPE). No request body.
- `POST .../romaneos/{id}/peso-bruto/` -- EN_PROCESO -> PESADO. Body:
  `{ "peso_bruto_kg": "28450.000" }`. Optionally `weighbridge_device`.
- `POST .../romaneos/{id}/analizar/` -- PESADO -> ANALIZADO. Body: inline 9
  quality parameters. Creates QualityAnalysis record.
- `POST .../romaneos/{id}/confirmar/` -- ANALIZADO -> CONFORME. Body:
  `{ "grado_asignado": 1 }`. Triggers Rust merma calculation. Creates
  MermaCalculation record. Sets `peso_neto_conforme_kg`. IMMUTABILITY GATE.
- `POST .../romaneos/{id}/tara/` -- capture tare weight while CONFORME. Body:
  `{ "tara_kg": "12340.000" }`. Computes `peso_neto_bruto_kg`. Prerequisite
  for `cerrar/`.
- `POST .../romaneos/{id}/cerrar/` -- CONFORME -> CERRADO. Requires `tara_kg`
  to be present. Returns 202 Accepted (async WSCPE x 2).

**Preview endpoint (non-persisting):**
- `GET .../romaneos/{id}/merma-preview/` -- returns projected merma deductions
  based on current quality analysis. Does not create or modify any record.
  Available when romaneo is PESADO or ANALIZADO.

### FR-011-007: QualityAnalysis API Endpoints

Implement nested endpoints per REST API Design v1.0 Section 6:

- `POST /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` -- create
  quality analysis record. Guard: romaneo must be EN_PROCESO or PESADO.
- `GET /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` -- retrieve
  quality analysis. Returns 404 if not yet created.
- `PATCH /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` -- update
  quality parameters. Guard: romaneo must be in ANALIZADO state. Returns 409
  if romaneo is CONFORME or CERRADO.

### FR-011-008: Romaneo Number Auto-Generation

Auto-generate `romaneo_number` sequentially per branch. Format:
`ROM-{YYYY}-{NNNNN}` (e.g., "ROM-2026-00142"). The number is assigned by the
server upon romaneo creation.

For offline-created romaneos, a temporary UUID-based placeholder is used
locally. The server replaces it with a sequential number at sync time (per
sync strategy `server_assigns_final` from REST API Design Section 10).

### FR-011-009: Merma Preview Service

Implement a non-persisting merma calculation preview. Uses the same Rust
`calculate_merma()` function but does not create a MermaCalculation record.
Returns the projected deductions in the response body.

Available when romaneo is in PESADO or ANALIZADO state (quality analysis data
must exist). Returns 409 if romaneo has no quality analysis yet.

---

## Non-Functional Requirements

### NF-011-001: All New Models Must Inherit TenantBoundModel

Romaneo, QualityAnalysis, and MermaCalculation all inherit `TenantBoundModel`
and use `TenantBoundManager` as their default manager. They must include
`tenant_id` field and participate in RLS policies.

### NF-011-002: Decimal Precision Convention

All percentage fields: `DecimalField(max_digits=5, decimal_places=2)`.
All weight fields: `DecimalField(max_digits=17, decimal_places=3)`.
Combined factor field: `DecimalField(max_digits=7, decimal_places=4)`.
Per ADR-007.

### NF-011-003: UUID Primary Keys

All models must use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
Per ADR-002.

### NF-011-004: Romaneo Save Latency (SRS-PF01)

Saving a completed romaneo (including merma calculation and stock update) must
complete within 3 seconds under normal load (up to 50 concurrent users per
tenant), including the Rust FFI call. Per SRS-PF01.

### NF-011-005: Test Coverage

Minimum 90% line coverage for all new code. Tests must use pytest with
pytest-django. Follow patterns in `gravitea-testing` skill.

### NF-011-006: Type Hints

All function parameters and return values must have type hints.

### NF-011-007: Rust Merma Correctness

The Rust `calculate_merma()` function must produce results identical to the
Python reference implementation (within `Decimal` precision). Add property-based
tests using `proptest` to verify boundary conditions (zero humidity, zero
foreign matter, maximum values).

### NF-011-008: Immutability Enforcement at DB Level

CONFORME and CERRADO romaneos must be protected by application-level
enforcement in `save()` and `delete()`. Future: PostgreSQL trigger to enforce
immutability at the DB level (defense-in-depth, analogous to Comprobante).

### NF-011-009: Composite Indexes for Query Performance

Add composite indexes for common query patterns:
- Romaneo: `(tenant_id, status, ts_entrada)`, `(tenant_id, branch_id, ts_entrada)`,
  `(tenant_id, campaign_id, grain_type_id)`.
- QualityAnalysis: `(romaneo_id)` (already covered by OneToOne FK).
- MermaCalculation: `(romaneo_id)` (already covered by OneToOne FK).

### NF-011-010: API Response Pagination

Romaneo list endpoints must use page-number pagination. Envelope:
`{ "count": N, "next": "...", "previous": "...", "results": [...] }`.
Per REST API Design Section 2.6.

---

## Key Technical Details

### Models (Django)

| Model | Base Class | Scope | Key Fields |
|-------|------------|-------|------------|
| `Romaneo` | TenantBoundModel | Tenant-scoped | 31 fields across 7 groups; 6-state state machine; immutable after CONFORME |
| `QualityAnalysis` | TenantBoundModel | Tenant-scoped | 9+ quality parameters; 1:1 with Romaneo; grain-specific nullable fields |
| `MermaCalculation` | TenantBoundModel | Tenant-scoped | All merma inputs, intermediates, final weight; 1:1 with Romaneo; fully immutable |

### Rust Module (`merma.rs`)

- **Purpose**: CPU-bound sequential merma calculation per ADR-031.
- **Crate deps**: `rust_decimal`, `rust_decimal_macros`, `serde`, `serde_json`,
  `pyo3`, `thiserror` (all already in `Cargo.toml`).
- **PyO3 interface**: single `#[pyfunction] fn calculate_merma(input_json: &str) -> PyResult<String>`.
- **Python wrapper**: `backend/apps/acopio/services/merma_engine.py` wraps the
  Rust FFI call, handles the MermaTable lookup, and constructs the input JSON.
  Falls back to a pure-Python implementation if the Rust module is not available
  (development/testing convenience).

### API Endpoints

| Method | Path | Description | Status Code |
|--------|------|-------------|-------------|
| `POST` | `/api/v1/acopio/romaneos/` | Create romaneo (PENDIENTE) | 201 |
| `GET` | `/api/v1/acopio/romaneos/` | List romaneos (paginated) | 200 |
| `GET` | `/api/v1/acopio/romaneos/{id}/` | Retrieve with nested QA + MC | 200 |
| `PATCH` | `/api/v1/acopio/romaneos/{id}/` | Update (PENDIENTE/EN_PROCESO only) | 200 / 409 |
| `POST` | `.../romaneos/{id}/confirmar-arribo/` | PENDIENTE -> EN_PROCESO (202 async) | 202 |
| `POST` | `.../romaneos/{id}/peso-bruto/` | EN_PROCESO -> PESADO | 200 |
| `POST` | `.../romaneos/{id}/analizar/` | PESADO -> ANALIZADO | 200 |
| `POST` | `.../romaneos/{id}/confirmar/` | ANALIZADO -> CONFORME (immutability gate) | 200 |
| `POST` | `.../romaneos/{id}/tara/` | Capture tare while CONFORME | 200 |
| `POST` | `.../romaneos/{id}/cerrar/` | CONFORME -> CERRADO (202 async) | 202 |
| `GET` | `.../romaneos/{id}/merma-preview/` | Non-persisting merma projection | 200 |
| `POST` | `.../romaneos/{id}/quality-analysis/` | Create QA satellite | 201 |
| `GET` | `.../romaneos/{id}/quality-analysis/` | Retrieve QA | 200 |
| `PATCH` | `.../romaneos/{id}/quality-analysis/` | Update QA (ANALIZADO only) | 200 / 409 |

### Integration Points

**Upstream (consumed by spec-11):**
- `GrainType` -- FK on Romaneo; `hf_secado_pct`, `manipuleo_fijo_pct`,
  `volatil_fijo_pct` used by merma engine; `grading_system` determines
  grading logic.
- `ToleranceTable` -- FK on Romaneo (`tolerance_table_version`); quality
  parameter thresholds for grade assignment.
- `MermaTable` -- FK on MermaCalculation (`merma_table_version`); zarandeo
  deduction lookup by `materias_extranas_pct`.
- `CampanaConfig` -- FK on Romaneo; active campaign for the tenant.
- `Branch` -- FK on Romaneo; receiving plant (from `apps.core.models`).
- `Tenant` -- FK on Romaneo (via TenantBoundModel).
- `AppUser` -- FK on Romaneo (`operator_id`, `laboratorista_id`).

**Downstream (consumed by future specs):**
- spec-12 (Storage & Position): needs Romaneo to create GrainMovement stock
  entries. StorageUnit and GrainLot FKs on Romaneo populated by spec-12.
- spec-13 (Producer Accounts): needs Romaneo for producer credit/debit entries.
  AccountMovement references Romaneo as deposit source.
- Future WSCPE spec: needs Romaneo state transitions to trigger
  `confirmarArriboCPE` and `confirmarDescargaCPE` via PendingOperation queue.
- Future Liquidacion spec: needs confirmed Romaneo to initiate WSLPG settlement.
- Future CertificadoDepositoCereal: 1:1 with Romaneo, created at reception via
  `cgAutorizarReq`.

### Application Structure (additions to spec-10)

```
backend/apps/acopio/
|-- models/
|   |-- __init__.py                   # Updated: re-export new models
|   |-- romaneo.py                    # NEW: Romaneo (31 fields, state machine)
|   |-- quality_analysis.py           # NEW: QualityAnalysis (1:1 Romaneo)
|   +-- merma_calculation.py          # NEW: MermaCalculation (1:1, immutable)
|-- serializers/
|   |-- __init__.py                   # Updated: re-export new serializers
|   +-- romaneo.py                    # NEW: Romaneo, QA, MC serializers
|-- views/
|   |-- __init__.py                   # Updated: re-export new viewsets
|   +-- romaneo.py                    # NEW: RomaneoViewSet + QA nested viewset
|-- services/
|   +-- merma_engine.py               # NEW: Rust FFI wrapper + Python fallback
|-- urls.py                           # Updated: register romaneo routes
+-- migrations/
    +-- 0002_romaneo_core.py           # NEW: migration for 3 models

rust/gravitea-core/src/
|-- merma.rs                           # NEW: Rust merma engine
+-- lib.rs                             # Updated: register calculate_merma

backend/tests/acopio/
|-- test_romaneo_models.py             # NEW: model + state machine tests
|-- test_romaneo_api.py                # NEW: API endpoint tests
|-- test_quality_analysis.py           # NEW: QA model + API tests
|-- test_merma_calculation.py          # NEW: merma correctness tests
+-- test_merma_rust.py                 # NEW: Rust FFI + property-based tests
```

---

## Acceptance Criteria

### AC-011-001: Romaneo Model Complete

Romaneo model exists with all 31 specified fields across 7 groups, inherits
`TenantBoundModel`, and uses `TenantBoundManager`. Verified by migration and
model unit tests.

### AC-011-002: State Machine Enforced

All 6 state transitions are enforced. Attempting an out-of-sequence transition
raises `ValueError` in the model and returns HTTP 409 in the API. Verified by
unit tests covering all valid and invalid transitions.

### AC-011-003: Immutability Gate at CONFORME

Once a romaneo reaches CONFORME status:
- `PATCH` to the romaneo returns HTTP 409 `romaneo_immutable`.
- `save()` with any field change raises `ValueError`.
- Only status transition to CERRADO is permitted.
Verified by model and API tests.

### AC-011-004: QualityAnalysis 1:1 Satellite

QualityAnalysis is created as a one-to-one satellite of Romaneo. Creating a
second QualityAnalysis for the same romaneo raises `IntegrityError`. All 9+
quality parameters are captured with correct precision. Verified by model tests.

### AC-011-005: MermaCalculation Immutable and Correct

MermaCalculation is created once at CONFORME transition. All input snapshots,
intermediate values, and final weight are stored. Attempting to update or delete
raises `ValueError`. Verified by model tests.

### AC-011-006: Merma Formula Correctness

The sequential merma calculation produces correct results:
- For trigo with Hi=15.2%, Hf=13.5%, ME=1.8%, zarandeo_deduction=1.0%,
  manipuleo=0.10%, volatil=0.30%, peso_neto_bruto=30000 kg: verify each
  intermediate step and final peso_neto_conforme against hand-calculated values.
- For soja with Hi=12.0% (Hi <= Hf): secado_pct = 0.00, manipuleo NOT applied.
- Edge case: all parameters at zero/minimum values.
Verified by Python unit tests and Rust unit tests with identical inputs.

### AC-011-007: Rust-Python Parity

`calculate_merma()` in Rust and the Python fallback produce identical results
(within Decimal precision) for the same inputs. Verified by cross-language
comparison tests with at least 10 test vectors.

### AC-011-008: Hf vs Humedad Base Correctness

The merma engine uses `GrainType.hf_secado_pct` (NOT `humedad_base_pct`) for the
secado formula. A dedicated test asserts that for trigo (Hf=13.5, base=14.0),
using Hf produces a different (correct) result than using base. The error
magnitude for a 30-tonne trigo truck must be documented in the test.

### AC-011-009: Tenant Isolation

Romaneos are tenant-isolated:
- Creating a romaneo sets `tenant_id` from the request.
- Listing romaneos returns only the requesting tenant's records.
- Accessing another tenant's romaneo by ID returns 404.
- QualityAnalysis and MermaCalculation are also tenant-isolated.
Verified by multi-tenant API integration tests.

### AC-011-010: API Endpoints Functional

All 14 API endpoints (4 CRUD + 6 transitions + 1 preview + 3 QA) return correct
responses with correct HTTP status codes. Verified by API integration tests.

### AC-011-011: Romaneo Number Auto-Generated

Creating a romaneo auto-assigns a sequential `romaneo_number` per branch.
Numbers are unique within branch scope. Verified by model test creating
multiple romaneos on the same branch.

### AC-011-012: State Transition Timestamps

Each state transition sets the corresponding timestamp field:
- EN_PROCESO sets `ts_entrada` (if not already set).
- PESADO sets `ts_pesada_bruta`.
- ANALIZADO sets `ts_analisis`.
- CONFORME does not set a new timestamp (uses MermaCalculation.calculated_at).
- CERRADO sets `ts_tara` (from tara capture).
Verified by model tests.

### AC-011-013: Tolerance Table Version Pinned

When a romaneo is graded, the exact ToleranceTable version active at
`Romaneo.ts_entrada` is stored in `tolerance_table_version` FK. A later
ToleranceTable update does not retroactively change the romaneo's grade.
Verified by test creating a romaneo, then updating ToleranceTable, then
verifying the romaneo still references the original version.

### AC-011-014: Test Suite Passing

All tests in `backend/tests/acopio/` pass with `pytest`. Minimum test count:
40 tests covering model creation, state machine transitions (all valid +
invalid), immutability enforcement, merma calculation correctness (multiple
grain types), API endpoints (CRUD + transitions + preview + QA), tenant
isolation, and romaneo number generation.

---

## Dependencies

### Depends On

- **spec-10** (Grain Reference Data) -- GrainType FK on Romaneo; ToleranceTable
  FK on Romaneo (`tolerance_table_version`); MermaTable FK on MermaCalculation
  (`merma_table_version`); CampanaConfig FK on Romaneo. All reference data
  models and seed fixtures must exist.
- **Core infrastructure** -- `TenantBoundModel`, `TenantBoundManager`,
  `AllObjectsManager` from `apps.core`; `Branch` from `apps.core.models`;
  `Tenant` from `apps.core.models.tenant`; `AppUser` from auth user model.
- **Rust infrastructure** -- PyO3/Maturin build pipeline; `rust_decimal`,
  `serde_json`, `thiserror` crates (all present in `Cargo.toml`).

### Blocks

- **spec-12** (Storage & Position) -- needs Romaneo model to create
  GrainMovement stock entries. StorageUnit and GrainLot FKs on Romaneo
  populated by spec-12 migration.
- **spec-13** (Producer Accounts) -- needs Romaneo for producer credit/debit
  entries. AccountMovement references Romaneo as deposit source.

---

## Agent Team Structure

| Agent | Role | Deliverables |
|-------|------|-------------|
| **A1** | Romaneo Model + Migration | `models/romaneo.py` (31 fields, 7 groups, state machine, immutability), `models/quality_analysis.py`, `models/merma_calculation.py`, `models/__init__.py` update, `0002_romaneo_core.py` migration, RLS policies for all 3 models |
| **A2** | Rust Merma Engine | `rust/gravitea-core/src/merma.rs` (calculate_merma function, serde structs, validation), `rust/gravitea-core/src/lib.rs` update (register export), Rust unit tests |
| **A3** | Python Merma Service | `services/merma_engine.py` (Rust FFI wrapper, MermaTable lookup, Python fallback implementation), merma preview logic |
| **A4** | API Layer -- Serializers | `serializers/romaneo.py` (Romaneo, QualityAnalysis, MermaCalculation serializers with nested representations, state transition request serializers) |
| **A5** | API Layer -- Views + URLs | `views/romaneo.py` (RomaneoViewSet with 6 action endpoints, QualityAnalysisViewSet nested, merma preview), `urls.py` update |
| **A6** | Tests | `tests/acopio/test_romaneo_models.py`, `test_romaneo_api.py`, `test_quality_analysis.py`, `test_merma_calculation.py`, `test_merma_rust.py`, `conftest.py` update -- model tests, state machine tests, immutability tests, merma correctness, API integration, tenant isolation |

### Agent Coordination Notes

- A1 must complete models before A3 (service depends on model imports), A4
  (serializers depend on models), and A5 (views depend on serializers + models).
- A2 (Rust) can work in parallel with A1 -- no Django model dependency.
- A3 depends on A1 (model imports) and A2 (Rust FFI). Can write Python fallback
  in parallel with A2, then add Rust wrapper once A2 delivers.
- A4 depends on A1 (models) only.
- A5 depends on A1 (models), A3 (merma service), and A4 (serializers).
- A6 can write test stubs in parallel with all agents, then fill in assertions
  once models/API are available. Rust tests can run independently of Django.

### Execution Order

```
Phase 1 (parallel):    A1 creates models + migration  |  A2 creates Rust merma engine
Phase 2 (parallel):    A3 creates merma service  |  A4 creates serializers
Phase 3 (sequential):  A5 creates views + URLs (depends on A3 + A4)
Phase 4 (sequential):  A6 writes and runs full test suite
Phase 5 (all):         Integration verification -- all agents confirm AC-011-001 through AC-011-014
```

---

## Execution Notes

**Type**: Implementation -- multi-agent execution (A1--A6)

**Base class reference**: `backend/apps/core/models/mixins.py` lines 28-137
(`TenantBoundModel`).

**Immutability pattern reference**: `backend/apps/inventario/models.py` lines
470-675 (`StockMovement`) -- follow the same `save()` override pattern for
Romaneo and MermaCalculation immutability enforcement.

**Rust module pattern reference**: `rust/gravitea-core/src/compute.rs` -- follow
the same serde deserialization, `decimal_utils` usage, and `GraviteaError`
pattern for `merma.rs`.

**Test pattern reference**: `backend/tests/core/test_tenant_isolation.py` --
`TestTenantBoundManager` and `TestTenantBoundModel` classes for tenant isolation
testing patterns.

**Writing persona**: Implementation agents should follow `django-expert` skill
for Django 5.2 patterns, `gravitea-tenant` skill for tenant isolation,
`gravitea-testing` skill for pytest conventions, and `gravitea-auth` skill for
JWT-authenticated API test patterns.

**RAG discipline**: Agents should run the RAG queries listed above before writing
merma calculation logic. Do NOT invent merma formulas or quality parameter values
-- use only values confirmed via RAG from Circular CAC 10/86, Resolucion JNG
22027/81, and SAGPyA/SENASA resolution sources.

**Critical merma formula warning**: The secado formula uses `Hf = GrainType.hf_secado_pct`,
NOT `humedad_base_pct`. Using the wrong value yields approximately 168 kg error
per 30-tonne truck. Every test that calculates merma must explicitly verify that
`hf_secado_pct` (not `humedad_base_pct`) is used.
