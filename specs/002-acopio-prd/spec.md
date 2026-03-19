# Feature Specification: Acopio PRD Rewrite

**Feature Branch**: `002-acopio-prd`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "Read @Docs/PROMPTS/spec-02-prd/02-specify.md"

## Clarifications

### Session 2026-03-16

- Q: Should the PRD specify a consolidated cross-plant producer account view in addition to per-plant ledgers? → A: Yes — per-plant ledger is the source of truth; PRD also requires a cross-plant "posición consolidada" view for the Dueño (adds to FR-004 + FR-012 scope).
- Q: What mechanism initiates the price-fixing event for "a fijar" grain? → A: Producer contacts acopiador to fix at current pizarra price → administrador creates fijación record → LPG generated → monetary value crystallizes (acopiador-side, producer-requested).
- Q: How much quality dispute handling must the PRD specify for the CALIDAD module? → A: Audit trail only — system exposes full transparent calculation history per romaneo on demand; formal disputes are escalated to Cámara Arbitral de Cereales (CAC) externally. No dispute lifecycle state machine inside the ERP.
- Q: What must the PRD specify as the campaign transition workflow? → A: Configuration + reconciliation report — admin defines new campaign year code → system generates carry-stock report (grain held from prior campaign) to support AFIP declaration; formal AFIP submission is manual/external to the system.
- Q: How prescriptive should the PRD's weighbridge section be? → A: Interface-level — specify supported interfaces (RS-232 serial, TCP/IP via converter bridge) and dual-scale workflow behavior; omit brand names, baud rates, and frame formats (those belong in spec-08c SRS).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Module Specification Reading (Priority: P1)

An engineer (or AI agent) opens the PRD to understand what a single acopio module must do — for example, RECEPCIÓN (Romaneo). The PRD must provide a complete, self-contained module specification: feature list, state machine, data capture requirements, offline behavior, and at least three acceptance scenarios per user story. The engineer should be able to implement the module entirely from the PRD without consulting external sources.

**Why this priority**: The PRD is the primary specification document for all engineering work. Module specifications are the highest-value content — without them, no implementation can begin reliably.

**Independent Test**: Open the PRD and navigate to any of the 8 acopio module sections (§4.1–§4.8). The section is complete enough to specify a data model and write unit tests without additional research.

**Acceptance Scenarios**:

1. **Given** the PRD's RECEPCIÓN section, **When** an engineer reads it, **Then** they can identify all 11 romaneo steps, all data fields per step, the state machine transitions (PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO), the offline behavior (store-and-forward CPE queue), and the CPE/CTG integration points — all from that section alone.

2. **Given** the PRD's CALIDAD section, **When** a laboratorista (lab analyst) reads it, **Then** they recognize their workflow: grading a sample, applying tolerance tables by grain type, computing merma in the mandatory sequential order (zarandeo → secado → manipuleo → volátil per CAC Circular 10/86), and generating a defensible quality determination — with the distinction that cereals (trigo, maíz, sorgo) use Grado 1/2/3, while oleaginosas (soja, girasol) use tolerance-based progressive rebajas.

3. **Given** the PRD's CUENTAS CORRIENTES section, **When** an engineer reads it, **Then** they can identify the dual-ledger structure (kg grain account + pesos/USD monetary account), the complete transaction type catalog (CEG deposit, LPG sale, retiro, service charges, canje), and the "a fijar" operation mechanics.

---

### User Story 2 — Regulatory Compliance Verification (Priority: P2)

An administrator/accountant reads the PRD to verify that all ARCA regulatory workflows are covered before development begins. They confirm: CPE/CTG lifecycle is handled for every truck reception, liquidación retention types are calculated with SISA-tier rates, and SISA status is verified as a blocking gate before any settlement.

**Why this priority**: Regulatory compliance failures result in sanctions and suspension of Carta de Porte issuance. Every ARCA workflow must be fully specified before any module touching fiscal data is built.

**Independent Test**: Navigate the PRD's Regulatory Compliance Specifications (§6). For each of five regulatory regimes (CPE/CTG, WSLPG, SISA, retentions, SICORE), find the specific RG citation and the automated system action vs. user confirmation boundary.

**Acceptance Scenarios**:

1. **Given** the PRD's WSLPG section (§6.2), **When** an accountant reads it, **Then** they find both Form 1116-C (Liquidación Primaria, acopiador-to-producer) and Form 1116-B (Liquidación Secundaria, acopiador-to-buyer) covered, with all retention types and SICORE magnetic file generation described.

2. **Given** the PRD's retention specification, **When** a developer reads it, **Then** they find the complete SISA-tier rate tables: IVA at 5% (Estado 1) / 8% (Estado 2) / 10.5% (Estado 3) / 16% (non-registered) per RG 2300, and Ganancias at 0% / 2% / 15% / 30% per RG 4325 — with a note that the SISA query before each liquidación determines which tier applies.

3. **Given** the PRD's SISA section (§6.3), **When** an accountant reads it, **Then** they find: RG 5689/2025 cited explicitly, the 24-hour grain movement registration requirement described, and the pre-liquidación SISA status check defined as a blocking gate (settlement cannot proceed without a valid SISA query result).

---

### User Story 3 — Phased Delivery Planning (Priority: P3)

The founder uses the PRD's phased delivery section to scope the MVP release and set measurable exit criteria. They confirm which modules ship in each phase, what the entry criteria are, and what the exit criteria are (customer-facing outcomes).

**Why this priority**: Phased planning protects cash flow and enables early customer validation. Phase 1 exit criteria define the demo-ready milestone for the first acopiador pilot — typically before the April–June optimal switching window.

**Independent Test**: Read §9 (Phased Delivery). Phase 1 scope is self-consistent: its four modules (RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES) cover the complete daily operational loop without requiring Phase 2+ modules.

**Acceptance Scenarios**:

1. **Given** the PRD's Phase 1 section, **When** the founder reads it, **Then** they find the complete Romaneo-to-Position loop as the MVP scope — truck arrival → quality grading → silo assignment → producer account credit — with exit criteria defined as "first real truck reception processed on a pilot plant."

2. **Given** the PRD's phase allocation, **When** counted, **Then** every one of the 8 acopio modules is assigned to exactly one phase, with entry and exit criteria for each, consistent with the roadmap in Product Vision & Scope v1.0 (Phase 1: RECEPCIÓN+CALIDAD+ALMACENAMIENTO+CUENTAS CORRIENTES; Phase 2: LIQUIDACIONES+FACTURACIÓN; Phase 3: CANJE+AGRONOMÍA; Phase 4: AI).

3. **Given** Phases 3 and 4, **When** a product manager reads them, **Then** Phase 3 includes CANJE, AGRONOMÍA, OCR document intelligence, and weighbridge fraud detection; Phase 4 includes AI features (quality degradation prediction, silo assignment optimization, price forecasting, predictive aeration) — consistent with Vision v1.0 §4.7.

---

### User Story 4 — Persona Journey Validation (Priority: P4)

All 5 personas can find their primary workflows in the PRD and verify that the system addresses their most critical pain points. Each persona has at minimum 3 user stories with testable acceptance criteria.

**Why this priority**: Without per-persona user stories, the system may be technically complete but miss the actual workflows that drive adoption. The PRD bridges Vision personas to engineering requirements.

**Independent Test**: Search for each of the 5 persona names in the PRD. For each, find at minimum 3 user stories with acceptance criteria specific to that persona's role.

**Acceptance Scenarios**:

1. **Given** the Balancero/Recibidor user stories, **When** read, **Then** they include: processing a truck in < 5 minutes during harvest peak, continuing romaneo processing when internet is down, and capturing peso bruto/tara from an integrated weighbridge without manual transcription.

2. **Given** the Contador Rural user stories, **When** read, **Then** they include: real-time multi-client transaction visibility without requesting files, one-click fiscal summary export for multiple acopio clients, and verification of retention calculations against SICORE obligations.

3. **Given** all persona user stories combined, **When** counted, **Then** there are at minimum 15 user stories total (5 personas × 3 minimum) with at least one Given/When/Then acceptance scenario each.

---

### User Story 5 — Operational Workflow Visualization (Priority: P5)

Engineers and AI agents use the PRD's Mermaid diagrams to understand business flows without requiring acopio domain knowledge. At minimum 5 diagrams cover: functional decomposition (module map mindmap), romaneo lifecycle (state diagram), complete operational flow (flowchart), liquidación lifecycle (state diagram), and module dependency graph.

**Why this priority**: Diagrams eliminate ambiguity in complex state machines. The romaneo has 6 states, the liquidación has its own lifecycle — without diagrams, implementers fill gaps with assumptions that diverge from business rules.

**Independent Test**: Render all Mermaid diagrams in the PRD. Each renders without errors and shows all states/transitions referenced in the surrounding text.

**Acceptance Scenarios**:

1. **Given** the romaneo lifecycle state diagram, **When** rendered, **Then** it shows all 6 states (PENDIENTE, EN_PROCESO, PESADO, ANALIZADO, CONFORME, CERRADO) with labeled transitions including the offline path (romaneo completes locally, CPE confirmation queued).

2. **Given** the operational flow diagram (§5.1), **When** rendered, **Then** it shows all 11 romaneo steps from truck arrival to CPE closure, with the fork after boleta de romaneo to both silo assignment (ALMACENAMIENTO) and producer account credit (CUENTAS CORRIENTES).

3. **Given** the module dependency graph, **When** rendered, **Then** all 8 modules appear with directional dependencies: RECEPCIÓN → ALMACENAMIENTO, RECEPCIÓN → CALIDAD, CALIDAD → CUENTAS CORRIENTES, CUENTAS CORRIENTES → LIQUIDACIONES, LIQUIDACIONES → FACTURACIÓN, CUENTAS CORRIENTES → CANJE, CANJE → AGRONOMÍA — matching the module map in Product Vision & Scope v1.0.

---

### Edge Cases

- What if an operation is partially online/offline (CPE arrival confirmation requires connectivity, but romaneo processing is offline)? → The per-module online/offline matrix (§8.1) must classify every operation: "works offline," "requires connectivity," or "store-and-forward."
- How does the PRD handle the two different quality grading systems (cereals vs. oleaginosas)? → Both systems must be explicitly specified in §4.2 with the distinction clearly labeled — not unified into one model.
- What if a producer disputes a quality grade? → The system provides on-demand audit trail access (all inputs, tolerance tables, merma steps). Formal dispute resolution is external — the acopiador submits the audit trail package to the Cámara Arbitral de Cereales (CAC). No internal dispute lifecycle is specified.
- What if a regulatory RG number changes after the PRD is published? → All RG citations must include the RG number and year, enabling future audits to identify which rules need updating.
- How does the PRD describe a romaneo that must remain as a local draft when CPE connectivity is unavailable at arrival? → The offline flow must specify: romaneo proceeds locally, CPE confirmarArriboCPE is queued in store-and-forward mode, CPE is confirmed when connectivity restores; descargadoDestinoCPE and confirmacionDefinitivaCPEAutomotor are called once connectivity is restored before romaneo closure.
- How does the PRD handle soja/girasol quality grading where "Fuera de Estándar" has different implications than for cereals? → The CALIDAD module must specify per-grain handling of out-of-tolerance lots.

---

## Requirements *(mandatory)*

### Functional Requirements

**Module Specifications**:

- **FR-001**: Document MUST specify RECEPCIÓN (Romaneo) module with: feature list, 6-state machine (PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO), data capture fields per romaneo step, offline flow (store-and-forward CPE confirmation queue), CPE/CTG integration points (confirmarArriboCPE on arrival; two-step closure: descargadoDestinoCPE at weight capture + confirmacionDefinitivaCPEAutomotor at romaneo close with actual peso neto conforme), and digital boleta de romaneo generation.

- **FR-002**: Document MUST specify CALIDAD module with: quality parameters for all 5 primary grains (trigo, maíz, soja, girasol, sorgo), two grading systems (Grado 1/2/3 for cereals; tolerance-based progressive rebajas for oleaginosas), merma calculation in mandatory sequential order (zarandeo → secado → manipuleo → volátil per CAC Circular 10/86), Hf adjustment table per grain for secado calculation, and configurable tolerance tables per plant.

- **FR-003**: Document MUST specify ALMACENAMIENTO module with: silo and cell management (capacity, state, type), grain assignment by type/quality/campaign, grain position report (what, where, whose), campaign year logical segregation (composite key: plant → grain → campaign per RG 3593), inter-silo movements, and cubicaje (volumetric estimation) support.

- **FR-004**: Document MUST specify CUENTAS CORRIENTES module with: dual-ledger (kg grain account + pesos/USD monetary account) as the per-plant source of truth, transaction type catalog (CEG deposit, LPG sale, retiro, service charges, canje entries, retention deductions), "a fijar" mechanics (grain enters at zero monetary value; price crystallizes when producer requests fijación → administrador records it at current pizarra price → LPG is generated), extracto (statement) generation by grain type and campaign, and a cross-plant "posición consolidada" view (aggregated kg + monetary balance per producer across all plants of the same tenant) for the Dueño/Gerente dashboard.

- **FR-005**: Document MUST specify LIQUIDACIONES module with: Liquidación Primaria (Form 1116-C) and Secundaria (Form 1116-B), full SISA-tier retention tables (IVA: 5%/8%/10.5%/16% per RG 2300; Ganancias: 0%/2%/15%/30% per RG 4325; IIBB per province), WSLPG electronic filing, SICORE magnetic file generation, and pre-liquidación SISA status verification as a blocking gate.

- **FR-006**: Document MUST specify FACTURACIÓN module with: electronic invoices (A/B/C) for plant services (secada, zarandeo, almacenaje, paritaria), credit/debit notes, CAE (online) and CAEA (offline) modes, noting that existing ARCA infrastructure from feature branch 001 is reused — only acopio-specific service types are new.

- **FR-007**: Document MUST specify AGRONOMÍA (Insumos) module with: input catalog (seeds, fertilizers, agroquímicos, repuestos), discrete inventory (units, not kg), stock by lot and expiry, purchases from distributors, sales to producers, and price lists.

- **FR-008**: Document MUST specify CANJE module with: grain-for-input exchange workflow, automatic compensation at pizarra price (grain credit vs. input debit), fiscal documentation (LPG + invoice), and recording of all entries in producer cuenta corriente.

**User Stories**:

- **FR-009**: Document MUST include Balancero/Recibidor user stories (minimum 3) covering: truck reception in < 5 minutes during harvest peak, offline romaneo when internet is down, and weighbridge integration eliminating manual transcription.

- **FR-010**: Document MUST include Laboratorista user stories (minimum 3) covering: grain sample grading with tolerance tables, automated merma with sequential formula, and quality dispute support via on-demand audit trail (inputs, tolerance tables applied, merma breakdown per step) — formal dispute escalation to Cámara Arbitral de Cereales (CAC) is external to the system; no dispute lifecycle state machine is required.

- **FR-011**: Document MUST include Administrador/Contable user stories (minimum 3) covering: Liquidación 1116-C filing with automatic SISA-tier retention calculations, SICORE magnetic file generation, and SISA status verification before settlement.

- **FR-012**: Document MUST include Dueño/Gerente user stories (minimum 3) covering: real-time grain position from mobile across all plants, consolidated producer account summary ("posición consolidada") showing outstanding balances aggregated across all plants of the tenant, and harvest throughput monitoring (trucks/hour per plant).

- **FR-013**: Document MUST include Contador Rural user stories (minimum 3) covering: real-time multi-client visibility, fiscal summary export, and retention calculation verification.

**Regulatory and Integration Specifications**:

- **FR-014**: Document MUST specify CPE/CTG integration with: WSCPE method catalog per romaneo step, offline store-and-forward queue, 5-day validity tracking, and state machine aligned with CPE lifecycle.

- **FR-015**: Document MUST specify weighbridge integration at interface level: supported interfaces (RS-232 serial and TCP/IP via converter bridge), dual-scale workflow behavior (primary scale for peso bruto, secondary scale for tara, automatic peso neto = peso bruto − tara), stability detection requirement (weight only captured when scale signals stable reading), and calibration tracking. Brand-specific protocol details (baud rates, frame formats, indicator models) are deferred to spec-08c (SRS).

- **FR-016**: Document MUST include a per-module online/offline matrix: offline operations (romaneo, quality grading, storage assignment, producer account credit), connectivity-required operations (CPE confirmation, WSLPG filing, SISA verification), and store-and-forward operations (CPE queue).

- **FR-017**: Document MUST specify campaign year management: split-year format (e.g., "2025/26"), logical segregation per campaign (composite key plant → grain → campaign per RG 3593), and a two-step campaign transition workflow — (1) admin defines the new campaign year code (system uses it for all subsequent romaneos), (2) system generates a carry-stock report identifying grain held from the prior campaign to support the operator's manual AFIP stock declaration. Formal AFIP submission is external to the system.

- **FR-018**: Document MUST specify phased delivery: every module assigned to a phase (Phase 1: RECEPCIÓN + CALIDAD + ALMACENAMIENTO + CUENTAS CORRIENTES; Phase 2: LIQUIDACIONES + FACTURACIÓN; Phase 3: CANJE + AGRONOMÍA; Phase 4: AI) with entry and exit criteria per phase.

- **FR-019**: Document MUST preserve the implementation foundation from v0.4: implementation status table, feature branch history (001–025), Rust module inventory, and API contract inventory.

### Key Entities

- **Romaneo (Weighing Ticket)**: The atomic operational transaction. Fields: CPE reference, grain type, campaign, truck plate, producer CUIT, peso bruto, tara, peso neto, quality parameters per grain type, merma breakdown (zarandeo/secado/manipuleo/volátil kg), peso neto conforme, silo assignment, state.

- **Merma Calculation**: Sequential deduction engine per CAC Circular 10/86. Inputs: grain type, peso bruto neto, actual humidity (Hᵢ), actual impurity levels, tolerance tables. Output: peso neto conforme. Formula: `Peso_final = Peso_bruto × (1 − %Z) × (1 − %S) × (1 − %M) × (1 − %V)`.

- **Producer Cuenta Corriente**: Dual ledger — per-plant ledger is the source of truth (grain sub-ledger in kg by grain type and campaign; monetary sub-ledger in ARS/USD). A cross-plant aggregated view ("posición consolidada") is derived by summing per-plant ledgers for the same producer CUIT across all plants of the tenant. Key documents: CEG (grain deposit), LPG (settlement), Cert. Retiro (withdrawal), F.2005/SIRE (retention certificate).

- **Liquidación (Settlement Document)**: Form 1116-C (Primaria) or 1116-B (Secundaria). Triggered by: (a) immediate sale at delivery, or (b) producer fijación request (for "a fijar" grain — producer contacts acopiador → administrador records fijación at current pizarra price → LPG generated). Fields: grain type, campaign, kg, price per ton/quintal, SISA status, IVA retention (SISA-tier rate), Ganancias retention (SISA-tier rate), IIBB retention, net payment. Filed via WSLPG.

- **Silo/Celda**: Physical storage unit. Attributes: identifier, type (vertical silo / horizontal celda / wet bin), capacity in tons, current occupancy by lot (grain type + quality + campaign + producer).

- **CPE (Carta de Porte Electrónica)**: Electronic waybill. Lifecycle: Activa (5-day validity) → Arribo (confirmarArriboCPE) → Descargada → Confirmada Definitiva (confirmarDescargaCPE with actual peso neto). Relationship: 1 CPE = 1 truck = 1 romaneo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An engineer reading any of the 8 module sections can identify all required data fields, state transitions, and offline behavior without consulting external sources — within 15 minutes per module.

- **SC-002**: All 5 personas are represented with at minimum 3 user stories each (≥ 15 total), and every user story has at least one Given/When/Then acceptance scenario.

- **SC-003**: Every regulatory citation includes a specific RG number and year (e.g., "RG 5689/2025"). Zero occurrences of vague references such as "ARCA regulations" or "applicable fiscal rules."

- **SC-004**: The merma calculation section is unambiguous: two independent developers implementing the same inputs (grain type, humidity, impurity levels, peso bruto) produce identical peso neto conforme values.

- **SC-005**: The retention tables are complete: IVA at 4 SISA-tier rates and Ganancias at 4 SISA-tier rates are explicitly listed, so any developer can implement the correct retention for any producer SISA status.

- **SC-006**: The PRD contains at minimum 5 Mermaid diagrams — all render without errors — covering: functional decomposition (mindmap), romaneo state machine, complete operational flow (11 steps), liquidación lifecycle, and module dependency graph.

- **SC-007**: The feature branch history (001–025) from v0.4 is preserved in §10, confirming continuity with the existing implementation foundation.

- **SC-008**: Zero occurrences of "cajero," "cashier," "retail," "ferretería," "distribuidor de bebidas," or "punto de venta" — confirmed by text search.

- **SC-009**: The PRD is consistent with Product Vision & Scope v1.0 on: 5 persona names, 8 module names, 4-phase allocation with same module assignments, and USD-indexed $90/seat/month pricing reference.

- **SC-010**: The per-module online/offline matrix (§8.1) classifies every module operation into one of three categories (offline / connectivity-required / store-and-forward), ensuring the offline-first architecture is reflected at the feature level.

## Assumptions

- **A-001**: The existing PRD v0.4 (`Docs/Project Blueprint/PRD.md`) is the structural starting point — implementation status tables, feature branch history 001–025, Rust module inventory, and API contract inventory are preserved and updated, not discarded.

- **A-002**: The PRD is written in English as the primary language, with Spanish domain terms used canonically (romaneo, merma, merma, acopiador, etc.) and translated on first use.

- **A-003**: The PRD does NOT duplicate strategic content from Product Vision & Scope v1.0 (market sizing, persona profiles, pricing rationale) — it references the Vision and focuses on functional decomposition and operational workflows.

- **A-004**: The phased delivery section matches exactly the 4-phase roadmap in Vision v1.0. No new phases are introduced.

- **A-005**: All 8 module names use the exact Spanish terminology committed in the Vision and Descripción General: RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE.

- **A-006**: The FACTURACIÓN module specification notes reuse of existing ARCA integration (feature branch 001) — only acopio-specific service types (secada, zarandeo, almacenaje, paritaria) are new content.

## Dependencies

- **Depends on**: spec-01 `Product Vision & Scope.md` v1.0 — ✅ completed
- **Blocks**: spec-03 (Data Model), spec-04 (Architecture Decision Records), spec-07 (Roadmap), spec-08a (ARCA Grain Guide), spec-08b (AI/ML Roadmap), spec-08c (SRS)
- **References**:
  - `Docs/Project Blueprint/Product Vision & Scope.md` v1.0
  - `Docs/Project Blueprint/Descripción General del Producto.md`
  - `Docs/Project Blueprint/PRD.md` v0.4 (implementation tables to preserve)
  - `Docs/PROMPTS/spec-02-prd/02-specify.md` (domain facts, FRs, ACs)
