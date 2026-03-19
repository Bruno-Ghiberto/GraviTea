# Spec 05: High-Level Design (HLD) -- Specification Context

## Feature Description

Create the `Docs/Project Blueprint/High-Level Design (HLD).md` document. This
document describes the **system architecture** of GRAVITEA ERP -- how components
fit together, what external integrations exist, data flows through the system,
and the deployment topology for both development and production environments.

The HLD is the document an architect reads before writing any code. It translates
the "what" of Vision (spec-01), PRD (spec-02), Data Model (spec-03), and ADR
(spec-04) into the "how the system is built" view. It is the required input for:
- spec-06 (REST API Design) -- API patterns derive from component boundaries
- spec-08a (ARCA Grain Integration Guide) -- ARCA architecture section is expanded here
- All implementation specs (09+) -- every implementation agent references this document
  to understand which layer their work lives in

This is a **Blueprint spec** (single-author document, no agent teams, no tmux).
The deliverable is a standalone Markdown document that a new engineer can read
without consulting any of specs 01-04 and understand the system's architecture.

## Current State (what exists)

No HLD document currently exists for the acopio vertical. Architecture is
currently documented across four sources that require synthesis:

- `Docs/Project Blueprint/Architecture Decision Records (ADR).md` -- 35 ADRs
  capturing individual decisions (the "why") but not the assembled system view (the "how")
- `Docs/Project Blueprint/PRD.md` -- Section 4 module specs and Section 5 offline
  architecture, written as functional requirements, not architecture diagrams
- `Docs/Project Blueprint/Data Model & Domain Model.md` -- ERD diagrams describing
  the database layer but not the container or component layers
- `CLAUDE.md` technology stack table -- lists technologies but not how they connect

The HLD must assemble all four sources into a single, diagram-driven architecture
document. It does not invent new decisions -- all decisions are captured in the ADRs.
It visualises those decisions as a coherent system.

## Research Inputs

### RAG Queries (run these FIRST -- do NOT read full research files)

Qdrant must be running before executing these queries:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -l 5
```

Required queries for this spec:

1. `"WSLPG SOAP endpoint authentication"`
   Target: WSDL URLs, service name, auth element structure, WSAA token expiry
2. `"ARCA grain services architecture"`
   Target: hub-and-spoke service map, per-service certificates, error paths
3. `"AI ML grain storage applications"`
   Target: 4-layer data strategy, model architectures, training data requirements
4. `"weighbridge RS-232 Modbus TCP protocol"`
   Target: baud rate, data format, KYASERV bridge, Sipel Orion Modbus memory map
5. `"offline sync conflict resolution grain ERP"`
   Target: store-and-forward queue, 5 conflict resolution strategies, CPE validity window
6. `"CPE carta de porte electronica lifecycle states"`
   Target: confirmarArribo, descargadoDestino, confirmacionDefinitiva, 5-day window
7. `"WSAA TRA authentication certificate token"`
   Target: TRA structure, CMS signing flow, token+sign pair, 12-hour expiry

### Source Documents (for reference -- prefer RAG results above)

These are the primary research documents for this spec. Only read specific
sections if RAG results are insufficient. **Do NOT read full files.**

| Doc ID | File Path | Relevant Sections |
|--------|-----------|-------------------|
| 5.1 | `Docs/Researches/Markdown/5.1 WSLPG -- Technical API Documentation.md` | §1 Service Endpoints and Authentication, §2 Complete SOAP Methods Catalog (LPG section) |
| 5.2 | `Docs/Researches/PDF/5.2 ARCA Grain Services Integration Architecture.pdf` | Full document (PDF-only, not in RAG -- read manually if needed for WSCPE architecture) |
| 9.1 | `Docs/Researches/Markdown/9.1 AI-ML Applications for Grain Storage Operations.md` | §Edge Computing for Offline AI, §Data collection strategy per layer |
| 10.1 | `Docs/Researches/Markdown/10.1 Existing Open-Source ARCA Grain Integration Code.md` | §Open-source reference implementations, §pyafipws patterns |
| 3.1 | `Docs/Researches/Markdown/3.1 Weighbridge Integration Standards.md` | §Communication Protocols, §Modbus RTU, §Ethernet/TCP-IP, §KYASERV |

### Critical Domain Facts

These facts are pre-extracted from upstream sources and MUST appear verbatim or
in substance in the HLD document. The author MUST NOT soften, qualify, or omit
any of these facts.

#### ARCA Integration Stack (ADR-025, ADR-026, ADR-027)

- **WSAA flow**: TRA (Ticket de Requerimiento de Acceso) + X.509 certificate → CMS
  (Cryptographic Message Syntax) signing → Base64 encoding → `LoginCMS` SOAP call →
  TA (Ticket de Acceso) containing `Token` + `Sign`. Tokens expire every **12 hours**.
- **WSLPG**: Electronic grain settlement filing (Form 1116-B/C). SOAP endpoints:
  production at `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl`;
  homologation (testing) at `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl`
  (requires pre-seeded ARCA test CUITs -- random CUITs will fail validation). Method
  `liquidacionAutorizar` returns a COE (Código de Operación Electrónico). WSLPG v1.24
  exposes 47+ methods. Each payload carries `codGrano` at the XML root -- one
  submission per grain type (ADR-019 constraint).
- **WSCPE**: CPE lifecycle management. Four lifecycle states at the WSCPE protocol
  level: **Activa** (issued by origin, valid for 5 days Automotor / 30 days Ferroviaria)
  → **Arribo** (confirmarArriboCPE) → **Descargada** (descargadoDestinoCPE) →
  **Confirmada_Definitiva** (confirmacionDefinitivaCPEAutomotor). "Vencida" (expired)
  is a derived condition, not a separate WSCPE state code — it applies when the
  current date exceeds the validity window of an active CPE. CPE validity window:
  **5 days from issuance** (Automotor). Expired CPEs produce legally invalid transport documents.
- **WSFEv1**: Standard invoice issuance (Comprobantes A/B/C). Returns CAE (Código
  de Autorización Electrónico). Per-invoice round-trip to ARCA required.
- **CAEA**: Código de Autorización Electrónico Anticipado. Pre-authorized batch codes
  for a **quincena** (15-day period). **CAEA codes MUST be obtained before the offline
  period begins**. An invoice issued with a deferred CAE (obtained after issuance)
  is a legally invalid fiscal document. CAEA batch builder implemented in Rust
  (feature 024, `serde_json`, GIL-released batch processing).
- Each ARCA service (WSLPG, WSCPE, WSFEv1) requires a **separate X.509 certificate
  registration**. A single shared certificate is rejected by ARCA.
- **SISA** (RG 5689/2025): Producer compliance registry replacing RUCA. Queried as
  a blocking gate before every WSLPG filing. Retention tiers by Estado:
  Estado 1 → IVA 5% / Ganancias 0%; Estado 2 → IVA 8% / Ganancias 2%;
  Estado 3 → IVA 10.5% / Ganancias 15%; Non-registered → IVA 16% / Ganancias 30%.

#### Weighbridge Protocol Stack (ADR-032, Research 3.1)

- **RS-232** is the universal baseline: all major Argentine indicator brands (Sipel,
  GaMa, Systel) include an RS-232 port as standard equipment.
  Serial parameters: 9600 baud, 8 data bits, No parity, 1 stop bit (8N1).
- **Primary protocol -- Sipel Orion**: Modbus RTU over RS-232. Supported functions:
  03h (Read Holding Registers), 06h (Write Single), 10h (Write Multiple).
  Memory map: Address 0 = Gross weight (2 registers, 32-bit signed int), Address 2 = Tare,
  Address 4 = Net weight, Address 6 = Flags/Status.
- **Primary protocol -- Systel** (Clipse, Croma, Bumer): Command/response ASCII
  over RS-232. No Modbus support -- polling-based ASCII frames.
- **Fallback**: Continuous ASCII stream parsing for GaMa A12 and similar indicators
  that do not support Modbus RTU.
- **Network bridge**: KYASERV RS232-to-Ethernet adapter converts full-duplex RS-232
  to UDP/TCP-IP over wired Ethernet, enabling the application server to communicate
  with the weighbridge over TCP/IP without requiring a direct serial connection to
  the weighbridge PC.
- Error path: RS-232 cable degradation and physical disconnects require a
  watchdog reconnection loop with operator alert on failed weight capture.

#### Offline-First Architecture (ADR-028, ADR-029, ADR-030)

- **Offline is the base, not the fallback.** 44% of operators report "regular"
  (not good) connectivity quality (INTA/ENACOM 2021). Every truck reception,
  quality analysis, silo assignment, and position query completes on the local
  device regardless of connectivity.
- **Five conflict resolution strategies by data type** (ADR-029):
  1. `server_wins` → Configuration data (tenant settings, tolerance tables, grain type definitions)
  2. `last_write_wins` → Inventory levels
  3. `additive` → Sales transactions / romaneo entries (never discard)
  4. `most_complete_wins` → Customer/producer data (merge; prefer more complete record)
  5. `server_assigns_final` → Document numbering (temporary offline IDs replaced at sync)
- **Store-and-forward queue** (`PendingOperation` entity): queues CPE lifecycle calls
  (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor) for
  deferred transmission. Queue is durable across device restarts.
- Fiscal invoice issuance uses CAEA (ADR-026), NOT store-and-forward, because ARCA
  requires authorization to precede issuance. Store-and-forward for CAE would produce
  legally invalid documents.

#### Security Architecture (ADR-021, ADR-022, ADR-005)

- **Three-layer defense-in-depth** (ADR-005):
  - Layer 1 (ORM): `TenantBoundManager` auto-filters all ORM queries by `tenant_id`
  - Layer 2 (DB): PostgreSQL RLS via `SET LOCAL app.current_tenant_id` (transaction-scoped)
  - Layer 3 (API): IDOR validation on every request using JWT claims (`iss`, `aud`, `exp`,
    `tenant_id`, `branch_id`)
- **JWT**: RS256 (RSA-PKCS1v15 + SHA-256, 4096-bit key). HS256 and HS512 are
  prohibited -- enforced via server-side algorithm whitelist. Access token: 15 minutes.
  Refresh token: 7 days.
- **Field encryption**: AES-256-GCM for PII (producer CUIT, names, addresses) via
  Python `cryptography` library. Master keys in Google Cloud Secret Manager.
  HMAC-SHA256 blind index for searchable encrypted fields (equality search only --
  range queries and LIKE patterns on encrypted fields are not supported).
- **Rust acceleration** on encryption hot path: AES-256-GCM 8.7× speedup,
  HMAC blind index 8.8× speedup (feature 018).

#### Rust/PyO3 Acceleration Boundary (ADR-031)

Criteria for moving computation to Rust (any one criterion triggers):
- Latency-sensitive hot path at >1,000 calls/second
- GIL contention in batch processing where Python threads cannot parallelize
- CPU-bound computation (cryptography, regex, merma calculations)
- Adversarial input validation requiring ReDoS protection

Benchmark table from feature branches 017-025:

| Module | Feature Branch | Speedup vs Python |
|--------|---------------|-------------------|
| AES-256-GCM encryption | 018-rust-crypto | 8.7× |
| HMAC blind index | 018-rust-crypto | 8.8× |
| IVA calculation | 019-rust-fiscal-compute | 4.4× |
| CUIT validation | 019-rust-fiscal-compute | 3.1× |
| Importes validation | 019-rust-fiscal-compute | 2.7× |
| Stock aggregation | 019-rust-fiscal-compute | 2.1× |
| Observability label sanitization | 021-rust-observability | 2.6× |

Python fallback is always present -- if the Rust `.so` module is unavailable, the
Python implementation runs without error or operator intervention.

#### AI/ML 4-Layer Data Strategy (ADR-033, ADR-034, ADR-035)

- **Layer 1 -- Operational**: All grain domain fields captured real-time with full
  timestamps. Every grain movement, quality parameter, and fiscal document stored
  verbatim with DECIMAL precision (no rounding at rest).
- **Layer 2 -- Behavioural**: `operator_id`, `laboratorista_id`, `device_id`, and
  6 named per-process timestamps per romaneo (`ts_entrada`, `ts_pesada_bruta`,
  `ts_calado`, `ts_analisis`, `ts_descarga`, `ts_tara`). Enables cycle-time analytics
  and operator performance baselines from day one.
- **Layer 3 -- Quality History**: `QualityAnalysis` rows accumulate per
  `(grain_type, campaign, storage_unit)`. Longitudinal quality record per silo
  enables quality degradation prediction (3D-CNN + LSTM, Phase 4).
- **Layer 4 -- Physical State (IoT-Ready)**: `StorageUnit.environment_sensor_id`
  as an IoT anchor FK. Populating this FK in a future phase requires no structural
  schema change.
- Qdrant vector database (optional container) for semantic search over operational
  data and RAG-based query expansion. Not required for Phase 1 or Phase 2.

#### Technology Stack (CLAUDE.md, ADR-001 through ADR-003)

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.14.3 |
| Framework | Django + DRF | 5.2.x |
| Database | PostgreSQL | 18.1 |
| Cache | Redis | 7.x |
| Performance | Rust + PyO3 | 1.93.1 + 0.28 |
| Auth | djangorestframework-simplejwt | Latest |
| Password | Argon2 (argon2-cffi) | Latest |
| Encryption | cryptography (AES-256-GCM) | Latest |
| Testing | pytest + pytest-django | Latest |
| Metrics | prometheus-client | Latest |
| Build (Rust) | Maturin | 1.12.4 |

## Functional Requirements

FR-0501: The HLD shall contain a C4 Level 1 system context diagram showing
GraviTea boundaries and all external actors: ARCA WSAA, ARCA WSLPG, ARCA WSCPE,
ARCA WSFEv1, weighbridge device, browser client, mobile client (future), and
operator PC.

FR-0502: The HLD shall contain a C4 Level 2 container diagram showing all major
containers (Django API, PostgreSQL, Redis, Rust extension .so, Qdrant optional)
and their communication protocols (HTTP/JSON, JDBC/SQL, TCP, Python FFI).

FR-0503: The HLD shall document the complete ARCA integration architecture including
the WSAA authentication flow (TRA → CMS → LoginCMS → TA), per-service certificate
management, token caching strategy, and CAEA offline mode.

FR-0504: The HLD shall document the weighbridge integration protocol stack in
three tiers: (1) Modbus RTU (Sipel Orion) and ASCII command/response (Systel),
(2) continuous ASCII stream fallback (GaMa A12), (3) KYASERV RS-232-to-Ethernet
bridge for LAN access -- per ADR-032.

FR-0505: The HLD shall document the offline-first sync architecture including the
store-and-forward queue mechanics, all 5 conflict resolution strategies with their
target data types, and CPE validity window constraints.

FR-0506: The HLD shall document the security architecture across all 3 isolation
layers (ORM TenantBoundManager, PostgreSQL RLS, IDOR/JWT validation) with a
defense-in-depth diagram showing how each layer operates independently.

FR-0507: The HLD shall document the Rust/PyO3 acceleration boundary including the
4 criteria for moving to Rust and the benchmark table (all 7 measured speedups from
feature branches 017-025).

FR-0508: The HLD shall include a step-by-step data flow diagram for the romaneo
reception flow covering all 10 steps: arrival → gross weigh → sampling → quality
analysis → merma calculation → grade assignment → unload → tare weigh → net
calculation → romaneo issuance.

FR-0509: The HLD shall include a data flow diagram for the fiscal authorization
flow covering both the CAE path (online, per-invoice round-trip) and the CAEA
path (offline, pre-authorized quincena batch).

FR-0510: The HLD shall document the AI/ML readiness 4-layer data architecture
(Operational, Behavioural, Quality History, Physical State/IoT) per ADR-033.

FR-0511: The HLD shall include a technology decisions cross-reference table linking
each HLD section to its corresponding ADR(s) from spec-04.

FR-0512: The HLD shall document the deployment topology for: (1) development
environment via Docker Compose and (2) production environment under the
single-server SMB constraint targeting small-to-medium acopiadores.

## Non-Functional Requirements

NF-0501: All diagrams MUST use text-based notation (Mermaid flowchart, sequenceDiagram,
or ASCII art). No binary image files. Every diagram must be renderable in standard
Markdown viewers that support Mermaid.

NF-0502: Every architecture section MUST cross-reference the relevant ADR(s) from
spec-04 using the exact format "ADR-NNN" with the ADR title in parentheses.

NF-0503: Zero hedging language. The document MUST NOT contain the words "TBD",
"TODO", "FIXME", "possibly", or "might consider". Every section is either fully
specified or explicitly deferred to a named future spec.

NF-0504: Document metadata: version 1.0, date 2026-03-17, status Accepted,
owner GraviTea Architecture Team. Same metadata format as the ADR document.

NF-0505: All integration flows MUST include error paths (e.g., WSAA token expiry
during a batch filing, weighbridge RS-232 cable disconnect mid-reception, CPE
validity window expiry during extended offline period).

NF-0506: All protocol choices MUST include their rationale tracing back to the
specific ADR that made the decision. The HLD does not invent new rationale --
it cites the ADR.

NF-0507: The document MUST be self-contained. A new engineer reading only this
document (without specs 01-04) must be able to understand: (a) what external
systems the product integrates with, (b) what containers compose the system,
(c) how data flows through the romaneo and fiscal workflows, and (d) what
architectural constraints apply.

## Target Document Structure

```
1. Document Metadata
   (version, date, owner, status, upstream references)

2. System Overview
   2.1 What This Document Is
   2.2 What This Document Is Not (scope exclusions)
   2.3 How to Read This Document (diagram notation, ADR cross-ref convention)

3. System Context (C4 Level 1)
   3.1 Context Diagram (Mermaid)
   3.2 External Actor Descriptions
       - ARCA WSAA (authentication gateway)
       - ARCA WSLPG (grain settlement)
       - ARCA WSCPE (CPE lifecycle)
       - ARCA WSFEv1 (invoicing)
       - Weighbridge device (RS-232/Modbus/TCP)
       - Browser client
       - Mobile client (Phase 3+ target)
       - Operator PC (local device running offline-first client)
   3.3 System Boundary Definition

4. Container Architecture (C4 Level 2)
   4.1 Container Diagram (Mermaid)
   4.2 Container Descriptions
       - Django API (Python 3.14.3 + Django 5.2.x + DRF; WSGI + Gunicorn)
       - PostgreSQL 18.1 (primary datastore; RLS enforcement)
       - Redis 7.x (session cache, rate limiter, Celery broker)
       - Rust Extension .so (PyO3 0.28; loaded at Django startup via Maturin)
       - Qdrant (optional; vector search for AI/ML layer)
   4.3 Communication Matrix (container × container, protocol, direction)

5. Component Overview by Django App
   5.1 apps/core (Tenant, Branch, TenantBoundManager, RLS middleware,
       AES-256-GCM encryption, Prometheus observability, SSRF validation)
   5.2 apps/auth (JWT RS256, Argon2, rate limiting, token lifecycle)
   5.3 apps/acopio (Romaneo, QualityAnalysis, MermaCalculation, CPE,
       StorageUnit, GrainLot, GrainMovement, CampanaConfig)
   5.4 apps/cuentas (ProducerAccount, AccountMovement, FijacionRecord)
   5.5 apps/facturacion (Comprobante, CAEA, ArcaCredential, PuntoDeVenta,
       WSAA client, WSFEv1 client)
   5.6 apps/liquidaciones (LiquidacionPrimaria, WSLPG client, SISA gate)
   5.7 apps/sync (SyncSession, PendingOperation, conflict resolution engine)
   5.8 apps/core/observability (Prometheus metrics, OpenTelemetry tracing,
       Rust-accelerated label sanitization)

6. ARCA Integration Architecture
   6.1 Architecture Overview (hub-and-spoke diagram: WSAA → WSLPG + WSCPE + WSFEv1)
   6.2 WSAA Authentication Flow
       - TRA generation (XML with service name, generation/expiry timestamps)
       - X.509 certificate signing (CMS envelope, Base64 encoding)
       - LoginCMS SOAP invocation
       - TA receipt (Token + Sign pair, 12-hour expiry)
       - Token caching strategy (Redis; concurrent refresh race prevention)
   6.3 WSLPG Integration
       - Service name: "wslpg"; homologation + production WSDL URLs
       - liquidacionAutorizar method → COE
       - Single-grain-type constraint (ADR-019): one XML payload per codGrano
       - Campaign code conversion ("2024/25" → "2425" for WSLPG campania field)
       - SISA blocking gate (ADR-027): query before every filing; four retention tiers
   6.4 WSCPE Integration
       - CPE lifecycle state machine (4 WSCPE-level states, 3 confirmation calls)
       - 5-day validity window; queued confirmation via store-and-forward
   6.5 WSFEv1 Integration
       - CAE flow (online, per-invoice authorization)
       - CAEA flow (offline, pre-authorized quincena batch)
       - Rust CAEA batch builder (feature 024)
   6.6 Certificate Management
       - Separate certificate per service
       - Google Cloud Secret Manager for private keys
       - Certificate rotation procedure
   6.7 Error Paths
       - WSAA timeout → token refresh retry with exponential backoff
       - Token expiry mid-batch → re-authenticate and resume
       - WSLPG rejection (schema error, SISA block) → user-facing error message
       - CPE validity window expiry → operator alert; no automatic extension

7. Weighbridge Integration Architecture
   7.1 Protocol Stack (3-tier diagram)
   7.2 Tier 1: Primary Protocols
       - Sipel Orion: Modbus RTU over RS-232 (memory map: addresses 0/2/4/6)
       - Systel (Clipse, Croma, Bumer): ASCII command/response over RS-232
   7.3 Tier 2: Fallback Protocol
       - GaMa A12: Continuous ASCII stream parsing
       - Frame format: {STX}{weight}{CR/LF} at 9600 baud, 8N1
   7.4 Tier 3: Network Bridge
       - KYASERV RS232-to-Ethernet adapter (RS-232 → UDP/TCP-IP over LAN)
       - Application server communicates over TCP to KYASERV IP:port
       - Eliminates requirement for application server to be the weighbridge PC
   7.5 WeighbridgeDevice Entity
       - First-class entity with interface_type, connection_address, calibration records
       - Romaneo.weighbridge_device_id (nullable FK, SET_NULL on decommission)
   7.6 Error Paths
       - RS-232 cable disconnect: watchdog reconnection loop; operator alert
       - Stable-weight timeout: configurable threshold; manual entry override
       - KYASERV network unreachable: fall back to manual entry mode

8. Offline-First Architecture
   8.1 Architecture Principle (ADR-028)
       - 44% of operators report "regular" connectivity (INTA/ENACOM 2021)
       - Offline is the base operating mode, not a degraded fallback
   8.2 Local Data Store
       - All core operations write to local SQLite (client device) or
         to the on-premises PostgreSQL instance (plant server deployment)
       - UUID v4 IDs generated locally (ADR-002) prevent collision at sync
   8.3 Sync Protocol
       - Push/pull idempotent sync; vector clock timestamps per entity
       - SyncSession tracks last-sync watermark per device per entity type
   8.4 Conflict Resolution Engine (ADR-029)
       - Five strategies: server_wins / last_write_wins / additive /
         most_complete_wins / server_assigns_final
       - Rust `most_complete_wins` merge implementation (feature 023, GIL-released)
   8.5 Store-and-Forward Queue (ADR-030)
       - PendingOperation entity: operation_type, payload, status, retry_count
       - Durable across device restarts; transmitted in FIFO order on reconnect
       - Queues: confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor
       - NOT used for fiscal invoice issuance (CAEA handles that path)
   8.6 CAEA Offline Fiscal Path (ADR-026)
       - CAEA quincena codes obtained before the offline period begins
       - Invoices issued offline using pre-authorized CAEA codes are legally valid
       - If CAEA codes not obtained before connectivity loss: offline invoicing blocked
   8.7 Error Paths
       - CPE validity window expiry (5 days) during extended outage → operator alert
       - CAEA quincena expiry during extended outage → invoicing blocked; no workaround
       - Sync merge conflict requiring manual resolution → conflict escalation queue

9. Data Flow Diagrams
   9.1 Romaneo Reception Flow (10 steps)
       Steps: Arrival → Gross Weigh (weighbridge) → Sampling (calado) →
       Quality Analysis (lab) → Merma Calculation (Rust merma engine) →
       Grade Assignment → Unload → Tare Weigh (weighbridge) →
       Net Weight Calculation → Romaneo Issuance (boleta + silo credit +
       account credit)
   9.2 Fiscal Authorization Flow
       CAE path: Invoice draft → WSFEv1 authorize → CAE received → invoice confirmed
       CAEA path: CAEA batch obtained (before quincena) → Invoice draft →
       CAEA code assigned → invoice confirmed (no ARCA round-trip at issuance time)
   9.3 Sync Flow (abbreviated)
       Local write → SyncSession queue → connectivity check → batch push →
       conflict resolution → server-side merge → pull delta → local apply

10. Security Architecture
    10.1 Defense-in-Depth Diagram (3 layers)
    10.2 Layer 1: ORM (TenantBoundManager)
         - Auto-filter: all manager queries prepend WHERE tenant_id = ?
         - Custom manager on every tenant-scoped model
    10.3 Layer 2: PostgreSQL RLS
         - Session variable: SET LOCAL app.current_tenant_id = '{uuid}'
         - Policy: USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
         - Applied on all per-tenant tables; global tables (GrainType,
           ToleranceTable) exempt (ADR-010)
    10.4 Layer 3: IDOR Validation
         - JWT RS256 claims checked on every request: iss, aud, exp,
           tenant_id, branch_id
         - Algorithm whitelist: RS256 only; HS256 / none rejected at middleware
    10.5 Field-Level Encryption
         - AES-256-GCM for PII; HMAC-SHA256 blind index for searchable fields
         - Encrypted: producer CUIT, full name, address, DNI, contact data
         - Limitation: blind index supports equality search only (no range, no LIKE)
    10.6 Key Management
         - Master encryption key: Google Cloud Secret Manager
         - JWT private key (4096-bit RSA): Google Cloud Secret Manager
         - ARCA X.509 private keys: Google Cloud Secret Manager
         - Never in code, environment variables, Docker configs, or git history

11. Deployment Topology
    11.1 Development Environment (Docker Compose)
         - Services: django-api, postgres, redis, rust-builder (Maturin build stage)
         - Qdrant: optional; disabled by default in dev
         - Ports: 8000 (Django), 5432 (PostgreSQL), 6379 (Redis)
         - Rust modules: built in multi-stage Docker build (rust-builder stage)
         - Local weighbridge: simulated via mock serial device in dev
    11.2 Production Topology (Single-Server SMB Constraint)
         - Target: small-to-medium acopiadores with 1-5 plants
         - Typical hardware: 1 on-premises plant server (Windows or Linux PC)
           plus cloud API server
         - Options: (a) full cloud deployment (Django + PostgreSQL on GCP Cloud
           Run + Cloud SQL Enterprise Plus); (b) hybrid (plant server runs
           offline client + local PostgreSQL; cloud server handles sync and ARCA)
         - Deployment unit: single Django process; modular monolith (ADR-003)
         - No microservices; no service mesh; no Kubernetes for initial scale
    11.3 Production Topology Diagram (Mermaid)
    11.4 Infrastructure Cost Rationale (ADR-004)
         - Shared schema: fixed DB cost regardless of tenant count
         - Single-server deployment: compatible with SMB USD 90-360/month SaaS budget

12. AI/ML Readiness Architecture
    12.1 4-Layer Data Strategy Overview (ADR-033)
    12.2 Layer 1 -- Operational Data
         - All grain domain fields captured real-time with full timestamps
         - DECIMAL(17,3) precision; no rounding at rest (ADR-007)
    12.3 Layer 2 -- Behavioural Data
         - 6 named timestamps per romaneo (ts_entrada through ts_tara)
         - operator_id, laboratorista_id, device_id on all grain domain models
    12.4 Layer 3 -- Quality History
         - QualityAnalysis.analysis_timestamp enables temporal quality series
         - Longitudinal per-silo quality record for degradation prediction
    12.5 Layer 4 -- Physical State (IoT-Ready)
         - StorageUnit.environment_sensor_id (nullable FK anchor)
         - No structural change required when IoT sensors are integrated
    12.6 Phase 4 ML Capabilities (reference only -- not in scope for HLD)
         - Quality degradation prediction: 3D-CNN + LSTM (97.38% accuracy target)
         - Silo assignment optimization: MILP (27% queue time reduction target)
         - Price forecasting: VMD-SGMD-LSTM (Matba Rofex) + XGBoost (pizarra basis)
         - Weighbridge fraud detection: anomaly detection on weight patterns
    12.7 Qdrant Container (optional)
         - Semantic vector search over operational data
         - Used in development for RAG-based query expansion
         - Production: optional; not required for Phase 1 or Phase 2

13. Technology Decisions Cross-Reference Table
    (Full table: HLD section → ADR IDs → ADR titles → decision category)
    Categories: Infrastructure, Data Architecture, Security, Grain Domain,
    Fiscal Integration, Offline & Sync, Performance, AI/ML Readiness
```

## Acceptance Criteria

AC-0501: C4 Level 1 context diagram (Mermaid) renders correctly and shows all
9 external actors: GraviTea system boundary, browser client, mobile client (future),
ARCA WSAA, ARCA WSLPG, ARCA WSCPE, ARCA WSFEv1, weighbridge device, operator PC.

AC-0502: C4 Level 2 container diagram (Mermaid) shows all 5 containers: Django API,
PostgreSQL, Redis, Rust extension (.so), Qdrant (optional), with labeled communication
protocols on each connection arrow.

AC-0503: ARCA section 6.5 explicitly states: "CAEA codes MUST be obtained before
the offline period begins. An invoice issued with a deferred CAE (authorization
obtained after issuance) is a legally invalid fiscal document." This sentence must
appear verbatim or in equivalent substance.

AC-0504: Romaneo reception data flow (section 9.1) covers all 10 steps in sequence:
arrival → gross weigh → sampling → quality analysis → merma calculation →
grade assignment → unload → tare weigh → net calculation → romaneo issuance.
Each step identifies the component responsible (weighbridge driver, Rust merma engine,
WSCPE client, etc.).

AC-0505: Conflict resolution section 8.4 lists all 5 strategies with their mapped
data types: server_wins (configuration), last_write_wins (inventory), additive
(transactions/romaneos), most_complete_wins (producer data), server_assigns_final
(document numbering).

AC-0506: Security section 10.1 shows a defense-in-depth diagram rendering correctly
in Mermaid, with 3 distinct layers labeled: Layer 1 ORM, Layer 2 RLS, Layer 3 IDOR.
Each layer includes the specific enforcement mechanism.

AC-0507: The section covering the Rust/PyO3 acceleration boundary (ADR-031) includes
the complete benchmark table with all 7 measured speedups from the Critical Domain
Facts section above, with feature branch references (018-rust-crypto through
021-rust-observability). This section must exist as a named heading in the output
document, cross-referenced from the container architecture section (section 4).

AC-0508: Technology cross-reference table (section 13) covers all 8 ADR categories
(Infrastructure through AI/ML Readiness) with at least one ADR ID per HLD section
that makes decisions in that category. Every ADR-NNN reference uses the exact ID
format matching the ADR document.

AC-0509: No "TBD", "TODO", "FIXME", "possibly", or "might consider" in the
deliverable document. A grep command against the output file must return 0 matches
for these terms.

AC-0510: The document is navigable: every section in the Target Document Structure
above exists in the output with an H2 or H3 heading. Internal Markdown anchor
links from the table of contents resolve to the correct sections.

AC-0511: Error paths are documented for WSAA authentication (section 6.7),
weighbridge integration (section 7.6), CPE validity window (section 8.7), and
CAEA quincena expiry (section 8.7). Each error path identifies the failure mode,
the system response, and whether operator intervention is required.

AC-0512: Deployment topology section (section 11) documents both environments:
(a) development environment via Docker Compose listing all services with their
exposed ports and the Rust multi-stage build; (b) production environment under
the single-server SMB constraint, covering the two topology options (full cloud
and hybrid plant/cloud). A Mermaid diagram (section 11.3) renders correctly
showing the production topology.

## Dependencies

### Depends On (must be complete before this spec runs)

- **spec-03**: `Docs/Project Blueprint/Data Model & Domain Model.md` v1.0 -- entity
  list (section 3), RLS approach (section 4.9 via Ironclad P2), and Ironclad
  Principles P1-P5. The HLD component descriptions derive from the Data Model ERD.
- **spec-04**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md` v1.0 --
  all 35 ADRs. Every HLD section cites specific ADRs. The ADR document is the
  authority for all architectural choices; the HLD is their visualisation.

### Blocks (must complete before these specs run)

- **spec-06**: REST API Design -- API endpoint patterns, versioning, and authentication
  flows are constrained by the container architecture and security layers documented here.
- **spec-08a**: ARCA Grain Integration Guide -- the ARCA integration architecture
  section (section 6) is the architectural overview that spec-08a expands into a
  complete technical integration guide with SOAP examples.
- **spec-09 through spec-12** (all implementation specs): Every implementation agent
  references the HLD to understand which app/container/layer their work lives in
  and what external service constraints apply.

### Peer References (informational, no ordering constraint)

- **spec-07**: Roadmap -- references Phase 1/2/3/4 phasing described in Vision and
  partially illustrated by the deployment topology here.
- **spec-08b**: AI/ML Feature Roadmap -- expands section 12 of this document.
