# Implementation Context: High-Level Design (HLD) Document

**Branch**: `005-acopio-hld` | **Date**: 2026-03-17
**Spec**: `specs/005-acopio-hld/spec.md` | **Plan**: `specs/005-acopio-hld/plan.md`
**Target deliverable**: `Docs/Project Blueprint/High-Level Design (HLD).md` (NEW FILE)

---

## 1. What You Are Writing

A single Markdown file (~1,500–2,500 lines) that synthesises the four upstream blueprint documents
(Vision v1.0, PRD v1.0, Data Model v1.0, ADR v1.0) into one diagram-driven architecture
reference for the GraviTea Acopio ERP. This is the **architecture reference** every developer,
AI agent, and architect uses when building or reviewing code against specs 09+.

**This is a documentation-only task.** No code, no migrations, no tests. The output is a
Markdown file with 7 Mermaid diagrams, ≥40 headings, 13 top-level sections, and zero hedging
language.

**Core constraint**: The HLD cites ADRs — it does not reproduce their rationale. Point readers to
`Docs/Project Blueprint/Architecture Decision Records (ADR).md` for the "why". The HLD provides
the "what" and "how the pieces connect".

---

## 2. Source Files — What to Read Before Writing

Read in this order. Do not skip ahead.

| File | Purpose | Read When |
|------|---------|-----------|
| `specs/005-acopio-hld/research.md` | **PRIMARY** — domain facts, verbatim constraints, numerical values, entity ownership, ARCA URLs, ADR cross-reference map | Before starting any section |
| `Docs/PROMPTS/spec-05-hld/05-plan.md` | **SECONDARY** — section-by-section writing plan, all 7 Mermaid starter skeletons, content guidelines, writing order | Before starting §3+; for every diagram |
| `specs/005-acopio-hld/tasks.md` | Task IDs, exact content requirements per task, phase checkpoints | During writing (per-task reference) |
| `specs/005-acopio-hld/plan.md` | Constitution check, writing order, checkpoint gate commands | Before starting; at each gate |
| `specs/005-acopio-hld/quickstart.md` | Acceptance verification script (run at end) | At T049 |

**ADR document** (`Docs/Project Blueprint/Architecture Decision Records (ADR).md`) — keep open
for ADR title lookups. The format for citations is: **ADR-NNN (Title)**. Look up the exact title
when writing each section.

**Do NOT** read `Docs/Project Blueprint/Data Model & Domain Model.md` or `PRD.md` in full. All
entity names and domain facts are pre-extracted in `research.md`. Use RAG queries for any
supplementary detail.

---

## 3. Writing Protocol

### 3.1 File Target

Every task writes to a single file:
```
Docs/Project Blueprint/High-Level Design (HLD).md
```

T002 creates the file with a skeleton of all 13 H2 headings. All subsequent tasks fill in or
append to the appropriate section. **Never overwrite an already-completed section.**

### 3.2 Section Addressing

Each section is addressed by its heading: `## Section N: Title`. Use the H2/H3 structure from
`Docs/PROMPTS/spec-05-hld/05-plan.md §4 Section-by-Section Writing Plan` for heading names.

### 3.3 Tone and Style Rules

- **Present tense**: "The system uses...", "Layer 2 enforces...", "The queue persists..."
- **Declarative**: Every sentence states what the system does, not what it might do
- **No hedging**: Zero instances of "TBD", "TODO", "FIXME", "possibly", "might consider"
- **Domain term first use**: Define each term on first use in each major section (§). See
  `research.md §2` for definitions ready to paste
- **ADR format**: "ADR-NNN (Title)" — three-digit ID, exact title from the ADR document
- **SOAP method names**: backtick format — `liquidacionAutorizar`, `confirmarArriboCPE`
- **Speedup values**: × symbol only — `8.7×`, not `8.7x`
- **App names**: backtick code format — `apps/acopio`, `apps/core`
- **Entity names**: PascalCase in backtick format — `Romaneo`, `PendingOperation`

### 3.4 Mermaid Diagrams

- Use the starter skeletons in `Docs/PROMPTS/spec-05-hld/05-plan.md §5`
- Expand starters — do not paste them verbatim without adding labels, error paths, or actor notes
- After writing each diagram, mentally verify it renders (check bracket matching, `-->` vs `--`)
- Test complex diagrams at https://mermaid.live before committing to file

### 3.5 RAG Query Protocol

Before writing each section group (not each individual task), run the relevant RAG queries below
to surface any supplementary facts not in `research.md`. The queries below are targeted — run
them in the terminal:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -l 5
```

**Never read the full PDFs in `Docs/Researches/`.** All domain knowledge comes through RAG or
is inlined in `research.md`.

---

## 4. Task Execution Guide

### Phase 1: Setup (T001–T002)

**T001 — Verify upstream sources**

```bash
test -f "Docs/Project Blueprint/Architecture Decision Records (ADR).md" && echo "ADR OK"
test -f "Docs/Project Blueprint/Data Model & Domain Model.md" && echo "DATA-MODEL OK"
test -f "Docs/Project Blueprint/PRD.md" && echo "PRD OK"
```

All three must print OK before proceeding.

**T002 — Create HLD skeleton**

Write the file with these 13 H2 headings in order, each with placeholder H3 stubs:

```markdown
# High-Level Design (HLD) — GraviTea Acopio ERP

## 1. Document Metadata
## 2. System Overview
## 3. System Context (C4 Level 1)
## 4. Container Architecture (C4 Level 2)
## 5. Component Overview by Django App
## 6. ARCA Integration Architecture
## 7. Weighbridge Integration Architecture
## 8. Offline-First Architecture
## 9. Data Flow Diagrams
## 10. Security Architecture
## 11. Deployment Topology
## 12. AI/ML Readiness Architecture
## 13. Technology Decisions Cross-Reference
```

---

### Phase 2: Foundational (T003–T005)

**T003 — §1 Document Metadata**

Render as a Markdown table:

| Field | Value |
|-------|-------|
| **Version** | 1.0 |
| **Date** | 2026-03-17 |
| **Status** | Accepted |
| **Owner** | GraviTea Architecture Team |
| **Upstream Documents** | ADR v1.0, Data Model v1.0, PRD v1.0, Vision v1.0 |

**T004 — §2 System Overview**

Three subsections:
- **§2.1 Purpose**: This document is the architecture reference for GraviTea Acopio ERP, translating 35 architectural decisions into diagrams and component maps. A new engineer reading only this document understands the container structure, external integrations, core data flows, and architectural constraints without consulting specs 01–04.
- **§2.2 Out of Scope** (explicit list — do not summarise or soften): database ERD and entity field details (spec-03), individual ADR rationale text (spec-04), REST API endpoint specifications (spec-06), detailed ARCA SOAP XML schemas and example payloads (spec-08a), Phase 4 ML model implementation details, frontend architecture.
- **§2.3 How to Read This Document**: All diagrams use Mermaid notation. Architecture sections cite ADRs in the format "ADR-NNN (Title)". For any architectural rationale, consult the cited ADR in spec-04.

**T005 — §13 Skeleton**

Write the §13 table header and 8 empty category rows with placeholder ADR IDs. Add a note at the top: `<!-- FILL AFTER §3–§12 COMPLETE — see T046 -->`. See `research.md §9` for the ADR ID list per category.

---

### Phase 3: US1 — Developer Architecture Reference (T006–T017)

**RAG queries to run before starting Phase 3:**

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'grain storage ERP offline sync architecture' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'Django multi-tenant RLS architecture' -l 5
```

**T006 — §3.1 C4 Level 1 System Context Diagram**

Expand Diagram 1 from `05-plan.md §5`. Requirements:
- All 8 external actors present (ARCA WSAA, WSLPG, WSCPE, WSFEv1, Weighbridge Device, Browser Client, Mobile Client Phase 3, Operator PC)
- Every arrow labeled with protocol
- Mobile Client labeled "Phase 3 – Future" with dashed arrow style
- GraviTea ERP as system boundary (subgraph or styled node)

**T007 — §3.2–§3.3 Actor Descriptions and System Boundary**

One paragraph per external actor (8 paragraphs). For each: what it is, what protocol it uses,
its regulatory significance. Then §3.3: what is inside the system boundary (Django containers),
what is outside (ARCA services, devices, browsers). Cite ADR-025 for ARCA, ADR-032 for
weighbridge.

**T008 — §4.1 C4 Level 2 Container Architecture Diagram**

Expand Diagram 2 from `05-plan.md §5`. Requirements:
- Subgraph boundary: "GraviTea ERP System"
- 5 containers with exact protocol labels: `SQL (psycopg3)`, `redis-py`, `Python FFI (import)`, `HTTP/JSON`
- Qdrant marked optional (note in label or dashed border)
- ARCA external services and Weighbridge shown outside subgraph with arrows from DjangoAPI

**T009 [P] — §4.2 Container Descriptions Table**

Use values from `research.md §8`. Python fallback sentence: "If the Rust `.so` extension fails
to load at Django startup, the Python fallback activates automatically without operator
intervention."

**T010 [P] — §4.3 Communication Matrix**

Table: Container ↔ Container | Protocol | Direction | Purpose.
Rows: Django→PostgreSQL, Django→Redis (3 uses), Django→RustExt, Django→Qdrant,
Django→ARCA WSAA, Django→ARCA WSLPG, Django→ARCA WSCPE, Django→ARCA WSFEv1,
Django→WeighbridgeDevice.

**T011 — §4.4 Rust/PyO3 Acceleration Boundary**

4 criteria (any one triggers Rust acceleration):
1. Hot path >1,000 calls/second (GIL becomes a bottleneck)
2. GIL contention in multi-request batch processing
3. CPU-bound computation: cryptography, regex validation, merma calculation
4. Adversarial input patterns requiring ReDoS-resistant regex (ADR-024)

Benchmark table — copy exactly from `research.md §4` with × symbol on all 7 rows. Cite ADR-031.

**T012 — §5 Component Overview (all 8 apps)**

Use the entity ownership table from `research.md §6`. Structure per app:
- Subsection heading: `### 5.N — apps/name (Phase 2)` or `### 5.N — apps/name`
- Opening sentence: brief description + phase annotation
- Owned entities list (from research.md §6)
- Key external calls (ARCA service, if any)
- ADR citation

Phase 2 annotation REQUIRED for `apps/facturacion` and `apps/liquidaciones`. No annotation on
Phase 1 apps.

**T013 — §8.1–§8.3 Offline-First Architecture Principle**

§8.1 must include both verbatim-equivalent sentences from `research.md §3 VC-002`:
- "44% of operators report 'regular' (not good) connectivity quality (INTA/ENACOM 2021)"
- "Offline is the base operating mode, not a degraded fallback"
Cite ADR-028.

§8.2: local data store — SQLite for standalone client / on-premises PostgreSQL for plant server;
UUID v4 prevents ID collision during offline operation. Cite ADR-002.

§8.3: sync protocol — push/pull idempotent operations; `SyncSession` watermark tracks last
synced position; vector clock resolves ordering ambiguity. Cite ADR-029.

**T014 — §8.4 Conflict Resolution Engine Table**

Copy the table exactly from `research.md §3` (or from `05-plan.md §4 §8`). Must have 5 rows
with exact strategy names (`server_wins`, `last_write_wins`, `additive`, `most_complete_wins`,
`server_assigns_final`), target data type, and implementation column. Cite ADR-029.

**T015 — §8.5 Store-and-Forward Queue**

`PendingOperation` entity: `operation_type`, `payload`, `status`, `retry_count`. Queue is
durable across device restarts (persisted to local storage). Transmitted FIFO on reconnect.

Three queued CPE operations (these exact method names):
- `confirmarArriboCPE`
- `descargadoDestinoCPE`
- `confirmacionDefinitivaCPEAutomotor`

State explicitly: "Store-and-forward is NOT used for fiscal invoice issuance. The CAEA offline
path handles that separately (see §6.5 and §8.6)." Cite ADR-030.

**T016 — §9.1 Romaneo Reception Flow**

Expand Diagram 5 from `05-plan.md §5`. MUST have exactly 10 steps in the sequence diagram.

After the diagram, write the numbered step list — copy from `research.md §7`. Add two notes:
- After step 1: "If the RS-232 connection is lost, the Weighbridge Driver's watchdog triggers
  a reconnection loop and alerts the operator. The romaneo cannot proceed without a weight reading."
- After step 10: "The CPE confirmation call is enqueued in PendingOperation (ADR-030) and
  transmitted on connectivity restore. The romaneo is issued immediately regardless of CPE queue
  state."

**T017 — §9.3 Sync Data Flow Diagram**

Nodes: Local write → SyncSession queue → connectivity check →
(connected) batch push → server conflict resolution → server merge →
pull delta → local apply.
Add a note: offline writes queue indefinitely; transmission is FIFO on reconnect. Cite ADR-028,
ADR-030.

**Checkpoint Gate 1** (after T017):
```bash
grep "Version 1.0" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep -c "^### ADR-" "Docs/Project Blueprint/High-Level Design (HLD).md"  # must be 0
grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1\|Weighbridge\|Browser\|Mobile\|Operator" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"  # must be ≥8
```

---

### Phase 4: US2 — ARCA Integration Architecture (T018–T025)

**RAG queries to run before starting Phase 4:**

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA AFIP ARCA token authentication TRA CMS' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG liquidacion primaria granos AFIP ARCA webservice' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'CAEA offline invoicing quincena fiscal authorization code' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'CPE carta porte electronica WSCPE lifecycle confirmar arribo' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SISA RUCA productor retenciones ganancias IVA grain' -l 5
```

**T018 — §6.1 ARCA Hub-and-Spoke Overview Diagram**

`graph LR` with WSAA at center. Three spokes to WSLPG (grain settlement), WSCPE (CPE lifecycle),
WSFEv1 (electronic invoicing). Label each spoke with the primary SOAP method category. All
communication routes through WSAA first (token validation). Cite ADR-025.

**T019 — §6.2 WSAA Authentication Flow**

Expand Diagram 4 from `05-plan.md §5`. Must include both the cache HIT path and cache MISS path
in an `alt` block. Add error path for WSAA timeout (exponential backoff, max 3 retries). Add
path for token expiry mid-batch (re-authenticate and resume at the current operation; do not
restart the batch from the beginning).

Key values from `research.md §4`:
- Token lifetime: **12 hours**
- Redis TTL: **11 hours** (1-hour safety margin)
- Token type: Token + Sign pair (both needed for service calls)

**T020 — §6.3 WSLPG Integration**

Two URLs (from `research.md §5`):
- Production: `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl`
- Homologation: `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl`

Note: homologation requires pre-seeded ARCA test CUITs. Random CUITs fail validation silently.

Method: `liquidacionAutorizar` → returns COE (Código de Operación Electrónico). One submission
per grain type: "`codGrano` is at the XML root — one WSLPG filing per grain type per batch."
Cite ADR-019.

SISA blocking gate — 4 tiers from `research.md §4`:
| SISA Estado | IVA | Ganancias |
|---|---|---|
| Estado 1 | 5% | 0% |
| Estado 2 | 8% | 2% |
| Estado 3 | 10.5% | 15% |
| Non-registered | 16% | 30% |

SISA check is blocking — filing is rejected if SISA validation fails. Cite ADR-027.

**T021 — §6.4 WSCPE Lifecycle**

4 WSCPE protocol states (these are web service protocol states, NOT app-level workflow states):

```
Activa (issued, 5-day Automotor validity)
  → Arribo (confirmarArriboCPE)
  → Descargada (descargadoDestinoCPE)
  → Confirmada_Definitiva (confirmacionDefinitivaCPEAutomotor)
```

Add a clear note: "'Vencida' is a derived condition (timer-based validity expiry) — it is NOT
a WSCPE state code. The system detects approaching expiry and alerts the operator; there is no
automatic extension." Alert threshold: approaching 5-day limit during extended offline period.

**T022 — §6.5 WSFEv1/CAEA**

**CRITICAL**: This subsection MUST include the following sentence verbatim (or equivalent
unambiguous substance):

> "CAEA codes MUST be obtained before the offline period begins. An invoice issued with a
> deferred CAE (authorization obtained after issuance) is a legally invalid fiscal document."

WSFEv1: per-invoice round-trip to ARCA using `FECAESolicitar`. Returns CAE code on success.

CAEA offline path: quincena (15-day period) batch codes obtained in advance. The Rust CAEA batch
builder (feature 024, `serde_json`, GIL-released batch processing) assembles and validates the
quincena request before submission. Cite ADR-026.

**T023 — §6.6 Certificate Management**

Each ARCA service requires a **separate** X.509 certificate:
- WSLPG certificate (grain settlement)
- WSCPE certificate (CPE lifecycle)
- WSFEv1 certificate (electronic invoicing)

Shared certificate is rejected at the service level. Private keys stored in Google Cloud Secret
Manager — never in code, env vars, Docker configurations, or git history. Cite ADR-022.

**T024 — §6.7 ARCA Error Paths**

Table or structured list — one row/bullet per failure mode, with system response and operator
action required:

| Failure | System Response | Operator Action |
|---------|----------------|-----------------|
| WSAA timeout | Exponential backoff, up to 3 retries | None required unless all retries fail |
| TA token expiry mid-WSLPG batch | Re-authenticate (LoginCMS), resume at current operation | None |
| WSLPG schema error | Return user-facing error with ARCA error code | Correct data and retry |
| SISA block | Return user-facing error with blocking reason | Resolve SISA status for producer |
| CPE validity window expiry (>5 days offline) | Operator alert; no automatic extension | Manual intervention required |
| CAEA quincena expiry during extended outage | Invoicing blocked; no workaround | Obtain new CAEA codes before next invoice |

**T025 — §9.2 Fiscal Authorization Flow**

Expand Diagram 6 from `05-plan.md §5`. The "INVOICING BLOCKED" node must reference the CAEA
legal constraint: add a note "See §6.5 — CAEA codes must be obtained before the offline period
begins." Show the quincena batch pre-fetch step that populates the CAEA code store before the
offline period starts (this is what prevents the blocked path).

**Checkpoint Gate 2** (after T025):
```bash
grep "CAEA codes MUST be obtained before" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "codGrano" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "8\.7×\|8\.8×\|4\.4×" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "Phase 2" "Docs/Project Blueprint/High-Level Design (HLD).md"
```
All must return ≥1 match.

---

### Phase 5: US3 — Product Owner Deployment Review (T026–T031)

**RAG queries to run before starting Phase 5:**

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'grain storage Argentina internet connectivity rural offline' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'acopio ERP deployment single server SMB cloud infrastructure' -l 5
```

**T026 — §8.6 CAEA Offline Fiscal Path**

This section is for the product owner — explain the operational consequence without assuming
ARCA familiarity. The key message: harvest planning must include a connectivity window before
going offline specifically to obtain CAEA quincena codes. If the operator fails to do this and
connectivity is lost, invoicing is blocked for the duration of the outage. There is no workaround.

Cross-reference: "See §6.5 (CAEA legal constraint) for the regulatory basis of this restriction."

**T027 — §8.7 Offline Error Paths**

Two scenarios — write as a structured error path subsection:

1. **CPE validity window expiry** (5-day Automotor limit):
   - System detects when a queued CPE confirmation is approaching the 5-day limit
   - Operator is alerted; the system does NOT automatically extend validity
   - Required action: operator must ensure connectivity to transmit the confirmation before expiry

2. **CAEA quincena expiry during extended outage**:
   - Invoicing is blocked immediately when quincena codes expire
   - No automatic workaround exists
   - Required action: obtain new CAEA codes (requires connectivity + ARCA service availability)

**T028 — §11.1 Development Docker Compose Environment**

Services table:

| Service | Port | Role | Notes |
|---------|------|------|-------|
| `django-api` | 8000 | Django API (WSGI/Gunicorn) | — |
| `postgres` | 5432 | PostgreSQL 18.1 | Primary datastore |
| `redis` | 6379 | Redis 7.x | Cache + rate limiter + TA token cache |
| `rust-builder` | — | Maturin build stage | NOT a runtime service; builds .so in multi-stage Docker build |
| `qdrant` | 6333 | Qdrant vector search | Optional; disabled by default |

Add note: "A mock serial device simulates weighbridge RS-232 communication in the dev environment,
eliminating the need for physical hardware during development."

**T029 — §11.2 Production Topology Narrative**

Target: 1–5 plants, small-to-medium acopiadores. Two options:

**Full-cloud option**: Django API on GCP Cloud Run; PostgreSQL 18.1 on Cloud SQL Enterprise Plus;
Redis on GCP Memorystore (or Cloud Run sidecar). All ARCA calls from the cloud endpoint. Clients
are thin browser-based or offline-capable; they sync to the cloud server.

**Hybrid option**: Plant server (Windows or Linux PC at the grain storage facility) runs Django
API + local PostgreSQL for offline-first operations. A lightweight cloud sync server relays ARCA
calls and handles multi-plant synchronisation. ARCA credentials and keys remain in Google Cloud
Secret Manager; the plant server holds only session-scoped ARCA tokens.

Both options: deployment unit is a **single Django process** (modular monolith, ADR-003). No
microservices, no service mesh, no Kubernetes required for initial scale. SMB budget compatible:
USD 90–360/month (ADR-004 shared schema cost model).

**T030 — §11.3 Production Topology Diagram**

`graph TD` — two subgraphs side by side (or a branching layout) showing full-cloud and hybrid
options. Label arrows with protocols. Key nodes per option:

Full-cloud: `Browser/OperatorPC` → (HTTPS/JSON + offline sync) → `Cloud Run Django API` →
(SQL psycopg3) → `Cloud SQL PostgreSQL` and (SOAP/XML over HTTPS) → `ARCA Services`.

Hybrid: `OperatorPC (offline)` → (local LAN) → `Plant Server (Django + local PostgreSQL)` →
(sync protocol) → `Cloud Sync Server` → (SOAP/XML over HTTPS) → `ARCA Services`.

**T031 — §11.4 Infrastructure Cost Rationale**

Cite ADR-003 (modular monolith — single deployment unit, no per-service overhead) and ADR-004
(shared schema — fixed database cost regardless of tenant count). State the SMB SaaS budget
range: USD 90–360/month. No per-tenant database provisioning is needed; all tenants share the
same schema under RLS enforcement.

**Checkpoint Gate 3** (after T031):
```bash
grep "confirmarArriboCPE\|descargadoDestinoCPE\|confirmacionDefinitivaCPEAutomotor" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"  # must be ≥3 matches
grep "server_wins\|last_write_wins\|additive\|most_complete_wins\|server_assigns_final" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"  # must be 5 matches
grep "44%" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "KYASERV" "Docs/Project Blueprint/High-Level Design (HLD).md"
```

---

### Phase 6: US4 — New Team Member Onboarding (T032–T045)

**RAG queries to run before starting Phase 6:**

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'weighbridge Modbus RTU RS-232 9600 baud Argentine scale' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'Sipel Systel GaMa weighbridge indicator protocol' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'KYASERV RS-232 Ethernet serial bridge weighbridge' -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'grain quality AI machine learning silo storage prediction' -l 5
```

**T032 — §7.1 Weighbridge 3-Tier Protocol Stack Diagram**

`graph TD` with three tiers stacked vertically. Show the WeighbridgeDevice entity connecting to
Django API via each tier path. The diagram conveys the fallback hierarchy: Tier 1 (preferred) →
Tier 2 (fallback for unsupported brands) → Tier 3 (network bridge overlay for any tier). Cite
ADR-032.

**T033 [P] — §7.2 Tier 1: Modbus RTU and ASCII Command-Response**

From `research.md §4`:
- RS-232 baseline: 9600 baud, 8N1 — universal for all Argentine indicator brands
- Sipel Orion Modbus RTU: Modbus function codes 03h (read), 06h (write single), 10h (write multiple)
  - Address 0: Gross weight (2 registers, 32-bit signed int)
  - Address 2: Tare weight
  - Address 4: Net weight
  - Address 6: Status flags
- Systel (Clipse, Croma, Bumer): ASCII command/response over RS-232; no Modbus support; proprietary command set

Cite ADR-032.

**T034 [P] — §7.3 Tier 2: Continuous ASCII Stream**

GaMa A12 weighbridge indicator. Emits continuous ASCII stream; no request/response cycle.
Frame format: `{STX}{weight_value}{CR/LF}` at 9600 baud, 8N1. Django weighbridge driver
parses the stream, detects stable-weight condition (3 consecutive readings within ±tolerance),
and captures the stable reading. Cite ADR-032.

**T035 — §7.4 Tier 3: KYASERV RS-232-to-Ethernet Bridge**

KYASERV converts RS-232 serial output to UDP/TCP-IP over LAN. The application server connects
to KYASERV's IP address and port — eliminating the requirement for the application server to be
physically co-located on the weighbridge PC. This enables centralised grain plant management
across multiple weighbridges. Cite ADR-032.

**T036 — §7.5 WeighbridgeDevice Entity and §7.6 Error Paths**

§7.5: `WeighbridgeDevice` is a first-class domain entity (not a configuration entry):
- Fields: `interface_type` (Modbus/ASCII/KYASERV), `connection_address` (serial port path or IP:port), calibration records
- Relationship: `Romaneo.weighbridge_device_id` is a nullable FK with `SET NULL` on decommission
- The entity persists calibration history for audit and ML purposes

State explicitly: "The 3-tier protocol stack covers all major Argentine weighbridge brands
currently in the market. New brands not in this stack require a new driver implementation
before integration is possible."

§7.6 Error paths:
| Failure | System Response | Operator Action |
|---------|----------------|-----------------|
| RS-232 disconnect | Watchdog loop triggers reconnection attempts; operator alert displayed | Check cable; reconnect |
| Stable-weight timeout | After configurable threshold (default: 60s), prompt for manual entry | Enter weight manually |
| KYASERV unreachable | Fall back to manual entry mode; alert operator | Check network; verify KYASERV device |

**T037 — §10.1 Defense-in-Depth Diagram**

Expand Diagram 3 from `05-plan.md §5`. Add rejection paths out of each layer:
- Layer 1 failure: `ORM raises PermissionDenied` → HTTP 403 before query executes
- Layer 2 failure: PostgreSQL rejects query at RLS policy → 0 rows returned or query error
- Layer 3 failure: JWT claim validation fails → HTTP 401 before view logic runs

Cite ADR-005.

**T038 [P] — §10.2 Layer 1: ORM TenantBoundManager**

`TenantBoundManager` overrides the default QuerySet to auto-filter `WHERE tenant_id = :current_tenant`
on every ORM query. All models inherit `TenantBoundModel` which uses this manager. Direct ORM
access that bypasses `TenantBoundModel` is a constitution violation (Principle II). Cite ADR-005.

**T039 [P] — §10.3 Layer 2: PostgreSQL RLS**

Session variable set at transaction start (verbatim from `research.md §3 VC-003`):
```sql
SET LOCAL app.current_tenant_id = '{uuid}';
```

RLS policy on all per-tenant tables:
```sql
USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
```

**Global tables exempt** from RLS (ADR-010): `GrainType`, `ToleranceTable`, `MermaTable` are
shared across tenants by design — they contain regulatory reference data, not tenant-specific
data. Cite ADR-005, ADR-010.

**T040 [P] — §10.4 Layer 3: IDOR/JWT Validation**

JWT claims validated on every request: `iss`, `aud`, `exp`, `tenant_id`, `branch_id`.

Algorithm whitelist: **RS256 only**. HS256 and `none` are rejected at middleware before any
view logic executes. 4096-bit RSA key pair. Access token: 15 minutes. Refresh token: 7 days.

Token blacklisting on logout prevents replay attacks. Cite ADR-021.

**T041 [P] — §10.5 Field-Level Encryption**

AES-256-GCM for PII fields. HMAC-SHA256 deterministic blind index for encrypted fields that
require equality search.

Encrypted fields: producer CUIT, full name, address, DNI, contact data.

**Blind index limitation**: The blind index supports only exact-match (equality) searches.
Range queries (`WHERE cuit BETWEEN ...`) and pattern searches (`WHERE name LIKE '%garcia%'`)
are not possible on encrypted fields. Cite ADR-022.

**T042 — §10.6 Key Management**

All master keys (AES-256-GCM, RSA private keys, ARCA X.509 private keys) are stored in Google
Cloud Secret Manager. Keys are never placed in: application code, environment variables (`.env`
files), Docker configurations (`docker-compose.yml`, `Dockerfile`), or git history. Cite ADR-022.

**T043 — §12.1–§12.5 AI/ML Readiness 4-Layer Strategy**

Write one subsection per layer. Each cites its ADR. Use `research.md §4` for exact field names
and numerical facts.

- **§12.1 Overview**: 4-layer strategy for ML readiness; data is collected today (Layers 1–3);
  Layer 4 is an IoT anchor that requires no schema change when populated in a future phase.
- **§12.2 Layer 1 — Operational**: All grain domain fields captured real-time with full timestamps.
  `DECIMAL(17,3)` precision everywhere — no rounding at rest (ADR-007). No post-hoc reconstruction
  needed.
- **§12.3 Layer 2 — Behavioural**: Provenance fields on all grain domain models: `operator_id`,
  `laboratorista_id`, `device_id` (ADR-034). Six named `Romaneo` timestamps: `ts_entrada`,
  `ts_pesada_bruta`, `ts_calado`, `ts_analisis`, `ts_descarga`, `ts_tara` (ADR-035).
- **§12.4 Layer 3 — Quality History**: `QualityAnalysis` rows per `(grain_type, campaign,
  storage_unit)` combination. This longitudinal quality record per silo enables grain degradation
  prediction (3D-CNN + LSTM, Phase 4). Cite ADR-035.
- **§12.5 Layer 4 — Physical State (IoT-Ready)**: `StorageUnit.environment_sensor_id` as a
  nullable FK anchor. Populating this FK in a future phase requires no structural schema change —
  the hook is in the schema today. Cite ADR-033.

**T044 [P] — §12.6 Phase 4 ML Capabilities (Informative)**

This subsection is **informative only** — do not add requirements. List the Phase 4 ML
capabilities enabled by the data architecture: grain quality degradation prediction; silo
assignment optimisation; weighbridge fraud detection (anomalous weight patterns); pizarra price
forecasting. Close with: "Detailed ML model architecture and training pipeline specifications are
out of scope for this document and are deferred to a future specification (ML Architecture Guide)."

**T045 [P] — §12.7 Qdrant Optional Container**

Qdrant is used in the **development environment** for RAG-based query expansion (enabling the
`qdrant_search.py` pipeline used during spec writing). It is not required for Phase 1 or Phase 2
production deployments. An optional flag in Docker Compose disables it by default in production
builds. Cite ADR-033 (AI/ML readiness, optional component).

**Checkpoint Gate 4** (after T045):
```bash
grep "SET LOCAL app.current_tenant_id" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep ":8000\|:5432\|:6379" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "environment_sensor_id" "Docs/Project Blueprint/High-Level Design (HLD).md"
grep "ts_entrada\|ts_pesada_bruta\|ts_calado\|ts_analisis\|ts_descarga\|ts_tara" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"  # must be ≥6
```

---

### Phase 7: Polish (T046–T049)

**T046 — §13 Technology Cross-Reference Table (complete)**

Fill in all ADR IDs. Use `research.md §9` for the ADR-per-section mapping.

Table structure:
```markdown
| HLD Section | ADR IDs | ADR Titles | Category |
|-------------|---------|------------|----------|
```

Group by 8 categories (from `research.md §9`). Every section §3–§12 must appear in at least
one row. Remove the `<!-- FILL AFTER ... -->` placeholder comment from T005.

**T047 [P] — Mermaid Diagram Syntax Verification**

For each of the 7 diagrams, paste the Mermaid block into https://mermaid.live or run `mmdc`
locally. All must render without syntax errors:

1. §3.1 — C4 Level 1 (`graph TD`)
2. §4.1 — C4 Level 2 (`graph TD` with subgraph)
3. §6.2 — WSAA Auth Flow (`sequenceDiagram`)
4. §9.1 — Romaneo Reception Flow (`sequenceDiagram`)
5. §9.2 — Fiscal Authorization Flow (`flowchart TD`)
6. §10.1 — Defense-in-Depth (`graph TD`)
7. §11.3 — Production Topology (`graph TD`)

Fix any syntax errors before proceeding to T048.

**T048 [P] — Gate 5 Final Verification**

```bash
# Zero hedging language (must return empty)
grep -i "TBD\|TODO\|FIXME\|possibly\|might consider" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"

# Minimum headings
grep -c "^## \|^### " "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥40

# Minimum Mermaid diagrams
grep -c '```mermaid' "Docs/Project Blueprint/High-Level Design (HLD).md"  # ≥6
```

If hedging language is found, replace each instance with a declarative statement. If heading
count is below 40, check that all subsections were written (§4 has §4.1–§4.4, §6 has §6.1–§6.7,
§10 has §10.1–§10.6, §12 has §12.1–§12.7).

**T049 — Quickstart Full Acceptance Verification**

Run the bash script from `specs/005-acopio-hld/quickstart.md §Full Gate Verification`. All 13
checks must show ✓. Common failure modes:

| Check | If it fails | Fix |
|-------|------------|-----|
| `CAEA codes MUST be obtained before` | Sentence missing or rephrased | Restore verbatim sentence in §6.5 |
| `8.7×\|8.8×\|4.4×` | ASCII `x` used instead of `×` | Replace `x` with `×` in benchmark table |
| `server_wins\|...\|server_assigns_final` | Strategy name drift | Restore exact names from research.md §3 |
| `SET LOCAL app.current_tenant_id` | Section 10.3 incomplete | Write missing RLS policy text |
| `environment_sensor_id` | Section 12.5 incomplete | Write missing IoT anchor description |
| Heading count < 40 | Missing subsections | Check §4, §6, §10, §12 for missing H3s |

---

## 5. Section Self-Review Checklist

After completing each section (before moving to the next task), verify:

- [ ] At least one ADR cited in format "ADR-NNN (Title)"
- [ ] No hedging language introduced in this section
- [ ] Domain terms defined on first use (if this is a major section)
- [ ] All Mermaid brackets balanced (`[`, `"`, `subgraph`/`end`)
- [ ] Error paths present for any external integration described (§6, §7, §8)
- [ ] Numbers match `research.md §4` (no off-by-one, no wrong units)
- [ ] Speedup values use `×` symbol (not `x`)

---

## 6. Verbatim "Must Appear" Summary

Five sentences that must appear in the output document with equivalent unambiguous substance.
See `research.md §3` for full context and verification grep commands.

| Code | Section | Substance |
|------|---------|-----------|
| VC-001 | §6.5 | "CAEA codes MUST be obtained before the offline period begins. An invoice issued with a deferred CAE...is a legally invalid fiscal document." |
| VC-002 | §8.1 | "44% of operators report 'regular' (not good) connectivity quality (INTA/ENACOM 2021)" AND "Offline is the base operating mode, not a degraded fallback" |
| VC-003 | §10.3 | `SET LOCAL app.current_tenant_id = '{uuid}'` AND `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)` |
| VC-004 | §4.2 | "If the Rust `.so` extension fails to load at Django startup, the Python fallback activates automatically without operator intervention." |
| VC-005 | §6.3 | "`codGrano` is at the XML root — one WSLPG submission per grain type (ADR-019)" |

---

## 7. Done Criteria

The task is complete when ALL 12 items are satisfied:

- [ ] 1. File created at `Docs/Project Blueprint/High-Level Design (HLD).md`
- [ ] 2. §1 metadata: Version 1.0, Date 2026-03-17, Status Accepted, Owner GraviTea Architecture Team, Upstream Documents row
- [ ] 3. C4 Level 1 diagram renders — all 8 external actors visible with labeled protocol arrows
- [ ] 4. C4 Level 2 diagram renders — 5 containers with labeled protocol on every arrow
- [ ] 5. §5: all 8 apps present; `apps/facturacion` and `apps/liquidaciones` annotated "(Phase 2)"; no Phase 1 app is annotated
- [ ] 6. §6.5 CAEA legal constraint sentence present (VC-001)
- [ ] 7. §9.1 romaneo flow: exactly 10 steps in sequence; responsible component at every step
- [ ] 8. §8.4 conflict resolution table: all 5 strategies with target data types and implementation column
- [ ] 9. §4.4 Rust benchmark table: all 7 rows with × symbol and feature branch column
- [ ] 10. §13 technology cross-reference table covers all 8 ADR categories; every section §3–§12 maps to ≥1 ADR-NNN
- [ ] 11. Gate 5: zero hedging language; `grep -i "TBD\|TODO\|FIXME\|possibly\|might consider"` returns empty
- [ ] 12. All 7 Mermaid diagrams render without syntax errors (quickstart.md verification passes)
