# Spec 06: REST API Design -- Plan Context

## Overview

**Target deliverable**: `Docs/Project Blueprint/REST API Design.md` v1.0
**Creates**: New document (no existing file to replace)
**Type**: Blueprint document (API specification, not code)
**Spec reference**: `specs/006-acopio-api-design/spec.md`
**Context reference**: `Docs/PROMPTS/spec-06-api-design/06-specify.md`

This plan guides the creation of the REST API Design blueprint. The output is a
~1000-1500 line Markdown file with 13 top-level sections, at least 40 headings,
at least 3 Mermaid sequence diagrams, field tables for every Phase 1 endpoint,
and a complete endpoint summary table.

The REST API Design doc is the **authoritative API contract** for all Phase 1
implementation specs (09-12). Every DRF ViewSet, URL pattern, serializer, and
status code in implementation specs derives from this document.

---

## Content Guidelines

### Tone & Voice

- **Technical reference document** — declarative and prescriptive
- "This endpoint MUST return..." not "This endpoint should..."
- No hedging: no "TBD", "to be determined", "under review" markers
- Each endpoint definition is self-contained: a reader can implement it without
  consulting external documents for field names, types, or status codes
- HTTP examples use `curl` notation or JSON request/response blocks, NOT
  Python/Django/DRF code

### Audience

- **Primary**: AI agents running `/speckit.implement` for specs 09-12 (must
  derive correct ViewSets and serializers from this document alone)
- **Secondary**: Security reviewer (validates tenant isolation and auth model
  coherence across all endpoints)
- **Tertiary**: Frontend/mobile developer (designs client sync and offline flow)

### Language

- English is the primary language of the document
- Spanish canonical domain terms used inline: romaneo, merma, campaña, zarandeo,
  secado, peso bruto, tara, grado, bonificación, rebaja, fijación, posición
  consolidada, pizarra, liquidación, facturación, cuenta corriente, canje
- First occurrence of each Spanish term per section includes English translation
  in parentheses
- Entity and field names in English snake_case (e.g., `peso_bruto_kg`,
  `grain_type`, `romaneo_number`)
- URL resource names in hyphen-separated lowercase plural (e.g., `/romaneos/`,
  `/grain-types/`, `/storage-units/`)

### Level of Detail

- **Endpoint definitions**: HTTP method, full URL pattern, description
- **Request schemas**: field table with columns: `Field | Type | Required | Description`
- **Response schemas**: field table with columns: `Field | Type | Description`
- **Status codes**: per endpoint, all possible codes with when each is returned
- **Sequence diagrams**: Mermaid `sequenceDiagram` syntax, participants labelled
  with role (Client, API, Rust Engine, PostgreSQL, ARCA WSCPE, Redis)
- **Error responses**: RFC 7807 Problem Details JSON example for each domain error type
- **Pagination**: cursor vs page-number decision per endpoint, with reasoning
- **No implementation code**: no Python imports, no Django/DRF class definitions,
  no serializer code

---

## Existing Content: Preserve vs. Replace

No existing `REST API Design.md` file. This is a net-new document.

### Source Documents to Derive From

All content is derived from these three upstream blueprint docs:

| Source | Sections to Reference | What to Extract |
|--------|----------------------|-----------------|
| `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0 | §5.3 Romaneo (31 fields, state machine), §5.4 QualityAnalysis, §5.5 MermaCalculation, §5.6 Storage, §5.7 CPE, §5.8 Weighbridge, §6 Producer Accounts, §7 Agronomia, §8 Facturación | Field names, types, nullability, choices → request/response field tables |
| `Docs/Project Blueprint/High-Level Design (HLD).md` v1.0 | §4 Container Architecture, §5 Component Overview, §8 Offline-First, §9 Data Flow Diagrams, §10 Security Architecture | Communication protocols, async patterns, sync watermarks, JWT claims, RLS layers |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` v1.0 | ADR-002, 005, 008, 010, 013, 021, 022, 028, 029, 030, 032 | Architectural constraints that become API rules (UUID PKs, tenant scope, append-only, etc.) |

---

## Research Inputs per Section

### RAG Queries (run BEFORE writing — do NOT read full files)

```bash
# For §5 Romaneo API — workflow sequence drives endpoint order
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo workflow steps truck arrival weight analysis" -l 5

# For §9 Producer Accounts — transaction types table
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account movements balance grain kilos" -l 5

# For §12 Phase 2 — WSLPG endpoint shapes
.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSLPG liquidacion API campos campania grano precio" -l 5

# For §10 Sync API — CPE lifecycle and sync protocol
.venv/bin/python scripts/qdrant/qdrant_search.py -q "CPE CTG state machine confirmarArribo confirmacionDefinitiva" -l 4
```

---

## Section-by-Section Writing Plan

### §1 — Document Metadata
**Lines**: ~20
**Source**: Boilerplate
**Content**:
- Blockquote: `> **Version 1.0** · Date: 2026-03-17 · Status: Accepted · Owner: GraviTea Architecture Team`
- Metadata table: Version, Date, Status, Owner rows
- Changelog table with single entry: v1.0 initial release
- "How to read this document" paragraph (2-3 sentences)

**Gate**: `grep 'Version 1.0' <file>` returns at least 2 matches (blockquote + table cell)

---

### §2 — Design Principles
**Lines**: ~80-100
**Source**: ADR-002 (UUID), ADR-005 (tenant isolation), ADR-008 (append-only), ADR-010 (global tables), ADR-021 (JWT RS256), ADR-022 (blind index), ADR-028 (offline-first), ADR-029 (conflict resolution)
**Content**:
- §2.1 RESTful Resource Orientation — resources are nouns (romaneos, accounts), actions are verbs on sub-resources (confirmar-arribo/)
- §2.2 Versioning Policy — `/api/v1/` prefix, 12-month deprecation notice
- §2.3 Authentication Model — JWT RS256 bearer token, HS256/none rejected at middleware, token lifetime (15 min access / 7 day refresh)
- §2.4 Tenant Scope Enforcement — `tenant_id` from JWT only, HTTP 404 on cross-tenant (not 403)
- §2.5 Error Format — RFC 7807 Problem Details, `Content-Type: application/problem+json`, domain extensions
- §2.6 Pagination Strategy — cursor for ledgers, page-number for lists, response envelope
- §2.7 Filtering & Ordering — `?ordering=field,-field`, ISO 8601 date ranges, `?field_after=&field_before=`
- §2.8 Rate Limiting Headers — `X-RateLimit-Limit/Remaining/Reset`, auth: 10/min/IP, standard: 1000/min/tenant

**Gate**: All 8 subsections present. No Python code.

---

### §3 — Authentication API
**Lines**: ~80-100
**Source**: HLD §5.2 (apps/auth), ADR-021, Data Model §4.7 (AppUser)
**Content**:
- §3.1 `POST /api/v1/auth/token/` — request: `{username, password}`, response: `{access, refresh}`, status: 200 OK / 401 Unauthorized
- §3.2 `POST /api/v1/auth/token/refresh/` — request: `{refresh}`, response: `{access}`, status: 200 / 401
- §3.3 `POST /api/v1/auth/logout/` — request: `{refresh}`, response: 204 No Content (token added to Redis blacklist)
- §3.4 JWT Claim Reference Table — `sub`, `tenant_id`, `branch_id`, `exp`, `iat`, `jti`, `iss`, `aud`
- §3.5 Authentication Flow Sequence Diagram (**Mermaid #1**) — Client → API (validate creds) → JWT issued → Client sends Bearer → API validates RS256 → Client refreshes → Client logs out (blacklist)

**Gate**: Mermaid diagram present. 3 endpoints documented with field tables. JWT claims table present.

---

### §4 — Grain Reference API
**Lines**: ~60-80
**Source**: Data Model §5.1 (Reference Data) + §5.2 (Regulatory Tables), ADR-010 (global tables)
**Content**:
- §4.1 `GET /api/v1/acopio/grain-types/` — response field table (id, codigo_arca, nombre, humedad_base, peso_hectolitrico_base, merma_volatil_pct, merma_manipuleo_pct), filterable by: none (small table). Note: global table, no tenant scope
- §4.2 `GET /api/v1/acopio/tolerance-tables/` — filterable by grain_type, active_at date. Note: global table
- §4.3 `GET /api/v1/acopio/merma-tables/` — filterable by grain_type. Note: global table
- §4.4 `GET /api/v1/acopio/campaigns/` — per-tenant; filterable by active_now=true. This IS tenant-scoped (CampanaConfig belongs to tenant)

**Gate**: Global vs tenant-scoped distinction documented per endpoint.

---

### §5 — Romaneo API
**Lines**: ~250-300 (largest section)
**Source**: Data Model §5.3 (Romaneo 31 fields, state machine), §5.4 (QualityAnalysis), §5.5 (MermaCalculation), HLD §9.1 (10-step flow), ADR-030 (store-and-forward)
**Content**:
- §5.1 Romaneo Resource Schema — full request field table (create) and response field table (retrieve), fields from all 7 Data Model groups
- §5.2 `POST /api/v1/acopio/romaneos/` — create (status = PENDIENTE), request = Group 1 (identification) + Group 3 (vehicle) + Group 5 (CPE/origin) fields, response = full resource, status: 201 Created
- §5.3 `GET /api/v1/acopio/romaneos/` — list, filterable by `status`, `grain_type`, `campaign`, `branch`, `ts_entrada_after/before`, page-number paginated
- §5.4 `GET /api/v1/acopio/romaneos/{id}/` — retrieve full resource with nested quality_analysis and merma_calculation (if present)
- §5.5 `PATCH /api/v1/acopio/romaneos/{id}/` — partial update, guard: status must be PENDIENTE or EN_PROCESO, else HTTP 409
- §5.6 State Transition Endpoints:
  - §5.6.1 `POST confirmar-arribo/` → EN_PROCESO, enqueues `confirmarArriboCPE` to PendingOperation, HTTP 202 Accepted, response includes `pending_operation_id`
  - §5.6.2 `POST peso-bruto/` → PESADO, request: `{peso_bruto_kg, weighbridge_device_id}`, sets `ts_pesada_bruta`, HTTP 200
  - §5.6.3 `POST analizar/` → ANALIZADO, request: inline QualityAnalysis fields (9 quality parameters), HTTP 200
  - §5.6.4 `POST confirmar/` → CONFORME (**immutability gate**), sets `grado_asignado`, `bonificacion_rebaja_pct`, `peso_neto_conforme_kg`, HTTP 200. **After this, no PATCH/PUT allowed.**
  - §5.6.5 `POST tara/` — captures tare weight post-unload, request: `{tara_kg, weighbridge_device_id}`, computes `peso_neto_bruto_kg = peso_bruto_kg - tara_kg`, sets `ts_tara`, HTTP 200
  - §5.6.6 `POST cerrar/` → CERRADO, enqueues `descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor` to PendingOperation, HTTP 202. Precondition: `tara_kg` must be non-null, else HTTP 422
- §5.7 `GET merma-preview/` — non-persisting, request via query params or body: quality params, returns computed merma intermediates, HTTP 200
- §5.8 Romaneo Lifecycle Sequence Diagram (**Mermaid #2**) — Client → API (create) → API (confirmar-arribo, async → ARCA) → Weighbridge → API (peso-bruto) → Lab → API (analizar) → Rust Engine (merma) → API (confirmar) → Client (tara) → API (cerrar, async → ARCA)
- §5.9 Immutability Rules — HTTP 409 `romaneo_immutable` problem detail JSON example, which endpoints reject (PATCH, PUT, DELETE on CONFORME/CERRADO)

**Gate**: 11 endpoints documented. Mermaid diagram present. Immutability rules explicit. Out-of-sequence transition errors documented (HTTP 409 with current status + valid transitions).

---

### §6 — Quality Analysis API
**Lines**: ~50-60
**Source**: Data Model §5.4 (QualityAnalysis fields)
**Content**:
- §6.1 QualityAnalysis Resource Schema — 9 quality parameter fields from Data Model: humedad_pct, materias_extranas_pct, granos_danados_pct, etc.
- §6.2 `POST romaneos/{id}/quality-analysis/` — create, guard: romaneo status must be EN_PROCESO or PESADO
- §6.3 `GET romaneos/{id}/quality-analysis/` — retrieve (one-to-one satellite)
- §6.4 `PATCH romaneos/{id}/quality-analysis/` — update, guard: romaneo status must be ANALIZADO (before CONFORME)

**Gate**: Field table includes all 9 quality parameters. Guards documented.

---

### §7 — Storage API
**Lines**: ~60-70
**Source**: Data Model §5.6 (StorageUnit, GrainLot, GrainMovement)
**Content**:
- §7.1 `GET /api/v1/acopio/storage-units/` — list, includes `current_occupancy_kg` (derived)
- §7.2 `GET /api/v1/acopio/storage-units/{id}/` — detail, includes capacity, grain_type, occupancy
- §7.3 `GET /api/v1/acopio/grain-lots/` — list, filterable by grain_type, campaign, storage_unit, status
- §7.4 `GET /api/v1/acopio/grain-lots/{id}/` — detail, includes `current_balance_kg` (derived)
- §7.5 `GET /api/v1/acopio/grain-lots/{id}/movements/` — cursor-paginated ledger of GrainMovements

**Gate**: Derived fields (occupancy, balance) documented as computed, not stored.

---

### §8 — Weighbridge API
**Lines**: ~30-40
**Source**: Data Model §5.8 (WeighbridgeDevice), HLD §7 (protocol stack), ADR-032
**Content**:
- §8.1 `GET /api/v1/acopio/weighbridges/` — list configured devices with status (online/offline)
- §8.2 `GET /api/v1/acopio/weighbridges/{id}/reading/` — live weight reading; HTTP 200 with `{weight_kg, stable, timestamp}` when online; HTTP 503 Service Unavailable with problem detail when disconnected

**Gate**: Disconnected device error documented (HTTP 503).

---

### §9 — Producer Accounts API
**Lines**: ~100-120
**Source**: Data Model §6 (ProducerAccount, AccountMovement, FijacionRecord), ADR-008 (append-only), ADR-013 (posición consolidada derived view), ADR-022 (encrypted CUIT)
**Content**:
- §9.1 Account Resource Schema — ProducerAccount fields: producer_cuit, branch, grain_type, campaign, grain_balance_kg, ars_balance, usd_balance
- §9.2 `GET /api/v1/cuentas/accounts/` — list, filterable by producer_cuit (blind index equality), grain_type, campaign
- §9.3 `GET /api/v1/cuentas/accounts/{id}/` — detail with balances
- §9.4 `GET /api/v1/cuentas/accounts/{id}/movements/` — cursor-paginated append-only ledger, 8 movement types. Note: no PATCH/DELETE (HTTP 405)
- §9.5 `GET /api/v1/cuentas/posicion-consolidada/` — derived view (SQL aggregation, not stored). Query params: producer_cuit, campaign. Response: array of per-grain-type totals across all branches. Note: ADR-013 governs this pattern.
- §9.6 `POST /api/v1/cuentas/fijaciones/` — create FijacionRecord (partial price fixation). Request: deposit_movement_id, pizarra_price, kg_fixed. Response: 201 with remaining_unfixed_kg.
- §9.7 `GET /api/v1/cuentas/fijaciones/` — list, filterable by account, campaign
- §9.8 Encrypted CUIT Field Behaviour Note — plaintext in requests, transparent encryption server-side, blind index for equality search only, no LIKE/range queries

**Gate**: Posición consolidada documented as derived view. Encrypted CUIT note present. Append-only enforcement documented.

---

### §10 — Offline Sync API
**Lines**: ~100-120
**Source**: HLD §8 (Offline-First), §9.3 (Sync Data Flow), ADR-028, ADR-029, ADR-030
**Content**:
- §10.1 Sync Model Overview — watermarks, delta vs full sync, 5 conflict strategies from ADR-029, PendingOperation queue for ARCA calls (ADR-030)
- §10.2 `GET /api/v1/sync/delta/` — query param `last_seq`, response: `{server_seq, changes: [{entity_type, id, action, data}]}`
- §10.3 `POST /api/v1/sync/push/` — request: `{mutations: [{entity_type, id, action, data, client_seq}]}`, response: `{results: [{id, status, conflict_strategy, server_version}]}`
- §10.4 `GET /api/v1/sync/pending-ops/` — list PendingOperations for current device session
- §10.5 `POST /api/v1/sync/pending-ops/{id}/retry/` — manually trigger retry of failed ARCA call
- §10.6 Conflict Signal Response Schema — per-item: `{id, status: "accepted"|"conflict"|"rejected", conflict_strategy: "server_wins"|"client_wins"|"most_complete_wins"|"manual"|"append_both", server_version: {...}}`
- §10.7 Offline Sync Round-Trip Sequence Diagram (**Mermaid #3**) — Client (offline mutations) → Client (reconnect) → API (delta pull, watermark) → Client (merge) → API (batch push) → Server (conflict resolution per ADR-029) → Client (apply results, advance watermark)

**Gate**: Mermaid diagram present. 5 conflict strategies listed. Conflict signal schema documented.

---

### §11 — Error Reference
**Lines**: ~60-80
**Source**: FR-012 (RFC 7807), edge cases from spec.md
**Content**:
- §11.1 RFC 7807 Problem Details Format — JSON template with all required fields (`type`, `title`, `status`, `detail`, `instance`) + domain extensions
- §11.2 Domain Error Type Catalog:
  - `romaneo_immutable` — PATCH/PUT on CONFORME/CERRADO romaneo (409)
  - `invalid_state_transition` — out-of-sequence state transition (409)
  - `tenant_mismatch` — cross-tenant UUID access (404 — never revealed as 403)
  - `cpe_not_confirmed` — cerrar/ called without prior confirmar-arribo (409)
  - `insufficient_grain_balance` — fijación exceeds unfixed kg (422)
  - `arca_unavailable` — ARCA service unreachable during sync (502)
  - `tare_weight_required` — cerrar/ called without tara_kg (422)
  - `weighbridge_disconnected` — live reading on offline device (503)
  - `append_only_violation` — PATCH/DELETE on ledger resource (405)
  - `token_expired` — JWT past exp (401)
  - `invalid_algorithm` — HS256 or none algorithm in JWT (401)
- §11.3 HTTP Status Code Decision Table — matrix: 200, 201, 202, 204, 400, 401, 404, 405, 409, 422, 429, 500, 502, 503

**Gate**: At least 10 domain error types cataloged. HTTP status decision table present.

---

### §12 — Phase 2 Endpoints
**Lines**: ~40-50
**Source**: HLD §5.7 (apps/facturacion), §5.8 (apps/liquidaciones), Data Model §8
**Content**:
- Opening blockquote: `> **Phase 2 — Not active in Phase 1 delivery.**`
- §12.1 Liquidaciones API — `POST /api/v1/liquidaciones/` (Form 1116-C submit → COE), `GET /api/v1/liquidaciones/{id}/` (retrieve with COE result). Tied to spec-14.
- §12.2 Facturación API — `POST /api/v1/facturacion/comprobantes/` (WSFEv1 → CAE), `GET /api/v1/facturacion/comprobantes/{id}/pdf/`. Phase 2, no spec assigned.
- §12.3 Pending ARCA Queue Integration — notes on how Phase 2 endpoints interact with the sync PendingOperation queue

**Gate**: Phase 2 blockquote present. No field tables required (placeholder shapes only).

---

### §13 — Endpoint Summary Table
**Lines**: ~60-80
**Source**: Aggregation of §3-§12
**Content**:
- Complete table with columns: `Method | URL | App | Phase | Auth | Description`
- Every endpoint from §3 through §12 included
- Sorted by URL path (alphabetical within each app)

**Gate**: Total endpoint count ≥ 35. Every endpoint from §3-§12 appears exactly once.

---

## Checkpoint Gates

| Gate | After Section | Verification | Fail Action |
|------|--------------|-------------|-------------|
| G1 | §1 Metadata | `grep 'Version 1.0' <file>` returns ≥ 2 matches | Fix version metadata format |
| G2 | §2 Design Principles | All 8 subsections (§2.1-§2.8) present, no Python code | Add missing subsections |
| G3 | §3 Auth API | Mermaid diagram #1 present, 3 endpoints with field tables | Add missing schemas |
| G4 | §5 Romaneo API | 11 endpoints documented, Mermaid diagram #2 present, immutability rules explicit | Add missing endpoints/guards |
| G5 | §9 Producer Accounts | Posición consolidada = derived view, encrypted CUIT note present, append-only documented | Add missing notes |
| G6 | §10 Sync API | Mermaid diagram #3 present, 5 conflict strategies listed, conflict signal schema documented | Add missing schemas |
| G7 | §11 Error Reference | ≥ 10 domain error types, HTTP status decision table present | Add missing error types |
| G8 | §13 Summary Table | Every endpoint from §3-§12 appears, ≥ 35 rows | Cross-check against earlier sections |

---

## Done Criteria

The document is done when ALL of the following are true:

1. `grep -c "^#" <file>` ≥ 40 (heading count)
2. `grep -c '```mermaid' <file>` ≥ 3 (Mermaid diagrams)
3. All 13 top-level sections (§1-§13) present with no "TBD" or placeholder text
4. Every Phase 1 endpoint has request AND response field tables
5. Endpoint summary table (§13) covers every endpoint from §3-§12
6. Version metadata block: both blockquote and table cell present
7. No Python/Django/DRF code snippets anywhere
8. Phase 2 section opens with `> **Phase 2 — Not active in Phase 1 delivery.**`
9. Encrypted CUIT field behaviour note in §9.8
10. All 6 romaneo state transition endpoints documented with status codes, including HTTP 202 for async endpoints (confirmar-arribo, cerrar)

---

## Execution Notes

### This is a Blueprint Spec

- **Single author** — no agent team, no tmux multi-pane
- **Single Write pass** — the entire document is written in one pass, then verified against gates
- **No testing required** — this is a document, not code. Verification is grep-based.
- **No scripts/run-tests-external.sh** — not applicable for document specs

### Writing Strategy

Write the document in a SINGLE Write tool call, covering all 13 sections. The
document is internally consistent (the summary table in §13 must match the
endpoints defined in §3-§12), so writing it atomically avoids drift.

After writing, run the checkpoint gates sequentially. Fix any failures
in-place with Edit, then re-verify.

### Token Management

Do NOT read full research Markdown files. Use RAG queries listed above to
gather specific domain facts. The upstream blueprint docs (Data Model, HLD, ADR)
are the primary sources — read specific sections via offset/limit, not full files.
