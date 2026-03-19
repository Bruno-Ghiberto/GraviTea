# Tasks: REST API Design for GraviTea Acopio ERP

**Input**: Design documents from `/specs/006-acopio-api-design/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md
**Deliverable**: `Docs/Project Blueprint/REST API Design.md` v1.0

**Organization**: Tasks are grouped by user story. Since this is a Blueprint spec (single-author document writing), tasks represent sections/content blocks of the deliverable document. The document is written in a single atomic pass but tasks serve as a verification checklist.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (independent content blocks)
- **[Story]**: Which user story this task serves (US1, US2, US3, US4)

## Path Conventions

- Deliverable: `Docs/Project Blueprint/REST API Design.md`
- Upstream sources: `Docs/Project Blueprint/Data Model & Domain Model.md`, `High-Level Design (HLD).md`, `Architecture Decision Records (ADR).md`

---

## Phase 1: Setup

**Purpose**: Gather inputs and prepare the deliverable file

- [x] T001 Read §5.3 Romaneo fields (31 fields, 7 groups) from `Docs/Project Blueprint/Data Model & Domain Model.md`
- [x] T002 [P] Read §5.4 QualityAnalysis fields from `Docs/Project Blueprint/Data Model & Domain Model.md`
- [x] T003 [P] Read §6 ProducerAccount + AccountMovement fields from `Docs/Project Blueprint/Data Model & Domain Model.md`
- [x] T004 [P] Read §5.6 Storage entities from `Docs/Project Blueprint/Data Model & Domain Model.md`
- [x] T005 [P] Read §4 Container Architecture + §10 Security from `Docs/Project Blueprint/High-Level Design (HLD).md`
- [x] T006 [P] Read §8 Offline-First + §9 Data Flow Diagrams from `Docs/Project Blueprint/High-Level Design (HLD).md`
- [x] T007 [P] Run RAG queries from `Docs/PROMPTS/spec-06-api-design/06-plan.md` Research Inputs section
- [x] T008 Create empty file `Docs/Project Blueprint/REST API Design.md`

**Checkpoint**: All upstream sources loaded, file created

---

## Phase 2: Foundation

**Purpose**: Document metadata and design principles — referenced by ALL endpoint sections

- [x] T009 Write §1 Document Metadata in `Docs/Project Blueprint/REST API Design.md` — blockquote `> **Version 1.0** · Date: 2026-03-17 · Status: Accepted`, metadata table, changelog
- [x] T010 Write §2.1 RESTful Resource Orientation in `Docs/Project Blueprint/REST API Design.md` — resources are nouns, actions are sub-resource verbs
- [x] T011 [P] Write §2.2 Versioning Policy in `Docs/Project Blueprint/REST API Design.md` — `/api/v1/` prefix, 12-month deprecation notice
- [x] T012 [P] Write §2.3 Authentication Model in `Docs/Project Blueprint/REST API Design.md` — JWT RS256 bearer, HS256/none rejected, 15-min access / 7-day refresh
- [x] T013 [P] Write §2.4 Tenant Scope Enforcement in `Docs/Project Blueprint/REST API Design.md` — tenant_id from JWT only, HTTP 404 on cross-tenant (not 403)
- [x] T014 [P] Write §2.5 Error Format in `Docs/Project Blueprint/REST API Design.md` — RFC 7807 Problem Details, domain extensions
- [x] T015 [P] Write §2.6 Pagination Strategy in `Docs/Project Blueprint/REST API Design.md` — cursor for ledgers, page-number for lists
- [x] T016 [P] Write §2.7 Filtering & Ordering in `Docs/Project Blueprint/REST API Design.md` — query params, ISO 8601 date ranges
- [x] T017 [P] Write §2.8 Rate Limiting Headers in `Docs/Project Blueprint/REST API Design.md` — X-RateLimit headers, auth: 10/min/IP, standard: 1000/min/tenant
- [x] T018 Verify Gate G2: all 8 §2 subsections present, no Python code in `Docs/Project Blueprint/REST API Design.md`

**Checkpoint**: §1-§2 complete. Design principles established for all endpoint sections to reference.

---

## Phase 3: User Story 1+2 — Endpoint Catalog (Priority: P1)

**Goal**: US1: Every Phase 1 endpoint is documented with field tables. US2: Security model is consistently applied across all endpoints.

**Independent Test**: A reader can answer "What URL, method, request fields, and response codes for [any endpoint]?" from the document alone. A security reviewer confirms no endpoint accepts tenant_id in URL/body.

### §3 Authentication API

- [x] T019 [US1] Write §3.1 POST /api/v1/auth/token/ — request/response field tables, status codes in `Docs/Project Blueprint/REST API Design.md`
- [x] T020 [P] [US1] Write §3.2 POST /api/v1/auth/token/refresh/ — request/response field tables in `Docs/Project Blueprint/REST API Design.md`
- [x] T021 [P] [US1] Write §3.3 POST /api/v1/auth/logout/ — 204 No Content, Redis blacklist in `Docs/Project Blueprint/REST API Design.md`
- [x] T022 [US2] Write §3.4 JWT Claim Reference Table — sub, tenant_id, branch_id, exp, iat, jti, iss, aud in `Docs/Project Blueprint/REST API Design.md`
- [x] T023 Verify Gate G3: 3 auth endpoints with field tables present in `Docs/Project Blueprint/REST API Design.md`

### §4 Grain Reference API

- [x] T024 [P] [US1] Write §4.1 GET /api/v1/acopio/grain-types/ — response field table, note: global table no tenant scope in `Docs/Project Blueprint/REST API Design.md`
- [x] T025 [P] [US1] Write §4.2-§4.3 tolerance-tables + merma-tables endpoints in `Docs/Project Blueprint/REST API Design.md`
- [x] T026 [P] [US1] Write §4.4 GET /api/v1/acopio/campaigns/ — per-tenant, filterable by active_now in `Docs/Project Blueprint/REST API Design.md`

### §5 Romaneo API (largest section)

- [x] T027 [US1] Write §5.1 Romaneo Resource Schema — full request + response field tables from Data Model §5.3 (all 7 groups) in `Docs/Project Blueprint/REST API Design.md`
- [x] T028 [P] [US1] Write §5.2 POST /api/v1/acopio/romaneos/ (create) — request fields, 201 Created in `Docs/Project Blueprint/REST API Design.md`
- [x] T029 [P] [US1] Write §5.3-§5.4 GET list + retrieve endpoints in `Docs/Project Blueprint/REST API Design.md`
- [x] T030 [P] [US2] Write §5.5 PATCH pre-CONFORME guard — HTTP 409 if CONFORME/CERRADO in `Docs/Project Blueprint/REST API Design.md`
- [x] T031 [US1] Write §5.6.1 POST confirmar-arribo/ → EN_PROCESO — HTTP 202, enqueues confirmarArriboCPE in `Docs/Project Blueprint/REST API Design.md`
- [x] T032 [P] [US1] Write §5.6.2 POST peso-bruto/ → PESADO — request: peso_bruto_kg, weighbridge_device_id in `Docs/Project Blueprint/REST API Design.md`
- [x] T033 [P] [US1] Write §5.6.3 POST analizar/ → ANALIZADO — inline 9 QualityAnalysis fields in `Docs/Project Blueprint/REST API Design.md`
- [x] T034 [P] [US1] Write §5.6.4 POST confirmar/ → CONFORME — immutability gate, sets grado/bonificacion/peso_neto_conforme in `Docs/Project Blueprint/REST API Design.md`
- [x] T035 [P] [US1] Write §5.6.5 POST tara/ — tare weight post-unload, computes peso_neto_bruto_kg in `Docs/Project Blueprint/REST API Design.md`
- [x] T036 [US1] Write §5.6.6 POST cerrar/ → CERRADO — HTTP 202, enqueues descargadoDestinoCPE + confirmacionDefinitivaCPEAutomotor, requires tara_kg in `Docs/Project Blueprint/REST API Design.md`
- [x] T037 [P] [US1] Write §5.7 GET merma-preview/ — non-persisting computation in `Docs/Project Blueprint/REST API Design.md`
- [x] T038 [US2] Write §5.9 Immutability Rules — HTTP 409 romaneo_immutable problem detail JSON example in `Docs/Project Blueprint/REST API Design.md`
- [x] T039 Verify Gate G4: 11 romaneo endpoints documented in `Docs/Project Blueprint/REST API Design.md`

### §6 Quality Analysis API

- [x] T040 [US1] Write §6.1 QualityAnalysis Resource Schema — 9 quality parameter fields in `Docs/Project Blueprint/REST API Design.md`
- [x] T041 [P] [US1] Write §6.2-§6.4 create/retrieve/update endpoints with ANALIZADO guard in `Docs/Project Blueprint/REST API Design.md`

### §7 Storage API

- [x] T042 [P] [US1] Write §7.1-§7.2 storage-units list/detail with current_occupancy_kg (derived) in `Docs/Project Blueprint/REST API Design.md`
- [x] T043 [P] [US1] Write §7.3-§7.5 grain-lots list/detail + cursor-paginated movements ledger in `Docs/Project Blueprint/REST API Design.md`

### §8 Weighbridge API

- [x] T044 [P] [US1] Write §8.1-§8.2 weighbridge list + live reading (HTTP 503 on disconnect) in `Docs/Project Blueprint/REST API Design.md`

### §9 Producer Accounts API

- [x] T045 [US1] Write §9.1 Account Resource Schema — ProducerAccount fields in `Docs/Project Blueprint/REST API Design.md`
- [x] T046 [P] [US1] Write §9.2-§9.3 accounts list/detail endpoints in `Docs/Project Blueprint/REST API Design.md`
- [x] T047 [US1] Write §9.4 movements cursor-paginated ledger — note append-only, HTTP 405 on PATCH/DELETE in `Docs/Project Blueprint/REST API Design.md`
- [x] T048 [US1] Write §9.5 GET posicion-consolidada/ — derived view (ADR-013), query params producer_cuit + campaign in `Docs/Project Blueprint/REST API Design.md`
- [x] T049 [P] [US1] Write §9.6-§9.7 fijaciones create/list endpoints in `Docs/Project Blueprint/REST API Design.md`
- [x] T050 [US2] Write §9.8 Encrypted CUIT Field Behaviour Note — blind index equality only in `Docs/Project Blueprint/REST API Design.md`
- [x] T051 Verify Gate G5: posicion consolidada = derived view, encrypted CUIT note present

### §11 Error Reference

- [x] T052 [US2] Write §11.1 RFC 7807 Problem Details Format with JSON example in `Docs/Project Blueprint/REST API Design.md`
- [x] T053 [US2] Write §11.2 Domain Error Type Catalog — 11 error types (romaneo_immutable, invalid_state_transition, tenant_mismatch, tare_weight_required, etc.) in `Docs/Project Blueprint/REST API Design.md`
- [x] T054 [P] [US2] Write §11.3 HTTP Status Code Decision Table (200, 201, 202, 204, 400, 401, 404, 405, 409, 422, 429, 500, 502, 503) in `Docs/Project Blueprint/REST API Design.md`
- [x] T055 Verify Gate G7: ≥ 10 domain error types, HTTP status decision table present

**Checkpoint**: US1+US2 complete — all Phase 1 endpoints documented with field tables, security model consistently applied.

---

## Phase 4: User Story 3 — Offline Sync Flow (Priority: P2)

**Goal**: Frontend/mobile developer can implement a complete sync round-trip from this document alone.

**Independent Test**: Developer can answer "How to pull delta, push mutations, and handle conflicts?" from the document.

- [x] T056 [US3] Write §10.1 Sync Model Overview — watermarks, delta vs full sync, 5 conflict strategies (ADR-029), PendingOperation queue (ADR-030) in `Docs/Project Blueprint/REST API Design.md`
- [x] T057 [US3] Write §10.2 GET /api/v1/sync/delta/ — query param last_seq, response: {server_seq, changes[]} in `Docs/Project Blueprint/REST API Design.md`
- [x] T058 [US3] Write §10.3 POST /api/v1/sync/push/ — request: {mutations[]}, response: per-item conflict signals in `Docs/Project Blueprint/REST API Design.md`
- [x] T059 [P] [US3] Write §10.4-§10.5 pending-ops list + retry endpoints in `Docs/Project Blueprint/REST API Design.md`
- [x] T060 [US3] Write §10.6 Conflict Signal Response Schema — status: accepted|conflict|rejected, conflict_strategy enum, server_version in `Docs/Project Blueprint/REST API Design.md`
- [x] T061 Verify Gate G6: 5 conflict strategies listed, conflict signal schema documented

**Checkpoint**: US3 complete — sync API fully specified.

---

## Phase 5: User Story 4 — Sequence Diagrams (Priority: P2)

**Goal**: 3 Mermaid sequence diagrams illustrating key API flows.

**Independent Test**: Each diagram renders correctly and matches the endpoint definitions in the text.

- [x] T062 [US4] Write §3.5 Authentication Flow Sequence Diagram (Mermaid #1) — Client → API (creds) → JWT → Bearer → Refresh → Logout in `Docs/Project Blueprint/REST API Design.md`
- [x] T063 [US4] Write §5.8 Romaneo Lifecycle Sequence Diagram (Mermaid #2) — 7 transitions with async ARCA calls marked in `Docs/Project Blueprint/REST API Design.md`
- [x] T064 [US4] Write §10.7 Offline Sync Round-Trip Sequence Diagram (Mermaid #3) — delta pull → offline → push → conflict resolution in `Docs/Project Blueprint/REST API Design.md`
- [x] T065 Verify Gate G3+G5+G7: `grep -c '```mermaid'` ≥ 3 in `Docs/Project Blueprint/REST API Design.md`

**Checkpoint**: US4 complete — all 3 diagrams present and consistent with endpoints.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Phase 2 stubs, summary table, and full verification

- [x] T066 Write §12 Phase 2 Endpoints — blockquote `> **Phase 2 — Not active in Phase 1 delivery.**`, 4 placeholder endpoints (liquidaciones + facturación) in `Docs/Project Blueprint/REST API Design.md`
- [x] T067 Write §13 Endpoint Summary Table — all endpoints from §3-§12, columns: Method | URL | App | Phase | Auth | Description, ≥ 35 rows in `Docs/Project Blueprint/REST API Design.md`
- [x] T068 Verify Gate G8: Phase 2 blockquote present in `Docs/Project Blueprint/REST API Design.md`
- [x] T069 Verify Gate G9: endpoint summary table ≥ 35 rows in `Docs/Project Blueprint/REST API Design.md`
- [x] T070 Verify Gate G10: `grep -c "^#"` ≥ 40 headings in `Docs/Project Blueprint/REST API Design.md`
- [x] T071 Verify Gate G11: `grep -ciE 'import |from .* import|class .*View|class .*Serializer'` = 0 in `Docs/Project Blueprint/REST API Design.md`
- [x] T072 Verify Gate G12: `grep -ci 'TBD\|to be determined\|placeholder\|TODO'` = 0 in `Docs/Project Blueprint/REST API Design.md`
- [x] T073 Verify Gate G13: `grep -c '202'` ≥ 2 (confirmar-arribo + cerrar async) in `Docs/Project Blueprint/REST API Design.md`
- [x] T074 Verify Gate G1: `grep 'Version 1.0'` ≥ 2 matches in `Docs/Project Blueprint/REST API Design.md`

**Checkpoint**: All 13 gates pass. Document v1.0 complete and verified.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — read upstream docs
- **Foundation (Phase 2)**: Depends on Setup — §2 Design Principles must be complete before endpoint sections
- **US1+US2 (Phase 3)**: Depends on Foundation — endpoint sections reference §2 conventions
- **US3 (Phase 4)**: Depends on Foundation — sync API references §2 error format + pagination
- **US4 (Phase 5)**: Depends on US1+US2 + US3 — diagrams must match endpoint definitions
- **Polish (Phase 6)**: Depends on all previous — summary table aggregates §3-§12

### User Story Dependencies

- **US1 (P1)** + **US2 (P1)**: Combined in Phase 3 — every endpoint section serves both stories
- **US3 (P2)**: Independent of US1/US2 after Foundation. Can run in parallel with Phase 3 if needed.
- **US4 (P2)**: Depends on US1/US2/US3 — diagrams illustrate endpoints that must be defined first

### Within Each Phase

- §2 subsections (T010-T017) are all parallelizable
- §5 state transition endpoints (T031-T036) are sequential (they form a lifecycle)
- §3, §4, §6-§9 are parallelizable (independent app sections)

### Parallel Opportunities

```
Phase 2: T010-T017 all [P] (8 Design Principles subsections)
Phase 3: T024-T026 [P] (grain ref), T028-T029 [P] (romaneo CRUD),
         T042-T044 [P] (storage + weighbridge), T046+T049 [P] (accounts)
Phase 4: T059 [P] (pending-ops independent of delta/push)
Phase 5: T062-T064 can run in parallel IF sections they reference are already written
```

---

## Implementation Strategy

### Atomic Write Approach (Recommended for Blueprint Specs)

This is a Blueprint spec producing a single Markdown document. The recommended approach:

1. Complete Phase 1 (read upstream docs)
2. Write the ENTIRE document in a single Write pass, covering §1-§13
3. Run all verification gates (Phase 6, T068-T074)
4. Fix any gate failures with targeted Edit calls
5. Mark all tasks [x] retroactively after verification

This approach avoids section-by-section drift. The summary table (§13) must match endpoints defined in §3-§12, so writing atomically ensures consistency.

### Section-by-Section Approach (Alternative)

If the atomic approach exceeds context limits:

1. Phase 1: Setup
2. Phase 2: Write §1-§2 (foundation)
3. Phase 3: Write §3-§9, §11 (endpoints + errors)
4. Phase 4: Write §10 (sync)
5. Phase 5: Add Mermaid diagrams into §3.5, §5.8, §10.7
6. Phase 6: Write §12-§13, run gates

### MVP Definition

MVP = Phase 1 + Phase 2 + Phase 3 (US1+US2). This delivers all Phase 1 endpoint definitions with security model — the core value for implementation specs 09-12.

---

## Notes

- Total tasks: 74 (T001-T074)
- Per-story: US1 = 26 tasks, US2 = 7 tasks, US3 = 5 tasks, US4 = 3 tasks
- Setup = 8, Foundation = 10, Verify gates = 14, Polish = 9
- 32 tasks marked [P] (parallelizable)
- No test tasks — Blueprint spec, verification is grep-based
- Single deliverable file: `Docs/Project Blueprint/REST API Design.md`
