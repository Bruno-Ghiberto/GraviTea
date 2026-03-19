# spec-08: New Blueprint Documents — Specify Context Prompt

## Feature Description

Produce **three** new blueprint documents that complete the GraviTea Acopio ERP blueprint suite
before implementation specs (09-12) begin:

| Sub-spec | Deliverable | Purpose |
|----------|-------------|---------|
| **08a** | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | Developer reference for implementing ARCA grain web services (WSAA, WSLPG, WSCPE, WSFEv1). Bridges the architectural overview in HLD §6 with actionable SOAP endpoint details, XML schema summaries, certificate management, error handling, and testing against the ARCA homologation environment. |
| **08b** | `Docs/Project Blueprint/AI-ML Feature Roadmap.md` | Detailed AI/ML feature plan expanding HLD §12 and Roadmap §7. Covers data readiness requirements, ML model candidates, feature engineering strategy, training data collection during Phases 1-2, and Phase 3 delivery sequence. |
| **08c** | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | Formal requirements specification derived from the PRD (spec-02). Transforms product-level user stories into engineering-level shall-statements with unique requirement IDs, priority classification, traceability to implementation specs (09-12), and detailed interface specifications (hardware, ARCA SOAP, REST API). |

These three documents are the last blueprint-tier artifacts before the implementation wave begins.
Together they provide: the ARCA integration playbook for spec-10/14 developers (08a), the ML
data strategy that justifies ADR-033/034/035 schema decisions (08b), and the formal requirements
traceability matrix that links PRD user stories to implementation specs (08c).

---

## Current State

**08a and 08b**: No existing versions.

**08c**: A stale SRS exists at `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
(dated 2026-03-01). It was written for the **old general-purpose ERP vertical** (ferreterías,
corralones, retail PyMEs) and is **not applicable** to the acopio de granos vertical. Spec-08c
is a **complete rewrite** of this document — not an update. The stale file will be overwritten.

The content for all three documents is currently distributed across upstream blueprints:

| Source | Content that moves into spec-08 deliverables |
|--------|----------------------------------------------|
| HLD §6 (ARCA Integration Architecture) | Architecture-level overview of WSAA, WSLPG, WSCPE, WSFEv1 → expanded into 08a with endpoint details, XML schemas, error codes, testing strategy |
| HLD §12 (AI/ML Readiness Architecture) | 4-layer data strategy overview → expanded into 08b with ML model architecture, feature engineering, training pipeline |
| PRD §4 (Module Specifications) | Product-level feature lists → formalized into 08c shall-statements with requirement IDs |
| PRD §6 (Regulatory Compliance) | ARCA compliance rules → referenced by 08a as integration constraints |
| PRD §7 (Hardware Integration) | Weighbridge overview → 08c adds baud rates, frame formats, protocol-specific details |
| PRD §8 (Non-Functional Requirements) | Performance/security targets → 08c formalizes into measurable requirements |
| ADR v1.0 (ADR-019, 025-030, 033-035) | Architectural constraints → 08a cites ARCA ADRs; 08b cites AI ADRs |
| REST API Design v1.0 | Phase 1 endpoint definitions → 08c traces requirements to API paths |
| Roadmap §5-§7 | Phase delivery plan → 08a/08b/08c all reference phase timelines |

The `specs/008-acopio-new-docs/` directory does not yet exist and will be created by
`/speckit.specify`.

---

## Research Inputs

### RAG Queries (run these FIRST — do NOT read full files)

```bash
# --- 08a: ARCA Grain Integration Guide ---

# WSAA authentication TRA flow, token lifecycle
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "WSAA authentication TRA LoginCMS Token Sign certificate X509" -l 5

# WSLPG grain settlement liquidacion primaria Form 1116 fields
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "WSLPG liquidacion primaria granos Form 1116 B C XML fields codGrano" -l 5

# WSCPE Carta de Porte Electronica lifecycle confirmation methods
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "WSCPE Carta de Porte CPE lifecycle confirmarArribo descargado confirmacion CTG" -l 5

# CAEA offline fiscal codes quincena batch
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "CAEA quincena offline fiscal authorization anticipado invoice" -l 5

# Open-source ARCA grain integration code reference implementations
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "open source ARCA grain integration code Python pyafipws WSLPG" -l 5

# ARCA homologacion testing environment CUIT certificates
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "ARCA homologacion testing environment test CUIT certificates" -l 5

# SISA retention calculation RG 5689 withholding tiers
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "SISA retention withholding tier Estado IVA Ganancias RG 5689" -l 5

# --- 08b: AI/ML Feature Roadmap ---

# AI ML applications for grain storage operations
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "AI ML applications grain storage operations predictive quality merma" -l 5

# Grain quality degradation prediction model
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "grain quality degradation prediction LSTM silo temperature humidity" -l 5

# Weighbridge fraud detection anomaly patterns
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "weighbridge fraud detection anomalous weight pattern behavioural baseline" -l 5

# --- 08c: SRS ---

# Romaneo workflow steps end-to-end for interface requirements
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo workflow steps truck arrival weighing quality grading" -l 5

# Weighbridge RS-232 Modbus protocol baud rate frame format
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "weighbridge RS-232 Modbus protocol baud rate frame format parity" -l 5

# Grain quality parameters tolerance tables bonificacion rebaja
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "grain quality parameters humidity tolerance base bonificacion rebaja" -l 5
```

### Source Documents (for reference only — prefer RAG)

| ID | Path | Relevant sections | For sub-spec |
|----|------|-------------------|-------------|
| 1.1 | `Docs/Researches/Markdown/1.1 Carta de Porte Electronica (CTG) -- Complete Lifecycle.md` | CPE lifecycle states, CTG codes, validity windows | 08a |
| 1.2 | `Docs/Researches/Markdown/1.2 AFIP Web Service WSCPE -- Technical Specification.md` | WSCPE SOAP methods, XML schemas, error codes | 08a |
| 1.3 | `Docs/Researches/Markdown/1.3 Liquidacion Primaria de Granos -- Form 1116 B and C.md` | Form 1116-B/C field structure, codGrano constraint | 08a |
| 1.4 | `Docs/Researches/Markdown/1.4 Registro de Operadores de Granos and Withholding Tax Regime.md` | SISA registry, withholding tiers | 08a |
| 5.1 | `Docs/Researches/Markdown/5.1 WSLPG -- Technical API Documentation.md` | WSLPG SOAP endpoints, XML field types, response codes | 08a |
| 10.1 | `Docs/Researches/Markdown/10.1 Existing Open-Source ARCA Grain Integration Code.md` | pyafipws reference implementations, Python SOAP patterns | 08a |
| 9.1 | `Docs/Researches/Markdown/9.1 AI-ML Applications for Grain Storage Operations.md` | Full AI roadmap, model candidates, data requirements | 08b |
| 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | Romaneo workflow for SRS interface specs | 08c |
| 2.2 | `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md` | Quality params, tolerance tables | 08c |
| 3.1 | `Docs/Researches/Markdown/3.1 Weighbridge Integration Standards.md` | RS-232, Modbus, baud rates, protocols | 08c |
| 3.2 | `Docs/Researches/Markdown/3.2 Grain Moisture Meters and Lab Equipment.md` | Lab equipment APIs | 08c |
| 8.3 | `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md` | Romaneo field spec | 08c |

### Critical Domain Facts (inlined — minimum context)

**ARCA Architecture (for 08a):**
- ARCA (Administracion de Ingresos Publicos, formerly AFIP) provides 4 SOAP web services
- Hub-and-spoke: WSAA is the authentication gateway for WSLPG, WSCPE, WSFEv1
- WSAA flow: TRA XML generation -> X.509 certificate signing -> CMS envelope -> Base64 -> LoginCMS -> Token+Sign (TA)
- Token+Sign lifetime = 12 hours; Redis cache TTL = 11 hours (1-hour safety margin)
- Each ARCA service requires a **separate** X.509 certificate — shared certificates rejected
- Private keys stored in Google Cloud Secret Manager exclusively (never in code, .env, or Docker)

**WSLPG (for 08a):**
- Grain settlement filing: `liquidacionAutorizar` -> COE (Codigo de Operacion Electronico)
- Production: `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl`
- Homologation: `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl`
- Single grain type per submission (codGrano at XML root) — ADR-019
- SISA blocking gate: must query producer SISA status before every filing (ADR-027)
- Retention tiers: Estado 1 (5% IVA / 0% Ganancias), Estado 2 (8% / 2%), Estado 3 (10.5% / 15%), Non-registered (16% / 30%)

**WSCPE (for 08a):**
- CPE lifecycle: Activa -> Arribo -> Descargada -> Confirmada_Definitiva
- Core methods (from HLD §6.4): `confirmarArriboCPE`, `descargadoDestinoCPE`, `confirmacionDefinitivaCPEAutomotor`
- **DISCREPANCY**: Research 1.2 (ARCA WSDL) lists `confirmarDescargaCPE` instead of `descargadoDestinoCPE` — 08a MUST resolve this against the actual ARCA WSDL
- Additional WSCPE methods from research 1.2 NOT in HLD: `solicitarCPEAutomotor`, `consultarCPEAutomotor`, `anularCPE`, `rechazoCPE`, `consultarRenspa` — 08a MUST document the full method catalog
- CPE Automotor validity window: 5 days from issuance
- Offline: WSCPE calls queued in PendingOperation store-and-forward (ADR-030)
- "Vencida" is a derived condition (elapsed time), not a WSCPE state code

**Weighbridge hardware (for 08c — from RAG Q12, research 3.1):**
- RS-232 serial parameters: 9600 bps default (1200-38400 configurable), 8 data bits, no parity, 1 stop bit, DB-9 male, 15m max
- Modbus RTU (Sipel Orion): functions 03h (Read Holding Registers), 06h (Write Single Register), 10h (Write Multiple Registers); RS-232 single-slave or RS-485 multi-slave (1200m max)
- ASCII stream fallback: frame delimiters STX/ETX or CR/LF (GaMa A12, Sipel FI=0)
- KYASERV RS-232-to-Ethernet bridge: TCP/IP LAN access for remote ERP connection

**WSFEv1/CAEA (for 08a):**
- Online: `FECAESolicitar` -> CAE per invoice
- Offline: CAEA (Codigo de Autorizacion Electronico Anticipado) quincena batch codes
- CAEA MUST be obtained BEFORE the offline period — no retroactive authorization
- Rust CAEA batch builder: feature 024-rust-arca-batch (serde_json, GIL-released)
- CAEA quincena codes cannot roll over; legal constraint is strict

**AI/ML Data Architecture (for 08b):**
- ADR-033: 4-layer data strategy captured from day one of production
  - Layer 1 — Operational Data: all grain fields in real-time, DECIMAL(17,3) precision
  - Layer 2 — Behavioural Data: operator_id, laboratorista_id, device_id + 6 named timestamps per romaneo
  - Layer 3 — Quality History: QualityAnalysis per (grain_type, campaign, storage_unit) — longitudinal
  - Layer 4 — Physical State (IoT-Ready): StorageUnit.environment_sensor_id nullable FK anchor
- Phase 3 ML capabilities per Roadmap §7.1 priorities:
  - P3-Q1: Predictive merma modelling (highest ROI — regression on tabular data)
  - P3-Q2: Price optimisation signals (MAT feed + AccountMovement history)
  - P3-Q3: Storage condition anomaly detection (IoT sensor readings — Layer 4)
  - P3-Q4: Natural language grain position queries (LLM -> SQL: "¿Cuánta soja tengo hoy?")
  - Deferred: Computer vision grain grading (requires camera hardware partnership — beyond Phase 3)
- HLD §12.6 also lists (informative): silo assignment optimization, weighbridge fraud detection — these may be added during Phase 3 planning
- ADR-034: provenance fields on all grain domain models (created_by, device_id)
- ADR-035: 6 named timestamps on Romaneo (ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara)
- Qdrant optional container for development RAG; not required in production (Phase 1-2)

**Phase model alignment (for 08b — IMPORTANT):**
- The **Roadmap v1.0** (authoritative) uses a **3-phase model**: Phase 1 (MVP), Phase 2 (Advanced), Phase 3 (Intelligence & Scale)
- The **PRD** and **HLD** use a **4-phase model** where Phase 3 = CANJE + AGRONOMIA + OCR and Phase 4 = AI/ML
- The Roadmap consolidated PRD Phase 3 + Phase 4 into Roadmap Phase 2 + Phase 3 respectively
- **08b MUST use the Roadmap's 3-phase model** — ML features are "Phase 3", not "Phase 4"
- Phase 3 triggers from Roadmap §7.4: (1) >= 20 paying customers, (2) >= 10,000 romaneos processed, (3) AI data pipeline review completed

**Open-source ARCA libraries (for 08a — from RAG Q05, research 10.1/5.1):**
- `pyafipws` (reingart/pyafipws on GitHub): main open-source Python library for all ARCA services; includes `wslpg.py` for grain liquidation
- `py3afipws` on PyPI: Python 3 fork of pyafipws
- `django-afip` (WhyNotHugo/django-afip): Django-specific AFIP/ARCA integration for invoicing (WSFEv1 focused)
- `afip.py` / Afip SDK (afipsdk.com): commercial alternative with simpler API wrapping WSLPG
- SistemasAgiles wiki: community documentation for LiquidacionPrimariaGranos implementation

**SRS Context (for 08c):**
- PRD §4 defines 8 modules: RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES, LIQUIDACIONES, FACTURACION, AGRONOMIA, CANJE
- PRD §7 defers hardware details to SRS: baud rates, frame formats, parity settings, protocol details
- PRD §8: online performance <500ms API response; offline sync <30s push/pull; romaneo <5 min end-to-end
- Three-tier weighbridge protocol: Modbus RTU (Sipel Orion), continuous ASCII (GaMa A12), TCP/IP via KYASERV bridge (ADR-032)
- Phase 1 modules: RECEPCION + CALIDAD + ALMACENAMIENTO + CUENTAS CORRIENTES (specs 09-12)
- Phase 2 modules: LIQUIDACIONES + FACTURACION + AGRONOMIA + CANJE (specs 13-16 per Roadmap)

---

## Functional Requirements

### Sub-Deliverable A: ARCA Grain Integration Guide

**FR-08A01 — WSAA authentication flow**
The guide MUST document the complete WSAA authentication flow (TRA generation -> X.509 signing -> CMS creation -> LoginCMS -> Token+Sign) with a sequence diagram, all parameter names, token lifetime, and Redis caching strategy.

**FR-08A02 — WSLPG integration reference**
The guide MUST document the WSLPG `liquidacionAutorizar` method: required XML fields, the codGrano single-grain-type constraint (ADR-019), the SISA blocking gate (ADR-027), response parsing, COE extraction, and error codes.

**FR-08A03 — WSCPE lifecycle reference**
The guide MUST document the WSCPE CPE lifecycle (Activa -> Arribo -> Descargada -> Confirmada_Definitiva): each method call, required parameters, the 5-day Automotor validity window, and offline store-and-forward behavior (ADR-030).

**FR-08A04 — WSFEv1/CAEA reference**
The guide MUST document both WSFEv1 authorization paths: CAE (online per-invoice) and CAEA (offline quincena batch). The CAEA legal constraint ("must obtain before offline period") MUST be highlighted with a warning callout.

**FR-08A05 — Certificate management**
The guide MUST document per-service certificate management: separate X.509 certs per service, private key storage in Secret Manager, certificate rotation procedure, and certificate expiry error handling.

**FR-08A06 — Homologation testing**
The guide MUST include a section on ARCA homologation environment testing: URLs for each service (production vs homologation), pre-seeded test CUITs, known homologation quirks, and a testing checklist. **Note**: The HLD only lists WSLPG URLs. WSCPE and WSFEv1 production/homologation URLs MUST be researched from ARCA documentation and research docs 1.2 and 5.1.

**FR-08A07 — Error handling reference**
The guide MUST include a consolidated error handling table covering all four ARCA services: failure modes, system responses, retry strategies, and operator actions required (matching HLD §6.7 and expanding it).

**FR-08A08 — Open-source reference implementations**
The guide MUST reference pyafipws and other open-source ARCA grain integration code (from research 10.1) as implementation reference material, with caveats on what is directly usable vs what needs adaptation.

**FR-08A09 — ADR cross-references**
The guide MUST cite all ARCA-related ADRs and explain how each constraint affects implementation: ADR-019 (Single Form 1116-C per Grain Type), ADR-025 (ARCA Web Service Architecture), ADR-026 (CAEA for Offline Fiscal Operations), ADR-027 (SISA-Tier Retention Calculation), ADR-028 (Offline-First as Base Architecture), ADR-029 (Conflict Resolution Taxonomy — affects store-and-forward queue ordering), ADR-030 (Store-and-Forward Queue for ARCA Web Service Calls).

### Sub-Deliverable B: AI/ML Feature Roadmap

**FR-08B01 — 4-layer data strategy documentation**
The document MUST describe the 4-layer data architecture (ADR-033) with concrete field references from the Data Model spec-03 for each layer, explaining what training data is captured and why.

**FR-08B02 — ML model candidates catalog**
The document MUST catalog all Phase 3 ML model candidates using the Roadmap §7.1 priority order as the authoritative sequence: (P3-Q1) predictive merma modelling, (P3-Q2) price optimisation signals, (P3-Q3) storage condition anomaly detection, (P3-Q4) natural language grain position queries (NLQ). Additionally, it MUST include HLD §12.6 informative candidates (silo assignment optimisation, weighbridge fraud detection) and the deferred computer vision grain grading. Each candidate MUST have: description, input features, target variable, minimum training data requirements, and estimated data accumulation timeline.

**FR-08B03 — Feature engineering strategy**
The document MUST describe the feature engineering approach for each ML model: which raw fields become features, transformation logic, temporal aggregation windows, and cross-entity feature joins.

**FR-08B04 — Training data collection plan**
The document MUST specify what data must be collected during Phases 1-2 to enable Phase 3 ML, including minimum romaneo count (>= 10,000 per Roadmap §7.4), minimum campaign coverage (>= 1 full campana), and minimum operator diversity for behavioral models.

**FR-08B05 — Delivery sequence and phase triggers**
The document MUST define the ML feature delivery sequence within Phase 3 using the Roadmap §7.1 priority order (P3-Q1 through P3-Q4) and the three Phase 3 trigger conditions from Roadmap §7.4: (1) >= 20 paying customers, (2) >= 10,000 romaneos processed in production, (3) AI data pipeline review completed. Each feature MUST have its own data-readiness trigger beyond the Phase 3 entry gate.

**FR-08B06 — IoT integration roadmap**
The document MUST describe the IoT sensor integration path for Layer 4 (StorageUnit.environment_sensor_id anchor): what sensors are needed, integration protocol options, and how sensor data feeds into ML models.

**FR-08B07 — Qdrant and vector search strategy**
The document MUST describe whether/when Qdrant moves from development-only to production for semantic search features, NLQ (natural language querying), or other user-facing ML capabilities.

### Sub-Deliverable C: Software Requirements Specification (SRS)

**FR-08C01 — Requirement ID scheme**
The SRS MUST use a traceable requirement ID scheme: `SRS-PPNN` where PP = module prefix (RE=Recepcion, CA=Calidad, AL=Almacenamiento, CC=CuentasCorrientes, LQ=Liquidaciones, FA=Facturacion, AG=Agronomia, CJ=Canje, HW=Hardware, IF=Interface, SE=Security, PF=Performance) and NN = sequential number.

**FR-08C02 — Shall-statements for Phase 1 modules**
The SRS MUST contain formal shall-statements for all Phase 1 modules (RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES) derived from PRD §4.1-§4.4. Each shall-statement MUST have: unique ID, description, priority (Must/Should/Could per MoSCoW), source (PRD section), and traceability to implementation spec (09/10/11/12).

**FR-08C03 — Interface requirements: ARCA SOAP**
The SRS MUST specify external interface requirements for all four ARCA web services: protocol (SOAP/XML over HTTPS), authentication method (WSAA TRA), data exchange format (XML), and reference to 08a for detailed integration guide.

**FR-08C04 — Interface requirements: weighbridge hardware**
The SRS MUST specify weighbridge interface requirements with protocol-level detail deferred from PRD §7: baud rates, frame formats, parity settings, stop bits, data bits for RS-232; Modbus RTU function codes and register addresses for Sipel Orion; ASCII stream format for GaMa A12; TCP/IP port and framing for KYASERV bridge.

**FR-08C05 — Interface requirements: REST API**
The SRS MUST trace each functional requirement to its corresponding REST API endpoint(s) from the REST API Design (spec-06), establishing a requirement-to-endpoint traceability matrix.

**FR-08C06 — Performance requirements**
The SRS MUST formalize the performance targets from PRD §8 as measurable requirements: API response time, sync latency, romaneo end-to-end time, concurrent user capacity, and database query thresholds.

**FR-08C07 — Security requirements**
The SRS MUST formalize security requirements: JWT RS256 authentication, tenant isolation (3-layer defense), field-level encryption for PII (AES-256-GCM), Argon2 password hashing, SSRF validation pipeline, and rate limiting.

**FR-08C08 — Data requirements**
The SRS MUST specify data requirements referencing the Data Model (spec-03): entity inventory, field types and precisions (DECIMAL(17,3) for weights/money), referential integrity rules (ON DELETE behaviors per ADR-012), and campaign-year segregation.

**FR-08C09 — Traceability matrix**
The SRS MUST include a traceability matrix mapping: PRD user story -> SRS requirement ID -> implementation spec (09-16) -> REST API endpoint -> test marker.

**FR-08C10 — Phase 2 deferred requirements**
The SRS MUST include Phase 2 module requirements (LIQUIDACIONES, FACTURACION, AGRONOMIA, CANJE) as "Deferred" status entries with requirement IDs reserved but not fully specified — establishing the ID namespace for future specs.

---

## Non-Functional Requirements

**NF-0801 — Expansion of upstream, not repetition**
Each deliverable MUST expand on its upstream source — not copy-paste from it. 08a expands HLD §6 with endpoint-level detail. 08b expands HLD §12 with ML-specific analysis. 08c formalizes PRD §4 into engineering requirements.

**NF-0802 — Zero TBD/TODO**
No unresolved placeholders in any of the three deliverables. If information is genuinely unavailable (e.g., exact Modbus register addresses vary by scale model), state the constraint explicitly instead of writing TBD.

**NF-0803 — Consistent terminology**
All three documents MUST use the canonical terms from the Data Model (spec-03) and PRD §2.1 glossary: romaneo, merma, CPE, liquidacion primaria, peso neto, grado asignado, bonificacion/rebaja, posicion consolidada, cuenta corriente de productores.

**NF-0804 — No implementation code**
These are blueprint documents. No Python, SQL, or shell code blocks. Mermaid diagrams, XML schema summaries (abbreviated, not full payloads), and configuration tables are allowed.

**NF-0805 — ADR citation format**
All ADR references MUST use the established format: **ADR-NNN (Title)** — e.g., "ADR-025 (ARCA Web Service Architecture)".

---

## Target Document Structures

### 08a — ARCA Grain Integration Guide

```
§1  Document Metadata
    — Version 1.0, status, date, changelog, upstream docs
    — "This document is the developer reference for ARCA grain web service integration ..."

§2  ARCA Service Overview
    §2.1 Hub-and-spoke architecture (Mermaid: WSAA -> WSLPG, WSCPE, WSFEv1)
    §2.2 Service catalog table (service | purpose | phase | production URL | homologation URL)
    §2.3 Authentication prerequisite (all services require WSAA Token+Sign)

§3  WSAA Authentication
    §3.1 TRA generation (XML structure, fields)
    §3.2 Certificate signing (X.509, CMS envelope, Base64)
    §3.3 LoginCMS invocation (SOAP method, request/response)
    §3.4 Token+Sign caching (Redis 11h TTL, concurrent refresh handling)
    §3.5 Sequence diagram (Mermaid)
    §3.6 Error handling (timeout, auth error mid-batch, certificate expiry)

§4  WSLPG — Grain Settlement (Form 1116-B/C)
    §4.1 Purpose and regulatory context (RG 3419/2012, RG 3690/2014)
    §4.2 Service URLs (production + homologation)
    §4.3 liquidacionAutorizar method (request fields, XML schema summary)
    §4.4 Single grain type constraint (codGrano at XML root — ADR-019)
    §4.5 SISA blocking gate (retention tier lookup — ADR-027)
    §4.6 Response parsing and COE extraction
    §4.7 Error codes and handling

§5  WSCPE — CPE Lifecycle
    §5.1 CPE/CTG overview and regulatory context
    §5.2 CPE state machine (Mermaid: Activa -> Arribo -> Descargada -> Confirmada_Definitiva)
    §5.3 Method catalog (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor)
    §5.4 5-day Automotor validity window
    §5.5 Offline store-and-forward (PendingOperation queue — ADR-030)
    §5.6 Error paths (CPE expiry, offline queue overflow)

§6  WSFEv1/CAEA — Electronic Invoicing
    §6.1 CAE online path (FECAESolicitar)
    §6.2 CAEA offline path (quincena batch pre-authorization)
    §6.3 Legal constraint: CAEA must precede offline period (warning callout)
    §6.4 Rust CAEA batch builder (feature 024 reference)
    §6.5 Error paths

§7  Certificate Management
    §7.1 Per-service certificate requirement
    §7.2 Certificate provisioning procedure (ARCA portal)
    §7.3 Private key storage (Google Cloud Secret Manager)
    §7.4 Certificate rotation procedure
    §7.5 Certificate expiry detection and alerting

§8  Homologation Testing Guide
    §8.1 Homologation environment overview
    §8.2 Pre-seeded test CUITs and known quirks
    §8.3 Testing checklist per service (WSAA, WSLPG, WSCPE, WSFEv1)
    §8.4 Promoting from homologation to production

§9  Open-Source Reference Implementations
    §9.1 pyafipws overview (scope, what is usable)
    §9.2 Other community libraries
    §9.3 Adaptation notes for GraviTea (Django + Rust context)

§10 ADR Cross-Reference
    — Table: ADR | Title | Impact on ARCA integration | Section reference

§11 Glossary
    — ARCA-specific terms (not duplicating PRD glossary but extending it)
```

**Section count**: 11 §-level sections. **Mermaid diagrams**: >= 3 (hub-spoke, WSAA sequence, CPE state machine).
**Tables**: >= 5 (service catalog, retention tiers, error handling, test checklist, ADR cross-ref).

### 08b — AI/ML Feature Roadmap

```
§1  Document Metadata
    — Version 1.0, status, date, changelog, upstream docs

§2  Strategic Context
    §2.1 Why AI/ML for acopio operations
    §2.2 Data advantage (structured from day one — ADR-033)
    §2.3 Competitive differentiation (no competitor has ML features)

§3  4-Layer Data Architecture
    §3.1 Layer 1: Operational Data (fields, precision, capture frequency)
    §3.2 Layer 2: Behavioural Data (provenance fields, 6 timestamps — ADR-034/035)
    §3.3 Layer 3: Quality History (longitudinal QualityAnalysis records)
    §3.4 Layer 4: Physical State / IoT-Ready (sensor anchor FK)
    §3.5 Data architecture diagram (Mermaid: layers -> ML models)

§4  ML Model Catalog (Roadmap §7.1 priority order)
    §4.1 P3-Q1: Predictive merma modelling (regression on tabular data — highest ROI)
    §4.2 P3-Q2: Price optimisation signals (MAT feed + AccountMovement time-series)
    §4.3 P3-Q3: Storage condition anomaly detection (IoT sensor threshold-based)
    §4.4 P3-Q4: Natural language grain position queries (NLQ: LLM -> SQL)
    §4.5 HLD informative candidates: silo assignment optimization, weighbridge fraud detection
    §4.6 Deferred: Computer vision grain grading (camera hardware partnership required)
    For each: description | input features | target variable | min training data | timeline

§5  Feature Engineering Strategy
    §5.1 Raw field -> feature transformation logic per model
    §5.2 Temporal aggregation windows
    §5.3 Cross-entity feature joins
    §5.4 Feature storage and serving considerations

§6  Training Data Collection Plan
    §6.1 Phase 1-2 data accumulation targets
    §6.2 Minimum thresholds per model (romaneo count, campana coverage, operator diversity)
    §6.3 Data quality monitoring during accumulation
    §6.4 Data labeling strategy (where applicable)

§7  Delivery Sequence
    §7.1 Phase 3 ML delivery order (P3-Q1 through P3-Q4 per Roadmap §7.1)
    §7.2 Phase 3 trigger conditions (Roadmap §7.4: 20 customers, 10k romaneos, AI pipeline review)
    §7.3 Deferred capabilities (computer vision, advanced silo optimization)
    §7.4 Dependency graph (Mermaid: data readiness -> model training -> deployment)

§8  IoT Integration Roadmap
    §8.1 Target sensors (temperature, humidity, CO2)
    §8.2 Integration protocols (LoRaWAN, Modbus TCP, MQTT)
    §8.3 Data pipeline: sensor -> Django API -> QualityAnalysis enrichment
    §8.4 Feed into quality degradation prediction model

§9  Vector Search and NLQ Strategy
    §9.1 Qdrant: development vs production use cases
    §9.2 User-facing semantic search feasibility
    §9.3 Natural Language Querying (NLQ) for operators

§10 Infrastructure Requirements
    §10.1 Model training infrastructure (GPU, storage)
    §10.2 Model serving (inference latency targets)
    §10.3 Feature store considerations
    §10.4 Cost estimates (directional)

§11 ADR Cross-Reference
    — Table: ADR | Title | Impact on ML strategy
```

**Section count**: 11 §-level sections. **Mermaid diagrams**: >= 2 (data layers, delivery sequence).
**Tables**: >= 4 (model catalog, training data thresholds, sensor options, ADR cross-ref).

### 08c — Software Requirements Specification (SRS)

```
§1  Document Metadata
    — Version 1.0, status, date, changelog, upstream docs

§2  Introduction
    §2.1 Purpose (formalize PRD into engineering requirements)
    §2.2 Scope (Phase 1 fully specified; Phase 2 ID-reserved, deferred)
    §2.3 Requirement ID scheme (SRS-PPNN)
    §2.4 Priority classification (MoSCoW: Must/Should/Could/Won't)
    §2.5 Glossary reference (PRD §2.1 — not duplicated)

§3  System Overview
    §3.1 System context (C4 Level 1 reference to HLD)
    §3.2 User roles (balancero, laboratorista, admin, contador, productor)
    §3.3 System boundaries

§4  Functional Requirements — Phase 1
    §4.1 RECEPCION (SRS-RE01 through SRS-RENN)
    §4.2 CALIDAD (SRS-CA01 through SRS-CANN)
    §4.3 ALMACENAMIENTO (SRS-AL01 through SRS-ALNN)
    §4.4 CUENTAS CORRIENTES (SRS-CC01 through SRS-CCNN)
    For each requirement: ID | Description (shall-statement) | Priority | Source (PRD §) | Impl spec | API endpoint

§5  Functional Requirements — Phase 2 (Deferred)
    §5.1 LIQUIDACIONES (SRS-LQ01...) — ID reserved, not fully specified
    §5.2 FACTURACION (SRS-FA01...) — ID reserved, not fully specified
    §5.3 AGRONOMIA (SRS-AG01...) — ID reserved, not fully specified
    §5.4 CANJE (SRS-CJ01...) — ID reserved, not fully specified

§6  External Interface Requirements
    §6.1 ARCA SOAP interfaces (SRS-IF01...) — protocol, auth, reference to 08a
    §6.2 Weighbridge hardware interfaces (SRS-HW01...)
        — RS-232: baud rates, frame format, parity, data bits, stop bits
        — Modbus RTU: function codes, register addresses (Sipel Orion)
        — ASCII stream: GaMa A12 format, delimiter, stability detection
        — TCP/IP: KYASERV bridge port, framing protocol
    §6.3 REST API interfaces (SRS-IF10...) — reference to spec-06

§7  Performance Requirements (SRS-PF01...)
    — API response time, sync latency, romaneo cycle time, concurrent users, DB query time

§8  Security Requirements (SRS-SE01...)
    — JWT RS256, tenant isolation, encryption, Argon2, SSRF, rate limiting

§9  Data Requirements (SRS-DA01...)
    — Entity inventory, field precisions, referential integrity, campaign segregation

§10 Traceability Matrix
    — Table: PRD User Story | SRS Requirement | Impl Spec | API Endpoint | Test Marker

§11 Constraints and Assumptions
    — Regulatory constraints, hardware constraints, team size, offline assumptions

§12 Appendix: Requirement ID Namespace
    — Reserved ID ranges per module for future expansion
```

**Section count**: 12 §-level sections. **Mermaid diagrams**: 0-1 (optional system context).
**Tables**: >= 6 (requirements tables per module, traceability matrix, interface specs, performance, security).

---

## Acceptance Criteria

### 08a — ARCA Grain Integration Guide

**AC-08A01 — All four ARCA services documented**
`grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1"` returns >= 40 (comprehensive coverage across sections).

**AC-08A02 — Mermaid diagrams**
`grep -c '```mermaid'` returns >= 3 (hub-spoke, WSAA sequence, CPE state machine).

**AC-08A03 — Homologation URLs**
`grep -c "fwshomo.afip"` returns >= 1 (homologation environment documented).

**AC-08A04 — ADR citations**
`grep -c "ADR-019\|ADR-025\|ADR-026\|ADR-027\|ADR-028\|ADR-029\|ADR-030"` returns >= 7 (one per ARCA-related ADR).

**AC-08A05 — Error handling table**
`grep -c "Failure Mode\|Error Code\|Retry"` returns >= 4 (error handling documented per service).

**AC-08A06 — No TBD/TODO**
`grep -ci "TBD\|TODO\|placeholder"` returns 0.

### 08b — AI/ML Feature Roadmap

**AC-08B01 — All Roadmap ML model candidates present**
`grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language"` returns >= 4 (P3-Q1 through P3-Q4).

**AC-08B02 — 4-layer data strategy**
`grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4"` returns >= 8.

**AC-08B03 — ADR citations**
`grep -c "ADR-033\|ADR-034\|ADR-035"` returns >= 3.

**AC-08B04 — Training data thresholds**
`grep -c "romaneo\|campana\|training data"` returns >= 6 (minimum data requirements specified).

**AC-08B05 — IoT section present**
`grep -c "sensor\|IoT\|LoRa\|MQTT\|temperature"` returns >= 4.

**AC-08B06 — No TBD/TODO**
`grep -ci "TBD\|TODO\|placeholder"` returns 0.

### 08c — Software Requirements Specification (SRS)

**AC-08C01 — Requirement IDs present**
`grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC"` returns >= 20 (Phase 1 modules have requirements).

**AC-08C02 — Shall-statements**
`grep -ci "shall"` returns >= 30 (formal requirement language used throughout).

**AC-08C03 — Weighbridge hardware detail**
`grep -c "baud\|parity\|Modbus\|RS-232\|frame format"` returns >= 5 (protocol-level detail present).

**AC-08C04 — Traceability matrix present**
`grep -c "Traceability\|PRD.*SRS\|SRS.*spec-09\|SRS.*spec-10"` returns >= 4.

**AC-08C05 — Phase 2 deferred section**
`grep -c "SRS-LQ\|SRS-FA\|SRS-AG\|SRS-CJ"` returns >= 4 (ID namespaces reserved).

**AC-08C06 — Performance requirements quantified**
`grep -c "ms\|second\|concurrent\|latency"` returns >= 4 (numeric performance targets).

**AC-08C07 — No TBD/TODO**
`grep -ci "TBD\|TODO\|placeholder"` returns 0.

---

## Dependencies

### This spec depends on:

| Spec | Document | What is consumed |
|------|----------|-----------------|
| spec-01 | Product Vision & Scope v1.0 | Strategic goals, AI vision, market context |
| spec-02 | PRD v1.0 | Module specs, user stories, regulatory compliance rules, hardware requirements, non-functional requirements |
| spec-03 | Data Model & Domain Model v1.0 | Entity names, field types/precisions, relationship rules, AI-ready data fields |
| spec-04 | Architecture Decision Records v1.0 | ADR-019 (single grain type), ADR-025-030 (ARCA architecture + offline + sync), ADR-032 (weighbridge), ADR-033-035 (AI data strategy) |
| spec-05 | High-Level Design v1.0 | §6 ARCA architecture (expanded by 08a), §12 AI/ML readiness (expanded by 08b), security architecture |
| spec-06 | REST API Design v1.0 | Phase 1 endpoint definitions (traced by 08c), Phase 2 deferred shapes |
| spec-07 | Roadmap v1.0 | Phase timelines, delivery sequence, Phase 2/3 triggers |

### This spec blocks:

| Downstream | What is provided |
|------------|-----------------|
| spec-09 (Grain Reference Data) | 08c requirements trace to spec-09; 08a provides ARCA context for understanding grain codes |
| spec-10 (Romaneo Core) | 08a is the ARCA integration playbook for WSCPE calls during romaneo; 08c provides formal romaneo requirements |
| spec-11 (Storage & Position) | 08c provides formal storage requirements; 08b explains data capture rationale for AI readiness |
| spec-12 (Producer Accounts) | 08c provides formal cuenta corriente requirements |
| spec-14 (WSLPG Integration) | 08a is the primary developer reference for WSLPG implementation |

### Notes:

- Implementation specs (09+) MUST have access to 08a (ARCA guide) and 08c (SRS) as reference material.
- 08b (AI/ML roadmap) justifies schema decisions already captured in ADR-033/034/035 — it does not create new schema requirements.
- If PRD (spec-02) or HLD (spec-05) are updated materially, re-run `/sc:improve` on this context file first.
- The three sub-deliverables are independent of each other — they can be written in any order within the spec-08 pipeline.
