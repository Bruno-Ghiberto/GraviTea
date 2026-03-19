# Spec 03: Data Model & Domain Model -- Implementation Context

## Execution Profile

**Type**: Blueprint document -- single-author writing task
**Target file**: `Docs/Project Blueprint/Data Model & Domain Model.md` (in-place rewrite v0.3 -> v1.0)
**Task source**: `specs/003-acopio-data-model/tasks.md` (47 tasks, 8 phases)
**Primary data source**: `specs/003-acopio-data-model/research.md` (all domain decisions + facts)
**Entity catalog**: `specs/003-acopio-data-model/data-model.md` (39 entities, field counts)
**Navigation guide**: `specs/003-acopio-data-model/quickstart.md`
**No code. No tests. No agent teams. No tmux.**

---

## Context Files -- Read Order

Read these files BEFORE writing. They contain everything needed.

| # | File | Why | Time |
|---|------|-----|------|
| 1 | `specs/003-acopio-data-model/quickstart.md` | Navigation guide, key formulas, key rules, end-to-end scenario | 5 min |
| 2 | `specs/003-acopio-data-model/research.md` | ALL domain decisions (D-001 to D-007), critical domain facts (Hf values, merma formula, 8 tx types, WSLPG fields, grading systems) | 10 min |
| 3 | `specs/003-acopio-data-model/data-model.md` | Complete entity catalog (39 entities, field counts, state machines, module assignments) | 10 min |
| 4 | `specs/003-acopio-data-model/spec.md` | 25 FRs, 10 SCs, 5 User Stories, 5 edge cases, 6 assumptions -- the contract to satisfy | 10 min |
| 5 | `specs/003-acopio-data-model/plan.md` | Execution order, 4 checkpoint gates, 12 done criteria, module assignment for new entities | 5 min |
| 6 | `Docs/Project Blueprint/Data Model & Domain Model.md` (v0.3) | Content to PRESERVE: Ironclad manifesto (P1-P4), Core Infrastructure, Facturacion entities, Sync entities | 10 min |
| 7 | `Docs/Project Blueprint/PRD.md` (v1.0) | Authoritative source for AccountMovement 8 transaction types (PRD v1.0 S4.4) | 5 min |

**Total pre-read**: ~55 minutes. All domain knowledge is in research.md. Do NOT read raw research PDFs.

---

## Writing Rules

### Tone & Voice
- **Technical reference document** -- not a narrative, not a design rationale
- Declarative and prescriptive: "The Romaneo model MUST have...", "This field is immutable after..."
- No hedging: no "TBD", "to be determined", "under review", "potentially"
- Every field table row is implementation-ready: a developer can write the Django field definition from the row alone
- State machines use exact state names that match the Django `choices` values

### Language Protocol
- English is the primary language
- Spanish domain terms are canonical: romaneo, merma, campaña, acopiador, cuenta corriente, liquidación, canje, calado, pizarra, balancero, laboratorista
- First occurrence includes English translation: "romaneo (weighing ticket)"
- After first use, Spanish term alone suffices
- Field names are snake_case English: `peso_bruto_kg`, not `pesoBruto`

### Precision Rules
- ALL weight and monetary fields: `DECIMAL(17,3)` -- zero exceptions (Constitution P-I)
- ALL percentage fields: `DECIMAL(5,2)` -- zero exceptions
- No FLOAT or DOUBLE anywhere in the document
- FK ON DELETE behavior documented for every foreign key
- Every entity section states its inheritance: "Inherits: TenantBoundModel" or "GLOBAL (no tenant FK)"

### Field Table Format
Every entity MUST have a 6-column field table:

```
| Field | Type | Precision | Null | Default | Description |
|-------|------|-----------|------|---------|-------------|
```

Fields from TenantBoundModel (id, tenant, created_at, updated_at, created_by) are NOT repeated in each table -- reference "Inherits: TenantBoundModel" instead.

---

## Design Overrides (spec-03 implementation decisions)

These decisions were made DURING spec-03 and DIFFER from original FR wording.
Implementation specs (09+) MUST follow these overrides, not the original FRs.

### Override 1: Grade Fields on Romaneo (not QualityAnalysis)

FR-003 originally placed grade fields on QualityAnalysis. **Actual placement**:
- `grado_asignado IntegerField null=True` -- on **Romaneo** (Group 7)
- `bonificacion_rebaja_pct DECIMAL(5,2) null=True` -- on **Romaneo** (single signed field: positive = bonificacion, negative = rebaja)
- `tolerance_table_version FK ToleranceTable null=True` -- on **Romaneo**
- For **oleaginosas**: `grado_asignado = 0` (convention for "no integer grade"); rebaja carried in `bonificacion_rebaja_pct`

**Rationale**: Grade is an output of the romaneo process (post-analysis + tolerance-table lookup), not an intermediate QualityAnalysis artefact. Makes immutability cleaner.

### Override 2: Per-Step Merma kg Fields NOT Stored

FR-004 listed zarandeo_kg, secado_kg, manipuleo_kg, volatil_kg as explicit fields. **Not stored.**

**Stored instead**: all four `_pct` inputs + all four `peso_post_*_kg` intermediate weights + `total_merma_kg` + `total_factor_pct`.

**Rationale**: Per-step kg values are derivable: `peso_neto_bruto - peso_post_zarandeo = zarandeo_kg`. Storing both the intermediate weight and the delta is redundant.

### Override 3: ON DELETE CASCADE for 1:1 Satellites (D-007)

Constitution P-I default is RESTRICT. Documented exceptions:
- **CASCADE**: CPE -> Romaneo, QualityAnalysis -> Romaneo, MermaCalculation -> Romaneo (1:1 satellites with no meaning without parent)
- **SET_NULL**: Romaneo.weighbridge_device, Romaneo.storage_unit, Romaneo.grain_lot (nullable assignment fields)

---

## Section-by-Section Drafting Instructions

Write in this dependency order -- NOT document section order:

```
Foundation: S1 -> S2 -> S4 -> S9 -> S7 -> S8.1
Grain domain: S5.1 -> S5.2 -> S5.3 -> S5.4 -> S5.5 -> S5.6 -> S5.7 -> S5.8
Accounts: S6.1 -> S6.2 -> S6.3
Factura extensions: S8.2 -> S8.3 -> S8.4
ERDs: S3 (requires all entities defined first)
Cross-cutting: S10 -> S11 -> S12
```

---

### PHASE 1: SETUP

**Tasks**: T001-T004

1. Read the v0.3 document to understand structure and content to preserve
2. Read research.md to internalize all domain decisions (D-001 to D-007) and critical facts
3. Read data-model.md for the complete 39-entity catalog
4. Replace the document skeleton: add all 12 section headings (S1-S12) preserving v0.3 content in-place before overwriting in later tasks

---

### PHASE 2: FOUNDATION (preserve/adapt from v0.3)

**Tasks**: T005-T010 | **Gate**: Foundation complete -- all preserved content in place

**S1 Metadata** (T005):
- Version -> 1.0 | Title -> "Data Model & Domain Model -- Grain Domain v1.0"
- Date -> 2026-03-16 | Owner -> Bruno Ghiberto
- Status -> "Acopio de Granos Vertical -- Active"
- Add Scope row: "SINGLE SOURCE OF TRUTH for all Django models; grain domain v1.0"

**S2 Design Manifesto "Ironclad"** (T006):
- Preserve P1-P4 verbatim from v0.3
- Extend P4 "Machine Learning First" with grain-specific AI examples
- Add NEW **P5 "AI-Ready Data Architecture"**: provenance fields (created_at, updated_at, created_by, device_id) + measurement fields paired with timestamps + derived fields stored alongside inputs

**S4 Core Infrastructure** (T007):
- Copy verbatim from v0.3: Tenant (8), Branch (7), TenantFieldDefinition (8), TenantModuleConfig (5), BusinessTemplate (5), AppUser (9), Role (5)
- ADD: TenantBoundModel abstract base class definition (id, tenant FK, created_at, updated_at, created_by FK)

**S9 Sync** (T008):
- Copy verbatim from v0.3: SyncSession (8), PendingOperation (7) -- unchanged

**S7 Agronomia / Discrete Inventory** (T009):
- S7.1 Product: copy v0.3 fields + ADD batch_number, lot_number, expiration_date, product_type (SEED/FERTILIZER/AGROQUIMICO/REPUESTO)
- REMOVE StockSnapshot (deprecated)
- S7.2 StockMovement: copy verbatim from v0.3
- Preserve Supplier, ProductCategory, PriceList

**S8.1 Facturacion Preserved** (T010):
- Copy verbatim: Comprobante (20+ fields), AlicIva, Tributo, CbteAsoc, ArcaCredential, PuntoDeVenta, CAEA
- Add note: "LiquidacionPrimaria (Form 1116-C) defined in S8.2"

**Checkpoint (Gate 1)**: Foundation sections complete. All preserved content in place. Grain domain sections ready to write.

---

### PHASE 3: GRAIN DOMAIN (the bulk -- S5, S6, S8.2-S8.4)

**Tasks**: T011-T029 | **Gate**: Gate 2 -- Romaneo >= 30 fields, formula uses Hf

#### S5.1 Reference Data

**GrainType** (T011) -- 8 fields, GLOBAL (no tenant FK):
- code, name, humedad_base_pct, hf_secado_pct, manipuleo_fijo_pct, volatil_fijo_pct, grading_system (GRADO/TOLERANCE), is_active
- MUST include reference data table with ALL 5 grains:
  | Grain | Hf | Base | Manipuleo | Volatil | Grading |
  |-------|-----|------|-----------|---------|---------|
  | Trigo | 13.5% | 14.0% | 0.10% | 0.30% | GRADO |
  | Maiz | 13.5% | 14.5% | 0.25% | 0.30% | GRADO |
  | Soja | 13.0% | 13.5% | 0.25% | 0.50% | TOLERANCE |
  | Girasol | 10.5% | 11.0% | 0.20% | 0.50% | TOLERANCE |
  | Sorgo | 13.5% | 15.0% | 0.25% | 0.30% | GRADO |
- CRITICAL note: "Hf != humedad_base_pct -- using wrong value yields ~168 kg error per 30t truck"

**CampanaConfig** (T012) -- 6 fields, per-tenant:
- campaign_code (CharField max_length=7, format "YYYY/YY"), start_date, end_date, is_active (default=False), tenant FK, notes
- Constraint: only 1 active per tenant

#### S5.2 Tolerance & Merma Tables

**ToleranceTable** (T013) -- 7 fields, GLOBAL:
- grain_type FK, valid_from, valid_to (null = currently active), parameter, tolerance_pct, grado_base, source_resolution
- Include grading note: cereals (Grado 1 bonif 1.0-1.5%, Grado 2 no adj, Grado 3 rebaja 1.0-1.5%) vs oleaginosas (progressive rebaja per point)

**MermaTable** (T014) -- 6 fields, GLOBAL:
- grain_type FK, valid_from, valid_to (null), materias_extranas_from_pct, materias_extranas_to_pct (null), zarandeo_deduction_pct
- CRITICAL inline note: "MermaTable covers ONLY zarandeo thresholds. Manipuleo and volatil are FIXED values stored on GrainType (not versioned, not in MermaTable)"

#### S5.3 Romaneo

**Romaneo field table** (T015) -- MINIMUM 30 fields across 9 groups:

1. **Identification** (5): romaneo_number, status (PENDIENTE/EN_PROCESO/PESADO/ANALIZADO/CONFORME/CERRADO), grain_type FK, campaign_code FK, branch FK
2. **Timestamps** (6): ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara
3. **Vehicle** (4): patente_chasis, patente_acoplado, driver_name, driver_dni
4. **Weight** (4): peso_bruto_kg, tara_kg, peso_neto_bruto_kg, weighbridge_device FK
5. **CPE/Origin** (4): cpe_numero, ctg_codigo, producer_cuit, origin_locality
6. **Assignment** (2): storage_unit FK null, grain_lot FK null
7. **Operator** (3): operator_id FK, laboratorista_id FK null, device_id null
8. **Quality outcome** (3): grado_asignado, bonificacion_rebaja_pct, tolerance_table_version FK
9. **Final** (1): peso_neto_conforme_kg

Immutability note: "IMMUTABLE after status=CONFORME -- no field changes permitted (same pattern as Comprobante AUTORIZADO)"

**Romaneo state machine** (T016) -- Mermaid `stateDiagram-v2`:
```
PENDIENTE -> EN_PROCESO: CPE arrival confirmed
EN_PROCESO -> PESADO: peso_bruto + tara captured
PESADO -> ANALIZADO: QualityAnalysis completed
ANALIZADO -> CONFORME: MermaCalculation + operator confirms [IMMUTABILITY GATE]
CONFORME -> CERRADO: CPE definitively closed + ts_tara
```

#### S5.4 QualityAnalysis

**QualityAnalysis** (T017) -- 12 fields:
- romaneo (OneToOneField CASCADE), humedad_pct ("Hi -- input to secado formula"), materias_extranas_pct, granos_danados_pct, granos_quebrados_pct
- peso_hectolitrico_kg (null, "cereals only"), proteina_pct (null, "trigo only"), granos_verdes_pct (null, "soja only")
- granos_ardidos_pct, cuerpos_extranos_pct, analysis_timestamp, sample_reference (null)
- Note: "QualityParameter is NOT a separate entity (D-002)"

#### S5.5 MermaCalculation

**MermaCalculation** (T018) -- 17 fields + formula block:

Write the formula block FIRST:
```
%S = (Hi - Hf) / (100 - Hf) x 100   [if Hi > Hf; else secado_pct = 0]
Step 1: post_zarandeo  = neto_bruto    x (1 - zarandeo_pct/100)
Step 2: post_secado    = post_zarandeo x (1 - secado_pct/100)
Step 3: post_manipuleo = post_secado   x (1 - manipuleo_pct/100)
Step 4: peso_final     = post_manipuleo x (1 - volatil_pct/100)
```

CRITICAL: "Hf = GrainType.hf_secado_pct (NOT humedad_base_pct)"

17 fields: romaneo (OneToOneField CASCADE), merma_table_version FK, peso_neto_bruto_input_kg, hi_input_pct, hf_used_pct ("snapshot of GrainType.hf_secado_pct at calculation time"), materias_extranas_input_pct, zarandeo_pct, secado_pct ("0.00 if Hi <= Hf"), manipuleo_pct, volatil_pct, peso_post_zarandeo_kg, peso_post_secado_kg, peso_post_manipuleo_kg, peso_final_kg, total_merma_kg, total_factor_pct DECIMAL(7,4), calculated_at (auto_now_add), calculated_by FK

Note: "IMMUTABLE -- created once when Romaneo reaches CONFORME; never updated"

#### S5.6 Storage (3 entities)

**StorageUnit** (T019) -- 7 fields: name, unit_type (SILO_VERTICAL/CELDA_HORIZONTAL/SECADERO_BIN), branch FK, capacity_tonnes, is_active, current_grain_type FK null, environment_sensor_id null

**GrainLot** (T020) -- 8 fields: lot_code, branch FK, grain_type FK, campaign FK, grado, storage_unit FK, total_kg, is_own_grain (True=balance-sheet 1.3.XX, False=off-balance-sheet 8.1.XX)
- Composite key: (branch + grain_type + campaign + grado) per RG 3593

**GrainMovement** (T021) -- 6 fields: grain_lot FK, movement_type (DEPOSIT/WITHDRAWAL/TRANSFER_IN/TRANSFER_OUT), romaneo FK null, quantity_kg (positive=inflow, negative=outflow), movement_at (auto_now_add), reference_document null
- Note: "Append-only LEDGER -- no UPDATE/DELETE"

Add section header note: "GRAIN INVENTORY (Continuous): measured in kg, derived from romaneo reception events, NOT counted by units. See S7 for discrete inventory."

#### S5.7 CPE

**CPE** (T022) -- 7 fields + state machine:
- romaneo (OneToOneField CASCADE), cpe_numero, ctg_codigo null, status (ACTIVA/ARRIBO_CONFIRMADO/DESCARGADA/CONFIRMADA_DEFINITIVA), validity_expires_at ("5-day window"), wscpe_response_payload JSONField null, pending_queue_ts null
- State machine: Activa -> confirmarArriboCPE -> Arribo_Confirmado -> descargadoDestinoCPE -> Descargada -> confirmacionDefinitivaCPEAutomotor -> Confirmada_Definitiva

#### S5.8 Weighbridge (2 entities)

**WeighbridgeDevice** (T023) -- 6 fields: name, serial_number, branch FK, is_active, interface_type (RS232/TCP_IP), connection_address null

**WeighbridgeCalibration** (T024) -- 7 fields: device FK (CASCADE), calibration_date, technician, certificate_number, reference_weight_kg, deviation_kg, next_due_date

#### S6 Producer Accounts (3 entities)

**ProducerAccount** (T025) -- 8 fields + dual-ledger architecture note:
- producer_cuit, branch FK, grain_type FK, campaign FK, grain_balance_kg (default=0), ars_balance (default=0), usd_balance (default=0), is_active
- Note: "Posicion consolidada (cross-plant view) is a DERIVED VIEW -- NOT a stored entity (D-005)"

**AccountMovement** (T026) -- 10 fields + 8 transaction types (authoritative per PRD v1.0 S4.4):
1. CEG_DEPOSIT | 2. LPG_SALE | 3. FIJACION | 4. RETIRO | 5. SERVICE_CHARGE | 6. CANJE_GRAIN_DEBIT | 7. CANJE_INPUT_CREDIT | 8. RETENTION_DEDUCTION
- Fields: producer_account FK, movement_type, romaneo FK null, liquidacion FK null, quantity_kg null, ars_amount null, usd_amount null, movement_at (auto_now_add), reference_document null, notes null
- Note: "Append-only LEDGER -- no UPDATE/DELETE"

**FijacionRecord** (T027) -- 7 fields:
- deposit_movement FK (PROTECT), liquidacion FK (PROTECT), pizarra_price, kg_fixed, remaining_unfixed_kg ("updated on each partial; reaches 0 when fully fixed"), fixed_at, fixed_by FK
- Note: "One CEG can generate multiple FijacionRecords over time (partial fijacion)"

#### S8.2 LiquidacionPrimaria

**LiquidacionPrimaria** (T028) -- 18 fields + state machine:
- CRITICAL constraint: "1 LiquidacionPrimaria = 1 grain type only (WSLPG schema constraint -- codGrano at root level)"
- Key fields: romaneo FK, grain_type FK, campaign FK, producer_account FK, status (DRAFT/RETENCION_CALCULADA/SISA_VERIFICADA/WSLPG_PRESENTADA/LIQUIDADA), tipo_operacion (COMPRA_VENTA/CONSIGNACION/CANJE), punto_emision, numero_orden, fecha_emision, peso_neto_granos_kg, precio_referencia, importe_bruto, importe_neto, alicuota_iva ("10.5% for grain"), importe_iva, retenciones JSONField, wslpg_response JSONField null, wslpg_submitted_at null

#### S8.3 WSLPG Field Mapping Table

Write mapping table with columns: XML Element | Data Type | Length/Precision | Requirement | Django Model Field

Minimum 17 XML elements including: tipo_reg, puntoEmision, numeroOrden, fechaEmision, codTipoOperacion, cuitComprador, codGrano, campania, codGrado, pesoNetoGranos, precioReferencia, importeBruto, importeNeto, alicuotaIva, importeIva, retenciones array

CRITICAL note: "codGrano is at the XML root level -- cannot cover multiple grain types per Form 1116-C"

#### S8.4 CanjeOperation

**CanjeOperation** (T029) -- 8 fields:
- lpg FK (PROTECT), comprobante FK (PROTECT), canje_type (TOTAL/PARCIAL), producer_account FK, grain_kg, input_amount_ars, net_balance_ars, created_at
- Note: "CanjeOperation is the convergence point of both inventory systems: grain (LPG at IVA 10.5%) + agronomia inputs (Comprobante at IVA 21%)"

**Checkpoint (Gate 2)**: Romaneo >= 30 fields (count rows). MermaCalculation uses `hf_secado_pct`. ToleranceTable + MermaTable have valid_from/valid_to. All 15 grain domain entities have 6-column field tables.

---

### PHASE 4: ERD DIAGRAMS (S3 -- requires all entities)

**Tasks**: T030-T033 | **Gate**: All Mermaid diagrams render without errors

**S3.1 Global ERD** (T030) -- Mermaid `erDiagram`:
- Group all entities under module comment blocks: INFRASTRUCTURE, GRAIN DOMAIN, PRODUCER ACCOUNTS, AGRONOMIA, FACTURACION, SYNC
- 30+ entities with primary relationships only (not all fields)
- Use `||--o{` for 1:N, `||--||` for 1:1

**S3.2 Grain Domain Detail ERD** (T031) -- Mermaid `erDiagram`:
- Include ALL fields for 8 core entities: Romaneo, QualityAnalysis, MermaCalculation, GrainLot, StorageUnit, ProducerAccount, AccountMovement, LiquidacionPrimaria
- Show field names with types, FK directions labeled

**S10 Cross-Module Links** (T032) -- FK table:
- Columns: Source Entity | Target Entity | FK Field | ON DELETE | Purpose
- Minimum 13 rows covering all cross-module FKs
- EVERY FK must document ON DELETE behavior (RESTRICT, CASCADE, or SET NULL)

**Syntax verification** (T033): Review all `erDiagram` and `stateDiagram-v2` blocks for unclosed brackets, invalid notation, reserved word conflicts.

---

### PHASE 5-7: ARCHITECTURE NOTES, VERSIONING, AI-READY

**S5.6 + S7 Dual Inventory Notes** (T034-T036):
- S5.6 header: "GRAIN INVENTORY (Continuous): measured in kg, derived from romaneo. Does NOT use StockMovement."
- S7 header: "DISCRETE INVENTORY (Agronomia): counted in units. Uses StockMovement. NOT used for grain."
- S8.4 convergence: "CanjeOperation bridges both inventory systems"

**S5.2 Versioning Behavior** (T037):
- "Version in effect at Romaneo.ts_entrada is used -- even if synced days later"
- "A romaneo can never retroactively change its grade due to a table update"

**S12 AI-Ready Data Architecture** (T039-T041):
- S12.1 Four-Layer Data Strategy: Operational, Behavioral, Quality History, Physical State
- S12.2 AI Capability -> Model Field Mapping: minimum 4 capabilities with >= 3 fields each:
  1. Quality Degradation Prediction -> QualityAnalysis fields + StorageUnit sensor
  2. Silo Assignment Optimization -> GrainLot + StorageUnit capacity + quality grades
  3. Weighbridge Fraud Detection -> Romaneo patente/peso/operator patterns
  4. Price Forecasting -> AccountMovement prices + FijacionRecord.pizarra_price
  5. Predictive Aeration Scheduling (optional) -> StorageUnit sensor + GrainLot + QualityAnalysis
- S12.3 Feature Store Readiness: provenance fields, paired timestamps, derived fields stored alongside inputs

---

### PHASE 8: POLISH & VERIFICATION

**Tasks**: T042-T047

**S11 RLS Policies** (T042):
- SQL template for each table: `CREATE POLICY tenant_isolation ON {table} USING (tenant_id = current_setting('app.current_tenant_id')::uuid);`
- GLOBAL tables (no RLS): grain_type, tolerance_table, merma_table
- All other grain domain tables: RLS enabled

**SC-010 Cross-Check** (T043): Verify 10 field names match between ERD (S3) and field tables (S5-S8):
- Romaneo.patente_chasis, Romaneo.ts_entrada, QualityAnalysis.humedad_pct, MermaCalculation.hf_used_pct, GrainLot.is_own_grain, ProducerAccount.grain_balance_kg, AccountMovement.movement_type, LiquidacionPrimaria.peso_neto_granos_kg, WeighbridgeCalibration.next_due_date, CanjeOperation.canje_type

**SC-002 Verify** (T044): Count Romaneo field table rows -- confirm >= 30.

**SC-004 Verify** (T045): Every grain domain entity has "Inherits: TenantBoundModel" (exception: GrainType, ToleranceTable, MermaTable = GLOBAL).

**Terminology Consistency** (T046): Verify exact TextChoices values across state machines and field tables:
- Romaneo: PENDIENTE / EN_PROCESO / PESADO / ANALIZADO / CONFORME / CERRADO
- LiquidacionPrimaria: DRAFT / RETENCION_CALCULADA / SISA_VERIFICADA / WSLPG_PRESENTADA / LIQUIDADA
- CPE: ACTIVA / ARRIBO_CONFIRMADO / DESCARGADA / CONFIRMADA_DEFINITIVA
- AccountMovement: CEG_DEPOSIT / LPG_SALE / FIJACION / RETIRO / SERVICE_CHARGE / CANJE_GRAIN_DEBIT / CANJE_INPUT_CREDIT / RETENTION_DEDUCTION

**Final Version Stamp** (T047): Confirm Metadata version=1.0, run Done Criteria checklist.

---

## RAG Query Protocol

**Primary rule**: research.md has ALL verified domain facts. Do NOT re-query unless you find a specific claim you need to verify or expand.

**If additional depth needed during writing**:
```bash
# Single query
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5

# Recommended supplementary queries (only if research.md is insufficient):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo data fields capture ERP weight quality" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula sequential zarandeo secado" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity peso hectolitrico" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account balance grain kilogram" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSLPG Form 1116-C XML field types lengths" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "storage unit silo celda capacity tracking" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "campaign year management grain segregation" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "AI ready data model grain ERP training features" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "tolerance tables bonification rebaja grain" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "chart of accounts acopio inventory valuation own grain third party" -l 5
```

**NEVER** read full research PDFs. All domain knowledge via RAG or research.md inline data.

---

## Critical Pitfalls to Avoid

1. **Hf vs Humedad Base**: The secado formula `%S = (Hi - Hf) / (100 - Hf)` uses **Hf** (`GrainType.hf_secado_pct`), NOT humedad_base. Using the wrong value yields ~168 kg error on a 30,000 kg truck. Both values MUST appear in GrainType field table with explicit distinction.

2. **Grade fields placement**: Grade outcome fields (`grado_asignado`, `bonificacion_rebaja_pct`, `tolerance_table_version`) go on **Romaneo**, NOT QualityAnalysis. See Design Override 1.

3. **Per-step kg not stored**: Do NOT add `zarandeo_kg`, `secado_kg`, `manipuleo_kg`, `volatil_kg` as fields. Store `peso_post_*_kg` intermediates instead. See Design Override 2.

4. **MermaTable scope**: MermaTable holds ONLY zarandeo thresholds. Manipuleo and volatil constants live on GrainType. Do NOT put all four parameters in MermaTable.

5. **FLOAT/DOUBLE prohibition**: Zero tolerance. Every numeric field is DECIMAL with explicit precision. `total_factor_pct` uses DECIMAL(7,4); all others use (17,3) or (5,2).

6. **FK ON DELETE omission**: Every foreign key MUST document its ON DELETE behavior. No undocumented FKs.

7. **Global vs tenant-bound**: GrainType, ToleranceTable, MermaTable are GLOBAL (no tenant FK, no RLS). Every other grain domain entity inherits TenantBoundModel.

8. **WSLPG single-grain constraint**: 1 LiquidacionPrimaria = 1 grain type only. codGrano is at the XML root level. This constraint MUST appear prominently in S8.2.

9. **Campaign format mismatch**: Django model stores "YYYY/YY" (7 chars, "2024/25"). WSLPG XML uses 4-digit "YYZZ" (e.g., "2425"). Document this conversion in S8.3.

10. **Posicion consolidada**: NOT a stored entity. It's a derived view computed on demand. Do NOT create a model for it.

---

## Review Checklist (run after all sections complete)

### Full-Text Searches

```bash
# No FLOAT or DOUBLE anywhere
grep -i "FLOAT\|DOUBLE\|FloatField\|DoubleField" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: no output

# DECIMAL precision consistency
grep "DECIMAL" "Docs/Project Blueprint/Data Model & Domain Model.md" | \
  grep -v "17,3\|5,2\|12,3\|7,4\|8,3" | head -20
# Expected: no unexpected precision values

# TenantBoundModel inheritance coverage
grep -c "Inherits.*TenantBoundModel\|GLOBAL" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: 15+ (one per grain domain entity)

# Romaneo field count
grep -A100 "### 5\.3.*Romaneo" "Docs/Project Blueprint/Data Model & Domain Model.md" | \
  grep "^|" | grep -v "Field\|---" | head -40
# Expected: >= 30 data rows

# Hf vs humedad_base distinction
grep -i "hf_secado_pct\|humedad_base_pct" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: both present, clearly distinguished

# Mermaid diagram count
grep -c '```mermaid' "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: >= 4 (2 ERDs + 2+ state machines)

# State machine values consistency
grep "PENDIENTE\|EN_PROCESO\|PESADO\|ANALIZADO\|CONFORME\|CERRADO" \
  "Docs/Project Blueprint/Data Model & Domain Model.md" | head -20
# Verify: exact values match throughout

# WSLPG field mapping coverage
grep -c "puntoEmision\|numeroOrden\|codGrano\|pesoNetoGranos\|importeBruto\|importeNeto" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: each appears at least once

# Line count
wc -l "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: 1000-1800 lines

# RLS policy coverage
grep -c "tenant_isolation" "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: >= 12 (one per tenant-bound table)

# AI capabilities count
grep -c "Quality Degradation\|Silo Assignment\|Fraud Detection\|Price Forecasting\|Aeration" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: >= 4

# Append-only notes
grep -c "Append-only\|append-only\|IMMUTABLE\|immutable" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: >= 4 (AccountMovement, GrainMovement, MermaCalculation, Romaneo post-CONFORME)
```

### Cross-Section Consistency

- [ ] SC-010: 10 field names match between ERD (S3) and field tables (S5-S8)
- [ ] SC-002: Romaneo field table >= 30 rows
- [ ] SC-004: Every grain domain entity states TenantBoundModel or GLOBAL
- [ ] SC-005: All Mermaid diagrams render in GitHub Markdown
- [ ] SC-007: Every FK in S10 has ON DELETE documented
- [ ] SC-008: AI section has >= 4 capabilities with >= 3 named fields each
- [ ] SC-009: ToleranceTable + MermaTable have valid_from/valid_to
- [ ] State machine values match between `stateDiagram-v2` blocks and field table `choices`
- [ ] AccountMovement 8 types match PRD v1.0 S4.4 exactly
- [ ] LiquidacionPrimaria WSLPG mapping covers all 17 mandatory XML elements

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. `Docs/Project Blueprint/Data Model & Domain Model.md` updated to v1.0
2. All 15 grain domain entities have complete field tables (6-column: name, type, precision, null, default, description)
3. Romaneo field count >= 30 (verified by counting table rows)
4. All Mermaid ERD diagrams render without syntax errors
5. MermaCalculation documents Hf values per grain type with explicit distinction from Humedad base
6. WSLPG field mapping table covers all mandatory XML elements (17+)
7. All new grain domain tables have RLS policy template in S11
8. AI-Ready section maps >= 4 AI capabilities to >= 3 specific named model fields each
9. Zero field-name mismatches between ERD and field tables (SC-010 cross-check)
10. No FLOAT or DOUBLE in any field definition
11. Every grain domain entity inherits TenantBoundModel (SC-004) -- except 3 GLOBAL tables
12. Version = 1.0, Date = 2026-03-16, all 4 checkpoint gates pass

---

## Execution Summary

| Phase | Tasks | What to Write | Gate |
|-------|-------|---------------|------|
| 1 Setup | T001-T004 | Read sources, stub skeleton | -- |
| 2 Foundation | T005-T010 | S1, S2, S4, S7, S8.1, S9 (preserve/adapt) | Gate 1 |
| 3 Grain Domain | T011-T029 | S5.1-S5.8, S6.1-S6.3, S8.2-S8.4 | Gate 2, Gate 3 |
| 4 ERDs + Links | T030-T033 | S3, S10 (Mermaid diagrams, FK table) | -- |
| 5 Dual Inventory | T034-T036 | Architecture notes in S5.6, S7, S8.4 | -- |
| 6 Versioning | T037-T038 | S5.2 behavior note, S8.3 WSLPG mapping | Gate 3 |
| 7 AI-Ready | T039-T041 | S12 (4-layer strategy, capability mapping) | -- |
| 8 Polish | T042-T047 | S11 RLS, cross-checks, version stamp | Gate 4 (final) |
