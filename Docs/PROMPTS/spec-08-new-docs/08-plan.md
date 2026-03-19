# spec-08: New Blueprint Documents -- Writing Plan

## 1. Overview

This spec produces **three Markdown documents** that complete the GraviTea Acopio ERP blueprint suite before implementation specs (09-12) begin:

| Sub-spec | Output File | Type |
|----------|-------------|------|
| **08a** | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | New file |
| **08b** | `Docs/Project Blueprint/AI-ML Feature Roadmap.md` | New file |
| **08c** | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | Overwrite stale file |

All three are **blueprint-tier documents** -- design-time references, not code. They contain Mermaid diagrams, tables, XML schema summaries, and configuration references, but zero implementation code (no Python, SQL, or shell).

**Authorship model**: Single author writes each document sequentially. No tmux agent teams or parallel implementation sessions are needed. This is a blueprint spec (01-08), not an implementation spec (09+).

---

## 2. Writing Order

**Recommended sequence: 08a -> 08c -> 08b**

| Order | Sub-spec | Rationale |
|-------|----------|-----------|
| 1st | **08a** (ARCA Grain Integration Guide) | Provides the ARCA service context that 08c references in its external interface requirements (SRS-IF01...) and that 08c's traceability matrix maps WSCPE/WSLPG calls to. Writing 08a first ensures 08c can cite it accurately. |
| 2nd | **08c** (Software Requirements Specification) | Depends on 08a for ARCA interface section cross-references. Independent of 08b. The traceability matrix in 08c requires the REST API Design (spec-06) and PRD (spec-02), both already complete. |
| 3rd | **08b** (AI/ML Feature Roadmap) | Most independent document. References HLD SS12, Roadmap SS7, and the Data Model -- all upstream and already finalized. Does not depend on 08a or 08c content. |

Each document is independently completable -- the recommended order reduces back-patching of cross-references but is not a hard dependency.

---

## 3. Section-by-Section Writing Plan for 08a (ARCA Grain Integration Guide)

### SS1 -- Document Metadata

- **What to write**: Version 1.0 header, status, date, changelog, upstream document list, "How to Read" note explaining ADR citation format and Mermaid notation.
- **Primary source**: Follow the established pattern from HLD SS1 and Roadmap SS1 (metadata table + changelog table + reading guide paragraph).
- **Secondary sources**: None.
- **Key facts that MUST appear**: Version 1.0, upstream dependencies (HLD SS6, ADR v1.0, PRD SS6), branch name `008-acopio-new-docs`, note that this document is the developer reference for ARCA grain web service integration.
- **Estimated effort**: Small.

### SS2 -- ARCA Service Overview

- **What to write**: Hub-and-spoke architecture explanation with a Mermaid diagram showing WSAA as authentication gateway for WSLPG, WSCPE, and WSFEv1. Service catalog table with purpose, phase, production URL, and homologation URL for each service. Authentication prerequisite summary.
- **Primary source**: HLD SS3.2 (external actor descriptions) for architecture overview; HLD SS6 for service catalog.
- **Secondary sources**: RAG `arca_api_specs` collection for exact production/homologation URLs; 08-specify.md Critical Domain Facts for WSLPG URLs.
- **Key facts that MUST appear**: (1) WSAA is the authentication gateway -- all other services require Token+Sign from WSAA. (2) Four services: WSAA, WSLPG, WSCPE, WSFEv1. (3) Production URL for WSLPG: `https://serviciosjava.afip.gob.ar/wslpg/LpgService?wsdl`. (4) Homologation URL for WSLPG: `https://fwshomo.afip.gov.ar/wslpg/LpgService?wsdl`. (5) WSCPE and WSFEv1 production/homologation URLs (research from docs 1.2 and 5.1). (6) Hub-and-spoke Mermaid diagram.
- **Estimated effort**: Medium.

### SS3 -- WSAA Authentication

- **What to write**: Complete TRA generation flow, X.509 certificate signing into CMS envelope, Base64 encoding, LoginCMS SOAP invocation, Token+Sign response structure, Redis caching strategy with 11h TTL, concurrent refresh handling, and a Mermaid sequence diagram. Error handling subsection covering timeout, auth error mid-batch, and certificate expiry.
- **Primary source**: RAG `arca_api_specs` collection -- `Especificacion_Tecnica_WSAA_1.2.2.pdf` for the WSAA technical specification; RAG `arca_dev_guides` collection -- `WSAAmanualDev.pdf` for the developer manual (TRA creation, CMS signing, LoginCMS method, architecture diagram).
- **Secondary sources**: HLD SS3.2 (WSAA actor description -- token lifetime, Redis caching); 08-specify.md Critical Domain Facts (WSAA flow steps, 12h token lifetime, 11h Redis TTL).
- **Key facts that MUST appear**: (1) TRA XML structure with fields. (2) X.509 signing -> CMS envelope -> Base64 encoding. (3) LoginCMS SOAP method invocation and parameters. (4) Token+Sign (TA) response with Token and Sign components. (5) Token lifetime = 12 hours. (6) Redis cache TTL = 11 hours (1-hour safety margin). (7) Concurrent refresh handling pattern. (8) WSAA Mermaid sequence diagram (contributes to the >= 3 diagrams gate). (9) Error handling: timeout, auth error mid-batch, certificate expiry scenarios.
- **Estimated effort**: Large.

### SS4 -- WSLPG -- Grain Settlement (Form 1116-B/C)

- **What to write**: Purpose and regulatory context (RG 3419/2012, RG 3690/2014). Service URLs (production + homologation). `liquidacionAutorizar` method reference with XML field summary. Single grain type constraint (codGrano at XML root). SISA blocking gate with retention tier lookup table. Response parsing and COE extraction. Error codes and handling.
- **Primary source**: RAG `acopio_research` collection -- research 5.1 "WSLPG Technical API Documentation" for SOAP methods catalog, parameter lookup methods, `liquidacionAutorizar` field reference.
- **Secondary sources**: RAG `acopio_research` -- research 8.1 "Grain Types and Quality Parameter Reference Data" for ncespecie/codGrano codes; 08-specify.md Critical Domain Facts for SISA retention tiers (Estado 1/2/3/Non-registered), codGrano single-grain-type constraint (ADR-019), SISA blocking gate (ADR-027).
- **Key facts that MUST appear**: (1) `liquidacionAutorizar` as the core filing method. (2) codGrano at XML root -- single grain type per submission per ADR-019 (Single Form 1116-C per Grain Type). (3) SISA blocking gate: must query producer SISA status before every filing per ADR-027 (SISA-Tier Retention Calculation). (4) Retention tiers: Estado 1 (5% IVA / 0% Ganancias), Estado 2 (8% / 2%), Estado 3 (10.5% / 15%), Non-registered (16% / 30%). (5) COE (Codigo de Operacion Electronico) returned on successful filing. (6) Production/homologation URLs. (7) Parameter lookup methods (tipoGranoConsultar, codigoGradoReferenciaConsultar, etc.) from research 5.1. (8) pyafipws `wslpg.py` reference (reingart/pyafipws on GitHub). (9) RG 3419/2012 and RG 3690/2014 regulatory context.
- **Estimated effort**: Large.

### SS5 -- WSCPE -- CPE Lifecycle

- **What to write**: CPE/CTG overview and regulatory context. State machine diagram (Mermaid) showing Activa -> Arribo -> Descargada -> Confirmada_Definitiva plus Anulada and Rechazada paths. Full method catalog. 5-day Automotor validity window. Offline store-and-forward via PendingOperation queue. Error paths for CPE expiry and offline queue overflow.
- **Primary source**: RAG `acopio_research` collection -- research 1.2 "AFIP Web Service WSCPE Technical Specification" for the complete method catalog (solicitarCPEAutomotor, consultarCPEAutomotor, confirmarArriboCPE, confirmarDescargaCPE, anularCPE, rechazoCPE, consultarRenspa).
- **Secondary sources**: RAG `acopio_research` -- research 1.1 "Carta de Porte Electronica Complete Lifecycle" for state transitions; research 8.2 "CTG Document Structure and State Machine" for confirmation fields (pesoBrutoDescarga, pesoTaraDescarga) and state codes (CF, DD, CN); 08-specify.md Critical Domain Facts for method name discrepancy resolution.
- **Key facts that MUST appear**: (1) CPE state machine: Activa -> Arribo (CF) -> Descargada (DD) -> Confirmada_Definitiva (CN), plus Anulada and Rechazada branches. (2) Method name discrepancy MUST be resolved: HLD says `descargadoDestinoCPE` but research 1.2 (ARCA WSDL) lists `confirmarDescargaCPE` -- resolve against ARCA WSDL, noting the discrepancy. (3) Additional WSCPE methods NOT in HLD that MUST be documented: `solicitarCPEAutomotor`, `consultarCPEAutomotor`, `anularCPE`, `rechazoCPE`, `consultarRenspa`. (4) 5-day Automotor validity window. (5) "Vencida" is a derived condition (elapsed time), not a WSCPE state code. (6) Offline store-and-forward via PendingOperation queue per ADR-030 (Store-and-Forward Queue for ARCA Web Service Calls). (7) Confirmacion Definitiva requires pesoBrutoDescarga and pesoTaraDescarga from destination weighbridge. (8) CPE state machine Mermaid diagram (contributes to >= 3 diagrams gate).
- **Estimated effort**: Large.

### SS6 -- WSFEv1/CAEA -- Electronic Invoicing

- **What to write**: CAE online path via `FECAESolicitar`. CAEA offline path with quincena batch pre-authorization. Legal constraint warning callout: CAEA must be obtained BEFORE the offline period. Rust CAEA batch builder reference (feature 024-rust-arca-batch). Error paths.
- **Primary source**: HLD SS3.2 (WSFEv1 actor description -- CAE/CAEA explanation); 08-specify.md Critical Domain Facts for CAEA constraint details.
- **Secondary sources**: RAG `arca_api_specs` or `arca_dev_guides` for WSFEv1 technical details; ADR-026 (CAEA for Offline Fiscal Operations) for the architectural decision.
- **Key facts that MUST appear**: (1) Online path: `FECAESolicitar` returns a CAE per invoice. (2) Offline path: CAEA (Codigo de Autorizacion Electronico Anticipado) -- quincena (15-day) batch codes obtained before the offline period. (3) Legal constraint: CAEA MUST be obtained before the offline period begins -- no retroactive authorization. This MUST be a warning callout. (4) CAEA quincena codes cannot roll over -- legal constraint is strict. (5) Rust CAEA batch builder: feature 024-rust-arca-batch (serde_json, GIL-released). (6) ADR-026 (CAEA for Offline Fiscal Operations) citation.
- **Estimated effort**: Medium.

### SS7 -- Certificate Management

- **What to write**: Per-service certificate requirement. Certificate provisioning procedure via ARCA portal. Private key storage in Google Cloud Secret Manager. Certificate rotation procedure. Certificate expiry detection and alerting.
- **Primary source**: 08-specify.md Critical Domain Facts for per-service cert requirement and Secret Manager storage; ADR-025 (ARCA Web Service Architecture) for architectural decision.
- **Secondary sources**: RAG `arca_dev_guides` for certificate provisioning steps from WSAA developer manual.
- **Key facts that MUST appear**: (1) Each ARCA service requires a SEPARATE X.509 certificate -- shared certificates are rejected. (2) Private keys stored in Google Cloud Secret Manager exclusively -- never in code, .env, or Docker. (3) Certificate rotation procedure. (4) Certificate expiry detection and alerting strategy.
- **Estimated effort**: Medium.

### SS8 -- Homologation Testing Guide

- **What to write**: Homologation environment overview. Pre-seeded test CUITs and known quirks. Testing checklist per service (WSAA, WSLPG, WSCPE, WSFEv1). Promotion from homologation to production.
- **Primary source**: 08-specify.md Critical Domain Facts for homologation URLs (WSLPG known; WSCPE/WSFEv1 must be researched from docs 1.2 and 5.1); HLD SS6 for any listed testing details.
- **Secondary sources**: RAG `arca_dev_guides` for homologation environment patterns; RAG `acopio_research` for WSCPE/WSFEv1 homologation URLs from research docs.
- **Key facts that MUST appear**: (1) `fwshomo.afip.gov.ar` base URL for homologation (must appear -- contributes to grep gate). (2) Production and homologation URLs for all four services. (3) Pre-seeded test CUITs. (4) Known homologation quirks. (5) Per-service testing checklist. (6) Promotion procedure from homologation to production.
- **Estimated effort**: Medium.

### SS9 -- Open-Source Reference Implementations

- **What to write**: pyafipws overview (reingart/pyafipws) with scope and usability assessment. Other community libraries (py3afipws, django-afip, afip.py/Afip SDK). Adaptation notes for GraviTea context (Django + Rust).
- **Primary source**: 08-specify.md Critical Domain Facts for library list; RAG `acopio_research` -- research 10.1 "Existing Open-Source ARCA Grain Integration Code" for detailed usability assessments.
- **Secondary sources**: RAG `acopio_research` -- research 5.1 references section for pyafipws GitHub links and SistemasAgiles wiki.
- **Key facts that MUST appear**: (1) `pyafipws` (reingart/pyafipws): main open-source Python library, includes `wslpg.py` for grain liquidation. (2) `py3afipws` on PyPI: Python 3 fork. (3) `django-afip` (WhyNotHugo/django-afip): Django-specific, WSFEv1 focused. (4) `afip.py` / Afip SDK (afipsdk.com): commercial alternative. (5) SistemasAgiles wiki: community documentation for LiquidacionPrimariaGranos. (6) Caveats on what is directly usable vs what needs adaptation for GraviTea (Django + Rust context).
- **Estimated effort**: Small.

### SS10 -- ADR Cross-Reference

- **What to write**: Table mapping each ARCA-related ADR to its title, impact on ARCA integration, and the 08a section that references it.
- **Primary source**: ADR v1.0 document (spec-04) for ADR titles; 08-specify.md for the list of required ADRs.
- **Secondary sources**: The content written in SS3-SS8 above (to fill in the section reference column).
- **Key facts that MUST appear**: All seven ARCA-related ADRs must be cited: (1) ADR-019 (Single Form 1116-C per Grain Type). (2) ADR-025 (ARCA Web Service Architecture). (3) ADR-026 (CAEA for Offline Fiscal Operations). (4) ADR-027 (SISA-Tier Retention Calculation). (5) ADR-028 (Offline-First as Base Architecture). (6) ADR-029 (Conflict Resolution Taxonomy). (7) ADR-030 (Store-and-Forward Queue for ARCA Web Service Calls). Minimum 7 citations required to pass the grep gate.
- **Estimated effort**: Small.

### SS11 -- Glossary

- **What to write**: ARCA-specific terms that extend (not duplicate) the PRD glossary. Terms such as TRA, CMS, Token+Sign (TA), COE, CTG, CPE, CAEA, quincena, liquidacion primaria, Form 1116-B/C, codGrano, SISA, homologacion.
- **Primary source**: Terms encountered while writing SS2-SS10 above; PRD SS2.1 glossary for terms to NOT duplicate.
- **Secondary sources**: Research docs 1.1, 1.2, 5.1 via RAG for precise definitions.
- **Key facts that MUST appear**: All ARCA-specific terms used in the document must be defined. No overlap with PRD glossary terms (romaneo, merma, etc. are already defined there -- reference them, do not redefine).
- **Estimated effort**: Small.

---

## 4. Section-by-Section Writing Plan for 08b (AI/ML Feature Roadmap)

### SS1 -- Document Metadata

- **What to write**: Version 1.0 header, status, date, changelog, upstream document list.
- **Primary source**: Follow HLD SS1 / Roadmap SS1 metadata pattern.
- **Secondary sources**: None.
- **Key facts that MUST appear**: Version 1.0, upstream dependencies (HLD SS12, Roadmap SS7, Data Model v1.0, ADR v1.0).
- **Estimated effort**: Small.

### SS2 -- Strategic Context

- **What to write**: Why AI/ML matters for acopio operations. Data advantage explanation (structured from day one via ADR-033). Competitive differentiation (no incumbent has ML features -- AGIS/Algoritmo are VB6/desktop with no analytics).
- **Primary source**: Roadmap SS3.2 for competitive landscape (no competitor has ML); Product Vision SS3 for AI vision; 08-specify.md for ADR-033 data advantage framing.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 for AI/ML applications context and industry trends.
- **Key facts that MUST appear**: (1) ADR-033 (4-layer data strategy) captures training data from day one. (2) No competitor in the acopio market has ML features. (3) AGIS on VB6 -- no data pipeline for analytics. (4) The data advantage compounds: every romaneo adds training examples for merma prediction.
- **Estimated effort**: Small.

### SS3 -- 4-Layer Data Architecture

- **What to write**: Detailed description of each layer with concrete field references from the Data Model (spec-03). Mermaid diagram showing how the four layers feed into ML models.
- **Primary source**: 08-specify.md Critical Domain Facts for the four layers (Layer 1 Operational, Layer 2 Behavioural, Layer 3 Quality History, Layer 4 Physical State/IoT-Ready); Data Model v1.0 (spec-03) for specific entity and field names.
- **Secondary sources**: ADR-033 for the architectural decision rationale; ADR-034 for provenance fields; ADR-035 for the 6 named timestamps.
- **Key facts that MUST appear**: (1) Layer 1 -- Operational Data: all grain fields in real-time, DECIMAL(17,3) precision. (2) Layer 2 -- Behavioural Data: operator_id, laboratorista_id, device_id + 6 named timestamps per romaneo (ts_entrada, ts_pesada_bruta, ts_calado, ts_analisis, ts_descarga, ts_tara) per ADR-035. (3) Layer 3 -- Quality History: QualityAnalysis per (grain_type, campaign, storage_unit) -- longitudinal. (4) Layer 4 -- Physical State / IoT-Ready: StorageUnit.environment_sensor_id nullable FK anchor. (5) ADR-033 citation. (6) ADR-034 (provenance fields on all grain domain models: created_by, device_id). (7) ADR-035 (6 named timestamps on Romaneo). (8) Mermaid diagram showing layers -> ML models. (9) Must have >= 8 mentions of "Layer 1/2/3/4" to pass grep gate.
- **Estimated effort**: Large.

### SS4 -- ML Model Catalog (Roadmap SS7.1 priority order)

- **What to write**: Detailed description of each ML model candidate in Roadmap SS7.1 priority order. For each: description, input features, target variable, minimum training data, estimated data accumulation timeline. Also include HLD SS12.6 informative candidates and deferred computer vision.
- **Primary source**: Roadmap SS7.1 for the priority order (P3-Q1 through P3-Q4); HLD SS12 for model details and informative candidates.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 "AI-ML Applications for Grain Storage Operations" for model architecture details, input features, academic references (LSTM for temperature prediction, SVM for mildew prediction, regression for merma); 08-specify.md Critical Domain Facts for model descriptions.
- **Key facts that MUST appear**: (1) P3-Q1: Predictive merma modelling -- regression on tabular data, highest ROI. Input features: grain_type, humedad at reception, storage_unit, duration, season. Target: actual merma percentage. (2) P3-Q2: Price optimisation signals -- MAT (Mercado a Termino) feed + AccountMovement history time-series. (3) P3-Q3: Storage condition anomaly detection -- IoT sensor readings (temperature, humidity, CO2), threshold-based initially, ML-enhanced later. (4) P3-Q4: Natural language grain position queries (NLQ) -- LLM -> SQL: "Cuanta soja tengo hoy?". (5) HLD SS12.6 informative candidates: silo assignment optimization, weighbridge fraud detection. (6) Deferred: Computer vision grain grading -- requires camera hardware partnership, beyond Phase 3. (7) Must have >= 4 mentions of merma model / price optim / anomaly detection / NLQ to pass grep gate.
- **Estimated effort**: Large.

### SS5 -- Feature Engineering Strategy

- **What to write**: Raw field -> feature transformation logic per model. Temporal aggregation windows (per-campaign, rolling 30-day, per-storage-unit). Cross-entity feature joins (Romaneo x QualityAnalysis x StorageUnit x AccountMovement). Feature storage and serving considerations.
- **Primary source**: Data Model v1.0 (spec-03) for entity relationships and field types; 08-specify.md FR-08B03 requirements.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 for feature engineering patterns in grain storage ML; HLD SS12 for data flow descriptions.
- **Key facts that MUST appear**: (1) Romaneo fields -> merma features: humedad, peso_bruto, peso_neto, grain_type, storage_duration. (2) QualityAnalysis fields -> quality degradation features: humedad, grado_asignado, bonificacion/rebaja. (3) Cross-entity join: Romaneo JOIN QualityAnalysis JOIN StorageUnit for storage condition correlation. (4) Temporal windows: per-campaign for merma trends, rolling 30-day for anomaly baselines. (5) DECIMAL(17,3) precision preserved through feature pipeline.
- **Estimated effort**: Medium.

### SS6 -- Training Data Collection Plan

- **What to write**: Phase 1-2 data accumulation targets. Minimum thresholds per model. Data quality monitoring during accumulation. Data labeling strategy where applicable.
- **Primary source**: Roadmap SS7.4 for Phase 3 trigger conditions (>= 20 customers, >= 10,000 romaneos, AI pipeline review); 08-specify.md FR-08B04 for minimum campaign coverage and operator diversity.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 for training data volume guidance.
- **Key facts that MUST appear**: (1) Minimum romaneo count >= 10,000 (from Roadmap SS7.4). (2) Minimum campaign coverage >= 1 full campana (gruesa or fina). (3) Operator diversity: >= 3 distinct operators for behavioral model validity. (4) Data quality monitoring: null rate tracking per field, outlier detection on weight measurements. (5) Merma model labeling: actual merma is naturally labeled (reception weight vs discharge weight over time).
- **Estimated effort**: Medium.

### SS7 -- Delivery Sequence

- **What to write**: Phase 3 ML delivery order (P3-Q1 through P3-Q4). Phase 3 trigger conditions from Roadmap SS7.4. Deferred capabilities. Mermaid dependency graph showing data readiness -> model training -> deployment.
- **Primary source**: Roadmap SS7.1 for priority order; Roadmap SS7.4 for trigger conditions; 08-specify.md for phase model alignment.
- **Secondary sources**: HLD SS12 for deferred capabilities.
- **Key facts that MUST appear**: (1) **MUST use the Roadmap's 3-phase model** -- ML features are "Phase 3", NOT "Phase 4". (2) Phase 3 trigger conditions: (a) >= 20 paying customers, (b) >= 10,000 romaneos processed in production, (c) AI data pipeline review completed. (3) P3-Q1 through P3-Q4 in Roadmap SS7.1 priority order. (4) Per-model data-readiness triggers beyond the Phase 3 entry gate. (5) Mermaid dependency graph (contributes to >= 2 diagrams for 08b). (6) SC-007 compliance: verify 3-phase model alignment.
- **Estimated effort**: Medium.

### SS8 -- IoT Integration Roadmap

- **What to write**: Target sensors (temperature, humidity, CO2 for silo monitoring). Integration protocols (LoRaWAN, Modbus TCP, MQTT). Data pipeline from sensor -> Django API -> QualityAnalysis enrichment. Connection to the quality degradation prediction model (P3-Q3).
- **Primary source**: 08-specify.md Critical Domain Facts for Layer 4 (StorageUnit.environment_sensor_id anchor); FR-08B06 requirements.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 for IoT sensor types and integration patterns in grain storage; research 3.1 for Modbus protocol context.
- **Key facts that MUST appear**: (1) StorageUnit.environment_sensor_id as the nullable FK anchor for IoT data. (2) Target sensors: temperature, relative humidity, CO2 concentration. (3) Protocol options: LoRaWAN for long-range low-power, Modbus TCP for industrial integration, MQTT for cloud gateway. (4) Data pipeline: sensor -> gateway -> Django REST API -> QualityAnalysis table enrichment. (5) Feed into P3-Q3 anomaly detection model. (6) Must contribute to grep gate: >= 4 mentions of sensor/IoT/LoRa/MQTT/temperature.
- **Estimated effort**: Medium.

### SS9 -- Vector Search and NLQ Strategy

- **What to write**: Qdrant development vs production use case analysis. User-facing semantic search feasibility. Natural Language Querying (NLQ) for operators -- LLM -> SQL translation for grain position queries.
- **Primary source**: 08-specify.md Critical Domain Facts for Qdrant strategy (optional dev container, not required in production for Phases 1-2); FR-08B07 requirements.
- **Secondary sources**: HLD SS12 for NLQ description; Roadmap SS7.1 for P3-Q4 NLQ priority.
- **Key facts that MUST appear**: (1) Qdrant is an optional container for development RAG -- not required in production during Phases 1-2. (2) Production Qdrant deployment evaluated during Phase 3 planning. (3) NLQ (P3-Q4): LLM translates operator natural language ("Cuanta soja tengo hoy?") into SQL against the posicion consolidada view. (4) NLQ feasibility depends on structured schema + few-shot examples, not embedding search.
- **Estimated effort**: Small.

### SS10 -- Infrastructure Requirements

- **What to write**: Model training infrastructure (GPU requirements, storage for training data). Model serving (inference latency targets for real-time vs batch). Feature store considerations. Directional cost estimates.
- **Primary source**: FR-08B requirements; HLD SS12 for infrastructure patterns.
- **Secondary sources**: RAG `acopio_research` -- research 9.1 for infrastructure requirements in grain storage ML.
- **Key facts that MUST appear**: (1) P3-Q1 (merma) and P3-Q2 (price) are tabular models -- GPU optional, CPU training feasible. (2) P3-Q3 (anomaly) is lightweight threshold-based initially. (3) P3-Q4 (NLQ) uses external LLM API -- no local GPU needed. (4) Inference latency: merma prediction < 200ms (real-time during romaneo); price signals can be batch (hourly). (5) Feature store is optional for Phase 3 scale; direct SQL queries sufficient initially.
- **Estimated effort**: Small.

### SS11 -- ADR Cross-Reference

- **What to write**: Table mapping each AI-related ADR to its title, impact on ML strategy, and the 08b section that references it.
- **Primary source**: ADR v1.0 document (spec-04) for ADR titles; 08-specify.md for required ADRs.
- **Secondary sources**: The content written in SS3-SS10 above.
- **Key facts that MUST appear**: All three AI-related ADRs must be cited: (1) ADR-033 (4-Layer Data Strategy). (2) ADR-034 (Provenance Fields on All Grain Domain Models). (3) ADR-035 (6 Named Timestamps on Romaneo). Minimum 3 citations required to pass the grep gate.
- **Estimated effort**: Small.

---

## 5. Section-by-Section Writing Plan for 08c (Software Requirements Specification)

### SS1 -- Document Metadata

- **What to write**: Version 1.0 header, status, date, changelog, upstream document list. Note that this file overwrites a stale SRS written for the old retail ERP vertical.
- **Primary source**: Follow HLD SS1 / Roadmap SS1 metadata pattern.
- **Secondary sources**: None.
- **Key facts that MUST appear**: Version 1.0, note that this is a complete rewrite (old SRS was for general-purpose ERP, not acopio), upstream dependencies (PRD v1.0, Data Model v1.0, REST API Design v1.0, HLD v1.0, 08a).
- **Estimated effort**: Small.

### SS2 -- Introduction

- **What to write**: Purpose (formalize PRD into engineering-level shall-statements). Scope (Phase 1 fully specified; Phase 2 ID-reserved, deferred). Requirement ID scheme explanation (SRS-PPNN). MoSCoW priority classification. Glossary reference to PRD SS2.1.
- **Primary source**: 08-specify.md FR-08C01 for the ID scheme definition; FR-08C02 for shall-statement format.
- **Secondary sources**: PRD SS2.1 for glossary reference.
- **Key facts that MUST appear**: (1) SRS-PPNN scheme where PP = module prefix (RE, CA, AL, CC, LQ, FA, AG, CJ, HW, IF, SE, PF, DA) and NN = sequential number. (2) MoSCoW: Must/Should/Could/Won't. (3) Phase 1 modules fully specified: RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES. (4) Phase 2 modules deferred: LIQUIDACIONES, FACTURACION, AGRONOMIA, CANJE. (5) Each shall-statement has: ID, description, priority, PRD source, impl spec, API endpoint.
- **Estimated effort**: Small.

### SS3 -- System Overview

- **What to write**: System context reference to HLD C4 Level 1 diagram. User roles (balancero, laboratorista, admin, contador, productor). System boundaries.
- **Primary source**: HLD SS3 for system context diagram reference; PRD for user roles.
- **Secondary sources**: 08-specify.md for user role list.
- **Key facts that MUST appear**: (1) Reference to HLD SS3 C4 Level 1 diagram -- not duplicated. (2) User roles: balancero, laboratorista, admin, contador, productor. (3) System boundary: Django API + PostgreSQL + Redis + Rust extensions.
- **Estimated effort**: Small.

### SS4 -- Functional Requirements -- Phase 1

- **What to write**: Formal shall-statements for all four Phase 1 modules. Each requirement as a table row with ID, description (shall-statement), MoSCoW priority, PRD source section, implementation spec assignment (09-12), and API endpoint from REST API Design.
- **Primary source**: PRD SS4.1-SS4.4 for module feature lists to transform into shall-statements; REST API Design v1.0 (spec-06) for endpoint mappings.
- **Secondary sources**: RAG `acopio_research` -- research 8.3 "Romaneo Weighing Ticket" for romaneo workflow steps to inform RECEPCION requirements; research 2.1 "Day-to-Day Operations" for operational context; Data Model v1.0 for entity names.
- **Key facts that MUST appear**:
  - **SS4.1 RECEPCION (SRS-RE01 through SRS-RENN)**: Romaneo creation, CPE arrival confirmation via WSCPE, weighbridge integration (gross/tare/net weight capture), truck queue management. Impl spec: spec-10. The romaneo workflow is: truck arrival -> CPE verification (Activa status, 5-day validity check) -> Confirmacion de Arribo -> weighing (peso bruto) -> sampling/calado -> unloading -> tare weighing (tara) -> peso neto calculation -> Confirmacion Definitiva (overwriting CPE kilograms with exact peso neto from romaneo).
  - **SS4.2 CALIDAD (SRS-CA01 through SRS-CANN)**: Quality analysis (humedad, grado, bonificacion/rebaja), tolerance table application, quality grading per grain type. Impl spec: spec-10 or spec-09.
  - **SS4.3 ALMACENAMIENTO (SRS-AL01 through SRS-ALNN)**: Storage unit management, silo assignment, grain position tracking (posicion consolidada), merma calculation. Impl spec: spec-11.
  - **SS4.4 CUENTAS CORRIENTES (SRS-CC01 through SRS-CCNN)**: Producer current accounts, account movements, balance tracking, campaign-year segregation. Impl spec: spec-12.
  - Must have >= 20 SRS-RE/CA/AL/CC IDs to pass the grep gate.
  - Must have >= 30 "shall" occurrences to pass the grep gate.
- **Estimated effort**: Large (largest section in 08c).

### SS5 -- Functional Requirements -- Phase 2 (Deferred)

- **What to write**: Reserved ID namespaces for Phase 2 modules with stub entries. Each module gets 2-3 placeholder requirements marked as "Deferred" status.
- **Primary source**: PRD SS4.5-SS4.8 for Phase 2 module descriptions; 08-specify.md FR-08C10 for deferred requirements format.
- **Secondary sources**: Roadmap SS5 for Phase 2 scope (specs 13-16).
- **Key facts that MUST appear**: (1) SRS-LQ01... for LIQUIDACIONES. (2) SRS-FA01... for FACTURACION. (3) SRS-AG01... for AGRONOMIA. (4) SRS-CJ01... for CANJE. All marked "Deferred -- to be specified in Phase 2 implementation specs". Must have >= 4 mentions of SRS-LQ/FA/AG/CJ to pass grep gate.
- **Estimated effort**: Small.

### SS6 -- External Interface Requirements

- **What to write**: Three subsections: ARCA SOAP interfaces, weighbridge hardware interfaces, REST API interfaces. Each with SRS-IF or SRS-HW requirement IDs.
- **Primary source**: 08-specify.md Critical Domain Facts for weighbridge hardware details (RS-232, Modbus RTU, ASCII stream, KYASERV); 08a (once written) for ARCA interface cross-reference; REST API Design v1.0 for REST API interface reference.
- **Secondary sources**: RAG `acopio_research` -- research 3.1 "Weighbridge Integration Standards" for protocol details; research 3.2 "Grain Moisture Meters and Lab Equipment" for lab equipment APIs; PRD SS7 for hardware overview.
- **Key facts that MUST appear**:
  - **SS6.1 ARCA SOAP (SRS-IF01...)**: Protocol = SOAP/XML over HTTPS, authentication = WSAA TRA, reference to 08a for detailed guide.
  - **SS6.2 Weighbridge hardware (SRS-HW01...)**: (a) RS-232: 9600 bps default (1200-38400 configurable), 8 data bits, no parity, 1 stop bit, DB-9 male, 15m max cable length. (b) Modbus RTU (Sipel Orion): functions 03h (Read Holding Registers), 06h (Write Single Register), 10h (Write Multiple Registers); RS-232 single-slave or RS-485 multi-slave (1200m max). (c) ASCII stream (GaMa A12): frame delimiters STX/ETX or CR/LF, continuous output, stability detection algorithm. (d) KYASERV: RS-232-to-Ethernet bridge, TCP/IP LAN access. Must have >= 5 mentions of baud/parity/Modbus/RS-232/frame format to pass grep gate.
  - **SS6.3 REST API (SRS-IF10...)**: Reference to REST API Design v1.0 (spec-06) endpoint catalog.
- **Estimated effort**: Large.

### SS7 -- Performance Requirements (SRS-PF01...)

- **What to write**: Formal performance shall-statements with quantified targets derived from PRD SS8.
- **Primary source**: PRD SS8 for performance targets; 08-specify.md FR-08C06 for the specific metrics.
- **Secondary sources**: HLD for architectural performance constraints.
- **Key facts that MUST appear**: (1) SRS-PF01: API response time < 500ms for standard CRUD endpoints. (2) SRS-PF02: Offline sync latency < 30s push/pull cycle. (3) SRS-PF03: Romaneo end-to-end cycle time < 5 minutes (truck on scale to romaneo signed). (4) SRS-PF04: Concurrent user capacity (per-tenant). (5) SRS-PF05: Database query time thresholds. Must contribute to grep gate: >= 4 mentions of ms/second/concurrent/latency.
- **Estimated effort**: Small.

### SS8 -- Security Requirements (SRS-SE01...)

- **What to write**: Formal security shall-statements covering all security mechanisms.
- **Primary source**: PRD SS8 (non-functional requirements -- security); HLD security architecture sections; 08-specify.md FR-08C07.
- **Secondary sources**: ADR v1.0 for security-related ADRs.
- **Key facts that MUST appear**: (1) SRS-SE01: JWT RS256 authentication (algorithm whitelist). (2) SRS-SE02: Tenant isolation via 3-layer defense (application TenantBoundManager + PostgreSQL RLS + IDOR validation). (3) SRS-SE03: AES-256-GCM field-level encryption for PII. (4) SRS-SE04: Argon2 password hashing. (5) SRS-SE05: SSRF validation pipeline (Rust-based URL validation). (6) SRS-SE06: Rate limiting on authentication endpoints.
- **Estimated effort**: Small.

### SS9 -- Data Requirements (SRS-DA01...)

- **What to write**: Formal data shall-statements referencing the Data Model (spec-03).
- **Primary source**: Data Model v1.0 (spec-03) for entity inventory and field specifications; 08-specify.md FR-08C08.
- **Secondary sources**: ADR-012 for ON DELETE behavior rules.
- **Key facts that MUST appear**: (1) SRS-DA01: Entity inventory covering all Phase 1 entities. (2) SRS-DA02: DECIMAL(17,3) precision for all weight and monetary fields. (3) SRS-DA03: Referential integrity rules including ON DELETE behaviors per ADR-012. (4) SRS-DA04: Campaign-year segregation (campana gruesa/fina).
- **Estimated effort**: Small.

### SS10 -- Traceability Matrix

- **What to write**: A comprehensive table mapping: PRD user story -> SRS requirement ID -> implementation spec (09-16) -> REST API endpoint -> test marker.
- **Primary source**: PRD SS4 for user stories; the SRS-PPNN requirements written in SS4 above; REST API Design v1.0 (spec-06) for endpoint paths; testing conventions from CLAUDE.md for test markers.
- **Secondary sources**: Roadmap SS4-SS5 for implementation spec assignments.
- **Key facts that MUST appear**: (1) Every Phase 1 functional requirement (Must priority) has a complete row with zero empty cells. (2) PRD source column references specific PRD section numbers. (3) Impl spec column maps to spec-09, spec-10, spec-11, or spec-12. (4) API endpoint column uses REST API Design paths. (5) Test marker column uses pytest marker convention (@pytest.mark.{module}). (6) Must contribute to grep gate: >= 4 mentions of Traceability / PRD.*SRS / SRS.*spec-09 / SRS.*spec-10.
- **Estimated effort**: Large.

### SS11 -- Constraints and Assumptions

- **What to write**: Regulatory constraints (ARCA compliance, RG 5689/2025, RG 5821/2026). Hardware constraints (weighbridge model diversity, RS-232 cable length, offline environments). Team size assumption (2 developers). Offline assumptions (44% poor connectivity during harvest per INTA/ENACOM survey).
- **Primary source**: Roadmap SS2 for team size and market context; PRD SS6 for regulatory compliance; 08-specify.md for weighbridge hardware constraints.
- **Secondary sources**: HLD for architectural constraints; Roadmap SS3.1 for connectivity survey data.
- **Key facts that MUST appear**: (1) ARCA compliance mandatory -- all fiscal documents must be authorized electronically. (2) Offline-first is a hard requirement, not a nice-to-have. (3) 2-developer team assumption for Phase 1. (4) Weighbridge models vary by plant -- protocol must be configurable.
- **Estimated effort**: Small.

### SS12 -- Appendix: Requirement ID Namespace

- **What to write**: Complete table of reserved ID ranges per module for future expansion.
- **Primary source**: 08-specify.md FR-08C01 for the ID scheme.
- **Secondary sources**: None.
- **Key facts that MUST appear**: (1) RE = Recepcion, CA = Calidad, AL = Almacenamiento, CC = CuentasCorrientes. (2) LQ = Liquidaciones, FA = Facturacion, AG = Agronomia, CJ = Canje. (3) HW = Hardware, IF = Interface, SE = Security, PF = Performance, DA = Data. (4) NN = 01-99 per namespace.
- **Estimated effort**: Small.

---

## 6. Research-to-Section Mapping

| Research Source | 08a Sections | 08b Sections | 08c Sections |
|----------------|-------------|-------------|-------------|
| RAG `arca_api_specs` -- Especificacion Tecnica WSAA 1.2.2 | SS3 (WSAA auth flow, TRA, LoginCMS) | -- | -- |
| RAG `arca_dev_guides` -- WSAAmanualDev | SS3 (TRA creation, CMS signing, architecture), SS7 (cert provisioning), SS8 (homologation) | -- | -- |
| Research 1.1 -- CPE Complete Lifecycle | SS5 (state transitions, validity windows, Anulada/Rechazada paths) | -- | -- |
| Research 1.2 -- WSCPE Technical Specification | SS5 (method catalog, confirmarDescargaCPE discrepancy resolution), SS8 (WSCPE homologation URLs) | -- | SS6.1 (ARCA SOAP interface) |
| Research 1.3 -- Liquidacion Primaria Form 1116 B/C | SS4 (Form 1116-B/C field structure, codGrano constraint) | -- | -- |
| Research 1.4 -- Registro de Operadores SISA | SS4 (SISA retention tiers, withholding regime) | -- | -- |
| Research 5.1 -- WSLPG Technical API Documentation | SS4 (SOAP methods, parameter lookups, XML fields), SS9 (pyafipws references) | -- | SS6.1 (ARCA SOAP interface) |
| Research 8.1 -- Grain Types and Quality Parameter Reference Data | SS4 (ncespecie/codGrano codes) | -- | SS4.2 (quality parameter requirements) |
| Research 8.2 -- CTG Document Structure and State Machine | SS5 (confirmation fields, state codes CF/DD/CN) | -- | -- |
| Research 8.3 -- Romaneo Weighing Ticket Structure | -- | -- | SS4.1 (romaneo workflow steps), SS6.2 (weighbridge interface) |
| Research 9.1 -- AI-ML Applications for Grain Storage | -- | SS2 (strategic context), SS4 (model candidates, academic refs), SS5 (feature engineering patterns), SS6 (training data volumes), SS8 (IoT sensors) | -- |
| Research 10.1 -- Open-Source ARCA Integration Code | SS9 (pyafipws, py3afipws, django-afip, afip.py assessment) | -- | -- |
| Research 2.1 -- Day-to-Day Operations of an Acopiador | -- | -- | SS4.1 (RECEPCION workflow), SS4.4 (cuenta corriente operations) |
| Research 2.2 -- Grain Quality Management Standards | -- | -- | SS4.2 (quality parameters, tolerance tables, bonificacion/rebaja) |
| Research 3.1 -- Weighbridge Integration Standards | -- | SS8 (Modbus TCP protocol context) | SS6.2 (RS-232, Modbus RTU, ASCII stream, KYASERV -- all protocol details) |
| Research 3.2 -- Grain Moisture Meters and Lab Equipment | -- | -- | SS6.2 (lab equipment API interfaces) |
| HLD SS3 (System Context) | SS2 (hub-and-spoke architecture, actor descriptions) | -- | SS3 (C4 Level 1 reference) |
| HLD SS6 (ARCA Integration Architecture) | SS2-SS8 (expanded into endpoint-level detail) | -- | SS6.1 (ARCA interface reference) |
| HLD SS12 (AI/ML Readiness Architecture) | -- | SS3 (4-layer architecture), SS4 (model candidates), SS10 (infrastructure) | -- |
| PRD SS4 (Module Specifications) | -- | -- | SS4 (Phase 1 shall-statements), SS5 (Phase 2 deferred) |
| PRD SS6 (Regulatory Compliance) | SS4 (RG 3419/2012, RG 3690/2014) | -- | SS11 (regulatory constraints) |
| PRD SS7 (Hardware Integration) | -- | -- | SS6.2 (weighbridge interface -- PRD defers to SRS) |
| PRD SS8 (Non-Functional Requirements) | -- | -- | SS7 (performance targets), SS8 (security requirements) |
| REST API Design v1.0 (spec-06) | -- | -- | SS4 (API endpoint column), SS6.3 (REST API interface), SS10 (traceability matrix) |
| Data Model v1.0 (spec-03) | -- | SS3 (field references per layer), SS5 (entity joins) | SS9 (data requirements) |
| ADR v1.0 (spec-04) | SS10 (ADR-019, 025-030 cross-ref) | SS11 (ADR-033, 034, 035 cross-ref) | SS8 (security ADRs), SS9 (ADR-012), SS11 (regulatory ADRs) |
| Roadmap v1.0 (spec-07) | -- | SS2 (competitive context), SS7 (delivery sequence, Phase 3 triggers) | SS11 (team size, timeline) |

---

## 7. Content Guidelines

### Tone and Register

Match the established blueprint document tone visible in the HLD and Roadmap: **technical but accessible**, written for practitioners rather than executives. Use precise language without being terse. Explain architectural constraints with their rationale. Use active voice for requirements ("The system shall..."), descriptive voice for explanations.

### Audience per Document

| Document | Primary Audience | Secondary Audience |
|----------|-----------------|-------------------|
| **08a** | Backend developers implementing ARCA integration (spec-10, spec-14) | QA engineers writing ARCA-related test plans |
| **08b** | Architects and product owners validating AI data strategy | Backend developers understanding why certain fields exist |
| **08c** | QA engineers writing test plans; developers implementing specs 09-12 | Product owner for requirements sign-off |

### Language

- **English** as the primary language for all three documents.
- **Spanish domain terms retained** without translation when they are canonical in the Argentine grain trade: romaneo, merma, liquidacion (primaria), CPE, CTG, campana (gruesa/fina), peso bruto, peso neto, tara, grado asignado, bonificacion, rebaja, posicion consolidada, cuenta corriente, acopiador, acopio, calado, tolva, secadora, celda, balancero, laboratorista, productor, contador (rural).
- **Italicize** Spanish terms on first use in each document; use plain text thereafter.

### Level of Detail

Each document **expands** its upstream source -- it does not repeat it:

- **08a** adds endpoint-level SOAP method details, XML field summaries, and error code tables that HLD SS6 omits.
- **08b** adds ML model architecture, feature engineering specifics, and training data thresholds that HLD SS12 omits.
- **08c** formalizes PRD SS4 product-level feature lists into testable shall-statements with unique IDs, MoSCoW priorities, and traceability chains.

### Formatting Conventions

- **Mermaid diagrams**: Use `graph TD`, `sequenceDiagram`, `stateDiagram-v2`, or `flowchart TD` as appropriate. Enclose in triple-backtick blocks with `mermaid` language tag.
- **Tables**: Use GitHub-Flavored Markdown tables. Align columns with pipes. Use bold for header rows.
- **ADR citations**: Always use the format **ADR-NNN (Title)** -- for example, "ADR-025 (ARCA Web Service Architecture)". Never cite an ADR by number alone.
- **Cross-document references**: Use the format "See 08a SS4 (WSLPG)" or "See PRD SS4.1 (Recepcion Module)".
- **Warning callouts**: Use blockquote with bold prefix: `> **WARNING**: CAEA must be obtained before the offline period begins.`
- **Requirement IDs**: Use monospace: `SRS-RE01`, `SRS-PF03`.

### Constraints

- **No implementation code**: No Python, SQL, or shell code blocks. Mermaid diagrams, abbreviated XML schema summaries, and configuration tables are allowed per FR-031.
- **No TBD/TODO/placeholder markers**: If information is genuinely unavailable (e.g., exact Modbus register addresses vary by scale model), state the constraint explicitly: "Register addresses are model-specific; the driver configuration file maps them per installation."
- **Version targeting**: Where ARCA WSDL versions matter, note the targeted version (e.g., WSLPG v1.24) and include instructions for checking for updates.

---

## 8. Existing Content to Preserve vs Replace

| Document | Action | Details |
|----------|--------|---------|
| **08a** (ARCA Grain Integration Guide) | **Create new file** | No existing version. Write from scratch at `Docs/Project Blueprint/ARCA Grain Integration Guide.md`. |
| **08b** (AI-ML Feature Roadmap) | **Create new file** | No existing version. Write from scratch at `Docs/Project Blueprint/AI-ML Feature Roadmap.md`. |
| **08c** (Software Requirements Specification) | **Overwrite existing file** | A stale SRS exists at `Docs/Project Blueprint/Software Requirements Specification (SRS).md` dated 2026-03-01. It was written for the old general-purpose retail ERP vertical (ferreterias, corralones, PyMEs) and is not applicable to the acopio de granos vertical. **Preserve nothing** -- complete rewrite. |

---

## 9. Checkpoint Gates

Review checkpoints are run after completing each document. All checks use `grep` against the finished document file.

### Gate 1 (after 08a -- ARCA Grain Integration Guide)

Run against `Docs/Project Blueprint/ARCA Grain Integration Guide.md`:

| Check | Command | Expected | Validates |
|-------|---------|----------|-----------|
| ARCA service coverage | `grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1" <file>` | >= 40 | AC-08A01: All four services documented comprehensively |
| Mermaid diagrams | `grep -c '```mermaid' <file>` | >= 3 | AC-08A02: Hub-spoke, WSAA sequence, CPE state machine |
| Homologation URL | `grep -c "fwshomo.afip" <file>` | >= 1 | AC-08A03: Homologation environment documented |
| ADR citations | `grep -c "ADR-019\|ADR-025\|ADR-026\|ADR-027\|ADR-028\|ADR-029\|ADR-030" <file>` | >= 7 | AC-08A04: One per ARCA-related ADR |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder" <file>` | = 0 | AC-08A06: No unresolved placeholders |

**If any check fails**: Fix the deficiency in the relevant section before proceeding to 08c.

### Gate 2 (after 08c -- Software Requirements Specification)

Run against `Docs/Project Blueprint/Software Requirements Specification (SRS).md`:

| Check | Command | Expected | Validates |
|-------|---------|----------|-----------|
| Phase 1 requirement IDs | `grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC" <file>` | >= 20 | AC-08C01: All Phase 1 modules have requirements |
| Shall-statements | `grep -ci "shall" <file>` | >= 30 | AC-08C02: Formal requirement language |
| Weighbridge hardware detail | `grep -c "baud\|parity\|Modbus\|RS-232" <file>` | >= 5 | AC-08C03: Protocol-level detail present |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder" <file>` | = 0 | AC-08C07: No unresolved placeholders |

**If any check fails**: Fix the deficiency before proceeding to 08b.

### Gate 3 (after 08b -- AI/ML Feature Roadmap)

Run against `Docs/Project Blueprint/AI-ML Feature Roadmap.md`:

| Check | Command | Expected | Validates |
|-------|---------|----------|-----------|
| ML model candidates | `grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language" <file>` | >= 4 | AC-08B01: P3-Q1 through P3-Q4 present |
| 4-layer data strategy | `grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4" <file>` | >= 8 | AC-08B02: All layers documented multiple times |
| ADR citations | `grep -c "ADR-033\|ADR-034\|ADR-035" <file>` | >= 3 | AC-08B03: All AI-related ADRs cited |
| No TBD/TODO | `grep -ci "TBD\|TODO\|placeholder" <file>` | = 0 | AC-08B06: No unresolved placeholders |

**If any check fails**: Fix the deficiency before declaring spec-08 complete.

---

## 10. Done Criteria

Spec-08 is complete when ALL of the following are true:

### Document Existence

- [ ] `Docs/Project Blueprint/ARCA Grain Integration Guide.md` exists (08a)
- [ ] `Docs/Project Blueprint/AI-ML Feature Roadmap.md` exists (08b)
- [ ] `Docs/Project Blueprint/Software Requirements Specification (SRS).md` exists and contains acopio content, not stale retail ERP content (08c)

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
- [ ] SC-004: Automated grep checks pass (gates 1-3 above)
- [ ] SC-005: Implementation spec authors (09-12) have complete upstream context
- [ ] SC-006: ADR cross-references verified (08a cites 7 ADRs, 08b cites 3 ADRs)
- [ ] SC-007: 08b uses the Roadmap's 3-phase model (not the HLD's 4-phase model)

### Final Validation

- [ ] Zero TBD/TODO/placeholder markers across all three documents
- [ ] Terminology consistent with Data Model (spec-03) and PRD (spec-02) glossary throughout
- [ ] All Mermaid diagrams render correctly (validated via preview)
- [ ] All cross-document references point to correct section numbers
