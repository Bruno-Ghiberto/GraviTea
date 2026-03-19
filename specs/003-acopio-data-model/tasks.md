# Tasks: Acopio Data Model & Domain Model

**Input**: Design documents from `specs/003-acopio-data-model/`
**Target**: `Docs/Project Blueprint/Data Model & Domain Model.md` (v0.3 → v1.0)
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Type**: Blueprint document rewrite (single-author Markdown, no code)
**Tests**: Not applicable (document spec). Verification = checkpoint gates from plan.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent sections, no cross-dependencies)
- **[Story]**: Which user story this task delivers
- All tasks write to `Docs/Project Blueprint/Data Model & Domain Model.md` unless noted

---

## Phase 1: Setup

**Purpose**: Read source documents, prepare workspace.

- [X] T001 Read existing `Docs/Project Blueprint/Data Model & Domain Model.md` (v0.3) to understand current structure and content to preserve
- [X] T002 Read `specs/003-acopio-data-model/research.md` to internalize all domain decisions (D-001–D-006) and critical domain facts (Hf values, merma formula, 8 tx types)
- [X] T003 Read `specs/003-acopio-data-model/data-model.md` for complete entity catalog (39 entities, field counts, state machines)
- [X] T004 Replace the v0.3 document header/structure: add all 12 target section headings (§1–§12) as a skeleton, preserving all v0.3 content in-place before overwriting sections in later tasks

---

## Phase 2: Foundational (Sections Shared by All User Stories)

**Purpose**: Sections that all user stories build on — metadata, manifesto, preserved infrastructure, agronomia, sync.

**⚠️ CRITICAL**: No user story sections can be finalized until foundation sections are complete.

- [X] T005 Update §1 Metadata table in `Docs/Project Blueprint/Data Model & Domain Model.md`: Version → 1.0, Title → "Data Model & Domain Model — Grain Domain v1.0", Language → English primary, Date → 2026-03-16, Owner → Bruno Ghiberto, Status → "Acopio de Granos Vertical — Active", add Scope row: "SINGLE SOURCE OF TRUTH for all Django models; grain domain v1.0"
- [X] T006 Update §2 Design Manifesto "Ironclad" in `Docs/Project Blueprint/Data Model & Domain Model.md`: preserve P1–P4 verbatim; extend P4 "Machine Learning First" with grain-specific AI examples (quality degradation, silo assignment, fraud detection, price forecasting); add NEW P5 "AI-Ready Data Architecture" (provenance fields: created_at, updated_at, created_by, device_id; measurement fields paired with timestamps; derived fields stored alongside inputs)
- [X] T007 Copy §4 Core Infrastructure verbatim from v0.3 into `Docs/Project Blueprint/Data Model & Domain Model.md`: Tenant (8 fields), Branch (7 fields), TenantFieldDefinition (8 fields), TenantModuleConfig (5 fields), BusinessTemplate (5 fields), AppUser (9 fields), Role (5 fields); add TenantBoundModel abstract base class definition (id, tenant FK, created_at, updated_at, created_by FK)
- [X] T008 Copy §9 Sync verbatim from v0.3 into `Docs/Project Blueprint/Data Model & Domain Model.md`: SyncSession (8 fields), PendingOperation (7 fields) — unchanged from v0.3
- [X] T009 Write §7 Agronomia / Discrete Inventory in `Docs/Project Blueprint/Data Model & Domain Model.md`: §7.1 Product field table — copy v0.3 fields + ADD batch_number (CharField max_length=50), lot_number (CharField max_length=50), expiration_date (DateField null=True), product_type (CharField choices: SEED/FERTILIZER/AGROQUIMICO/REPUESTO); REMOVE StockSnapshot (deprecated); §7.2 StockMovement — copy from v0.3 verbatim; preserve Supplier, ProductCategory, PriceList
- [X] T010 Copy §8.1 Facturación preserved entities verbatim from v0.3 into `Docs/Project Blueprint/Data Model & Domain Model.md`: Comprobante (20+ fields), AlicIva, Tributo, CbteAsoc, ArcaCredential, PuntoDeVenta, CAEA — no field changes; add section note: "LiquidacionPrimaria (Form 1116-C) defined in §8.2"

**Checkpoint**: Foundation sections complete. All preserved content in place. Grain domain sections (§5–§6, §8.2–§8.4, §10–§12) ready to be written.

---

## Phase 3: User Story 1 — Grain Domain Model Comprehension (Priority: P1) 🎯 MVP

**Goal**: Write complete field tables for all 15 grain domain entities so any entity definition is sufficient to write a model class without further research.

**Independent Test**: Open the document to any grain domain entity (e.g., Romaneo). The field table contains: field name, Django field type, max_digits/decimal_places, null, default, description — sufficient to write a model class and migration without additional research (SC-001).

### Implementation for User Story 1

- [X] T011 [P] [US1] Write §5.1 GrainType field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 8 fields (code CharField max_length=3, name CharField, humedad_base_pct DECIMAL(5,2), hf_secado_pct DECIMAL(5,2) with CRITICAL note "≠ humedad_base_pct — using wrong value yields ~168 kg error per 30t truck", manipuleo_fijo_pct DECIMAL(5,2), volatil_fijo_pct DECIMAL(5,2), grading_system CharField choices GRADO/TOLERANCE, is_active BooleanField); include reference data table: trigo Hf=13.5%/base=14.0%, maiz Hf=13.5%/base=14.5%, soja Hf=13.0%/base=13.5%, girasol Hf=10.5%/base=11.0%, sorgo Hf=13.5%/base=15.0%; note: GLOBAL entity (no tenant FK)
- [X] T012 [P] [US1] Write §5.1 CampanaConfig field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 6 fields (campaign_code CharField max_length=7 format "YYYY/YY", start_date DateField, end_date DateField, is_active BooleanField default=False, tenant FK ON DELETE PROTECT, notes TextField null=True); constraint: only 1 active per tenant; per-tenant (has tenant FK unlike GrainType)
- [X] T013 [P] [US1] Write §5.2 ToleranceTable field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 7 fields (grain_type FK GrainType PROTECT, valid_from DateField, valid_to DateField null=True "NULL=currently active", parameter CharField max_length=50, tolerance_pct DECIMAL(5,2), grado_base IntegerField, source_resolution CharField null=True); note: GLOBAL table (Cámara Arbitral de Cereales via SAGPyA/SENASA resolutions); section note re: cereals grading (Grado 1 bonif 1.0–1.5%, Grado 2 no adj, Grado 3 rebaja 1.0–1.5%) vs oleaginosas (progressive rebaja per point above tolerance)
- [X] T014 [P] [US1] Write §5.2 MermaTable field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 6 fields (grain_type FK GrainType PROTECT, valid_from DateField, valid_to DateField null=True, materias_extranas_from_pct DECIMAL(5,2), materias_extranas_to_pct DECIMAL(5,2) null=True, zarandeo_deduction_pct DECIMAL(5,2)); CRITICAL inline note: "MermaTable covers ONLY zarandeo thresholds. Manipuleo and volatil are FIXED values stored on GrainType (not versioned, not in MermaTable)"; note: GLOBAL table
- [X] T015 [US1] Write §5.3 Romaneo field table in `Docs/Project Blueprint/Data Model & Domain Model.md` with 7 field groups (minimum 30 total fields): (1) Identification: romaneo_number CharField, status CharField choices PENDIENTE/EN_PROCESO/PESADO/ANALIZADO/CONFORME/CERRADO default=PENDIENTE, grain_type FK, campaign_code FK CampanaConfig, branch FK; (2) Timestamps (FR-027): ts_entrada DateTimeField, ts_pesada_bruta null, ts_calado null, ts_analisis null, ts_descarga null, ts_tara null; (3) Vehicle (FR-026): patente_chasis CharField max_length=15, patente_acoplado CharField null=True, driver_name CharField, driver_dni CharField; (4) Weight: peso_bruto_kg DECIMAL(17,3) null, tara_kg DECIMAL(17,3) null, peso_neto_bruto_kg DECIMAL(17,3) null, weighbridge_device FK WeighbridgeDevice null; (5) CPE/Origin: cpe_numero CharField, ctg_codigo null, producer_cuit CharField max_length=13, origin_locality CharField; (6) Assignment: storage_unit FK null, grain_lot FK null; (7) Operator (FR-028): operator_id FK AppUser, laboratorista_id FK AppUser null, device_id CharField null; (8) Quality outcome: grado_asignado IntegerField null, bonificacion_rebaja_pct DECIMAL(5,2) null, tolerance_table_version FK ToleranceTable null; (9) Final: peso_neto_conforme_kg DECIMAL(17,3) null; immutability note: "IMMUTABLE after status=CONFORME — no field changes permitted (same pattern as Comprobante AUTORIZADO)"
- [X] T016 [US1] Write §5.3 Romaneo state machine Mermaid `stateDiagram-v2` in `Docs/Project Blueprint/Data Model & Domain Model.md`: 6 states with labeled transitions: PENDIENTE → EN_PROCESO (CPE arrival confirmed via confirmarArriboCPE) → PESADO (peso_bruto + tara captured from WeighbridgeDevice) → ANALIZADO (QualityAnalysis completed) → CONFORME (MermaCalculation completed + operator confirms — IMMUTABILITY GATE) → CERRADO (CPE definitively closed via confirmacionDefinitivaCPEAutomotor + ts_tara recorded); note "Romaneo is IMMUTABLE after CONFORME state"
- [X] T017 [P] [US1] Write §5.4 QualityAnalysis field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 12 fields (romaneo OneToOneField CASCADE, humedad_pct DECIMAL(5,2) "Hi — input to secado formula", materias_extranas_pct DECIMAL(5,2) "drives zarandeo lookup in MermaTable", granos_danados_pct DECIMAL(5,2), granos_quebrados_pct DECIMAL(5,2), peso_hectolitrico_kg DECIMAL(5,2) null "cereals only: trigo/maiz/sorgo", proteina_pct DECIMAL(5,2) null "trigo only", granos_verdes_pct DECIMAL(5,2) null "soja only", granos_ardidos_pct DECIMAL(5,2), cuerpos_extranos_pct DECIMAL(5,2), analysis_timestamp DateTimeField, sample_reference CharField null); note: "QualityParameter is NOT a separate entity — all measurement fields are inline; grain-type conditionality documented in help_text"
- [X] T018 [US1] Write §5.5 MermaCalculation field table and sequential formula in `Docs/Project Blueprint/Data Model & Domain Model.md`: document the formula block: Step 1 post_zarandeo = neto_bruto × (1−%Z/100); Step 2 post_secado = post_zarandeo × (1−%S/100); Step 3 post_manipuleo = post_secado × (1−%M/100); Step 4 peso_final = post_manipuleo × (1−%V/100); secado formula: `%S = (Hi − Hf) / (100 − Hf) × 100` with explicit note "Hf = GrainType.hf_secado_pct (NOT humedad_base_pct — using wrong value yields ~168 kg error per 30t truck)"; if Hi ≤ Hf then secado_pct = 0; then write 17-field table: romaneo OneToOneField CASCADE, merma_table_version FK MermaTable PROTECT, peso_neto_bruto_input_kg DECIMAL(17,3), hi_input_pct DECIMAL(5,2), hf_used_pct DECIMAL(5,2) "snapshot of GrainType.hf_secado_pct at calculation time", materias_extranas_input_pct DECIMAL(5,2), zarandeo_pct DECIMAL(5,2) "looked up from MermaTable", secado_pct DECIMAL(5,2) "0.00 if Hi≤Hf", manipuleo_pct DECIMAL(5,2) "snapshot of GrainType.manipuleo_fijo_pct", volatil_pct DECIMAL(5,2) "snapshot of GrainType.volatil_fijo_pct", peso_post_zarandeo_kg DECIMAL(17,3), peso_post_secado_kg DECIMAL(17,3), peso_post_manipuleo_kg DECIMAL(17,3), peso_final_kg DECIMAL(17,3), total_merma_kg DECIMAL(17,3), total_factor_pct DECIMAL(7,4), calculated_at DateTimeField auto_now_add, calculated_by FK AppUser; note: "IMMUTABLE — created once when Romaneo reaches CONFORME; never updated"
- [X] T019 [P] [US1] Write §5.6 StorageUnit field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 7 fields (name CharField max_length=100, unit_type CharField choices SILO_VERTICAL/CELDA_HORIZONTAL/SECADERO_BIN, branch FK Branch PROTECT, capacity_tonnes DECIMAL(12,3), is_active BooleanField default=True, current_grain_type FK GrainType null "NULL if empty", environment_sensor_id CharField null "IoT sensor ID for AI quality monitoring")
- [X] T020 [P] [US1] Write §5.6 GrainLot field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 8 fields (lot_code CharField max_length=30 "generated: BRANCH-GRAIN-CAMPAIGN-GRADE", branch FK Branch PROTECT, grain_type FK GrainType PROTECT, campaign FK CampanaConfig PROTECT, grado IntegerField "1/2/3; 0 for oleaginosas", storage_unit FK StorageUnit PROTECT, total_kg DECIMAL(17,3) default=0, is_own_grain BooleanField default=False "True=balance-sheet asset 1.3.XX; False=off-balance-sheet 8.1.XX"); note: composite key (branch + grain_type + campaign + grado) per RG 3593
- [X] T021 [P] [US1] Write §5.6 GrainMovement field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 6 fields (grain_lot FK GrainLot PROTECT, movement_type CharField choices DEPOSIT/WITHDRAWAL/TRANSFER_IN/TRANSFER_OUT, romaneo FK Romaneo null "source for DEPOSIT", quantity_kg DECIMAL(17,3) "positive=inflow, negative=outflow", movement_at DateTimeField auto_now_add, reference_document CharField null); note: "Append-only LEDGER — no UPDATE/DELETE"
- [X] T022 [P] [US1] Write §5.7 CPE field table and state machine in `Docs/Project Blueprint/Data Model & Domain Model.md`: 7 fields (romaneo OneToOneField CASCADE, cpe_numero CharField max_length=20, ctg_codigo CharField null "assigned by ARCA at confirmarArribo", status CharField choices ACTIVA/ARRIBO_CONFIRMADO/DESCARGADA/CONFIRMADA_DEFINITIVA default=ACTIVA, validity_expires_at DateTimeField "5-day validity window from issuance", wscpe_response_payload JSONField null "raw ARCA response for audit", pending_queue_ts DateTimeField null "enqueue timestamp if offline"); state machine: Activa → confirmarArriboCPE → Arribo_Confirmado → descargadoDestinoCPE → Descargada → confirmacionDefinitivaCPEAutomotor → Confirmada_Definitiva; note "Store-and-forward required for offline operations"
- [X] T023 [P] [US1] Write §5.8 WeighbridgeDevice field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 6 fields (name CharField max_length=100, serial_number CharField max_length=50, branch FK Branch PROTECT, is_active BooleanField default=True, interface_type CharField choices RS232/TCP_IP, connection_address CharField null "IP:port for TCP_IP; COM port for RS232")
- [X] T024 [P] [US1] Write §5.8 WeighbridgeCalibration field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 7 fields (device FK WeighbridgeDevice CASCADE, calibration_date DateField, technician CharField max_length=200, certificate_number CharField max_length=50, reference_weight_kg DECIMAL(12,3), deviation_kg DECIMAL(8,3), next_due_date DateField)
- [X] T025 [US1] Write §6.1 ProducerAccount field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: dual-ledger architecture explanation first; 8 fields (producer_cuit CharField max_length=13 "producer depositor CUIT", branch FK Branch PROTECT "per-plant scope", grain_type FK GrainType PROTECT "one account per grain type per producer per branch", campaign FK CampanaConfig PROTECT, grain_balance_kg DECIMAL(17,3) default=0 "running grain balance in kg", ars_balance DECIMAL(17,3) default=0 "ARS monetary balance", usd_balance DECIMAL(17,3) default=0 "USD monetary balance", is_active BooleanField default=True); note: "Posición consolidada (cross-plant view) is a DERIVED VIEW computed on demand — NOT a stored entity"
- [X] T026 [US1] Write §6.2 AccountMovement field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 8 authoritative transaction types list; 10 fields (producer_account FK ProducerAccount PROTECT, movement_type CharField choices CEG_DEPOSIT/LPG_SALE/FIJACION/RETIRO/SERVICE_CHARGE/CANJE_GRAIN_DEBIT/CANJE_INPUT_CREDIT/RETENTION_DEDUCTION, romaneo FK Romaneo null "for CEG_DEPOSIT", liquidacion FK LiquidacionPrimaria null "for LPG_SALE/FIJACION", quantity_kg DECIMAL(17,3) null "grain leg delta; positive=inflow, negative=outflow", ars_amount DECIMAL(17,3) null "ARS monetary delta", usd_amount DECIMAL(17,3) null "USD monetary delta", movement_at DateTimeField auto_now_add, reference_document CharField null, notes TextField null); note: "Append-only LEDGER — no UPDATE/DELETE"
- [X] T027 [P] [US1] Write §6.3 FijacionRecord field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 7 fields (deposit_movement FK AccountMovement PROTECT "CEG_DEPOSIT source movement", liquidacion FK LiquidacionPrimaria PROTECT "resulting LPG", pizarra_price DECIMAL(17,3) "published price at fix time", kg_fixed DECIMAL(17,3), remaining_unfixed_kg DECIMAL(17,3) "updated on each partial fijacion; reaches 0 when fully fixed", fixed_at DateTimeField, fixed_by FK AppUser PROTECT); note: "One CEG can generate multiple FijacionRecords over time (partial fijacion)"
- [X] T028 [US1] Write §8.2 LiquidacionPrimaria field table and state machine in `Docs/Project Blueprint/Data Model & Domain Model.md`: CRITICAL constraint: "1 LiquidacionPrimaria = 1 grain type only (WSLPG schema constraint — codGrano at root level)"; 18 fields including: romaneo FK Romaneo PROTECT, grain_type FK GrainType PROTECT, campaign FK CampanaConfig PROTECT, producer_account FK ProducerAccount PROTECT, status CharField choices DRAFT/RETENCION_CALCULADA/SISA_VERIFICADA/WSLPG_PRESENTADA/LIQUIDADA default=DRAFT, tipo_operacion CharField choices COMPRA_VENTA/CONSIGNACION/CANJE, punto_emision IntegerField "ARCA registered POS number", numero_orden IntegerField "sequential per punto_emision", fecha_emision DateField, peso_neto_granos_kg DECIMAL(17,3) "pesoNetoGranos in XML", precio_referencia DECIMAL(17,3), importe_bruto DECIMAL(17,3), importe_neto DECIMAL(17,3), alicuota_iva DECIMAL(5,2) "10.5% for grain", importe_iva DECIMAL(17,3), retenciones JSONField "array of {cod_retencion, importe_retencion}", wslpg_response JSONField null "raw ARCA response", wslpg_submitted_at DateTimeField null; state machine: DRAFT → RETENCION_CALCULADA → SISA_VERIFICADA → WSLPG_PRESENTADA → LIQUIDADA
- [X] T029 [P] [US1] Write §8.4 CanjeOperation field table in `Docs/Project Blueprint/Data Model & Domain Model.md`: 8 fields (lpg FK LiquidacionPrimaria PROTECT "grain leg: LPG at IVA 10.5%", comprobante FK Comprobante PROTECT "input leg: invoice at IVA 21%", canje_type CharField choices TOTAL/PARCIAL "retentions apply only to cash portion in PARCIAL", producer_account FK ProducerAccount PROTECT, grain_kg DECIMAL(17,3) "grain leg quantity", input_amount_ars DECIMAL(17,3) "input invoice amount", net_balance_ars DECIMAL(17,3) "residual after LPG credit − input invoice debit", created_at DateTimeField auto_now_add); note: "All entries flow into ProducerAccount via AccountMovement (CANJE_GRAIN_DEBIT + CANJE_INPUT_CREDIT)"

**Checkpoint (Gate 2)**: Count Romaneo field table rows ≥30 (SC-002). Verify MermaCalculation formula uses `hf_secado_pct` not `humedad_base_pct`. Both ToleranceTable and MermaTable have valid_from/valid_to (SC-009). All 15 grain domain entities have complete 6-column field tables.

---

## Phase 4: User Story 2 — Entity Relationship Visualization (Priority: P2)

**Goal**: Write all Mermaid ERD diagrams so engineers can understand cross-entity relationships without reading every field table.

**Independent Test**: Render each Mermaid diagram in GitHub-flavored Markdown. All diagrams render without syntax errors. Global ERD shows all 30+ entities grouped by module. Grain detail ERD shows Romaneo and its 5 satellite entities with FK direction labeled (SC-005, SC-006).

### Implementation for User Story 2

- [X] T030 [US2] Write §3.1 Global ERD Mermaid `erDiagram` in `Docs/Project Blueprint/Data Model & Domain Model.md`: group all entities under module comment blocks (`%% === INFRASTRUCTURE ===`, `%% === GRAIN DOMAIN ===`, `%% === PRODUCER ACCOUNTS ===`, `%% === AGRONOMIA ===`, `%% === FACTURACION ===`, `%% === SYNC ===`); show entity names + primary relationships only (not all fields); 30+ entities across all modules; use `||--o{` notation for 1:N, `||--||` for 1:1
- [X] T031 [US2] Write §3.2 Grain Domain Detail ERD Mermaid `erDiagram` in `Docs/Project Blueprint/Data Model & Domain Model.md`: include ALL fields for 8 core grain entities: Romaneo, QualityAnalysis, MermaCalculation, GrainLot, StorageUnit, ProducerAccount, AccountMovement, LiquidacionPrimaria; show field names with types; FK directions labeled
- [X] T032 [P] [US2] Write §10 Cross-Module Links FK table in `Docs/Project Blueprint/Data Model & Domain Model.md`: table with columns Source Entity | Target Entity | FK Field | ON DELETE | Purpose; minimum 13 rows covering: Romaneo→ProducerAccount (CEG_DEPOSIT trigger), Romaneo→StorageUnit (grain assignment), Romaneo→GrainLot (lot membership), CPE→Romaneo (1:1 companion CASCADE), QualityAnalysis→Romaneo (1:1 satellite CASCADE), MermaCalculation→Romaneo (1:1 immutable CASCADE), GrainMovement→Romaneo (deposit movement PROTECT), LiquidacionPrimaria→Romaneo (settlement PROTECT), FijacionRecord→LiquidacionPrimaria (price fix PROTECT), CanjeOperation→LiquidacionPrimaria (grain leg PROTECT), CanjeOperation→Comprobante (input leg PROTECT), AccountMovement→Romaneo (CEG_DEPOSIT PROTECT), AccountMovement→LiquidacionPrimaria (LPG_SALE/FIJACION PROTECT)
- [X] T033 [US2] Syntax-verify all Mermaid diagrams in `Docs/Project Blueprint/Data Model & Domain Model.md` by reviewing `erDiagram` and `stateDiagram-v2` blocks for common issues: unclosed brackets, invalid relationship notation, reserved word conflicts; fix any syntax errors found (SC-005)

**Checkpoint**: All Mermaid diagrams render. Cross-module FK table has ≥13 rows. Each FK documents ON DELETE behavior (SC-007).

---

## Phase 5: User Story 3 — Dual Inventory Architecture (Priority: P3)

**Goal**: Clarify the two coexisting inventory models and their convergence point (canje).

**Independent Test**: Navigate to the dual inventory sections. Grain inventory (continuous, kg, derived from romaneo) vs discrete inventory (counted units, agronomia inputs) is self-evident from section headings and architecture notes. CanjeOperation documents both document streams (SC from US3.3).

### Implementation for User Story 3

- [X] T034 [US3] Add §5.6 section header note in `Docs/Project Blueprint/Data Model & Domain Model.md` explicitly contrasting grain inventory with discrete inventory: "GRAIN INVENTORY (Continuous): measured in kg, derived from romaneo reception events, segregated by grain_type/quality/campaign/silo. NOT counted by units. Does NOT use StockMovement. See §7 for discrete inventory."; add own-grain vs third-party grain accounting note (GrainLot.is_own_grain: True=balance-sheet 1.3.XX; False=off-balance-sheet 8.1.XX)
- [X] T035 [P] [US3] Add §7 section header note in `Docs/Project Blueprint/Data Model & Domain Model.md` explicitly contrasting with grain inventory: "DISCRETE INVENTORY (Agronomia): counted in units (seeds, fertilizers, agroquimicos, repuestos). Uses StockMovement append-only ledger. NOT used for grain. Grain position is tracked by GrainLot + GrainMovement in §5.6."
- [X] T036 [US3] Add §8.4 CanjeOperation convergence note in `Docs/Project Blueprint/Data Model & Domain Model.md`: "CanjeOperation is the convergence point of both inventory systems: grain inventory (continuous) settles via LiquidacionPrimaria (LPG) at IVA 10.5%; agronomia inputs (discrete) invoice via Comprobante at IVA 21%. Both legs flow into ProducerAccount via AccountMovement: CANJE_GRAIN_DEBIT (grain sub-ledger debit) + CANJE_INPUT_CREDIT (ARS debit for input invoice value)."

**Checkpoint**: §5.6 and §7 have explicit architecture distinction notes. §8.4 documents the dual document FK convergence.

---

## Phase 6: User Story 4 — Reference Data Versioning (Priority: P4)

**Goal**: Ensure versioning is explicit in ToleranceTable/MermaTable, WSLPG field mapping is documented.

**Independent Test**: Navigate to §5.2. Both tables have valid_from/valid_to fields (SC-009). Navigate to §8.3 — WSLPG mapping table covers all mandatory XML elements.

### Implementation for User Story 4

- [X] T037 [US4] Add §5.2 versioning behavior note in `Docs/Project Blueprint/Data Model & Domain Model.md`: "Both ToleranceTable and MermaTable are versioned via valid_from/valid_to date fields. The version in effect at Romaneo.ts_entrada (local creation timestamp) is used — even if the romaneo is synced days later. QualityAnalysis.tolerance_table_version FK stores the exact version used. MermaCalculation.merma_table_version FK stores the exact MermaTable version used. A romaneo can never retroactively change its grade due to a table update."
- [X] T038 [US4] Write §8.3 WSLPG Field Mapping table in `Docs/Project Blueprint/Data Model & Domain Model.md`: columns XML Element | Data Type | Length/Precision | Requirement | Django Model Field; rows: tipo_reg (String/1 char/Mandatory/LiquidacionPrimaria), puntoEmision (Integer/4 digits/Mandatory/.punto_emision), numeroOrden (Integer/8 digits/Mandatory/.numero_orden — "must be lastAuthorized+1"), fechaEmision (Date/YYYY-MM-DD/Mandatory/.fecha_emision), codTipoOperacion (Enum/2 digits/Mandatory/.tipo_operacion), cuitComprador (String/11 digits/Mandatory/derived from ProducerAccount.producer_cuit), codGrano (Integer/2 digits/Mandatory/GrainType.code — "ROOT LEVEL: one Form 1116-C per grain type ONLY"), campania (Integer/4 digits/Mandatory/CampanaConfig.campaign_code YYZZ), codGrado (Integer/2 digits/Optional/Romaneo.grado_asignado), pesoNetoGranos (Integer/kg/Mandatory/.peso_neto_granos_kg), precioReferencia (Decimal/Mandatory/.precio_referencia), importeBruto (Decimal/Mandatory/.importe_bruto), importeNeto (Decimal/Mandatory/.importe_neto), alicuotaIva (Decimal/Mandatory/.alicuota_iva "10.5% for grain"), importeIva (Decimal/Mandatory/.importe_iva), retenciones (Array/Mandatory/.retenciones JSONField "array of {codRetencion, importeRetencion}"); add: "CRITICAL CONSTRAINT: codGrano is at the XML root level. A single Form 1116-C/B cannot cover multiple grain types. Generate separate XML payloads per grain type."

**Checkpoint (Gate 3)**: ToleranceTable + MermaTable have valid_from/valid_to in field tables (SC-009). WSLPG mapping table covers all 17 XML elements including retenciones array.

---

## Phase 7: User Story 5 — AI-Ready Data Architecture (Priority: P5)

**Goal**: Map model fields to AI capabilities so data scientists can identify training features.

**Independent Test**: Navigate to §12. Find at least 4 AI capabilities each with ≥3 specific named model fields as training features (SC-008).

### Implementation for User Story 5

- [X] T039 [US5] Write §12.1 Four-Layer Data Strategy in `Docs/Project Blueprint/Data Model & Domain Model.md`: Layer 1 Operational (all grain domain fields captured in real-time with timestamps); Layer 2 Behavioral (operator_id + laboratorista_id + device_id + 6 named timestamps per romaneo for process analytics); Layer 3 Quality History (QualityAnalysis + ToleranceTable versions + historical tolerance table versions for grade trend analysis); Layer 4 Physical State (StorageUnit.environment_sensor_id for IoT integration — predictive aeration scheduling data source)
- [X] T040 [US5] Write §12.2 AI Capability → Model Field Mapping table in `Docs/Project Blueprint/Data Model & Domain Model.md`: minimum 4 capabilities: (1) Quality Degradation Prediction → QualityAnalysis.humedad_pct, QualityAnalysis.granos_ardidos_pct, QualityAnalysis.analysis_timestamp, StorageUnit.environment_sensor_id, GrainLot.campaign — "time-series of quality readings per silo"; (2) Silo Assignment Optimization → GrainLot.total_kg, StorageUnit.capacity_tonnes, GrainLot.grado, GrainLot.grain_type, Romaneo.ts_entrada — "ML-assisted routing: which silo maximizes blending margin while preserving grade segregation"; (3) Weighbridge Fraud Detection → Romaneo.patente_chasis, Romaneo.patente_acoplado, Romaneo.peso_bruto_kg, Romaneo.tara_kg, Romaneo.operator_id, Romaneo.ts_pesada_bruta — "behavioral baseline: same plates, systematic peso differences, operator pattern analysis"; (4) Price Forecasting → AccountMovement.ars_amount, AccountMovement.usd_amount, AccountMovement.movement_at, FijacionRecord.pizarra_price, CampanaConfig.campaign_code, GrainType.code — "pizarra price time series + historical fixing behavior per producer"; (5 optional) Predictive Aeration Scheduling → StorageUnit.environment_sensor_id, GrainLot.campaign, QualityAnalysis.humedad_pct, GrainLot.grain_type
- [X] T041 [US5] Write §12.3 Feature Store Readiness section in `Docs/Project Blueprint/Data Model & Domain Model.md`: provenance fields present on all grain domain models (created_at, updated_at, created_by, device_id); every measurement field paired with a timestamp (QualityAnalysis.analysis_timestamp, MermaCalculation.calculated_at, Romaneo.ts_pesada_bruta, Romaneo.ts_analisis); derived fields stored alongside inputs (MermaCalculation: all 4 peso_post_* intermediate values + formula inputs preserved); no post-hoc data reconstruction needed — ML training can start from day 1 of production data

**Checkpoint**: §12 has 4+ AI capabilities mapped to ≥3 named model fields each (SC-008).

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: RLS policies, consistency verification, final quality gates.

- [X] T042 Write §11 RLS Policy templates in `Docs/Project Blueprint/Data Model & Domain Model.md` for ALL 18 new grain domain tables: use this SQL template pattern for each table: `CREATE POLICY tenant_isolation ON {table_name} USING (tenant_id = current_setting('app.current_tenant_id')::uuid);`; list tables: grain_type (GLOBAL — no RLS), campana_config, tolerance_table (GLOBAL — no RLS), merma_table (GLOBAL — no RLS), romaneo, quality_analysis, merma_calculation, storage_unit, grain_lot, grain_movement, weighbridge_device, weighbridge_calibration, cpe, producer_account, account_movement, fijacion_record, liquidacion_primaria, canje_operation; note which tables are GLOBAL (no RLS needed) vs tenant-bound
- [X] T043 [P] SC-010 cross-check: verify 10 field names match between ERD diagrams (§3) and field tables (§5–§8) in `Docs/Project Blueprint/Data Model & Domain Model.md`; pick: Romaneo.patente_chasis, Romaneo.ts_entrada, QualityAnalysis.humedad_pct, MermaCalculation.hf_used_pct, GrainLot.is_own_grain, ProducerAccount.grain_balance_kg, AccountMovement.movement_type, LiquidacionPrimaria.peso_neto_granos_kg, WeighbridgeCalibration.next_due_date, CanjeOperation.canje_type; fix any mismatches found
- [X] T044 [P] SC-002 verify: count fields in Romaneo field table; confirm ≥30 rows; if count < 30, add missing fields from spec FR-002 in `Docs/Project Blueprint/Data Model & Domain Model.md`
- [X] T045 SC-004 verify: confirm every grain domain entity definition includes "Inherits: TenantBoundModel" note (exception: GrainType, ToleranceTable, MermaTable which are GLOBAL); add missing inheritance notes in `Docs/Project Blueprint/Data Model & Domain Model.md`
- [X] T046 Terminology consistency sweep: verify these exact Django TextChoices values are used consistently between state machines and field tables throughout `Docs/Project Blueprint/Data Model & Domain Model.md`: Romaneo status: PENDIENTE/EN_PROCESO/PESADO/ANALIZADO/CONFORME/CERRADO; LiquidacionPrimaria status: DRAFT/RETENCION_CALCULADA/SISA_VERIFICADA/WSLPG_PRESENTADA/LIQUIDADA; CPE status: ACTIVA/ARRIBO_CONFIRMADO/DESCARGADA/CONFIRMADA_DEFINITIVA; AccountMovement type: CEG_DEPOSIT/LPG_SALE/FIJACION/RETIRO/SERVICE_CHARGE/CANJE_GRAIN_DEBIT/CANJE_INPUT_CREDIT/RETENTION_DEDUCTION
- [X] T047 Final version stamp: update §1 Metadata in `Docs/Project Blueprint/Data Model & Domain Model.md` — confirm Version = 1.0, Date = 2026-03-16, Status = "Acopio de Granos Vertical — Active"; run through Done Criteria checklist from plan.md (12 items); confirm all 12 pass before marking complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story phases
- **US1 (Phase 3)**: Depends on Phase 2 — can begin once foundation sections are complete
- **US2 (Phase 4)**: Depends on US1 (Phase 3) — ERD requires all entities defined first
- **US3 (Phase 5)**: Can begin in parallel with US2 after US1 completes — independent sections
- **US4 (Phase 6)**: Can begin in parallel with US2/US3 after US1 completes — §5.2 verify + §8.3 new
- **US5 (Phase 7)**: Can begin after US1 completes — §12 requires entity field names from §5–§8
- **Polish (Phase 8)**: Depends on ALL user story phases — cross-cutting verification

### Within Phase 3 (US1 — Largest Phase)

- T011–T014 [P]: GrainType, CampanaConfig, ToleranceTable, MermaTable → can write in parallel
- T015–T016: Romaneo field table + state machine → sequential (state machine references field names)
- T017 [P]: QualityAnalysis → can write in parallel with Romaneo
- T018: MermaCalculation → depends on Romaneo (references peso_neto_bruto) and QualityAnalysis (references humedad_pct)
- T019–T022 [P]: StorageUnit, GrainLot, GrainMovement, CPE → can write in parallel
- T023–T024 [P]: WeighbridgeDevice, WeighbridgeCalibration → can write in parallel
- T025–T026: ProducerAccount → AccountMovement (account before movements)
- T027 [P]: FijacionRecord → can write in parallel with AccountMovement (different entity)
- T028: LiquidacionPrimaria → depends on GrainType + CampanaConfig + ProducerAccount (field references)
- T029 [P]: CanjeOperation → can write in parallel with LiquidacionPrimaria

### Parallel Opportunities

All [P]-marked tasks within a phase can be written simultaneously by parallel agents or in any order by a single agent.

---

## Parallel Example: Phase 3 (US1) Reference Data Sub-Group

```text
Launch in parallel (T011–T014):
  Task: "Write §5.1 GrainType field table (T011)"
  Task: "Write §5.1 CampanaConfig field table (T012)"
  Task: "Write §5.2 ToleranceTable field table (T013)"
  Task: "Write §5.2 MermaTable field table (T014)"

Then sequential:
  Task: "Write §5.3 Romaneo field table 30+ fields (T015)"
  Task: "Write §5.3 Romaneo state machine (T016)"

Then parallel (T017–T022):
  Task: "Write §5.4 QualityAnalysis (T017)"
  Task: "Write §5.6 StorageUnit (T019)"
  Task: "Write §5.6 GrainLot (T020)"
  Task: "Write §5.6 GrainMovement (T021)"
  Task: "Write §5.7 CPE (T022)"
  Task: "Write §5.8 WeighbridgeDevice (T023)"
  Task: "Write §5.8 WeighbridgeCalibration (T024)"

Then sequential:
  Task: "Write §5.5 MermaCalculation + formula (T018)"  [depends on T015 + T017]
  Task: "Write §6.1 ProducerAccount (T025)"
  Task: "Write §6.2 AccountMovement (T026)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational — preserved + adapted sections)
3. Complete Phase 3 (US1 — all 15 grain domain entity field tables)
4. **STOP and VALIDATE**: Gate 2 check — Romaneo ≥30 fields, formula uses Hf, all entities have 6-column tables
5. Document is usable by implementation engineers even without ERDs

### Full Delivery

1. Setup + Foundational → preserved structure in place
2. US1 → all grain domain entity field tables → Gate 2 ✓
3. US2 → ERD diagrams → Gate 1 ✓ (ERDs confirm entity relationships)
4. US3 + US4 in parallel → dual inventory notes + WSLPG mapping → Gate 3 ✓
5. US5 → AI-Ready section
6. Polish → RLS, SC-010, SC-002, terminology → Gate 4 ✓ → v1.0 complete

---

## Notes

- [P] tasks = independent document sections, no content dependencies
- [Story] label maps writing task to user story for traceability
- Each user story phase produces a verifiable increment of the target document
- Single-author rewrite: one agent writes the complete document sequentially (no tmux/multi-agent)
- All field definitions use DECIMAL(17,3) for weight/monetary, DECIMAL(5,2) for percentages — zero exceptions
- Target document path: `Docs/Project Blueprint/Data Model & Domain Model.md`
