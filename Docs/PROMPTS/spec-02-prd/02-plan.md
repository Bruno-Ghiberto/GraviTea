# Spec 02: Product Requirements Document (PRD) -- Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/PRD.md` v1.0
**Replaces**: Same file, v0.4 (2026-03-01, in Spanish, generic retail)
**Type**: Blueprint document (functional specification, not code)
**Spec reference**: `specs/002-acopio-prd/spec.md`

This plan guides the rewrite of the PRD from a generic horizontal ERP targeting
"PyMEs minoristas" to a comprehensive **acopio de granos** Product Requirements
Document. The output is a ~700-1000 line Markdown file with 10 major sections,
at least 5 Mermaid diagrams (SC-006), all 8 acopio modules specified with user
stories and acceptance criteria, and all regulatory citations with specific RG
numbers (SC-003).

The PRD is the **BRIDGE** between the Vision (spec-01) and engineering (spec-03+).
It says WHAT and HOW MUCH: feature specs, user stories, acceptance criteria,
operational workflows, regulatory detail, data capture requirements, hardware
integration. It does NOT repeat market sizing, competitive analysis, or pricing
strategy already in Vision v1.0.

---

## Content Guidelines

### Tone & Voice

- **Functional specification document** — not a sales pitch, not a technical manual
- Prescriptive and declarative: "The system MUST..." "The module MUST specify..."
- No hedging: eliminate "planificado", "bajo evaluación", "a determinar"
- Every regulatory claim cites a specific RG number and year (e.g., "RG 5689/2025")
- Testable: every acceptance criterion must be independently verifiable

### Audience

- **Primary**: Development team and AI agents (implement from this document alone)
- **Secondary**: Product owner / founder (scope and compliance decisions)
- **Tertiary**: Future technical reviewers (spec-03 data model, spec-04 ADRs)

### Language

- English is the primary language of the document
- Spanish domain terms used where they are the canonical industry terms:
  romaneo, merma, acopiador, cuenta corriente, liquidación, canje, boleta de
  romaneo, zarandeo, secado, fijación, pizarra, almacenaje, balancero,
  laboratorista, administrador
- First occurrence of each Spanish term includes English translation in parentheses
- Example: "romaneo (weighing ticket)" on first use, then just "romaneo" after
- Module names always in SPANISH CAPS: RECEPCIÓN, CALIDAD, ALMACENAMIENTO,
  CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE

### Level of Detail

- Module specifications: feature list + state machine + data fields + offline behavior
- State machines: named states with labeled transitions (not abstract boxes)
- User stories: minimum 3 per persona in Given/When/Then format
- Regulatory: cite RG number, year, and specific automated action vs user boundary
- Mermaid diagrams: functional and renderable (test in Markdown viewer)
- Data fields: field name, type, required/optional, source (weighbridge/manual/calculated)

---

## Existing Content: Preserve vs. Replace

### PRESERVE VERBATIM (copy exact from v0.4)

| v0.4 Section | Lines | Action | Notes |
|-------------|-------|--------|-------|
| §1 Implementation Progress table | 13-24 | **Preserve verbatim** | Backend/Rust/API/Frontend status; move to §10 |
| §3.2 Estado de Implementación | 98-120 | **Preserve verbatim** | 19-row feature branch table (001-025 + API Audit) |
| §4.3 ARCA integration (WSAA/WSFEv1) | 227-254 | **Preserve in §10** | ARCACredential, Comprobante, CAEA, QR Fiscal; reused by FACTURACIÓN |
| §4.4 Sync engine (SyncSession/PendingOperation) | 256-294 | **Preserve in §10** | State diagram + conflict resolution; applies to romaneo offline |
| §4.5 Personalización (custom fields JSONB) | 296-311 | **Preserve in §10** | TenantFieldDefinition, TenantModuleConfig, BusinessTemplate |
| §4.6 Auth JWT RS256 | 313-336 | **Preserve in §10** | Claims, rate limiting, Defense-in-Depth |
| §5.1 NFR-SEC (security) | 390-395 | **Preserve in §8** | AES-256-GCM, JWT, RLS, rate limiting |
| §5.2 NFR-PERF Rust benchmarks | 400 | **Preserve in §8** | 9 Rust modules, speedup figures |
| §5.3 NFR-EDGE | 403-406 | **Preserve in §8** | ARCA OBSERVADO, offline stock, fail-closed encryption |
| §7 item 4 (certificates) | 434 | **Preserve in §8/§9** | Client manages ARCA cert renewal; system alerts |
| §7 item 6 (dual-environment) | 435 | **Preserve in §8** | Next.js current + Electron planned; not to be confused |

### ADAPT (update context, keep structure)

| v0.4 Section | Lines | Action | Notes |
|-------------|-------|--------|-------|
| §1 Metadata table | 3-12 | **Adapt** | Version → 1.0; Status → "Acopio Vertical — Active Development"; date → current |
| §2.1 Glossary | 33-53 | **Adapt** | Keep: Tenant, TenantBoundModel, CAE/CAEA, Ledger, RLS, PII, Defense-in-Depth; ADD: romaneo, merma, CPE, SISA, pizarra, fijación, liquidación, CEG, LPG, posición consolidada |
| §5.2 NFR-PERF | 396-400 | **Adapt** | Replace POS latency targets with acopio targets (< 5 min/truck, < 60s sync); keep Rust acceleration table |
| §7 Supuestos | 429-436 | **Adapt** | Replace POS/retail hardware with weighbridge + connectivity assumptions; keep certificates + dual-environment |

### REPLACE COMPLETELY (new content replaces old)

| v0.4 Section | Why Replace |
|-------------|-------------|
| §1 "Nota estratégica" box (line 26-27) | "Evaluating 4 niches" → committed acopio |
| §2 Introduction body | "PyMEs minoristas" → acopio de granos operators |
| §3.1 Functional Architecture mindmap | Generic retail (Ventas, Inventario, Compras) → 8 acopio modules |
| §4.1 Ventas module (POS-01/02/03, SaleOrder) | Retail sales flow → RECEPCIÓN (Romaneo) module |
| §4.2 Inventario module (StockMovement, BranchStock) | Generic stock → ALMACENAMIENTO (Silo/Celda) module |
| §4.7 Clientes module | Generic CRM → absorbed into CUENTAS CORRIENTES (Productor) |
| §4.8 Compras partial | Generic procurement → AGRONOMÍA (Insumos) module |
| §4.9 Reportes (planned) | Generic reports → acopio-specific reports |
| §6 Traceability Matrix | Retail requirements → FR-001 to FR-019 acopio matrix |

### NEW SECTIONS (do not exist in v0.4)

| New Section | Source | Notes |
|-------------|--------|-------|
| §4.2 CALIDAD | Research 2.2 + RAG | Quality grading, tolerance tables, merma formula |
| §4.4 CUENTAS CORRIENTES | Research 2.3 + RAG | Dual ledger, CEG/LPG, fijación, posición consolidada |
| §4.5 LIQUIDACIONES | Research 5.1 + RAG | 1116-C/B, SISA-tier retentions, WSLPG, SICORE |
| §4.8 CANJE | Research 2.3 + RAG | Grain-for-input exchange, LPG + invoice |
| §5 Operational Workflows | spec.md US-5 + Research 2.1 | Romaneo flow, fijación flow, campaign transition |
| §6 Regulatory Compliance | Research 5.1 + 1.x RAG | CPE/CTG, WSLPG, SISA, retentions per RG |
| §7 Hardware Integration | Research 3.1 + spec.md FR-015 | Weighbridge RS-232/TCP + dual-scale behavior |
| §9 Phased Delivery | spec.md FR-018 | 4 phases with entry/exit criteria per module |

---

## Section-by-Section Writing Plan

### Section 1: Document Metadata
**Effort**: Small (copy-adapt from v0.4)
**Source**: v0.4 §1 (lines 3-27)
**Action**:
- Copy metadata table structure from v0.4
- Update: Version → 1.0, Status → "Acopio de Granos Vertical — Active Development", date → current
- Add: Owner "Bruno Ghiberto", Spec Reference → spec-02 + Vision v1.0
- Remove the "Nota estratégica" box about "evaluating 4 niches" (line 26-27)
- **Move** Implementation Progress table to §10 (Implementation Foundation)
  — reference it from §1 with a link: "See §10 for implementation progress"

**RAG queries**: None needed

---

### Section 2: Introduction
**Effort**: Small-Medium
**Source**: v0.4 §2 (adapt) + Vision v1.0 §1 (context)

**2.1 Purpose Statement**
- Replace "plataforma de gestión integral para PyMEs minoristas" with:
  "GRAVITEA ERP is the functional specification for an acopio de granos
  (grain collection and storage) management platform targeting independent
  Argentine acopiadores. This PRD translates the strategic vision (spec-01)
  into implementable requirements for 8 functional modules."
- State explicitly: PRD covers WHAT and HOW MUCH. Vision covers WHY and MARKET.
- Cross-reference Vision v1.0 for: personas, market sizing, pricing, roadmap rationale

**2.2 Glossary (Adapt)**
- KEEP from v0.4: Tenant, TenantBoundModel, CAE, CAEA, Ledger, RLS, PII, Defense-in-Depth, DRF, Blind Index
- REMOVE from v0.4: BranchStock (replaced by Posición), SaleOrder, Cajero, Comprobante (keep but re-scope to FACTURACIÓN)
- ADD acopio terms:

| Term | Definition |
|------|-----------|
| Romaneo | Weighing ticket — the atomic transaction recording a truck's grain reception |
| CPE | Carta de Porte Electrónica — mandatory electronic waybill per WSCPE |
| CTG | Código de Trazabilidad de Granos — truck grain traceability code |
| Merma | Measurable grain loss (% deduction) from impurities, humidity, manipulation |
| Pizarra | Published grain market price per ton/quintal at a given moment |
| Fijación | Price-crystallization event for "a fijar" grain at current pizarra |
| CEG | Certificado de Existencia de Granos — grain deposit certificate |
| LPG | Liquidación Primaria de Granos — Form 1116-C settlement |
| SISA | Registro Sistémico de la Actividad Agropecuaria (RG 5689/2025) |
| WSLPG | Web Service Liquidaciones Primarias de Granos (ARCA) |
| WSCPE | Web Service Carta de Porte Electrónica (ARCA) |
| Posición Consolidada | Cross-plant aggregated producer account view (derived, not stored) |

**RAG queries**: None needed (internal domain vocabulary)

---

### Section 3: Functional Decomposition
**Effort**: Medium
**Source**: Descripción General del Producto + spec.md FR-001 to FR-008

**3.1 Functional Architecture (Mermaid mindmap)**
- NEW Mermaid mindmap replacing v0.4's generic retail mindmap
- Root: GRAVITEA ERP Acopio
- 8 branches (one per module): RECEPCIÓN, CALIDAD, ALMACENAMIENTO,
  CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE
- Each branch: 3-4 sub-items listing key features
- Cross-cutting branches: Plataforma (Auth, Sync, Rust, RLS), Reportes, Administración

**3.2 Implementation Status (PRESERVE VERBATIM)**
- Copy §3.2 table from v0.4 lines 98-120 EXACTLY as-is
- Add a header note: "Acopio modules (§4.1–§4.8) specify new functionality
  built on top of this infrastructure. Modules FR-001–FR-008 are not yet
  in the implementation table above — they will be added as feature branches
  are created."
- Do NOT edit individual rows

**3.3 Module Dependency Graph (Mermaid)**
- NEW graph diagram (does not exist in v0.4)
- Directional edges per spec.md US-5 acceptance scenario 3:
  - RECEPCIÓN → ALMACENAMIENTO
  - RECEPCIÓN → CALIDAD
  - CALIDAD → CUENTAS CORRIENTES
  - CUENTAS CORRIENTES → LIQUIDACIONES
  - LIQUIDACIONES → FACTURACIÓN
  - CUENTAS CORRIENTES → CANJE
  - CANJE → AGRONOMÍA
- Platform layer (Auth, Sync, ARCA) shown as foundation used by all modules

**RAG queries**:
- `"day to day operations acopiador complete workflow 10 steps"`

---

### Section 4: Module Specifications
**Effort**: Very Large (8 modules — heaviest section of the PRD)
**Source**: Research 2.x + 3.x + spec.md FR-001 to FR-013 + RAG results

Each module follows this template:
```
### §4.X MODULE NAME
**Phase**: [1/2/3/4]  **Priority**: [P0/P1/P2]

**Feature List**: (bullet list of capabilities)
**State Machine**: (Mermaid stateDiagram-v2 if applicable)
**Data Capture**: (key fields with type, source, required/optional)
**Offline Behavior**: (from online/offline matrix FR-016)
**User Stories** (minimum 3, persona-tagged, Given/When/Then)
**Acceptance Criteria** (numbered, testable)
```

#### §4.1 RECEPCIÓN (Romaneo) — Phase 1, P0
**RAG queries**:
- `"romaneo workflow steps truck arrival weighbridge reception grain quality"`
- `"romaneo data fields peso bruto tara neto ERP capture document structure"`
- `"CPE CTG lifecycle states WSCPE confirmation arribo definitiva"`

**Content to produce**:
- Feature list: CPE/CTG arrival registration, weighbridge weight capture (peso bruto), tara capture, peso neto = peso bruto − tara, quality sample handoff, 6-state machine, boleta de romaneo (digital), offline store-and-forward CPE queue
- State machine: PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO with labeled transitions
- Data fields: CPE number, grain type (ARCA code), campaign year, truck plate, driver, producer CUIT, origin party, destination party, peso bruto (kg from scale), tara (kg from scale), peso neto (calculated), quality sample ID, silo assignment, romaneo date/time
- Offline behavior: romaneo fully offline except CPE confirmation — confirmarArriboCPE queued; confirmed when connectivity restores before CPE definitive closure
- CPE integration: WSCPE methods per step:
  - EN_PROCESO: `confirmarArriboCPE` (registers physical truck arrival at destination)
  - CERRADO (two-step): `descargadoDestinoCPE` (records unloading) → `confirmacionDefinitivaCPEAutomotor` (sends final gross/tare; ARCA computes net and closes CTG)
- Acceptance criteria per FR-001 + spec.md US-1 AC-1

#### §4.2 CALIDAD (Quality) — Phase 1, P1
**RAG queries**:
- `"grain quality parameters humidity moisture bonification rebaja tolerance tables"`
- `"merma calculation formula secado zarandeo volatil manipuleo sequential"`
- `"grain types codes ARCA humidity base quality parameters reference"`

**Content to produce**:
- Feature list: sample grading by grain type, two grading systems (Grado 1/2/3 for cereals; tolerance-based progressive rebajas for oleaginosas), merma calculation engine, Hf table for secado, configurable tolerance tables per plant, on-demand audit trail
- Merma formula (mandatory sequential order per CAC Circular 10/86 + Resolución JNG N° 22027/81):
  `Peso_final = Peso_bruto × (1 − %Z) × (1 − %S) × (1 − %M) × (1 − %V)`
  where Z=zarandeo, S=secado, M=manipuleo, V=volátil — each step applied to weight result of previous step (multiplicative chain)
- Fixed merma values to inline in PRD (use these directly):
  - Manipuleo: trigo 0.10%; maíz/soja 0.25%; girasol 0.20%
  - Volátil: cereales (trigo, maíz, avena, cebada, centeno) 0.30%; oleaginosas (soja, girasol) 0.50%
- Key distinction: cereals (trigo, maíz, sorgo) use Grado 1/2/3 classification (Grado 1 = bonificación, Grado 2 = base, Grado 3 = rebaja, Fuera de Estándar); oleaginosas (soja, girasol) use tolerance-based progressive rebajas — NOT the Grado scale
- Secado Hf table: secado deduction = (Hi − Hf) / (100 − Hf) × Peso_bruto per grain type
- Tolerance tables: configurable per plant (parameters vary by region/agreement — IIEE publishes national base tables; local variation applies)
- Quality determination: Grado or rebaja assignment based on worst measured parameter
- ERP data capture per merma step: grain type, % merma per concept (zarandeo/secado/manipuleo/volátil), kg deducted per concept, peso result after each step, final peso neto conforme
- Audit trail: all inputs (grain type, Hi, actual parameter values), tolerance tables applied, merma breakdown per step, final peso neto conforme — accessible on demand per romaneo; supports external escalation to Cámara Arbitral de Cereales (CAC) if producer disputes
- User stories per FR-010 (Laboratorista): grading workflow, automated merma, audit trail access

#### §4.3 ALMACENAMIENTO (Storage) — Phase 1, P1
**RAG queries**:
- `"grain silo storage cell management assignment campaign year segregation"`
- `"campaign year management agricultural cosecha segregation grain"`

**Content to produce**:
- Feature list: silo and celda (cell) management, grain lot assignment (grain type + quality + campaign + producer), grain position report, inter-silo movements, cubicaje (volumetric estimation), campaign year logical segregation
- Storage unit types: vertical silo, horizontal celda, wet bin (secadero bin)
- Composite key: plant → grain type → campaign year → producer (per RG 3593)
- Grain position report: at any time, system can answer "what grain is where" (type, quality grade, kg, producer CUIT, campaign)
- Campaign transition: admin defines new campaign code; system tags all subsequent romaneos with it; generates carry-stock report for prior campaign grain (supports AFIP manual declaration)
- Acceptance criteria per FR-003 + FR-017

#### §4.4 CUENTAS CORRIENTES (Producer Account) — Phase 1, P0
**RAG queries**:
- `"producer current account balance structure cuenta corriente grain kg pesos"`
- `"canje grain barter exchange supplies insumos producer accounting"`
- `"CEG LPG grain deposit certificate withdrawal settlement document structure"`

**Content to produce**:
- Feature list: dual ledger (kg grain sub-ledger + pesos/USD monetary sub-ledger), transaction catalog, "a fijar" mechanics, extracto (statement), posición consolidada
- Dual ledger: per-plant is the source of truth; each sub-ledger is append-only (immutable ledger pattern from platform)
- Transaction type catalog (with document type per each):
  - CEG (Certificado de Existencia de Granos) → grain deposit credit
  - LPG / Form 1116-C (Liquidación) → grain debit + monetary credit
  - Cert. Retiro → grain debit (physical withdrawal)
  - F.2005/SIRE → retention certificate (monetary debit)
  - Service charges (secada, zarandeo, almacenaje, paritaria) → monetary debit
  - Canje entry → grain debit + insumo credit offset
  - Fijación record → crystallizes monetary value of "a fijar" grain
- "A fijar" mechanics: grain enters at zero monetary value; producer contacts acopiador → administrador creates fijación record at current pizarra price → LPG is generated → monetary sub-ledger credited
- Posición consolidada: derived view aggregating per-plant ledgers for same producer CUIT across all plants of the tenant — shown on Dueño/Gerente dashboard
- Extracto: filterable by grain type, campaign, date range; shows all transactions with document reference
- User stories per FR-012 (Dueño): cross-plant posición consolidada, mobile grain position

#### §4.5 LIQUIDACIONES (Settlement) — Phase 2, P0
**RAG queries**:
- `"liquidacion primaria secundaria Form 1116 B C grain settlement WSLPG"`
- `"IVA retention 8% RG 2300 ganancias IIBB withholding grain calculation"`
- `"SISA registro sistemico RG 5689 2025 grain registration 24 hours"`

**Content to produce**:
- Feature list: Liquidación Primaria (Form 1116-C), Liquidación Secundaria (Form 1116-B), SISA-tier retention tables, WSLPG electronic filing, SICORE magnetic file, pre-liquidación SISA blocking gate
- Form types:
  - 1116-C: Primaria — acopiador pays producer for grain (acopiador-to-producer)
  - 1116-B: Secundaria — acopiador sells to buyer (acopiador-to-buyer)
- SISA-tier retention tables (FR-005):
  - IVA: 5% (Estado 1 — high compliance) / 8% (Estado 2 — medium) / 10.5% (Estado 3 — low) / 16% (non-registered) per RG 2300
  - Ganancias: 0% / 2% / 15% / 30% per RG 4325 (grain-specific tiers)
  - IIBB: per-province rate (configurable)
- SISA blocking gate: before liquidación can proceed, system queries SISA status for producer CUIT; result determines retention tier; settlement blocked if query fails
- WSLPG: electronic filing of Form 1116-C/B via ARCA web service after all retentions computed
- SICORE: magnetic file for periodic retention reporting to ARCA
- Liquidación state machine: DRAFT → RETENCION_CALCULADA → SISA_VERIFICADA → WSLPG_PRESENTADA → LIQUIDADA
- User stories per FR-011 (Administrador/Contable): SISA-tier calculation, SICORE file, 1116-C workflow

#### §4.6 FACTURACIÓN (Invoicing) — Phase 2, P1
**Source**: Reuse existing ARCA infrastructure (feature branch 001)

**Content to produce**:
- Feature list: electronic invoices A/B/C for plant services, credit/debit notes, CAE (online) and CAEA (offline)
- **NOTE**: Core ARCA infrastructure (WSAA + WSFEv1, ARCACredential, Comprobante ledger, QR fiscal) is implemented and preserved in §10. This module specifies only the acopio-specific service types that use that infrastructure.
- Acopio service types (new concepts not in v0.4):
  - Secada (drying service) — charged per ton, billed separately from grain purchase
  - Zarandeo (sieving service) — charged per ton
  - Almacenaje (storage service) — charged per ton-month or per quintal
  - Paritaria (inbound handling fee) — charged per ton on arrival
- Invoice generation: triggered by service charges accumulation or explicit billing cycle
- Credit/debit notes: for service corrections
- CAEA mode: acopio plants may be in connectivity-limited environments; CAEA covers offline billing
- Cross-reference FR-006 + A-006 (reuse of branch 001 infrastructure)

#### §4.7 AGRONOMÍA (Insumos) — Phase 3, P2
**Source**: Research 2.3 partial + spec.md FR-007

**Content to produce**:
- Feature list: input catalog (seeds, fertilizers, agroquímicos, repuestos), discrete inventory (units/kg, not continuous grain kg), stock by lot and expiry, purchases from distributors, sales to producers, price lists
- Inventory type distinction: AGRONOMÍA uses discrete lot-controlled inventory (different model from grain position)
- Price lists: configurable per product, per season, per producer tier
- Expiry tracking: mandatory for agroquímicos and fertilizers
- Acceptance criteria per FR-007

#### §4.8 CANJE (Grain-for-Input Exchange) — Phase 3, P2
**RAG queries**:
- `"canje grain barter exchange supplies insumos producer accounting"`

**Content to produce**:
- Feature list: grain-for-input exchange workflow, automatic compensation at pizarra price, fiscal documentation, cuenta corriente entries
- Workflow: producer requests input → system calculates kg of grain equivalent at current pizarra → creates grain debit in cuenta corriente + insumo delivery record → LPG generated (grain purchase leg) + invoice issued (input sale leg)
- Both fiscal documents (LPG + invoice) must be generated and filed
- All entries recorded in producer cuenta corriente (grain sub-ledger debit, insumo charge debit offset by insumo credit)
- Acceptance criteria per FR-008

---

### Section 5: Operational Workflows
**Effort**: Medium
**Source**: Research 2.1 + spec.md US-5 + RAG

**5.1 Complete Romaneo Operational Flow (Mermaid flowchart)**
- NEW diagram showing all 11 romaneo steps from truck arrival to CPE closure
- Steps (per Research 2.1 acopiador day-to-day workflow):
  1. Truck arrives at plant
  2. CPE/CTG arrival registration (confirmarArriboCPE — queued if offline)
  3. Gross weight capture (primary scale → peso bruto)
  4. Lab sample collection
  5. Tara capture (secondary scale → truck weight empty)
  6. Peso neto calculation (peso bruto − tara)
  7. Quality sample analysis (CALIDAD module)
  8. Merma calculation (sequential: zarandeo → secado → manipuleo → volátil)
  9. Peso neto conforme assignment
  10. Boleta de romaneo generation (digital) + silo assignment (ALMACENAMIENTO)
  11. Producer account credit (CUENTAS CORRIENTES — CEG issued) + CPE closure (`descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor`)
- Fork after step 10: parallel paths to ALMACENAMIENTO and CUENTAS CORRIENTES
- Offline path annotation: steps 1-9 fully offline; steps 2 and 11 store-and-forward

**5.2 "A Fijar" Price-Fixing Flow**
- Short flowchart: Producer contacts acopiador → administrador opens fijación screen → selects grain type + campaign + kg quantity → system shows current pizarra price → administrador confirms → system generates LPG at confirmed price → cuenta corriente monetary credit created
- State: grain was in cuenta corriente with zero monetary value; after fijación it has a crystallized value

**5.3 Campaign Year Transition Workflow**
- Step description (not a full diagram): Admin navigates to campaign settings → defines new campaign code (e.g., "2025/26") → system uses new code for all subsequent romaneos → admin triggers carry-stock report (identifies grain from prior campaign still in storage) → operator uses report to prepare manual AFIP stock declaration (external step)
- Formal AFIP submission is outside the system scope

---

### Section 6: Regulatory Compliance Specifications
**Effort**: Large (most domain-critical section for compliance)
**Source**: Research 5.1 + 1.x + spec.md FR-014 + RAG

**6.1 CPE/CTG Integration (FR-014)**
**RAG queries**:
- `"CPE CTG lifecycle states WSCPE confirmation arribo definitiva"`
- `"CTG document structure state machine fields transitions"`

Content: WSCPE method catalog per romaneo step, offline store-and-forward, 5-day validity, state machine aligned with romaneo states:
- CPE state machine (Mermaid): Activa (5-day window) → Arribo (`confirmarArriboCPE`) → Descargada (`descargadoDestinoCPE`) → Confirmada Definitiva (`confirmacionDefinitivaCPEAutomotor` — sends final gross/tare; ARCA computes net peso)
- 1 CPE = 1 truck = 1 romaneo (bijection)
- WSCPE methods mapped to romaneo steps:
  - EN_PROCESO: `confirmarArriboCPE`
  - CERRADO step 1: `descargadoDestinoCPE` (records unloading event)
  - CERRADO step 2: `confirmacionDefinitivaCPEAutomotor` (final peso bruto/tara required; ARCA closes CTG)
- Offline behavior: store-and-forward queue; system tracks pending CPE operations; connectivity restored → auto-submit in order

**6.2 WSLPG Settlement Filing (FR-005)**
**RAG queries**:
- `"liquidacion primaria secundaria Form 1116 B C grain settlement WSLPG"`
- `"Form 1116 B-C XML field structure types lengths WSLPG"`

Content: Both Form 1116-C (Primaria) and 1116-B (Secundaria); automated action vs user confirmation boundary:
- Automated: retention calculation, SISA tier lookup, form field population
- User confirmation required: final approval before WSLPG submission
- SICORE: magnetic file format per ARCA spec; generated after period closing
- RG citations: RG 3419/2012, RG 3690/2014, RG 3691/2014 for WSLPG

**6.3 SISA Compliance (FR-005)**
**RAG queries**:
- `"SISA registro sistemico RG 5689 2025 grain registration 24 hours"`

Content: RG 5689/2025 cited explicitly; 24-hour grain movement registration requirement; pre-liquidación SISA query as blocking gate:
- System queries SISA for producer CUIT before each liquidación
- SISA result determines retention tier (Estado 1/2/3 or non-registered)
- Settlement BLOCKED if SISA query fails or returns "Inhabilitado"
- 24-hour rule: grain movements must be registered within 24 hours (affects romaneo timestamp requirements)

**6.4 Retention Calculation Reference (FR-005)**
Complete reference tables (must appear verbatim in PRD):

IVA Retention (RG 2300):
| SISA Estado | Rate | Note |
|------------|------|------|
| Estado 1 (High Compliance) | 5% | Most common for established producers |
| Estado 2 (Medium) | 8% | |
| Estado 3 (Low) | 10.5% | |
| Non-registered | 16% | Unregistered in SISA |

Ganancias Retention (RG 4325 — grain-specific):
| SISA Estado | Rate |
|------------|------|
| Estado 1 | 0% |
| Estado 2 | 2% |
| Estado 3 | 15% |
| Non-registered | 30% |

IIBB: per-province rate, configurable by tenant admin (not a federal table)

---

### Section 7: Hardware Integration
**Effort**: Small-Medium
**Source**: Research 3.1 + spec.md FR-015 + clarification Q5 (interface-level only)
**RAG queries**:
- `"weighbridge RS-232 serial interface integration grain scale ERP"`
- `"grain scale weighbridge calibration stability detection dual scale"`

Content: Supported interfaces (RS-232 serial + TCP/IP via converter bridge), dual-scale workflow, stability detection, calibration tracking. NO brand names, baud rates, or frame formats (those belong in spec-08c SRS).

**7.1 Supported Interfaces**
- RS-232 serial: direct connection to scale indicator
- TCP/IP: via RS-232-to-TCP converter bridge (e.g., Moxa NPort — do not name brand in PRD); same logical interface
- Both interface types expose the same application-level behavior

**7.2 Dual-Scale Workflow**
- Primary scale: captures peso bruto (full truck)
- Secondary scale: captures tara (empty truck after unloading)
- System: peso neto = peso bruto − tara (calculated, not captured from scale)
- Alternative tara modes: fixed tara per truck plate (stored) or manual entry fallback
- Stability detection: system only captures weight when scale sends a "stable" signal; does not capture fluctuating readings

**7.3 Calibration Tracking**
- Each scale has a calibration record: last calibration date, calibration certificate number, next due date
- System alerts when calibration is approaching expiry
- Calibration dates are recorded against each romaneo (audit trail)

---

### Section 8: Non-Functional Requirements (NFRs)
**Effort**: Medium (adapt §5 from v0.4 + add acopio-specific)
**Source**: v0.4 §5 (adapt) + spec.md FR-016 + spec.md SC-010

**8.1 Per-Module Online/Offline Matrix (FR-016)**
- NEW — the primary acopio-specific NFR section
- Three categories per module operation:

| Module | Operation | Classification |
|--------|-----------|---------------|
| RECEPCIÓN | Romaneo creation, weight capture, quality handoff | Offline |
| RECEPCIÓN | CPE confirmarArriboCPE | Store-and-forward |
| RECEPCIÓN | CPE descargadoDestinoCPE + confirmacionDefinitivaCPEAutomotor | Store-and-forward |
| CALIDAD | Sample grading, merma calculation | Offline |
| ALMACENAMIENTO | Silo assignment, grain movement | Offline |
| CUENTAS CORRIENTES | Account credit, extracto generation | Offline |
| CUENTAS CORRIENTES | Posición consolidada (cross-plant) | Connectivity-required |
| LIQUIDACIONES | Retention calculation | Offline |
| LIQUIDACIONES | SISA status query | Connectivity-required |
| LIQUIDACIONES | WSLPG filing | Connectivity-required |
| FACTURACIÓN | CAE issuance | Store-and-forward (CAEA mode) |
| AGRONOMÍA | Catalog, inventory, sales | Offline |
| CANJE | Exchange calculation, cuenta entries | Offline |

**8.2 Performance NFRs (Adapt from v0.4 §5.2)**
- Preserve Rust acceleration table (NFR-PERF-05): AES-256-GCM 8.7x, IVA 4.4x, CUIT 3.1x, etc.
- Add acopio-specific targets:
  - NFR-PERF-06: Full romaneo processing (weight to boleta) must complete in < 5 minutes during harvest peak
  - NFR-PERF-07: Sync latency for offline operations must not exceed 60 seconds when connectivity restores
  - NFR-PERF-08: CALIDAD merma calculation must return result in < 2 seconds for any grain type input
  - NFR-PERF-09: Posición consolidada query across all plants of a tenant must return in < 5 seconds

**8.3 Security NFRs (Preserve from v0.4 §5.1)**
- Preserve NFR-SEC-01 through NFR-SEC-04 verbatim
- Add: Producer CUIT and financial data (cuenta corriente amounts) are PII — must be encrypted at rest

**8.4 Edge Case NFRs (Preserve from v0.4 §5.3)**
- Preserve NFR-EDGE-01 (ARCA OBSERVADO), NFR-EDGE-02 (offline stock), NFR-EDGE-03 (fail-closed encryption), NFR-EDGE-04 (idempotent sync) verbatim
- Add acopio edge cases:
  - NFR-EDGE-05: If CPE arrives offline and connectivity never restores before the 5-day CPE validity expires, system alerts operator; romaneo remains in ANALIZADO state; no data loss
  - NFR-EDGE-06: If SISA query fails (service unavailable), system blocks settlement and shows last known SISA status with timestamp; operator can override with documented acknowledgment
  - NFR-EDGE-07: Merma deductions that result in peso neto conforme ≤ 0 must fail with explicit error — not silently produce negative weight

---

### Section 9: Phased Delivery
**Effort**: Small (clear from spec.md FR-018 + Vision v1.0)
**Source**: spec.md FR-018 + Vision v1.0 Phase allocation

**Phase 1: Romaneo-to-Position Loop (MVP)**
- Modules: RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES
- Entry criteria: infrastructure (Auth, Sync, Rust, ARCA) deployed; at least one pilot acopiador identified
- Exit criteria: "first real truck reception processed end-to-end on a pilot plant" — truck arrives → romaneo completed → silo assigned → producer account credited → boleta de romaneo generated
- Key features: weighbridge integration, offline CPE queue, dual-ledger producer account, boleta digital
- NOT included: settlement, invoicing, insumos, canje

**Phase 2: Fiscal Settlement Loop**
- Modules: LIQUIDACIONES, FACTURACIÓN (service invoicing)
- Entry criteria: Phase 1 stable and running with real data from ≥ 1 pilot
- Exit criteria: first complete 1116-C Liquidación Primaria filed via WSLPG for a real producer
- Key features: SISA-tier retentions, WSLPG, SICORE, service invoicing (secada/zarandeo/almacenaje)
- Note: FACTURACIÓN platform (WSAA/WSFEv1/CAEA) already implemented; only service types are new

**Phase 3: Insumos and Canje**
- Modules: AGRONOMÍA, CANJE
- Entry criteria: Phase 2 stable; pilot has executed at least one settlement cycle
- Exit criteria: first canje operation creating both LPG and insumo invoice in same transaction
- Key features: input catalog, grain-for-input compensation, OCR document intelligence, weighbridge fraud detection
- Consistent with Vision v1.0 §4.7

**Phase 4: AI Features**
- Modules: AI Layer (cross-cutting, not a standalone module)
- Entry criteria: Phase 3 stable; sufficient historical data (≥ 1 full campaign)
- Exit criteria: quality degradation prediction model deployed and validated on real silo data
- Key features (per Research 9.1): quality degradation prediction, silo assignment optimization, price forecasting, predictive aeration scheduling, document intelligence
- Consistent with Vision v1.0 §4.7

---

### Section 10: Implementation Foundation
**Effort**: Small (preserve from v0.4)
**Source**: v0.4 §1 (Implementation Progress) + §3.2 + §4.3-§4.6 + §5.2 NFR-PERF-05 + §7

**Content**: All preserved infrastructure from v0.4 consolidated into one section:
- Implementation Progress table (was §1 Progreso de Implementación, lines 13-24)
- Feature branch history / Estado de Implementación (§3.2, lines 98-120) — VERBATIM
- ARCA integration details (§4.3) — WSAA/WSFEv1 sequence diagram, ARCACredential entity, CAEA, QR Fiscal
- Sync engine (§4.4) — state diagram, SyncSession/PendingOperation, conflict resolution
- Personalización (§4.5) — custom fields JSONB, TenantModuleConfig, BusinessTemplate
- Auth JWT RS256 (§4.6) — claims, rate limiting, Defense-in-Depth
- Rust acceleration benchmarks (§5.2 NFR-PERF-05)
- API contracts: 9 OpenAPI specs — 79 paths, 154 schemas, 137 operations
- Frame with header: "This section documents the existing technical foundation on which all 8 acopio modules (§4.1–§4.8) are built."

---

## Research-to-Section Mapping

| Research Doc | Sections Fed |
|-------------|-------------|
| 2.1 (Day-to-Day Acopiador) | §5.1 Operational Flow, §4.1 RECEPCIÓN feature list |
| 2.2 (Quality Management) | §4.2 CALIDAD (grading systems, tolerance tables, merma formula) |
| 2.3 (Producer Current Accounts) | §4.4 CUENTAS CORRIENTES (dual ledger, CEG/LPG/SIRE docs) |
| 2.4 (Pricing, Contracts) | §4.4 "a fijar" mechanics, §4.5 pizarra price reference |
| 2.5 (Merma Calculations) | §4.2 CALIDAD (merma formula, Hf table, CAC 10/86) |
| 2.6 (Campaign Management) | §4.3 ALMACENAMIENTO (campaign segregation, RG 3593) |
| 3.1 (Weighbridge) | §7 Hardware Integration (RS-232, TCP/IP, dual-scale) |
| 5.1 (WSLPG Technical API) | §4.5 LIQUIDACIONES, §6.2 WSLPG, §6.4 retention tables |
| 8.3 (Romaneo Structure) | §4.1 RECEPCIÓN data fields |
| 8.4 (Form 1116 B-C) | §4.5 LIQUIDACIONES form fields, §6.2 WSLPG |
| 9.1 (AI/ML) | §9 Phase 4 AI features |
| v0.4 PRD | §10 Implementation Foundation (all preserved sections) |
| Vision v1.0 | §9 Phase allocation, §2 Introduction (do not duplicate) |
| Descripción General | §3.1 Functional Decomposition mindmap, §4 module names |

### RAG Query Schedule

Run these queries before writing the corresponding section.
Do NOT read full research PDFs — use RAG only.

```bash
# Operations — Core domain (§4.1, §4.2, §5.1)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo workflow steps truck arrival weighbridge reception grain quality" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo data fields peso bruto tara neto ERP capture document structure" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "day to day operations acopiador complete workflow 10 steps" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity moisture bonification rebaja tolerance tables" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula secado zarandeo volatil manipuleo sequential" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types codes ARCA humidity base quality parameters reference" -l 5

# Producer Account (§4.4)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account balance structure cuenta corriente grain kg pesos" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "CEG LPG grain deposit certificate withdrawal settlement document structure" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "canje grain barter exchange supplies insumos producer accounting" -l 5

# Regulatory (§4.5, §6.x)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "CPE CTG lifecycle states WSCPE confirmation arribo definitiva" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "liquidacion primaria secundaria Form 1116 B C grain settlement WSLPG" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "IVA retention RG 2300 ganancias RG 4325 IIBB withholding grain calculation" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "SISA registro sistemico RG 5689 2025 grain registration 24 hours" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "Form 1116 B-C XML field structure types lengths WSLPG" -l 5

# Storage and Campaign (§4.3)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "campaign year management agricultural cosecha segregation grain" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain silo storage cell management assignment campaign year segregation" -l 5

# Hardware (§7)
.venv/bin/python scripts/qdrant/qdrant_search.py -q "weighbridge RS-232 serial interface integration grain scale ERP" -l 5
```

---

## Mermaid Diagrams Required (minimum 5 — SC-006)

| # | Diagram | Type | Section | Notes |
|---|---------|------|---------|-------|
| 1 | Functional Architecture mindmap | mindmap | §3.1 | 8 acopio modules + Platform + AI |
| 2 | Romaneo state machine | stateDiagram-v2 | §4.1 | 6 states: PENDIENTE→EN_PROCESO→PESADO→ANALIZADO→CONFORME→CERRADO with offline path |
| 3 | Complete Romaneo Operational Flow | flowchart | §5.1 | All 11 steps from truck arrival to CPE closure; fork to ALMACENAMIENTO + CUENTAS CORRIENTES |
| 4 | Liquidación lifecycle | stateDiagram-v2 | §4.5 | DRAFT→RETENCION_CALCULADA→SISA_VERIFICADA→WSLPG_PRESENTADA→LIQUIDADA |
| 5 | Module Dependency Graph | graph LR | §3.3 | Directional edges between 8 modules + platform foundation |

Optional (recommended for completeness):

| # | Diagram | Type | Section | Notes |
|---|---------|------|---------|-------|
| 6 | CPE lifecycle | stateDiagram-v2 | §6.1 | Activa→Arribo→Descargada→Confirmada Definitiva |
| 7 | "A Fijar" fijación flow | flowchart | §5.2 | Short: producer contacts → admin records → LPG generated |

---

## Checkpoint Gates

### Gate 1: After §1-§2 (Metadata + Introduction)
- [ ] Version updated to 1.0; status changed to "Acopio de Granos Vertical — Active Development"
- [ ] "Nota estratégica" box about "evaluating 4 niches" REMOVED
- [ ] Introduction says "acopio de granos" not "PyMEs minoristas"
- [ ] Glossary includes all acopio terms: romaneo, CPE, merma, pizarra, fijación, CEG, LPG, SISA, WSLPG, posición consolidada
- [ ] Glossary retains all platform terms: TenantBoundModel, CAE/CAEA, Ledger, RLS, Defense-in-Depth
- [ ] No strategic duplication: introduction cross-references Vision v1.0 instead of repeating personas/market/pricing

### Gate 2: After §3 (Functional Decomposition)
- [ ] §3.1 mindmap renders correctly with 8 acopio modules (not generic retail)
- [ ] §3.2 implementation status table copied VERBATIM from v0.4 (19 rows, branches 001-025 + API Audit)
- [ ] §3.3 module dependency graph renders correctly with all 7 directional edges per spec.md US-5 AC-3
- [ ] Zero occurrences of "Ventas", "Inventario", "Cajero", "BranchStock", "SaleOrder" in §3.1 (replaced)

### Gate 3: After §4.1-§4.4 (Modules — Phase 1)
- [ ] §4.1 RECEPCIÓN: 6-state machine (PENDIENTE→EN_PROCESO→PESADO→ANALIZADO→CONFORME→CERRADO) present and rendered
- [ ] §4.2 CALIDAD: merma formula `Peso_final = Peso_bruto × (1−%Z) × (1−%S) × (1−%M) × (1−%V)` explicit and correct order
- [ ] §4.2 CALIDAD: distinction between cereals (Grado 1/2/3) and oleaginosas (tolerance-based rebajas) explicitly labeled
- [ ] §4.4 CUENTAS CORRIENTES: dual ledger (kg + pesos/USD), "a fijar" mechanics, posición consolidada all specified
- [ ] Each Phase 1 module has ≥ 3 user stories per assigned persona (Balancero for §4.1, Laboratorista for §4.2, Dueño for §4.4)

### Gate 4: After §4.5-§4.8 (Modules — Phase 2-3)
- [ ] §4.5 LIQUIDACIONES: complete IVA SISA-tier table (5/8/10.5/16%) and Ganancias table (0/2/15/30%) present with RG citations (RG 2300, RG 4325)
- [ ] §4.5 LIQUIDACIONES: pre-liquidación SISA blocking gate explicitly specified
- [ ] §4.6 FACTURACIÓN: reuse note for branch 001 infrastructure; only acopio service types (secada, zarandeo, almacenaje, paritaria) are new
- [ ] §4.7 AGRONOMÍA: discrete inventory (units/lots, not kg continuous)
- [ ] §4.8 CANJE: both LPG + invoice fiscal documents specified; cuenta corriente entries described

### Gate 5: After §5-§7 (Workflows + Regulatory + Hardware)
- [ ] §5.1 Romaneo flow diagram renders and shows all 11 steps with offline path annotation
- [ ] §6.1 CPE state machine present (Activa→Arribo [confirmarArriboCPE]→Descargada [descargadoDestinoCPE]→Confirmada Definitiva [confirmacionDefinitivaCPEAutomotor])
- [ ] §6.3 SISA: RG 5689/2025 cited explicitly; blocking gate defined; 24-hour registration requirement stated
- [ ] §6.4 retention tables complete: both IVA and Ganancias tables present with all 4 tiers and RG citations
- [ ] §7 weighbridge: RS-232 + TCP/IP specified; NO brand names or baud rates; dual-scale + stability detection defined

### Gate 6: After §8-§9 (NFRs + Phased Delivery)
- [ ] §8.1 per-module online/offline matrix covers all 8 modules with operation-level classification
- [ ] §8.2 acopio performance targets: < 5 min/truck, < 60s sync, < 2s merma calculation, < 5s posición consolidada
- [ ] NFR-SEC-01 to NFR-SEC-04 preserved verbatim (encryption, JWT, RLS, rate limiting)
- [ ] NFR-EDGE-01 to NFR-EDGE-04 preserved verbatim + 3 new acopio edge cases
- [ ] §9 all 4 phases present with entry and exit criteria
- [ ] Phase allocation consistent with Vision v1.0: Phase 1 = RECEPCIÓN+CALIDAD+ALMACENAMIENTO+CUENTAS CORRIENTES

### Gate 7: After §10 + Full Document (Implementation Foundation + Final Validation)
- [ ] §10 contains all preserved infrastructure: Implementation Progress table + Estado de Implementación + ARCA + Sync + Personalización + Auth + Rust benchmarks + API contracts
- [ ] §10 header clearly frames it as "existing technical foundation"
- [ ] Full-text search: ZERO hits for "cajero", "cashier", "PyMEs minoristas", "ferretería", "distribuidora de bebidas", "punto de venta", "bajo evaluación", "4 nichos"
- [ ] All 5 Mermaid diagrams render without errors (test in Markdown viewer)
- [ ] SC-001 to SC-010 from spec.md verifiable: modules self-contained, 15+ user stories, RG citations, retention tables, 5 diagrams, branch history preserved, zero retail language, consistent with Vision, offline matrix complete
- [ ] Zero [NEEDS CLARIFICATION] or TODO markers remaining
- [ ] Document is in English with Spanish domain terms (A-002)
- [ ] No Vision-level duplication: no market sizing, competitor analysis, or pricing in PRD (A-003)

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. **FR-001 through FR-019** from `specs/002-acopio-prd/spec.md` are all satisfied:
   each "Document MUST specify..." requirement is locatable in the PRD
2. **SC-001 through SC-010** from `specs/002-acopio-prd/spec.md` are all verifiable:
   - SC-001: any module section is self-contained (data fields, states, offline behavior — no external lookup needed)
   - SC-002: 15+ user stories total (5 personas × ≥ 3 each), all Given/When/Then
   - SC-003: zero vague regulatory references; every citation is "RG XXXX/YYYY"
   - SC-004: merma formula unambiguous — two developers produce identical results
   - SC-005: both IVA and Ganancias tables complete with 4 tiers each
   - SC-006: ≥ 5 Mermaid diagrams, all rendered without errors
   - SC-007: feature branch history (001-025) preserved in §10
   - SC-008: zero occurrences of "cajero", "retail", "ferretería", "distribuidora de bebidas", "punto de venta"
   - SC-009: consistent with Vision v1.0 on 5 persona names, 8 module names, 4-phase allocation
   - SC-010: per-module online/offline matrix covers all modules with three-category classification
3. **All 7 checkpoint gates** above are fully checked
4. **File replaced**: `Docs/Project Blueprint/PRD.md` updated in-place (v0.4 → v1.0)
5. **No stale content**: zero references to "PyMEs minoristas", POS retail scenarios, or "evaluating 4 niches"
6. **Diagram verification**: all Mermaid diagrams tested in a Markdown renderer
7. **Cross-reference check**: module names match `Descripción General del Producto.md`
8. **Clarification compliance**: all 5 clarifications from `specs/002-acopio-prd/spec.md` are reflected:
   - Posición consolidada view specified in §4.4 CUENTAS CORRIENTES
   - "A fijar" trigger (producer → admin → LPG) specified in §4.4 and §5.2
   - Dispute handling = audit trail only (no CAC lifecycle); stated in §4.2
   - Campaign transition = config + carry-stock report; stated in §4.3 + §5.3
   - Weighbridge = interface-level only (RS-232 + TCP/IP + dual-scale behavior); stated in §7

---

## RAG-Verified Inline Data (use these directly, do not re-query)

The following facts were verified by RAG queries during spec-02 `/sc:improve` and are
ready to inline during writing. Use these to avoid redundant queries on facts already
confirmed.

### Romaneo Workflow (Research 2.1) [RAG-verified 2026-03-16]
- 11 steps: Arrival → CPE registration → Gross weight → Lab sample → Tara → Net weight → Quality analysis → Merma calc → Net conforme → Boleta + Silo assignment → Account credit + CPE closure
- The romaneo is the atomic transaction that drives all downstream operations
- Balancero/recibidor processes truck in < 5 minutes during harvest peak (target from competitive analysis)

### Merma Formula (Research 2.5, CAC Circular 10/86 + Resolución JNG N° 22027/81) [RAG-verified 2026-03-16]
- Mandatory sequential order per both CAC Circular 10/86 and Resolución JNG N° 22027/81: zarandeo → secado → manipuleo → volátil
- Formula: `Peso_final = Peso_bruto × (1 − %Z) × (1 − %S) × (1 − %M) × (1 − %V)`
- Each step applied on the weight result of the previous step (multiplicative chain — NOT each deducted from original weight)
- Secado: uses Hf table per grain type published by Cámara Arbitral: `%S = (Hi − Hf) / (100 − Hf)`
- Manipuleo fixed values (% of weight after secado): trigo 0.10%; maíz/soja 0.25%; girasol 0.20%
- Volátil fixed values: cereales (trigo, maíz, avena, cebada, centeno) 0.30%; oleaginosas (soja, girasol) 0.50%
- Cereals (trigo, maíz, sorgo): graded Grado 1 (bonif.) / Grado 2 (base) / Grado 3 (rebaja) / Fuera de Estándar based on worst parameter
- Oleaginosas (soja, girasol): tolerance-based progressive rebajas (NOT Grado 1/2/3); e.g., soja materias extrañas >1%: 1% rebaja per point up to 3%, then 1.5% per point above 3%

### Producer Account Documents (Research 2.3) [RAG-verified 2026-03-16]
- CEG: Certificado de Existencia de Granos — grain deposit certificate (issued at romaneo closure)
- LPG / Form 1116-C: Liquidación Primaria — settlement on grain sale or fijación
- Cert. Retiro: withdrawal certificate — grain physical exit
- F.2005/SIRE: retention certificate — fiscal retention confirmation document

### CPE Lifecycle (Research 8.2 + 1.1) [RAG-verified 2026-03-16]
- States: Borrador (local draft) → Activa (CTG assigned, 5-day validity) → Arribo → Descargada → Confirmada Definitiva
- Creation: `autorizarCPEAutomotor` — ARCA validates SISA, assigns 12-digit CTG, activates CPE
- Arrival: `confirmarArriboCPE` — state-only change (no business data sent)
- Unloading: `descargadoDestinoCPE` — records physical unloading event
- Closure: `confirmacionDefinitivaCPEAutomotor` — sends final peso bruto + tara; ARCA computes net and closes CTG
- Side paths: `anularCPE` (cancel before departure), `rechazoCPE` (destination rejects), `informarContingencia` (delay — pauses TTL)
- 1 CPE = 1 truck = 1 romaneo (bijection enforced by ARCA)
- WSCPE online required for confirmation; system must queue confirmarArriboCPE and closure methods when offline
- **Note on spec.md terminology**: spec.md uses the shorthand `confirmarDescargaCPE` to refer to the closure step; the PRD should document the actual two-step sequence (`descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor`) for engineering precision

### Retention Tables (Research 7.3 — authoritative) [RAG-verified 2026-03-16]
- IVA per RG 2300 (SISA-tiered, from Research 7.3 table): Estado 1 = 5%, Estado 2 = 8%, Estado 3 = 10.5%, non-registered = 16%
  - **Source discrepancy note**: Research 1.3 and Research 7.1 cite a different table (5%/7%/8%/—). Use Research 7.3 values, which are consistent with spec.md (user-confirmed). The discrepancy likely reflects different research time periods or IVA regime versions — the PRD should cite Research 7.3 values.
  - Estado 1 rate (5%) is fully refunded by ARCA to producer within ~45 days (automatic reintegro)
- Ganancias per RG 4325 (grain-specific, replaces older RG 2118/2006): Estado 1 = 0%, Estado 2 = 2%, Estado 3 = 15%, non-registered = 30%
- IIBB: per-province rate, NOT a federal table — configurable by tenant admin
- SISA RG 5689/2025: 24-hour grain movement registration rule; SISA status determines retention tier per liquidación
- Pre-liquidación SISA query is a blocking gate: system queries producer CUIT via SISA API; result determines retention tier; settlement blocked if query fails or returns "Inhabilitado"

### Weighbridge Integration (Research 3.1) [RAG-verified 2026-03-16]
- RS-232 serial is the dominant standard for Argentine grain scale indicators; RS-485 is also used in some installations (same family, different electrical standard — treat equivalently at application level)
- No Argentine weighbridge manufacturer offers a REST API; integration is via serial/Modbus or middleware
- TCP/IP access via converter bridges: e.g., KYASERV module converts RS-232 → Ethernet socket (up to 4 scales); virtual serial port or network socket consumption
- Stability signal: weighbridge indicator emits a "stable" flag; system only captures weight when stable — never captures fluctuating readings
- Dual scale: primary scale (laden truck) captures peso bruto; secondary scale (empty truck after unloading) captures tara; peso neto = peso bruto − tara (computed, not from scale)
- Alternative tara modes: fixed tara per truck plate (stored in system) or manual entry fallback when secondary scale unavailable
- Calibration: INTA/SENASA/INPM standards require periodic calibration with certificate; system should track last calibration date + next due date per scale and alert before expiry

---

## Execution Notes

### Pre-Writing Setup
Before writing any section:
1. Read `specs/002-acopio-prd/spec.md` — authoritative spec with 19 FRs, 10 SCs, and 5 clarifications
2. Read `Docs/Project Blueprint/PRD.md` (v0.4) — know exactly what to preserve verbatim
3. Read `Docs/Project Blueprint/Descripción General del Producto.md` — module names and operational flow authority
4. Use the RAG-Verified Inline Data section above for facts already confirmed (no re-querying needed)
5. Run targeted RAG queries (see §§ above) for any section needing additional domain depth

### Writing Order Recommendation
Write sections in dependency order, not document order:
1. **§10** (Implementation Foundation) — copy from v0.4 verbatim first; establishes what carries forward
2. **§1** (Metadata) — quick, sets framing
3. **§2** (Introduction + Glossary) — acopio intro + adapted glossary
4. **§3** (Functional Decomposition) — mindmap (new) + §3.2 (verbatim) + dependency graph (new)
5. **§4.1–§4.4** (Phase 1 modules) — RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES
6. **§4.5–§4.8** (Phase 2-3 modules) — LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE
7. **§5** (Operational Workflows) — cross-module flows that reference §4 content
8. **§6** (Regulatory Compliance) — detailed regulatory specs using verified retention tables
9. **§7** (Hardware Integration) — weighbridge interface spec
10. **§8** (NFRs) — adapt §5 from v0.4 + add offline matrix and acopio performance targets
11. **§9** (Phased Delivery) — synthesize from §4 module list + Vision v1.0 phase allocation
12. **Traceability Matrix** — synthesize from all FRs; maps spec.md FR-001 to FR-019 to PRD sections

### Key Cross-References to Maintain
- Module names in §3.1 and §4.x MUST match `Descripción General del Producto.md`
- Phase allocation in §9 MUST match Vision v1.0 (RECEPCIÓN+CALIDAD+ALMACENAMIENTO+CUENTAS CORRIENTES in Phase 1)
- Retention tables in §6.4 MUST match the tables in §4.5 LIQUIDACIONES
- Offline matrix in §8.1 MUST cover every operation mentioned in each module in §4
- Feature branch history in §10 MUST match v0.4 §3.2 verbatim (no edits to individual rows)

### File Operations
- **Target file**: `Docs/Project Blueprint/PRD.md`
- **Operation**: REPLACE entire file content (v0.4 → v1.0)
- **Backup**: Git tracks v0.4 in history (`git log -- "Docs/Project Blueprint/PRD.md"`)
- **No new files created** — this is an in-place rewrite
