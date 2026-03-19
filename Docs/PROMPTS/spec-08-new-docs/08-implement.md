# spec-08: New Blueprint Documents -- Implementation Context

## 1. Overview

Spec-08 produces **three Markdown blueprint documents** that complete the GraviTea Acopio ERP
design suite before implementation specs (09-12) begin.

| Sub-spec | Output File | Action |
|----------|-------------|--------|
| **08a** | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | Create new file |
| **08b** | `Docs/Project Blueprint/AI-ML Feature Roadmap.md` | Create new file |
| **08c** | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | Overwrite stale retail-vertical SRS |

**Authorship model**: Single-author document writing. No tmux agent teams, no agent instruction
files, no code implementation. This is a blueprint spec (01-08).

**Writing order**: 08a -> 08c -> 08b

| Order | Sub-spec | Rationale |
|-------|----------|-----------|
| 1st | **08a** (ARCA Grain Integration Guide) | 08c cross-references 08a in its external interface section (SRS-IF01). Writing 08a first avoids back-patching. |
| 2nd | **08c** (Software Requirements Specification) | Depends on 08a for ARCA interface cross-references. Independent of 08b. |
| 3rd | **08b** (AI/ML Feature Roadmap) | Most independent document. References only upstream blueprints (HLD, Roadmap, Data Model, ADRs). |

---

## 2. Full Writing Context

Read these files **in this order** before starting any document:

| Priority | File | What it provides |
|----------|------|-----------------|
| 1 | `Docs/PROMPTS/spec-08-new-docs/08-specify.md` | Critical Domain Facts (primary knowledge source), Functional Requirements (FR-08A01 through FR-08C10), Non-Functional Requirements (NF-0801 through NF-0805), Target Document Structures, Acceptance Criteria |
| 2 | `Docs/PROMPTS/spec-08-new-docs/08-plan.md` | Section-by-section writing plans with research source mapping, content guidelines, checkpoint gates, done criteria |
| 3 | `specs/008-acopio-new-docs/plan.md` | Technical context, document structure definitions, writing order rationale, gate thresholds |
| 4 | `specs/008-acopio-new-docs/tasks.md` | Task execution order (T001-T033), phase dependencies, parallel opportunities |
| 5 | `specs/008-acopio-new-docs/spec.md` | User stories, acceptance scenarios, functional requirements (FR-001 through FR-031), success criteria (SC-001 through SC-007) |

The **Critical Domain Facts** section in `08-specify.md` is the single most important reference.
It consolidates all verified domain knowledge needed across all three documents. Use it as the
primary source and supplement with RAG queries only when a section requires detail beyond what
the domain facts provide.

---

## 3. Domain Knowledge Protocol

### RAG Queries -- Required Method

**NEVER** read full research PDF or Markdown files in `Docs/Researches/`. They are too large
for context windows and contain unstructured content.

**ALWAYS** use targeted RAG queries:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'YOUR QUERY HERE' -l 5
```

### Available RAG Collections

| Collection | Contents | Use for |
|------------|----------|---------|
| `acopio_research` | 20+ grain industry research docs: weighbridge protocols, quality standards, WSLPG/WSCPE technical specs, AI/ML applications, day-to-day operations | 08a (WSLPG fields, WSCPE lifecycle, open-source refs), 08b (ML model details, IoT sensors), 08c (romaneo workflow, weighbridge hardware, quality parameters) |
| `arca_api_specs` | 8 ARCA technical specifications: WSAA, WSFEv1, WSMTXCA, WSBFEV1, WSSEG, padron, SIRE | 08a (WSAA auth spec, service URLs, XML schemas) |
| `arca_dev_guides` | 14 ARCA developer manuals: WSAA, WSLPG, WSCPE, WSCDC, SIRE, WSFEv1, WSFEX | 08a (TRA creation, CMS signing, cert provisioning, homologation patterns) |
| `arca_setup_certs` | 8 certificate and environment setup docs | 08a (certificate management, Secret Manager) |

### Knowledge Priority

1. **Critical Domain Facts** from `08-specify.md` -- treat as ground truth
2. **RAG query results** -- supplement domain facts with specific details (URLs, field names, method signatures)
3. **Upstream blueprints** (HLD, PRD, Data Model, ADR, REST API, Roadmap) -- reference for cross-document consistency

---

## 4. Section Drafting Instructions per Document

### 4A. ARCA Grain Integration Guide (08a)

**Target file**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`

**Tasks**: T007-T014 (Phase 3 in tasks.md)

**Minimum deliverables**: 11 sections, >= 3 Mermaid diagrams, >= 5 tables

---

#### SS1 -- Document Metadata

- **What to write**: Version 1.0 header following the HLD/Roadmap pattern (metadata table, changelog, reading guide, upstream dependencies).
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - Version 1.0, branch `008-acopio-new-docs`
  - Upstream dependencies: HLD SS6, ADR v1.0, PRD SS6
  - Purpose statement: developer reference for ARCA grain web service integration
- **Effort**: Small

#### SS2 -- ARCA Service Overview

- **What to write**: Hub-and-spoke architecture explanation with Mermaid diagram showing WSAA as authentication gateway for WSLPG, WSCPE, WSFEv1. Service catalog table with purpose, phase, production URL, and homologation URL.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSAA WSLPG WSCPE WSFEv1 production homologation URL" -l 5`
- **Key facts that MUST appear**:
  - 4 services: WSAA, WSLPG, WSCPE, WSFEv1
  - WSLPG production URL: `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl`
  - WSLPG homologation URL: `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl`
  - WSCPE and WSFEv1 URLs (research from RAG)
  - Hub-and-spoke Mermaid diagram (counts toward >= 3 gate)
- **Effort**: Medium

#### SS3 -- WSAA Authentication

- **What to write**: Complete TRA -> CMS -> LoginCMS -> Token+Sign flow with Mermaid sequence diagram. Redis caching strategy. Concurrent refresh handling. Error handling subsection.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSAA authentication TRA LoginCMS Token Sign certificate X509" -l 5`
- **Key facts that MUST appear**:
  - TRA XML structure with fields
  - X.509 signing -> CMS envelope -> Base64 encoding
  - LoginCMS SOAP method invocation and parameters
  - Token lifetime = 12 hours
  - Redis cache TTL = 11 hours (1-hour safety margin)
  - Concurrent refresh handling pattern
  - Mermaid sequence diagram (counts toward >= 3 gate)
  - Error handling: timeout, auth error mid-batch, certificate expiry
- **Effort**: Large

#### SS4 -- WSLPG -- Grain Settlement (Form 1116-B/C)

- **What to write**: Regulatory context, service URLs, `liquidacionAutorizar` XML field reference, codGrano constraint, SISA blocking gate with retention tiers table, COE extraction, error codes.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSLPG liquidacionAutorizar XML codGrano SISA retention" -l 5`
- **Key facts that MUST appear**:
  - codGrano single-grain constraint per ADR-019 (Single Form 1116-C per Grain Type)
  - Retention tiers table: Estado 1 (5% IVA / 0% Ganancias), Estado 2 (8% / 2%), Estado 3 (10.5% / 15%), Non-registered (16% / 30%)
  - SISA blocking gate per ADR-027 (SISA-Tier Retention Calculation)
  - COE (Codigo de Operacion Electronico) returned on success
  - RG 3419/2012, RG 3690/2014 regulatory context
  - Parameter lookup methods from research 5.1 (tipoGranoConsultar, codigoGradoReferenciaConsultar, etc.)
- **Effort**: Large

#### SS5 -- WSCPE -- CPE Lifecycle

- **What to write**: CPE/CTG overview, Mermaid state machine diagram, full method catalog, 5-day validity, offline store-and-forward, discrepancy resolution.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSCPE CPE lifecycle confirmarArribo confirmarDescargaCPE methods" -l 5`
- **Key facts that MUST appear**:
  - State machine: Activa -> Arribo -> Descargada -> Confirmada_Definitiva (plus Anulada/Rechazada)
  - All 7 methods: `solicitarCPEAutomotor`, `consultarCPEAutomotor`, `confirmarArriboCPE`, `confirmarDescargaCPE`, `anularCPE`, `rechazoCPE`, `consultarRenspa`
  - Method name discrepancy resolution: HLD says `descargadoDestinoCPE`, ARCA WSDL says `confirmarDescargaCPE` -- resolve against ARCA WSDL, document the discrepancy
  - 5-day Automotor validity window
  - "Vencida" is a derived condition (elapsed time), not a WSCPE state code
  - Offline store-and-forward via PendingOperation queue per ADR-030 (Store-and-Forward Queue for ARCA Web Service Calls)
  - Mermaid state machine diagram (counts toward >= 3 gate)
- **Effort**: Large

#### SS6 -- WSFEv1/CAEA -- Electronic Invoicing

- **What to write**: CAE online path, CAEA offline path, legal warning callout, Rust 024 reference, error paths.
- **RAG query**: None strictly needed -- domain facts in 08-specify.md are sufficient. Optionally: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "CAEA quincena offline fiscal authorization" -l 5`
- **Key facts that MUST appear**:
  - Online path: `FECAESolicitar` returns a CAE per invoice
  - Offline path: CAEA (quincena batch codes obtained before offline period)
  - CAEA legal constraint as a `> **WARNING**:` callout -- must obtain BEFORE offline period, no retroactive authorization
  - CAEA quincena codes cannot roll over
  - Rust CAEA batch builder: feature 024-rust-arca-batch (serde_json, GIL-released)
  - ADR-026 (CAEA for Offline Fiscal Operations)
- **Effort**: Medium

#### SS7 -- Certificate Management

- **What to write**: Per-service certificate requirement, provisioning procedure, Secret Manager storage, rotation procedure, expiry alerting.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "ARCA certificate X509 per service provisioning Secret Manager" -l 5`
- **Key facts that MUST appear**:
  - Each ARCA service requires a SEPARATE X.509 certificate -- shared certificates rejected
  - Private keys stored in Google Cloud Secret Manager exclusively -- never in code, .env, or Docker
  - ADR-025 (ARCA Web Service Architecture)
  - Certificate rotation procedure
  - Expiry detection and alerting strategy
- **Effort**: Medium

#### SS8 -- Homologation Testing Guide

- **What to write**: Environment overview, production/homologation URLs table for all 4 services, pre-seeded test CUITs, known quirks, per-service testing checklist, promotion procedure.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "ARCA homologacion testing CUIT certificates environment" -l 5`
- **Key facts that MUST appear**:
  - `fwshomo.afip.gov.ar` base URL for homologation (required for grep gate)
  - Production and homologation URLs for all four services
  - Pre-seeded test CUITs
  - Per-service testing checklist
  - Promotion procedure from homologation to production
- **Effort**: Medium

#### SS9 -- Open-Source Reference Implementations

- **What to write**: pyafipws assessment, other libraries, adaptation notes for GraviTea (Django + Rust).
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "pyafipws WSLPG open source ARCA integration" -l 5`
- **Key facts that MUST appear**:
  - `pyafipws` (reingart/pyafipws on GitHub): main open-source Python library, includes `wslpg.py`
  - `py3afipws` on PyPI: Python 3 fork
  - `django-afip` (WhyNotHugo/django-afip): Django-specific, WSFEv1 focused
  - `afip.py` / Afip SDK (afipsdk.com): commercial alternative
  - SistemasAgiles wiki: community documentation for LiquidacionPrimariaGranos
  - Adaptation caveats for GraviTea (Django + Rust context)
- **Effort**: Small

#### Consolidated Error Handling Table (FR-007)

- **What to write**: Place after SS9 or as appendix to SS8. Cross-reference failure modes, retry strategies, and operator actions across all 4 ARCA services (WSAA, WSLPG, WSCPE, WSFEv1).
- **RAG query**: Not strictly needed -- synthesize from content written in SS3-SS6 error handling subsections.
- **Key facts that MUST appear**:
  - Failure modes per service
  - Retry strategies (exponential backoff, circuit breaker, manual intervention)
  - Operator actions required
  - Column structure: Service | Failure Mode | System Response | Retry Strategy | Operator Action
- **Effort**: Medium

#### SS10 -- ADR Cross-Reference

- **What to write**: Table mapping each ARCA-related ADR to title, impact, and section reference.
- **RAG query**: None needed -- use ADR v1.0 document.
- **Key facts that MUST appear**:
  - All 7 ADRs (required for grep gate):
    1. ADR-019 (Single Form 1116-C per Grain Type)
    2. ADR-025 (ARCA Web Service Architecture)
    3. ADR-026 (CAEA for Offline Fiscal Operations)
    4. ADR-027 (SISA-Tier Retention Calculation)
    5. ADR-028 (Offline-First as Base Architecture)
    6. ADR-029 (Conflict Resolution Taxonomy)
    7. ADR-030 (Store-and-Forward Queue for ARCA Web Service Calls)
- **Effort**: Small

#### SS11 -- Glossary

- **What to write**: ARCA-specific terms only. Extend the PRD glossary, do not duplicate it.
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - Terms: TRA, CMS, Token+Sign (TA), COE, CTG, CPE, CAEA, quincena, liquidacion primaria, Form 1116-B/C, codGrano, SISA, homologacion
  - No overlap with PRD glossary (romaneo, merma, etc. are defined there)
- **Effort**: Small

---

### 4B. Software Requirements Specification (08c)

**Target file**: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

**Tasks**: T015-T022 (Phase 4 in tasks.md)

**Minimum deliverables**: 12 sections, >= 20 SRS-XX IDs, >= 30 shall-statements

**Note**: This file overwrites the stale retail-vertical SRS. Preserve nothing from the existing file.

---

#### SS1-SS3 -- Metadata, Introduction, System Overview

- **What to write**: Version header (note: complete rewrite). SRS-PPNN ID scheme explanation. MoSCoW classification. User roles. C4 Level 1 reference to HLD (not duplicated).
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - SRS-PPNN scheme: PP = module prefix (RE, CA, AL, CC, LQ, FA, AG, CJ, HW, IF, SE, PF, DA), NN = sequential number
  - MoSCoW: Must/Should/Could/Won't
  - User roles: balancero, laboratorista, admin, contador, productor
  - Phase 1 fully specified; Phase 2 ID-reserved and deferred
- **Effort**: Small

#### SS4.1 -- RECEPCION Functional Requirements

- **What to write**: SRS-RE01 through SRS-RENN shall-statements. Each as table row: ID | shall-statement | MoSCoW | PRD source | impl spec | API endpoint.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo workflow truck arrival weighing quality grading" -l 5`
- **Key facts that MUST appear**:
  - CPE arrival confirmation via WSCPE
  - Weighbridge integration (gross/tare/net weight capture)
  - Romaneo workflow: truck arrival -> CPE verification -> Confirmacion de Arribo -> weighing (peso bruto) -> calado -> unloading -> tare -> peso neto -> Confirmacion Definitiva
  - Truck queue management
  - Impl spec: spec-10
- **Effort**: Large

#### SS4.2 -- CALIDAD Functional Requirements

- **What to write**: SRS-CA01 through SRS-CANN shall-statements.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity tolerance bonificacion rebaja" -l 5`
- **Key facts that MUST appear**:
  - Quality analysis: humedad, grado, bonificacion/rebaja
  - Tolerance table application per grain type
  - Quality grading workflow
  - Impl spec: spec-09 or spec-10
- **Effort**: Medium

#### SS4.3 -- ALMACENAMIENTO Functional Requirements

- **What to write**: SRS-AL01 through SRS-ALNN shall-statements.
- **RAG query**: None strictly needed -- PRD SS4.3 and Data Model provide sufficient context.
- **Key facts that MUST appear**:
  - Storage unit management, silo assignment
  - Grain position tracking (posicion consolidada)
  - Merma calculation
  - Impl spec: spec-11
- **Effort**: Medium

#### SS4.4 -- CUENTAS CORRIENTES Functional Requirements

- **What to write**: SRS-CC01 through SRS-CCNN shall-statements.
- **RAG query**: None strictly needed.
- **Key facts that MUST appear**:
  - Producer current accounts, account movements
  - Balance tracking, campaign-year segregation
  - Impl spec: spec-12
- **Effort**: Medium

#### SS5 -- Phase 2 Deferred Requirements

- **What to write**: SRS-LQ/FA/AG/CJ stub entries marked "Deferred".
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - SRS-LQ01 (Liquidaciones), SRS-FA01 (Facturacion), SRS-AG01 (Agronomia), SRS-CJ01 (Canje)
  - All marked "Deferred -- to be specified in Phase 2 implementation specs"
  - ID namespaces reserved for future expansion
- **Effort**: Small

#### SS6 -- External Interface Requirements

- **What to write**: SS6.1 ARCA SOAP (cross-ref to 08a). SS6.2 Weighbridge hardware (protocol-level detail). SS6.3 REST API (cross-ref to spec-06).
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "weighbridge RS-232 Modbus protocol baud rate frame format parity" -l 5`
- **Key facts that MUST appear**:
  - SS6.1: SOAP/XML over HTTPS, WSAA TRA auth, reference to 08a
  - SS6.2 -- RS-232: 9600 bps default (1200-38400), 8 data bits, no parity, 1 stop bit, DB-9 male, 15m max
  - SS6.2 -- Modbus RTU (Sipel Orion): functions 03h (Read Holding Registers), 06h (Write Single Register), 10h (Write Multiple Registers)
  - SS6.2 -- ASCII stream (GaMa A12): STX/ETX or CR/LF delimiters, stability detection
  - SS6.2 -- KYASERV: RS-232-to-Ethernet bridge, TCP/IP LAN access
  - SS6.3: Reference REST API Design v1.0 (spec-06)
- **Effort**: Large

#### SS7-SS9 -- Performance, Security, Data Requirements

- **What to write**: Formal shall-statements with quantified targets.
- **RAG query**: None needed -- PRD SS8 and domain facts are sufficient.
- **Key facts that MUST appear**:
  - SS7: SRS-PF01 <500ms API, SRS-PF02 <30s sync, SRS-PF03 <5min romaneo cycle
  - SS8: SRS-SE01 JWT RS256, SRS-SE02 RLS 3-layer defense, SRS-SE03 AES-256-GCM, SRS-SE04 Argon2, SRS-SE05 SSRF validation, SRS-SE06 rate limiting
  - SS9: SRS-DA01 entity inventory, SRS-DA02 DECIMAL(17,3) precision, SRS-DA03 ON DELETE per ADR-012, SRS-DA04 campaign segregation
- **Effort**: Small

#### SS10 -- Traceability Matrix

- **What to write**: Table: PRD user story -> SRS-ID -> impl spec (09-12) -> REST API endpoint -> pytest marker.
- **RAG query**: None needed -- synthesize from SS4 requirements and REST API Design.
- **Key facts that MUST appear**:
  - Every Must-priority requirement has a complete row with zero empty cells
  - PRD source references specific PRD section numbers
  - Impl spec maps to spec-09, spec-10, spec-11, or spec-12
  - API endpoint uses REST API Design paths
  - Test marker uses pytest marker convention (@pytest.mark.{module})
- **Effort**: Large

#### SS11 -- Constraints and Assumptions

- **What to write**: Regulatory, hardware, team size, offline constraints.
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - ARCA compliance mandatory
  - Offline-first is a hard requirement (44% poor connectivity during harvest)
  - 2-developer team assumption for Phase 1
  - Weighbridge models vary by plant -- protocol must be configurable
- **Effort**: Small

#### SS12 -- Appendix: Requirement ID Namespace

- **What to write**: Complete PP code table with reserved NN ranges.
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - 13 PP codes: RE, CA, AL, CC, LQ, FA, AG, CJ, HW, IF, SE, PF, DA
  - NN = 01-99 per namespace
- **Effort**: Small

---

### 4C. AI/ML Feature Roadmap (08b)

**Target file**: `Docs/Project Blueprint/AI-ML Feature Roadmap.md`

**Tasks**: T023-T029 (Phase 5 in tasks.md)

**Minimum deliverables**: 11 sections, >= 2 Mermaid diagrams, >= 4 tables

**Critical constraint**: MUST use the Roadmap's **3-phase model** -- ML features are Phase 3, NOT Phase 4. The HLD uses a 4-phase model where Phase 4 = AI/ML. The Roadmap consolidated this into Phase 3. 08b follows the Roadmap (SC-007).

---

#### SS1-SS2 -- Metadata and Strategic Context

- **What to write**: Version header. Why AI/ML for acopio. ADR-033 data advantage. Competitive differentiation.
- **RAG query**: None strictly needed -- domain facts sufficient. Optionally: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "AI ML grain storage competitive advantage acopio" -l 5`
- **Key facts that MUST appear**:
  - ADR-033 (4-Layer Data Strategy) captures training data from day one
  - No competitor in the acopio market has ML features
  - AGIS on VB6 -- no data pipeline for analytics
  - Data advantage compounds: every romaneo adds training examples
- **Effort**: Small

#### SS3 -- 4-Layer Data Architecture

- **What to write**: Detailed layer descriptions with concrete field references from Data Model. Mermaid diagram showing layers feeding into ML models.
- **RAG query**: None strictly needed -- domain facts and Data Model provide sufficient detail.
- **Key facts that MUST appear**:
  - Layer 1 -- Operational Data: all grain fields in real-time, DECIMAL(17,3) precision
  - Layer 2 -- Behavioural Data: operator_id, laboratorista_id, device_id + 6 named timestamps per romaneo (ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara) per ADR-035
  - Layer 3 -- Quality History: QualityAnalysis per (grain_type, campaign, storage_unit) -- longitudinal
  - Layer 4 -- Physical State / IoT-Ready: StorageUnit.environment_sensor_id nullable FK anchor
  - ADR-033, ADR-034 (provenance fields: created_by, device_id), ADR-035 (6 timestamps)
  - Mermaid data architecture diagram (counts toward >= 2 gate)
  - Must have >= 8 mentions of "Layer 1/2/3/4" for grep gate
- **Effort**: Large

#### SS4 -- ML Model Catalog

- **What to write**: Each model in Roadmap SS7.1 priority order. For each: description, input features, target variable, minimum training data, timeline.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "AI ML grain storage predictive merma model" -l 5`
- **Key facts that MUST appear**:
  - P3-Q1: Predictive merma modelling -- regression on tabular data, highest ROI
  - P3-Q2: Price optimisation signals -- MAT feed + AccountMovement time-series
  - P3-Q3: Storage condition anomaly detection -- IoT sensor threshold-based
  - P3-Q4: Natural language grain position queries (NLQ) -- LLM -> SQL
  - HLD SS12.6 informative candidates: silo assignment optimization, weighbridge fraud detection
  - Deferred: Computer vision grain grading (camera hardware partnership required)
  - Must have >= 4 mentions of merma model / price optim / anomaly detection / NLQ for grep gate
- **Effort**: Large

#### SS5-SS6 -- Feature Engineering and Training Data

- **What to write**: Raw field -> feature transforms, temporal windows, cross-entity joins. Minimum data thresholds, quality monitoring, labeling strategy.
- **RAG query**: None strictly needed. Optionally: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality degradation prediction feature engineering" -l 5`
- **Key facts that MUST appear**:
  - Romaneo fields -> merma features: humedad, peso_bruto, peso_neto, grain_type, storage_duration
  - Cross-entity join: Romaneo JOIN QualityAnalysis JOIN StorageUnit
  - Temporal windows: per-campaign for merma trends, rolling 30-day for anomaly baselines
  - Minimum thresholds: >= 10,000 romaneos, >= 1 full campana, >= 3 distinct operators
  - Natural labeling for merma (reception weight vs discharge weight)
- **Effort**: Medium

#### SS7 -- Delivery Sequence

- **What to write**: 3-phase model delivery order, Phase 3 triggers, deferred capabilities, Mermaid dependency graph.
- **RAG query**: None needed -- Roadmap SS7.1 and SS7.4 are the authoritative sources.
- **Key facts that MUST appear**:
  - **3-phase model** (NOT 4-phase) -- this is SC-007
  - Phase 3 triggers: (1) >= 20 paying customers, (2) >= 10,000 romaneos processed, (3) AI data pipeline review completed
  - P3-Q1 through P3-Q4 in Roadmap SS7.1 priority order
  - Per-model data-readiness triggers beyond the Phase 3 entry gate
  - Mermaid dependency graph (counts toward >= 2 gate)
- **Effort**: Medium

#### SS8 -- IoT Integration Roadmap

- **What to write**: Target sensors, integration protocols, data pipeline from sensor to ML model.
- **RAG query**: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "IoT grain storage sensor temperature humidity LoRaWAN MQTT" -l 5`
- **Key facts that MUST appear**:
  - StorageUnit.environment_sensor_id as nullable FK anchor
  - Target sensors: temperature, relative humidity, CO2 concentration
  - Protocol options: LoRaWAN (long-range low-power), Modbus TCP (industrial), MQTT (cloud gateway)
  - Data pipeline: sensor -> gateway -> Django REST API -> QualityAnalysis enrichment
  - Feed into P3-Q3 anomaly detection model
- **Effort**: Medium

#### SS9-SS10 -- Vector Search/NLQ and Infrastructure

- **What to write**: Qdrant dev vs prod strategy. NLQ feasibility. Training infrastructure. Inference latency targets.
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - Qdrant optional container for dev RAG -- not required in production Phases 1-2
  - NLQ: LLM translates natural language to SQL, not embedding search
  - Tabular models (merma, price): CPU training feasible, GPU optional
  - NLQ uses external LLM API -- no local GPU
  - Merma inference < 200ms (real-time); price signals hourly batch
  - Feature store optional for Phase 3 scale
- **Effort**: Small

#### SS11 -- ADR Cross-Reference

- **What to write**: Table: ADR | Title | Impact on ML strategy | Section reference.
- **RAG query**: None needed.
- **Key facts that MUST appear**:
  - All 3 ADRs (required for grep gate):
    1. ADR-033 (4-Layer Data Strategy)
    2. ADR-034 (Provenance Fields on All Grain Domain Models)
    3. ADR-035 (6 Named Timestamps on Romaneo)
- **Effort**: Small

---

## 5. Content Guidelines

| Guideline | Rule |
|-----------|------|
| **Tone** | Technical but accessible -- same register as HLD and Roadmap |
| **Language** | English primary. Spanish domain terms retained: romaneo, merma, liquidacion, CPE, CTG, campana, peso bruto/neto/tara, grado asignado, bonificacion/rebaja, posicion consolidada, cuenta corriente, acopiador |
| **Spanish terms** | Italicize on first use in each document; plain text thereafter |
| **ADR citations** | Always "ADR-NNN (Title)" -- e.g., "ADR-025 (ARCA Web Service Architecture)". Never by number alone |
| **Warning callouts** | `> **WARNING**: text` for critical legal/compliance constraints |
| **Cross-references** | "See 08a SS4 (WSLPG)" or "See PRD SS4.1 (Recepcion Module)" |
| **Requirement IDs** | Monospace: `SRS-RE01`, `SRS-PF03` |
| **No code** | No Python, SQL, or shell. Mermaid diagrams and abbreviated XML summaries allowed |
| **No TBD** | State constraints explicitly -- never write TBD, TODO, or placeholder |
| **Expansion rule** | Each document expands its upstream source. Never copy-paste from HLD, PRD, or Data Model |
| **Phase model** | 08b MUST use the Roadmap's 3-phase model. ML = Phase 3, not Phase 4 |
| **Mermaid syntax** | Use `graph TD`, `sequenceDiagram`, `stateDiagram-v2`, or `flowchart TD` as appropriate |
| **Tables** | GitHub-Flavored Markdown. Bold header rows. Aligned columns |
| **Version targeting** | Where ARCA WSDL versions matter (e.g., WSLPG v1.24), note the version and include update-checking instructions |

---

## 6. Gate Checks

Run after completing each document. All checks use `grep` against the finished file.

### Gate 1 -- After 08a (ARCA Grain Integration Guide)

File: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`

```bash
# ARCA service coverage (>= 40)
grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# Mermaid diagrams (>= 3)
grep -c '```mermaid' "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# Homologation URL (>= 1)
grep -c "fwshomo.afip" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# ADR citations (>= 7)
grep -c "ADR-019\|ADR-025\|ADR-026\|ADR-027\|ADR-028\|ADR-029\|ADR-030" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# No TBD/TODO (= 0)
grep -ci "TBD\|TODO\|placeholder" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
```

| Check | Command Pattern | Threshold | Validates |
|-------|----------------|-----------|-----------|
| ARCA service coverage | `grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1"` | >= 40 | AC-08A01 |
| Mermaid diagrams | `grep -c '` `` ` `` `mermaid'` | >= 3 | AC-08A02 |
| Homologation URL | `grep -c "fwshomo.afip"` | >= 1 | AC-08A03 |
| ADR citations | `grep -c "ADR-019\|ADR-025\|...\|ADR-030"` | >= 7 | AC-08A04 |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder"` | = 0 | AC-08A06 |

**If any check fails**: Fix the deficiency before proceeding to 08c.

### Gate 2 -- After 08c (Software Requirements Specification)

File: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

```bash
# Phase 1 requirement IDs (>= 20)
grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"

# Shall-statements (>= 30)
grep -ci "shall" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"

# Weighbridge hardware detail (>= 5)
grep -c "baud\|parity\|Modbus\|RS-232" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"

# No TBD/TODO (= 0)
grep -ci "TBD\|TODO\|placeholder" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
```

| Check | Command Pattern | Threshold | Validates |
|-------|----------------|-----------|-----------|
| Phase 1 requirement IDs | `grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC"` | >= 20 | AC-08C01 |
| Shall-statements | `grep -ci "shall"` | >= 30 | AC-08C02 |
| Weighbridge hardware detail | `grep -c "baud\|parity\|Modbus\|RS-232"` | >= 5 | AC-08C03 |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder"` | = 0 | AC-08C07 |

**If any check fails**: Fix the deficiency before proceeding to 08b.

### Gate 3 -- After 08b (AI/ML Feature Roadmap)

File: `Docs/Project Blueprint/AI-ML Feature Roadmap.md`

```bash
# ML model candidates (>= 4)
grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language" "Docs/Project Blueprint/AI-ML Feature Roadmap.md"

# 4-layer data strategy (>= 8)
grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4" "Docs/Project Blueprint/AI-ML Feature Roadmap.md"

# ADR citations (>= 3)
grep -c "ADR-033\|ADR-034\|ADR-035" "Docs/Project Blueprint/AI-ML Feature Roadmap.md"

# No TBD/TODO (= 0)
grep -ci "TBD\|TODO\|placeholder" "Docs/Project Blueprint/AI-ML Feature Roadmap.md"
```

| Check | Command Pattern | Threshold | Validates |
|-------|----------------|-----------|-----------|
| ML model candidates | `grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language"` | >= 4 | AC-08B01 |
| 4-layer data strategy | `grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4"` | >= 8 | AC-08B02 |
| ADR citations | `grep -c "ADR-033\|ADR-034\|ADR-035"` | >= 3 | AC-08B03 |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder"` | = 0 | AC-08B06 |

**If any check fails**: Fix the deficiency before declaring spec-08 complete.

---

## 7. Review Checklist

Run after each document is complete, before proceeding to the next:

- [ ] All sections from the target structure (in 08-specify.md) are present
- [ ] Mermaid diagrams render correctly (preview in a Markdown viewer)
- [ ] ADR citations use "ADR-NNN (Title)" format throughout
- [ ] Spanish domain terms italicized on first use in the document
- [ ] No TBD/TODO/placeholder markers anywhere in the document
- [ ] Cross-references to other documents are correct (section numbers, file names)
- [ ] Content expands upstream sources -- not copy-paste from HLD, PRD, or Data Model
- [ ] Terminology matches Data Model (spec-03) and PRD (spec-02) glossary
- [ ] No implementation code (Python, SQL, shell) -- only Mermaid, XML summaries, config tables

---

## 8. Done Criteria

Spec-08 is complete when ALL of the following are true:

### Document Existence

- [ ] `Docs/Project Blueprint/ARCA Grain Integration Guide.md` exists (08a)
- [ ] `Docs/Project Blueprint/AI-ML Feature Roadmap.md` exists (08b)
- [ ] `Docs/Project Blueprint/Software Requirements Specification (SRS).md` exists and contains acopio content (08c)

### Checkpoint Gates

- [ ] Gate 1 (08a) -- all 5 checks pass
- [ ] Gate 2 (08c) -- all 4 checks pass
- [ ] Gate 3 (08b) -- all 4 checks pass

### Functional Requirements Coverage

- [ ] FR-001 through FR-009 satisfied (08a: WSAA, WSLPG, WSCPE, WSFEv1, certificates, homologation, error handling, open-source refs, ADR citations)
- [ ] FR-010 through FR-016 satisfied (08b: 4-layer data, ML catalog, feature engineering, training data, delivery sequence, IoT, Qdrant)
- [ ] FR-017 through FR-026 satisfied (08c: ID scheme, shall-statements, ARCA interface, weighbridge interface, REST API traceability, performance, security, data requirements, traceability matrix, Phase 2 deferred)
- [ ] FR-027 through FR-031 satisfied (cross-cutting: expansion not repetition, zero TBD, consistent terminology, ADR format, no implementation code)

### Success Criteria Verifiability

- [ ] SC-001: 08a is self-contained for ARCA integration understanding
- [ ] SC-002: 100% of Phase 1 PRD user stories have corresponding SRS requirements
- [ ] SC-003: Traceability matrix has zero empty cells in Must-priority rows
- [ ] SC-004: Automated grep checks pass (Gates 1-3)
- [ ] SC-005: Implementation spec authors (09-12) have complete upstream context
- [ ] SC-006: ADR cross-references verified (08a cites 7 ADRs, 08b cites 3 ADRs)
- [ ] SC-007: 08b uses the Roadmap's 3-phase model (not the HLD's 4-phase model)

### Final Validation

- [ ] Zero TBD/TODO/placeholder markers across all three documents
- [ ] Terminology consistent with Data Model (spec-03) and PRD (spec-02) glossary throughout
- [ ] All Mermaid diagrams render correctly (validated via preview)
- [ ] All cross-document references point to correct section numbers
