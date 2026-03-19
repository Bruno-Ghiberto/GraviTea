# Spec-06: REST API Design — Context Prompt

## Feature Description

Produce `Docs/Project Blueprint/REST API Design.md` — the authoritative REST API specification
for GraviTea Acopio ERP. This is a **Blueprint spec** (document writing, single author, no agent
teams). The deliverable is a reference document that all implementation specs (09+) treat as
requirements authority.

The document defines:

1. API conventions — versioning, auth headers, error format (RFC 7807), pagination, filtering,
   and rate-limit response headers
2. Full endpoint catalog organized by Django app, with HTTP method, URL pattern, and description
3. Detailed request/response schemas for Phase 1 endpoints (romaneo lifecycle, quality analysis,
   storage, producer accounts, auth, sync)
4. State transition endpoints — the Romaneo state machine exposed as resource actions
5. Security model — JWT RS256 bearer tokens, IDOR cross-validation, tenant scope enforcement
6. Offline sync API — delta pull, push, watermarks, conflict signals
7. Phase 2 endpoints (WSLPG liquidaciones, WSFEv1 facturación) documented as "Phase 2 — not
   active in Phase 1 delivery"

**Output file**: `Docs/Project Blueprint/REST API Design.md`

---

## Current State

No `REST API Design.md` exists yet. The upstream blueprint docs are complete:

| Doc | Status | Key inputs to this spec |
|-----|--------|------------------------|
| `Docs/Project Blueprint/Data Model & Domain Model.md` | v1.0 Accepted | All entity fields, FK relations, state machines |
| `Docs/Project Blueprint/High-Level Design (HLD).md` | v1.0 Accepted | Container arch §4, security §10, offline §8, Django app inventory §5 |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | v1.0 Accepted | ADR-002 UUID PKs, ADR-005 tenant isolation, ADR-021 JWT RS256, ADR-028 offline-first |

The existing codebase (`backend/apps/`) has DRF ViewSets for auth, inventario, facturación, and
sync — but these are the pre-pivot "ferretería" implementation, not the acopio grain domain. The
API Design doc defines the **target acopio API** that implementation specs 09–12 will build.

---

## Research Inputs

### RAG Queries (run these FIRST — do NOT read full files)

```bash
# Romaneo fields and workflow sequence
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo workflow steps truck arrival weight analysis" -l 5

# WSLPG liquidacion fields for Phase 2 API shape reference
.venv/bin/python scripts/qdrant/qdrant_search.py -q "liquidacion API campos campania grano productor kilos precio" -l 5

# Producer account transaction types and API movements
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account movements balance API grain" -l 5

# CPE/CTG state machine for sync endpoint design
.venv/bin/python scripts/qdrant/qdrant_search.py -q "CPE CTG state machine confirmarArribo confirmacionDefinitiva" -l 4

# Pizarra price API for future reference endpoint shape
.venv/bin/python scripts/qdrant/qdrant_search.py -q "BCR API pizarra price grain endpoint authentication" -l 3
```

### Source Documents (prefer RAG; read sections only if RAG is insufficient)

| ID | Path | Relevant Sections |
|----|------|-------------------|
| 8.3 | `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md` | Full field list, document lifecycle |
| 8.4 | `Docs/Researches/Markdown/8.4 Form 1116 B-C Field Structure for Data Model Design.md` | WSLPG XML field mapping → REST equivalents |
| 5.1 | `Docs/Researches/Markdown/5.1 WSLPG -- Technical API Documentation.md` | SOAP methods catalog (§2), liquidacionAutorizar fields (§3) |
| 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | 10-step romaneo workflow → drives endpoint sequencing |
| 2.3 | `Docs/Researches/Markdown/2.3 Producer Current Accounts (Cuentas Corrientes de Productores).md` | Transaction type table → AccountMovement API |

### Critical Domain Facts (minimum context — inline these facts)

**Romaneo lifecycle** (maps to HLD §9.1 ten-step flow):
1. Truck arrives → CPE number verified, romaneo created (`PENDIENTE`)
2. CPE arrival confirmed to ARCA (`confirmarArriboCPE`) → `EN_PROCESO`
   (ARCA call enqueued to `PendingOperation` via ADR-030 — async, HTTP 202)
3. Gross weight captured from weighbridge (`peso_bruto_kg`) → `PESADO`
4. Sampling (calado) and lab analysis (9 quality parameters) → `ANALIZADO`
5. Merma calculated (Rust engine), operator confirms → `CONFORME` — **IMMUTABILITY GATE**
6. Truck unloads grain → tare weight captured (`tara_kg`, `ts_tara`)
7. CPE closure: `descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor` enqueued
   (ADR-030 — two ARCA WSCPE calls queued sequentially) → `CERRADO`

**Romaneo is immutable after `CONFORME`**: no PATCH/PUT requests permitted on CONFORME or CERRADO
romaneos. The API must enforce this and return HTTP 409 with problem detail.

**Key Romaneo fields for API**:
- Identification: `romaneo_number`, `status`, `grain_type`, `campaign`, `branch`
- Timestamps: `ts_entrada`, `ts_pesada_bruta`, `ts_calado`, `ts_analisis`, `ts_descarga`, `ts_tara`
- Vehicle: `patente_chasis`, `patente_acoplado`, `driver_name`, `driver_dni`
- Weight: `peso_bruto_kg`, `tara_kg`, `peso_neto_bruto_kg`, `weighbridge_device`
- CPE/Origin: `cpe_numero`, `ctg_codigo`, `producer_cuit`, `origin_locality`
- Storage: `storage_unit`, `grain_lot`
- Outcome: `grado_asignado`, `bonificacion_rebaja_pct`, `tolerance_table_version`, `peso_neto_conforme_kg`

**JWT claims that scope every request**: `tenant_id`, `branch_id`, `sub` (user UUID).
All endpoints auto-filter by `tenant_id` from the JWT — clients never pass tenant in the URL.

**UUID v4 primary keys** everywhere (ADR-002). URL patterns use UUIDs, not integer IDs.

**Append-only ledgers**: `AccountMovement` and `StockMovement` never accept PATCH/DELETE.
`FijacionRecord` is append-only. Attempting UPDATE on these returns HTTP 405.

**Offline sync model**: device pulls a delta via watermark (`last_sync_seq`), pushes local
mutations as a batch. Conflicts are server-resolved with one of 5 strategies (ADR-029).
API must expose: delta-pull endpoint, push endpoint, conflict signal in response body.

**Posición Consolidada** is a derived view (SQL aggregation over `ProducerAccount`). It is not
a stored resource — it is a `GET` on a computed endpoint, not a CRUD endpoint.

**CAEA offline path**: when `apps/sync.PendingOperation` holds queued ARCA calls, the API must
expose an endpoint to query and retry the queue. CAEA (quincena batch code) replaces CAE when
ARCA is unreachable during harvest peak.

**Phase 1 vs Phase 2 split**:
- Phase 1 (specs 09-12): auth, grain reference data, romaneo, quality analysis, storage,
  producer accounts, sync, weighbridge
- Phase 2 (Wave 6): spec-13 agronomía adaptation, spec-14 WSLPG integration, spec-15 reports,
  spec-16 canje. WSFEv1 facturación (apps/facturacion) is also Phase 2 but has no spec assigned.

---

## Functional Requirements

### FR-006-01 — API Versioning and Base URL

All endpoints MUST be prefixed `/api/v1/`. The version token `v1` is in the URL path.
No existing ADR covers URL versioning — this convention is established by this spec.
Example: `GET /api/v1/acopio/romaneos/`.

### FR-006-02 — JWT Authentication on All Endpoints

Every endpoint (except `/api/v1/auth/token/` and `/api/v1/auth/token/refresh/`) MUST require a
valid RS256 JWT bearer token in the `Authorization: Bearer <token>` header. HS256 and `none`
algorithm tokens return HTTP 401 before any view logic runs (ADR-021).

### FR-006-03 — Tenant Scope via JWT Claims

All resource endpoints MUST auto-filter results to the `tenant_id` encoded in the JWT.
The tenant identifier is NEVER accepted as a URL parameter or request body field. If a URL
resource UUID does not belong to the JWT's `tenant_id`, the endpoint returns HTTP 404 (not 403,
to prevent tenant enumeration).

### FR-006-04 — Romaneo CRUD Endpoints

The API MUST expose:
- `POST /api/v1/acopio/romaneos/` — create (status = PENDIENTE)
- `GET /api/v1/acopio/romaneos/` — list (filterable by status, grain_type, campaign, branch)
- `GET /api/v1/acopio/romaneos/{id}/` — retrieve
- `PATCH /api/v1/acopio/romaneos/{id}/` — partial update (only when status is PENDIENTE or EN_PROCESO)
- `POST /api/v1/acopio/romaneos/{id}/confirmar-arribo/` — enqueues `confirmarArriboCPE` → EN_PROCESO (HTTP 202)
- `POST /api/v1/acopio/romaneos/{id}/peso-bruto/` — captures gross weight → PESADO
- `POST /api/v1/acopio/romaneos/{id}/analizar/` — attach QualityAnalysis → ANALIZADO
- `POST /api/v1/acopio/romaneos/{id}/confirmar/` — operator sign-off → CONFORME (immutability gate)
- `POST /api/v1/acopio/romaneos/{id}/tara/` — captures tare weight + computes peso_neto (post-unload)
- `POST /api/v1/acopio/romaneos/{id}/cerrar/` — enqueues `descargadoDestinoCPE` + `confirmacionDefinitivaCPEAutomotor` → CERRADO (HTTP 202; requires tara_kg present)
- `GET /api/v1/acopio/romaneos/{id}/merma-preview/` — compute merma without persisting (Rust engine)

### FR-006-05 — Quality Analysis Endpoints

- `POST /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` — create QualityAnalysis satellite
- `GET /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` — retrieve
- `PATCH /api/v1/acopio/romaneos/{romaneo_id}/quality-analysis/` — update (only while ANALIZADO)

### FR-006-06 — Grain Reference Data Endpoints

Read-only. Global tables shared across tenants (ADR-010), no tenant filter applied.
- `GET /api/v1/acopio/grain-types/` — list all grain species with ARCA codes
- `GET /api/v1/acopio/grain-types/{id}/` — retrieve
- `GET /api/v1/acopio/tolerance-tables/` — list (filterable by grain_type, active_at date)
- `GET /api/v1/acopio/merma-tables/` — list (filterable by grain_type)
- `GET /api/v1/acopio/campaigns/` — list (per-tenant; filterable by active_now=true)

### FR-006-07 — Storage Endpoints

- `GET /api/v1/acopio/storage-units/` — list silos/bins for the tenant
- `GET /api/v1/acopio/storage-units/{id}/` — retrieve with current occupancy kg
- `GET /api/v1/acopio/grain-lots/` — list grain lots (filterable by grain_type, campaign, status)
- `GET /api/v1/acopio/grain-lots/{id}/` — retrieve with current kg balance
- `GET /api/v1/acopio/grain-lots/{id}/movements/` — paginated grain movement ledger

### FR-006-08 — Weighbridge Endpoints

- `GET /api/v1/acopio/weighbridges/` — list configured weighbridge devices
- `GET /api/v1/acopio/weighbridges/{id}/reading/` — current live weight reading (SSE or poll)

### FR-006-09 — Producer Account Endpoints

- `GET /api/v1/cuentas/accounts/` — list accounts (filterable by producer_cuit, grain_type, campaign)
- `GET /api/v1/cuentas/accounts/{id}/` — retrieve with grain_balance_kg + ars_balance
- `GET /api/v1/cuentas/accounts/{id}/movements/` — paginated append-only ledger
- `GET /api/v1/cuentas/posicion-consolidada/` — derived view across all branches (ADR-013)
  (query param: `producer_cuit`, `campaign`; returns per-grain-type totals — SQL aggregation, not stored)
- `POST /api/v1/cuentas/fijaciones/` — create a FijacionRecord (partial price fixation)
- `GET /api/v1/cuentas/fijaciones/` — list fixation records (filterable by account, campaign)

### FR-006-10 — Auth Endpoints

- `POST /api/v1/auth/token/` — obtain JWT pair (access 15 min, refresh 7 days)
- `POST /api/v1/auth/token/refresh/` — exchange refresh token for new access token
- `POST /api/v1/auth/logout/` — blacklist the refresh token (Redis blacklist)

### FR-006-11 — Offline Sync Endpoints

- `GET /api/v1/sync/delta/` — delta pull (query param: `last_seq`; returns changed resources
  since watermark, plus new `server_seq`)
- `POST /api/v1/sync/push/` — push batch of local mutations; returns per-item conflict signals
- `GET /api/v1/sync/pending-ops/` — list queued ARCA PendingOperations for this device session
- `POST /api/v1/sync/pending-ops/{id}/retry/` — manually trigger retry of a failed ARCA call

### FR-006-12 — Error Format (RFC 7807 Problem Details)

All error responses MUST use `Content-Type: application/problem+json` with fields:
`type`, `title`, `status`, `detail`, `instance`. Domain-specific extensions: `romaneo_status`
(for immutability violations), `conflict_strategy` (for sync conflicts).

### FR-006-13 — Pagination

- List endpoints MUST be paginated.
- Default style: **cursor-based** for ledgers (AccountMovement, GrainMovement — append-only,
  high cardinality). **Page-number** for reference data and romaneo lists.
- Response envelope: `{ "count": N, "next": "...", "previous": "...", "results": [...] }`

### FR-006-14 — Filtering and Ordering

All list endpoints MUST support `?ordering=field,-field` (DRF ordering filter). Key filter
fields per endpoint must be documented in the spec. Date range filters use ISO 8601:
`?ts_entrada_after=2024-03-01T00:00:00Z&ts_entrada_before=2024-03-31T23:59:59Z`.

### FR-006-15 — Rate Limit Response Headers

All endpoints MUST include rate-limit headers on responses:
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`. Auth endpoints have
stricter limits (10 req/min per IP) vs. standard endpoints (1000 req/min per tenant).

### FR-006-16 — Phase 2 Endpoints (documented, not active in Phase 1)

The doc MUST include a "Phase 2 Endpoints" section clearly labelled
`> Not active in Phase 1 delivery`. This section covers:
- `POST /api/v1/liquidaciones/` — submit WSLPG Form 1116-C (apps/liquidaciones, spec-14)
- `GET /api/v1/liquidaciones/{id}/` — retrieve COE result
- `POST /api/v1/facturacion/comprobantes/` — issue WSFEv1 electronic invoice (apps/facturacion — Phase 2, no spec assigned yet)
- `GET /api/v1/facturacion/comprobantes/{id}/pdf/` — render fiscal PDF

---

## Non-Functional Requirements

### NF-006-01 — No Implementation Code in the Document

The API Design doc is a specification document. It MUST NOT contain Django/DRF view code,
serializer code, or Python snippets. Use YAML-like schema notation or prose field tables.

### NF-006-02 — Concrete Field Tables for Key Endpoints

All "key endpoint" request/response schemas (romaneo create, romaneo state transitions, quality
analysis, posición consolidada, sync delta, sync push) MUST include field tables with:
field name, type, required/optional, and description. No vague "see data model" references.

### NF-006-03 — Versioning Policy Stated

The document MUST state the versioning policy: `v1` is the only active version; `v2` will be
introduced only for breaking changes; `v1` has a minimum 12-month deprecation notice period.

### NF-006-04 — Minimum Heading Count

The document MUST contain at least 40 headings. API Design docs are dense reference material.

### NF-006-05 — Mermaid Diagrams for Key Flows

At least 3 Mermaid sequence diagrams MUST be included:
1. Romaneo lifecycle — client → API → Rust (merma) → PostgreSQL → ARCA CPE
2. JWT authentication flow — token obtain → request → refresh
3. Offline sync round-trip — delta pull → local mutations → push → conflict resolution

### NF-006-06 — Consistent URL Naming Convention

All URLs MUST use snake_case resource names in plural form (e.g., `/romaneos/`, `/grain-types/`,
`/producer-accounts/`). Hyphens separate multi-word resource names. No camelCase in URLs.

### NF-006-07 — Searchable Encrypted Fields Note

The document MUST note that `producer_cuit` is stored as AES-256-GCM ciphertext + HMAC-SHA256
blind index (ADR-022). The API accepts plaintext CUIT in requests; the server handles
encryption/blind-index transparently. Filtering by `?producer_cuit=XX` searches the blind index
only — LIKE/range queries on CUIT are not supported.

---

## Target Document Structure

The REST API Design doc MUST follow this section order:

```
§1  Document Metadata
    Version, Date, Status, Owner, Changelog table

§2  Design Principles
    §2.1  RESTful Resource Orientation
    §2.2  Versioning Policy (/api/v1/)
    §2.3  Authentication Model (JWT RS256, bearer token)
    §2.4  Tenant Scope Enforcement (JWT claim, no tenant in URL)
    §2.5  Error Format (RFC 7807 Problem Details)
    §2.6  Pagination Strategy (cursor vs page-number)
    §2.7  Filtering & Ordering Conventions
    §2.8  Rate Limiting Headers

§3  Authentication API
    §3.1  POST /api/v1/auth/token/
    §3.2  POST /api/v1/auth/token/refresh/
    §3.3  POST /api/v1/auth/logout/
    §3.4  JWT Claim Reference Table
    §3.5  Authentication Flow Sequence Diagram

§4  Grain Reference API  (apps/acopio — global tables)
    §4.1  GET /api/v1/acopio/grain-types/
    §4.2  GET /api/v1/acopio/tolerance-tables/
    §4.3  GET /api/v1/acopio/merma-tables/
    §4.4  GET /api/v1/acopio/campaigns/

§5  Romaneo API  (apps/acopio — Phase 1)
    §5.1  Romaneo Resource Schema (request + response field tables)
    §5.2  POST /api/v1/acopio/romaneos/ — Create
    §5.3  GET /api/v1/acopio/romaneos/ — List
    §5.4  GET /api/v1/acopio/romaneos/{id}/ — Retrieve
    §5.5  PATCH /api/v1/acopio/romaneos/{id}/ — Update (guard: pre-CONFORME only)
    §5.6  State Transition Endpoints
          §5.6.1  POST confirmar-arribo/ → EN_PROCESO
          §5.6.2  POST peso-bruto/ → PESADO
          §5.6.3  POST analizar/ → ANALIZADO
          §5.6.4  POST confirmar/ → CONFORME (immutability gate)
          §5.6.5  POST tara/ — tare weight capture (post-unload)
          §5.6.6  POST cerrar/ → CERRADO (queues 2 ARCA calls, HTTP 202)
    §5.7  GET .../merma-preview/ — Non-persisting merma computation
    §5.8  Romaneo Lifecycle Sequence Diagram
    §5.9  Immutability Rules (HTTP 409 on CONFORME/CERRADO mutations)

§6  Quality Analysis API  (apps/acopio)
    §6.1  QualityAnalysis Resource Schema
    §6.2  POST romaneos/{id}/quality-analysis/
    §6.3  GET romaneos/{id}/quality-analysis/
    §6.4  PATCH romaneos/{id}/quality-analysis/ (guard: ANALIZADO state only)

§7  Storage API  (apps/acopio — Phase 1)
    §7.1  GET /api/v1/acopio/storage-units/
    §7.2  GET /api/v1/acopio/storage-units/{id}/
    §7.3  GET /api/v1/acopio/grain-lots/
    §7.4  GET /api/v1/acopio/grain-lots/{id}/
    §7.5  GET /api/v1/acopio/grain-lots/{id}/movements/

§8  Weighbridge API  (apps/acopio)
    §8.1  GET /api/v1/acopio/weighbridges/
    §8.2  GET /api/v1/acopio/weighbridges/{id}/reading/

§9  Producer Accounts API  (apps/cuentas — Phase 1)
    §9.1  Account Resource Schema
    §9.2  GET /api/v1/cuentas/accounts/
    §9.3  GET /api/v1/cuentas/accounts/{id}/
    §9.4  GET /api/v1/cuentas/accounts/{id}/movements/ (cursor-paginated ledger)
    §9.5  GET /api/v1/cuentas/posicion-consolidada/ (derived view)
    §9.6  POST /api/v1/cuentas/fijaciones/
    §9.7  GET /api/v1/cuentas/fijaciones/
    §9.8  Encrypted CUIT Field Behaviour Note

§10 Offline Sync API  (apps/sync)
    §10.1 Sync Model Overview (watermarks, delta, conflict)
    §10.2 GET /api/v1/sync/delta/
    §10.3 POST /api/v1/sync/push/
    §10.4 GET /api/v1/sync/pending-ops/
    §10.5 POST /api/v1/sync/pending-ops/{id}/retry/
    §10.6 Conflict Signal Response Schema
    §10.7 Offline Sync Round-Trip Sequence Diagram

§11 Error Reference
    §11.1 RFC 7807 Problem Details Format
    §11.2 Domain Error Type Catalog (romaneo_immutable, tenant_mismatch,
          cpe_not_confirmed, insufficient_grain_balance, arca_unavailable)
    §11.3 HTTP Status Code Decision Table

§12 Phase 2 Endpoints  (not active in Phase 1 delivery)
    §12.1 Liquidaciones API (WSLPG Form 1116-C — spec-14)
    §12.2 Facturación API (WSFEv1 — Phase 2, no spec assigned)
    §12.3 Pending ARCA Queue Integration Notes

§13 Endpoint Summary Table
    Complete table: Method | URL | App | Phase | Auth | Description
```

---

## Acceptance Criteria

### AC-006-01 — Structural Completeness
All 13 sections from the Target Document Structure are present. No sections listed as
"TBD" or placeholder.

### AC-006-02 — Heading Count
`grep -c "^#" "Docs/Project Blueprint/REST API Design.md"` ≥ 40.

### AC-006-03 — Mermaid Diagrams
`grep -c '```mermaid' "Docs/Project Blueprint/REST API Design.md"` ≥ 3 (romaneo lifecycle,
JWT auth flow, sync round-trip).

### AC-006-04 — Romaneo State Transitions Covered
All 6 state transition endpoints (confirmar-arribo, peso-bruto, analizar, confirmar, tara, cerrar)
are documented with request schema and expected HTTP response codes. Endpoints that enqueue
ARCA WSCPE calls (confirmar-arribo, cerrar) return HTTP 202 Accepted.

### AC-006-05 — Immutability Enforcement Documented
HTTP 409 response with problem detail `type: romaneo_immutable` is documented for attempts
to PATCH a CONFORME or CERRADO romaneo.

### AC-006-06 — Posición Consolidada Documented
`GET /api/v1/cuentas/posicion-consolidada/` is documented as a derived/computed endpoint
(SQL aggregation — not a stored CRUD resource) with query params and response schema.

### AC-006-07 — Phase 2 Section Present and Labelled
§12 exists and begins with a blockquote:
`> **Phase 2 — Not active in Phase 1 delivery.**`

### AC-006-08 — No Implementation Code
No Python, Django, or DRF code snippets appear in the document. Only HTTP examples using
`curl` or request/response JSON notation.

### AC-006-09 — Encrypted CUIT Note
§9.8 documents that `producer_cuit` is encrypted at rest and searchable only by equality
via blind index.

### AC-006-10 — Endpoint Summary Table
§13 contains a complete table covering every endpoint defined in §3-§12 with columns:
Method, URL, App, Phase, Auth required, Short description.

### AC-006-11 — Version Metadata Block
§1 contains `| **Version** | 1.0 |` in a metadata table AND a blockquote
`> **Version 1.0** · Date: ...` above it (prevents grep failures seen in spec-05).

---

## Dependencies

### Depends On

| Spec | Doc | What is consumed |
|------|-----|-----------------|
| spec-03 | `Data Model & Domain Model.md` v1.0 | All entity field tables, state machine, append-only rules |
| spec-05 | `High-Level Design (HLD).md` v1.0 | §4 Container Architecture (DRF + Gunicorn), §5 Django app inventory, §8 Offline-First model, §10 Security (JWT RS256, IDOR, RLS) |
| spec-04 | `Architecture Decision Records.md` v1.0 | ADR-002 (UUID PKs), ADR-005 (3-layer tenant isolation), ADR-008 (append-only ledger), ADR-010 (global table exemption), ADR-013 (posición consolidada as derived view), ADR-021 (JWT RS256), ADR-022 (AES-256-GCM blind index), ADR-028 (offline-first), ADR-029 (conflict resolution), ADR-030 (store-and-forward queue for ARCA calls), ADR-032 (weighbridge integration) |

### Blocks

| Spec | Why |
|------|-----|
| spec-09 (Grain Reference Data) | Django ViewSets must conform to URL patterns defined here |
| spec-10 (Romaneo Core) | Romaneo endpoint schemas and state transitions are the implementation target |
| spec-11 (Storage & Position) | Storage API endpoints defined here |
| spec-12 (Producer Accounts) | Producer account + fijación API endpoints defined here |
| spec-14 (WSLPG — Phase 2) | Phase 2 section §12.1 pre-defines the liquidaciones URL contract |
