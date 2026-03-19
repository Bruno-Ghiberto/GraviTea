# Spec 06: REST API Design -- Implementation Context

**Branch**: `006-acopio-api-design`
**Deliverable**: `Docs/Project Blueprint/REST API Design.md` v1.0
**Type**: Blueprint spec — **single-author document writing, no agent team, no tmux**
**Spec**: `specs/006-acopio-api-design/spec.md` (20 FRs, 10 SCs)
**Plan**: `specs/006-acopio-api-design/plan.md` (13 sections, 13 gates)
**Tasks**: `specs/006-acopio-api-design/tasks.md` (74 tasks)

---

## Execution Protocol

> **BLUEPRINT SPEC (01-08)**: Single author, single Write pass, no agent team.
> Write the ENTIRE document atomically in one Write tool call covering all 13 sections.
> Then verify gates. Fix failures with targeted Edit calls.

### Writing Strategy

1. Read Phase 1 setup tasks (T001-T007) — gather upstream doc sections
2. Write `Docs/Project Blueprint/REST API Design.md` in a SINGLE Write pass (§1-§13)
3. Run verification gates (T068-T074)
4. Fix gate failures with Edit
5. Mark all 74 tasks [x] after verification

### Why Atomic Write?

The summary table (§13) must match endpoints defined in §3-§12. Writing atomically
avoids section-by-section drift. The document is internally cross-referenced — §2
Design Principles are cited by every endpoint section.

---

## RAG Query Protocol

**RULE**: NEVER read full research Markdown files. Use RAG for supplementary facts.

```bash
# Run BEFORE writing — gather domain facts
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo workflow steps truck arrival weight analysis" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "producer current account movements balance grain kilos" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSLPG liquidacion API campos campania grano precio" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "CPE CTG state machine confirmarArribo confirmacionDefinitiva" -l 4
```

### Upstream Docs to Read (specific sections only)

| Source | Sections | What to Extract |
|--------|----------|-----------------|
| `Docs/Project Blueprint/Data Model & Domain Model.md` | §5.3 Romaneo (lines 503-620), §5.4 QualityAnalysis, §5.6 Storage, §6 ProducerAccount (lines 810-900) | Field names, types, nullability → request/response field tables |
| `Docs/Project Blueprint/High-Level Design (HLD).md` | §4 (lines 95-175), §5 (lines 175-250), §8 (lines 486-575), §9.1 (lines 576-620), §10 (lines 683-780) | Container arch, app inventory, sync model, romaneo flow, security |
| `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-002, 005, 008, 010, 013, 021, 022, 028, 029, 030, 032 | Constraints that become API rules |

---

## Critical Domain Facts (inline — no RAG needed for these)

### Romaneo Lifecycle (7 steps → 6 API state transitions)

```
PENDIENTE → EN_PROCESO    confirmar-arribo/  (enqueues confirmarArriboCPE, HTTP 202)
EN_PROCESO → PESADO       peso-bruto/        (captures peso_bruto_kg)
PESADO → ANALIZADO        analizar/          (attaches 9 quality parameters)
ANALIZADO → CONFORME      confirmar/         (immutability gate — no more PATCH)
(tare capture)            tara/              (captures tara_kg post-unload)
CONFORME → CERRADO        cerrar/            (enqueues descargadoDestinoCPE +
                                              confirmacionDefinitivaCPEAutomotor, HTTP 202;
                                              requires tara_kg present, else HTTP 422)
```

**IMMUTABLE after CONFORME**: PATCH/PUT on CONFORME or CERRADO → HTTP 409 `romaneo_immutable`

### Romaneo Fields (31 fields, 7 groups — from Data Model §5.3)

- **Group 1 — Identification**: romaneo_number, status, grain_type (FK), campaign (FK), branch (FK)
- **Group 2 — Timestamps**: ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara
- **Group 3 — Vehicle**: patente_chasis, patente_acoplado, driver_name, driver_dni
- **Group 4 — Weight**: peso_bruto_kg DECIMAL(17,3), tara_kg, peso_neto_bruto_kg, weighbridge_device (FK)
- **Group 5 — CPE/Origin**: cpe_numero, ctg_codigo, producer_cuit, origin_locality
- **Group 6 — Storage**: storage_unit (FK), grain_lot (FK)
- **Group 7 — Outcome**: grado_asignado, bonificacion_rebaja_pct DECIMAL(5,2), tolerance_table_version (FK), peso_neto_conforme_kg DECIMAL(17,3)

### QualityAnalysis (9 parameters — from Data Model §5.4)

humedad_pct, materias_extranas_pct, granos_danados_pct, granos_quebrados_pct,
peso_hectolitrico, proteina_pct, granos_verdes_pct, granos_ardidos_pct, insectos_vivos

### Producer Account (dual-ledger — from Data Model §6)

- **ProducerAccount**: producer_cuit (encrypted), branch, grain_type, campaign, grain_balance_kg, ars_balance, usd_balance
- **AccountMovement** (append-only, 8 types): CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION
- **FijacionRecord**: deposit_movement, liquidacion, pizarra_price, kg_fixed, remaining_unfixed_kg
- **Posición Consolidada**: derived SQL aggregation across branches (ADR-013), not stored

### JWT Claims

`sub` (user UUID), `tenant_id`, `branch_id`, `exp`, `iat`, `jti`, `iss`, `aud`
- Access: 15 min, Refresh: 7 days
- RS256 only; HS256 and `none` rejected at middleware → HTTP 401
- Blacklisting on logout via Redis

### Security Rules

- tenant_id from JWT only — NEVER in URL or body
- Cross-tenant access → HTTP 404 (not 403, prevents enumeration)
- producer_cuit: AES-256-GCM encrypted, HMAC-SHA256 blind index, equality search only
- Append-only ledgers: PATCH/DELETE → HTTP 405

### Sync Model

- Delta pull: `GET /api/v1/sync/delta/?last_seq=N` → `{server_seq, changes[]}`
- Batch push: `POST /api/v1/sync/push/` → per-item conflict signals
- 5 strategies (ADR-029): server_wins, client_wins, most_complete_wins, manual, append_both
- PendingOperation queue for ARCA calls (ADR-030)

### Pagination

- **Cursor-based**: AccountMovement, GrainMovement (append-only, high cardinality)
- **Page-number**: grain-types, romaneo lists, reference data
- Envelope: `{ "count": N, "next": "...", "previous": "...", "results": [...] }`

### Rate Limits

- Auth endpoints: 10 req/min per IP
- Standard endpoints: 1000 req/min per tenant
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Section Drafting Instructions

Write the document following this exact section order. Each section note
gives the content source, estimated lines, and key requirements.

### §1 — Document Metadata (~20 lines)
**Must include BOTH**:
- Blockquote: `> **Version 1.0** · Date: 2026-03-17 · Status: Accepted · Owner: GraviTea Architecture Team`
- Metadata table: `| **Version** | 1.0 |`
- Changelog table (v1.0 entry only)
- "How to read this document" paragraph

### §2 — Design Principles (~80-100 lines)
8 subsections (§2.1-§2.8):
1. RESTful Resource Orientation — nouns for resources, verbs as sub-resource actions
2. Versioning Policy — `/api/v1/`, 12-month deprecation notice
3. Authentication Model — JWT RS256 bearer, HS256/none rejected
4. Tenant Scope Enforcement — tenant_id from JWT, HTTP 404 on cross-tenant
5. Error Format — RFC 7807 Problem Details, domain extensions
6. Pagination Strategy — cursor vs page-number, envelope
7. Filtering & Ordering — `?ordering=field,-field`, ISO 8601 date ranges
8. Rate Limiting Headers — X-RateLimit-* headers

### §3 — Authentication API (~80-100 lines)
- §3.1 POST /api/v1/auth/token/ — request: {username, password}, response: {access, refresh}, 200/401
- §3.2 POST /api/v1/auth/token/refresh/ — request: {refresh}, response: {access}, 200/401
- §3.3 POST /api/v1/auth/logout/ — request: {refresh}, response: 204 No Content
- §3.4 JWT Claim Reference Table (8 claims)
- §3.5 **Mermaid #1**: Auth flow sequence diagram

### §4 — Grain Reference API (~60-80 lines)
- §4.1 GET /api/v1/acopio/grain-types/ — **global table, no tenant scope**
- §4.2 GET /api/v1/acopio/tolerance-tables/ — global
- §4.3 GET /api/v1/acopio/merma-tables/ — global
- §4.4 GET /api/v1/acopio/campaigns/ — **per-tenant** (CampanaConfig)

### §5 — Romaneo API (~250-300 lines, LARGEST section)
- §5.1 Romaneo Resource Schema — FULL field tables from all 7 groups
- §5.2 POST create — 201 Created
- §5.3 GET list — filterable by status, grain_type, campaign, branch
- §5.4 GET retrieve — nested quality_analysis + merma_calculation
- §5.5 PATCH update — guard: PENDIENTE or EN_PROCESO only, else 409
- §5.6 State Transitions (6 endpoints):
  - §5.6.1 confirmar-arribo/ → EN_PROCESO (HTTP 202, async ARCA)
  - §5.6.2 peso-bruto/ → PESADO
  - §5.6.3 analizar/ → ANALIZADO (9 quality fields)
  - §5.6.4 confirmar/ → CONFORME (immutability gate)
  - §5.6.5 tara/ — post-unload tare capture
  - §5.6.6 cerrar/ → CERRADO (HTTP 202, 2 async ARCA calls, requires tara_kg)
- §5.7 GET merma-preview/ — non-persisting
- §5.8 **Mermaid #2**: Romaneo lifecycle sequence diagram
- §5.9 Immutability Rules — HTTP 409 `romaneo_immutable` JSON example

### §6 — Quality Analysis API (~50-60 lines)
- §6.1 Schema — 9 quality parameter fields
- §6.2 POST create — guard: romaneo EN_PROCESO or PESADO
- §6.3 GET retrieve
- §6.4 PATCH update — guard: romaneo ANALIZADO only

### §7 — Storage API (~60-70 lines)
- §7.1-§7.2 storage-units list/detail with current_occupancy_kg (derived)
- §7.3-§7.5 grain-lots list/detail + cursor-paginated movements

### §8 — Weighbridge API (~30-40 lines)
- §8.1 GET list devices
- §8.2 GET live reading — HTTP 503 if disconnected

### §9 — Producer Accounts API (~100-120 lines)
- §9.1 Account Resource Schema
- §9.2-§9.3 accounts list/detail
- §9.4 movements cursor-paginated ledger (append-only, HTTP 405 on PATCH/DELETE)
- §9.5 GET posicion-consolidada/ — **derived view** (ADR-013), query: producer_cuit + campaign
- §9.6-§9.7 fijaciones create/list
- §9.8 **Encrypted CUIT note** — blind index, equality only, no LIKE/range

### §10 — Offline Sync API (~100-120 lines)
- §10.1 Sync Model Overview — watermarks, 5 conflict strategies
- §10.2 GET delta/ — last_seq param, server_seq response
- §10.3 POST push/ — batched mutations, per-item conflict signals
- §10.4-§10.5 pending-ops list + retry
- §10.6 Conflict Signal Schema — {status, conflict_strategy, server_version}
- §10.7 **Mermaid #3**: Sync round-trip sequence diagram

### §11 — Error Reference (~60-80 lines)
- §11.1 RFC 7807 format with JSON template
- §11.2 Domain Error Catalog (11 types):
  `romaneo_immutable`, `invalid_state_transition`, `tenant_mismatch`,
  `cpe_not_confirmed`, `insufficient_grain_balance`, `arca_unavailable`,
  `tare_weight_required`, `weighbridge_disconnected`, `append_only_violation`,
  `token_expired`, `invalid_algorithm`
- §11.3 HTTP Status Code Decision Table

### §12 — Phase 2 Endpoints (~40-50 lines)
- **MUST open with**: `> **Phase 2 — Not active in Phase 1 delivery.**`
- §12.1 Liquidaciones: POST + GET (spec-14)
- §12.2 Facturación: POST + GET PDF (no spec assigned)
- §12.3 ARCA queue integration notes

### §13 — Endpoint Summary Table (~60-80 lines)
- Complete table: Method | URL | App | Phase | Auth | Description
- **Must include EVERY endpoint from §3-§12**
- Minimum 35 rows

---

## Review Checklist (run after writing)

| # | Gate | Command | Expected |
|---|------|---------|----------|
| G1 | Version metadata | `grep 'Version 1.0' <file> \| wc -l` | ≥ 2 |
| G2 | §2 subsections | Count §2.1-§2.8 | All 8 present |
| G3 | Mermaid diagrams | `grep -c '` `` ` `` `mermaid' <file>` | ≥ 3 |
| G4 | Romaneo endpoints | Count /api/v1/acopio/romaneos | ≥ 11 |
| G5 | Posicion consolidada | `grep -i 'posicion.consolidada' <file>` | Match: "derived view" |
| G6 | Encrypted CUIT | `grep -i 'blind.index' <file>` | Match found |
| G7 | Domain errors | Count error types in §11.2 | ≥ 10 |
| G8 | Phase 2 label | `grep 'Phase 2' <file>` | "Not active in Phase 1" |
| G9 | Summary table | Count `\| .* \| /api/v1/` rows | ≥ 35 |
| G10 | Headings | `grep -c "^#" <file>` | ≥ 40 |
| G11 | No code | `grep -ciE 'import \|from .* import\|class .*View'` | 0 |
| G12 | No TBD | `grep -ci 'TBD\|to be determined\|TODO'` | 0 |
| G13 | HTTP 202 async | `grep -c '202' <file>` | ≥ 2 |

---

## Done Criteria

The document is DONE when ALL of the following are true:

1. All 13 gates (G1-G13) pass
2. `grep -c "^#" <file>` ≥ 40 headings
3. `grep -c '```mermaid' <file>` ≥ 3 diagrams
4. All 13 top-level sections present with no TBD/placeholder
5. Every Phase 1 endpoint has request AND response field tables
6. Endpoint summary table covers every endpoint from §3-§12
7. Version metadata: blockquote AND table cell
8. No Python/Django/DRF code snippets
9. Phase 2 opens with blockquote
10. Encrypted CUIT note in §9.8
11. All 6 romaneo state transitions with status codes (HTTP 202 for async)
12. All 74 tasks in tasks.md marked [x]

---

## Post-Implementation

After all gates pass:
1. Save Serena memory: `session-2026-03-17-spec06-api-design-complete`
2. Save Engram observation with deliverable summary
3. Update `specs/006-acopio-api-design/spec.md` Status from Draft → Complete
