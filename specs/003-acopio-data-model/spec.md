# Feature Specification: Acopio Data Model & Domain Model

**Feature Branch**: `003-acopio-data-model`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "Read @Docs/PROMPTS/spec-03-data-model/03-specify.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Grain Domain Model Comprehension (Priority: P1)

An engineer (or AI agent) opens the Data Model document to understand the complete grain domain model — all entities, fields, relationships, and constraints — for implementing a specific acopio module (e.g., Romaneo, Quality, Storage). The document must provide field-level definitions precise enough to generate model code and write unit tests without consulting any other source.

**Why this priority**: The Data Model document is the SINGLE SOURCE OF TRUTH for all Django models. Every implementation spec (09–12+) derives its model definitions from this document. Without precise, complete field definitions, implementation cannot begin.

**Independent Test**: Open the document to any grain domain entity (e.g., Romaneo). The field table contains: field name, data type, precision (max_digits/decimal_places), nullable, default, description — sufficient to write a model class and its migration without additional research.

**Acceptance Scenarios**:

1. **Given** the Romaneo entity definition, **When** an engineer reads it, **Then** they find at least 30 fields covering: identification (CPE, CTG, grain type, campaign), measurement (peso bruto, tara, peso neto, peso neto conforme), temporal (6 named timestamps: entrada, pesada_bruta, calado, analisis, descarga, tara), operational (state machine, operator, laboratorista, device_id), vehicle (patente_chasis, patente_acoplado, driver), and storage (silo/celda assignment) — all with explicit types and precision.

2. **Given** the MermaCalculation entity definition, **When** an engineer reads it, **Then** they find: the sequential formula `Peso_final = Peso_bruto × (1−%Z) × (1−%S) × (1−%M) × (1−%V)` documented, all input fields (grain type, incoming humidity Hi, Hf for secado formula, actual impurity levels), all intermediate results (peso after zarandeo, peso after secado, peso after manipuleo), the final peso neto conforme, fixed-value references (manipuleo: trigo 0.10%, maiz/soja 0.25%, girasol 0.20%, sorgo 0.25%; volatil: cereales 0.30%, oleaginosas 0.50%), and the secado formula `%S = (Hi − Hf) / (100 − Hf)` with the critical note that Hf differs from Humedad base per grain type.

3. **Given** the ProducerAccount entity definition, **When** an engineer reads it, **Then** they find: the dual-ledger structure (grain sub-ledger in kg by grain type + campaign; monetary sub-ledger in ARS/USD), the 8 transaction types (CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION), "a fijar" mechanics (remaining unfixed kg balance tracked per CEG via FijacionRecord), and the posición consolidada documented as a derived cross-plant view.

---

### User Story 2 — Entity Relationship Visualization (Priority: P2)

Engineers and AI agents use the ERD diagrams to understand how grain domain entities relate to each other, to existing infrastructure entities (Tenant, Branch, AppUser), and to downstream modules (Facturacion, Sync). The diagrams must render correctly in GitHub-flavored Markdown Mermaid and show all cross-module foreign keys.

**Why this priority**: Diagrams eliminate ambiguity in complex multi-entity domains. The grain domain has 15+ entities with cross-module relationships — without ERD visualization, implementers miss FK constraints and create inconsistent schemas.

**Independent Test**: Render each Mermaid ERD diagram in the document. All entities appear with their relationships (1:1, 1:N, N:M), FK directions are labeled, and ON DELETE behavior is annotated.

**Acceptance Scenarios**:

1. **Given** the global ERD (Section 3), **When** rendered, **Then** it shows all grain domain entities (Romaneo, QualityAnalysis, MermaCalculation, StorageUnit, GrainLot, GrainMovement, ProducerAccount, AccountMovement, LiquidacionPrimaria, CPE, FijacionRecord, CanjeOperation), all infrastructure entities (Tenant, Branch, AppUser), and all preserved entities (Comprobante, Product, StockMovement, SyncSession) — with directional relationships and cardinality labels.

2. **Given** the cross-module links section, **When** read, **Then** every FK between modules documents: source entity, target entity, FK field name, ON DELETE behavior (RESTRICT, CASCADE, or SET NULL), and a one-line rationale for the constraint choice.

3. **Given** the RLS policies section, **When** read, **Then** every new grain domain table has a documented RLS policy template specifying: the policy name, the qualifying column (tenant_id), and the session variable used (app.current_tenant_id) — matching the existing pattern used by Comprobante and StockMovement.

---

### User Story 3 — Dual Inventory Architecture Understanding (Priority: P3)

The document clearly separates and explains the two fundamentally different inventory models coexisting in the system: grain inventory (continuous, measured in kg, derived from romaneo peso neto conforme) and discrete inventory (units, counted, for agronomia inputs). A product owner can understand how both converge in the producer's cuenta corriente via the canje operation.

**Why this priority**: The dual inventory is a defining architectural characteristic of the acopio ERP. Incorrect modeling of either inventory type, or of their convergence point (canje), would break the most complex business operation in the system.

**Independent Test**: Navigate to the Dual Inventory section. The distinction is self-evident: grain inventory derives from romaneo events and is segregated by type/quality/campaign/silo; discrete inventory is counted by units with lot/expiry tracking. The canje operation is documented as the convergence point.

**Acceptance Scenarios**:

1. **Given** the grain inventory section (StorageUnit, GrainLot, GrainMovement), **When** read, **Then** the reader finds: silo/celda management with capacity, grain assignment by type/quality/campaign using composite key `(plant_id, grain_code, campaign_id)` per RG 3593, the distinction between own grain (balance-sheet asset) and third-party grain (off-balance-sheet cuentas de orden), and the link from Romaneo → GrainLot → StorageUnit.

2. **Given** the discrete inventory section (Product, StockMovement), **When** read, **Then** the reader finds: the existing inventory models preserved with added batch/lot/expiration fields for agronomia inputs (seeds, fertilizers, agroquimicos, repuestos), and discrete unit-based counting (not kg).

3. **Given** the CanjeOperation entity definition, **When** read, **Then** the reader finds: grain-for-input exchange workflow modeled with two parallel document FKs (LiquidacionPrimaria for grain settlement at IVA 10.5% + Comprobante for input invoice at IVA 21%), a canje_total vs canje_parcial flag (retentions apply only to cash portion in parcial), and all entries flowing into the producer cuenta corriente.

---

### User Story 4 — Reference Data Versioning (Priority: P4)

The document defines how tolerance tables, merma formulas, and quality parameters are versioned so that historical romaneos always reference the exact table version that was in effect when they were graded. A product owner understands that changing tolerance tables does not retroactively alter past quality grades.

**Why this priority**: Versioned reference data is essential for regulatory compliance — the Cámara Arbitral de Cereales updates tolerance tables periodically, and past operations must remain traceable to the exact version applied.

**Independent Test**: Navigate to the Tolerance & Merma Tables section. Each table entity has valid_from/valid_to temporal fields, and the Romaneo or QualityAnalysis entity includes an FK or snapshot reference to the specific version used.

**Acceptance Scenarios**:

1. **Given** the ToleranceTable entity, **When** read, **Then** it has: grain_type FK, valid_from date, valid_to date (nullable = currently active), and per-parameter tolerance thresholds with bonificación/rebaja percentages. Two versions for the same grain type can exist with non-overlapping date ranges.

2. **Given** a historical romaneo's QualityAnalysis, **When** the tolerance table version that was in effect is looked up, **Then** the FK or snapshot reference traces back to the exact version — even if a newer version has since been published.

---

### User Story 5 — AI-Ready Data Architecture Understanding (Priority: P5)

Data scientists and ML engineers can identify which operational fields serve as training features for each AI capability (quality degradation prediction, silo assignment optimization, price forecasting, weighbridge fraud detection, predictive aeration scheduling). The document maps model fields to AI features.

**Why this priority**: Phase 4 AI capabilities depend on structured data captured from day one. If fields are omitted or incorrectly typed during Phase 1 implementation, retroactive data migration is required.

**Independent Test**: Navigate to the AI-Ready section. For each AI capability, find the specific model fields that serve as training features, with field names, types, and the AI capability they support.

**Acceptance Scenarios**:

1. **Given** the AI-Ready Data Architecture section, **When** read, **Then** it maps at least 4 AI capabilities to specific model fields: (a) quality degradation prediction → QualityAnalysis fields + StorageUnit environment readings, (b) silo assignment optimization → GrainLot + StorageUnit capacity + quality grades, (c) weighbridge fraud detection → Romaneo patente_chasis/acoplado + peso_bruto/tara patterns + operator_id, (d) price forecasting → AccountMovement prices + campaign + grain type.

2. **Given** the provenance fields (created_at, updated_at, created_by, device_id, operator_id, laboratorista_id), **When** reviewed, **Then** every grain domain model includes these fields — enabling behavioral analytics on operator patterns and device reliability.

---

### Edge Cases

- What if a tolerance table is updated mid-campaign — do in-progress romaneos use the old or new version? → The version in effect at the romaneo's creation timestamp is used. The QualityAnalysis stores an FK to the specific ToleranceTable version.
- What if a romaneo is created offline and synced days later — which tolerance table version applies? → The version effective at the romaneo's local creation timestamp (ts_entrada), not the sync timestamp.
- How does the model handle "Fuera de Estándar" loads for cereals? → QualityAnalysis stores the grade as "FUERA_DE_ESTANDAR" with an operator_override flag and audit log. The romaneo can proceed but the grade cannot be changed retroactively.
- What if a producer's CUIT is associated with multiple ProducerAccounts across plants? → Each ProducerAccount is per-plant (TenantBoundModel + plant FK). Posición consolidada is a derived view aggregating across plants of the same tenant — not a stored entity.
- How does the model handle campaign carry-stock (grain from prior campaign still in silos)? → GrainLot retains its original campaign_id even when a new campaign starts. CampanaConfig tracks which campaign is active for new romaneos. Carry-stock report queries GrainLots where campaign_id ≠ active campaign.

---

## Requirements *(mandatory)*

### Functional Requirements

**Grain Domain Models**:

- **FR-001**: Document MUST define all grain domain models: GrainType, CampanaConfig, ToleranceTable, MermaTable, Romaneo, QualityAnalysis, MermaCalculation, StorageUnit (Silo/Celda), GrainLot, GrainMovement, WeighbridgeDevice — each with complete field-level definitions (name, type, precision, nullable, default, description). Quality measurement fields (humedad, materias_extranas, granos_dañados, etc.) are defined inline in QualityAnalysis with grain-type conditionality documented as field-level constraints; no separate QualityParameter entity is required.

- **FR-002**: Document MUST define the Romaneo model with at least 30 fields covering: CPE/CTG references, grain type and campaign FKs, peso bruto / tara / peso neto / peso neto conforme (all DECIMAL(17,3)), 6 named timestamps (ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara), state machine (PENDIENTE→EN_PROCESO→PESADO→ANALIZADO→CONFORME→CERRADO), operator_id and laboratorista_id FKs to AppUser, patente_chasis and patente_acoplado as separate fields, device_id for offline provenance, silo/celda assignment FK, and the immutability rule (append-only after CONFORME state, like Comprobante pattern).

- **FR-003**: Document MUST define QualityAnalysis with grain-specific measurement fields: humedad (%), materias_extranas (%), granos_danados (%), granos_quebrados (%), peso_hectolitrico (kg/hl, cereals only), proteina (%, trigo only), granos_verdes (%, soja only), granos_ardidos (%), cuerpos_extranos (%) — all as DECIMAL(5,2); plus derived fields: grado (Grado 1/2/3/FUERA_DE_ESTANDAR for cereals; tolerance-based rebaja for oleaginosas), bonificacion_pct, rebaja_pct, and a FK to the specific ToleranceTable version used.

  > **Design clarification (2026-03-16)**: The derived grade fields were placed on **Romaneo** (not QualityAnalysis) during spec-03 implementation. Specifically: `grado_asignado IntegerField`, `bonificacion_rebaja_pct DECIMAL(5,2)` (single signed field — positive = bonificación, negative = rebaja), and `tolerance_table_version FK ToleranceTable` all live on Romaneo.Group 7. Rationale: grade is an output of the romaneo process, not an intermediate analysis artefact. For **oleaginosas** (TOLERANCE grading system): `grado_asignado = 0` (convention for "no integer grade") and `bonificacion_rebaja_pct` carries the calculated rebaja percentage. Implementation specs (09+) MUST follow this placement, not the original FR-003 field list.

- **FR-004**: Document MUST define MermaCalculation as a separate immutable record linked to Romaneo, with: the sequential formula documented, input fields (grain_type, incoming_humidity_hi, hf_for_secado, impurity_levels), per-step deduction fields (zarandeo_pct, zarandeo_kg, peso_after_zarandeo; secado_pct, secado_kg, peso_after_secado; manipuleo_pct, manipuleo_kg, peso_after_manipuleo; volatil_pct, volatil_kg), and the final peso_neto_conforme. The secado formula `%S = (Hi − Hf) / (100 − Hf)` MUST be documented with the critical note that Hf values differ from Humedad base per grain type (trigo Hf=13.5% vs base=14.0%).

  > **Design clarification (2026-03-16)**: The per-step absolute **kg loss fields** (`zarandeo_kg`, `secado_kg`, `manipuleo_kg`, `volatil_kg`) are **not stored as separate fields** — they are derivable from the sequential intermediate weights (`peso_neto_bruto − peso_post_zarandeo = zarandeo_kg`, etc.). The implementation stores: all four input `_pct` values, all four `peso_post_*_kg` intermediate weights, `total_merma_kg`, and `total_factor_pct`. The per-step kg values can be reconstructed without separate columns. This is the canonical field set for implementation specs.

- **FR-005**: Document MUST define StorageUnit (type: vertical silo / horizontal celda / wet bin), GrainLot (grain in a silo with type/quality/campaign/producer), and GrainMovement (transfers between storage units) — with campaign composite key `(plant_id, grain_code, campaign_id)` per RG 3593, and the distinction between own grain (balance-sheet asset) and third-party grain (off-balance-sheet cuentas de orden).

**Producer Accounts**:

- **FR-006**: Document MUST define ProducerAccount (per-plant dual-ledger: grain sub-ledger in kg by grain type + campaign, monetary sub-ledger in ARS/USD) and AccountMovement with 8 transaction types: CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION. AccountMovement is append-only (ledger pattern). Posición consolidada documented as a derived cross-plant view (not a stored entity).

- **FR-007**: Document MUST define FijacionRecord linked to CEG: pizarra_price at fix time, kg_fixed, remaining_unfixed_kg (for partial fijacion tracking — single CEG can generate multiple LPGs over time), LiquidacionPrimaria FK, timestamp.

**Reference Data Versioning**:

- **FR-008**: Document MUST define versioning pattern for ToleranceTable and MermaTable: valid_from date, valid_to date (nullable = currently active), grain_type FK. Both tables are global (not per-tenant); all tenants share the same regulated versions published by the Cámara Arbitral de Cereales. Historical romaneos always reference the version in effect at their creation timestamp (ts_entrada).

**Infrastructure Preservation**:

- **FR-009**: Document MUST preserve existing infrastructure models: Tenant, Branch, Role, AppUser, TenantBoundModel — unchanged from v0.3.

- **FR-010**: Document MUST preserve existing facturacion models (Comprobante, AlicIva, Tributo) and define LiquidacionPrimaria (Form 1116-C) as a new entity with single-grain-type constraint (1 form = 1 codGrano per WSLPG schema), WSLPG field mapping table (nroOrden, cuitComprador, codGrano, campania, pesoNetoGranos, precioReferencia, importeBruto, importeNeto, retenciones array), and lifecycle state machine (DRAFT→RETENCION_CALCULADA→SISA_VERIFICADA→WSLPG_PRESENTADA→LIQUIDADA).

- **FR-011**: Document MUST preserve existing inventory models (Product, ProductCategory, StockMovement) and adapt Product for agronomia inputs with batch/lot/expiration fields. StockMovement preserved for discrete SKU inventory.

- **FR-012**: Document MUST preserve SyncSession and PendingOperation models — unchanged from v0.3.

- **FR-013**: Document MUST preserve Customer, SaleOrder, SaleOrderItem models for service invoicing to producers (facturacion module), alongside the new grain domain models.

**Cross-Module and Compliance**:

- **FR-014**: Document MUST define CPE model linked 1:1 to Romaneo with lifecycle state tracking per WSCPE methods (Activa→Arribo→Descargada→Confirmada_Definitiva), 5-day validity tracking, and store-and-forward offline behavior annotation.

- **FR-015**: Document MUST define WeighbridgeDevice model (name, serial_number, branch FK, is_active) and WeighbridgeCalibration model: device FK → WeighbridgeDevice, calibration_date, technician, reference_weight, measured_deviation, certificate_number, next_due_date. One branch may have multiple devices; each calibration record belongs to one device.

- **FR-016**: Document MUST define CanjeOperation model with dual document FKs (LiquidacionPrimaria for grain + Comprobante for inputs), canje_total/parcial flag, and all entries flowing into ProducerAccount via AccountMovement.

- **FR-017**: Document MUST define CampanaConfig model: campaign_code (YYYY/YY format, 7 chars), start_date, end_date, is_active flag, per-tenant scope.

**Data Integrity**:

- **FR-018**: All grain domain models MUST inherit TenantBoundModel.

- **FR-019**: All weight and monetary fields MUST use DECIMAL(17,3). Percentage fields MUST use DECIMAL(5,2). No FLOAT or DOUBLE permitted (Constitution Principle I).

- **FR-020**: Every model MUST include created_at (auto), updated_at (auto), and created_by (FK to AppUser) for AI-ready provenance. Grain domain models additionally include device_id for offline provenance.

**Documentation**:

- **FR-021**: Document MUST include ERD diagrams using Mermaid syntax — at minimum: (a) global view showing all entities and their module grouping, (b) grain domain detail view showing Romaneo and its satellite entities.

- **FR-022**: Document MUST include cross-module link documentation: every FK between modules with source entity, target entity, FK field name, ON DELETE behavior, and rationale.

- **FR-023**: Document MUST include RLS policy templates for all new grain domain tables, following the existing pattern (policy name, tenant_id column, app.current_tenant_id session variable).

- **FR-024**: Document MUST include AI-Ready Data Architecture section mapping model fields to AI capabilities: quality degradation prediction, silo assignment optimization, weighbridge fraud detection, price forecasting, predictive aeration scheduling.

- **FR-025**: FR-001 through FR-024 collectively supersede all 11 entities from `specs/002-acopio-prd/data-model.md`. The spec-03 entity set is authoritative.

### Key Entities

- **GrainType**: ARCA grain species code, name (Spanish canonical + English), humidity base (commercialization), Hf (merma secado), manipuleo fixed %, volatil fixed %. 5 primary: trigo, maiz, soja, girasol, sorgo.

- **CampanaConfig**: Campaign year code (YYYY/YY), start/end dates, active flag, per-tenant. Determines which campaign applies to new romaneos.

- **ToleranceTable**: Versioned reference data per grain type. Valid_from/valid_to temporal range. Contains per-quality-parameter tolerance thresholds with bonificación/rebaja rates used to assign Grado and calculate rebaja %.

- **MermaTable**: Versioned reference data per grain type. Valid_from/valid_to temporal range. Contains zarandeo threshold ranges (materias_extranas % ranges → %zarandeo deduction). Manipuleo and volatil fixed % constants live in GrainType (not versioned).

- **Romaneo**: The atomic operational transaction. Links to: CPE (1:1), QualityAnalysis (1:1), MermaCalculation (1:1), StorageUnit (N:1), ProducerAccount (via AccountMovement). 30+ fields. Immutable after CONFORME state.

- **QualityAnalysis**: Per-romaneo lab results. All grain-specific measurements + derived grade + FK to ToleranceTable version used.

- **MermaCalculation**: Immutable calculation record. Sequential formula with all intermediate steps preserved. Linked 1:1 to Romaneo.

- **StorageUnit**: Physical silo/celda/wet bin. Capacity, type, current occupancy. Contains GrainLots.

- **GrainLot**: Grain in a storage unit: type, quality, campaign, producer, quantity. Campaign composite key (plant_id, grain_code, campaign_id).

- **ProducerAccount / AccountMovement**: Per-plant dual-ledger. 8 transaction types. Append-only. Posición consolidada is derived view.

- **LiquidacionPrimaria**: Form 1116-C/B settlement. Single-grain-type constraint. WSLPG field mapping. Lifecycle state machine.

- **CPE**: Electronic waybill. 1:1 with Romaneo. WSCPE lifecycle states. 5-day validity.

- **FijacionRecord**: Price crystallization for "a fijar" grain. Tracks partial fijaciones against a single CEG.

- **CanjeOperation**: Grain-for-input exchange. Dual document streams (LPG + Factura). Total/parcial flag.

- **WeighbridgeDevice**: Physical weighbridge asset per branch. Serial number, active flag. One branch may have multiple devices.

- **WeighbridgeCalibration**: Calibration record per WeighbridgeDevice. Certificate tracking. Next-due alerting.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer reading any entity definition can write a complete model class with migration — including all fields, types, precision, constraints, and FKs — without consulting any other document. Verification: pick any 3 entities at random and generate models; all 3 produce valid, consistent schemas.

- **SC-002**: The Romaneo entity has at least 30 explicitly defined fields covering all 5 field categories (identification, measurement, temporal, operational, vehicle). Verification: count fields in the Romaneo table.

- **SC-003**: The merma formula section is unambiguous: two independent engineers implementing the same inputs produce identical peso_neto_conforme values. Verification: provide test inputs (grain type, humidity, impurity levels, peso bruto) and confirm both engineers derive identical outputs using only the document.

- **SC-004**: Every grain domain entity inherits TenantBoundModel and has a documented RLS policy template. Verification: scan all entity definitions and RLS section; zero exceptions.

- **SC-005**: All ERD diagrams render correctly in GitHub-flavored Markdown Mermaid. Verification: render each diagram in a Markdown preview; zero syntax errors.

- **SC-006**: The document contains at least 2 Mermaid ERD diagrams: (a) global entity view, (b) grain domain detail view. Both render without errors.

- **SC-007**: Every cross-module FK documents ON DELETE behavior (RESTRICT, CASCADE, or SET NULL). Verification: scan the cross-module links section; zero undocumented FKs.

- **SC-008**: The AI-Ready section maps at least 4 AI capabilities to specific model fields by name. Verification: for each AI capability, find at least 3 named model fields that serve as training features.

- **SC-009**: Reference data tables (ToleranceTable, MermaTable) have valid_from/valid_to versioning fields. Verification: inspect the entity definitions.

- **SC-010**: The document is self-consistent: field names in ERD diagrams match field names in entity definition tables. Verification: cross-check a sample of 10 fields between ERD and tables; zero mismatches.

## Clarifications

### Session 2026-03-16

- Q: What data does `MermaTable` hold that is not already in `GrainType` or `MermaCalculation`? → A: `MermaTable` holds per-grain zarandeo thresholds (materias_extranas tolerance ranges → %zarandeo deduction), versioned with valid_from/valid_to. Fixed manipuleo % and volatil % constants remain in `GrainType` (they do not change with regulatory updates).
- Q: Is `QualityParameter` a standalone DB entity or inline enumeration within `QualityAnalysis`? → A: Not a separate entity. Remove from FR-001. Quality measurement fields are defined inline in `QualityAnalysis`; grain-type conditionality documented as field-level constraints (e.g., peso_hectolitrico cereals only, proteina trigo only).
- Q: What entity does the `scale FK` in `WeighbridgeCalibration` point to? → A: Add `WeighbridgeDevice` as a new entity (name, serial_number, branch FK, is_active) to FR-001. `WeighbridgeCalibration.scale FK` points to `WeighbridgeDevice`. One branch may have multiple devices; calibration records are per-device for regulatory traceability.

## Assumptions

- **A-001**: The existing Data Model document v0.3 (`Docs/Project Blueprint/Data Model & Domain Model.md`) is the structural starting point — Ironclad manifesto, infrastructure models, and facturacion models are preserved and extended, not discarded.

- **A-002**: The document is written in English as the primary language, with Spanish domain terms used canonically (romaneo, merma, campaña, etc.) and translated on first use.

- **A-003**: All field definitions use Django model field conventions (CharField, DecimalField, ForeignKey, etc.) for familiarity, but the document is a specification — not executable code. Implementation specs (09+) translate these definitions into actual model classes.

- **A-004**: The 8 transaction types for AccountMovement are authoritative per PRD v1.0 §4.4. No additional types are introduced without PRD amendment.

- **A-005**: WSLPG XML field precision differences (e.g., ARCA uses different decimal places) are handled at the API serialization layer, not the model layer. All model fields use DECIMAL(17,3) for weights/monetary and DECIMAL(5,2) for percentages.

- **A-006**: The posición consolidada is a derived view (computed on demand), not a stored entity. It aggregates per-plant ProducerAccount balances for the same producer CUIT across all plants of the same tenant.

## Dependencies

- **Depends on**: spec-01 (Product Vision & Scope v1.0) ✅, spec-02 (PRD v1.0) ✅
- **Blocks**: spec-04 (ADRs), spec-05 (HLD), spec-06 (API Design), spec-09 through spec-12 (all implementation specs)
- **References**: existing `Docs/Project Blueprint/Data Model & Domain Model.md` (v0.3), `Docs/Project Blueprint/PRD.md` (v1.0)
