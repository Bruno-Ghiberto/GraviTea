# Feature Specification: New ARCA Docs — Blueprint Knowledge Update

**Feature Branch**: `009-new-arca-docs`
**Created**: 2026-03-18
**Status**: Draft
**Input**: Enrich 9 existing blueprint documents with authoritative facts from newly ingested ARCA official PDFs (WSCPE, WSLPG, SIRE, WSCDC, WS Padrón, WSAA cert chain)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ARCA Guide Enrichment with Official Method Catalogs (Priority: P1)

As the implementation team lead, I need the ARCA Grain Integration Guide to contain **authoritative SOAP method names, XML field catalogs, and error codes** drawn from official ARCA developer manuals, so that downstream implementation specs (10–13) can reference exact API signatures without guessing or inferring.

**Why this priority**: This is the primary deliverable — the ARCA Guide is the single reference document for all ARCA integration work. Every implementation spec depends on it. Inaccurate method names or field types here propagate as bugs in code.

**Independent Test**: Can be verified by checking that the ARCA Guide documents all 8 ARCA services/sub-services (WSAA, WSCPE, WSLPG, SIRE, SIRE IVA, WSCDC, WS Padrón A4, WS Constancia Inscripción) with official SOAP method names and at least one field catalog table per service.

**Acceptance Scenarios**:

1. **Given** the current ARCA Guide written during spec-08 with research-layer knowledge, **When** spec-09 enrichment is applied, **Then** every ARCA service section contains authoritative SOAP method names matching official developer manuals.
2. **Given** the known method name discrepancy (`descargadoDestinoCPE` vs `confirmarDescargaCPE`), **When** the enrichment pass completes, **Then** zero instances of the incorrect name remain in any document.
3. **Given** WSCDC was entirely absent from specs 01–08, **When** spec-09 completes, **Then** the ARCA Guide contains a dedicated WSCDC section with lifecycle, SOAP methods, XML fields, and error codes.
4. **Given** SIRE retention calculations were approximate, **When** enrichment is applied, **Then** a retention tier table with exact IVA and Ganancias percentages per SISA category appears in the ARCA Guide.

---

### User Story 2 - WSCDC Integration Across Blueprint Suite (Priority: P2)

As the implementation team lead, I need the **WSCDC grain deposit certificate service** documented across all relevant blueprints (ARCA Guide, Data Model, HLD, ADR, SRS), because this is a mandatory ARCA obligation for acopiadores that was entirely missing from our design suite.

**Why this priority**: WSCDC is a legal obligation — acopiadores must inform ARCA when grain is received at the establishment. WSCDC fires at romaneo reception time (same trigger point as WSCPE confirmation), making Romaneo Core (spec-11) the primary implementation spec that cannot proceed without WSCDC requirements defined in the blueprints. This is a blocking gap.

**Independent Test**: Can be verified by checking that WSCDC appears in at least 5 blueprint documents: ARCA Guide (dedicated section), Data Model (CertificadoDepositoCereal entity), HLD (in integration architecture), ADR (decision record), and SRS (requirements block).

**Acceptance Scenarios**:

1. **Given** WSCDC is not mentioned in any current blueprint document, **When** spec-09 completes, **Then** the ARCA Guide has a new dedicated WSCDC section documenting legal obligation, lifecycle, SOAP methods, XML fields, and error codes.
2. **Given** no CertificadoDepositoCereal entity exists in the Data Model, **When** enrichment is applied, **Then** the Data Model includes this new entity with all WSCDC-mandated fields.
3. **Given** the HLD integration architecture diagram does not include WSCDC, **When** enrichment is applied, **Then** WSCDC appears alongside WSCPE and WSLPG in the ARCA integration flow.
4. **Given** no ADR exists for WSCDC, **When** enrichment is applied, **Then** a new ADR documents the decision to integrate WSCDC at romaneo reception time.

---

### User Story 3 - Cross-Document Method Name Correction (Priority: P3)

As a technical architect reviewing blueprints before implementation, I need all ARCA method names to be **consistent and correct** across all 9 documents, so that no implementation spec inherits an incorrect API reference from a blueprint.

**Why this priority**: The known `descargadoDestinoCPE` vs `confirmarDescargaCPE` discrepancy proves that inaccuracies exist in the current blueprints. Fixing this and ensuring cross-document consistency for all ARCA facts prevents cascading errors across 4 implementation specs.

**Independent Test**: Can be verified by running a text search across all 9 blueprint files for the incorrect method name — zero results expected. Additionally, verifying that SISA retention percentages are identical wherever they appear.

**Acceptance Scenarios**:

1. **Given** the HLD uses `descargadoDestinoCPE` in §6, **When** enrichment is applied, **Then** all instances are replaced with `confirmarDescargaCPE` and no other document contains the incorrect name.
2. **Given** SISA retention percentages appear in ARCA Guide, ADR-027, and SRS, **When** enrichment is applied, **Then** the same IVA% and Ganancias% values appear in all three documents.
3. **Given** ADR-027 is mislabelled, **When** enrichment is applied, **Then** ADR-027 label reads "SISA-Tier Retention Calculation at WSLPG Filing Time".

---

### User Story 4 - SIRE Retention and WS Padrón Documentation (Priority: P4)

As the producer accounts module designer, I need **SIRE retention SOAP methods, batch processing format, and WS Padrón SISA lookup** fully documented, so that the Producer Accounts spec (spec-13) can define retention workflows with exact API references.

**Why this priority**: Producer Accounts (spec-13) is the most ARCA-dependent implementation spec. It needs WSLPG field precision (Form 1116 B/C), SIRE retention calculation mechanics, and WS Padrón SISA tier determination. All three services must be precisely documented before spec-13 can be designed.

**Independent Test**: Can be verified by checking that SIRE and WS Padrón each have dedicated documentation with SOAP method names and response field catalogs, and that the SRS contains requirements for both services.

**Acceptance Scenarios**:

1. **Given** SIRE documentation is approximate, **When** enrichment is applied, **Then** ARCA Guide §7 contains SIRE SOAP method names (emitirRetencion and at least one other) and a batch lote import format description.
2. **Given** WS Padrón is not documented in the ARCA Guide, **When** enrichment is applied, **Then** a new §9 documents `getPersona(CUIT)` method with a response field catalog and the SISA validation workflow.
3. **Given** no SISA validation proxy endpoint exists in the REST API Design, **When** enrichment is applied, **Then** a new endpoint is documented for producer SISA status lookup at romaneo time.

---

### User Story 5 - WSAA Certificate Chain and TLS Documentation (Priority: P5)

As the security architect, I need the **WSAA certificate lifecycle (production vs homologación chains), ADMINREL delegation, and TLS protocol requirements** precisely documented, so that the multi-tenant certificate management architecture is built correctly from the start.

**Why this priority**: Certificate management is a foundational security concern. Incorrect certificate chain details or missed TLS requirements could block ARCA production access for all tenants. This is lower priority only because the information is partially present — it needs enrichment, not creation from scratch.

**Independent Test**: Can be verified by checking that ARCA Guide §3 and the HLD security section contain exact CA names, validity dates, CSR DN field requirements, and TLS minimum version.

**Acceptance Scenarios**:

1. **Given** approximate cert chain info in the current docs, **When** enrichment is applied, **Then** ARCA Guide §3 lists production cert chain (AFIPRootCA2 → Computadores) and homologación chain (AC_Raiz_Homo → ComputadoresTest) with exact validity dates.
2. **Given** TLS requirements are not documented, **When** enrichment is applied, **Then** the HLD security section specifies the minimum TLS version required by ARCA for production connections.
3. **Given** ADMINREL delegation is mentioned but not detailed, **When** enrichment is applied, **Then** the ARCA Guide describes the DelegarWS workflow for multi-tenant certificate management.

---

### Edge Cases

- What happens if a RAG query returns no relevant results for a specific ARCA service method? Fallback to direct PDF read of the official developer manual (last resort, documented in NF-0906).
- What happens if an ARCA official manual contradicts a design decision in an existing ADR? The official manual takes precedence; the ADR is updated with a note explaining the correction source.
- What happens if WSCDC legal obligation applies only to acopiadores above a certain storage threshold? Document the threshold found in the manual; if the threshold is not specified, note "applies to all registered acopiadores" and verify via RAG.
- What happens if a method name differs between the WSDL and the developer manual text? The WSDL is authoritative for method names; the manual text is authoritative for field descriptions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The ARCA Grain Integration Guide MUST contain authoritative SOAP method names for all 8 ARCA services/sub-services (WSAA, WSCPE, WSLPG, SIRE, SIRE IVA, WSCDC, WS Padrón A4, WS Constancia Inscripción).
- **FR-002**: The ARCA Guide WSCPE section MUST include the complete CPE state machine with all states and valid transitions, an XML field catalog with field names/types/lengths, and an error code table.
- **FR-003**: All instances of `descargadoDestinoCPE` MUST be replaced with `confirmarDescargaCPE` across all 9 blueprint documents.
- **FR-004**: The ARCA Guide WSLPG section MUST include Form 1116-B and Form 1116-C XML field tables (name, type, length, required), a retention calculation table with SISA tier percentages, and an error code table.
- **FR-005**: WSCDC MUST be documented as a new service in the following 5 mandatory blueprint documents: ARCA Guide (dedicated section), Data Model (new entity), HLD (integration architecture), ADR (decision record), SRS (requirement block). Updates to Roadmap, PRD, and Product Vision are optional enhancements; their absence does not constitute a failure of FR-005 or SC-003.
- **FR-006**: The ARCA Guide MUST include a dedicated SIRE section documenting SOAP methods (general SIRE and SIRE IVA separately), batch lote import format, and retention tier table.
- **FR-007**: The ARCA Guide MUST include a dedicated WS Padrón section documenting `getPersona(CUIT)` method, full response field catalog, and the SISA validation workflow used at romaneo time.
- **FR-008**: Existing ADRs (ADR-007 WSAA, ADR-018 WSCPE, ADR-027 SIRE) MUST be enriched with authoritative details from official manuals, and new ADRs MUST be added for WSCDC and WS Padrón.
- **FR-009**: All ARCA-related SRS requirements MUST reference specific service names and methods (not generic "ARCA integration"), and new requirements MUST be added for WSCDC and WS Padrón.
- **FR-010**: A cross-service error code catalog MUST be compiled in the ARCA Guide for at least 3 ARCA services (WSCPE, WSLPG, and at least one of SIRE/WSCDC/WSAA).
- **FR-011**: The ARCA Guide and HLD MUST document WSAA certificate chains (production and homologación) with exact CA names and validity dates, CSR DN field requirements, and ADMINREL delegation workflow.
- **FR-012**: HLD and/or ARCA Guide MUST document the minimum TLS version required by ARCA for production connections.
- **FR-013**: The REST API Design MUST include new endpoints for WSCDC proxy operations and SISA producer validation.
- **FR-014**: The Data Model MUST include a new CertificadoDepositoCereal entity with all WSCDC-mandated fields.
- **FR-015**: All ARCA-related TBD, TODO, or "approximate" markers across all 9 documents MUST be resolved.
- **FR-016**: Non-ARCA content across all 9 documents MUST remain unchanged (scope is strictly additive/corrective for ARCA sections only).

### Key Entities

- **ARCA Web Services**: The 8 services/sub-services that GraviTea integrates with — WSAA (authentication), WSCPE (grain movement), WSLPG (grain settlement), SIRE (retention general), SIRE IVA (IVA retention), WSCDC (deposit certificate), WS Padrón A4 (CUIT lookup), WS Constancia Inscripción (SISA certificate).
- **Blueprint Documents**: The 9 existing documents in `Docs/Project Blueprint/` that require ARCA enrichment, ordered by change volume (ARCA Guide > SRS > HLD > ADR > REST API > Data Model > Roadmap > PRD > Vision).
- **CertificadoDepositoCereal**: New data entity representing the WSCDC grain deposit certificate — tracks grain species, kg received, humidity, establishment, and deposit certificate lifecycle.
- **SISA Registration**: The fiscal registry that determines a producer's retention tier (IVA and Ganancias percentages) used at WSLPG liquidation time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ARCA Grain Integration Guide documents 8 or more ARCA services/sub-services, each with at least one official SOAP method name documented.
- **SC-002**: Zero instances of the incorrect method name `descargadoDestinoCPE` remain across all 9 blueprint documents (verified by text search).
- **SC-003**: WSCDC appears in at least 5 blueprint documents (ARCA Guide, Data Model, HLD, ADR, SRS), each with substantive content defined as: at minimum one requirement ID or entity field definition accompanied by a brief description of 1–3 sentences (a bare mention without a traceable artifact does not qualify).
- **SC-004**: Zero TBD, TODO, or "approximate" markers remain in any ARCA-related section across all 9 documents.
- **SC-005**: Error code tables are present for at least 3 ARCA services in the ARCA Guide.
- **SC-006**: TLS minimum version for ARCA production connections is documented in HLD or ARCA Guide.
- **SC-007**: SISA retention percentages (IVA% and Ganancias% per tier) are identical in every document where they appear (ARCA Guide, ADR-027, SRS).
- **SC-008**: Non-ARCA content across all 9 documents shows no substantive changes (structural/whitespace-only is acceptable).
- **SC-009**: ADR-027 label reads "SISA-Tier Retention Calculation at WSLPG Filing Time" (exact match).
- **SC-010**: ARCA Guide §3 and the HLD security section contain production and homologación certificate chain CA names with validity date ranges.
- **SC-011**: REST API Design contains at least 2 new endpoints: one for WSCDC proxy operations and one for SISA producer validation.

## Clarifications

### Session 2026-03-18

- Q: What is the minimum content threshold that counts as "substantive" WSCDC content in non-primary docs (SC-003)? → A: At minimum one requirement ID or entity field definition accompanied by a brief description of 1–3 sentences; a bare mention without a traceable artifact does not qualify.
- Q: Which implementation spec is primarily unblocked by WSCDC documentation — spec-11 (Romaneo Core) or spec-12 (Storage & Position)? → A: Spec-11 (Romaneo Core) — WSCDC fires at romaneo reception time, concurrent with WSCPE confirmation; spec-12 references WSCDC certificates only indirectly.
- Q: Are Roadmap, PRD, and Product Vision required for the FR-005 five-document WSCDC count, or optional? → A: Optional — the five mandatory docs (ARCA Guide, Data Model, HLD, ADR, SRS) fully satisfy FR-005; Roadmap/PRD/Vision are best-effort enhancements that do not gate completion.

## Assumptions

- **A-001**: All official ARCA PDFs have been successfully ingested into the Qdrant RAG system (`arca_api_specs`, `arca_dev_guides`, `arca_setup_certs` collections). If a RAG query returns empty, the ingestion script must be re-run before proceeding.
- **A-002**: The Qdrant and Ollama services are running locally and accessible at their configured ports (Qdrant at 6333, Ollama at 11434).
- **A-003**: The WSDL is authoritative for SOAP method names when a conflict exists between the WSDL and developer manual text.
- **A-004**: This spec does not create new blueprint documents — it enriches existing ones. New sections within existing documents are in scope; new standalone documents are not.
- **A-005**: The spec-08 session finding that `confirmarDescargaCPE` is the correct method name (per WSDL) is trusted and will be verified via RAG during execution.
- **A-006**: WSCDC applies to all registered acopiadores (no minimum storage threshold exemption assumed unless RAG evidence shows otherwise).
- **A-007**: All 9 blueprint documents preserve their current heading hierarchy and writing style. ARCA updates are enrichments, not rewrites.

## Dependencies

- **Depends on**: Specs 01–08 (all complete), ARCA PDF ingestion into Qdrant RAG system (complete).
- **Blocks**: Spec-10 (Grain Reference Data), Spec-11 (Romaneo Core — primary WSCDC dependency, fires at romaneo reception), Spec-12 (Storage & Position — references WSCDC certificates indirectly), Spec-13 (Producer Accounts) — all implementation specs depend on enriched ARCA knowledge.
