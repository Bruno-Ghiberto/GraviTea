# Feature Specification: REST API Design for GraviTea Acopio ERP

**Feature Branch**: `006-acopio-api-design`
**Created**: 2026-03-17
**Status**: Complete
**Input**: Write the authoritative REST API Design blueprint document (`Docs/Project Blueprint/REST API Design.md`) defining the complete endpoint catalog, request/response schemas, security model, and conventions for the GraviTea Acopio ERP system.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Implementation Engineer References API Endpoint Specification (Priority: P1)

A backend engineer starting spec-10 (Romaneo Core) needs to know the exact URL pattern, HTTP method, request body fields, response schema, and status codes for every romaneo-related endpoint. They open the REST API Design document and find all 11 romaneo endpoints documented with field tables showing name, type, required/optional, and description for each request and response. They implement the endpoint exactly as specified without ambiguity.

**Why this priority**: The API Design document is the single reference for all Phase 1 implementation specs (09-12). If endpoint definitions are incomplete or ambiguous, every downstream team blocks or diverges.

**Independent Test**: Can be validated by checking that a reader can answer "What URL do I call to capture gross weight on a romaneo?" without consulting any other document, and the answer includes the full URL pattern, HTTP method, request fields, and all possible response codes.

**Acceptance Scenarios**:

1. **Given** the API Design document is complete, **When** an engineer looks up "romaneo create", **Then** they find `POST /api/v1/acopio/romaneos/` with a request field table listing all required and optional fields, and a response field table showing the created resource plus HTTP 201.
2. **Given** the API Design document is complete, **When** an engineer looks up "close romaneo", **Then** they find `POST /api/v1/acopio/romaneos/{id}/cerrar/` documented as HTTP 202 Accepted (async), with a note that it enqueues two ARCA WSCPE calls, and that `tara_kg` must already be present on the romaneo.
3. **Given** the API Design document is complete, **When** an engineer attempts to find the URL for updating a CONFORME romaneo, **Then** the document explicitly states that PATCH returns HTTP 409 with a `romaneo_immutable` problem detail for any romaneo in CONFORME or CERRADO status.

---

### User Story 2 - Architect Validates Security Model Coherence (Priority: P1)

A security reviewer reads the API Design document to verify that tenant isolation, JWT authentication, and IDOR prevention are consistently applied across all endpoints. They find a dedicated Design Principles section that defines the security model once, and each endpoint section references it. They confirm that no endpoint accepts `tenant_id` as a URL or body parameter, that unauthenticated access returns HTTP 401, and that cross-tenant resource access returns HTTP 404 (not 403).

**Why this priority**: Security is a foundational concern. An API specification that leaves ambiguity in authentication or tenant scoping creates vulnerabilities in every implementation that follows it.

**Independent Test**: Can be validated by reviewing every endpoint in the document and confirming: (a) auth requirement is stated, (b) tenant scope behaviour is documented, (c) no endpoint leaks tenant existence via 403 responses.

**Acceptance Scenarios**:

1. **Given** the API Design document is complete, **When** a reviewer checks the auth endpoints section, **Then** `POST /api/v1/auth/token/` and `POST /api/v1/auth/token/refresh/` are the only endpoints marked as not requiring a JWT bearer token.
2. **Given** the API Design document is complete, **When** a reviewer searches for `tenant_id` in any request body or URL parameter definition, **Then** zero occurrences are found — tenant context is derived exclusively from JWT claims.
3. **Given** the API Design document is complete, **When** a reviewer checks IDOR prevention for resource endpoints, **Then** the document states that accessing a UUID belonging to a different tenant returns HTTP 404.

---

### User Story 3 - Frontend/Mobile Developer Designs Offline Sync Flow (Priority: P2)

A client-side developer building the offline-capable mobile app needs to understand the sync protocol: how to request a delta of changes, how to push local mutations, what conflict signals look like in the response, and how to handle queued ARCA operations. They find the Offline Sync API section with a sequence diagram, request/response schemas for delta pull and push, a conflict signal response schema, and a pending operations management API.

**Why this priority**: The offline-first architecture is a core differentiator of the product. Without a clear sync API contract, client teams cannot implement store-and-forward logic.

**Independent Test**: Can be validated by checking that a developer can implement a complete sync round-trip (pull delta → work offline → push changes → handle conflicts) using only information in the API Design document.

**Acceptance Scenarios**:

1. **Given** the API Design document is complete, **When** a developer reads the sync delta endpoint, **Then** they find `GET /api/v1/sync/delta/` with query parameter `last_seq`, and a response schema that includes `server_seq` (the new watermark) and an array of changed resources.
2. **Given** the API Design document is complete, **When** a developer reads the sync push endpoint, **Then** they find `POST /api/v1/sync/push/` with a request schema for batched mutations and a response that includes per-item conflict signals with `conflict_strategy` indicating which of the 5 resolution strategies was applied.
3. **Given** the API Design document is complete, **When** a developer reads the pending operations section, **Then** they find endpoints to list queued ARCA calls and manually retry failed ones.

---

### User Story 4 - Spec Author Writes Romaneo Lifecycle Sequence Diagram (Priority: P2)

A document author writing the API Design blueprint needs to produce at least 3 Mermaid sequence diagrams that clearly illustrate the romaneo lifecycle (including async ARCA calls), the JWT authentication flow, and the offline sync round-trip. Each diagram must be self-explanatory and consistent with the endpoint definitions in the same document.

**Why this priority**: Visual sequence diagrams make dense API specifications accessible to non-API-specialist reviewers and catch inconsistencies between endpoint definitions.

**Independent Test**: Can be validated by rendering each Mermaid diagram and confirming it matches the endpoint definitions in the text.

**Acceptance Scenarios**:

1. **Given** the API Design document is complete, **When** the romaneo lifecycle diagram is rendered, **Then** it shows 7 state transitions (PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → tara capture → CERRADO) with the ARCA calls marked as async/queued.
2. **Given** the API Design document is complete, **When** the JWT auth diagram is rendered, **Then** it shows token obtain, bearer header on requests, token refresh, and logout (blacklist) flows.
3. **Given** the API Design document is complete, **When** the sync diagram is rendered, **Then** it shows delta pull with watermark, local offline mutations, batch push, server conflict resolution, and response with conflict signals.

---

### Edge Cases

- What happens when an endpoint is called with an expired JWT? The document must specify HTTP 401 with a problem detail indicating token expiration, distinct from invalid algorithm (also 401 but different `type` URI).
- What happens when a state transition endpoint is called out of sequence (e.g., `confirmar/` called when status is PENDIENTE, skipping PESADO and ANALIZADO)? The document must specify HTTP 409 with a problem detail indicating the current status and the valid transition.
- What happens when the posición consolidada endpoint is called for a producer CUIT that exists in one branch but not another? The response must return data only for branches where the account exists, not error.
- What happens when `cerrar/` is called but `tara_kg` has not been captured yet? The document must specify HTTP 422 with a problem detail indicating that tare weight is required before closure.
- How does the API handle the weighbridge live reading endpoint when the device is disconnected? The document must specify the error response (HTTP 503 or equivalent) and note the watchdog reconnection behaviour from the HLD.
- What happens when an append-only ledger endpoint (AccountMovement, GrainMovement) receives a PATCH or DELETE request? HTTP 405 Method Not Allowed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The document MUST define URL path versioning with `/api/v1/` prefix on all endpoints, with a stated deprecation policy (minimum 12-month notice before removal of any version).
- **FR-002**: The document MUST specify that all endpoints (except token obtain and token refresh) require a valid RS256 JWT bearer token, and that HS256 and the `none` algorithm are rejected with HTTP 401.
- **FR-003**: The document MUST specify that all resource endpoints auto-filter by `tenant_id` from the JWT, that `tenant_id` is never accepted as a URL or body parameter, and that cross-tenant access returns HTTP 404 (not 403).
- **FR-004**: The document MUST define 11 romaneo-related endpoints: create, list, retrieve, partial update (pre-CONFORME guard), 6 state transition actions (confirmar-arribo, peso-bruto, analizar, confirmar, tara, cerrar), and merma-preview. Each must include HTTP method, URL pattern, request schema, response schema, and status codes.
- **FR-005**: The document MUST define 3 quality analysis endpoints (create, retrieve, update) nested under the romaneo resource, with an update guard that only allows changes in ANALIZADO state.
- **FR-006**: The document MUST define read-only grain reference data endpoints (grain-types, tolerance-tables, merma-tables, campaigns) and note that grain-types, tolerance-tables, and merma-tables are global tables not scoped by tenant.
- **FR-007**: The document MUST define storage endpoints (storage-units list/detail, grain-lots list/detail, grain-lot movements ledger) with current occupancy and balance information.
- **FR-008**: The document MUST define weighbridge endpoints (list devices, live weight reading) with error handling for disconnected devices.
- **FR-009**: The document MUST define producer account endpoints (accounts list/detail, movements ledger, posición consolidada as a derived/computed view, fijaciones create/list) and note that movements are append-only (no PATCH/DELETE).
- **FR-010**: The document MUST define 3 auth endpoints (token obtain, token refresh, logout/blacklist) with JWT claim reference table and authentication flow diagram.
- **FR-011**: The document MUST define offline sync endpoints (delta pull with watermark, batch push with per-item conflict signals, pending operations list, pending operation retry) with a sync round-trip sequence diagram.
- **FR-012**: The document MUST specify RFC 7807 Problem Details as the error response format, with domain-specific extension fields (`romaneo_status`, `conflict_strategy`) and a catalog of domain error types.
- **FR-013**: The document MUST specify pagination strategy: cursor-based for append-only ledgers, page-number for reference data and lists, with a standard response envelope.
- **FR-014**: The document MUST specify filtering and ordering conventions using query parameters, with ISO 8601 date range filters.
- **FR-015**: The document MUST specify rate-limit response headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) on all endpoints, with stricter limits on auth endpoints.
- **FR-016**: The document MUST include a Phase 2 Endpoints section clearly labelled as not active in Phase 1, covering liquidaciones (WSLPG) and facturación (WSFEv1) endpoint shapes.
- **FR-017**: The document MUST include a complete endpoint summary table listing every endpoint with method, URL, app, phase, auth requirement, and short description.
- **FR-018**: The document MUST note that `producer_cuit` is encrypted at rest and searchable only by equality via blind index, with no support for LIKE or range queries.
- **FR-019**: The document MUST specify that endpoints enqueuing ARCA WSCPE calls (confirmar-arribo, cerrar) return HTTP 202 Accepted, indicating asynchronous processing via the store-and-forward queue.
- **FR-020**: The document MUST include at least 3 Mermaid sequence diagrams: romaneo lifecycle, JWT authentication flow, and offline sync round-trip.

### Key Entities

- **REST API Design Document**: The single deliverable — a structured Markdown document at `Docs/Project Blueprint/REST API Design.md` serving as the authoritative API contract for all Phase 1 implementation specs (09-12).
- **Endpoint Specification**: Each endpoint definition within the document, consisting of URL pattern, HTTP method, request schema (field tables), response schema (field tables), status codes, and guards/preconditions.
- **Design Principles Section**: The cross-cutting conventions section that defines authentication model, tenant scoping, error format, pagination, filtering, rate limiting, and URL naming conventions — referenced by all endpoint sections.
- **Phase 2 Placeholder Section**: Pre-defined endpoint shapes for future implementation waves, providing URL contract stability for planning purposes.

## Assumptions

- The document targets the grain domain (acopio) API surface only. Pre-pivot "ferretería" endpoints (existing in `backend/apps/`) are not covered.
- All entity field definitions are taken verbatim from the Data Model v1.0 document. No new entities or fields are introduced by this spec.
- The Romaneo state machine (PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME → CERRADO) is taken from the Data Model v1.0 and is not modified.
- Tare weight is captured as a separate step after unloading (between CONFORME and CERRADO), consistent with the HLD §9.1 ten-step flow.
- ARCA WSCPE calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) are always asynchronous via the PendingOperation queue, never synchronous.
- The document uses YAML-like schema notation and prose field tables, not implementation code (no Python/Django/DRF snippets).
- URL naming uses hyphen-separated, lowercase, plural resource names (e.g., `/grain-types/`, `/romaneos/`).
- UUID v4 identifiers are used in all URL patterns for resource IDs.
- This is a Blueprint spec (single-author document writing), not an implementation spec.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The document contains at least 40 headings, verifiable by `grep -c "^#"`.
- **SC-002**: The document contains at least 3 Mermaid sequence diagrams, verifiable by `grep -c '```mermaid'`.
- **SC-003**: All 13 top-level sections from the target document structure are present, with no "TBD" or placeholder content.
- **SC-004**: Every Phase 1 endpoint (auth, grain reference, romaneo, quality analysis, storage, weighbridge, producer accounts, sync) includes a request schema and response schema with field tables.
- **SC-005**: A complete endpoint summary table exists listing every endpoint with method, URL, app, phase, auth requirement, and description.
- **SC-006**: The document contains a version metadata block with both a metadata table (`| **Version** | 1.0 |`) and a blockquote (`> **Version 1.0** ...`) for grep-verifiable version identification.
- **SC-007**: No Python, Django, or DRF code snippets appear anywhere in the document.
- **SC-008**: The Phase 2 section is present and begins with `> **Phase 2 - Not active in Phase 1 delivery.**`.
- **SC-009**: The encrypted CUIT field behaviour is documented, noting blind-index equality search only.
- **SC-010**: All 6 romaneo state transition endpoints are documented with request schema and expected HTTP response codes, with async endpoints (confirmar-arribo, cerrar) returning HTTP 202.
