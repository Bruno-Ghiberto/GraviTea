# Spec 03: Data Model & Domain Model -- Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0
**Replaces**: Same file, v0.3 (generic retail ERP, partially in Spanish)
**Type**: Blueprint document (technical specification, not code)
**Spec reference**: `specs/003-acopio-data-model/spec.md`

This plan guides the rewrite of the Data Model from a generic horizontal ERP with
Product/Customer/SaleOrder entities to a comprehensive **acopio de granos** domain
model. The output is a ~1200-1800 line Markdown file with Mermaid ERDs, complete
field tables for all 15+ grain domain entities, RLS policy templates, and an
AI-ready data architecture section.

The Data Model is the **SINGLE SOURCE OF TRUTH** for all Django models. Every
implementation spec (spec-09 through spec-12+) derives its model definitions from
this document. It must be implementation-ready: every field table row is directly
translatable to a Django model field definition.

---

## Content Guidelines

### Tone & Voice

- **Technical reference document** — not a narrative, not a design rationale document
- Declarative and prescriptive: "The Romaneo model MUST have...", "This field is immutable after..."
- No hedging: no "TBD", "to be determined", "under review"
- Every field table row is implementation-ready: a developer reading a row can write the Django field definition without further research
- State machines use exact state names that match the Django `choices` values

### Audience

- **Primary**: AI agents running `/speckit.plan` (must produce a correct v1.0 document from this context alone, without querying additional sources for basic domain facts)
- **Secondary**: Lead data architect (review field definitions for completeness and correctness)
- **Tertiary**: Implementation engineers (spec-09 through spec-12+ derive from this document)

### Language

- English is the primary language of the document
- Spanish canonical domain terms used inline throughout: romaneo, merma, campaña, zarandeo, secado, manipuleo, volátil, liquidación, fijación, pizarra, acopiador, balancero, laboratorista, canje, almacenaje
- First occurrence of each Spanish term in each section includes English translation in parentheses
- Module names always in SPANISH CAPS: RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE
- Entity names in English PascalCase (e.g., `GrainType`, `Romaneo`, `MermaCalculation`)

### Level of Detail

- **Field tables**: one row per field with columns: `name | Django field type | max_digits/decimal_places | null | default | help_text`
- **State machines**: Mermaid `stateDiagram-v2` with exact state names and labeled transitions
- **ERDs**: Mermaid `erDiagram` syntax, entities grouped by module comment, FK direction explicit with `||--o{` notation
- **RLS policies**: SQL template with `{table_name}` placeholder and `tenant_id` filter
- **WSLPG mapping table**: columns `XML element | type | max chars/digits | mandatory | Django model field`
- **Merma formula**: every intermediate step field documented alongside the formula

---

## Existing Content: Preserve vs. Replace

### PRESERVE VERBATIM

| v0.3 Section | Action | Notes |
|-------------|--------|-------|
| §2 Ironclad manifesto — Principles 1-4 | **Preserve verbatim** | P4 "Machine Learning First" extended to add grain-specific AI capabilities; principles 1-3 unchanged |
| §3.2 Core/Tenancy entities: Tenant, Branch, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate | **Preserve verbatim** | Infrastructure entities unchanged by acopio pivot |
| §3.3 Auth entities: AppUser, Role | **Preserve verbatim** | Auth model unchanged |
| §3.6 Comprobante, AlicIva, Tributo, CbteAsoc, ArcaCredential, PuntoDeVenta, CAEA | **Preserve verbatim** | ARCA invoicing infrastructure unchanged; ADD LiquidacionPrimaria alongside |
| §3.7 Sync: SyncSession, PendingOperation | **Preserve verbatim** | Sync engine unchanged |

### ADAPT

| v0.3 Section | Action | Notes |
|-------------|--------|-------|
| §1 Metadatos | **Adapt** | Version → 1.0; add "Grain Domain v1.0" subtitle; switch primary language to English; update date |
| §2 P4 Machine Learning First | **Extend** | Add grain domain AI capabilities (quality degradation, silo optimization, fraud detection, price forecasting) as concrete examples; do not replace the principle |
| §3.4 Inventario: Product | **Adapt** | ADD batch_number, lot_number, expiration_date, product_type ENUM (SEED/FERTILIZER/AGROQUIMICO/REPUESTO); StockSnapshot REMOVE (grain position tracked by GrainLot, not periodic snapshot); Supplier/PriceList PRESERVE |
| §3.5 Ventas: Customer, SaleOrder, SaleOrderItem | **Preserve and relabel** | Retain for service invoicing to producers; clarify scope: these are used for FACTURACIÓN service charges, not grain purchases (grain purchases use LiquidacionPrimaria) |

### REPLACE COMPLETELY

| v0.3 Section | Why Replace |
|-------------|-------------|
| §3.1 Global ERD | Generic retail entities → new global ERD showing all grain domain entities + preserved entities |
| §3.4 StockSnapshot | Removed: grain inventory tracked by GrainLot + GrainMovement (continuous grain) and StockMovement (discrete SKU) |
| §3.4 StockMovement (generic) | Kept but reframed as discrete SKU inventory for AGRONOMÍA module; not used for grain |
| §3 entire grain section | Does not exist in v0.3 — new §5 through §8 are fully new content |

### NEW SECTIONS

| New Section | Source | Notes |
|-------------|--------|-------|
| §5 Grain Domain (§5.1–§5.8) | 03-specify.md + RAG queries | GrainType through WeighbridgeCalibration — 15 grain domain entities |
| §6 Producer Accounts (§6.1–§6.3) | 03-specify.md + RAG queries | ProducerAccount, AccountMovement, FijacionRecord |
| §8.2 LiquidacionPrimaria | 03-specify.md FR-010 | Form 1116-C, 5-state machine, single-grain-type constraint |
| §8.3 WSLPG Field Mapping | 03-specify.md FR-019 | XML element → model field table |
| §8.4 CanjeOperation | 03-specify.md FR-024 | Dual document FK pattern |
| §10 Cross-Module Links | 03-specify.md FR-016 | FK table with ON DELETE behavior for all inter-module FKs |
| §11 RLS Policies | 03-specify.md FR-017 | SQL templates for all new grain domain tables |
| §12 AI-Ready Data Architecture | 03-specify.md FR-024 + NF-001 | 4-layer strategy, capability → field mapping, feature store |

---

## Section-by-Section Writing Plan

### Section 1: Document Metadata

**Effort**: Small
**Source**: v0.3 §1 (adapt)
**Action**:
- Copy metadata table structure from v0.3
- Update: Version → 1.0, subtitle → "Grain Domain v1.0", primary language → English, date → current
- Add: Owner "Bruno Ghiberto", Spec Reference → spec-03
- Add row: "Scope" → "Grain domain entities + preserved infrastructure; SINGLE SOURCE OF TRUTH for all Django models"
- Status → "Acopio de Granos Vertical — Active"

**RAG queries**: None needed

---

### Section 2: Design Manifesto "Ironclad"

**Effort**: Small
**Source**: v0.3 §2 (preserve P1–P3 verbatim; extend P4; add P5)
**Action**:
- **P1 — The Ledger Never Lies**: Preserve verbatim. Immutability applies to Romaneo (after CONFORME), AccountMovement, MermaCalculation, and Comprobante.
- **P2 — One Source of Truth**: Preserve verbatim. Single canonical field definition; no duplicated derived fields.
- **P3 — Defense in Depth**: Preserve verbatim. Application layer → PostgreSQL RLS → IDOR validation; every grain domain model inherits TenantBoundModel.
- **P4 — Machine Learning First**: Preserve existing principle body; ADD concrete grain domain AI examples:
  - Quality degradation prediction: QualityAnalysis.humedad + StorageUnit.environment fields over time
  - Silo assignment optimization: GrainLot capacity fields + quality grades
  - Weighbridge fraud detection: Romaneo.patente_chasis + patente_acoplado + peso_bruto + operator_id across multiple romaneos
  - Price forecasting: AccountMovement monetary fields + campaign_code + grain_type
- **P5 — AI-Ready Data Architecture (NEW)**: Every model captures provenance: created_at, updated_at, created_by FK to AppUser, device_id. Every measurement field paired with a timestamp. Derived fields stored alongside inputs (calculation provenance). These fields serve as training features — no post-hoc data reconstruction needed.

**Key constraints**:
- Do NOT remove any existing principle body text
- P5 is new; do not renumber existing principles

---

### Section 3: ERD — Global View

**Effort**: Large
**Source**: v0.3 §3.1 (replace) + all entity definitions from §4–§9
**Action**:
- Write a new global Mermaid `erDiagram` replacing the v0.3 generic ERD
- Group entities into labeled comment blocks: `%% === INFRASTRUCTURE ===`, `%% === GRAIN DOMAIN ===`, `%% === PRODUCER ACCOUNTS ===`, `%% === AGRONOMIA ===`, `%% === FACTURACION ===`, `%% === SYNC ===`
- Show all primary FKs between modules (not all fields — only entity names and key relationships)
- Grain domain entities to include: GrainType, CampanaConfig, ToleranceTable, MermaTable, Romaneo, QualityAnalysis, MermaCalculation, StorageUnit, GrainLot, GrainMovement, WeighbridgeDevice, WeighbridgeCalibration, CPE, ProducerAccount, AccountMovement, FijacionRecord, LiquidacionPrimaria, CanjeOperation
- Infrastructure entities: Tenant, Branch, AppUser, Role, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate
- Facturación entities: Comprobante, AlicIva, Tributo, CbteAsoc, ArcaCredential, PuntoDeVenta, CAEA
- Sync entities: SyncSession, PendingOperation
- Agronomía entities: Product, ProductCategory, Supplier, StockMovement
- **Gate requirement**: diagram must render in GitHub-flavored Markdown without syntax errors
- Followed by a second detailed `erDiagram` for grain domain only (§3.2), showing all field names for the 8 core grain entities: Romaneo, QualityAnalysis, MermaCalculation, GrainLot, StorageUnit, ProducerAccount, AccountMovement, LiquidacionPrimaria

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo data fields capture ERP weight quality" -l 5
```

---

### Section 4: Core Infrastructure

**Effort**: Small
**Source**: v0.3 §3.2 (preserve verbatim) + v0.3 §3.3 (preserve verbatim)
**Action**:
- Copy §3.2 (Tenant, Branch, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate) EXACTLY as-is from v0.3
- Copy §3.3 (AppUser, Role) EXACTLY as-is from v0.3
- Add header note: "Infrastructure entities are unchanged from v0.3. All grain domain models inherit from TenantBoundModel, which in turn inherits these isolation guarantees."
- Add a brief TenantBoundModel abstract base class definition if not present in v0.3 (fields: id UUID PK, tenant FK, created_at, updated_at, created_by FK AppUser)

**Key constraints**:
- No field edits to any infrastructure entity
- Do NOT add grain domain references inside infrastructure entity field tables

---

### Section 5: Grain Domain

**Effort**: Very Large (8 sub-sections, 15 entities)

---

#### §5.1 Reference Data: GrainType, CampanaConfig

**Effort**: Medium
**Source**: 03-specify.md FR-001 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types codes ARCA humidity base quality parameters reference" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "campaign year management grain segregation" -l 5
```

**GrainType field table** — write these fields exactly:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `code` | CharField | max_length=3 | False | — | ARCA grain code (e.g. "23"=trigo, "31"=maiz, "83"=soja) |
| `name` | CharField | max_length=100 | False | — | Common name (e.g. "Trigo Pan") |
| `humedad_base_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Commercialization humidity base (%) — used to determine if secado applies |
| `hf_secado_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Hf value for secado formula %S=(Hi−Hf)/(100−Hf). DISTINCT from humedad_base_pct — using wrong value yields ~168 kg error per 30t truck |
| `manipuleo_fijo_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Fixed manipuleo deduction %. Trigo: 0.10; maiz/soja: 0.25; girasol: 0.20; sorgo: 0.25 |
| `volatil_fijo_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Fixed volátil deduction %. Cereales: 0.30; oleaginosas: 0.50 |
| `grading_system` | CharField | max_length=20, choices: GRADO/TOLERANCE | False | — | GRADO = Grado 1/2/3 (cereals); TOLERANCE = progressive rebaja (oleaginosas) |
| `is_active` | BooleanField | — | False | True | Inactive grain types hidden from UI but preserved for historical data |

**CRITICAL domain fact to inline**:
- trigo: humedad_base=14.0%, Hf=13.5%, manipuleo=0.10%, volátil=0.30% (cereal)
- maiz: humedad_base=14.5%, Hf=13.5%, manipuleo=0.25%, volátil=0.30% (cereal)
- soja: humedad_base=13.5%, Hf=13.0%, manipuleo=0.25%, volátil=0.50% (oleaginosa)
- girasol: humedad_base=11.0%, Hf=10.5%, manipuleo=0.20%, volátil=0.50% (oleaginosa)
- sorgo: humedad_base=15.0%, Hf=13.5%, manipuleo=0.25%, volátil=0.30% (cereal)

**CampanaConfig field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `campaign_code` | CharField | max_length=7 | False | — | Format "YYYY/YY" (e.g. "2024/25"). Starts April, ends March |
| `start_date` | DateField | — | False | — | April 1st of opening year |
| `end_date` | DateField | — | False | — | March 31st of closing year |
| `is_active` | BooleanField | — | False | False | True for current campaign; only one active per tenant |
| `tenant` | FK(Tenant) | ON DELETE PROTECT | False | — | Per-tenant campaign configuration |
| `notes` | TextField | — | True | blank | Admin notes for transition |

**Key constraint**: GrainType is GLOBAL (not per-tenant). No tenant FK on GrainType. CampanaConfig IS per-tenant.

---

#### §5.2 Tolerance & Merma Tables: ToleranceTable, MermaTable

**Effort**: Medium
**Source**: 03-specify.md FR-003 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "tolerance tables bonification rebaja grain" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula sequential zarandeo secado" -l 5
```

**Action**:
- Define ToleranceTable as the versioned quality tolerance thresholds per grain type (materias_extranas %, granos_dañados %, etc.) from Cámara Arbitral de Cereales
- Define MermaTable as the versioned zarandeo deduction schedule: per materias_extranas % range → zarandeo deduction %
- Both tables are GLOBAL (no tenant FK) — regulatory tables from Cámara Arbitral de Cereales de Rosario via SAGPyA/SENASA resolutions
- Both tables use valid_from/valid_to versioning; an old romaneo always references the table version active on its ts_entrada date

**ToleranceTable field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | Grain this tolerance applies to |
| `valid_from` | DateField | — | False | — | Start date of this tolerance version |
| `valid_to` | DateField | — | True | None | NULL = currently active |
| `parameter` | CharField | max_length=50 | False | — | Parameter name (e.g. "materias_extranas", "granos_danados") |
| `tolerance_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Maximum allowed % without grade penalty |
| `grado_base` | IntegerField | — | False | — | Grado 1, 2, or 3 this tolerance corresponds to (cereals only; 0 for oleaginosas) |
| `source_resolution` | CharField | max_length=100 | True | blank | Source regulation (e.g. "Cámara Arbitral Circular 10/86") |

**MermaTable field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | Grain this zarandeo schedule applies to |
| `valid_from` | DateField | — | False | — | Start date of this version |
| `valid_to` | DateField | — | True | None | NULL = currently active |
| `materias_extranas_from_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Lower bound of materias_extranas % range (inclusive) |
| `materias_extranas_to_pct` | DecimalField | max_digits=5, decimal_places=2 | True | None | Upper bound (NULL = unbounded) |
| `zarandeo_deduction_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | % zarandeo deduction applied when materias_extranas falls in this range |

**CRITICAL clarification to inline**: MermaTable covers ONLY zarandeo thresholds. Manipuleo and volátil are FIXED values stored on GrainType, not in MermaTable and not versioned.

**Key constraint**: SC-009 requirement — both tables MUST have valid_from/valid_to. An implementation that omits versioning fails SC-009.

---

#### §5.3 Romaneo

**Effort**: Very Large (≥30 fields, state machine, 6 timestamps)
**Source**: 03-specify.md FR-002 + FR-026 + FR-027 + FR-028 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo data fields capture ERP weight quality" -l 5
```

**Action**:
- Define Romaneo as the atomic grain reception transaction — one Romaneo = one truck arrival
- Romaneo inherits TenantBoundModel
- Immutable after status reaches CONFORME (same pattern as Comprobante)
- Write 6-state machine as Mermaid `stateDiagram-v2` with exact state names and labeled transitions:

```
PENDIENTE → EN_PROCESO: CPE arrival registered (confirmarArriboCPE)
EN_PROCESO → PESADO: peso_bruto + tara captured
PESADO → ANALIZADO: QualityAnalysis linked
ANALIZADO → CONFORME: MermaCalculation completed + operator confirms
CONFORME → CERRADO: CPE definitively closed (confirmacionDefinitivaCPEAutomotor)
```

**Note on CONFORME immutability**: Once status = CONFORME, no fields may be modified. This must be enforced at the model save() override and at the API layer.

**Complete Romaneo field table** (minimum 30 fields — Gate 2 requirement):

Identification group:
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `romaneo_number` | CharField | max_length=20 | False | — | Human-readable number: YYYY-NNNNNN (campaign year + sequential per branch) |
| `status` | CharField | max_length=20, choices | False | PENDIENTE | One of: PENDIENTE, EN_PROCESO, PESADO, ANALIZADO, CONFORME, CERRADO |
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | Grain being received |
| `campaign_code` | FK(CampanaConfig) | ON DELETE PROTECT | False | — | Harvest campaign this reception belongs to |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant receiving the grain |

Timestamp group (6 named timestamps — FR-027):
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `ts_entrada` | DateTimeField | — | False | — | Truck physical arrival at plant gate |
| `ts_pesada_bruta` | DateTimeField | — | True | None | Weight captured from primary scale (peso_bruto) |
| `ts_calado` | DateTimeField | — | True | None | Lab sample collection moment |
| `ts_analisis` | DateTimeField | — | True | None | QualityAnalysis completed |
| `ts_descarga` | DateTimeField | — | True | None | Grain unloaded into silo |
| `ts_tara` | DateTimeField | — | True | None | Tara weight captured (empty truck) |

Vehicle group (FR-026):
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `patente_chasis` | CharField | max_length=15 | False | — | Truck/chassis plate — required for fraud detection baseline |
| `patente_acoplado` | CharField | max_length=15 | True | None | Trailer plate — may be absent for rigid trucks |
| `driver_name` | CharField | max_length=200 | False | — | Driver full name |
| `driver_dni` | CharField | max_length=20 | False | — | Driver national ID |

Weight group:
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `peso_bruto_kg` | DecimalField | max_digits=17, decimal_places=3 | True | None | Gross weight from primary scale (kg). NULL until PESADO state |
| `tara_kg` | DecimalField | max_digits=17, decimal_places=3 | True | None | Tare from secondary scale after unloading (kg) |
| `peso_neto_bruto_kg` | DecimalField | max_digits=17, decimal_places=3 | True | None | Calculated: peso_bruto_kg − tara_kg. Input to merma pipeline |
| `weighbridge_device` | FK(WeighbridgeDevice) | ON DELETE PROTECT | True | None | Scale device that captured weights |

CPE/Origin group:
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `cpe_numero` | CharField | max_length=20 | False | — | Carta de Porte Electrónica number |
| `ctg_codigo` | CharField | max_length=20 | True | None | CTG traceability code assigned by ARCA |
| `producer_cuit` | CharField | max_length=13 | False | — | Producer CUIT (grain depositor) |
| `origin_locality` | CharField | max_length=200 | False | — | Origin location of grain shipment |

Assignment group:
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `storage_unit` | FK(StorageUnit) | ON DELETE PROTECT | True | None | Assigned silo/celda. NULL until silo assignment |
| `grain_lot` | FK(GrainLot) | ON DELETE PROTECT | True | None | Grain lot this romaneo feeds into |

Operator group (FR-028):
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `operator_id` | FK(AppUser) | ON DELETE PROTECT | False | — | Balancero who processed the romaneo |
| `laboratorista_id` | FK(AppUser) | ON DELETE PROTECT | True | None | Lab technician who performed quality analysis |
| `device_id` | CharField | max_length=50 | True | None | Offline device UUID for sync provenance |

Quality outcome (populated after ANALIZADO):
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `grado_asignado` | IntegerField | — | True | None | Assigned grade (1/2/3 for cereals; 0 if no grade system) |
| `bonificacion_rebaja_pct` | DecimalField | max_digits=5, decimal_places=2 | True | None | Net quality adjustment %. Positive = bonificación; negative = rebaja |
| `tolerance_table_version` | FK(ToleranceTable) | ON DELETE PROTECT | True | None | Version of tolerance table used for this grading |

Final weight (populated after CONFORME):
| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `peso_neto_conforme_kg` | DecimalField | max_digits=17, decimal_places=3 | True | None | Final commercial weight after all merma deductions |

**Total fields**: 30+ field rows above. Count before publishing to verify Gate 2 compliance.

---

#### §5.4 Quality Analysis

**Effort**: Medium
**Source**: 03-specify.md FR-012 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity peso hectolitrico" -l 5
```

**Action**:
- Define QualityAnalysis as a 1:1 satellite to Romaneo (one quality record per romaneo)
- QualityParameters are NOT a separate entity — all measurement fields are inline in QualityAnalysis with grain-type conditionality noted as field-level help_text
- QualityAnalysis inherits TenantBoundModel
- Immutable after Romaneo reaches CONFORME

**QualityAnalysis field table** — 9 grain-specific measurement fields (from 03-specify.md §Critical Domain Facts):

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `romaneo` | OneToOneField(Romaneo) | ON DELETE CASCADE | False | — | Parent romaneo record |
| `humedad_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Measured humidity % (Hi). Used as input to secado formula |
| `materias_extranas_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Foreign matter %. Drives zarandeo deduction lookup in MermaTable |
| `granos_danados_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Damaged grains % (all grains) |
| `granos_quebrados_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Broken grains % |
| `peso_hectolitrico_kg` | DecimalField | max_digits=5, decimal_places=2 | True | None | Hectolitric weight (kg/hl). Applicable to cereals only (trigo, maiz, sorgo) |
| `proteina_pct` | DecimalField | max_digits=5, decimal_places=2 | True | None | Protein %. Applicable to trigo only |
| `granos_verdes_pct` | DecimalField | max_digits=5, decimal_places=2 | True | None | Green grains %. Applicable to soja only |
| `granos_ardidos_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Heat-damaged (ardidos) grains % |
| `cuerpos_extranos_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Extraneous matter % (stones, metal, etc.) — subset of materias_extranas |
| `analysis_timestamp` | DateTimeField | — | False | — | When analysis was completed (maps to Romaneo.ts_analisis) |
| `sample_reference` | CharField | max_length=50 | True | None | Lab sample ID or bag number for physical audit trail |

**Key constraint**: All 9 measurement fields are present in every QualityAnalysis record. Grain-type conditionality is captured in help_text ("Applicable to X only") — the database enforces NULL/NOT NULL at application layer, not database constraint, to allow future grain types.

---

#### §5.5 Merma Calculation

**Effort**: Large (full formula provenance, all intermediate steps)
**Source**: 03-specify.md FR-004 + FR-013 + Critical Domain Facts

**Action**:
- Define MermaCalculation as an immutable record created once when Romaneo reaches CONFORME
- It is a separate entity (not embedded in Romaneo) to preserve calculation provenance
- Inherits TenantBoundModel
- NEVER updated after creation

**Sequential merma formula** (must appear verbatim in this section):

```
Step 1: Peso_post_zarandeo  = peso_neto_bruto_kg × (1 − zarandeo_pct/100)
Step 2: Peso_post_secado    = peso_post_zarandeo  × (1 − secado_pct/100)
Step 3: Peso_post_manipuleo = peso_post_secado     × (1 − manipuleo_pct/100)
Step 4: Peso_final          = peso_post_manipuleo  × (1 − volatil_pct/100)

Secado formula: secado_pct = (Hi − Hf) / (100 − Hf) × 100
  where Hi = QualityAnalysis.humedad_pct
        Hf = GrainType.hf_secado_pct  [NOT humedad_base_pct]
If Hi ≤ Hf: secado_pct = 0 (no drying deduction applies)
```

**MermaCalculation field table** — all intermediate steps documented:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `romaneo` | OneToOneField(Romaneo) | ON DELETE CASCADE | False | — | Romaneo this calculation belongs to |
| `merma_table_version` | FK(MermaTable) | ON DELETE PROTECT | False | — | MermaTable version used for zarandeo lookup |
| `peso_neto_bruto_input_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Input value: Romaneo.peso_neto_bruto_kg at time of calculation |
| `hi_input_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Input: QualityAnalysis.humedad_pct |
| `hf_used_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | GrainType.hf_secado_pct at time of calculation (snapshot) |
| `materias_extranas_input_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Input: QualityAnalysis.materias_extranas_pct |
| `zarandeo_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Looked up from MermaTable using materias_extranas_input_pct |
| `secado_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Calculated: (Hi−Hf)/(100−Hf)×100; stored as 0.00 if Hi≤Hf |
| `manipuleo_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Fixed value from GrainType.manipuleo_fijo_pct at time of calculation |
| `volatil_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | Fixed value from GrainType.volatil_fijo_pct at time of calculation |
| `peso_post_zarandeo_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Intermediate: after zarandeo step |
| `peso_post_secado_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Intermediate: after secado step |
| `peso_post_manipuleo_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Intermediate: after manipuleo step |
| `peso_final_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Final peso neto conforme (= Romaneo.peso_neto_conforme_kg) |
| `total_merma_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Derived: peso_neto_bruto_input_kg − peso_final_kg |
| `total_factor_pct` | DecimalField | max_digits=7, decimal_places=4 | False | — | Factor 100 ± adjustments; stored as decimal (e.g. 97.3200 = 97.32%) |
| `calculated_at` | DateTimeField | — | False | auto_now_add | When this immutable record was created |
| `calculated_by` | FK(AppUser) | ON DELETE PROTECT | False | — | User who triggered the calculation |

**Key constraint**: All 4 intermediate `peso_post_*` fields MUST be stored. Storing only the final result fails FR-011 (calculation provenance). The `secado_pct` MUST use `hf_secado_pct` not `humedad_base_pct`.

---

#### §5.6 Storage: StorageUnit, GrainLot, GrainMovement

**Effort**: Medium
**Source**: 03-specify.md FR-001 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "storage unit silo celda capacity tracking" -l 5
```

**StorageUnit field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `name` | CharField | max_length=100 | False | — | Human name (e.g. "Silo 3A", "Celda B") |
| `unit_type` | CharField | max_length=20, choices | False | — | SILO_VERTICAL / CELDA_HORIZONTAL / SECADERO_BIN |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant where this unit is located |
| `capacity_tonnes` | DecimalField | max_digits=12, decimal_places=3 | False | — | Maximum physical capacity (tonnes) |
| `is_active` | BooleanField | — | False | True | Inactive units hidden from assignment UI |
| `current_grain_type` | FK(GrainType) | ON DELETE PROTECT | True | None | Current grain type if unit is in use; NULL if empty |
| `environment_sensor_id` | CharField | max_length=50 | True | None | IoT sensor ID for AI quality monitoring (optional hardware integration) |

**GrainLot field table** (composite: branch + grain_type + campaign + quality grade):

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `lot_code` | CharField | max_length=30 | False | — | Generated: BRANCH-GRAIN-CAMPAIGN-GRADE (e.g. "R01-23-2024/25-G2") |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant owning this lot |
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | Single grain type per lot |
| `campaign` | FK(CampanaConfig) | ON DELETE PROTECT | False | — | Campaign year this lot belongs to |
| `grado` | IntegerField | — | False | — | Quality grade of this lot (1/2/3; 0 for oleaginosas tolerance system) |
| `storage_unit` | FK(StorageUnit) | ON DELETE PROTECT | False | — | Physical storage unit |
| `total_kg` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | Running total (updated on each GrainMovement) |
| `is_own_grain` | BooleanField | — | False | False | True = own grain (balance-sheet asset 1.3.XX); False = third-party (off-balance-sheet 8.1.XX) |

**GrainMovement field table** (append-only — immutable ledger):

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `grain_lot` | FK(GrainLot) | ON DELETE PROTECT | False | — | Lot being moved |
| `movement_type` | CharField | max_length=20, choices | False | — | DEPOSIT / WITHDRAWAL / TRANSFER_IN / TRANSFER_OUT |
| `romaneo` | FK(Romaneo) | ON DELETE PROTECT | True | None | Source romaneo (for DEPOSIT movements) |
| `quantity_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Signed quantity (positive = inflow; negative = outflow) |
| `movement_at` | DateTimeField | — | False | auto_now_add | When movement was recorded |
| `reference_document` | CharField | max_length=50 | True | None | External document reference |

---

#### §5.7 CPE

**Effort**: Small-Medium
**Source**: 03-specify.md FR-021

**Action**:
- Define CPE as a 1:1 companion to Romaneo tracking the Carta de Porte Electrónica lifecycle
- CPE state machine (Mermaid `stateDiagram-v2`): Activa → Arribo (confirmarArriboCPE) → Descargada (descargadoDestinoCPE) → ConfirmadaDefinitiva (confirmacionDefinitivaCPEAutomotor)

**CPE field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `romaneo` | OneToOneField(Romaneo) | ON DELETE CASCADE | False | — | 1:1 bijection: one CPE per romaneo |
| `cpe_numero` | CharField | max_length=20 | False | — | CPE number from ARCA/WSCPE |
| `ctg_codigo` | CharField | max_length=20 | True | None | CTG traceability code (assigned by ARCA at confirmarArribo) |
| `status` | CharField | max_length=25, choices | False | ACTIVA | ACTIVA / ARRIBO_CONFIRMADO / DESCARGADA / CONFIRMADA_DEFINITIVA |
| `validity_expires_at` | DateTimeField | — | False | — | CPE validity window (5-day window from issue) |
| `wscpe_response_payload` | JSONField | — | True | None | Raw ARCA WSCPE response for audit trail |
| `pending_queue_ts` | DateTimeField | — | True | None | If offline, timestamp when operation was enqueued for store-and-forward |

---

#### §5.8 Weighbridge: WeighbridgeDevice, WeighbridgeCalibration

**Effort**: Small
**Source**: 03-specify.md FR-022

**WeighbridgeDevice field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `name` | CharField | max_length=100 | False | — | Human name (e.g. "Báscula Norte") |
| `serial_number` | CharField | max_length=50 | False | — | Manufacturer serial number |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant where device is installed |
| `is_active` | BooleanField | — | False | True | Inactive devices rejected at weight capture |
| `interface_type` | CharField | max_length=20, choices | False | — | RS232 / TCP_IP |
| `connection_address` | CharField | max_length=100 | True | None | IP:port for TCP_IP type; COM port for RS232 |

**WeighbridgeCalibration field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `device` | FK(WeighbridgeDevice) | ON DELETE CASCADE | False | — | Scale this calibration belongs to |
| `calibration_date` | DateField | — | False | — | When calibration was performed |
| `technician` | CharField | max_length=200 | False | — | Calibration technician name or company |
| `certificate_number` | CharField | max_length=50 | False | — | Calibration certificate reference number |
| `reference_weight_kg` | DecimalField | max_digits=12, decimal_places=3 | False | — | Reference weight used in calibration (kg) |
| `deviation_kg` | DecimalField | max_digits=8, decimal_places=3 | False | — | Measured deviation from reference weight |
| `next_due_date` | DateField | — | False | — | Next required calibration date (system alerts when approaching) |

---

### Section 6: Producer Accounts

**Effort**: Large (3 entities, 8 transaction types, dual-ledger pattern)

---

#### §6.1 ProducerAccount

**Effort**: Medium
**Source**: 03-specify.md FR-002 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account balance grain kilogram" -l 5
```

**Action**:
- ProducerAccount is PER-PLANT (per branch), not per-tenant aggregate
- Posición consolidada (cross-plant view) is a DERIVED VIEW, not a stored model
- Dual-ledger: grain sub-ledger (kg per grain type) + monetary sub-ledger (ARS + USD)
- Only own-grain transactions appear in monetary sub-ledger; third-party grain handled separately

**ProducerAccount field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `producer_cuit` | CharField | max_length=13 | False | — | Producer CUIT — the account owner identifier |
| `producer_name` | CharField | max_length=200 | False | — | Producer business/personal name |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant this account belongs to (per-plant source of truth) |
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | One account per grain type per producer per plant |
| `campaign` | FK(CampanaConfig) | ON DELETE PROTECT | False | — | Campaign year (accounts segregated per campaign) |
| `balance_kg` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | Running grain balance (kg). Derived from AccountMovement sum; updated on each movement |
| `balance_ars` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | Monetary balance (Argentine pesos) |
| `balance_usd` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | Monetary balance (USD) |
| `is_a_fijar` | BooleanField | — | False | False | True if producer has unfixed grain (grain with zero monetary crystallization) |

**Key constraint**: Unique constraint on (producer_cuit, branch, grain_type, campaign). One account row per this composite key.

---

#### §6.2 AccountMovement

**Effort**: Medium
**Source**: 03-specify.md FR-002

**Action**:
- AccountMovement is append-only — no UPDATE or DELETE ever
- 8 authoritative transaction types (from PRD v1.0 §4.4 — do not add/remove types):

```
CEG_DEPOSIT          — grain deposit credit (kg positive)
LPG_SALE             — grain purchase by acopiador (kg negative, monetary credit)
FIJACION             — price crystallization event (monetary credit for "a fijar" grain)
RETIRO               — physical grain withdrawal (kg negative)
SERVICE_CHARGE       — service billing debit (almacenaje/secada/zarandeo/paritaria) — monetary negative
CANJE_GRAIN_DEBIT    — grain deducted for canje exchange (kg negative)
CANJE_INPUT_CREDIT   — input credit from canje exchange (monetary credit)
RETENTION_DEDUCTION  — tax retention deducted from settlement (monetary negative)
```

**AccountMovement field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `account` | FK(ProducerAccount) | ON DELETE PROTECT | False | — | Parent account |
| `transaction_type` | CharField | max_length=25, choices | False | — | One of the 8 types above |
| `quantity_kg` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | Grain kg delta (positive=credit, negative=debit; 0 for monetary-only transactions) |
| `amount_ars` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | ARS monetary delta (positive=credit, negative=debit; 0 if no monetary component) |
| `amount_usd` | DecimalField | max_digits=17, decimal_places=3 | False | 0 | USD monetary delta |
| `reference_romaneo` | FK(Romaneo) | ON DELETE PROTECT | True | None | Source romaneo (for CEG_DEPOSIT, CANJE_GRAIN_DEBIT) |
| `reference_liquidacion` | FK(LiquidacionPrimaria) | ON DELETE PROTECT | True | None | Source liquidación (for LPG_SALE, FIJACION, RETENTION_DEDUCTION) |
| `reference_comprobante` | FK(Comprobante) | ON DELETE PROTECT | True | None | Invoice reference (for SERVICE_CHARGE, CANJE_INPUT_CREDIT) |
| `pizarra_price` | DecimalField | max_digits=17, decimal_places=3 | True | None | Pizarra price at time of transaction (for FIJACION, LPG_SALE) |
| `notes` | TextField | — | True | blank | Operator notes |
| `movement_at` | DateTimeField | — | False | auto_now_add | When movement was recorded (immutable) |
| `created_by` | FK(AppUser) | ON DELETE PROTECT | False | — | User who created the movement |

---

#### §6.3 FijacionRecord

**Effort**: Small
**Source**: 03-specify.md FR-023

**Action**:
- FijacionRecord tracks partial fijacion: a producer may fix only a portion of their "a fijar" grain
- Links to the CEG (AccountMovement with type=CEG_DEPOSIT) it partially or fully fixes
- Links to the LPG generated for this fijacion

**FijacionRecord field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `account` | FK(ProducerAccount) | ON DELETE PROTECT | False | — | Producer account being fixed |
| `ceg_movement` | FK(AccountMovement) | ON DELETE PROTECT | False | — | The CEG_DEPOSIT movement being (partially) fixed |
| `liquidacion` | FK(LiquidacionPrimaria) | ON DELETE PROTECT | True | None | LPG generated for this fijacion event |
| `kg_fixed` | DecimalField | max_digits=17, decimal_places=3 | False | — | Kg fixed in this fijacion event |
| `remaining_unfixed_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Kg still unfixed after this event |
| `pizarra_price` | DecimalField | max_digits=17, decimal_places=3 | False | — | Pizarra price at which grain was fixed |
| `fixed_at` | DateTimeField | — | False | auto_now_add | When fijacion was recorded |
| `fixed_by` | FK(AppUser) | ON DELETE PROTECT | False | — | Administrador who processed the fijacion |

---

### Section 7: Agronomia / Discrete Inventory

**Effort**: Small (adapt from v0.3)
**Source**: v0.3 §3.4 (adapt Product entity) + 03-specify.md FR-005

**Action**:
- Adapt Product model: ADD `batch_number`, `lot_number`, `expiration_date`, `product_type`
- Remove StockSnapshot (replaced by GrainLot for grain; discrete inventory only needs StockMovement)
- StockMovement preserved for discrete SKU (AGRONOMÍA insumos); NOT used for grain
- Supplier/PriceList preserved verbatim
- Add note: "AGRONOMÍA uses discrete lot-controlled inventory. Grain position is tracked separately in §5.6 (GrainLot/GrainMovement). Do NOT use StockMovement for grain."

**Product additions** (append to existing field table):

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `batch_number` | CharField | max_length=50 | True | None | Manufacturer batch number (for agroquímicos/fertilizers) |
| `lot_number` | CharField | max_length=50 | True | None | Internal lot identifier |
| `expiration_date` | DateField | — | True | None | Required for agroquímicos and fertilizers; NULL for non-expiring products |
| `product_type` | CharField | max_length=20, choices | False | REPUESTO | SEED / FERTILIZER / AGROQUIMICO / REPUESTO |

---

### Section 8: Facturación

**Effort**: Medium (preserve existing + add LiquidacionPrimaria + WSLPG mapping + CanjeOperation)

#### §8.1 Comprobante and ARCA Infrastructure

**Source**: v0.3 §3.6 (preserve verbatim)
**Action**: Copy Comprobante, AlicIva, Tributo, CbteAsoc, ArcaCredential, PuntoDeVenta, CAEA EXACTLY as-is

---

#### §8.2 LiquidacionPrimaria

**Effort**: Medium
**Source**: 03-specify.md FR-010 + FR-018 + FR-019

**Action**:
- Define LiquidacionPrimaria as the Form 1116-C settlement document
- CRITICAL constraint: one LiquidacionPrimaria covers exactly ONE grain type (codGrano at root level in WSLPG XML schema)
- 5-state machine (Mermaid `stateDiagram-v2`): DRAFT → RETENCION_CALCULADA → SISA_VERIFICADA → WSLPG_PRESENTADA → LIQUIDADA

**LiquidacionPrimaria field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `status` | CharField | max_length=25, choices | False | DRAFT | DRAFT / RETENCION_CALCULADA / SISA_VERIFICADA / WSLPG_PRESENTADA / LIQUIDADA |
| `grain_type` | FK(GrainType) | ON DELETE PROTECT | False | — | Single grain type per liquidación — WSLPG constraint |
| `campaign` | FK(CampanaConfig) | ON DELETE PROTECT | False | — | Campaign year |
| `producer_cuit` | CharField | max_length=13 | False | — | Producer CUIT (grain seller) |
| `branch` | FK(Branch) | ON DELETE PROTECT | False | — | Plant issuing the liquidación |
| `peso_neto_granos_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Net grain weight (kg) — WSLPG: pesoNetoGranos |
| `precio_referencia` | DecimalField | max_digits=17, decimal_places=3 | False | — | Reference price per tonne — WSLPG: precioReferencia |
| `importe_bruto` | DecimalField | max_digits=17, decimal_places=3 | False | — | Gross settlement amount — WSLPG: importeBruto |
| `importe_neto` | DecimalField | max_digits=17, decimal_places=3 | False | — | Net settlement after retentions — WSLPG: importeNeto |
| `alicuota_iva_pct` | DecimalField | max_digits=5, decimal_places=2 | False | — | IVA rate applied (SISA-tier: 5/8/10.5/16) |
| `importe_iva` | DecimalField | max_digits=17, decimal_places=3 | False | — | IVA amount — WSLPG: importeIva |
| `retenciones_json` | JSONField | — | False | list | Array of retention objects: [{codRetencion, importeRetencion}] |
| `nro_orden` | CharField | max_length=20 | True | None | WSLPG nroOrden (assigned after WSLPG_PRESENTADA) |
| `punto_emision` | IntegerField | — | False | — | WSLPG puntoEmision |
| `cod_tipo_operacion` | CharField | max_length=5 | False | — | WSLPG codTipoOperacion |
| `sisa_status` | CharField | max_length=20 | True | None | SISA estado at time of verification (1/2/3/NO_INSCRIPTO) |
| `sisa_checked_at` | DateTimeField | — | True | None | Timestamp of SISA query |
| `wslpg_response_payload` | JSONField | — | True | None | Raw WSLPG response for audit trail |
| `wslpg_presented_at` | DateTimeField | — | True | None | When filed to WSLPG |
| `liquidated_at` | DateTimeField | — | True | None | When LIQUIDADA status was reached |

---

#### §8.3 WSLPG Field Mapping

**Effort**: Medium
**Source**: 03-specify.md FR-019 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSLPG Form 1116-C XML field types lengths" -l 5
```

**Action**:
- Write a table mapping mandatory WSLPG XML elements to LiquidacionPrimaria model fields
- Include all mandatory elements identified in 03-specify.md

| XML Element | Type | Max chars/digits | Mandatory | Django model field |
|-------------|------|-----------------|-----------|-------------------|
| `nroOrden` | String | 20 | Yes (after submit) | `nro_orden` |
| `cuitComprador` | String | 13 | Yes | `branch.tenant.cuit` (resolved at serialization) |
| `codGrano` | String | 3 | Yes | `grain_type.code` |
| `campania` | Integer | 4 | Yes | `campaign.campaign_code` (YYYY parsed) |
| `codGrado` | String | 3 | Yes | from associated AccountMovement/GrainLot |
| `pesoNetoGranos` | Decimal | 17,3 | Yes | `peso_neto_granos_kg` |
| `precioReferencia` | Decimal | 17,3 | Yes | `precio_referencia` |
| `importeBruto` | Decimal | 17,3 | Yes | `importe_bruto` |
| `importeNeto` | Decimal | 17,3 | Yes | `importe_neto` |
| `alicuotaIva` | Decimal | 5,2 | Yes | `alicuota_iva_pct` |
| `importeIva` | Decimal | 17,3 | Yes | `importe_iva` |
| `retenciones` | Array | — | Yes | `retenciones_json` (array: codRetencion, importeRetencion) |
| `codTipoOperacion` | String | 5 | Yes | `cod_tipo_operacion` |
| `puntoEmision` | Integer | 4 | Yes | `punto_emision` |

**Key constraint**: WSLPG XML precision differences (ARCA may require fewer decimal places in specific fields) are handled at the API serialization layer — NOT by storing lower-precision values in the model. Model always stores DECIMAL(17,3).

---

#### §8.4 CanjeOperation

**Effort**: Small
**Source**: 03-specify.md FR-024

**CanjeOperation field table**:

| name | Django field | precision | null | default | help_text |
|------|-------------|-----------|------|---------|-----------|
| `account` | FK(ProducerAccount) | ON DELETE PROTECT | False | — | Producer executing the canje |
| `liquidacion` | FK(LiquidacionPrimaria) | ON DELETE PROTECT | False | — | Grain purchase leg (LPG) |
| `comprobante` | FK(Comprobante) | ON DELETE PROTECT | False | — | Input sale invoice leg |
| `canje_type` | CharField | max_length=10, choices | False | — | TOTAL / PARCIAL |
| `grain_kg` | DecimalField | max_digits=17, decimal_places=3 | False | — | Grain kg exchanged |
| `input_total_ars` | DecimalField | max_digits=17, decimal_places=3 | False | — | Value of inputs exchanged (ARS) |
| `pizarra_at_exchange` | DecimalField | max_digits=17, decimal_places=3 | False | — | Pizarra price used for grain valuation at time of canje |
| `exchanged_at` | DateTimeField | — | False | auto_now_add | When canje was executed |

---

### Section 9: Sync

**Effort**: Small
**Source**: v0.3 §3.7 (preserve verbatim)
**Action**: Copy SyncSession and PendingOperation EXACTLY as-is from v0.3. Add note: "Romaneo and CPE offline operations use the PendingOperation queue. CPE operations (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) are store-and-forward via this queue."

---

### Section 10: Cross-Module Links

**Effort**: Medium
**Source**: 03-specify.md FR-016 (synthesize from all entity FK definitions above)

**Action**:
- Write a comprehensive FK table documenting all inter-module foreign keys
- Specify ON DELETE behavior for every FK
- Group by direction: Grain Domain → Infrastructure, Grain Domain → Facturación, Facturación → Grain Domain, Accounts → Grain Domain

| Source Model | Field | Target Model | ON DELETE | Notes |
|-------------|-------|-------------|-----------|-------|
| Romaneo | grain_type | GrainType | PROTECT | Prevent grain type deletion with existing romaneos |
| Romaneo | campaign_code | CampanaConfig | PROTECT | Prevent campaign deletion with existing romaneos |
| Romaneo | branch | Branch | PROTECT | — |
| Romaneo | storage_unit | StorageUnit | PROTECT | — |
| Romaneo | grain_lot | GrainLot | PROTECT | — |
| Romaneo | operator_id | AppUser | PROTECT | — |
| Romaneo | laboratorista_id | AppUser | PROTECT | — |
| Romaneo | weighbridge_device | WeighbridgeDevice | PROTECT | — |
| QualityAnalysis | romaneo | Romaneo | CASCADE | QA deleted with romaneo (draft only) |
| MermaCalculation | romaneo | Romaneo | CASCADE | Immutable; protected by CONFORME status check |
| MermaCalculation | merma_table_version | MermaTable | PROTECT | — |
| CPE | romaneo | Romaneo | CASCADE | CPE deleted with romaneo (draft only) |
| GrainLot | grain_type | GrainType | PROTECT | — |
| GrainLot | branch | Branch | PROTECT | — |
| GrainLot | campaign | CampanaConfig | PROTECT | — |
| GrainLot | storage_unit | StorageUnit | PROTECT | — |
| GrainMovement | grain_lot | GrainLot | PROTECT | — |
| GrainMovement | romaneo | Romaneo | PROTECT | — |
| ProducerAccount | branch | Branch | PROTECT | — |
| ProducerAccount | grain_type | GrainType | PROTECT | — |
| ProducerAccount | campaign | CampanaConfig | PROTECT | — |
| AccountMovement | account | ProducerAccount | PROTECT | Ledger immutable |
| AccountMovement | reference_romaneo | Romaneo | PROTECT | — |
| AccountMovement | reference_liquidacion | LiquidacionPrimaria | PROTECT | — |
| AccountMovement | reference_comprobante | Comprobante | PROTECT | — |
| FijacionRecord | account | ProducerAccount | PROTECT | — |
| FijacionRecord | ceg_movement | AccountMovement | PROTECT | — |
| FijacionRecord | liquidacion | LiquidacionPrimaria | PROTECT | — |
| LiquidacionPrimaria | grain_type | GrainType | PROTECT | — |
| LiquidacionPrimaria | campaign | CampanaConfig | PROTECT | — |
| LiquidacionPrimaria | branch | Branch | PROTECT | — |
| CanjeOperation | account | ProducerAccount | PROTECT | — |
| CanjeOperation | liquidacion | LiquidacionPrimaria | PROTECT | — |
| CanjeOperation | comprobante | Comprobante | PROTECT | — |
| WeighbridgeCalibration | device | WeighbridgeDevice | CASCADE | Calibration history deleted with device |

---

### Section 11: RLS Policies

**Effort**: Medium
**Source**: 03-specify.md FR-017 + existing v0.3 §5 RLS pattern

**Action**:
- Write SQL RLS policy templates for all new grain domain tables
- Follow the exact template from v0.3 §5 (same pattern)
- Policy type: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`
- Cover these tables: romaneo, quality_analysis, merma_calculation, storage_unit, grain_lot, grain_movement, producer_account, account_movement, fijacion_record, liquidacion_primaria, canje_operation, weighbridge_device, weighbridge_calibration, campana_config, cpe

**RLS template pattern**:

```sql
-- Enable RLS on {table_name}
ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation ON {table_name}
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

**Global tables (NO RLS)**: `grain_type`, `tolerance_table`, `merma_table`
- These are regulatory reference tables with no tenant_id column
- Note explicitly: "GrainType, ToleranceTable, MermaTable are GLOBAL tables — no RLS applied. They are read-only for all tenants."

---

### Section 12: AI-Ready Data Architecture

**Effort**: Medium
**Source**: 03-specify.md NF-001 to NF-006 + RAG

**RAG queries**:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "AI ready data model grain ERP training features" -l 5
```

#### §12.1 4-Layer Data Strategy

**Action**: Write 4 layers:
1. **Operational Layer**: Transactional models (Romaneo, QualityAnalysis, AccountMovement) — optimized for OLTP
2. **Provenance Layer**: All calculated fields stored alongside inputs (MermaCalculation intermediate steps, WeighbridgeCalibration deviation) — enables model explainability
3. **Temporal Layer**: 6 named timestamps per Romaneo, analysis_timestamp on QualityAnalysis, movement_at on AccountMovement — enables time-series training data extraction
4. **Feature Layer**: Named fields serving as ML features, already in normalized form (percentages as DECIMAL(5,2), weights as DECIMAL(17,3)) — no data transformation needed for feature engineering

#### §12.2 AI Capability to Model Field Mapping

**Action**: Write a table mapping ≥4 AI capabilities to specific named model fields (Gate 4 requirement):

| AI Capability | Input Model Fields | Output |
|--------------|-------------------|--------|
| Quality degradation prediction | `QualityAnalysis.humedad_pct` + `QualityAnalysis.granos_ardidos_pct` + `StorageUnit.environment_sensor_id` (linked IoT data) + `ts_analisis` series | Predicted quality grade at future date |
| Silo assignment optimization | `GrainLot.grado` + `StorageUnit.capacity_tonnes` + `GrainLot.total_kg` + `GrainType.code` + `CampanaConfig.campaign_code` | Recommended silo assignment per incoming romaneo |
| Weighbridge fraud detection | `Romaneo.patente_chasis` + `Romaneo.patente_acoplado` + `Romaneo.peso_bruto_kg` + `Romaneo.tara_kg` + `Romaneo.operator_id` across multiple romaneos | Anomaly score: weight pattern deviation, plate reuse frequency |
| Price forecasting | `AccountMovement.pizarra_price` + `AccountMovement.movement_at` + `AccountMovement.grain_type` (via account) + `CampanaConfig.campaign_code` | Predicted pizarra price trajectory |
| Merma anomaly detection | `MermaCalculation.zarandeo_pct` + `MermaCalculation.secado_pct` + `MermaCalculation.hi_input_pct` + `Romaneo.grain_type` + `Romaneo.origin_locality` | Flag unusual merma combinations vs historical baseline |

#### §12.3 Feature Store Readiness

**Action**: Note which fields are already normalized for ML:
- All percentage fields: DECIMAL(5,2) — no normalization needed for logistic/tree models
- All weight fields: DECIMAL(17,3) — scale to [0,1] by dividing by max truck weight (~40,000 kg)
- All timestamp fields: stored as UTC DateTimeField — convert to Unix epoch or cyclical features at training pipeline
- Categorical fields (grain_type.code, status choices): already string-coded for label encoding or one-hot

---

## Research-to-Section Mapping

| Research Doc / RAG Query | Target Sections |
|--------------------------|-----------------|
| "romaneo data fields capture ERP weight quality" | §5.3 (Romaneo field table) |
| "tolerance tables bonification rebaja grain" | §5.2 (ToleranceTable field table) |
| "merma calculation formula sequential zarandeo secado" | §5.2 (MermaTable), §5.5 (MermaCalculation formula) |
| "grain quality parameters humidity peso hectolitrico" | §5.4 (QualityAnalysis field table) |
| "storage unit silo celda capacity tracking" | §5.6 (StorageUnit, GrainLot) |
| "producer current account balance grain kilogram" | §6.1 (ProducerAccount), §6.2 (AccountMovement) |
| "campaign year management grain segregation" | §5.1 (CampanaConfig), §5.6 (GrainLot composite key) |
| "WSLPG Form 1116-C XML field types lengths" | §8.3 (WSLPG field mapping table) |
| "AI ready data model grain ERP training features" | §12 (AI-Ready Data Architecture) |
| v0.3 §3.2 Core/Tenancy | §4 (Core Infrastructure — preserve verbatim) |
| v0.3 §3.3 Auth | §4 (Auth entities — preserve verbatim) |
| v0.3 §3.6 Facturación | §8.1 (Comprobante — preserve verbatim) |
| v0.3 §3.7 Sync | §9 (Sync — preserve verbatim) |
| v0.3 §2 Ironclad Manifesto | §2 (Manifesto — preserve P1-P3, extend P4, add P5) |
| 03-specify.md FR-001 to FR-028 | §5 through §8 (all grain domain entities) |

---

## Checkpoint Gates

### Gate 1 — After §1–§4 (Infrastructure)

- [ ] Version updated to 1.0 in §1 metadata table
- [ ] §2 Ironclad Manifesto: P1, P2, P3 preserved verbatim; P4 extended with grain AI examples; P5 "AI-Ready Data Architecture" added as new principle
- [ ] §3 Global ERD renders in GitHub-flavored Mermaid without syntax errors
- [ ] §3 ERD shows all 15 grain domain entities grouped in a `%% === GRAIN DOMAIN ===` comment block
- [ ] §4 Core Infrastructure: Tenant, Branch, TenantFieldDefinition, TenantModuleConfig, BusinessTemplate, AppUser, Role all present with original field tables unchanged
- [ ] §4 includes TenantBoundModel abstract base class definition (id, tenant FK, created_at, updated_at, created_by)

### Gate 2 — After §5 (Grain Domain)

- [ ] §5.1 GrainType field table contains `humedad_base_pct` AND `hf_secado_pct` as two distinct fields with help_text distinguishing them
- [ ] §5.1 Inline table of per-grain Hf vs humedad_base values (all 5 main grains: trigo, maiz, soja, girasol, sorgo) present in section body
- [ ] §5.2 MermaTable: covers zarandeo thresholds ONLY; explicit note that manipuleo/volátil are in GrainType, not here
- [ ] §5.2 Both ToleranceTable and MermaTable have valid_from/valid_to columns (SC-009)
- [ ] §5.3 Romaneo field count ≥ 30 (count table rows before publishing)
- [ ] §5.3 All 6 named timestamps present: ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara
- [ ] §5.3 Both patente_chasis AND patente_acoplado present as separate fields
- [ ] §5.3 Both operator_id AND laboratorista_id FKs present
- [ ] §5.3 State machine diagram renders with all 6 states and labeled transitions
- [ ] §5.4 QualityAnalysis has all 9 grain-specific measurement fields
- [ ] §5.5 MermaCalculation: all 4 intermediate `peso_post_*` fields present; secado formula shows Hf vs humedad_base distinction
- [ ] §5.5 Secado formula `%S = (Hi − Hf) / (100 − Hf)` appears verbatim with note that Hf ≠ humedad_base
- [ ] §5.6 GrainLot includes `is_own_grain` field (balance-sheet vs off-balance-sheet distinction)
- [ ] §5.7 CPE state machine renders with 4 states and WSCPE method names on transitions
- [ ] §5.8 WeighbridgeDevice separate entity with `branch` FK; WeighbridgeCalibration has `next_due_date`

### Gate 3 — After §6–§9 (Accounts + Inventory + Facturación + Sync)

- [ ] §6.1 ProducerAccount has unique constraint on (producer_cuit, branch, grain_type, campaign)
- [ ] §6.1 Dual-ledger: balance_kg + balance_ars + balance_usd all present
- [ ] §6.2 AccountMovement: all 8 transaction types listed and defined (CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION)
- [ ] §6.2 AccountMovement: append-only note explicit — no UPDATE or DELETE
- [ ] §6.3 FijacionRecord has `remaining_unfixed_kg` field for partial fijacion tracking
- [ ] §7 Product: batch_number, lot_number, expiration_date, product_type all added; StockSnapshot removed; note distinguishing discrete (AGRONOMÍA) vs continuous (grain) inventory explicit
- [ ] §8.1 Comprobante and all ARCA entities preserved verbatim from v0.3
- [ ] §8.2 LiquidacionPrimaria: single-grain-type constraint explicit in notes; 5-state machine renders
- [ ] §8.3 WSLPG mapping table: all mandatory XML elements mapped to model fields with types
- [ ] §8.4 CanjeOperation: both liquidacion FK and comprobante FK present (dual document stream)
- [ ] §9 SyncSession and PendingOperation preserved verbatim

### Gate 4 — Final (§10–§12)

- [ ] SC-010 cross-check: sample 10 field names from ERD (§3) and verify they appear with identical names in field tables (§5–§8) — zero mismatches
- [ ] §10 Cross-module links table covers all inter-module FKs with ON DELETE behavior
- [ ] §11 RLS policy template present for every grain domain table listed in the action items
- [ ] §11 Explicit note: GrainType, ToleranceTable, MermaTable are GLOBAL — no RLS
- [ ] §12.2 maps ≥5 AI capabilities to specific named model fields (≥3 fields per capability)
- [ ] SC-002: count Romaneo fields ≥ 30
- [ ] SC-009: both ToleranceTable and MermaTable have valid_from/valid_to
- [ ] No FLOAT or DOUBLE anywhere in the document — only DECIMAL, CharField, IntegerField, DateTimeField, BooleanField, JSONField, FK
- [ ] All Mermaid diagrams render: global ERD (§3), Romaneo state machine (§5.3), CPE state machine (§5.7), LiquidacionPrimaria state machine (§8.2)

---

## Done Criteria

1. Target document `Docs/Project Blueprint/Data Model & Domain Model.md` updated to v1.0 and saved
2. All 15 grain domain entities have complete field tables with all 6 columns (name, Django field type, precision, null, default, help_text)
3. Romaneo field count ≥ 30 (verified by counting table rows in §5.3)
4. All Mermaid ERD and stateDiagram-v2 diagrams render without syntax errors in GitHub Markdown preview
5. MermaCalculation documents Hf values per grain type in section body with explicit note: "Hf is NOT humedad_base — using the wrong value yields ~168 kg error per 30,000 kg truck"
6. WSLPG field mapping table (§8.3) covers all mandatory XML elements for Form 1116-C with types and Django field names
7. All grain domain entities (romaneo, quality_analysis, merma_calculation, storage_unit, grain_lot, grain_movement, producer_account, account_movement, fijacion_record, liquidacion_primaria, canje_operation, weighbridge_device, weighbridge_calibration, campana_config, cpe) have RLS policy template in §11
8. AI-Ready section (§12) maps ≥5 AI capabilities to ≥3 specific named model fields each
9. SC-010 compliance: zero field-name mismatches between §3 ERD and §5–§8 field tables (manual cross-check performed before marking done)
10. No FLOAT or DOUBLE fields anywhere in the document — only DECIMAL(x,y) or integer types for all numeric fields
11. Both ToleranceTable and MermaTable have valid_from/valid_to columns (SC-009)
12. GrainType, ToleranceTable, and MermaTable are explicitly documented as GLOBAL tables (no tenant_id, no RLS)
