# Plan Context: Spec-09 — New ARCA Docs Blueprint Knowledge Update

> **For**: `/speckit.plan "Read @Docs/PROMPTS/spec-09-New-ARCA-Docs/09-plan.md"`
> **Produces**: `specs/009-new-arca-docs/plan.md`
> **Spec type**: Blueprint Update (single-author, document enrichment — NOT a code implementation)

---

## What `/speckit.plan` Must Produce

`specs/009-new-arca-docs/plan.md` is the **execution playbook** for a human or AI agent that will:
1. Query the Qdrant RAG system with targeted queries
2. Extract authoritative ARCA facts from query results
3. Edit 9 existing blueprint documents in priority order
4. Verify each document's success criteria before moving to the next

The plan MUST be structured as a **section-by-section document update guide** — not a software architecture plan, not an agent team orchestration plan, not a Gantt chart. It is a precise editorial enrichment plan.

---

## Spec Inputs Summary

Read `specs/009-new-arca-docs/spec.md` before generating the plan. Key parameters:

| Parameter | Value |
|-----------|-------|
| Documents to update | 9 (all in `Docs/Project Blueprint/`) |
| New document sections | 3+ new sections in ARCA Guide (SIRE, WSCDC, WS Padrón); 2 new ADRs |
| New entities | `CertificadoDepositoCereal` in Data Model |
| New API endpoints | WSCDC proxy + SISA validation in REST API Design |
| Method name corrections | 4 occurrences of `descargadoDestinoCPE` → `confirmarDescargaCPE` in HLD |
| ADR label fix | ADR-027: "LPG Filing Time" → "WSLPG Filing Time" |
| Success criteria | 11 (SC-001 through SC-011 in spec.md) |

---

## Document Execution Order

Execute documents in this exact priority sequence. Do NOT reorder.

| Step | Document | Priority | Primary Change Type |
|------|----------|----------|---------------------|
| 1 | ARCA Grain Integration Guide | P1 — blocks all others | New sections + enrichment |
| 2 | Software Requirements Specification (SRS) | P1 | Add WSCDC + WS Padrón requirements |
| 3 | High-Level Design (HLD) | P2 | Method name fix + WSCDC in architecture |
| 4 | Architecture Decision Records (ADR) | P2 | 2 new ADRs + 3 enrichments + label fix |
| 5 | REST API Design | P3 | 2 new endpoints |
| 6 | Data Model & Domain Model | P3 | New `CertificadoDepositoCereal` entity |
| 7 | Roadmap | Optional | WSCDC mention if scope allows |
| 8 | PRD | Optional | WSCDC mention if scope allows |
| 9 | Product Vision & Scope | Optional | WSCDC mention if scope allows |

---

## RAG Query Infrastructure

All domain facts MUST come from RAG queries. Never fabricate ARCA field names, method names, error codes, or CA certificate names.

### How to Run Queries

```bash
# Single query (5 results)
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY TEXT' -l 5

# Collection-specific query
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY TEXT' -c arca_dev_guides -l 5

# Broader result set for catalogs
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY TEXT' -l 10
```

### RAG Collections Available

| Collection | Contents |
|------------|----------|
| `arca_dev_guides` | Developer manuals: WSCDC v4, WSLPG v1.24, WSCPE, SIRE, SIRE IVA v1.0.0, WSAA |
| `arca_api_specs` | Technical specs: WS Padrón A4 v1.3, WS Constancia Inscripción, SIRE lote spec |
| `arca_setup_certs` | Certificate procedures: production chain, homologación chain, ADMINREL delegation, TLS migration schedule |
| `acopio_research` | Grain domain research (secondary — use for business context only) |

### Critical RAG Query Bank

Include ALL of these queries in the plan, grouped by document section. Agents must run each query and extract relevant facts before editing.

**WSAA Certificate Chain & TLS (for ARCA Guide §3 + HLD security section)**:
```
'WSAA production certificate chain AFIPRootCA CA authority validity'
'WSAA homologacion test certificate chain AC Raiz authority'
'TLS version minimum ARCA web services SOAP production requirement'
'ADMINREL DelegarWS multi-tenant certificate delegation workflow steps'
'CSR DN fields CUIT country organization ARCA certificate generation'
```

**WSCPE Method Verification (for HLD correction + ARCA Guide §5)**:
```
'WSCPE confirmarDescargaCPE method name WSDL'
'WSCPE CPE state machine transitions estados validos'
'WSCPE XML fields catalog cartaDePorte numeroOrden'
'WSCPE error codes codigos error'
'WSCPE descargadoDestinoCPE deprecated incorrect method name'
```

**WSLPG Form 1116-B/C & SISA Retention (for ARCA Guide §4)**:
```
'WSLPG Form 1116-B fields liquidacion primaria granos XML'
'WSLPG Form 1116-C fields liquidacion secundaria campos XML'
'WSLPG SISA retention tier percentages IVA Ganancias porcentaje'
'WSLPG error codes tabla codigos error'
'WSLPG liqLiquidacionACuenta method liquidacion a cuenta campos'
```

**SIRE Retention (for ARCA Guide new SIRE section)**:
```
'SIRE emitirRetencion SOAP method retencion general parametros'
'SIRE IVA emitirRetencionIVA method parametros'
'SIRE batch lote importacion formato archivo XML estructura'
'SIRE consultar retenciones SOAP method consulta'
'SIRE preguntas frecuentes importacion lote errores'
'SIRE IVA retencion percentages IVA Ganancias tiers SISA'
```

**WSCDC Grain Deposit Certificate (for ARCA Guide new section + all 5 mandatory docs)**:
```
'WSCDC certificado deposito cereal grain deposit certificate legal obligation'
'WSCDC SOAP methods informar deposito cereal metodos'
'WSCDC XML fields especie grano kilos humedad establecimiento campos'
'WSCDC error codes codigos error certificado'
'WSCDC lifecycle estados ciclo vida certificado deposito'
'WSCDC when to call romaneo reception trigger timing'
'WSCDC acopiadores obligacion legal registro ARCA'
```

**WS Padrón A4 & Constancia Inscripción (for ARCA Guide new section)**:
```
'WS Padron A4 getPersona CUIT method SOAP consulta'
'WS Padron A4 response fields persona juridica natural actividades'
'WS Padron SISA category inscription validation workflow'
'WS Constancia Inscripcion SISA certificate method inscripto'
'WS Padron domicilio categorias impositivas response structure'
```

---

## Document 1: ARCA Grain Integration Guide

**File**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`

### Current Section Structure (PRESERVE)

```
§1  Introduction & Purpose
§2  Service Overview (table of 8 services)
§3  WSAA — Authentication Service
§4  WSLPG — Grain Settlement
§5  WSCPE — Grain Movement (CPE)
§6  WSFEv1 / CAEA — Electronic Invoicing
§7  Certificate Management
§8  Homologation Environment
§9  Open Source References
```

### Target Section Structure (AFTER enrichment)

```
§1  Introduction & Purpose  [no change]
§2  Service Overview  [add WSCDC, SIRE IVA, WS Padrón rows to table]
§3  WSAA  [enrich: prod chain CA names, homo chain, TLS version, ADMINREL workflow]
§4  WSLPG  [enrich: Form 1116-B/C field table, SISA tier % table, error codes]
§5  WSCPE  [enrich: state machine table, XML field catalog, error codes]
§6  SIRE — Retention General & IVA  [NEW — insert here]
§7  WSCDC — Grain Deposit Certificate  [NEW — insert here]
§8  WS Padrón A4 & WS Constancia Inscripción  [NEW — insert here]
§9  Cross-Service Error Code Catalog  [NEW — insert here]
§10 WSFEv1 / CAEA  [renumbered from §6]
§11 Certificate Management  [renumbered from §7]
§12 Homologation Environment  [renumbered from §8]
§13 Open Source References  [renumbered from §9]
```

**NOTE**: Inserting §6–§9 requires renumbering §6→§10, §7→§11, §8→§12, §9→§13. Update all internal cross-references.

### Section-by-Section Update Plan

#### §2 Service Overview (update existing table)
- Add row: WSCDC (Grain Deposit Certificate, grain-dev collection, acopiadores)
- Add row: SIRE IVA (IVA Retention via SOAP, arca_dev_guides, all)
- Add row: WS Padrón A4 (CUIT/SISA Lookup, arca_api_specs, all)
- Verify all 8 services appear: WSAA, WSCPE, WSLPG, SIRE, SIRE IVA, WSCDC, WS Padrón A4, WS Constancia Inscripción
- RAG queries: none needed — derive from other section enrichments

#### §3 WSAA (enrich existing)
- Add production certificate chain table (CA name, validity dates)
  - Chain: `AFIPRootCA2 → Computadores` (verify names from RAG)
- Add homologación certificate chain table
  - Chain: `AC_Raiz_Homo → ComputadoresTest` (verify names from RAG)
- Add CSR DN field requirements table (Country, Organization, CN, CUIT)
- Add TLS minimum version subsection (derive from TLS migration schedule PDF)
- Add ADMINREL DelegarWS workflow for multi-tenant (numbered steps)
- **Content to preserve**: existing WSAA token flow, LoginTicketRequest/Response structure
- RAG queries: all 5 WSAA/cert queries listed above

#### §4 WSLPG (enrich existing)
- Add Form 1116-B field table (name, type, length, required — derive from RAG)
- Add Form 1116-C field table (same schema)
- Add SISA retention tier table (SISA category, IVA%, Ganancias% — CRITICAL: this table must match exactly what appears in ADR-027 and SRS)
- Add error code table (code, description, resolution)
- **Content to preserve**: existing WSLPG overview, liqLiquidacionACuenta description
- RAG queries: all 5 WSLPG queries listed above

#### §5 WSCPE (enrich existing)
- Add CPE state machine table (state, valid transitions, trigger event)
  - Known states: Pendiente, Activo, Descargado, Confirmado, Anulado (verify from RAG)
- Add XML field catalog table (field name, type, length, required)
- Add error code table
- Verify `confirmarDescargaCPE` is used (not `descargadoDestinoCPE`) — this section already has the correct name per §5.3 and §5.4
- **Content to preserve**: existing CPE lifecycle narrative, integration diagram
- RAG queries: WSCPE queries listed above

#### §6 SIRE — Retention General & IVA (NEW SECTION)

Structure:
```markdown
## 6. SIRE — Retention Services

### 6.1 Overview
[Legal basis, when applied, relationship to WSLPG liquidation]

### 6.2 SIRE General — SOAP Methods
[Table: method name, description, key parameters]
- emitirRetencion(...)
- [other methods from RAG]

### 6.3 SIRE IVA — SOAP Methods
[Table: method name, description, key parameters]
- emitirRetencionIVA(...)
- [other methods from RAG]

### 6.4 Batch Lote Import Format
[File structure, encoding, record types — from SIRE lote spec]

### 6.5 Retention Tier Table
[SISA category → IVA% → Ganancias% — MUST match §4 WSLPG and ADR-027 exactly]
```

- RAG queries: all 6 SIRE queries listed above

#### §7 WSCDC — Grain Deposit Certificate (NEW SECTION)

Structure:
```markdown
## 7. WSCDC — Grain Deposit Certificate

### 7.1 Legal Obligation
[Regulatory basis, who must use it, when it fires — romaneo reception trigger]
[Note: fires concurrent with WSCPE confirmation at romaneo time]

### 7.2 Certificate Lifecycle
[State diagram or table: states, transitions, terminal states]

### 7.3 SOAP Methods
[Table: method name, description, required parameters]

### 7.4 XML Field Catalog
[Table: field name, type, length, required, description]
[Must include: especie (grain species), kg received, humidity %, establishment ID, date]

### 7.5 Error Codes
[Table: code, description, resolution — from WSCDC v4 manual]

### 7.6 Integration Pattern
[When to call relative to WSCPE, sequence, error handling]
```

- RAG queries: all 7 WSCDC queries listed above

#### §8 WS Padrón A4 & WS Constancia Inscripción (NEW SECTION)

Structure:
```markdown
## 8. WS Padrón A4 & WS Constancia Inscripción

### 8.1 Purpose
[CUIT validation, SISA tier lookup for retention calculation]

### 8.2 WS Padrón A4 — getPersona Method
[Method signature, parameters, response structure]
[Response field catalog table: field name, description, type]

### 8.3 WS Constancia Inscripción
[Method name, parameters, use case for SISA certificate retrieval]

### 8.4 SISA Validation Workflow
[Steps: call getPersona → extract SISA category → map to retention tier]
[Integration point: must be called at romaneo time before WSLPG liquidation]
```

- RAG queries: all 5 WS Padrón queries listed above

#### §9 Cross-Service Error Code Catalog (NEW SECTION)

```markdown
## 9. Cross-Service Error Code Catalog

### 9.1 WSCPE Error Codes
[Table from §5]

### 9.2 WSLPG Error Codes
[Table from §4]

### 9.3 WSCDC Error Codes
[Table from §7]
```

Minimum 3 services required (SC-005). Include SIRE or WSAA as 4th if RAG returns codes.

#### §10–§13 (renumbered)
Update section numbers only. No content changes to §10 (WSFEv1), §11 (Certs), §12 (Homo), §13 (OSS Refs).

### ARCA Guide Checkpoint (verify before moving to Document 2)

```bash
# SC-001: 8 services in overview table
grep -c "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\|WS Padrón\|Constancia\|WSAA" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: ≥8 matches (one per service)

# SC-002: no wrong method name in ARCA Guide
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0

# SC-005: error code tables in ≥3 services
grep -c "Error Code\|error code\|Código.*Error" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: ≥3 sections with error codes

# SC-006: TLS documented
grep -i "TLS\|tls" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: at least one line mentioning TLS version number

# SC-010: cert chain CA names present
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: ≥2 matches (prod + homo chain names)
```

---

## Document 2: Software Requirements Specification (SRS)

**File**: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

### Changes Required

1. **Update generic ARCA requirements**: Replace any "ARCA integration" wording with specific service names and method references.
2. **Add WSCDC requirements block**:
   - The system SHALL call WSCDC `informarDepositoCereal` (or correct method name from RAG) upon romaneo reception confirmation.
   - The system SHALL store the WSCDC deposit certificate number returned by ARCA.
   - The system SHALL handle WSCDC errors without blocking the romaneo reception record.
3. **Add WS Padrón requirements block**:
   - The system SHALL query WS Padrón A4 `getPersona(CUIT)` to validate producer registration at romaneo time.
   - The system SHALL use the SISA category from WS Padrón to calculate retention percentages in WSLPG liquidation.
4. **SISA retention percentages**: Add the exact tier table (matching ARCA Guide §6 and ADR-027 exactly).
5. **Resolve TBD markers**: Find and replace all ARCA-related TBD/TODO/approximate markers.

### Content to Preserve
- All non-ARCA requirements (business rules, inventory, authentication)
- Existing requirement numbering scheme
- Section hierarchy

### SRS Checkpoint

```bash
# SC-003: WSCDC in SRS
grep -c "WSCDC\|CertificadoDeposito\|deposit.*cereal" \
  "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: ≥1 (with requirement ID + description)

# SC-004: no TBD markers in ARCA sections
grep -c "TBD\|TODO\|approximate\|NEEDS CLARIFICATION" \
  "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: 0

# SC-007: SISA retention percentages present
grep -c "IVA.*%\|Ganancias.*%\|SISA.*tier" \
  "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: ≥1 (retention tier table)
```

---

## Document 3: High-Level Design (HLD)

**File**: `Docs/Project Blueprint/High-Level Design (HLD).md`

### Changes Required

#### 3a. Method Name Correction (CRITICAL — 4 exact locations)

Replace ALL 4 occurrences of `descargadoDestinoCPE` with `confirmarDescargaCPE`:

| Approximate Line | Context | Action |
|-----------------|---------|--------|
| ~142 | ARCA integration table row | Replace method name in table cell |
| ~264 | Mermaid sequence diagram node label | Replace in Mermaid code block |
| ~341 | State machine description text | Replace in prose |
| ~539 | Numbered list item | Replace in list item |

**Verification before edit**: Run `grep -n "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"` to confirm exact line numbers. The summary recorded ~142, ~264, ~341, ~539 but use actual grep output.

#### 3b. WSCDC in Integration Architecture (§6)

- Add WSCDC to the ARCA integration flow diagram (alongside WSCPE and WSLPG)
- Add WSCDC to the integration table in §6 (method name, trigger, response)
- Add a note: "WSCDC fires at romaneo reception time, concurrent with WSCPE `confirmarDescargaCPE`"

#### 3c. TLS & Certificate Security (find ARCA security section)

- Add minimum TLS version to the HLD security architecture section
- Note: Summary recorded security is at §10 (not §12 as spec references). Verify actual section number with grep before editing.

### Content to Preserve
- All non-ARCA architecture sections
- Existing Mermaid diagrams (edit nodes only, not structure)
- All HLD section headings and numbering

### HLD Checkpoint

```bash
# SC-002: zero wrong method names in HLD
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0

# SC-003: WSCDC in HLD
grep -c "WSCDC" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1

# SC-006: TLS in HLD or ARCA Guide (combined check)
grep -i "TLS" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1 line with TLS version
```

---

## Document 4: Architecture Decision Records (ADR)

**File**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md`

### Changes Required

#### 4a. ADR-027 Label Fix (CRITICAL)

Current label: `"SISA-Tier Retention Calculation at LPG Filing Time"`
Required label: `"SISA-Tier Retention Calculation at WSLPG Filing Time"`

Find the ADR-027 heading line and update the label text only. Do not alter ADR-027 content.

#### 4b. Enrich ADR-007 (WSAA)

Find ADR-007. Add or update:
- Production certificate chain: `AFIPRootCA2 → Computadores` (exact CA names from RAG)
- Homologación chain: `AC_Raiz_Homo → ComputadoresTest` (verify from RAG)
- Certificate validity date ranges (from RAG)
- ADMINREL delegation decision rationale

#### 4c. Enrich ADR-018 (WSCPE)

Find ADR-018. Add or update:
- Correct method name `confirmarDescargaCPE` (WSDL-authoritative)
- Note superseding the incorrect `descargadoDestinoCPE` reference
- State machine reference to ARCA Guide §5

#### 4d. Enrich ADR-027 (SIRE/WSLPG Retention)

Find ADR-027. Add or update:
- Exact SISA tier retention percentages (IVA% and Ganancias% per tier)
- Reference to SIRE SOAP methods `emitirRetencion` and `emitirRetencionIVA`
- **CRITICAL**: Same % values must appear in ARCA Guide §6 and SRS (SC-007)

#### 4e. New ADR-036: WSCDC Integration Decision

```markdown
### ADR-036: WSCDC Grain Deposit Certificate Integration

**Date**: 2026-03-18
**Status**: Accepted
**Decision**: Integrate WSCDC `informarDepositoCereal` at romaneo reception time, concurrent with WSCPE `confirmarDescargaCPE` confirmation, to satisfy ARCA legal obligation for registered acopiadores.
**Context**: [...]
**Consequences**: [...]
**References**: WSCDC Manual v4, FR-005, SC-003
```

RAG queries for ADR-036 content: all 7 WSCDC queries listed above.

#### 4f. New ADR-037: WS Padrón SISA Validation Decision

```markdown
### ADR-037: WS Padrón A4 SISA Tier Lookup at Romaneo Time

**Date**: 2026-03-18
**Status**: Accepted
**Decision**: Query WS Padrón A4 `getPersona(CUIT)` at romaneo reception to determine producer SISA category before WSLPG liquidation, caching results for 24 hours to reduce ARCA API calls.
**Context**: [...]
**Consequences**: [...]
**References**: WS Padrón A4 Manual v1.3, FR-007, SC-001
```

### ADR Checkpoint

```bash
# SC-003: WSCDC in ADR (ADR-036 present)
grep -c "ADR-036\|WSCDC" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: ≥2

# SC-009: ADR-027 label exact match
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: exactly 1 match

# SC-002: no wrong method name in ADR
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 0
```

---

## Document 5: REST API Design

**File**: `Docs/Project Blueprint/REST API Design.md`

### Changes Required

Add 2 new endpoints (SC-011):

#### Endpoint 1: WSCDC Proxy Operations

```markdown
### POST /api/v1/arca/wscdc/deposit-certificate

**Purpose**: Inform ARCA of grain received at the establishment (WSCDC proxy)
**Trigger**: Called internally after romaneo reception is confirmed
**Request Body**:
- romaneo_id (UUID)
- grain_species (string)
- kg_received (decimal)
- humidity_percent (decimal)
- establishment_id (string)
**Response**: WSCDC deposit certificate number, status
**Auth**: Tenant-scoped service account
```

#### Endpoint 2: SISA Producer Validation

```markdown
### GET /api/v1/arca/padron/sisa-status/{cuit}

**Purpose**: Validate producer SISA registration and retrieve retention tier
**Trigger**: Called at romaneo reception to determine retention %
**Path Parameter**: cuit (11-digit string)
**Response**: sisa_category, iva_retention_percent, ganancias_retention_percent, inscripto (bool)
**Caching**: 24-hour TTL per CUIT to reduce ARCA API calls
**Auth**: Tenant-scoped
```

### Content to Preserve
- All existing endpoints and their definitions
- API versioning scheme and authentication patterns
- Response envelope structure

### REST API Checkpoint

```bash
# SC-011: 2 new endpoints documented
grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
# Expected: ≥2 distinct endpoint sections
```

---

## Document 6: Data Model & Domain Model

**File**: `Docs/Project Blueprint/Data Model & Domain Model.md`

### Changes Required

Add new entity `CertificadoDepositoCereal` (FR-014, SC-003):

```markdown
### CertificadoDepositoCereal

Represents the WSCDC grain deposit certificate issued by ARCA upon romaneo reception.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | UUID | Yes | Internal primary key |
| romaneo_id | FK → Romaneo | Yes | Reception record that triggered this certificate |
| arca_nro_certificado | String | Yes | Certificate number returned by ARCA WSCDC |
| especie | String | Yes | Grain species code (ARCA catalog) |
| kg_bruto | Decimal(10,2) | Yes | Gross kg received |
| kg_neto | Decimal(10,2) | Yes | Net kg after drying/merma |
| humedad_percent | Decimal(5,2) | Yes | Humidity percentage at reception |
| establecimiento_id | String | Yes | ARCA establishment ID |
| fecha_ingreso | Date | Yes | Date of grain reception |
| estado | Enum | Yes | Lifecycle state (Pendiente, Emitido, Anulado) |
| wscdc_response_raw | JSON | No | Full WSCDC API response for audit |
| created_at | DateTime | Yes | Record creation timestamp |
| tenant_id | FK → Tenant | Yes | Multi-tenant isolation |
```

**Note**: Field names and types above are derived from spec requirements. RAG queries for exact WSCDC XML field names should inform final field names during implementation.

Add relationship note: `Romaneo 1 → 0..1 CertificadoDepositoCereal`

### Data Model Checkpoint

```bash
# SC-003: CertificadoDepositoCereal entity in Data Model
grep -c "CertificadoDepositoCereal\|certificado.*deposito\|deposit.*cereal" \
  "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: ≥1 entity definition with fields
```

---

## Documents 7–9: Roadmap, PRD, Product Vision (Optional)

**Files**:
- `Docs/Project Blueprint/Roadmap.md`
- `Docs/Project Blueprint/PRD.md`
- `Docs/Project Blueprint/Product Vision & Scope.md`

These are **optional enhancements** per FR-005 clarification. Their absence does NOT constitute failure of FR-005 or SC-003. Include WSCDC only if a natural integration point exists.

**If updating**:
- Add WSCDC to Phase 1 / MVP requirements where romaneo or ARCA integration is mentioned
- One sentence: "Acopiadores must report grain receipts to ARCA via WSCDC upon romaneo confirmation."
- Do NOT restructure these documents or add new sections.

---

## Session Strategy

This is a multi-session task. Recommended breakdown:

| Session | Documents | Estimated Effort |
|---------|-----------|-----------------|
| Session A | ARCA Guide (Document 1 — largest, most new content) | Full session |
| Session B | SRS + HLD (Documents 2–3) | Full session |
| Session C | ADR + REST API + Data Model (Documents 4–6) | Full session |
| Session D | Optional docs 7–9 + final SC verification sweep | Half session |

Before each session, re-read the relevant sections of `spec.md` to keep SC targets fresh.

---

## Done Criteria

The plan MUST include a final verification sweep against all 11 success criteria:

| SC | Verification Command | Expected |
|----|---------------------|----------|
| SC-001 | `grep -c "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\|WS Padrón\|Constancia\|WSAA" "ARCA Guide"` | ≥8 |
| SC-002 | `grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"` | 0 files |
| SC-003 | Manual check: WSCDC in ARCA Guide, Data Model, HLD, ADR, SRS with traceable artifact | 5 docs |
| SC-004 | `grep -ri "TBD\|TODO\|approximate" "Docs/Project Blueprint/" | grep -i arca` | 0 matches |
| SC-005 | Check error code tables in ARCA Guide for WSCPE, WSLPG, WSCDC | ≥3 services |
| SC-006 | `grep -ri "TLS" "Docs/Project Blueprint/"` | ≥1 doc with TLS version |
| SC-007 | Compare IVA%/Ganancias% in ARCA Guide §6, ADR-027, SRS — must match exactly | Identical |
| SC-008 | `git diff "Docs/Project Blueprint/" | grep "^[+-]" | grep -v "ARCA\|WSCDC\|WSCPE\|WSLPG\|SIRE\|WS Padrón\|cert\|TLS"` | Non-ARCA content unchanged |
| SC-009 | `grep "SISA-Tier Retention Calculation at WSLPG Filing Time" ADR.md` | 1 match |
| SC-010 | `grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/"` | CA names in ARCA Guide + HLD |
| SC-011 | `grep -c "wscdc\|sisa-status" "REST API Design.md"` | ≥2 endpoints |

---

## Content Guidelines

- **Tone**: Technical reference documentation. Factual, precise, third-person.
- **Audience**: Backend engineers who will implement ARCA integration (not business stakeholders).
- **Format**: Markdown tables for field catalogs, error codes, state machines. Numbered lists for workflows.
- **Accuracy standard**: All method names, field names, CA names, and % values MUST come from RAG query results. Never invent or interpolate ARCA technical details.
- **Scope guard**: Do not edit non-ARCA sections. If a change touches non-ARCA content, flag it explicitly and ask for confirmation before saving.
- **Preservation rule**: Preserve all existing headings, subsection structure, and writing style. Add content within existing patterns — do not rewrite surrounding context.
- **Consistency rule**: If the same fact (e.g., SISA retention %) appears in multiple documents, it must be identical across all of them.

---

## Key Reference Facts (Pre-Verified)

These facts have been confirmed from prior research and spec-08 RAG sessions. Use as expected values when querying RAG.

| Fact | Expected Value | Source |
|------|---------------|--------|
| Correct CPE method (discharge) | `confirmarDescargaCPE` | WSCPE WSDL |
| Wrong method (to remove) | `descargadoDestinoCPE` | HLD §6 (incorrect) |
| WSCDC developer manual | Version 4 | ingested to `arca_dev_guides` |
| WS Padrón A4 manual | Version 1.3 | ingested to `arca_api_specs` |
| WSLPG manual | Version 1.24 | ingested to `arca_dev_guides` |
| ADR-027 current label | "SISA-Tier Retention Calculation at LPG Filing Time" | ADR.md (to fix) |
| ADR-027 target label | "SISA-Tier Retention Calculation at WSLPG Filing Time" | SC-009 |
| Last existing ADR number | ADR-035 | ADR.md |
| New WSCDC ADR number | ADR-036 | Sequentially assigned |
| New WS Padrón ADR number | ADR-037 | Sequentially assigned |
| HLD occurrences of wrong method | 4 (approx lines 142, 264, 341, 539) | grep-verified |
| WSCDC trigger point | Romaneo reception time | Spec-09 clarification |
| WSCDC primary dependency spec | Spec-11 (Romaneo Core) | Spec-09 clarification |

---

## Non-Goals (Scope Boundary)

Do NOT include these in the plan:
- Creating new blueprint documents (A-004 assumption)
- Editing implementation specs (specs/001-025/)
- Making decisions about implementation language, framework, or library
- Writing code or pseudocode
- Documenting ARCA services outside the 8 listed in FR-001
- Changing non-ARCA content in any blueprint document
