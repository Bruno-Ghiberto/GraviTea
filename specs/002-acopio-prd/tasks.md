# Tasks: Acopio PRD Rewrite

**Feature**: `002-acopio-prd`
**Input**: Design documents from `specs/002-acopio-prd/`
**Output**: `Docs/Project Blueprint/PRD.md` (in-place rewrite v0.4 → v1.0)
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

> **Blueprint Spec**: This is a document-writing task list, not a code implementation.
> All tasks write to `Docs/Project Blueprint/PRD.md`. No test tasks (document spec).
> Single-author sequential execution — no multi-agent orchestration.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (no dependency on preceding incomplete task)
- **[Story]**: Which user story this task satisfies (US1–US5)
- No story label: Setup or Foundational phase tasks

---

## Phase 1: Setup

**Purpose**: Read source materials and identify content to preserve before writing begins.

- [x] T001 Read `Docs/Project Blueprint/PRD.md` (v0.4) and extract all content blocks marked for verbatim preservation: §1 lines 13-24 (implementation progress table), §3.2 lines 98-120 (Estado de Implementación 19-row table), §4.3 ARCA integration, §4.4 sync engine, §4.5 personalización, §4.6 auth JWT RS256
- [x] T002 [P] Read `Docs/Project Blueprint/Product Vision & Scope.md` v1.0 and extract: 5 persona names, 8 canonical module names (Spanish CAPS), 4-phase allocation, USD $90/seat/month pricing reference — to validate SC-009 consistency
- [x] T003 [P] Read `Docs/Project Blueprint/Descripción General del Producto.md` and confirm 8 canonical Spanish module names exactly as committed: RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE

---

## Phase 2: Foundational (Non-Story PRD Sections)

**Purpose**: Foundation sections that must exist before module specs are written. These sections are not tied to a single user story.

**⚠️ CRITICAL**: Gate W1 — complete §10 verbatim preservation before writing any new content.

- [x] T004 Write §10 Implementation Foundation in `Docs/Project Blueprint/PRD.md` — copy verbatim from v0.4 in this order: (1) §1 lines 13-24 Implementation Progress table, (2) §3.2 lines 98-120 Estado de Implementación 19-row feature branch table (001–025), (3) §4.3 ARCA integration details (WSAA/WSFEv1 certificates), (4) §4.4 sync engine, (5) §4.5 personalización, (6) §4.6 auth JWT RS256 — confirm SC-007: "001-sal-invo-inve-backend" present in this section
- [x] T005 Write §1 Metadata in `Docs/Project Blueprint/PRD.md` — version 1.0, status "Acopio de Granos Vertical — Active Development", date 2026-03-16, cross-reference to §10 for implementation progress; remove "Nota estratégica" box and "evaluando 4 nichos" language from v0.4
- [x] T006 Write §2 Introduction and Glossary in `Docs/Project Blueprint/PRD.md` — (1) acopio de granos intro paragraph explaining the domain (2) 24-term canonical glossary table from `research.md §2`: romaneo, merma, CPE/CTG, WSLPG, SISA, CEG, LPG, boleta de romaneo, peso neto conforme, "a fijar", fijación, pizarra, posición consolidada, campañA, acopiador, balancero, zarandeo, secado, manipuleo, volátil, cubicaje, canje, liquidación primaria/secundaria — each term with English translation on first use

**Checkpoint (Gate W1)**: §10 presente, §3.2 verbatim lines 98-120 verified, zero retail/generic language introduced.

---

## Phase 3: User Story 1 — Module Specifications (Priority: P1) 🎯 MVP

**Goal**: An engineer or AI agent can open any of the 8 §4.x sections and implement that module without consulting external sources.

**Independent Test**: Open any of §4.1–§4.8. The section contains: feature list, data capture requirements, state machine or operational rules, and offline behavior. (User story acceptance scenarios are added in Phase 6 — Phase 3 verifies technical module content only.)

### Implementation for User Story 1

- [x] T007 [US1] Write §3.1 Functional Decomposition Mindmap in `Docs/Project Blueprint/PRD.md` — Mermaid `mindmap` diagram with root "GRAVITEA Acopio" and 8 leaf nodes using exact Spanish CAPS names; replaces generic retail modules from v0.4
- [x] T008 [US1] Write §3.2 Implementation Status in `Docs/Project Blueprint/PRD.md` — VERBATIM copy of v0.4 §3.2 lines 98-120, the 19-row feature branch table (001-sal-invo-inve-backend through 025-rust-custom-field-validator) with Spec, Status, Branch, and Notes columns unchanged
- [x] T009 [US1] Write §3.3 Module Dependency Graph in `Docs/Project Blueprint/PRD.md` — Mermaid `graph LR` diagram with directional arrows exactly as specified in spec.md US5 AC3: RECEPCIÓN→ALMACENAMIENTO, RECEPCIÓN→CALIDAD, CALIDAD→CUENTAS_CORRIENTES, CUENTAS_CORRIENTES→LIQUIDACIONES, LIQUIDACIONES→FACTURACIÓN, CUENTAS_CORRIENTES→CANJE, CANJE→AGRONOMÍA
- [x] T010 [US1] Write §4.1 RECEPCIÓN in `Docs/Project Blueprint/PRD.md` — (1) feature list (truck reception, peso bruto/tara capture, boleta de romaneo, CPE closure, offline mode), (2) romaneo 6-state Mermaid `stateDiagram-v2` (PENDIENTE→EN_PROCESO→PESADO→ANALIZADO→CONFORME→CERRADO with offline path: PENDIENTE→EN_PROCESO→PESADO with CPE queue note), (3) data capture table per step (columns: Step, Fields Captured, Source, Offline Behavior), (4) offline behavior description (store-and-forward CPE confirmation queue, romaneo completes locally when connectivity unavailable), (5) digital boleta de romaneo fields
- [x] T011 [US1] Write §4.2 CALIDAD in `Docs/Project Blueprint/PRD.md` — (1) quality parameters table for 5 grains (trigo, maíz, soja, girasol, sorgo) with grain-specific parameters, (2) two grading systems table explicitly labeled: cereals (trigo/maíz/sorgo) use Grado 1/2/3 classification; oleaginosas (soja/girasol) use tolerance-based progressive rebajas, (3) merma calculation in mandatory sequential order per CAC Circular 10/86 + Resolución JNG N° 22027/81: `Peso_final = Peso_bruto × (1−%Z) × (1−%S) × (1−%M) × (1−%V)` with fixed values: manipuleo (trigo 0.10%, maíz/soja 0.25%, girasol 0.20%), volátil (cereales 0.30%, oleaginosas 0.50%), (4) Hf adjustment table for secado calculation per grain type, (5) audit trail note: system exposes full transparent calculation history per romaneo on demand; formal disputes escalated to Cámara Arbitral de Cereales (CAC) externally — no internal dispute lifecycle
- [x] T012 [US1] Write §4.3 ALMACENAMIENTO in `Docs/Project Blueprint/PRD.md` — (1) silo and celda management: identifier, type (vertical silo/horizontal celda/wet bin), capacity in tons, current occupancy by lot, (2) grain assignment rules by type/quality/campaign, (3) grain position report (what, where, whose), (4) campaign year logical segregation using composite key (plant_id, grain_code, campaign_id) per RG 3593, (5) inter-silo movements, (6) cubicaje (volumetric estimation) support
- [x] T013 [US1] Write §4.4 CUENTAS CORRIENTES in `Docs/Project Blueprint/PRD.md` — (1) dual-ledger architecture: per-plant grain sub-ledger (kg by grain type + campaign) + monetary sub-ledger (ARS/USD), per-plant ledger is source of truth, (2) transaction type catalog table (8 types: CEG deposit, LPG sale, retiro, service charges, canje grain debit, canje input credit, retention deduction, ajuste), (3) "a fijar" mechanics: grain enters at zero monetary value; price crystallizes when producer requests fijación → administrador records at current pizarra price → LPG generated; single CEG can generate multiple partial LPGs, (4) extracto (statement) generation by grain type and campaign, (5) posición consolidada: cross-plant derived view (NOT stored), aggregates per-plant kg + monetary balances for same producer CUIT across all plants of the same tenant, visible only to Dueño/Gerente role
- [x] T014 [US1] Write §4.5 LIQUIDACIONES in `Docs/Project Blueprint/PRD.md` — (1) Form 1116-C (Liquidación Primaria, acopiador-to-producer) and Form 1116-B (Liquidación Secundaria, acopiador-to-buyer) spec with required fields, (2) liquidación lifecycle Mermaid `stateDiagram-v2`: DRAFT→RETENCION_CALCULADA→SISA_VERIFICADA→WSLPG_PRESENTADA→LIQUIDADA, (3) complete SISA-tier retention tables: IVA (Estado 1: 5%, Estado 2: 8%, Estado 3: 10.5%, no-registrado: 16% per RG 2300); Ganancias (Estado 1: 0%, Estado 2: 2%, Estado 3: 15%, no-registrado: 30% per RG 4325), (4) SISA pre-liquidación blocking gate description, (5) SICORE magnetic file generation, (6) WSLPG electronic filing reference
- [x] T015 [P] [US1] Write §4.6 FACTURACIÓN in `Docs/Project Blueprint/PRD.md` — (1) explicit reuse note: ARCA infrastructure (WSAA + WSFEv1) from feature branch 001-sal-invo-inve-backend is reused unchanged, (2) acopio-specific service types only: secada (drying fee), zarandeo (sieving fee), almacenaje (storage fee), paritaria (handling fee), otros servicios, (3) invoice types A/B/C, credit/debit notes, (4) CAE mode (online, synchronous ARCA call) and CAEA mode (offline, pre-authorized range) with no-connectivity fallback
- [x] T016 [P] [US1] Write §4.7 AGRONOMÍA in `Docs/Project Blueprint/PRD.md` — (1) input catalog: categories (seeds, fertilizers, agroquímicos, repuestos) with SKU/lot tracking, (2) discrete inventory (units not kg), (3) stock tracking by lot and expiry date, (4) purchase orders from distributors, (5) sales to producers, (6) price lists with effective-date support
- [x] T017 [P] [US1] Write §4.8 CANJE in `Docs/Project Blueprint/PRD.md` — (1) grain-for-input exchange workflow: producer requests canje → system compensates grain credit against input debit at current pizarra price, (2) two parallel document streams: LPG (grain settlement, IVA at grain rate 10.5%) + Factura (input invoice, IVA at input rate 21%), (3) canje total vs canje parcial: canje total has no cash retentions; canje parcial applies IVA/Ganancias/IIBB retentions only on the cash portion, (4) all entries recorded in producer cuenta corriente with transaction type "canje grain debit" and "canje input credit"

**Checkpoint (Gate W3)**: Navigate each of §4.1–§4.8. Confirm: (a) feature list present, (b) state machine or operational rules present, (c) data capture requirements specified, (d) offline behavior described, (e) merma formula exact with fixed values, (f) posición consolidada specified in §4.4.

---

## Phase 4: User Story 2 — Regulatory Compliance (Priority: P2)

**Goal**: Accountant can navigate §6 and find the specific RG citation and system action vs. user confirmation boundary for each of the 5 regulatory regimes (CPE/CTG, WSLPG, SISA, retentions, SICORE).

**Independent Test**: Navigate §6. For each regulatory regime, find: (1) specific RG number + year, (2) what the system does automatically, (3) what the user must confirm manually.

### Implementation for User Story 2

- [x] T018 [US2] Write §6.1 CPE/CTG Integration in `Docs/Project Blueprint/PRD.md` — (1) CPE lifecycle Mermaid `stateDiagram-v2`: Activa (5-day validity) → confirmarArriboCPE (on arrival) → Arribo → descargadoDestinoCPE (at weight capture) → Descargada → confirmacionDefinitivaCPEAutomotor (at romaneo close with actual peso neto conforme) → Confirmada Definitiva, (2) WSCPE method catalog table (columns: Romaneo Step, WSCPE Method, Required Data, Offline Behavior): step 3 arrival→confirmarArriboCPE, step 8 weight→descargadoDestinoCPE, step 10 close→confirmacionDefinitivaCPEAutomotor, (3) offline store-and-forward queue: romaneo proceeds locally, confirmarArriboCPE queued, CPE confirmed when connectivity restores before next WSCPE call, (4) 5-day CTG validity tracking and alert, (5) 1 CPE = 1 truck = 1 romaneo relationship constraint
- [x] T019 [US2] Write §6.2 WSLPG in `Docs/Project Blueprint/PRD.md` — (1) electronic filing workflow for Form 1116-C (Liquidación Primaria) via WSLPG web service, (2) Form 1116-B (Liquidación Secundaria) for grain buyer settlements, (3) SICORE magnetic file: generation schedule (monthly), file format, what operations are included (retention deductions per liquidación), (4) specific RG citations for both forms
- [x] T020 [US2] Write §6.3 SISA in `Docs/Project Blueprint/PRD.md` — (1) RG 5689/2025 explicit citation (current regulation), (2) producer classification: Estado 1 (full compliant), Estado 2 (partial compliant), Estado 3 (marginal), no-registrado, (3) 24-hour grain movement registration requirement, (4) pre-liquidación blocking gate: system calls SISA query before each settlement; settlement cannot proceed without a valid SISA response — this is a hard system block, not a warning
- [x] T021 [US2] Write §6.4 Retention Calculation Reference in `Docs/Project Blueprint/PRD.md` — complete tables: (1) IVA retention table (4 rows: Estado 1→5%, Estado 2→8%, Estado 3→10.5%, no-registrado→16%) with citation "per RG 2300/2007", (2) Ganancias retention table (4 rows: Estado 1→0%, Estado 2→2%, Estado 3→15%, no-registrado→30%) with citation "per RG 4325/2018 (grain-specific, replaces RG 2118/2006)", (3) IIBB note: rate is provincial and requires separate provincial-padron query, not covered in this table; (4) cross-reference: this table must match §4.5 LIQUIDACIONES retention tables exactly (SC-005)
- [x] T022 [US2] Write §7 Hardware Integration in `Docs/Project Blueprint/PRD.md` — (1) supported interfaces: RS-232 serial (primary standard, all Argentine indicator manufacturers support this), TCP/IP via RS-232→Ethernet converter bridge (KYASERV-type device; no brand names), (2) dual-scale workflow: primary scale captures peso bruto (gross), secondary scale captures tara (truck weight), system auto-calculates peso neto = peso bruto − tara, (3) stability detection: weight value only accepted when scale signals stable reading (scale-side flag, not polling); configurable stability timeout, (4) calibration log: track last calibration date and certificate per scale unit; alert when calibration is overdue; (5) note: baud rates, frame formats, indicator model-specific commands deferred to spec-08c (SRS)

**Checkpoint (Gate W5)**: Navigate §6 and verify: (a) CPE state machine renders and shows all WSCPE methods, (b) WSLPG section references both Form 1116-C and 1116-B, (c) SISA section cites RG 5689/2025 and states blocking gate, (d) retention tables in §6.4 match §4.5 exactly.

---

## Phase 5: User Story 3 — Phased Delivery (Priority: P3)

**Goal**: Phase 1 scope covers the complete Romaneo-to-Position daily loop with measurable exit criteria. Every module assigned exactly once.

**Independent Test**: Read §9. Phase 1 scope (4 modules) covers a complete operational day without requiring Phase 2+ features. Count modules: exactly 8 across 4 phases.

### Implementation for User Story 3

- [x] T023 [US3] Write §8.1 Per-module online/offline matrix in `Docs/Project Blueprint/PRD.md` — table with columns (Module, Operation, Offline Status) and 3-category classification: **Offline** (romaneo processing, quality grading, storage assignment, account credit, CAEA invoicing), **Connectivity-Required** (CPE confirmation calls, WSLPG filing, SISA query, CAE issuance, SISA status check), **Store-and-Forward** (CPE queue pending confirmarArriboCPE, CPE queue pending confirmacionDefinitivaCPEAutomotor, pending WSLPG when connectivity restores) — covers all 8 modules
- [x] T024 [P] [US3] Write §8.2–§8.4 NFRs in `Docs/Project Blueprint/PRD.md` — §8.2 Performance: romaneo end-to-end < 5 min during harvest peak (100+ trucks/day per plant), scale read latency < 500ms from stability signal to capture, offline queue sync < 2min when connectivity restores; §8.3 Security: AES-256-GCM for producer CUIT and financial data, PostgreSQL RLS for tenant isolation, JWT RS256 (inherit from platform), field-level encryption for cuenta corriente balances; §8.4 Edge cases: offline romaneo with CPE store-and-forward queue, campaign transition carry-stock report, quality dispute audit trail export to PDF, "Fuera de Estándar" handling for soja/girasol out-of-tolerance lots
- [x] T025 [US3] Write §9 Phased Delivery in `Docs/Project Blueprint/PRD.md` — 4 phases each with entry criteria, scope, exit criteria: Phase 1 (entry: infrastructure + ARCA certs ready; modules: RECEPCIÓN+CALIDAD+ALMACENAMIENTO+CUENTAS CORRIENTES; exit: first real truck reception processed on pilot plant), Phase 2 (entry: Phase 1 exit met + SISA API access; modules: LIQUIDACIONES+FACTURACIÓN; exit: first settlement filed via WSLPG), Phase 3 (entry: Phase 2 exit + campo inventory baseline; modules: CANJE+AGRONOMÍA+OCR document intelligence+weighbridge fraud detection; exit: first canje operation completed), Phase 4 (entry: Phase 3 + 1 full campaign of data; AI features: quality degradation prediction, silo assignment optimization, price forecasting, predictive aeration scheduling; exit: AI recommendations accepted by ≥3 pilot plants) — consistent with Vision v1.0 §4.7

**Checkpoint (Gate W6)**: Read §9 and count modules: exactly 8 across 4 phases. Verify Phase 1 exit = "first real truck reception." Verify Phase 4 AI features match Vision v1.0 §4.7.

---

## Phase 6: User Story 4 — Persona Journey Validation (Priority: P4)

**Goal**: All 5 personas have ≥3 user stories each (≥15 total), each with at least one Given/When/Then acceptance scenario.

**Independent Test**: `grep -c "Given\|Dado que"` in PRD — result ≥ 15.

### Implementation for User Story 4

- [x] T026 [US4] Add Balancero/Recibidor user stories (≥3 with Given/When/Then ACs) to §4.1 RECEPCIÓN in `Docs/Project Blueprint/PRD.md` — US: truck processed in < 5 minutes during harvest peak; US: romaneo continues normally when internet connection is down; US: weighbridge auto-captures peso bruto and tara without manual keyboard entry — each user story must have at minimum one Given/When/Then acceptance scenario
- [x] T027 [US4] Add Laboratorista user stories (≥3 with Given/When/Then ACs) to §4.2 CALIDAD in `Docs/Project Blueprint/PRD.md` — US: grade sample using per-grain tolerance tables (system shows which Grado applies for cereals, which rebaja applies for oleaginosas); US: automated merma calculation shows all 4 sequential steps (zarandeo → secado → manipuleo → volátil) with intermediate weights; US: export full audit trail per romaneo (all inputs, tolerance tables applied, merma breakdown per step) for CAC dispute submission — each with Given/When/Then AC
- [x] T028 [US4] Add Administrador/Contable user stories (≥3 with Given/When/Then ACs) to §4.5 LIQUIDACIONES in `Docs/Project Blueprint/PRD.md` — US: Liquidación 1116-C auto-calculates SISA-tier retentions (system shows which tier and rate applies based on live SISA query result); US: generate SICORE magnetic file for monthly retention filing obligation; US: SISA blocking gate prevents settlement from proceeding when SISA query fails or returns invalid status — each with Given/When/Then AC
- [x] T029 [US4] Add Dueño/Gerente user stories (≥3 with Given/When/Then ACs) to §4.4 CUENTAS CORRIENTES in `Docs/Project Blueprint/PRD.md` — US: view real-time grain position (kg by grain type + campaign) from mobile device across all plants; US: view posición consolidada (aggregated kg + monetary balance) per producer across all plants of the tenant without manual reconciliation; US: monitor harvest throughput (trucks/hour per plant, today vs campaign average) — each with Given/When/Then AC
- [x] T030 [US4] Add Contador Rural user stories (≥3 with Given/When/Then ACs) to §4.5 LIQUIDACIONES in `Docs/Project Blueprint/PRD.md` — US: real-time transaction visibility across multiple acopio clients (no need to request files from each acopiador); US: one-click fiscal summary export (SICORE obligations, retention totals) for multiple clients simultaneously; US: verify that each settlement's retention calculation matches the applicable SISA tier without manual re-calculation — each with Given/When/Then AC

**Checkpoint (Gate W4 partial + US4)**: Run `grep -c "Given\|Dado que" "Docs/Project Blueprint/PRD.md"` — expected: ≥ 15 results. Verify each of 5 persona names appears ≥3 times with user story context.

---

## Phase 7: User Story 5 — Operational Workflow Visualization (Priority: P5)

**Goal**: ≥5 Mermaid diagrams render without errors; each shows all states and transitions referenced in the surrounding prose.

**Independent Test**: Render all diagrams in GitHub-flavored Markdown preview — zero errors; romaneo flow shows 11 steps; dependency graph shows 8 modules.

### Implementation for User Story 5

- [x] T031 [US5] Write §5.1 11-step Romaneo Operational Flow in `Docs/Project Blueprint/PRD.md` — Mermaid `flowchart TD` or `sequenceDiagram` showing all 11 steps: (1) truck arrives at plant, (2) CPE number scanned → confirmarArriboCPE queued, (3) weighbridge: peso bruto captured (scale stable), (4) tara captured → peso neto calculated, (5) quality sample taken to lab, (6) lab analyst grades sample per grain tolerance tables, (7) merma calculated (zarandeo→secado→manipuleo→volátil), (8) peso neto conforme computed, (9) boleta de romaneo generated → FORK: (9a) silo assignment (ALMACENAMIENTO), (9b) CEG issued → producer account credited (CUENTAS CORRIENTES) both in parallel, (10) descargadoDestinoCPE called, (11) confirmacionDefinitivaCPEAutomotor called with peso neto conforme → CPE Confirmada Definitiva; include offline path annotation at step 2 and 10-11
- [x] T032 [P] [US5] Write §5.2 "A Fijar" Fijación Flow in `Docs/Project Blueprint/PRD.md` — Mermaid `flowchart LR` showing: producer contacts acopiador with fijación request → administrador opens fijación screen → system shows current pizarra price for grain type + campaign → administrador confirms price → system records fijación record with timestamp and pizarra price → LPG generated → monetary value crystallizes in cuenta corriente → CEG balance reduced by fixed kg; include note: single CEG can generate multiple partial LPGs (partial fijación supported)
- [x] T033 [P] [US5] Write §5.3 Campaign Transition Workflow in `Docs/Project Blueprint/PRD.md` — prose workflow (no diagram required by spec): (1) admin opens campaign configuration → defines new split-year code (format "YYYY/YY", e.g. "2025/26"), (2) system validates format and uniqueness per plant, (3) admin activates new campaign — all subsequent romaneos use new campaign code automatically, (4) system generates carry-stock report: lists all grain lots from prior campaign still in silos, grouped by producer CUIT, grain type, and silo — this report supports the operator's manual AFIP stock declaration per RG 3593; formal AFIP submission is external to the system
- [x] T034 [US5] Render-test all 5 mandatory Mermaid diagrams in `Docs/Project Blueprint/PRD.md` — open GitHub-flavored Markdown preview or use `grep -c '```mermaid' "Docs/Project Blueprint/PRD.md"` (expected ≥5) and verify each renders without syntax error: (1) §3.1 module mindmap, (2) §3.3 module dependency graph, (3) §4.1 romaneo state machine (6 states), (4) §4.5 liquidación state machine (5 states), (5) §5.1 romaneo 11-step operational flow — if any diagram fails to render, fix syntax before proceeding

**Checkpoint (Gate W5 diagrams + US5)**: All 5 mandatory Mermaid diagrams render. Romaneo flow shows 11 nodes with fork at step 9. Dependency graph shows 7 directional arrows.

---

## Phase 8: Final Validation

**Purpose**: Run all 7 checkpoint gates from `Docs/PROMPTS/spec-02-prd/02-plan.md` and verify all 10 success criteria from `specs/002-acopio-prd/spec.md`.

- [x] T035 Run SC-008 retail language check — `grep -i "cajero\|cashier\|ferretería\|PyMEs minoristas\|punto de venta\|distribuidores de bebidas" "Docs/Project Blueprint/PRD.md"` — expected: 0 results; if any found, remove from PRD
- [x] T036 [P] Run SC-002 user story count — `grep -c "Given\|Dado que" "Docs/Project Blueprint/PRD.md"` — expected: ≥15; if < 15, return to Phase 6 and add missing user stories
- [x] T037 [P] Run SC-003 regulatory citation density — `grep -i "RG [0-9]" "Docs/Project Blueprint/PRD.md" | wc -l` — expected: ≥10 distinct regulatory citations; if < 10, verify §4.5, §6.1, §6.2, §6.3, §6.4 all have RG numbers with year
- [x] T038 [P] Run SC-006 Mermaid diagram count — `grep -c '^\`\`\`mermaid' "Docs/Project Blueprint/PRD.md"` — expected: ≥5; if < 5, check which mandatory diagram is missing
- [x] T039 [P] Verify SC-007 feature branch history preserved — `grep "001-sal-invo-inve-backend" "Docs/Project Blueprint/PRD.md"` — expected: present in §10; if missing, re-check T004 output
- [x] T040 [P] Verify SC-004 merma formula completeness — search §4.2 for: formula string `Peso_final = Peso_bruto × (1−%Z) × (1−%S) × (1−%M) × (1−%V)` AND fixed values (manipuleo: trigo 0.10%, maíz/soja 0.25%, girasol 0.20%; volátil: cereales 0.30%, oleaginosas 0.50%) AND both citations (CAC Circular 10/86, Resolución JNG N° 22027/81) — all must be present for SC-004 pass
- [x] T041 [P] Verify SC-005 retention table completeness — search §4.5 and §6.4 for: IVA 4-tier values (5/8/10.5/16%) with "RG 2300" citation AND Ganancias 4-tier values (0/2/15/30%) with "RG 4325" citation — both tables must be complete for SC-005 pass
- [x] T042 Verify SC-009 Vision v1.0 consistency — confirm all of the following match between PRD and `Docs/Project Blueprint/Product Vision & Scope.md` v1.0: (a) 5 persona names exactly (Balancero/Recibidor, Laboratorista, Administrador/Contable, Dueño/Gerente, Contador Rural), (b) 8 module names in Spanish CAPS, (c) 4-phase allocation with same module assignments, (d) USD pricing reference ($90/seat/month) present — if any mismatch, update PRD to match Vision v1.0
- [x] T043 [P] Verify SC-010 offline matrix completeness — search §8.1 in `Docs/Project Blueprint/PRD.md` and confirm all 8 module names (RECEPCIÓN, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACIÓN, AGRONOMÍA, CANJE) appear in the matrix; verify each module has at least one operation classified in each of the 3 categories (Offline / Connectivity-Required / Store-and-Forward) — expected: 8 modules present with full 3-category coverage

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately; T002 and T003 can run in parallel with T001
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS Phase 3+
- **US1 (Phase 3)**: Depends on Foundational (Phase 2); T015, T016, T017 can run in parallel with T014 completion
- **US2 (Phase 4)**: Depends on Foundational (Phase 2); can start after §1-§2 are written (does not require US1 to be complete)
- **US3 (Phase 5)**: Depends on Foundational (Phase 2); can start after §4.x writing is complete (needs module names for phase allocation)
- **US4 (Phase 6)**: Depends on US1 (Phase 3) — adds user stories to existing §4.x sections
- **US5 (Phase 7)**: T031-T033 depend on US1 (§4.x sections exist to receive §5 content); T034 depends on all diagrams being written
- **Validation (Phase 8)**: Depends on ALL phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no dependency on other stories
- **US2 (P2)**: Can start after Foundational (Phase 2) — §6-§7 are new sections, independent of §4.x **except T021 (§6.4 retention tables) which MUST follow T014 (§4.5 LIQUIDACIONES) — SC-005 requires both tables match exactly and §6.4 cross-references §4.5**
- **US3 (P3)**: Needs US1 complete (module names) — Phase 3 must finish before Phase 5
- **US4 (P4)**: Depends on US1 — appends to existing §4.x sections written in Phase 3
- **US5 (P5)**: T031-T033 independent of US4; T034 render-test needs all 5 diagrams written

### Within Each Phase

- Section writing is sequential within a phase (document sections build on each other)
- §4.6, §4.7, §4.8 (T015, T016, T017) can be written in parallel (independent modules)
- §8.2-§8.4 (T024) can be written in parallel with §8.1 (T023) after T023 draft exists
- All Phase 8 validation grep tasks (T036-T041) can run in parallel

---

## Parallel Opportunities

```bash
# Phase 1 — run T002 and T003 while T001 reads PRD v0.4:
Read Vision v1.0 (T002) [in parallel with T001]
Read Descripción General (T003) [in parallel with T001]

# Phase 3 — after §4.5 written (T014), write remaining modules in parallel:
Write §4.6 FACTURACIÓN (T015) [in parallel]
Write §4.7 AGRONOMÍA (T016) [in parallel]
Write §4.8 CANJE (T017) [in parallel]

# Phase 5 — §8 sections partially parallel:
Write §8.1 offline matrix (T023) first, then:
Write §8.2-§8.4 NFRs (T024) [in parallel with §9]

# Phase 7 — §5.2 and §5.3 parallel after §5.1:
Write §5.2 fijación flow (T032) [in parallel with T033]
Write §5.3 campaign transition (T033) [in parallel with T032]

# Phase 8 — all SC-validation greps in parallel after writing complete:
SC-002 user story count (T036) [in parallel]
SC-003 regulatory citations (T037) [in parallel]
SC-006 Mermaid count (T038) [in parallel]
SC-007 feature branch history (T039) [in parallel]
SC-004 merma formula (T040) [in parallel]
SC-005 retention tables (T041) [in parallel]
```

---

## Implementation Strategy

### MVP First (US1 Only — Module Specs Readable)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T006)
3. Complete Phase 3: US1 Module Specs (T007–T017)
4. **STOP and VALIDATE**: Gate W3 — navigate each §4.x and confirm completeness
5. PRD is already useful to engineers at this point

### Full Blueprint Completion

1. Setup + Foundational → Foundation ready (T001–T006)
2. US1 — Module Specs → §3-§4 complete (T007–T017)
3. US2 — Regulatory → §6-§7 complete (T018–T022)
4. US3 — Phased Delivery → §8-§9 complete (T023–T025)
5. US4 — Persona User Stories → 15 user stories added (T026–T030)
6. US5 — Operational Flows → §5 + diagram render verification (T031–T034)
7. Validation — all 10 SCs verified (T035–T042)
8. PRD v1.0 complete — unblocks spec-03 Data Model

---

## Task Count Summary

| Phase | Tasks | User Story | Can Parallelize |
|-------|-------|-----------|----------------|
| Phase 1: Setup | 3 | — | T002, T003 |
| Phase 2: Foundational | 3 | — | none |
| Phase 3: US1 Modules | 11 | US1 (P1) | T015, T016, T017 |
| Phase 4: US2 Regulatory | 5 | US2 (P2) | none within phase |
| Phase 5: US3 Phased | 3 | US3 (P3) | T024 |
| Phase 6: US4 Personas | 5 | US4 (P4) | T026–T030 |
| Phase 7: US5 Diagrams | 4 | US5 (P5) | T032, T033 |
| Phase 8: Validation | 9 | — | T036–T041, T043 |
| **Total** | **43** | | |

**Suggested MVP scope**: Phase 1 + Phase 2 + Phase 3 (T001–T017) — 17 tasks to reach a PRD that unblocks data model design.

---

## Notes

- All tasks write to a single file: `Docs/Project Blueprint/PRD.md`
- No TDD, no test tasks — this is a document specification, not code
- Use `scripts/qdrant/qdrant_search.py` for domain detail lookups during writing (never read full research PDFs)
- RAG query command: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5`
- When in doubt about a domain fact, query the RAG pipeline rather than guessing
- Mark each task `[x]` in this file when complete
- Commit after each Writing Phase (W1–W7) completes, not after every task
- Gate W7 validation: all 10 SCs in `specs/002-acopio-prd/spec.md` must pass before marking PRD v1.0 complete
