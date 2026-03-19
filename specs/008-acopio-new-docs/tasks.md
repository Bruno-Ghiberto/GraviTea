# Tasks: Acopio New Blueprint Documents (08a/08b/08c)

**Input**: Design documents from `/specs/008-acopio-new-docs/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: No code tests. Gate checks (grep-based) serve as validation after each document.

**Organization**: Tasks grouped by user story. Each story produces one complete blueprint document that can be validated independently via checkpoint gates.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=08a, US2=08c, US3=08b)
- All file paths are relative to repository root

---

## Phase 1: Setup (Context Loading)

**Purpose**: Load upstream blueprints and verify RAG infrastructure before writing begins

- [x] T001 Read upstream blueprint documents for section-level context: `Docs/Project Blueprint/High-Level Design (HLD).md` §6 (ARCA) and §12 (AI/ML), `Docs/Project Blueprint/PRD.md` §4 (modules) and §7-§8 (hardware, NFRs), `Docs/Project Blueprint/Architecture Decision Records (ADR).md` (ADR-019, 025-030, 033-035), `Docs/Project Blueprint/REST API Design.md` (Phase 1 endpoints), `Docs/Project Blueprint/Roadmap.md` §5-§7 (phases, delivery, ML triggers), `Docs/Project Blueprint/Data Model & Domain Model.md` (entity fields for 08b/08c)
- [x] T002 Verify Qdrant RAG collections are available by running `.venv/bin/python scripts/qdrant/qdrant_search.py -q "test" -l 1` and confirming `acopio_research`, `arca_api_specs`, and `arca_dev_guides` collections respond
- [x] T003 Read context prompt files `Docs/PROMPTS/spec-08-new-docs/08-specify.md` (domain facts, FRs, ACs, target structures) and `Docs/PROMPTS/spec-08-new-docs/08-plan.md` (section-by-section writing plans, research mapping, content guidelines)

**Checkpoint**: Context loaded — upstream content accessible, RAG operational, writing plans understood

---

## Phase 2: Foundational (RAG Research Queries)

**Purpose**: Run targeted RAG queries to gather domain facts needed by all three documents. Cache results for reference during writing.

**CRITICAL**: RAG queries must use `.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -l 5`

- [x] T004 [P] Run ARCA-focused RAG queries for 08a: (1) `"WSAA authentication TRA LoginCMS Token Sign certificate"`, (2) `"WSLPG liquidacionAutorizar XML fields codGrano"`, (3) `"WSCPE CPE lifecycle confirmarArribo confirmarDescargaCPE"`, (4) `"CAEA quincena offline fiscal authorization"`, (5) `"pyafipws WSLPG open source ARCA integration"`, (6) `"ARCA homologacion testing CUIT certificates"`, (7) `"SISA retention withholding tier Estado IVA Ganancias"`
- [x] T005 [P] Run SRS-focused RAG queries for 08c: (1) `"romaneo workflow truck arrival weighing quality grading"`, (2) `"weighbridge RS-232 Modbus protocol baud rate frame format"`, (3) `"grain quality parameters humidity tolerance bonificacion rebaja"`
- [x] T006 [P] Run AI/ML-focused RAG queries for 08b: (1) `"AI ML grain storage predictive merma model"`, (2) `"grain quality degradation prediction LSTM silo temperature"`, (3) `"weighbridge fraud detection anomalous weight pattern"`

**Checkpoint**: RAG results cached — domain facts available for document writing

---

## Phase 3: User Story 1 — ARCA Grain Integration Guide (Priority: P1) MVP

**Goal**: A developer unfamiliar with ARCA can read 08a and correctly describe authentication, WSLPG filing, and WSCPE lifecycle within 30 minutes

**Independent Test**: Gate 1 grep checks pass (ARCA ≥40, Mermaid ≥3, fwshomo ≥1, ADRs ≥7, TBD=0)

### Implementation for User Story 1

- [x] T007 [US1] Write §1 Document Metadata (version header, changelog, upstream refs) and §2 ARCA Service Overview (hub-and-spoke Mermaid diagram, service catalog table with production/homologation URLs for WSAA, WSLPG, WSCPE, WSFEv1) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T008 [US1] Write §3 WSAA Authentication: TRA XML generation, X.509 CMS signing, Base64 encoding, LoginCMS SOAP method, Token+Sign response, Redis 11h TTL caching, concurrent refresh handling, Mermaid sequence diagram, error handling (timeout, auth error mid-batch, cert expiry) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T009 [US1] Write §4 WSLPG — Grain Settlement: regulatory context (RG 3419/2012, RG 3690/2014), service URLs, `liquidacionAutorizar` XML field reference, codGrano single-grain-type constraint (ADR-019), SISA blocking gate (ADR-027), retention tiers table (Estado 1-3 + Non-registered), COE extraction, parameter lookup methods, error codes in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T010 [US1] Write §5 WSCPE — CPE Lifecycle: CPE/CTG overview, Mermaid state machine diagram (Activa→Arribo→Descargada→Confirmada_Definitiva + Anulada/Rechazada), full method catalog (solicitarCPEAutomotor, consultarCPEAutomotor, confirmarArriboCPE, confirmarDescargaCPE, anularCPE, rechazoCPE, consultarRenspa), 5-day validity, offline store-and-forward (ADR-030), resolve method name discrepancy (HLD `descargadoDestinoCPE` vs ARCA `confirmarDescargaCPE`) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T011 [P] [US1] Write §6 WSFEv1/CAEA (CAE online path, CAEA offline quincena batch, legal warning callout, Rust 024 reference, ADR-026) and §7 Certificate Management (per-service X.509 certs, Secret Manager storage, rotation procedure, expiry alerting, ADR-025) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T012 [US1] Write §8 Homologation Testing Guide (environment overview, production/homologation URLs table for all 4 services, pre-seeded test CUITs, known quirks, per-service testing checklist, promotion procedure) and §9 Open-Source Reference Implementations (pyafipws assessment, py3afipws, django-afip, afip.py/Afip SDK, SistemasAgiles wiki, adaptation caveats for Django + Rust) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T013 [US1] Write consolidated error handling summary table (FR-007) cross-referencing failure modes, retry strategies, and operator actions across all 4 ARCA services (WSAA, WSLPG, WSCPE, WSFEv1) — place after §9 or as appendix to §8. Then write §10 ADR Cross-Reference table (ADR-019, ADR-025, ADR-026, ADR-027, ADR-028, ADR-029, ADR-030 with titles, impacts, section references) and §11 Glossary (ARCA-specific terms only: TRA, CMS, Token+Sign, COE, CTG, CPE, CAEA, quincena, etc. — no overlap with PRD glossary) in `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
- [x] T014 [US1] Run Gate 1 validation on `Docs/Project Blueprint/ARCA Grain Integration Guide.md`: `grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1"` ≥40, `grep -c '` ` `` `mermaid'` ≥3, `grep -c "fwshomo.afip"` ≥1, `grep -c "ADR-019\|ADR-025\|ADR-026\|ADR-027\|ADR-028\|ADR-029\|ADR-030"` ≥7, `grep -ci "TBD\|TODO\|placeholder"` =0. Fix any failures before proceeding.

**Checkpoint**: 08a complete and gate-validated. Developer can now read ARCA integration guide independently.

---

## Phase 4: User Story 2 — Software Requirements Specification (Priority: P1)

**Goal**: QA engineer can produce a test plan for any Phase 1 module using traceable SRS requirement IDs

**Independent Test**: Gate 2 grep checks pass (SRS-IDs ≥20, shall ≥30, hardware ≥5, TBD=0)

### Implementation for User Story 2

- [x] T015 [US2] Write §1 Document Metadata (version header, changelog, note: complete rewrite replacing stale retail SRS), §2 Introduction (purpose, scope, SRS-PPNN ID scheme, MoSCoW classification, glossary reference to PRD §2.1), and §3 System Overview (C4 Level 1 reference to HLD, user roles: balancero/laboratorista/admin/contador/productor, system boundaries) in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T016 [US2] Write §4.1 RECEPCION functional requirements (SRS-RE01 through SRS-RENN): romaneo creation, CPE arrival confirmation via WSCPE, weighbridge integration (gross/tare/net), truck queue management. Each requirement as table row: ID | shall-statement | MoSCoW priority | PRD §4.1 source | spec-10 | API endpoint in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T017 [P] [US2] Write §4.2 CALIDAD requirements (SRS-CA01...: quality analysis, humedad/grado, tolerance tables, bonificacion/rebaja) and §4.3 ALMACENAMIENTO requirements (SRS-AL01...: storage unit management, silo assignment, posicion consolidada, merma calculation). Same table format. PRD §4.2-§4.3 sources, spec-09/10/11 assignments in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T018 [US2] Write §4.4 CUENTAS CORRIENTES requirements (SRS-CC01...: producer accounts, movements, balance tracking, campaign segregation, PRD §4.4, spec-12) and §5 Phase 2 Deferred requirements (SRS-LQ01, SRS-FA01, SRS-AG01, SRS-CJ01 stubs marked "Deferred") in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T019 [US2] Write §6 External Interface Requirements: §6.1 ARCA SOAP interfaces (SRS-IF01..., SOAP/XML over HTTPS, WSAA TRA auth, cross-ref to 08a), §6.2 Weighbridge hardware (SRS-HW01..., RS-232 9600/8N1/DB-9/15m, Modbus RTU 03h/06h/10h Sipel Orion, ASCII GaMa A12 STX/ETX, KYASERV TCP/IP bridge), §6.3 REST API interfaces (SRS-IF10..., reference spec-06) in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T020 [P] [US2] Write §7 Performance Requirements (SRS-PF01-05: <500ms API, <30s sync, <5min romaneo, concurrent users, DB query), §8 Security Requirements (SRS-SE01-06: JWT RS256, RLS 3-layer, AES-256-GCM, Argon2, SSRF, rate limiting), §9 Data Requirements (SRS-DA01-04: entity inventory, DECIMAL(17,3), ON DELETE per ADR-012, campaign segregation) in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T021 [US2] Write §10 Traceability Matrix (table: PRD user story → SRS-ID → impl spec 09-12 → REST API endpoint → pytest marker, zero empty cells in Must rows), §11 Constraints and Assumptions (ARCA compliance, offline-first, 2-developer team, weighbridge model diversity), §12 Appendix: Requirement ID Namespace (13 PP codes with reserved NN ranges) in `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- [x] T022 [US2] Run Gate 2 validation on `Docs/Project Blueprint/Software Requirements Specification (SRS).md`: `grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC"` ≥20, `grep -ci "shall"` ≥30, `grep -c "baud\|parity\|Modbus\|RS-232"` ≥5, `grep -ci "TBD\|TODO\|placeholder"` =0. Fix any failures before proceeding.

**Checkpoint**: 08c complete and gate-validated. QA can now trace any Phase 1 requirement to its PRD source, API endpoint, and test marker.

---

## Phase 5: User Story 3 — AI/ML Feature Roadmap (Priority: P2)

**Goal**: Architect can answer "What data do we need to collect during Phases 1-2 to enable Phase 3 ML?"

**Independent Test**: Gate 3 grep checks pass (ML models ≥4, Layers ≥8, ADRs ≥3, TBD=0)

### Implementation for User Story 3

- [x] T023 [US3] Write §1 Document Metadata (version header, upstream refs: HLD §12, Roadmap §7, Data Model, ADR-033/034/035) and §2 Strategic Context (why AI/ML for acopio, ADR-033 data advantage, competitive differentiation — no competitor has ML, AGIS on VB6) in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T024 [US3] Write §3 4-Layer Data Architecture: Layer 1 Operational (DECIMAL(17,3) grain fields), Layer 2 Behavioural (operator_id, device_id, 6 timestamps per ADR-035), Layer 3 Quality History (QualityAnalysis longitudinal), Layer 4 Physical State/IoT (StorageUnit.environment_sensor_id FK). Include Mermaid diagram showing layers→ML models. Cite ADR-033/034/035 in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T025 [US3] Write §4 ML Model Catalog in Roadmap §7.1 priority order: P3-Q1 predictive merma (regression, tabular, highest ROI), P3-Q2 price optimization (MAT + AccountMovement), P3-Q3 anomaly detection (IoT sensors), P3-Q4 NLQ (LLM→SQL). Add HLD §12.6 informative candidates (silo assignment, weighbridge fraud) and deferred computer vision. Each with: description, inputs, target, min data, timeline in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T026 [P] [US3] Write §5 Feature Engineering Strategy (raw field→feature transforms, temporal windows per-campaign/rolling-30d, cross-entity joins Romaneo×QualityAnalysis×StorageUnit) and §6 Training Data Collection Plan (≥10,000 romaneos, ≥1 campana, ≥3 operators, null rate monitoring, natural labeling for merma) in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T027 [US3] Write §7 Delivery Sequence (3-phase model from Roadmap — NOT 4-phase, P3-Q1→Q4, Phase 3 triggers: ≥20 customers + ≥10k romaneos + AI pipeline review, Mermaid dependency graph), §8 IoT Integration (temperature/humidity/CO2 sensors, LoRaWAN/Modbus TCP/MQTT, data pipeline to QualityAnalysis), §9 Vector Search/NLQ Strategy (Qdrant dev-only Phases 1-2, NLQ via LLM→SQL not embedding search) in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T028 [P] [US3] Write §10 Infrastructure Requirements (CPU training for tabular models, external LLM for NLQ, merma inference <200ms, price signals hourly batch, feature store optional) and §11 ADR Cross-Reference table (ADR-033, ADR-034, ADR-035 with titles, impacts, section references) in `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T029 [US3] Run Gate 3 validation on `Docs/Project Blueprint/AI-ML Feature Roadmap.md`: `grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language"` ≥4, `grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4"` ≥8, `grep -c "ADR-033\|ADR-034\|ADR-035"` ≥3, `grep -ci "TBD\|TODO\|placeholder"` =0. Fix any failures before proceeding.

**Checkpoint**: 08b complete and gate-validated. Architect can now justify every ADR-033/034/035 schema decision.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate consistency across all three documents and verify done criteria

- [x] T030 Run cross-document terminology consistency check: verify all three documents use canonical terms from Data Model and PRD glossary (romaneo, merma, liquidacion, CPE, CTG, campana, peso bruto/neto/tara, grado asignado, bonificacion/rebaja, posicion consolidada, cuenta corriente). Fix any inconsistencies in all three files under `Docs/Project Blueprint/`
- [x] T031 Verify all Mermaid diagrams render correctly by previewing: 08a must have ≥3 (hub-spoke, WSAA sequence, CPE state machine), 08b must have ≥2 (data layers, delivery sequence). Fix any syntax errors in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` and `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
- [x] T032 Verify all cross-document references are correct: 08c §6.1 references 08a for ARCA details, 08c §4 API endpoint column matches REST API Design v1.0, 08c §10 traceability matrix has zero empty cells in Must-priority rows, 08b §7 uses Roadmap 3-phase model (SC-007). Also spot-check 3 sections per document for FR-027 compliance (expand, not copy-paste): compare against upstream HLD §6/§12 and PRD §4 to confirm new detail was added. Fix any broken references or copy-paste violations across all files under `Docs/Project Blueprint/`
- [x] T033 Final validation sweep: `grep -rci "TBD\|TODO\|placeholder" "Docs/Project Blueprint/ARCA Grain Integration Guide.md" "Docs/Project Blueprint/AI-ML Feature Roadmap.md" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"` must return 0 for each file. Verify ADR citation format "ADR-NNN (Title)" is consistent. Confirm no implementation code (Python/SQL/shell) exists in any document.

**Checkpoint**: All three documents validated. Done criteria from plan.md fully met.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — RAG queries need Qdrant running
- **US1/08a (Phase 3)**: Depends on Foundational — needs RAG results from T004
- **US2/08c (Phase 4)**: Depends on US1/08a — 08c §6.1 cross-references 08a
- **US3/08b (Phase 5)**: Depends on Foundational only — independent of 08a and 08c
- **Polish (Phase 6)**: Depends on all three documents being complete

### User Story Dependencies

- **US1 (08a)**: Can start after Phase 2. No dependency on other stories.
- **US2 (08c)**: Depends on US1 (08a) for ARCA interface cross-references in §6.1.
- **US3 (08b)**: Can start after Phase 2. Independent of US1 and US2.
- **US4 (validation)**: Depends on US1 + US2 + US3 all complete.

### Within Each User Story

- Sections are written sequentially (same file, must maintain document flow)
- Earlier sections provide context for later sections within same document
- Gate check runs after all sections complete

### Parallel Opportunities

- T004, T005, T006 can all run in parallel (different RAG query sets)
- US1 (08a) and US3 (08b) can run in parallel after Phase 2 (different files)
- Within US1: T011 (§6-§7) can run in parallel with T007-T010 (different sections, same file but non-overlapping)
- Within US2: T017 (§4.2-§4.3) and T020 (§7-§9) can run in parallel
- Within US3: T026 (§5-§6) and T028 (§10-§11) can run in parallel
- T030-T033 (Polish) are sequential — each validates different aspects

---

## Parallel Example: Phase 3 + Phase 5 Concurrent

```text
# After Phase 2 completes, launch both documents in parallel:

# Stream 1: US1 (08a — ARCA Integration Guide)
Task T007: Write §1-§2 (metadata, service overview, hub-spoke diagram)
Task T008: Write §3 (WSAA authentication, sequence diagram)
Task T009: Write §4 (WSLPG, XML fields, retention tiers)
...through T014 (Gate 1)

# Stream 2: US3 (08b — AI/ML Feature Roadmap)
Task T023: Write §1-§2 (metadata, strategic context)
Task T024: Write §3 (4-layer data architecture, diagram)
Task T025: Write §4 (ML model catalog)
...through T029 (Gate 3)

# After Stream 1 completes: US2 (08c — SRS, depends on 08a)
Task T015-T022

# After all streams complete: Polish (Phase 6)
Task T030-T033
```

---

## Implementation Strategy

### MVP First (08a Only)

1. Complete Phase 1: Setup (context loading)
2. Complete Phase 2: Foundational (RAG queries)
3. Complete Phase 3: US1 — 08a ARCA Grain Integration Guide
4. **STOP and VALIDATE**: Run Gate 1. Developer can now implement ARCA integration.
5. Proceed to 08c and 08b

### Incremental Delivery

1. Setup + Foundational → RAG results ready
2. Write 08a → Gate 1 passes → Developers unblocked for spec-10/14
3. Write 08c → Gate 2 passes → QA unblocked for test plans on spec-09-12
4. Write 08b → Gate 3 passes → AI data strategy justified, schema decisions defended
5. Polish → Cross-document validation → Spec-08 complete

### Parallel Strategy (2 writers)

1. Both writers complete Setup + Foundational together
2. Writer A: 08a (US1) → then 08c (US2, depends on 08a)
3. Writer B: 08b (US3, independent)
4. Both: Polish phase together

---

## Notes

- All file writes target `Docs/Project Blueprint/` directory
- No implementation code in any document — Mermaid diagrams and XML summaries are allowed
- 08c **overwrites** the existing stale retail SRS — preserve nothing
- ADR citation format: always "ADR-NNN (Title)"
- Spanish domain terms retained without translation
- 08b MUST use Roadmap's 3-phase model (Phase 3 = ML, not Phase 4)
- Gate checks are the "tests" for this blueprint spec — run after each document
