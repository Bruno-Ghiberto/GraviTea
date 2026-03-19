# Implementation Plan: New ARCA Docs — Blueprint Knowledge Update

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-new-arca-docs/spec.md`

---

## Summary

Enrich 9 existing blueprint documents in `Docs/Project Blueprint/` with authoritative facts extracted from official ARCA developer manuals (already ingested into Qdrant RAG). The primary deliverable is a corrected and extended ARCA Grain Integration Guide that adds 4 new sections (SIRE, WSCDC, WS Padrón, Error Code Catalog) and enriches 3 existing sections (WSAA, WSLPG, WSCPE). Secondary deliverables include WSCDC coverage across 5 mandatory blueprint documents, correction of 4 incorrect method name occurrences in the HLD, and 2 new ADRs (ADR-036, ADR-037). All facts must be sourced from RAG queries — no interpolation of ARCA technical details is permitted.

---

## Technical Context

**Language/Version**: Markdown (documentation enrichment — no code written in this spec)
**Primary Dependencies**: Qdrant (localhost:6333) + Ollama (localhost:11434) for RAG queries
**Storage**: N/A — edits to existing `.md` files only
**Testing**: grep/text search verification commands per document checkpoint
**Target Platform**: `Docs/Project Blueprint/` — 9 markdown documents
**Project Type**: Blueprint Update (documentation enrichment, single-author)
**Performance Goals**: N/A
**Constraints**: RAG-only for ARCA facts; scope-additive for ARCA sections; non-ARCA content must remain unchanged
**Scale/Scope**: 9 documents, 4 execution sessions, 11 verifiable success criteria

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This spec produces documentation only — no Django models, views, migrations, or API code is written. Constitutional principles apply as **design constraints** on the entities and endpoints being documented:

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | PASS | `CertificadoDepositoCereal` entity uses `DECIMAL(17,3)` for weight fields per constitution; UUID PK; append-only state via `estado` enum |
| II. Multi-Tenant Isolation | PASS | `CertificadoDepositoCereal` includes `tenant_id FK → Tenant` — must appear in Data Model doc |
| III. Modular Architecture | PASS | Entity belongs to `acopio` module (`gravitea_acopio`) per constitution; REST endpoints follow `/api/v1/` versioning |
| VI. Fiscal Compliance | PASS | WSCDC is a legal ARCA obligation — documenting it is mandatory, not optional |
| XIV. API Documentation | PASS | New endpoints follow existing REST API Design patterns (OpenAPI-compatible) |

**No constitution violations.** Complexity Tracking table not required.

---

## Project Structure

### Documentation (this feature)

```text
specs/009-new-arca-docs/
├── plan.md              # This file
├── research.md          # Phase 0: RAG query guide + findings template
├── data-model.md        # Phase 1: CertificadoDepositoCereal entity
├── quickstart.md        # Phase 1: Execution environment setup
├── contracts/
│   └── api-contract.md  # Phase 1: 2 new REST endpoints (WSCDC proxy + SISA validation)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Target Documents (repository root)

```text
Docs/Project Blueprint/              # ← 9 files to enrich (6 mandatory + 3 optional)
├── ARCA Grain Integration Guide.md  # P1 — 4 new sections, 3 enriched sections
├── Software Requirements Specification (SRS).md  # P1 — WSCDC + WS Padrón reqs
├── High-Level Design (HLD).md       # P2 — 4 method fixes + WSCDC in §6
├── Architecture Decision Records (ADR).md  # P2 — ADR-036, ADR-037 + 3 enrichments
├── REST API Design.md               # P3 — 2 new endpoints
├── Data Model & Domain Model.md     # P3 — CertificadoDepositoCereal entity
├── Roadmap.md                       # Optional — WSCDC mention if natural fit
├── PRD.md                           # Optional — WSCDC mention if natural fit
└── Product Vision & Scope.md        # Optional — WSCDC mention if natural fit
```

**Structure Decision**: No new source code files. All edits target existing markdown documents in `Docs/Project Blueprint/`. The `specs/009-new-arca-docs/` folder holds planning artifacts only.

---

## RAG Query Infrastructure

**Prerequisite**: Verify Qdrant + Ollama are running before any edit session.

```bash
# Health check
curl -s http://localhost:6333/collections | python3 -c "import sys,json; d=json.load(sys.stdin); print([c['name'] for c in d['result']['collections']])"
# Expected: ['arca_api_specs', 'arca_dev_guides', 'arca_setup_certs', 'acopio_research', ...]
```

**Query command**:
```bash
# Standard: 5 results from all collections
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -l 5

# Collection-targeted: more precise retrieval
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -c arca_dev_guides -l 5

# Broad: field catalogs and error code tables
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'QUERY' -l 10
```

**Fallback**: If RAG returns empty results, read the source PDF directly from `Docs/ARCA/` as a last resort. Document the fallback in research.md.

---

## Phase 0 — Research

**Output**: `specs/009-new-arca-docs/research.md`

Research for this spec consists of running targeted RAG queries against the ingested ARCA PDFs and recording authoritative facts. No external web research needed — all sources are locally ingested.

### Research Task 1: WSAA Certificate Chain & TLS

**Purpose**: Populate ARCA Guide §3 and HLD security section.

RAG queries to run (in `arca_setup_certs` collection):
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA production certificate chain AFIPRootCA CA authority validity' -c arca_setup_certs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA homologacion test certificate chain AC Raiz authority' -c arca_setup_certs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'TLS version minimum ARCA web services SOAP production requirement' -c arca_setup_certs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'ADMINREL DelegarWS multi-tenant certificate delegation workflow steps' -c arca_setup_certs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'CSR DN fields CUIT country organization ARCA certificate generation' -c arca_setup_certs -l 5
```

Record:
- Production CA chain (exact names + validity periods)
- Homologación CA chain (exact names + validity periods)
- Minimum TLS version for production connections
- ADMINREL DelegarWS workflow steps
- CSR DN required fields

### Research Task 2: WSCPE Method Verification

**Purpose**: Confirm `confirmarDescargaCPE` is correct (WSDL-authoritative) and gather state machine + field catalog.

RAG queries:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE confirmarDescargaCPE method name WSDL' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE CPE state machine transitions estados validos' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE XML fields catalog cartaDePorte numeroOrden' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE error codes codigos error' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE descargadoDestinoCPE deprecated incorrect method name' -c arca_dev_guides -l 5
```

Record:
- Confirmed correct method name for CPE discharge
- Full CPE state machine (states + valid transitions + trigger events)
- XML field catalog (name, type, length, required)
- Error code table

### Research Task 3: WSLPG Form 1116-B/C & SISA Retention

**Purpose**: Populate ARCA Guide §4 with field tables and retention tiers.

RAG queries:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG Form 1116-B fields liquidacion primaria granos XML' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG Form 1116-C fields liquidacion secundaria campos XML' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG SISA retention tier percentages IVA Ganancias porcentaje' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG error codes tabla codigos error' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG liqLiquidacionACuenta method liquidacion a cuenta campos' -c arca_dev_guides -l 5
```

Record:
- Form 1116-B field table (name, type, length, required)
- Form 1116-C field table (name, type, length, required)
- **SISA retention tier table** (SISA category → IVA% → Ganancias%) — CRITICAL: record exact values; they must match identically in ADR-027 and SRS
- WSLPG error code table

### Research Task 4: SIRE General & IVA

**Purpose**: Write new ARCA Guide §6 (SIRE section).

RAG queries:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE emitirRetencion SOAP method retencion general parametros' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE IVA emitirRetencionIVA method parametros' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE batch lote importacion formato archivo XML estructura' -c arca_api_specs -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE consultar retenciones SOAP method consulta' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE preguntas frecuentes importacion lote errores' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE IVA retencion percentages IVA Ganancias tiers SISA' -c arca_dev_guides -l 5
```

Record:
- SIRE General SOAP methods (name, description, key parameters)
- SIRE IVA SOAP methods (name, description, key parameters)
- Batch lote file format (structure, encoding, record types)
- Any additional SISA retention % details (cross-check with WSLPG findings)

### Research Task 5: WSCDC Grain Deposit Certificate

**Purpose**: Write new ARCA Guide §7 and populate all 5 mandatory WSCDC documents.

RAG queries:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC certificado deposito cereal grain deposit certificate legal obligation' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC SOAP methods informar deposito cereal metodos' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC XML fields especie grano kilos humedad establecimiento campos' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC error codes codigos error certificado' -c arca_dev_guides -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC lifecycle estados ciclo vida certificado deposito' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC when to call romaneo reception trigger timing' -c arca_dev_guides -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC acopiadores obligacion legal registro ARCA' -c arca_dev_guides -l 5
```

Record:
- Legal obligation basis (regulatory reference)
- Complete SOAP method list (exact names from WSDL)
- Full XML field catalog (field name, type, max length, required/optional)
- Certificate lifecycle states and valid transitions
- Error code table
- Trigger timing relative to WSCPE (confirm: concurrent at romaneo reception)
- Exemption thresholds, if any (expected: none for registered acopiadores)

### Research Task 6: WS Padrón A4 & Constancia Inscripción

**Purpose**: Write new ARCA Guide §8.

RAG queries:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Padron A4 getPersona CUIT method SOAP consulta' -c arca_api_specs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Padron A4 response fields persona juridica natural actividades' -c arca_api_specs -l 10
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Padron SISA category inscription validation workflow' -c arca_api_specs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Constancia Inscripcion SISA certificate method inscripto' -c arca_api_specs -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Padron domicilio categorias impositivas response structure' -c arca_api_specs -l 5
```

Record:
- `getPersona(CUIT)` full method signature and parameters
- Complete response field catalog (field name, type, description)
- SISA category field name and possible values
- WS Constancia Inscripción method name and response fields
- SISA validation workflow (step-by-step)

---

## Phase 1 — Design & Contracts

**Prerequisites**: `research.md` complete with all 6 tasks filled.

### 1a. Data Model: CertificadoDepositoCereal

**Output**: `specs/009-new-arca-docs/data-model.md`

New entity to add to `Docs/Project Blueprint/Data Model & Domain Model.md`. Field types comply with constitution (DECIMAL(17,3) for weight, UUID PK, tenant_id FK).

See: [data-model.md](data-model.md)

### 1b. Interface Contracts: 2 New REST Endpoints

**Output**: `specs/009-new-arca-docs/contracts/api-contract.md`

Documents the 2 new endpoints for `Docs/Project Blueprint/REST API Design.md`.

See: [contracts/api-contract.md](contracts/api-contract.md)

### 1c. Quickstart

**Output**: `specs/009-new-arca-docs/quickstart.md`

Execution environment setup and session-by-session workflow.

See: [quickstart.md](quickstart.md)

---

## Document Execution Order

| Step | Document | Priority | Primary Change | SC Covered |
|------|----------|----------|----------------|------------|
| 1 | ARCA Grain Integration Guide | P1 | 4 new sections + 3 enrichments + renumber §6-§9 | SC-001, SC-002, SC-004, SC-005, SC-006, SC-010 |
| 2 | SRS | P1 | WSCDC reqs + WS Padrón reqs + SISA tier table | SC-003, SC-004, SC-007 |
| 3 | HLD | P2 | Fix 4 method names + WSCDC in §6 + TLS in security section | SC-002, SC-003, SC-006 |
| 4 | ADR | P2 | ADR-027 label fix + enrich ADR-007/018/027 + add ADR-036/037 | SC-003, SC-007, SC-009 |
| 5 | REST API Design | P3 | 2 new endpoints | SC-011 |
| 6 | Data Model | P3 | CertificadoDepositoCereal entity | SC-003 |
| 7-9 | Roadmap / PRD / Vision | Optional | WSCDC mention | SC-008 (scope guard) |

---

## Step-by-Step Edit Guide

### Step 1: ARCA Grain Integration Guide

**File**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`

#### 1.1 Pre-Edit Verification
```bash
# Confirm current section structure
grep -n "^## " "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Confirm no descargadoDestinoCPE in this doc (should already be clean)
grep -n "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0 matches
```

#### 1.2 Section Renumbering Plan
Current §6–§9 must shift to §10–§13 to make room for 4 new sections. Update ALL heading text and ALL internal cross-references that mention these section numbers.

| Before | After | Action |
|--------|-------|--------|
| `## 6. WSFEv1 / CAEA` | `## 10. WSFEv1 / CAEA` | Rename heading |
| `## 7. Certificate Management` | `## 11. Certificate Management` | Rename heading |
| `## 8. Homologation Environment` | `## 12. Homologation Environment` | Rename heading |
| `## 9. Open Source References` | `## 13. Open Source References` | Rename heading |

#### 1.3 Updates to Existing Sections

**§2 Service Overview table** — Add 3 rows:
- SIRE IVA row
- WSCDC row
- WS Padrón A4 + WS Constancia Inscripción rows

**§3 WSAA** — Add after existing content:
- Certificate chain tables (production + homologación) from Research Task 1
- CSR DN requirements table from Research Task 1
- TLS minimum version subsection from Research Task 1
- ADMINREL DelegarWS numbered workflow from Research Task 1

**§4 WSLPG** — Add after existing content:
- Form 1116-B field table from Research Task 3
- Form 1116-C field table from Research Task 3
- SISA retention tier table from Research Task 3 (exact values — must match ADR-027 and SRS)
- Error code table from Research Task 3

**§5 WSCPE** — Add after existing content:
- CPE state machine table from Research Task 2
- XML field catalog table from Research Task 2
- Error code table from Research Task 2

#### 1.4 New Sections to Insert (before renumbered §10)

**§6 SIRE — Retention Services**
```
### 6.1 Overview
### 6.2 SIRE General — SOAP Methods   [from Research Task 4]
### 6.3 SIRE IVA — SOAP Methods       [from Research Task 4]
### 6.4 Batch Lote Import Format       [from Research Task 4]
### 6.5 Retention Tier Table           [from Research Task 4 — cross-check with RT3]
```

**§7 WSCDC — Grain Deposit Certificate**
```
### 7.1 Legal Obligation               [from Research Task 5]
### 7.2 Certificate Lifecycle          [from Research Task 5]
### 7.3 SOAP Methods                   [from Research Task 5]
### 7.4 XML Field Catalog              [from Research Task 5]
### 7.5 Error Codes                    [from Research Task 5]
### 7.6 Integration Pattern            [WSCDC fires concurrent with confirmarDescargaCPE]
```

**§8 WS Padrón A4 & WS Constancia Inscripción**
```
### 8.1 Purpose                        [CUIT lookup + SISA tier determination]
### 8.2 WS Padrón A4 — getPersona     [from Research Task 6]
### 8.3 WS Constancia Inscripción      [from Research Task 6]
### 8.4 SISA Validation Workflow       [from Research Task 6]
```

**§9 Cross-Service Error Code Catalog**
```
### 9.1 WSCPE Error Codes              [condensed from §5]
### 9.2 WSLPG Error Codes              [condensed from §4]
### 9.3 WSCDC Error Codes              [condensed from §7]
### 9.4 SIRE Error Codes               [from Research Task 4, if available]
```

#### 1.5 ARCA Guide Checkpoint
```bash
# SC-001: ≥8 service mentions
grep -ci "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\b\|WS Padrón\|Constancia\|WSAA" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-002: zero wrong method
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0

# SC-005: ≥3 error code sections
grep -c "Error Code\|Código.*Error\|error code" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-006: TLS version documented
grep -i "TLS" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-010: CA names present
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: ≥2 matches
```

---

### Step 2: Software Requirements Specification (SRS)

**File**: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

#### 2.1 Pre-Edit Scan
```bash
# Find all ARCA-related sections
grep -n "ARCA\|WSCPE\|WSLPG\|SIRE\|CPE" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Find TBD markers
grep -n "TBD\|TODO\|approximate\|NEEDS CLARIFICATION" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
```

#### 2.2 Changes
1. **Update generic ARCA req text** — Replace "ARCA integration" phrases with specific service + method references where found.
2. **Add WSCDC requirements block** (in ARCA requirements section, or create subsection):
   ```
   WSCDC-REQ-01: The system SHALL invoke WSCDC [exact method from RAG] upon romaneo
                  reception confirmation, concurrent with WSCPE confirmarDescargaCPE.
   WSCDC-REQ-02: The system SHALL persist the WSCDC deposit certificate number returned
                  by ARCA in CertificadoDepositoCereal.arca_nro_certificado.
   WSCDC-REQ-03: WSCDC API errors SHALL NOT block romaneo reception record creation;
                  failed certificates transition to Pendiente state for retry.
   ```
3. **Add WS Padrón requirements block**:
   ```
   PADRON-REQ-01: The system SHALL query WS Padrón A4 getPersona(CUIT) at romaneo time
                   to determine producer SISA category.
   PADRON-REQ-02: SISA category SHALL be used to calculate IVA and Ganancias retention
                   percentages in WSLPG liquidación.
   PADRON-REQ-03: WS Padrón responses SHALL be cached for 24 hours per CUIT to
                   minimize ARCA API calls.
   ```
4. **Add SISA retention tier table** (exact values from Research Task 3 — must match ARCA Guide §6.5 and ADR-027).
5. **Resolve TBD/TODO/approximate markers** in ARCA sections using RAG findings.

#### 2.3 SRS Checkpoint
```bash
# SC-003: WSCDC in SRS
grep -c "WSCDC" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: ≥1 (requirement ID + description)

# SC-004: no placeholders in ARCA sections
grep -c "TBD\|TODO\|approximate" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: 0

# SC-007: SISA percentages present
grep -i "IVA.*%\|Ganancias.*%\|SISA.*tier\|retención.*%" \
  "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: ≥1 match
```

---

### Step 3: High-Level Design (HLD)

**File**: `Docs/Project Blueprint/High-Level Design (HLD).md`

#### 3.1 Method Name Correction (4 Exact Locations)

**Confirmed line numbers** (verified via grep):

| Line | Current Text | Corrected Text |
|------|-------------|----------------|
| 142 | `CPE lifecycle calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor)` | Replace `descargadoDestinoCPE` → `confirmarDescargaCPE` |
| 264 | Mermaid node: `descargadoDestinoCPE` | Replace in Mermaid code block |
| 341 | `→ Descargada (descargadoDestinoCPE — grain unloaded at destination)` | Replace `descargadoDestinoCPE` → `confirmarDescargaCPE` |
| 539 | `2. descargadoDestinoCPE — grain discharge at destination` | Replace `descargadoDestinoCPE` → `confirmarDescargaCPE` |

**Procedure**: Use Edit tool with exact context strings. Do NOT use sed (use dedicated Edit tool).

#### 3.2 Add WSCDC to §6 Integration Architecture
```bash
# Find §6 heading
grep -n "^## 6\|^## ARCA Integration" "Docs/Project Blueprint/High-Level Design (HLD).md"
```
- Add WSCDC row to the ARCA integration table (alongside WSCPE and WSLPG rows)
- Add WSCDC node to Mermaid integration diagram if present
- Add note: "WSCDC `[method from RAG]` fires concurrent with WSCPE `confirmarDescargaCPE` at romaneo reception"

#### 3.3 TLS in Security Section
```bash
# Find actual security section number
grep -n "^## [0-9].*[Ss]ecur" "Docs/Project Blueprint/High-Level Design (HLD).md"
```
Add a note specifying minimum TLS version (from Research Task 1) for ARCA production connections.

#### 3.4 HLD Checkpoint
```bash
# SC-002: zero wrong method
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0

# SC-003: WSCDC in HLD
grep -c "WSCDC" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1

# SC-006: TLS in HLD
grep -i "TLS" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1 match
```

---

### Step 4: Architecture Decision Records (ADR)

**File**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md`

#### 4.1 ADR-027 Label Fix (CRITICAL — SC-009)
```bash
# Locate ADR-027
grep -n "ADR-027\|ADR 027" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
```
Change `"SISA-Tier Retention Calculation at LPG Filing Time"` → `"SISA-Tier Retention Calculation at WSLPG Filing Time"`.

#### 4.2 Enrich ADR-007 (WSAA)
Locate ADR-007. Add facts from Research Task 1:
- Production cert chain (AFIPRootCA2 → Computadores)
- Homologación chain (AC_Raiz_Homo → ComputadoresTest)
- Validity date ranges
- ADMINREL delegation rationale

#### 4.3 Enrich ADR-018 (WSCPE)
Locate ADR-018. Add:
- Statement that `confirmarDescargaCPE` is the WSDL-authoritative name
- Note that `descargadoDestinoCPE` was an error in earlier docs, now corrected
- Cross-reference to ARCA Guide §5 for full state machine

#### 4.4 Enrich ADR-027 (SIRE/WSLPG Retention)
Locate ADR-027. Add:
- Exact SISA tier retention percentages (from Research Tasks 3 + 4 — **must match** ARCA Guide §6.5 and SRS exactly)
- Reference SIRE SOAP methods `emitirRetencion` and `emitirRetencionIVA`

#### 4.5 New ADR-036: WSCDC Integration Decision

Add after ADR-035:

```markdown
### ADR-036: WSCDC Grain Deposit Certificate Integration at Romaneo Reception

**Date**: 2026-03-18
**Status**: Accepted
**Category**: External Integration / Legal Compliance

**Context**
Argentine law (via ARCA) requires registered acopiadores to inform ARCA of grain received
at the establishment via the WSCDC (Web Service Certificado de Depósito de Cereal).
This obligation was absent from specs 01–08. The WSCDC fires at romaneo reception time,
concurrent with WSCPE CPE confirmation.

**Decision**
Invoke WSCDC `[exact method name from RAG]` at romaneo reception confirmation time,
immediately after WSCPE `confirmarDescargaCPE` succeeds. Store the returned deposit
certificate number in `CertificadoDepositoCereal`. WSCDC errors are non-blocking for
romaneo record creation but must retry to eventual consistency.

**Consequences**
- Spec-11 (Romaneo Core) must implement WSCDC call in the romaneo reception workflow.
- New entity `CertificadoDepositoCereal` required in `gravitea_acopio` module.
- REST proxy endpoint required: `POST /api/v1/arca/wscdc/deposit-certificate`.
- WSCDC credentials scoped per tenant (same WSAA token flow as WSCPE).

**References**: WSCDC Manual v4 (ingested: `arca_dev_guides`), FR-005, SC-003, spec-11
```

#### 4.6 New ADR-037: WS Padrón SISA Tier Lookup Decision

Add after ADR-036:

```markdown
### ADR-037: WS Padrón A4 SISA Tier Lookup at Romaneo Reception

**Date**: 2026-03-18
**Status**: Accepted
**Category**: External Integration / Fiscal Compliance

**Context**
WSLPG grain liquidation requires retention percentages (IVA and Ganancias) based on
the producer's SISA registration category. The SISA tier must be determined before
WSLPG `liqLiquidacionACuenta` is invoked. WS Padrón A4 `getPersona(CUIT)` is the
authoritative ARCA source for SISA category.

**Decision**
Query WS Padrón A4 `getPersona(CUIT)` at romaneo reception to retrieve the producer's
SISA category. Cache the result per CUIT for 24 hours (Redis) to reduce ARCA API calls.
Use the SISA category to look up the retention tier table at WSLPG liquidation time.
WS Constancia Inscripción is used to verify the SISA certificate is current before
finalizing liquidation.

**Consequences**
- REST endpoint required: `GET /api/v1/arca/padron/sisa-status/{cuit}`.
- 24-hour Redis cache required per CUIT.
- Spec-13 (Producer Accounts) depends on this lookup for retention calculation.
- WS Padrón credentials scoped per tenant (same WSAA token flow).

**References**: WS Padrón A4 Manual v1.3 (ingested: `arca_api_specs`), FR-007, SC-001, spec-13
```

#### 4.7 ADR Checkpoint
```bash
# SC-009: exact label match
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 1 match

# SC-003: WSCDC in ADR
grep -c "ADR-036\|WSCDC" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: ≥2

# SC-002: zero wrong method
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 0
```

---

### Step 5: REST API Design

**File**: `Docs/Project Blueprint/REST API Design.md`

#### 5.1 Locate Insertion Point
```bash
# Find ARCA-related section or last endpoint group
grep -n "^## \|arca\|factur" "Docs/Project Blueprint/REST API Design.md" | head -20
```

#### 5.2 Add WSCDC Proxy Endpoint
Insert in the ARCA integration section (or create `### ARCA Grain Integration` subsection):

```markdown
#### POST /api/v1/arca/wscdc/deposit-certificate

**Purpose**: Inform ARCA of grain received at the acopiador establishment
**Authorization**: JWT — tenant-scoped; requires `acopio.wscdc.write` permission
**Trigger**: Internal call upon romaneo reception confirmation

**Request Body** (`application/json`):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| romaneo_id | UUID | Yes | Reception record that triggered the certificate |
| grain_species | string | Yes | ARCA grain species code |
| kg_received | decimal | Yes | Gross kg received at establishment |
| humidity_percent | decimal | Yes | Humidity percentage at reception |
| establishment_id | string | Yes | ARCA-registered establishment ID |

**Response 201**:
| Field | Type | Description |
|-------|------|-------------|
| nro_certificado | string | WSCDC deposit certificate number from ARCA |
| estado | string | Certificate state (Emitido / Pendiente on retry) |
| certificado_id | UUID | Internal CertificadoDepositoCereal record ID |

**Error responses**: 400 (validation), 422 (ARCA rejection — includes WSCDC error code), 503 (ARCA unavailable — certificate queued for retry)
```

#### 5.3 Add SISA Validation Endpoint

```markdown
#### GET /api/v1/arca/padron/sisa-status/{cuit}

**Purpose**: Retrieve producer SISA registration status and retention tier from ARCA WS Padrón A4
**Authorization**: JWT — tenant-scoped; requires `acopio.padron.read` permission
**Caching**: 24-hour TTL per CUIT (Redis)

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| cuit | string(11) | Producer CUIT (digits only, no hyphens) |

**Response 200**:
| Field | Type | Description |
|-------|------|-------------|
| cuit | string | Queried CUIT |
| sisa_category | string | SISA registration category code |
| iva_retention_percent | decimal | IVA retention % applicable at liquidation |
| ganancias_retention_percent | decimal | Ganancias retention % applicable at liquidation |
| inscripto | boolean | Whether producer has active SISA inscription |
| cache_expires_at | datetime | When cached result expires (ISO 8601) |

**Error responses**: 400 (invalid CUIT format), 404 (CUIT not found in ARCA), 503 (ARCA unavailable)
```

#### 5.4 REST API Checkpoint
```bash
# SC-011: 2 new endpoints
grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
# Expected: ≥2
```

---

### Step 6: Data Model & Domain Model

**File**: `Docs/Project Blueprint/Data Model & Domain Model.md`

#### 6.1 Locate Acopio Section
```bash
grep -n "acopio\|Romaneo\|grain\|granos" "Docs/Project Blueprint/Data Model & Domain Model.md" | head -20
```

#### 6.2 Add CertificadoDepositoCereal Entity

Insert near Romaneo entity (same module — `gravitea_acopio`):

```markdown
### CertificadoDepositoCereal

Represents the WSCDC grain deposit certificate issued by ARCA upon grain reception at the establishment. Created at romaneo reception time concurrent with WSCPE CPE confirmation. Lives in `gravitea_acopio` module.

**Relationship**: `Romaneo 1 → 0..1 CertificadoDepositoCereal`

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| id | UUID | Yes | PK | Internal primary key |
| tenant_id | FK → Tenant | Yes | ON DELETE RESTRICT | Multi-tenant isolation (RLS enforced) |
| romaneo_id | FK → Romaneo | Yes | ON DELETE RESTRICT, UNIQUE | Reception record that triggered this certificate |
| arca_nro_certificado | VARCHAR(50) | Yes | | Deposit certificate number returned by WSCDC |
| especie | VARCHAR(10) | Yes | ARCA catalog code | Grain species code |
| kg_bruto | DECIMAL(17,3) | Yes | > 0 | Gross kg received |
| kg_neto | DECIMAL(17,3) | Yes | > 0, ≤ kg_bruto | Net kg after merma/drying |
| humedad_percent | DECIMAL(5,2) | Yes | 0–100 | Humidity percentage at reception |
| establecimiento_id | VARCHAR(50) | Yes | | ARCA-registered establishment ID |
| fecha_ingreso | DATE | Yes | | Date of grain reception |
| estado | ENUM | Yes | Pendiente, Emitido, Anulado | WSCDC certificate lifecycle state |
| wscdc_response_raw | JSONB | No | | Full WSCDC API response for audit trail |
| created_at | TIMESTAMPTZ | Yes | auto | Record creation timestamp |

**State Transitions**: `Pendiente` (ARCA call failed, retry pending) → `Emitido` (ARCA accepted) | `Emitido` → `Anulado` (cancelled by acopiador)

**Notes**:
- `DECIMAL(17,3)` for weight fields per constitution financial precision standard.
- `wscdc_response_raw` enables audit and debugging of ARCA responses.
- `romaneo_id` is UNIQUE — one certificate per romaneo reception.
- RLS policy must include `tenant_id` filter.
```

#### 6.3 Data Model Checkpoint
```bash
# SC-003: entity present
grep -c "CertificadoDepositoCereal" "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: ≥1
```

---

### Steps 7–9: Optional Documents

Only update if a natural WSCDC integration point exists in the document.

**Roadmap** (`Docs/Project Blueprint/Roadmap.md`):
```bash
grep -n "romaneo\|ARCA\|WSCPE\|WSLPG\|Phase 1\|MVP" "Docs/Project Blueprint/Roadmap.md" | head -10
```
If Phase 1 / MVP includes ARCA or romaneo: add bullet "WSCDC grain deposit certificate reporting (legal obligation — fires at romaneo reception)".

**PRD** / **Product Vision**: Same approach — search for ARCA or romaneo context, add one sentence if natural fit.

**Scope guard**: Do NOT add new sections or restructure. One-sentence addition maximum per optional document.

---

## Final Verification Sweep

Run after all 6 mandatory documents are complete:

```bash
# SC-001: ARCA Guide has ≥8 services
echo "=== SC-001 ==="; grep -ci "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\b\|WS Padrón\|Constancia\|WSAA" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-002: Zero wrong method name across all docs
echo "=== SC-002 ==="; grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"
# Expected: no output (0 files)

# SC-003: Manual check — WSCDC in 5 docs (ARCA Guide, Data Model, HLD, ADR, SRS)
echo "=== SC-003 ==="; for f in "ARCA Grain Integration Guide.md" "Data Model & Domain Model.md" "High-Level Design (HLD).md" "Architecture Decision Records (ADR).md" "Software Requirements Specification (SRS).md"; do count=$(grep -c "WSCDC" "Docs/Project Blueprint/$f"); echo "$f: $count"; done

# SC-004: Zero TBD/TODO in any ARCA section across all docs
echo "=== SC-004 ==="; grep -ri "TBD\|TODO\|approximate" "Docs/Project Blueprint/"

# SC-005: ≥3 error code sections in ARCA Guide
echo "=== SC-005 ==="; grep -c "Error Code\|error code\|Código.*Error" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-006: TLS version documented
echo "=== SC-006 ==="; grep -ri "TLS" "Docs/Project Blueprint/"

# SC-007: SISA percentages consistent (manual cross-check)
echo "=== SC-007 ==="; grep -A3 "SISA.*tier\|IVA.*%\|Ganancias.*%" "Docs/Project Blueprint/ARCA Grain Integration Guide.md" | head -15
echo "---ADR---"; grep -A3 "IVA.*%\|Ganancias.*%" "Docs/Project Blueprint/Architecture Decision Records (ADR).md" | grep "%"
echo "---SRS---"; grep -A3 "IVA.*%\|Ganancias.*%" "Docs/Project Blueprint/Software Requirements Specification (SRS).md" | grep "%"

# SC-008: Non-ARCA content unchanged (spot check)
echo "=== SC-008 ==="; git diff "Docs/Project Blueprint/" -- | grep "^[+-]" | grep -v "^[+-][+-][+-]" | grep -vi "ARCA\|WSCDC\|WSCPE\|WSLPG\|SIRE\|WS Padrón\|cert\|TLS\|ADR-03[67]\|confirmar\|descargado" | head -20
# Expected: only whitespace/formatting changes for non-ARCA lines

# SC-009: ADR-027 label exact match
echo "=== SC-009 ==="; grep "SISA-Tier Retention Calculation at WSLPG Filing Time" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: exactly 1 match

# SC-010: CA names in ARCA Guide
echo "=== SC-010 ==="; grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: ≥2 matches (prod + homo chains)

# SC-011: 2 new endpoints in REST API Design
echo "=== SC-011 ==="; grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
# Expected: ≥2
```

---

## Session Strategy

| Session | Documents | Entry Condition |
|---------|-----------|-----------------|
| A — ARCA Guide | Step 1 | RAG services running; research.md populated |
| B — SRS + HLD | Steps 2–3 | Session A ARCA Guide checkpoint PASSED |
| C — ADR + REST + Data Model | Steps 4–6 | Session B checkpoints PASSED |
| D — Optional + Final Sweep | Steps 7–9 + Final | Session C checkpoints PASSED |

Start each session by reading spec.md and relevant step from this plan.

---

## Content Guidelines

- **Tone**: Technical reference. Factual, precise, third-person.
- **Audience**: Backend engineers implementing ARCA integration.
- **Format**: Markdown tables for catalogs; numbered lists for workflows; Mermaid for diagrams.
- **Accuracy rule**: All ARCA technical details (method names, field names, % values, CA names) MUST come from RAG query results. Never interpolate.
- **Scope guard**: If an edit would change non-ARCA content substantively, stop and document the concern before proceeding.
- **Consistency rule**: SISA retention % values must be identical wherever they appear (ARCA Guide §6.5, ADR-027, SRS).

---

## Key Reference Facts (Pre-Verified)

| Fact | Value | Source |
|------|-------|--------|
| Correct CPE discharge method | `confirmarDescargaCPE` | WSCPE WSDL |
| Wrong method to replace | `descargadoDestinoCPE` | HLD §6 (4 occurrences at lines 142, 264, 341, 539) |
| WSCDC manual version | v4 | `arca_dev_guides` collection |
| WS Padrón A4 manual | v1.3 | `arca_api_specs` collection |
| WSLPG manual | v1.24 | `arca_dev_guides` collection |
| ADR-027 current label | "SISA-Tier Retention Calculation at LPG Filing Time" | ADR.md |
| ADR-027 target label | "SISA-Tier Retention Calculation at WSLPG Filing Time" | SC-009 |
| Last existing ADR | ADR-035 | ADR.md |
| New ADR for WSCDC | ADR-036 | This plan |
| New ADR for WS Padrón | ADR-037 | This plan |
| WSCDC trigger timing | Romaneo reception, concurrent with WSCPE | spec-09 clarification |
| CertificadoDepositoCereal module | `gravitea_acopio` | constitution §III |
