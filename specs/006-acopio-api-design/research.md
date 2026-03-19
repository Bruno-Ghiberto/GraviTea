# Research: REST API Design for GraviTea Acopio ERP

**Feature**: `006-acopio-api-design`
**Date**: 2026-03-17

## R1: Romaneo Endpoint Field Sources

**Decision**: All romaneo request/response fields taken verbatim from Data Model §5.3 (31 fields, 7 groups).
**Rationale**: Data Model v1.0 is the single source of truth. No new fields invented by this spec.
**Alternatives Considered**: Creating abbreviated field subsets per endpoint — rejected because downstream implementation specs need exact field-to-endpoint mapping.

## R2: State Transition Endpoint Sequencing

**Decision**: 6 state transition endpoints map to the romaneo lifecycle: confirmar-arribo → EN_PROCESO, peso-bruto → PESADO, analizar → ANALIZADO, confirmar → CONFORME, tara (weight capture), cerrar → CERRADO.
**Rationale**: HLD §9.1 ten-step physical workflow + Data Model §5.3 state machine. Tare captured after unloading (between CONFORME and CERRADO), consistent with the `ts_tara` field comment "CPE definitiva".
**Alternatives Considered**: Combining tara into cerrar — rejected because tare weight capture and CPE closure are separate physical events.

## R3: ARCA Async Call Pattern

**Decision**: Endpoints triggering ARCA WSCPE calls (confirmar-arribo, cerrar) return HTTP 202 Accepted, enqueue to PendingOperation.
**Rationale**: ADR-030 (Store-and-Forward Queue) mandates async. ADR-028 (Offline-First) requires romaneo issuance to proceed regardless of ARCA connectivity.
**Alternatives Considered**: Synchronous ARCA calls with timeout — rejected because harvest peak connectivity is unreliable.

## R4: Producer Account Derived Views

**Decision**: Posición consolidada is a GET-only computed endpoint (SQL aggregation), not a stored CRUD resource.
**Rationale**: ADR-013 explicitly governs this. Cross-branch aggregation by producer_cuit + campaign.
**Alternatives Considered**: Materialized view — rejected because data freshness is critical and the query is bounded (one tenant's branches).

## R5: Pagination Strategy Split

**Decision**: Cursor-based for append-only ledgers (AccountMovement, GrainMovement). Page-number for reference data and romaneo lists.
**Rationale**: Constitution XIII mandates cursor for large datasets. Append-only ledgers grow unboundedly; reference data is small and bounded.
**Alternatives Considered**: Cursor-only for everything — rejected because page-number gives count awareness useful for romaneo list UX.

## R6: Error Response Format

**Decision**: RFC 7807 Problem Details with domain extensions (`romaneo_status`, `conflict_strategy`).
**Rationale**: Industry standard for structured errors. Extensions enable programmatic handling of grain-domain errors.
**Alternatives Considered**: Custom JSON error envelope — rejected for interoperability reasons.

## R7: Encrypted CUIT Field API Behaviour

**Decision**: Plaintext CUIT in requests, transparent server-side encryption, blind index equality search only.
**Rationale**: ADR-022 (AES-256-GCM + HMAC-SHA256 blind index). Non-deterministic ciphertext requires blind index for search.
**Alternatives Considered**: Client-side encryption — rejected because it complicates sync and requires key distribution to offline clients.

## R8: Phase 2 Endpoint Shapes

**Decision**: URL patterns and HTTP methods only, no full field tables. Clearly labelled "Phase 2 — Not active in Phase 1."
**Rationale**: Stabilizes URL contract for planning. Full schemas deferred to Phase 2 specs.
**Alternatives Considered**: Full field tables — rejected because Data Model entities for liquidaciones are Phase 2 and may change.
