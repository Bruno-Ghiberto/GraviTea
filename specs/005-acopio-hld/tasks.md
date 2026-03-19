# Tasks: High-Level Design (HLD) Document

**Input**: Design documents from `specs/005-acopio-hld/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅
**Deliverable**: `Docs/Project Blueprint/High-Level Design (HLD).md`

**Project type**: Blueprint documentation (spec-05). This is a document writing task, not a code
implementation. "Implementation" means writing each HLD section. No test tasks — the
`quickstart.md` verification script serves as the acceptance gate.

**Key reference**: `Docs/PROMPTS/spec-05-hld/05-plan.md` — section-by-section writing guide with
Mermaid starter skeletons, domain facts, and verbatim constraint sentences. Read this file before
writing each section.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent sections, no dependency)
- **[Story]**: Which user story this section primarily serves (US1–US4)

---

## Phase 1: Setup

**Purpose**: Verify sources and create the document skeleton.

- [x] T001 Verify all upstream sources are readable: `Docs/Project Blueprint/Architecture Decision Records (ADR).md`, `Docs/Project Blueprint/Data Model & Domain Model.md`, `Docs/Project Blueprint/PRD.md` — confirm each file exists and has content
- [x] T002 Create `Docs/Project Blueprint/High-Level Design (HLD).md` with a skeleton of all 13 H2 section headings (§1–§13) and placeholder H3 subsection stubs, so every subsequent task has a target location to fill in

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Document metadata, overview, and §13 skeleton must exist before any section content
is written. §13 is scaffolded early as a tracking mechanism and completed last.

**⚠️ CRITICAL**: No user story content tasks can begin until this phase is complete.

- [x] T003 Write §1 Document Metadata table in `Docs/Project Blueprint/High-Level Design (HLD).md` — Version 1.0, Date 2026-03-17, Status Accepted, Owner GraviTea Architecture Team, Upstream Documents row (ADR v1.0, Data Model v1.0, PRD v1.0, Vision v1.0)
- [x] T004 Write §2 System Overview in `Docs/Project Blueprint/High-Level Design (HLD).md` — §2.1 what the document is, §2.2 explicit out-of-scope list (database ERD, ADR rationale, REST API specs, ARCA SOAP schemas, Phase 4 ML details, frontend), §2.3 how to read (ADR-NNN citation format, Mermaid notation)
- [x] T005 Scaffold §13 Technology Cross-Reference Table skeleton in `Docs/Project Blueprint/High-Level Design (HLD).md` — table with 8 category rows (Infrastructure, Data Architecture, Grain Domain, Security, Fiscal Integration, Offline & Sync, Performance, AI/ML Readiness) and placeholder ADR IDs; note "fill after §3–§12 complete"

**Checkpoint**: §1, §2, §13 skeleton present → user story sections can now be written.

---

## Phase 3: User Story 1 — Developer Architecture Reference (Priority: P1) 🎯 MVP

**Goal**: A developer reads the HLD and can immediately identify which Django app owns any domain
entity, understand the container topology, trace the romaneo reception flow, and know what happens
to CPE calls when the server is offline.

**Independent Test**: Give a developer who has read only this document: "Which Django app handles
CPE lifecycle calls, and what happens to those calls when the server is offline?" They answer
within 2 minutes using only sections 4, 5, 8, and 9.

- [x] T006 [US1] Write §3.1 C4 Level 1 System Context Mermaid `graph TD` diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — expand the starter skeleton from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 1`; include all 8 external actors (ARCA WSAA, WSLPG, WSCPE, WSFEv1, Weighbridge Device, Browser Client, Mobile Client Phase 3, Operator PC); label every arrow with protocol
- [x] T007 [US1] Write §3.2 External Actor Descriptions and §3.3 System Boundary in `Docs/Project Blueprint/High-Level Design (HLD).md` — one paragraph per external actor (purpose, protocol, regulatory context); state what is inside the boundary (Django containers) and outside (ARCA services, physical devices, browsers); cite ADR-025 for ARCA, ADR-032 for weighbridge
- [x] T008 [US1] Write §4.1 C4 Level 2 Container Architecture Mermaid `graph TD` diagram with subgraph in `Docs/Project Blueprint/High-Level Design (HLD).md` — expand starter skeleton from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 2`; 5 containers (Django API, PostgreSQL 18.1, Redis 7.x, Rust Extension .so, Qdrant optional); every connection arrow labeled with exact protocol string (SQL psycopg3, redis-py, Python FFI import, HTTP/JSON); mark Qdrant optional
- [x] T009 [P] [US1] Write §4.2 Container Descriptions table in `Docs/Project Blueprint/High-Level Design (HLD).md` — one row per container: technology, version, role, port (Django 3.14.3/5.2.x/8000, PostgreSQL 18.1/5432, Redis 7.x/6379, Rust 1.93.1+PyO3 0.28+Maturin 1.12.4/N/A, Qdrant/6333); note Python fallback activates automatically if Rust .so fails to load at startup
- [x] T010 [P] [US1] Write §4.3 Communication Matrix in `Docs/Project Blueprint/High-Level Design (HLD).md` — table of container × container connections with protocol, direction, and purpose
- [x] T011 [US1] Write §4.4 Rust/PyO3 Acceleration Boundary in `Docs/Project Blueprint/High-Level Design (HLD).md` — 4 criteria for using Rust (>1,000 calls/sec hot path; GIL contention in batch; CPU-bound crypto/regex/merma; adversarial input requiring ReDoS protection); complete 7-row benchmark table with × symbol (8.7×, 8.8×, 4.4×, 3.1×, 2.7×, 2.1×, 2.6×) including feature branch column; cite ADR-031
- [x] T012 [US1] Write §5 Component Overview — all 8 Django apps (§5.1–§5.8) in `Docs/Project Blueprint/High-Level Design (HLD).md` — use consistent structure per app: brief description, owned entities, key external calls, phase annotation; `apps/facturacion` and `apps/liquidaciones` MUST include "(Phase 2)" annotation; use entity ownership table from `specs/005-acopio-hld/research.md §6`; cite ADRs per app (ADR-021/023 for auth, ADR-024 for core SSRF, ADR-028–030 for sync, ADR-031 for observability)
- [x] T013 [US1] Write §8.1–§8.3 Offline-First Architecture in `Docs/Project Blueprint/High-Level Design (HLD).md` — §8.1 principle: cite "44% of operators report 'regular' connectivity" (INTA/ENACOM 2021) and state "offline is the base operating mode, not a degraded fallback" (ADR-028); §8.2 local data store (SQLite client / on-premises PostgreSQL, UUID v4 prevents collision); §8.3 sync protocol (push/pull idempotent, vector clock, SyncSession watermark)
- [x] T014 [US1] Write §8.4 Conflict Resolution Engine table in `Docs/Project Blueprint/High-Level Design (HLD).md` — exactly 5 rows: `server_wins` (config data), `last_write_wins` (inventory levels), `additive` (sales/romaneo), `most_complete_wins` (customer/producer data), `server_assigns_final` (document numbering); include Implementation column; cite ADR-029
- [x] T015 [US1] Write §8.5 Store-and-Forward Queue in `Docs/Project Blueprint/High-Level Design (HLD).md` — PendingOperation entity fields (operation_type, payload, status, retry_count); durable across device restarts; FIFO on reconnect; list 3 queued CPE operations (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor); state explicitly that store-and-forward is NOT used for fiscal invoice issuance; cite ADR-030
- [x] T016 [US1] Write §9.1 Romaneo Reception Flow in `Docs/Project Blueprint/High-Level Design (HLD).md` — `sequenceDiagram` using starter from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 5`; MUST have exactly 10 steps; followed by numbered step list naming responsible component at each step (use table from `specs/005-acopio-hld/research.md §7`); add offline note on step 1 (weighbridge watchdog) and queue note on step 10 (PendingOperation)
- [x] T017 [US1] Write §9.3 Sync Data Flow diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — `sequenceDiagram` or `flowchart`; nodes: Local write → SyncSession queue → connectivity check → batch push → conflict resolution → server merge → pull delta → local apply; cite ADR-028 and ADR-030

**Checkpoint (Gate 1)**: Run Gate 1 verification from `specs/005-acopio-hld/plan.md` — all 8 external actors, Version 1.0, zero reproduced ADR headings.

---

## Phase 4: User Story 2 — Architect ARCA Integration Evaluation (Priority: P2)

**Goal**: An architect reads §6 and can answer within 5 minutes: "Why can't we use store-and-forward
CAE for offline invoicing?" and "What happens if the WSAA token expires mid-WSLPG batch?"

**Independent Test**: Select section 6 (ARCA Integration Architecture). Both questions answerable
from §6 alone within 5 minutes.

- [x] T018 [US2] Write §6.1 ARCA Hub-and-Spoke Overview Mermaid `graph LR` diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — WSAA at center, three spokes to WSLPG, WSCPE, WSFEv1; label each spoke with service name and SOAP method category; cite ADR-025
- [x] T019 [US2] Write §6.2 WSAA Authentication Flow `sequenceDiagram` in `Docs/Project Blueprint/High-Level Design (HLD).md` — expand starter from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 4`; participants: Django App, Redis Cache, ARCA WSAA; show cache HIT and MISS paths (alt block); TRA XML generation → X.509 CMS signing → Base64 → LoginCMS → TA (Token+Sign) 12-hour expiry → Redis 11-hour TTL; add WSAA timeout error path (exponential backoff retry) and token expiry mid-batch path (re-authenticate and resume)
- [x] T020 [US2] Write §6.3 WSLPG Integration in `Docs/Project Blueprint/High-Level Design (HLD).md` — production URL and homologation URL (from `specs/005-acopio-hld/research.md §5`); note homologation requires pre-seeded ARCA test CUITs; `liquidacionAutorizar` returns COE; `codGrano` at XML root — one submission per grain type (ADR-019); SISA blocking gate before every filing with all 4 retention tiers (Estado 1–3 + non-registered withholding percentages from `research.md §4`); cite ADR-027
- [x] T021 [US2] Write §6.4 WSCPE Lifecycle in `Docs/Project Blueprint/High-Level Design (HLD).md` — 4 WSCPE protocol states: Activa (issued, 5-day Automotor validity) → Arribo (confirmarArriboCPE) → Descargada (descargadoDestinoCPE) → Confirmada_Definitiva (confirmacionDefinitivaCPEAutomotor); note "Vencida" is a derived condition (timer), not a WSCPE state code; alert on approaching expiry during outage; no automatic extension
- [x] T022 [US2] Write §6.5 WSFEv1/CAEA in `Docs/Project Blueprint/High-Level Design (HLD).md` — WSFEv1 per-invoice CAE round-trip (FECAESolicitar → CAE code returned); CAEA offline pre-authorisation (quincena batch, Rust CAEA batch builder feature-024); MUST include verbatim sentence: "CAEA codes MUST be obtained before the offline period begins. An invoice issued with a deferred CAE (authorization obtained after issuance) is a legally invalid fiscal document."; cite ADR-026
- [x] T023 [US2] Write §6.6 Certificate Management in `Docs/Project Blueprint/High-Level Design (HLD).md` — each ARCA service (WSLPG, WSCPE, WSFEv1) requires a separate X.509 certificate; shared certificate is rejected; private keys in Google Cloud Secret Manager; keys never in code, env vars, Docker configs, or git history; cite ADR-022
- [x] T024 [US2] Write §6.7 ARCA Error Paths in `Docs/Project Blueprint/High-Level Design (HLD).md` — WSAA timeout (exponential backoff + retry); token expiry mid-batch (re-authenticate and resume at current operation); WSLPG rejection (schema error → user-facing error, SISA block → user-facing error); CPE validity window expiry → operator alert, no automatic extension
- [x] T025 [US2] Write §9.2 Fiscal Authorization Flow in `Docs/Project Blueprint/High-Level Design (HLD).md` — `flowchart TD` using starter from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 6`; Invoice Draft → online/offline decision → CAE subgraph (WSAA→TA, WSFEv1.FECAESolicitar, CAE received) → CAEA subgraph (CAEA available? → Assign code OR INVOICING BLOCKED); add note on Blocked node referencing CAEA legal constraint sentence; show quincena batch pre-fetch that populates CAEA codes before offline period

**Checkpoint (Gate 2)**: Run Gate 2 verification — CAEA legal constraint sentence, codGrano, 8.7×/8.8×/4.4× benchmark values, Phase 2 annotations present.

---

## Phase 5: User Story 3 — Product Owner Deployment and Connectivity Review (Priority: P3)

**Goal**: A product owner reads §8 and §11 and can answer: "Can a client run on a single server?"
and "What happens if the internet goes out during harvest?"

**Independent Test**: Read sections 8.1, 8.6, and 11.2. Answer both questions within 3 minutes.

- [x] T026 [US3] Write §8.6 CAEA Offline Fiscal Path in `Docs/Project Blueprint/High-Level Design (HLD).md` — quincena codes must be obtained before the offline period begins (connects to CAEA legal constraint in §6.5); invoicing blocked (not degraded) if CAEA codes were not obtained before connectivity loss; no automatic workaround; operator must plan harvest connectivity windows to obtain CAEA codes before going offline
- [x] T027 [US3] Write §8.7 Offline Error Paths in `Docs/Project Blueprint/High-Level Design (HLD).md` — CPE validity window (5-day Automotor): operator alert on approaching expiry during outage; no automatic extension; CAEA quincena expiry during extended outage: invoicing blocked, no workaround; both require operator action
- [x] T028 [US3] Write §11.1 Development Docker Compose Environment in `Docs/Project Blueprint/High-Level Design (HLD).md` — services list: django-api (:8000), postgres (:5432), redis (:6379), rust-builder (Maturin build stage, NOT a runtime service), qdrant (:6333, optional, disabled by default); Rust modules built in multi-stage Docker build (rust-builder stage); local weighbridge simulated via mock serial device
- [x] T029 [US3] Write §11.2 Production Topology Narrative in `Docs/Project Blueprint/High-Level Design (HLD).md` — target: 1–5 plants, small-to-medium acopiadores; full-cloud option: Django + PostgreSQL on GCP Cloud Run + Cloud SQL Enterprise Plus; hybrid option: plant server (Windows or Linux PC) with offline client + local PostgreSQL, cloud server handles sync and ARCA calls; deployment unit: single Django process, modular monolith (ADR-003); no microservices, no service mesh, no Kubernetes for initial scale
- [x] T030 [US3] Write §11.3 Production Topology Mermaid `graph TD` diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — two topology options side-by-side (full-cloud and hybrid) with labeled arrows; full-cloud: Browser/OperatorPC → Cloud Run Django → Cloud SQL; hybrid: OperatorPC → Plant Server (Django + local PostgreSQL) → Cloud Sync Server → ARCA services
- [x] T031 [US3] Write §11.4 Infrastructure Cost Rationale in `Docs/Project Blueprint/High-Level Design (HLD).md` — shared schema fixed DB cost regardless of tenant count (ADR-004); compatible with USD 90–360/month SMB SaaS budget; no per-tenant database (cite ADR-003 modular monolith and ADR-004 shared schema cost model)

**Checkpoint (Gate 3)**: Run Gate 3 verification — all 3 CPE WSCPE method names, 5 conflict resolution strategies, 44% connectivity statistic, KYASERV named.

---

## Phase 6: User Story 4 — New Team Member System Onboarding (Priority: P3)

**Goal**: A new team member reads only the HLD and can (a) sketch the C4 container diagram,
(b) name all 5 conflict resolution strategies, (c) describe the 3-layer security model,
(d) explain what data the system collects for Phase 4 ML features.

**Independent Test**: New team member reads HLD only. Can answer (a)–(d) without consulting
specs 01–04.

- [x] T032 [US4] Write §7.1 Weighbridge 3-Tier Protocol Stack Mermaid `graph TD` diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — 3 tiers stacked vertically: Tier 1 (Modbus RTU/ASCII), Tier 2 (Continuous ASCII stream), Tier 3 (KYASERV network bridge); WeighbridgeDevice entity connects to Django API via each tier path; cite ADR-032
- [x] T033 [P] [US4] Write §7.2 Tier 1 Weighbridge Protocols in `Docs/Project Blueprint/High-Level Design (HLD).md` — RS-232: 9600 baud, 8N1 (universal baseline); Sipel Orion Modbus RTU: memory map Address 0=Gross weight (2 regs, 32-bit signed int), Address 2=Tare, Address 4=Net, Address 6=Flags; functions 03h/06h/10h; Systel (Clipse, Croma, Bumer): command/response ASCII over RS-232, no Modbus support; cite ADR-032
- [x] T034 [P] [US4] Write §7.3 Tier 2 Continuous ASCII Stream in `Docs/Project Blueprint/High-Level Design (HLD).md` — GaMa A12 fallback; frame: {STX}{weight}{CR/LF} at 9600 baud, 8N1; continuous stream parsing; cite ADR-032
- [x] T035 [US4] Write §7.4 Tier 3 KYASERV Bridge in `Docs/Project Blueprint/High-Level Design (HLD).md` — RS-232-to-Ethernet bridge; converts RS-232 to UDP/TCP-IP over LAN; application server connects to KYASERV IP:port; eliminates requirement for app server to be co-located on weighbridge PC; cite ADR-032
- [x] T036 [US4] Write §7.5 WeighbridgeDevice Entity and §7.6 Weighbridge Error Paths in `Docs/Project Blueprint/High-Level Design (HLD).md` — §7.5: first-class entity with interface_type, connection_address, calibration records; Romaneo.weighbridge_device_id nullable FK (SET_NULL on decommission); note explicitly that the 3-tier stack covers all major Argentine weighbridge brands currently on the market and that new brands not in this stack require a new driver implementation before integration is possible; §7.6: RS-232 disconnect → watchdog reconnection loop + operator alert; stable-weight timeout → configurable threshold + manual entry override; KYASERV unreachable → fall back to manual entry mode
- [x] T037 [US4] Write §10.1 Defense-in-Depth Mermaid `graph TD` diagram in `Docs/Project Blueprint/High-Level Design (HLD).md` — expand starter from `Docs/PROMPTS/spec-05-hld/05-plan.md §5 Diagram 3`; Incoming API Request → Layer 1 ORM TenantBoundManager → Layer 2 PostgreSQL RLS → Layer 3 IDOR Validation → Tenant-Isolated Data; add rejection/error paths (HTTP 403) out of each layer for failed checks; cite ADR-005
- [x] T038 [P] [US4] Write §10.2 Layer 1 ORM TenantBoundManager in `Docs/Project Blueprint/High-Level Design (HLD).md` — TenantBoundManager auto-filters ALL ORM queries by tenant_id; inheritance pattern; cite ADR-005
- [x] T039 [P] [US4] Write §10.3 Layer 2 PostgreSQL RLS in `Docs/Project Blueprint/High-Level Design (HLD).md` — `SET LOCAL app.current_tenant_id = '{uuid}'` (transaction-scoped session variable); USING policy: `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)` applied on all per-tenant tables; global tables (GrainType, ToleranceTable) exempt (ADR-010); cite ADR-005, ADR-010
- [x] T040 [P] [US4] Write §10.4 Layer 3 IDOR/JWT Validation in `Docs/Project Blueprint/High-Level Design (HLD).md` — JWT RS256 claims checked on every request: iss, aud, exp, tenant_id, branch_id; algorithm whitelist: RS256 only; HS256/none rejected at middleware; 4096-bit RSA key; access token 15 min; refresh token 7 days; cite ADR-021
- [x] T041 [P] [US4] Write §10.5 Field-Level Encryption in `Docs/Project Blueprint/High-Level Design (HLD).md` — AES-256-GCM for PII; HMAC-SHA256 blind index for searchable fields; encrypted fields: producer CUIT, full name, address, DNI, contact data; blind index limitation: equality search only — no range queries, no LIKE patterns on encrypted fields; cite ADR-022
- [x] T042 [US4] Write §10.6 Key Management in `Docs/Project Blueprint/High-Level Design (HLD).md` — all master keys in Google Cloud Secret Manager; never in code, env vars, Docker configs, or git history; separate key per ARCA service certificate; cite ADR-022
- [x] T043 [US4] Write §12.1–§12.5 AI/ML Readiness 4-Layer Strategy in `Docs/Project Blueprint/High-Level Design (HLD).md` — §12.1 overview; §12.2 Layer 1 Operational (DECIMAL(17,3) precision, all grain domain fields real-time with full timestamps, ADR-007); §12.3 Layer 2 Behavioural (operator_id, laboratorista_id, device_id on all grain domain models; 6 named romaneo timestamps: ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara; ADR-034); §12.4 Layer 3 Quality History (QualityAnalysis rows per grain_type/campaign/storage_unit; longitudinal record enables degradation prediction; ADR-035); §12.5 Layer 4 Physical State/IoT (StorageUnit.environment_sensor_id as nullable FK anchor; populating this FK in a future phase requires no structural schema change; ADR-033)
- [x] T044 [P] [US4] Write §12.6 Phase 4 ML Capabilities (informative) in `Docs/Project Blueprint/High-Level Design (HLD).md` — 3D-CNN + LSTM grain quality prediction; silo assignment optimisation; weighbridge fraud detection; pizarra price forecasting; explicitly note: "Detailed ML model architecture and training pipeline specifications are out of scope for this document and are deferred to spec-08b"
- [x] T045 [P] [US4] Write §12.7 Qdrant Optional Container in `Docs/Project Blueprint/High-Level Design (HLD).md` — used in development for RAG-based query expansion; not required for Phase 1 or Phase 2 production deployments; optional flag in Docker Compose (disabled by default)

**Checkpoint (Gate 4)**: Run Gate 4 verification — `SET LOCAL app.current_tenant_id`, Docker ports `:8000/:5432/:6379`, `environment_sensor_id`, 6 romaneo timestamps.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Complete §13, validate Mermaid syntax, run final acceptance checks.

- [x] T046 Complete §13 Technology Cross-Reference Table in `Docs/Project Blueprint/High-Level Design (HLD).md` — fill in all ADR IDs from sections written in Phases 3–6; ensure every HLD section §3–§12 maps to at least one ADR-NNN reference; table columns: HLD Section | ADR IDs | ADR Titles | Category; grouped by 8 ADR categories (Infrastructure, Data Architecture, Grain Domain, Security, Fiscal Integration, Offline & Sync, Performance, AI/ML Readiness)
- [x] T047 [P] Verify all 7 Mermaid diagrams render without syntax errors in `Docs/Project Blueprint/High-Level Design (HLD).md` — paste each mermaid block into mermaid.live or run `mmdc`; diagrams: C4 L1 (§3.1), C4 L2 (§4.1), WSAA auth flow (§6.2), romaneo flow (§9.1), fiscal flow (§9.2), defense-in-depth (§10.1), production topology (§11.3); fix any syntax errors
- [x] T048 [P] Run Gate 5 final verification in `Docs/Project Blueprint/High-Level Design (HLD).md` — `grep -i "TBD\|TODO\|FIXME\|possibly\|might consider"` → 0 matches; `grep -c "^## \|^### "` → ≥40; `grep -c '```mermaid'` → ≥6; replace any hedging language with declarative statements
- [x] T049 Run quickstart.md full gate verification script on `Docs/Project Blueprint/High-Level Design (HLD).md` — execute the bash script from `specs/005-acopio-hld/quickstart.md §Full Gate Verification`; all 13 checks must show ✓; fix any failures before marking tasks complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion
- **US1 (Phase 3)**: Depends on Foundational — no dependencies on US2/US3/US4
- **US2 (Phase 4)**: Depends on Foundational — can run in parallel with US1 (different sections)
- **US3 (Phase 5)**: Depends on Foundational — can run in parallel with US1/US2 (§8.6, §11 are independent of §6)
- **US4 (Phase 6)**: Depends on Foundational — §7 and §10 are independent; §12 is independent
- **Polish (Phase 7)**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Sections §3, §4, §5, §8.1–§8.5, §9.1, §9.3 — no cross-story dependencies
- **US2 (P2)**: Sections §6.1–§6.7, §9.2 — references §8 for CAEA offline context (informative only; §8 need not be complete before §6 is written)
- **US3 (P3)**: Sections §8.6–§8.7, §11 — references §6.5 CAEA legal constraint (write §6.5 first or note "see §6.5" as a placeholder)
- **US4 (P3)**: Sections §7, §10, §12 — fully independent of US1/US2/US3

### Within Each User Story

- Sequential where diagram comes before prose description (T008 diagram before T009 prose descriptions)
- Tasks marked [P] within a phase are independent and can be done in any order

### Parallel Opportunities

- US1, US2, US3, US4 phases can all be worked in parallel by different authors after Phase 2 completes
- Within US4: §7 (weighbridge) and §10 (security) and §12 (AI/ML) are fully independent of each other
- Within US3: §11 (deployment) is independent of §8.6 (CAEA offline path)
- T047 and T048 in Polish phase can run in parallel

---

## Parallel Example: Running US3 and US4 Simultaneously

```text
After Phase 2 completion and US1+US2 sections written:

Author A — US3:
  T026: Write §8.6 CAEA Offline Fiscal Path
  T027: Write §8.7 Offline Error Paths
  T028: Write §11.1 Docker Compose Environment
  T029: Write §11.2 Production Topology Narrative
  T030: Write §11.3 Production Topology Diagram
  T031: Write §11.4 Infrastructure Cost Rationale

Author B — US4 (fully parallel with Author A):
  T032: Write §7.1 Weighbridge Diagram
  T033 [P], T034 [P]: Write §7.2 Tier 1 and §7.3 Tier 2 (parallel)
  T035: Write §7.4 KYASERV Tier 3
  T036: Write §7.5 Entity + §7.6 Error Paths
  T037: Write §10.1 Defense-in-Depth Diagram
  T038 [P], T039 [P], T040 [P], T041 [P]: Write §10.2–10.5 (parallel)
  T042: Write §10.6 Key Management
  T043: Write §12.1–12.5 AI/ML 4-Layer Strategy
  T044 [P], T045 [P]: Write §12.6 and §12.7 (parallel)
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T005)
3. Complete Phase 3: US1 (T006–T017)
4. **STOP and VALIDATE**: Run Gate 1 check; confirm a developer can answer the US1 independent test
5. The document is partially useful — §3–§5 and §8–§9 are complete

### Incremental Delivery

1. Setup + Foundational → skeleton ready
2. US1 (P1) → developer reference sections complete → validate
3. US2 (P2) → ARCA integration architecture complete → validate
4. US3+US4 (P3, parallel) → deployment + security + weighbridge + AI/ML → validate
5. Polish → §13 complete, all Mermaid renders, zero hedging language → document ready

---

## Notes

- [P] tasks = different HLD sections, can be written in any order within the phase
- The 14-step writing order in `Docs/PROMPTS/spec-05-hld/05-plan.md §3` is the recommended single-author sequence; the task phases above reflect reader-story priority for multi-author delivery
- Each gate verification command is in `specs/005-acopio-hld/plan.md §Checkpoint Gates`
- Full acceptance verification: `specs/005-acopio-hld/quickstart.md §Full Gate Verification`
- Commit after completing each phase checkpoint
- Do NOT add implementation details (field-level schema, SOAP XML, REST endpoints) — those belong in spec-03, spec-08a, spec-06 respectively
