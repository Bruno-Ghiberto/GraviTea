# spec-09: New ARCA Docs — Blueprint Knowledge Update — Implementation Context

## 1. Overview

Spec-09 enriches **9 existing blueprint documents** in `Docs/Project Blueprint/` with authoritative
facts from ARCA official PDFs (ingested into Qdrant RAG). No new documents are created. All edits
are strictly ARCA-additive — non-ARCA content remains unchanged.

**Authorship model**: Single-author document enrichment. No tmux agent teams, no agent instruction
files, no code implementation. This is a Blueprint Update spec (Wave 5).

**Session model**: 4 sessions (A → B → C → D), each gated by checkpoint verification.

| Session | Target Documents | Tasks | Phases |
|---------|-----------------|-------|--------|
| **A** | research.md + ARCA Guide | T001–T020 | 1 (Setup) + 2 (Research) + 3 (US1) |
| **B** | SRS + HLD | T021–T022, T026–T032, T041–T041b | 4 (partial) + 5 + 6 (SRS only) + 7 (HLD only) |
| **C** | ADR + REST API + Data Model | T023–T025, T033–T040, T042 | 4 (partial) + 6 (partial) + 7 (partial) |
| **D** | Optional docs + Final sweep | T043–T047 | 8 (Polish + PR) |

> **Note on task ordering**: tasks.md organizes by user story/phase for traceability.
> This file groups tasks by **target document** for practical execution (edit each file
> once rather than revisiting). Both orderings satisfy the dependency graph in tasks.md.

### Documents Modified (by change volume)

| Priority | Document | Primary Changes |
|----------|----------|----------------|
| P1 | ARCA Grain Integration Guide | 4 new sections (§6–§9), 3 enrichments (§3–§5), §2 table update, renumber §6–§9 → §10–§13 |
| P1 | SRS | WSCDC reqs + WS Padrón reqs + SISA tier table |
| P2 | HLD | Fix 4 method names + WSCDC in §6 + TLS in security + cert chain in security |
| P2 | ADR | ADR-027 label fix + enrich ADR-007/018/027 + add ADR-036/037 |
| P3 | REST API Design | 2 new endpoints (WSCDC POST + SISA GET) |
| P3 | Data Model | CertificadoDepositoCereal entity |
| Opt | Roadmap / PRD / Vision | WSCDC one-sentence mention (if natural fit) |

---

## 2. Full Writing Context

Read these files **in this order** before starting any editing session:

| Priority | File | What it provides |
|----------|------|-----------------|
| 1 | `specs/009-new-arca-docs/spec.md` | User stories (US1–US5), functional requirements (FR-001–FR-016), success criteria (SC-001–SC-011), assumptions, edge cases |
| 2 | `specs/009-new-arca-docs/plan.md` | Step-by-step edit guide per document, section renumbering plan, checkpoint commands, content guidelines, key reference facts |
| 3 | `specs/009-new-arca-docs/tasks.md` | 48 tasks across 8 phases, dependency graph, parallel execution opportunities, session mapping |
| 4 | `specs/009-new-arca-docs/research.md` | RAG query guide and findings template — populate BEFORE editing any document |
| 5 | `specs/009-new-arca-docs/quickstart.md` | Session-by-session workflow commands, done criteria per session, final verification sweep |
| 6 | `specs/009-new-arca-docs/data-model.md` | CertificadoDepositoCereal entity definition (fields, types, constraints, state transitions) |
| 7 | `specs/009-new-arca-docs/contracts/api-contract.md` | 2 new REST endpoints (WSCDC POST + SISA GET) with full request/response schemas |

**At each session start**: Re-read `spec.md` SC targets and the relevant Step section from `plan.md`.

---

## 3. Domain Knowledge Protocol

### RAG Queries — Required Method

**NEVER** read full research PDFs or Markdown files in `Docs/Researches/` or `Docs/ARCA/`.
They are too large for context windows and contain unstructured content.

**ALWAYS** use targeted RAG queries:

```bash
# Standard: 5 results, auto-routed
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'YOUR QUERY' -l 5

# Collection-targeted: more precise
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'YOUR QUERY' -c arca_dev_guides -l 5

# Broad: field catalogs and error code tables
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'YOUR QUERY' -l 10

# Batch: multiple queries at once (saves results to Docs/RAG_results/)
.venv/bin/python scripts/qdrant/qdrant_batch_search.py -f queries.txt -l 5 -o Docs/RAG_results
```

### Available RAG Collections

| Collection | Contents | Use for |
|------------|----------|---------|
| `arca_dev_guides` | 14 ARCA developer manuals: WSAA, WSLPG, WSCPE, WSCDC, SIRE, WSFEv1, WSFEX | Method names, XML fields, error codes, state machines, lifecycle flows |
| `arca_api_specs` | 8 ARCA technical specs: WSAA, WSFEv1, WSMTXCA, padron, SIRE | WS Padrón A4 getPersona, SISA categories, SIRE API specs |
| `arca_setup_certs` | 8 certificate/environment docs | WSAA cert chains, TLS requirements, CSR DN fields, ADMINREL delegation |
| `acopio_research` | 20+ grain industry research docs | Not primary for spec-09 — use only if ARCA collections lack needed context (e.g., SISA regulatory background) |

### Knowledge Priority

1. **RAG query results** from ARCA collections — ground truth for ARCA technical details
2. **research.md findings** (once populated) — authoritative for cross-document consistency (esp. SISA %)
3. **Existing blueprint documents** — reference for writing style, section structure, terminology
4. **Direct PDF read** — LAST RESORT if RAG returns empty; read from `Docs/ARCA/` and document the fallback in research.md

### Critical Accuracy Rules

- All ARCA method names, field names, % values, CA names, error codes **MUST** come from RAG results
- WSDL is authoritative for method names when WSDL and manual text conflict (A-003)
- SISA retention % values **MUST** be identical across ARCA Guide §6.5, ADR-027, and SRS (SC-007)
- Never interpolate, estimate, or fabricate ARCA technical details

---

## 4. Session A: Research + ARCA Guide Enrichment

**Tasks**: T001–T020 | **Phases**: 1 + 2 + 3

### A1. Environment Verification (T001–T003)

```bash
# T001: Confirm branch
git branch --show-current
# Expected: 009-new-arca-docs

# T002: Verify Qdrant health
curl -s http://localhost:6333/healthz

# T003: Verify RAG collections have content
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA authentication token' -l 2
# If empty: .venv/bin/python scripts/qdrant/ingest_arca_qdrant.py --collection all
```

### A2. Foundational Research (T004–T009) — PARALLELIZABLE

Run all 6 research tasks from `specs/009-new-arca-docs/research.md`. Each task has 5–7
RAG queries targeting specific ARCA collections.

| Task | Domain | Collection | Key Outputs |
|------|--------|------------|-------------|
| T004 | WSAA cert chain + TLS | `arca_setup_certs` | CA names, validity dates, TLS version, ADMINREL steps, CSR DN |
| T005 | WSCPE method verification | `arca_dev_guides` | Confirmed method name, state machine, XML field catalog, error codes |
| T006 | WSLPG Form 1116-B/C + SISA | `arca_dev_guides` | Form field tables, **SISA retention tier table** (IVA%/Ganancias%), error codes |
| T007 | SIRE General + IVA | `arca_dev_guides` + `arca_api_specs` | SOAP methods, batch lote format, additional SISA % |
| T008 | WSCDC | `arca_dev_guides` | Legal basis, SOAP method name, XML fields, lifecycle states, error codes |
| T009 | WS Padrón A4 | `arca_api_specs` | getPersona signature, response fields, SISA category field, validation workflow |

**Populate all findings** in `specs/009-new-arca-docs/research.md` — replace every `[FROM RAG]` placeholder.

**RESEARCH GATE**: Before proceeding to A3, confirm T006 SISA % values match T007 values.
If they differ, use WSLPG (T006) as authoritative and note discrepancy in research.md.

### A3. ARCA Guide Editing (T010–T020) — SEQUENTIAL (same file)

**File**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`

Follow `plan.md §Step 1` exactly. Summary of operations:

| Task | Operation | Source |
|------|-----------|--------|
| T010 | Verify baseline headings (`grep -n "^## "`) | — |
| T011 | Renumber §6→§10, §7→§11, §8→§12, §9→§13 + internal cross-refs | — |
| T012 | Update §2 Service Overview table: add WSCDC, SIRE IVA, WS Padrón A4, WS Constancia | — |
| T013 | Enrich §3 WSAA: cert chain tables (prod + homo), CSR DN table, TLS subsection, ADMINREL workflow | T004 findings |
| T014 | Enrich §4 WSLPG: Form 1116-B field table, 1116-C field table, SISA tier table, error codes | T006 findings |
| T015 | Enrich §5 WSCPE: state machine table, XML field catalog, error codes; verify `confirmarDescargaCPE` | T005 findings |
| T016 | **Write new §6** SIRE: 6.1 Overview, 6.2 General SOAP methods, 6.3 IVA SOAP methods, 6.4 Batch Lote, 6.5 Retention Tier Table (values must match §4 exactly) | T007 findings |
| T017 | **Write new §7** WSCDC: 7.1 Legal Obligation, 7.2 Certificate Lifecycle, 7.3 SOAP Methods, 7.4 XML Field Catalog, 7.5 Error Codes, 7.6 Integration Pattern | T008 findings |
| T018 | **Write new §8** WS Padrón A4 & WS Constancia Inscripción: 8.1 Purpose, 8.2 getPersona + response fields, 8.3 WS Constancia method, 8.4 SISA Validation Workflow | T009 findings |
| T019 | **Write new §9** Cross-Service Error Code Catalog: 9.1 WSCPE, 9.2 WSLPG, 9.3 WSCDC, 9.4 SIRE (if available) | §4/§5/§7 |
| T020 | Run ARCA Guide checkpoint (see below) | — |

### A4. Session A Checkpoint (T020)

```bash
# SC-001: ≥8 service mentions
grep -ci "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\b\|WS Padrón\|Constancia\|WSAA" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-002: zero wrong method
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0

# SC-004: no TBD/TODO/approximate in ARCA Guide (catch early)
grep -ci "TBD\|TODO\|approximate" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0 in ARCA sections (non-ARCA TBDs are out of scope)

# SC-005: ≥3 error code sections
grep -c "Error Code\|error code\|Código.*Error" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-006: TLS version documented
grep -i "TLS" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

# SC-010: CA names present (≥2 matches: prod + homo)
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
```

**All checks must pass before committing Session A.**

**Commit**:
```bash
git add "Docs/Project Blueprint/ARCA Grain Integration Guide.md" \
        specs/009-new-arca-docs/research.md
git commit -m "spec-09: enrich ARCA Guide with WSCDC, SIRE, WS Padrón sections"
```

---

## 5. Session B: SRS + HLD

**Tasks**: T021–T022, T026–T032, T041, T041b | **Phases**: 4 (SRS+HLD) + 5 + 6 (SRS) + 7 (HLD)
**Entry condition**: Session A ARCA Guide checkpoint PASSED; research.md SISA % values filled.

### B1. SRS Edits (T021, T031, T032)

**File**: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`

From `plan.md §Step 2`:

1. **Pre-scan**: `grep -in "ARCA integration\|ARCA system" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"` — update each generic match to reference specific service names
2. **Add WSCDC requirements block** (T021):
   - WSCDC-REQ-01: Invoke WSCDC [exact method from T008] on romaneo confirmation, concurrent with WSCPE `confirmarDescargaCPE`
   - WSCDC-REQ-02: Persist `arca_nro_certificado` in CertificadoDepositoCereal
   - WSCDC-REQ-03: WSCDC errors non-blocking for romaneo record creation (retry to eventual consistency)
3. **Add WS Padrón requirements block** (T031):
   - PADRON-REQ-01: Query `getPersona(CUIT)` at romaneo time for SISA category
   - PADRON-REQ-02: Use SISA category for WSLPG retention % calculation
   - PADRON-REQ-03: Cache WS Padrón responses 24h per CUIT (Redis)
4. **Add SISA retention tier table** (T032): exact IVA% and Ganancias% from research.md — **must match ARCA Guide §6.5 identically** (SC-007)
5. **Resolve all ARCA TBD/TODO markers**: use research.md findings

### B2. HLD Edits (T022, T026–T029, T041, T041b)

**File**: `Docs/Project Blueprint/High-Level Design (HLD).md`

From `plan.md §Step 3`:

**Method name fixes** (T026–T029) — use Edit tool with exact context strings, NOT sed:

| Task | Line | Current Context | Fix |
|------|------|----------------|-----|
| T026 | ~142 | `confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor` | Replace `descargadoDestinoCPE` → `confirmarDescargaCPE` |
| T027 | ~264 | Mermaid node `descargadoDestinoCPE` | Update node label only |
| T028 | ~341 | `→ Descargada (descargadoDestinoCPE — grain unloaded at destination)` | Replace method name only |
| T029 | ~539 | `2. descargadoDestinoCPE — grain discharge at destination` | Replace method name only |

**WSCDC integration** (T022):
- Add WSCDC row to §6 ARCA integration table
- Add WSCDC node to Mermaid diagram if present
- Add timing note: "fires concurrent with WSCPE `confirmarDescargaCPE` at romaneo reception"

**TLS in security section** (T041):
- Find section: `grep -n "^## [0-9].*[Ss]ecur" "Docs/Project Blueprint/High-Level Design (HLD).md"`
- Add TLS minimum version note (from research Task 1)

**WSAA cert chain in security section** (T041b):
- In same security section, add "WSAA Certificate Chain" subsection
- Document production chain (AFIPRootCA2 → Computadores, validity dates from T004)
- Document homologación chain (AC_Raiz_Homo → ComputadoresTest, validity dates from T004)

### B3. Session B Checkpoint (includes T030)

```bash
# SC-003: WSCDC in SRS (≥1 requirement ID + description)
grep -c "WSCDC" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"

# SC-004: no placeholders in SRS ARCA sections
grep -c "TBD\|TODO\|approximate" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: 0

# SC-007: SISA % present in SRS
grep -i "IVA.*%\|Ganancias.*%" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"

# SC-002: zero wrong method in HLD (T030 — full cross-doc check)
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0
# Also verify no remaining occurrences in ARCA Guide or SRS:
grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"
# Expected: empty output (0 files)

# SC-003: WSCDC in HLD (≥1)
grep -c "WSCDC" "Docs/Project Blueprint/High-Level Design (HLD).md"

# SC-006: TLS documented in HLD
grep -i "TLS" "Docs/Project Blueprint/High-Level Design (HLD).md"

# SC-010: CA chain names in HLD (≥2)
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/High-Level Design (HLD).md"
```

**Commit**:
```bash
git add "Docs/Project Blueprint/Software Requirements Specification (SRS).md" \
        "Docs/Project Blueprint/High-Level Design (HLD).md"
git commit -m "spec-09: WSCDC/WS Padrón reqs in SRS; fix HLD method names + WSCDC + TLS + cert chain"
```

---

## 6. Session C: ADR + REST API + Data Model

**Tasks**: T023–T025, T033–T040, T042 | **Phases**: 4 (Data Model + ADR-036) + 6 + 7 (ADR edits)
**Entry condition**: Sessions A+B checkpoints PASSED.

### C1. ADR Edits (T037–T040, T024, T035)

**File**: `Docs/Project Blueprint/Architecture Decision Records (ADR).md`

From `plan.md §Step 4`:

| Task | ADR | Operation | Key Detail |
|------|-----|-----------|------------|
| T037 | ADR-027 | **Label fix (SC-009)** | Change `"at LPG Filing Time"` → `"at WSLPG Filing Time"` (heading text only) |
| T038 | ADR-007 | Enrich (WSAA) | Add production CA chain (AFIPRootCA2 → Computadores), homologación chain, validity dates, ADMINREL rationale (from T004) |
| T039 | ADR-018 | Enrich (WSCPE) | Add `confirmarDescargaCPE` is WSDL-authoritative; `descargadoDestinoCPE` was an error; cross-ref ARCA Guide §5 |
| T040 | ADR-027 | Enrich (SIRE/WSLPG retention) | Add exact SISA tier % (must match Guide §6.5 and SRS); reference `emitirRetencion` and `emitirRetencionIVA` from T007 |
| T024 | **ADR-036** | **Write new** (WSCDC) | Date 2026-03-18, Accepted, WSCDC at romaneo reception concurrent with WSCPE, non-blocking errors, CertificadoDepositoCereal entity — template in `plan.md §4.5` |
| T035 | **ADR-037** | **Write new** (WS Padrón) | Date 2026-03-18, Accepted, getPersona(CUIT) at romaneo, 24h Redis cache, SISA → tier lookup at liquidation — template in `plan.md §4.6` |

### C2. REST API Design (T033–T034)

**File**: `Docs/Project Blueprint/REST API Design.md`

From `plan.md §Step 5` + `specs/009-new-arca-docs/contracts/api-contract.md`:

1. **Locate insertion point**: `grep -n "^## \|arca\|factur" "Docs/Project Blueprint/REST API Design.md" | head -20`
2. **Add WSCDC endpoint** (T033):
   - `POST /api/v1/arca/wscdc/deposit-certificate`
   - Request: romaneo_id, grain_species, kg_received, humidity_percent, establishment_id
   - Response 201: certificado_id, nro_certificado, estado (`Emitido`), created_at
   - Response 202: certificado_id, estado (`Pendiente`), message — ARCA unavailable, certificate queued for retry (non-blocking pattern per WSCDC-REQ-03)
   - Errors: 400, 404, 409, 422, 503
   - Tag: `arca-grain`
3. **Add SISA endpoint** (T034):
   - `GET /api/v1/arca/padron/sisa-status/{cuit}`
   - Path param: cuit (11 digits)
   - Response: cuit, sisa_category, iva_retention_percent, ganancias_retention_percent, inscripto, cache_expires_at, source
   - Errors: 400, 404, 503
   - Tag: `arca-padron`

Follow the existing REST API Design document's endpoint format (OpenAPI-compatible patterns).

### C3. Data Model (T023)

**File**: `Docs/Project Blueprint/Data Model & Domain Model.md`

From `plan.md §Step 6` + `specs/009-new-arca-docs/data-model.md`:

1. **Locate acopio section**: `grep -n "acopio\|Romaneo\|grain\|granos" "Docs/Project Blueprint/Data Model & Domain Model.md" | head -20`
2. **Add CertificadoDepositoCereal entity** near Romaneo entity:
   - Full field table (id, tenant_id, romaneo_id, arca_nro_certificado, especie, kg_bruto, kg_neto, humedad_percent, establecimiento_id, fecha_ingreso, estado, wscdc_response_raw, created_at)
   - State transitions: Pendiente → Emitido, Emitido → Anulado, Pendiente → Anulado
   - Relationship: `Romaneo 1 → 0..1 CertificadoDepositoCereal`
   - Module: `gravitea_acopio`
   - Note: DECIMAL(17,3) for weight fields per constitution

### C4. Session C Checkpoint (includes T025, T036, T042)

```bash
# T025 — SC-003: WSCDC in ALL 5 mandatory docs (first time all 5 are edited)
for f in "ARCA Grain Integration Guide.md" "Data Model & Domain Model.md" \
         "High-Level Design (HLD).md" "Architecture Decision Records (ADR).md" \
         "Software Requirements Specification (SRS).md"; do
  count=$(grep -c "WSCDC" "Docs/Project Blueprint/$f" 2>/dev/null)
  echo "  $f: $count (need ≥1 with substantive content)"
done

# SC-009: ADR-027 label exact match
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 1 match

# SC-003: WSCDC in ADR (≥2)
grep -c "ADR-036\|WSCDC" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"

# SC-003: WSCDC in Data Model
grep -c "CertificadoDepositoCereal" "Docs/Project Blueprint/Data Model & Domain Model.md"
# Expected: ≥1

# SC-002: zero wrong method in ADR
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 0

# T036 — SC-011: 2 new endpoints
grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
# Expected: ≥2

# T036 + T042 — SC-007: SISA % consistency (manual visual cross-check)
echo "-- ARCA Guide §6.5 --"
grep -A5 "Ganancias.*%" "Docs/Project Blueprint/ARCA Grain Integration Guide.md" | head -10
echo "-- ADR-027 --"
grep -A3 "Ganancias.*%" "Docs/Project Blueprint/Architecture Decision Records (ADR).md" | head -5
echo "-- SRS --"
grep -A3 "Ganancias.*%" "Docs/Project Blueprint/Software Requirements Specification (SRS).md" | head -5
# All three must show IDENTICAL IVA% and Ganancias% values

# T042 — SC-010: CA chain names in ARCA Guide AND HLD
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥2 matches in each file

# T042 — SC-006: TLS in HLD
grep -i "TLS" "Docs/Project Blueprint/High-Level Design (HLD).md"
```

**Commit**:
```bash
git add "Docs/Project Blueprint/Architecture Decision Records (ADR).md" \
        "Docs/Project Blueprint/REST API Design.md" \
        "Docs/Project Blueprint/Data Model & Domain Model.md"
git commit -m "spec-09: ADR-036/037 WSCDC/WS Padrón; 2 API endpoints; CertificadoDepositoCereal entity"
```

---

## 7. Session D: Optional Docs + Final Verification Sweep

**Tasks**: T043–T047 | **Phase**: 8
**Entry condition**: Sessions A+B+C checkpoints PASSED.

### D1. Optional Documents (T043–T044)

**Scope guard**: Do NOT add new sections or restructure. One-sentence addition maximum per document.

```bash
# Check Roadmap for ARCA/romaneo context
grep -n "romaneo\|ARCA\|WSCPE\|Phase 1\|MVP" "Docs/Project Blueprint/Roadmap.md" | head -10
# If matches found: add one sentence about WSCDC legal obligation at romaneo reception

# Check PRD
grep -n "romaneo\|ARCA" "Docs/Project Blueprint/PRD.md" | head -10
# Same approach — one sentence if natural fit
```

### D2. Resolve Remaining Markers (T045)

```bash
grep -rni "TBD\|TODO\|approximate" "Docs/Project Blueprint/"
# Replace each ARCA-related marker using research.md findings
# Leave non-ARCA markers untouched — scope guard (SC-008)
```

### D3. Final 11-SC Verification Sweep (T046)

Run the complete block from `quickstart.md §Final Verification Commands`:

```bash
echo "=== SC-001: ≥8 services in ARCA Guide ==="
grep -ci "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\b\|WS Padrón\|Constancia\|WSAA" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

echo "=== SC-002: Zero wrong method name ==="
grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"
echo "(empty output = PASS)"

echo "=== SC-003: WSCDC in 5 mandatory docs ==="
for f in "ARCA Grain Integration Guide.md" "Data Model & Domain Model.md" \
         "High-Level Design (HLD).md" "Architecture Decision Records (ADR).md" \
         "Software Requirements Specification (SRS).md"; do
  count=$(grep -c "WSCDC" "Docs/Project Blueprint/$f" 2>/dev/null)
  echo "  $f: $count"
done

echo "=== SC-004: Zero TBD/TODO/approximate ==="
grep -ri "TBD\|TODO\|approximate" "Docs/Project Blueprint/" | grep -vi "^Binary" | head -10
echo "(empty output = PASS)"

echo "=== SC-005: Error code tables in ≥3 services ==="
grep -c "Error Code\|error code\|Código.*Error" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

echo "=== SC-006: TLS documented ==="
grep -ri "TLS" "Docs/Project Blueprint/"

echo "=== SC-007: SISA % consistency (manual cross-check) ==="
echo "-- ARCA Guide --"
grep -A5 "SISA.*tier\|Ganancias.*%" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md" | head -10
echo "-- ADR --"
grep -A3 "Ganancias.*%" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md" | head -5
echo "-- SRS --"
grep -A3 "Ganancias.*%" \
  "Docs/Project Blueprint/Software Requirements Specification (SRS).md" | head -5

echo "=== SC-008: Non-ARCA content unchanged (spot check) ==="
git diff "Docs/Project Blueprint/" -- | grep "^[+-]" | grep -v "^[+-][+-][+-]" | \
  grep -vi "ARCA\|WSCDC\|WSCPE\|WSLPG\|SIRE\|WS Padrón\|cert\|TLS\|ADR-03[67]\|confirmar\|descargado" | head -20
echo "(minimal output = PASS)"

echo "=== SC-009: ADR-027 label exact match ==="
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"

echo "=== SC-010: CA chain names ==="
echo "-- ARCA Guide --"
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
echo "-- HLD --"
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"

echo "=== SC-011: 2 new endpoints in REST API Design ==="
grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
```

**ALL 11 criteria must show PASS before proceeding.**

### D4. Final Commit + PR (T047)

```bash
git add "Docs/Project Blueprint/"
git commit -m "spec-09: ARCA blueprint enrichment complete — all 11 SC verified"

gh pr create \
  --title "spec-09: ARCA Blueprint Knowledge Update (WSCDC, SIRE, WS Padrón)" \
  --body "Enriches 9 blueprint docs with authoritative ARCA facts from RAG.

- ARCA Guide: 4 new sections (SIRE, WSCDC, WS Padrón, Error Catalog) + 3 enrichments (WSAA, WSLPG, WSCPE)
- HLD: fix confirmarDescargaCPE (4 instances), add WSCDC, add TLS + cert chain in security
- SRS: WSCDC-REQ-01–03, PADRON-REQ-01–03, SISA tier table
- ADR: ADR-036 (WSCDC), ADR-037 (WS Padrón), enrich ADR-007/018/027, fix ADR-027 label
- REST API: POST wscdc/deposit-certificate, GET padron/sisa-status/{cuit}
- Data Model: CertificadoDepositoCereal entity

SC-001 through SC-011 verified."
```

---

## 8. Content Guidelines

| Guideline | Rule |
|-----------|------|
| **Tone** | Technical reference. Factual, precise, third-person |
| **Audience** | Backend engineers implementing ARCA integration |
| **Format** | Markdown tables for catalogs; numbered lists for workflows; Mermaid for diagrams |
| **Accuracy** | All ARCA technical details MUST come from RAG query results — never interpolate |
| **Scope guard** | Edits are ARCA-additive ONLY. If an edit would change non-ARCA content, STOP and document the concern |
| **SISA consistency** | Retention % values MUST be identical in ARCA Guide §6.5, ADR-027, and SRS |
| **Style preservation** | Match each document's existing heading hierarchy, table format, and writing style |
| **ADR citations** | Always `ADR-NNN (Title)` format — never number alone |
| **No TBD** | Never write TBD, TODO, placeholder, or approximate — state constraints explicitly |
| **No code** | No Python, SQL, or shell in blueprint docs — Mermaid diagrams and XML summaries allowed |
| **Edit tool** | Use Edit tool with exact context strings for replacements — never sed |

---

## 9. Critical Domain Facts (Pre-Verified)

These facts are confirmed from prior spec analysis. Use directly without re-verification:

| Fact | Value | Source |
|------|-------|--------|
| Correct CPE discharge method | `confirmarDescargaCPE` | WSCPE WSDL |
| Incorrect method to replace | `descargadoDestinoCPE` | HLD §6 (4 occurrences at lines ~142, ~264, ~341, ~539) |
| WSCDC trigger timing | Romaneo reception, concurrent with WSCPE `confirmarDescargaCPE` | spec-09 clarification |
| ADR-027 current label | "SISA-Tier Retention Calculation at LPG Filing Time" | ADR.md |
| ADR-027 target label | "SISA-Tier Retention Calculation at WSLPG Filing Time" | SC-009 |
| Last existing ADR number | ADR-035 | ADR.md |
| New ADR for WSCDC | ADR-036 | plan.md §4.5 |
| New ADR for WS Padrón | ADR-037 | plan.md §4.6 |
| CertificadoDepositoCereal module | `gravitea_acopio` | constitution §III |
| Weight field precision | `DECIMAL(17,3)` | constitution |
| CertificadoDepositoCereal states | Pendiente → Emitido, Emitido → Anulado, Pendiente → Anulado | data-model.md |
| WSCDC manual version | v4 | `arca_dev_guides` collection |
| WS Padrón A4 manual | v1.3 | `arca_api_specs` collection |
| WSLPG manual | v1.24 | `arca_dev_guides` collection |
| **SISA retention % values** | **MUST come from RAG** (not pre-verified) | research Tasks 3 + 4 |
| WSCDC applies to | All registered acopiadores (no threshold exemption assumed) | A-006 |

---

## 10. Review Checklist

Run after each session, before committing:

- [ ] All edits are strictly ARCA-additive — non-ARCA content unchanged
- [ ] New sections follow the existing document's heading hierarchy and numbering
- [ ] Tables use the same column format as existing tables in the document
- [ ] SISA retention % values are identical wherever they appear (3 documents)
- [ ] All ARCA method names, field names, and error codes come from RAG results
- [ ] No TBD/TODO/placeholder/approximate markers in edited sections
- [ ] ADR citations use `ADR-NNN (Title)` format
- [ ] Cross-references to other sections/documents are correct
- [ ] New entities include `tenant_id FK` for multi-tenant isolation
- [ ] Session checkpoint commands all pass

---

## 11. Done Criteria

Spec-09 is complete when ALL of the following are true:

### SC Verification (11/11 PASS required)

- [ ] SC-001: ARCA Guide documents ≥8 ARCA services/sub-services
- [ ] SC-002: Zero `descargadoDestinoCPE` across ALL 9 blueprint documents
- [ ] SC-003: WSCDC in ≥5 docs (ARCA Guide, Data Model, HLD, ADR, SRS) with substantive content
- [ ] SC-004: Zero TBD/TODO/approximate in any ARCA-related section
- [ ] SC-005: Error code tables for ≥3 ARCA services in ARCA Guide
- [ ] SC-006: TLS minimum version documented in ARCA Guide or HLD
- [ ] SC-007: SISA retention % identical in ARCA Guide §6.5, ADR-027, SRS
- [ ] SC-008: Non-ARCA content shows no substantive changes
- [ ] SC-009: ADR-027 label reads "SISA-Tier Retention Calculation at WSLPG Filing Time" (exact)
- [ ] SC-010: CA chain names in ARCA Guide §3 AND HLD security section
- [ ] SC-011: 2 new endpoints in REST API Design (WSCDC POST + SISA GET)

### New Content Created

- [ ] ARCA Guide §6 SIRE with SOAP methods + batch format + retention tier table
- [ ] ARCA Guide §7 WSCDC with lifecycle + SOAP methods + XML fields + error codes
- [ ] ARCA Guide §8 WS Padrón with getPersona + SISA validation workflow
- [ ] ARCA Guide §9 Cross-Service Error Code Catalog (≥3 services)
- [ ] ADR-036 (WSCDC Integration Decision)
- [ ] ADR-037 (WS Padrón SISA Tier Lookup Decision)
- [ ] CertificadoDepositoCereal entity in Data Model
- [ ] WSCDC POST endpoint in REST API Design
- [ ] SISA GET endpoint in REST API Design
- [ ] WSCDC requirements block (WSCDC-REQ-01–03) in SRS
- [ ] WS Padrón requirements block (PADRON-REQ-01–03) in SRS
- [ ] SISA retention tier table in SRS

### Research Completeness

- [ ] research.md fully populated (all 6 tasks, zero `[FROM RAG]` placeholders)
- [ ] SISA % cross-check between Tasks 3 and 4 completed and documented

### PR Created

- [ ] Final verification sweep: 11/11 SC PASS
- [ ] PR created with title "spec-09: ARCA Blueprint Knowledge Update"
- [ ] PR body lists all changes and SC verification status
