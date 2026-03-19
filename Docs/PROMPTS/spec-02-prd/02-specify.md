# Spec 02: Product Requirements Document (PRD) -- Specification Context

## Feature Description

Rewrite the `Docs/Project Blueprint/PRD.md` document from a generic
horizontal ERP PRD (v0.4, targeting PyMEs minoristas) to a comprehensive
**acopio de granos** Product Requirements Document. The current PRD
specifies modules for Ventas, Inventario, Compras, POS, and Sync for
generic retail operations. The new version translates the committed
acopio vision (spec-01 v1.0) into implementable requirements with
module-by-module functional decomposition, user stories per persona,
operational workflows, regulatory compliance specifications, and
phased delivery.

The PRD is the **BRIDGE** between strategic vision and engineering.
Every data model entity (spec-03), architecture decision (spec-04),
and implementation spec (09-12+) derives its functional justification
from requirements defined in this document.

**Key distinction from spec-01**: The Vision says WHAT and WHY (market,
positioning, personas). The PRD says WHAT and HOW MUCH (feature specs,
user stories, acceptance criteria, operational workflows, regulatory
detail, data capture requirements, hardware integration).

## Current State (what exists)

The existing PRD (v0.4, 2026-03-01, in Spanish) contains:

- **Status**: "Fase de Investigación Vertical SaaS" -- CHANGE to committed acopio
- **Introduction**: "plataforma de gestión integral para PyMEs minoristas" -- REPLACE
- **Glossary**: Generic retail terms (Cajero, Comprobante, BranchStock) -- ADAPT for acopio domain terms
- **Functional decomposition**: Ventas, Inventario, Facturación ARCA, Compras, Sincronización, Personalización, Plataforma -- REPLACE with 8 acopio modules
- **Module details**: POS-01 through POS-xx with Cajero (cashier) scenarios -- REPLACE with romaneo, quality, storage, producer account scenarios
- **State diagrams**: SaleOrder lifecycle (DRAFT→CONFIRMED→INVOICED) -- ADAPT for romaneo/liquidación lifecycles
- **Implementation status table**: Feature branches 001-025 -- PRESERVE and update
- **Infrastructure**: Auth, Sync, Rust, ARCA integration details -- PRESERVE (this carries forward)
- **Mermaid diagrams**: Generic retail flows -- REPLACE with acopio operational flows

**Upstream dependency completed**: `Docs/Project Blueprint/Product Vision & Scope.md` v1.0
is the authoritative source for vision, personas, market, pricing, and roadmap.
The PRD must be consistent with it but NOT duplicate its strategic content.

Also reference `Docs/Project Blueprint/Descripción General del Producto.md`
which already contains the acopio module map, operational flow, dual inventory
architecture, and module descriptions in Spanish.

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

Use the RAG pipeline to gather operational domain knowledge:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

**Priority queries (run ALL before writing)**:

```bash
# Operations (2.x) — the core domain for the PRD
"romaneo workflow steps truck arrival weighbridge reception grain quality"
"grain quality parameters humidity moisture bonification rebaja tolerance tables"
"producer current account balance structure cuenta corriente grain kg pesos"
"merma calculation formula secado zarandeo volatil manipuleo sequential"
"campaign year management agricultural cosecha segregation grain"
"canje grain barter exchange supplies insumos producer accounting"
"day to day operations acopiador complete workflow 10 steps"

# Regulatory (1.x) — compliance specs per operation
"CPE CTG lifecycle states WSCPE confirmation arribo definitiva"
"liquidacion primaria secundaria Form 1116 B C grain settlement WSLPG"
"SISA registro sistemico RG 5689 2025 grain registration 24 hours"
"IVA retention 8% RG 2300 ganancias IIBB withholding grain calculation"
"provincial tax obligations IIBB rates acopio grain operations"

# Data Model (8.x) — field specifications for each operation
"romaneo data fields peso bruto tara neto ERP capture document structure"
"grain types codes ARCA humidity base quality parameters reference"
"CTG document structure state machine fields transitions"
"Form 1116 B-C XML field structure types lengths WSLPG"

# Hardware (3.x) — integration requirements
"weighbridge integration standards scale protocols serial RS232 IP"
"grain moisture meters lab equipment API integration"
```

### Source Documents (for reference -- prefer RAG results above)

Only read specific sections if RAG results are insufficient:

| Doc ID | Path | Relevant Sections |
|--------|------|-------------------|
| 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | All 10 steps of the romaneo workflow; complete operational flow |
| 2.2 | `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md` | Quality parameters per grain, grade tables, tolerance thresholds |
| 2.3 | `Docs/Researches/Markdown/2.3 Producer Current Accounts (Cuentas Corrientes de Productores).md` | Dual-ledger structure (kg + pesos), transaction types, canje mechanics |
| 2.4 | `Docs/Researches/Markdown/2.4 Grain Pricing, Contracts, and Market Mechanisms.md` | Pricing mechanisms, "a fijar" operations, forward contracts |
| 2.5 | `Docs/Researches/Markdown/2.5 Merma (Grain Loss) Calculations and Tolerance Tables.md` | Sequential merma formula (CAC 10/86), per-grain base values |
| 2.6 | `Docs/Researches/Markdown/2.6 Campaign Year Management.md` | Campaign lifecycle, grain segregation by campaign |
| 8.1 | `Docs/Researches/Markdown/8.1 Grain Types and Quality Parameter Reference Data.md` | Grain codes, humidity bases, quality fields per species |
| 8.2 | `Docs/Researches/Markdown/8.2 CTG Document Structure and State Machine.md` | CTG states, CPE fields, WSCPE method catalog |
| 8.3 | `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md` | Complete romaneo field specification, 5 data sections |
| 8.4 | `Docs/Researches/Markdown/8.4 Form 1116 B-C Field Structure for Data Model Design.md` | WSLPG XML fields, liquidación data model |
| 1.1 | `Docs/Researches/Markdown/1.1 Carta de Porte Electronica (CTG) -- Complete Lifecycle.md` | CPE lifecycle, CTG codes, 5-day validity, confirmation flow |
| 1.2 | `Docs/Researches/Markdown/1.2 AFIP Web Service WSCPE -- Technical Specification.md` | WSCPE SOAP endpoints, XML schemas, method catalog |
| 1.3 | `Docs/Researches/Markdown/1.3 Liquidacion Primaria de Granos -- Form 1116 B and C.md` | Form 1116 B/C field structure, regulatory requirements |
| 1.4 | `Docs/Researches/Markdown/1.4 Registro de Operadores de Granos and Withholding Tax Regime.md` | SISA, withholding tiers, operator categories |
| 1.5 | `Docs/Researches/Markdown/1.5 Provincial Tax Obligations for Grain Operations.md` | IIBB rates by province, retention certificates |
| 1.6 | `Docs/Researches/Markdown/1.6 Ley de Granos, Warrants, and Storage Legal Framework.md` | Legal framework, storage obligations, warrant system |
| 3.1 | `Docs/Researches/Markdown/3.1 Weighbridge Integration Standards.md` | Scale protocols (RS-232, IP), calibration, dual-scale setup |
| 3.2 | `Docs/Researches/Markdown/3.2 Grain Moisture Meters and Lab Equipment.md` | Lab equipment APIs, moisture meter integration |

### Critical Domain Facts (minimum context -- inlined from RAG)

**Romaneo workflow (from 2.1, 8.3)** [RAG-verified]:
The romaneo (weighing ticket) is the atomic transaction of an acopio plant. Every truck follows this exact sequence:
1. **Arrival**: Truck arrives with CPE (Carta de Porte Electrónica). Facility verifies CPE is "Activa" via WSCPE, confirms arrival (`confirmarArriboCPE`)
2. **Peso Bruto**: Loaded truck weighed on primary balanza (weighbridge). System captures gross weight
3. **Calado y Muestreo**: Pneumatic probe extracts grain sample for quality analysis
4. **Quality Analysis**: Lab grades sample against Cámara Arbitral tolerance tables — determines grade (1/2/3/fuera de estándar), bonificaciones, rebajas
5. **Merma Calculation**: Sequential deductions per CAC Circular 10/86: zarandeo → secado → manipuleo → volátil. Each applied to result of previous step. Formula: `Peso_final = Peso_bruto × (1-%Z) × (1-%S) × (1-%M) × (1-%V)`
6. **Tara**: Empty truck weighed on secondary balanza. System computes Peso Neto = Peso Bruto - Tara
7. **Peso Neto Conforme**: Final certified weight after all quality deductions applied
8. **Boleta de Romaneo**: Printed/digital ticket with all data — signed by recibidor and driver
9. **Silo Assignment**: Grain routed to specific silo/cell by type, quality, campaign
10. **Producer Account Credit**: Peso neto conforme credited to producer's cuenta corriente (kg balance)
11. **CPE Closure**: Facility calls `confirmarDescargaCPE` sending final weight, CTG closes

**Quality grading (from 2.2, 8.1)** [RAG-verified]:
- 5 primary grains: Trigo (wheat), Maíz (corn), Soja (soybean), Girasol (sunflower), Sorgo (sorghum)
- Each grain has specific: base humidity %, quality parameters, grade thresholds, tolerance tables
- Key parameters: humedad (moisture), materias extrañas (foreign matter), granos dañados (damaged), granos quebrados (broken), peso hectolítrico (test weight)
- **Cereals** (trigo, maíz, sorgo): 3-grade system — Grado 1 (premium, +bonification), Grado 2 (standard), Grado 3 (below standard, -rebaja)
- **Oleaginosas** (soja, girasol): **do NOT use the Grado 1/2/3 system** — they use tolerance-based rebajas: progressive % deductions per unit of excess over each tolerance threshold (e.g., for soja: materias extrañas >1% → 1% rebaja per excess point up to 3%, then 1.5% per point above 3%)
- "Fuera de Estándar" applies to lots with values so far out of tolerance that they require special commercial treatment or rejection
- Authority: Cámara Arbitral de Cereales de Rosario (CAC) publishes official tolerance tables per grain type and harvest year

**Merma formula (from 2.5)** [RAG-verified]:
Sequential application per CAC Circular 10/86 and Resolución JNG 22027/81:
1. Zarandeo (cleaning): applied first on peso bruto neto
2. Secado (drying): applied on result after zarandeo — uses published drying tables per grain
3. Manipuleo (handling): fixed % — trigo 0.10%, maíz/soja 0.25%, girasol 0.20%
4. Volátil (volatile): applied last — cereales 0.3%, oleaginosas 0.5%

**Producer accounts (from 2.3)** [RAG-verified]:
Dual-ledger system:
- **Grain account** (physical): deposits (entries from romaneo, backed by CEG — Certificación Electrónica de Granos), withdrawals (sales, deliveries), deductions (mermas, services in kind) — measured in kg by grain type
- **Monetary account** (financial): flows when grain is sold (liquidación via LPG — Liquidación Primaria de Granos), cash transactions, service charges, retention deductions — in ARS/USD
- "A fijar" operations: grain enters at zero monetary value; price crystallized later when producer fixes price; formal documents: CEG for deposit, LPG for sale
- Canje: producer delivers grain (debit kg), receives inputs (debit pesos for invoice), LPG credits pesos — compensated in account
- **Key formal documents**: CEG (grain deposit/certification), LPG (sale settlement), Cert. Retiro (withdrawal), F.2005/SIRE (tax retention certificate)

**CPE/CTG lifecycle (from 1.1, 8.2)** [RAG-verified]:
States: Activa → En Camino → Arribada → Descargada → Confirmada Definitiva
Key WSCPE methods: `solicitarCPEAutomotor`, `confirmarArriboCPE`, `confirmarDescargaCPE`, `anularCPE`, `rechazoCPE`
5-day validity period. One CPE = one truck = one romaneo (1:1:1 relationship)
Confirmation Definitiva overwrites estimated field weight with actual peso neto from romaneo

**Liquidación (from 1.3, 8.4)** [RAG-verified]:
- Liquidación Primaria (Form 1116-C): acopiador settles with producer — price × kg - retentions = net payment
- Liquidación Secundaria (Form 1116-B): acopiador settles with buyer (when selling to exporter/industry)
- Filed electronically via WSLPG web service
- Retentions calculated per liquidación: IVA (SISA-tier dependent: 5% Estado 1 / 8% Estado 2 / 10.5% Estado 3 / 16% non-registered; governed by RG 2300 as updated by SISA regime), Ganancias (0% Estado 1 / 2% Estado 2 / 15% Estado 3 / 30% non-registered; governed by RG 4325), IIBB (variable by province, see NF-006)
- Note: the "8% IVA" figure commonly cited (incl. in market comparisons) refers to SISA Estado 2 (Medium Risk) — the actual rate varies per producer's SISA compliance status
- SICORE magnetic files generated for retention reporting

**Campaign year (from 2.6)** [RAG-verified]:
- Agricultural campaign: typically April-March (e.g., 2025/26)
- All grain segregated by campaign year in storage and accounts
- Campaign affects: quality parameters, pricing, reporting, stock positions

**Strategic decisions (from spec-01 Vision v1.0)**:
- Architecture: new `apps/acopio/` + `apps/cuentas/` alongside existing infrastructure
- MVP scope: Phase 1 = Romaneo-to-Position loop (RECEPCIÓN → CALIDAD → ALMACENAMIENTO → CUENTAS CORRIENTES)
- Dual inventory: grain (continuous kg) + insumos (discrete units)
- Offline-first: primary operating mode, not fallback
- Phased roadmap: Phase 1 (Romaneo+Position), Phase 2 (Liquidaciones+WSLPG), Phase 3 (Canje+Agronomía), Phase 4 (AI)
- 5 personas: Dueño/Gerente, Balancero/Recibidor, Laboratorista, Administrador/Contable, Contador Rural

## Requirements

### Functional Requirements

**Module Decomposition (FR-001 through FR-008)**:

FR-001: RECEPCIÓN (Romaneo) module — truck arrival registration, CPE/CTG validation and confirmation, peso bruto capture from weighbridge, calado initiation, tara capture, peso neto calculation, boleta de romaneo generation with digital signature. Must specify offline flow (store-and-forward CPE confirmation when connectivity restores). Include state machine: PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO.

FR-002: CALIDAD module — grain sample analysis workflow, quality parameter capture per grain type (humedad, materias extrañas, granos dañados, quebrados, peso hectolítrico), grade determination against Cámara Arbitral tolerance tables: cereals (trigo, maíz, sorgo) use Grado 1/2/3 system with grade-based bonificación/rebaja; oleaginosas (soja, girasol) use tolerance-based progressive rebajas (NOT Grado 1/2/3). Merma calculation (zarandeo → secado → manipuleo → volátil in sequential order per CAC 10/86). Must specify configurable tolerance tables per plant.

FR-003: ALMACENAMIENTO module — silo/cell management with capacity and state tracking, grain assignment by type/quality/campaign, grain position report (posición de granos: qué hay, dónde está, de quién es), campaign year segregation, inter-silo movements, cubicaje (volumetric estimation) support.

FR-004: CUENTAS CORRIENTES module — producer account as dual-ledger (grain kg + monetary pesos/USD), movement history per producer per grain type, "a fijar" operation support (grain at zero monetary value until price-fixing event), extracto (statement) generation, automatic credit from romaneo peso neto conforme.

FR-005: LIQUIDACIONES module — Liquidación Primaria (1116-C) and Secundaria (1116-B) generation, price × kg calculation with all retention deductions (IVA at SISA-tier rate: 5%/8%/10.5%/16% per RG 2300, Ganancias at SISA-tier rate: 0%/2%/15%/30% per RG 4325, IIBB per province), WSLPG electronic filing, SICORE magnetic file generation, SISA status verification before settlement — the SISA query determines both IVA and Ganancias retention rates dynamically.

FR-006: FACTURACIÓN module — electronic invoices A/B/C for plant services (secada, zarandeo, almacenaje, paritaria), credit/debit notes, CAE online and CAEA offline modes. Reuse existing ARCA integration (already implemented in feature 001).

FR-007: AGRONOMÍA (Insumos) module — input catalog (seeds, fertilizers, agroquímicos, repuestos), stock by lot and expiry, purchases from distributors, sales to producers, price lists. This is discrete inventory (units, not kg).

FR-008: CANJE module — grain-for-input exchange workflow, automatic compensation (grain credit at pizarra price vs input debit), fiscal documentation generation (LPG + invoice), recording in producer cuenta corriente.

**User Stories (FR-009 through FR-013)**:

FR-009: Balancero/Recibidor stories — at minimum: (a) process a truck reception end-to-end in < 5 minutes during harvest peak, (b) continue processing romaneos when internet is down, (c) capture peso bruto/tara from integrated weighbridge without manual transcription.

FR-010: Laboratorista stories — at minimum: (a) grade a grain sample using tolerance tables without spreadsheets, (b) calculate merma automatically with the correct sequential formula, (c) handle a quality dispute by showing transparent calculation audit trail.

FR-011: Administrador/Contable stories — at minimum: (a) file a Liquidación 1116-C with automatic retention calculations, (b) generate SICORE magnetic files for all retentions in a period, (c) verify producer SISA status before settlement.

FR-012: Dueño/Gerente stories — at minimum: (a) view real-time grain position across all plants from mobile, (b) see producer account summary with outstanding balances, (c) monitor harvest throughput (trucks/hour) per plant.

FR-013: Contador Rural stories — at minimum: (a) view all client transactions in real-time without requesting files, (b) export fiscal summaries for multiple acopio clients, (c) verify retention calculations match SICORE obligations.

**Operational & Integration Requirements (FR-014 through FR-019)**:

FR-014: CPE/CTG integration — specify WSCPE methods per romaneo step (confirmarArriboCPE on arrival, confirmarDescargaCPE on closure), offline queue for confirmations, 5-day validity tracking, state machine alignment.

FR-015: Weighbridge integration — serial (RS-232) and IP protocol support, dual-scale workflow (primary for peso bruto, secondary for tara), automatic peso neto calculation, calibration data tracking.

FR-016: Offline-first requirements per module — specify which operations MUST work offline (romaneo, quality grading, storage assignment, producer account credit) vs which REQUIRE connectivity (CPE confirmation, WSLPG filing, SISA verification). Include CAEA mode for fiscal operations during outages.

FR-017: Campaign year management — campaign definition (typically April-March), grain segregation per campaign in all modules, campaign-based reporting, campaign transition workflow.

FR-018: Phased delivery specification — allocate each module and feature to a phase: Phase 1 (RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES), Phase 2 (LIQUIDACIONES, FACTURACIÓN extended), Phase 3 (CANJE, AGRONOMÍA), Phase 4 (AI features). Each phase must have clear entry/exit criteria.

FR-019: Preserve existing infrastructure summary — implementation status table, feature branch history (001-025), Rust module inventory, API contract inventory. This content validates that the PRD builds on a proven foundation.

### Non-Functional Requirements

NF-001: Document in English (primary language), Spanish domain terms used canonically (romaneo, merma, acopiador, cuenta corriente, liquidación, canje, calado, pizarra, balancero, laboratorista) with English translation on first use.

NF-002: All operational workflows must cite research document IDs (e.g., "[Research 2.1]", "[Research 8.3]").

NF-003: User stories must follow "As a [persona], I want [action], so that [outcome]" format with testable acceptance criteria.

NF-004: Include Mermaid diagrams for: functional decomposition (mindmap), romaneo lifecycle (state diagram), operational flow (flowchart), liquidación lifecycle (state diagram), module dependencies (graph).

NF-005: Consistent with `Product Vision & Scope.md` v1.0 (personas, modules, phases, differentiators) and `Descripción General del Producto.md` (module names and operational flow).

NF-006: Regulatory citations must include specific RG numbers (e.g., "RG 3419/2012", "RG 5689/2025") — no vague "ARCA regulations" references.

NF-007: Merma formula must show the exact sequential order (zarandeo → secado → manipuleo → volátil) with the mathematical formula and per-grain base values.

NF-008: Each module section must specify: what works offline, what requires connectivity, and what uses store-and-forward.

## Target Document Structure

```
1. Document Metadata
   - Version 1.0, Status: Acopio Vertical — Active Development
   - Implementation Progress table (preserved from v0.4)
   - Glossary of acopio-specific terms

2. Introduction
   2.1 Purpose (bridge between Vision and Engineering)
   2.2 Scope (acopio de granos — what this PRD covers)
   2.3 Upstream References (Vision v1.0, Descripción General)

3. Functional Decomposition
   3.1 Module Map (Mermaid mindmap — 8 acopio modules)
   3.2 Module Dependency Graph (which modules depend on which)
   3.3 Phase Allocation (which modules in which phase)

4. Module Specifications
   4.1 RECEPCIÓN (Romaneo)
       - Feature list, state machine, data capture fields
       - Offline flow, CPE/CTG integration points
       - User stories (Balancero)
   4.2 CALIDAD
       - Quality parameters per grain, tolerance tables, grades
       - Merma calculation (formula + sequential order)
       - User stories (Laboratorista)
   4.3 ALMACENAMIENTO
       - Silo management, grain position, campaign segregation
       - User stories (Dueño)
   4.4 CUENTAS CORRIENTES
       - Dual ledger (kg + pesos), "a fijar", extractos
       - User stories (Administrador)
   4.5 LIQUIDACIONES
       - 1116-B/C, retentions, WSLPG filing, SICORE
       - User stories (Administrador)
   4.6 FACTURACIÓN
       - Plant services invoicing, CAE/CAEA
       - Reuse existing ARCA infrastructure
   4.7 AGRONOMÍA (Insumos)
       - Input catalog, discrete inventory
   4.8 CANJE
       - Grain-for-input exchange, compensation, fiscal docs

5. Operational Workflows (Mermaid flowcharts)
   5.1 Romaneo-to-Position (complete flow with all 11 steps)
   5.2 Liquidación lifecycle
   5.3 Canje operation flow
   5.4 Campaign transition

6. Regulatory Compliance Specifications
   6.1 CPE/CTG (WSCPE methods, state machine, offline handling)
   6.2 WSLPG (1116-B/C filing, XML field requirements)
   6.3 SISA (RG 5689/2025, 24h registration, status verification)
   6.4 Retentions (IVA, Ganancias, IIBB calculations per liquidación)
   6.5 SICORE (magnetic file generation)

7. Hardware Integration
   7.1 Weighbridge (RS-232/IP, dual-scale workflow)
   7.2 Lab Equipment (moisture meters, optional)

8. Non-Functional Requirements
   8.1 Offline-First (per-module online/offline matrix)
   8.2 Performance (10 trucks/hour harvest throughput)
   8.3 Security (RLS, encryption, audit — per Vision)
   8.4 Sync (conflict resolution, latency targets)

9. Phased Delivery
   9.1 Phase 1: Romaneo-to-Position (MVP)
   9.2 Phase 2: Liquidaciones + WSLPG
   9.3 Phase 3: Canje + Agronomía
   9.4 Phase 4: AI Features
   Each phase: scope, entry criteria, exit criteria, success metrics

10. Implementation Foundation (preserved from v0.4)
    10.1 Existing infrastructure that carries forward
    10.2 Feature branch history (001-025)
    10.3 Rust module inventory
    10.4 API contract inventory
```

## Acceptance Criteria

AC-001: All 8 acopio modules specified with feature lists and data capture requirements
AC-002: Romaneo workflow includes all 11 steps from truck arrival to CPE closure with data fields per step
AC-003: Merma formula shows exact sequential order (zarandeo → secado → manipuleo → volátil) with CAC 10/86 citation and per-grain base values
AC-004: Quality grading specifies parameters for at least 5 grain types (trigo, maíz, soja, girasol, sorgo)
AC-005: Producer account specified as dual-ledger (kg + pesos) with "a fijar" and canje mechanics
AC-006: CPE/CTG integration specifies WSCPE methods per romaneo step with state transitions
AC-007: Liquidación specifies 1116-B/C forms with SISA-dependent retention calculations (IVA 5%/8%/10.5%/16% per RG 2300, Ganancias 0%/2%/15%/30% per RG 4325, IIBB per province) and WSLPG filing
AC-008: At minimum 3 user stories per persona (5 personas × 3 = 15+ stories) with acceptance criteria
AC-009: Offline/online matrix specifies per-module which operations work offline
AC-010: Phased delivery allocates every module to a phase with entry/exit criteria
AC-011: No references to "cajero", "cashier", "retail", "ferretería", "distribuidor", or generic POS remain
AC-012: All operational workflows cite research document IDs
AC-013: Feature branch history (001-025) preserved from v0.4
AC-014: Consistent with Product Vision & Scope v1.0 — same personas, modules, phases, differentiators
AC-015: At minimum 5 Mermaid diagrams (module map, romaneo state machine, operational flow, liquidación lifecycle, module dependencies)
AC-016: Weighbridge integration specified (RS-232/IP, dual-scale, offline capture)
AC-017: Campaign year management specified with lifecycle and segregation rules
AC-018: SISA integration specified (RG 5689/2025, 24h registration, status check before liquidación)

## Dependencies

- **Depends on**: spec-01 (Product Vision & Scope v1.0) ✅ COMPLETED
- **Blocks**: spec-03 (Data Model), spec-04 (ADR), spec-07 (Roadmap), spec-08a (ARCA Grain Guide), spec-08b (AI/ML Roadmap), spec-08c (SRS)
- **References**:
  - `Docs/Project Blueprint/Product Vision & Scope.md` v1.0 (vision, personas, phases, market)
  - `Docs/Project Blueprint/Descripción General del Producto.md` (module definitions, operational flow)
  - `Docs/Project Blueprint/PRD.md` v0.4 (implementation status tables to preserve)
  - Research docs: 2.1-2.6, 8.1-8.4, 1.1-1.6, 3.1-3.2
