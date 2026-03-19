# Feature Specification: Acopio New Blueprint Documents (08a/08b/08c)

**Feature Branch**: `008-acopio-new-docs`
**Created**: 2026-03-18
**Status**: Draft
**Input**: Produce three new blueprint documents that complete the GraviTea Acopio ERP blueprint suite before implementation specs (09-12) begin: 08a ARCA Grain Integration Guide, 08b AI/ML Feature Roadmap, 08c Software Requirements Specification (SRS).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Developer implements ARCA grain web service integration (Priority: P1)

A backend developer is assigned spec-10 (Romaneo Core) or spec-14 (WSLPG Integration). They need to call WSCPE to confirm truck arrival and unloading, and WSLPG to file grain settlements. Today this information is scattered across the HLD §6 (architecture-level) and 12+ research documents — no single developer reference exists.

The developer opens **08a (ARCA Grain Integration Guide)** and finds: the WSAA authentication flow with a sequence diagram, the exact WSLPG `liquidacionAutorizar` request fields, the WSCPE CPE lifecycle state machine, WSFEv1/CAEA offline paths, certificate management procedures, homologation testing URLs, error handling tables, and pyafipws reference code pointers.

**Why this priority**: Without 08a, every developer writing ARCA integration code must independently research SOAP endpoints, XML schemas, and error codes from raw ARCA PDFs — the single highest source of rework and bugs in the implementation phase.

**Independent Test**: A developer unfamiliar with ARCA can read 08a alone and correctly describe how to authenticate via WSAA, file a grain settlement via WSLPG, and confirm a CPE arrival via WSCPE — without consulting any other document.

**Acceptance Scenarios**:

1. **Given** a developer opens 08a, **When** they search for WSAA authentication, **Then** they find a complete TRA→CMS→LoginCMS→Token+Sign flow with a Mermaid sequence diagram and all parameter names.
2. **Given** a developer opens 08a, **When** they need WSLPG field details, **Then** they find the `liquidacionAutorizar` XML field reference, the codGrano single-grain-type constraint (ADR-019), and the SISA blocking gate (ADR-027).
3. **Given** a developer opens 08a, **When** they need WSCPE lifecycle information, **Then** they find a state machine diagram (Activa→Arribo→Descargada→Confirmada_Definitiva) with method names, parameters, and the 5-day validity window.
4. **Given** a developer opens 08a, **When** they need to test against ARCA, **Then** they find production and homologation URLs for all four services, test CUITs, and a testing checklist.
5. **Given** a developer opens 08a, **When** they look for error handling guidance, **Then** they find a consolidated error table covering all four ARCA services with failure modes, retry strategies, and operator actions.

---

### User Story 2 — QA engineer traces requirements to implementation specs (Priority: P1)

A QA engineer is writing test plans for spec-09 through spec-12. They need formal, testable requirements with unique IDs that trace back to PRD user stories and forward to API endpoints and test markers. Today the PRD has product-level user stories but no engineering-level shall-statements, and there is no traceability matrix.

The QA engineer opens **08c (Software Requirements Specification)** and finds: shall-statements with SRS-PPNN IDs for all Phase 1 modules (RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES), MoSCoW priorities, PRD source references, implementation spec assignments, and a traceability matrix mapping PRD→SRS→spec→API→test marker.

**Why this priority**: Equal to P1 because without 08c, implementation specs (09-12) have no formal requirements to implement against, QA has no acceptance criteria to test, and there is no audit trail from PRD to code.

**Independent Test**: A QA engineer can read 08c alone and produce a test plan for the RECEPCION module that covers every Must-priority requirement with traceable test cases.

**Acceptance Scenarios**:

1. **Given** a QA engineer opens 08c, **When** they search for RECEPCION requirements, **Then** they find shall-statements with SRS-RE01 through SRS-RENN IDs, each with priority, PRD source, and implementation spec assignment.
2. **Given** a QA engineer opens 08c, **When** they need interface specifications, **Then** they find weighbridge hardware details (baud rates, Modbus function codes, ASCII frame format) and ARCA SOAP interface specs.
3. **Given** a QA engineer opens 08c, **When** they need the traceability matrix, **Then** they find a table mapping PRD user story → SRS requirement → implementation spec → REST API endpoint → test marker.
4. **Given** a QA engineer opens 08c, **When** they check performance requirements, **Then** they find quantified targets: API response time, sync latency, romaneo cycle time, concurrent user capacity.
5. **Given** a QA engineer opens 08c, **When** they check Phase 2 coverage, **Then** they find deferred requirement ID namespaces (SRS-LQ, SRS-FA, SRS-AG, SRS-CJ) reserved but not fully specified.

---

### User Story 3 — Architect validates AI/ML data readiness before Phase 3 (Priority: P2)

An architect or product owner needs to understand what ML capabilities will be available in Phase 3, what data must be captured during Phases 1-2 to enable them, and when each ML feature becomes viable. Today the AI strategy is split between HLD §12 (architecture) and Roadmap §7 (timeline) with no unified feature-level plan.

The architect opens **08b (AI/ML Feature Roadmap)** and finds: the 4-layer data architecture mapped to concrete Data Model fields, ML model candidates in Roadmap §7.1 priority order (merma prediction, price optimization, anomaly detection, NLQ), training data accumulation targets, Phase 3 trigger conditions, IoT integration path, and vector search strategy.

**Why this priority**: 08b justifies the ADR-033/034/035 schema decisions already baked into the Data Model. If a future schema migration removes a field that 08b identifies as ML-critical, the architect needs this document to defend the schema.

**Independent Test**: An architect can read 08b alone and answer: "What minimum data volume is needed before we can train the merma prediction model?", "What Phase 3 trigger conditions must be met?", and "Which fields from the Romaneo entity feed into which ML models?"

**Acceptance Scenarios**:

1. **Given** an architect opens 08b, **When** they look for the data architecture, **Then** they find all 4 layers described with concrete field references from the Data Model (spec-03).
2. **Given** an architect opens 08b, **When** they check ML model candidates, **Then** they find P3-Q1 through P3-Q4 in the correct Roadmap §7.1 priority order, plus HLD §12.6 informative candidates and the deferred computer vision item.
3. **Given** an architect opens 08b, **When** they check Phase 3 readiness, **Then** they find three trigger conditions (≥20 customers, ≥10,000 romaneos, AI pipeline review) and per-model data-readiness thresholds.
4. **Given** an architect opens 08b, **When** they look for IoT details, **Then** they find target sensors, integration protocols, and the data pipeline from sensor to ML model.

---

### User Story 4 — Product owner validates blueprint completeness before implementation kickoff (Priority: P2)

A product owner needs to confirm that all prerequisite documentation is complete before authorizing the implementation phase (specs 09-12). They review the three new documents to verify: ARCA integration is fully documented (08a), AI data strategy is justified (08b), and all Phase 1 requirements have formal IDs and traceability (08c).

**Why this priority**: Gate-keeping function — ensures no implementation spec starts without its upstream references being complete.

**Independent Test**: The product owner can review all three documents and confirm that every PRD module has SRS coverage, every ARCA service has a developer reference, and the AI strategy has concrete data-readiness triggers.

**Acceptance Scenarios**:

1. **Given** a product owner reviews all three documents, **When** they check cross-references, **Then** 08a cites ADR-019/025-030 correctly, 08b cites ADR-033-035 correctly, and 08c traces every Phase 1 requirement to its PRD source.
2. **Given** a product owner reviews all three documents, **When** they search for unresolved placeholders, **Then** they find zero TBD/TODO/placeholder markers in any document.
3. **Given** a product owner reviews all three documents, **When** they check terminology, **Then** all three use canonical terms from the Data Model and PRD glossary consistently.

---

### Edge Cases

- What happens when ARCA changes a WSDL version (e.g., WSLPG v1.25)? — 08a includes a version reference and notes that the guide targets a specific WSDL version, with instructions for checking updates.
- What happens when a WSCPE method name in the HLD contradicts the actual ARCA WSDL? — 08a resolves the discrepancy (HLD says `descargadoDestinoCPE`, research says `confirmarDescargaCPE`) against official ARCA documentation and notes the resolution.
- What happens when Phase 2 modules need their requirements specified later? — 08c reserves the SRS-LQ/FA/AG/CJ ID namespaces with stub entries; future specs populate them without renumbering.
- What happens when an ML model candidate is removed from the roadmap? — 08b marks it as "Deferred" or "Removed" rather than deleting, preserving the decision history.
- What happens when PRD or HLD is updated after 08c is written? — The Dependencies section notes that `/sc:improve` must be re-run on the context file, and 08c must be re-validated against the updated upstream.

## Requirements *(mandatory)*

### Functional Requirements

**Sub-Deliverable A: ARCA Grain Integration Guide (08a)**

- **FR-001**: The guide MUST document the complete WSAA authentication flow (TRA→X.509 signing→CMS→LoginCMS→Token+Sign) with a sequence diagram, parameter names, token lifetime, and Redis caching strategy.
- **FR-002**: The guide MUST document WSLPG `liquidacionAutorizar`: XML fields, codGrano single-grain-type constraint (ADR-019), SISA blocking gate (ADR-027), COE extraction, and error codes.
- **FR-003**: The guide MUST document the WSCPE CPE lifecycle (Activa→Arribo→Descargada→Confirmada_Definitiva): each method, parameters, 5-day Automotor validity, offline store-and-forward (ADR-030).
- **FR-004**: The guide MUST document WSFEv1 CAE (online) and CAEA (offline quincena batch) paths, with a warning callout on the CAEA legal constraint.
- **FR-005**: The guide MUST document per-service certificate management: separate X.509 certs, Secret Manager storage, rotation, and expiry error handling.
- **FR-006**: The guide MUST include homologation testing: URLs for all four services (production + homologation), test CUITs, known quirks, testing checklist.
- **FR-007**: The guide MUST include a consolidated error handling table covering all four ARCA services.
- **FR-008**: The guide MUST reference pyafipws and other open-source ARCA integration code with usability caveats.
- **FR-009**: The guide MUST cite all ARCA-related ADRs: ADR-019, ADR-025 through ADR-030.

**Sub-Deliverable B: AI/ML Feature Roadmap (08b)**

- **FR-010**: The document MUST describe the 4-layer data architecture (ADR-033) with concrete field references from the Data Model.
- **FR-011**: The document MUST catalog ML model candidates in Roadmap §7.1 priority order: P3-Q1 (merma), P3-Q2 (price), P3-Q3 (anomaly), P3-Q4 (NLQ), plus HLD informative candidates and deferred computer vision.
- **FR-012**: The document MUST describe feature engineering: raw fields→features, transformation logic, temporal windows, cross-entity joins.
- **FR-013**: The document MUST specify training data collection requirements during Phases 1-2: minimum romaneo count (≥10,000), campaign coverage (≥1 full), operator diversity.
- **FR-014**: The document MUST define Phase 3 ML delivery sequence (P3-Q1 through P3-Q4) with trigger conditions (≥20 customers, ≥10,000 romaneos, AI pipeline review).
- **FR-015**: The document MUST describe IoT integration path for Layer 4: target sensors, protocols, data pipeline to ML models.
- **FR-016**: The document MUST describe Qdrant/vector search strategy: development vs production use cases, NLQ feasibility.

**Sub-Deliverable C: Software Requirements Specification (08c)**

- **FR-017**: The SRS MUST use requirement ID scheme SRS-PPNN (PP = module prefix, NN = sequential number).
- **FR-018**: The SRS MUST contain formal shall-statements for all Phase 1 modules (RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES) with unique IDs, MoSCoW priority, PRD source, and implementation spec traceability.
- **FR-019**: The SRS MUST specify ARCA SOAP external interface requirements with reference to 08a.
- **FR-020**: The SRS MUST specify weighbridge hardware interface requirements at protocol level: RS-232 parameters, Modbus RTU function codes, ASCII stream format, KYASERV TCP/IP framing.
- **FR-021**: The SRS MUST trace each functional requirement to its REST API endpoint(s) from spec-06.
- **FR-022**: The SRS MUST formalize performance targets from PRD §8: API response time (<500ms), sync latency (<30s), romaneo cycle time (<5 min), concurrent user capacity.
- **FR-023**: The SRS MUST formalize security requirements: JWT RS256, tenant isolation (3-layer defense), AES-256-GCM encryption, Argon2 hashing, SSRF validation, rate limiting.
- **FR-024**: The SRS MUST specify data requirements referencing the Data Model: entity inventory, DECIMAL(17,3) precisions, ON DELETE behaviors (ADR-012), campaign-year segregation.
- **FR-025**: The SRS MUST include a traceability matrix: PRD user story → SRS requirement → implementation spec → REST API endpoint → test marker.
- **FR-026**: The SRS MUST include Phase 2 deferred modules (LIQUIDACIONES, FACTURACION, AGRONOMIA, CANJE) with reserved ID namespaces.

**Cross-Cutting Requirements**

- **FR-027**: All three documents MUST expand on their upstream sources — not copy-paste.
- **FR-028**: All three documents MUST contain zero TBD/TODO/placeholder markers.
- **FR-029**: All three documents MUST use canonical terminology from the Data Model and PRD glossary.
- **FR-030**: All three documents MUST cite ADRs using the format "ADR-NNN (Title)".
- **FR-031**: No document may contain implementation code (Python, SQL, shell). Mermaid diagrams, abbreviated XML schema summaries, and configuration tables are allowed.

### Key Entities

- **Blueprint Document**: A Markdown file in `Docs/Project Blueprint/` that serves as a design-time reference. Key attributes: title, version, status (Draft/Review/Approved), upstream dependencies, downstream consumers.
- **Requirement (SRS)**: A formal shall-statement with unique ID (SRS-PPNN), description, MoSCoW priority, PRD source, implementation spec assignment, and API endpoint mapping. Lives exclusively in 08c.
- **ARCA Web Service**: An external SOAP service (WSAA, WSLPG, WSCPE, WSFEv1) documented in 08a with: service name, purpose, production URL, homologation URL, authentication method, key methods, error codes.
- **ML Model Candidate**: A planned machine learning capability documented in 08b with: name, input features, target variable, minimum training data, Roadmap priority, data-readiness trigger.
- **Traceability Link**: A mapping chain (PRD story → SRS-ID → impl spec → API endpoint → test marker) that ensures every requirement is traceable from business need to test verification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer unfamiliar with ARCA can read 08a and correctly describe the authentication flow, WSLPG filing process, and WSCPE lifecycle within 30 minutes — without consulting any other document.
- **SC-002**: 100% of Phase 1 PRD user stories (RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES) have at least one corresponding SRS requirement with a unique ID in 08c.
- **SC-003**: The 08c traceability matrix covers every Phase 1 functional requirement, with each row containing: PRD source, SRS-ID, implementation spec (09-12), API endpoint, and test marker — zero empty cells in Must-priority rows.
- **SC-004**: All three documents pass automated acceptance criteria validation: grep-based checks confirm ARCA service coverage (≥40 mentions in 08a), ML model coverage (≥4 candidates in 08b), requirement IDs (≥20 SRS-XX IDs in 08c), and zero TBD/TODO markers across all three.
- **SC-005**: Implementation spec authors (09-12) can begin work without requesting additional upstream documentation — 08a/08b/08c together with existing blueprints provide complete context.
- **SC-006**: All ADR cross-references are verified: 08a cites ADR-019/025-030 (7 ADRs), 08b cites ADR-033-035 (3 ADRs), 08c cites relevant ADRs per module.
- **SC-007**: 08b correctly uses the Roadmap's 3-phase model (not the HLD's 4-phase model) and references Phase 3 trigger conditions from Roadmap §7.4.
