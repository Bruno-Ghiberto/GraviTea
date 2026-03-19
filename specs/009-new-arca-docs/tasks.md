# Tasks: New ARCA Docs — Blueprint Knowledge Update

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Total tasks**: 48 | **Parallelizable**: 18

> **Blueprint Update spec** — all tasks produce edits to existing markdown documents in
> `Docs/Project Blueprint/`. No code is written. Each task is independently verifiable
> via text search or direct document review.

---

## Task ID Reference

| Phase | Stories | Task Range | Count |
|-------|---------|-----------|-------|
| Phase 1 — Setup | — | T001–T003 | 3 |
| Phase 2 — Foundational Research | — | T004–T009 | 6 |
| Phase 3 — US1: ARCA Guide Enrichment | US1 | T010–T020 | 11 |
| Phase 4 — US2: WSCDC Blueprint Suite | US2 | T021–T025 | 5 |
| Phase 5 — US3: Method Name Corrections | US3 | T026–T030 | 5 |
| Phase 6 — US4: SIRE / WS Padrón | US4 | T031–T036 | 6 |
| Phase 7 — US5: WSAA Certs & TLS | US5 | T037–T042 (incl. T041b) | 7 |
| Phase 8 — Polish & Final Sweep | — | T043–T047 | 5 |

---

## Phase 1: Setup

> Verify environment is ready. All subsequent phases depend on Phase 1.

- [x] T001 Confirm active branch is `009-new-arca-docs` (run `git branch --show-current`)
- [x] T002 Verify Qdrant health at localhost:6333 and Ollama availability at localhost:11434 via `curl -s http://localhost:6333/healthz`
- [x] T003 Confirm ARCA RAG collections have content: run `.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA authentication token' -l 2` and verify non-empty results; if empty, run `ingest_arca_qdrant.py --collection all` before proceeding

---

## Phase 2: Foundational Research

> Populate `specs/009-new-arca-docs/research.md` with authoritative ARCA facts before
> any document editing begins. All Phase 3+ tasks depend on research findings.
> Tasks T004–T009 are fully parallelizable — run them in any order or simultaneously.

- [x] T004 [P] Run Research Task 1 (WSAA cert chain + TLS) — execute all 5 queries from `specs/009-new-arca-docs/research.md` §Task 1 against `arca_setup_certs` collection and populate findings (CA names, validity dates, TLS version, ADMINREL steps, CSR DN fields) in `specs/009-new-arca-docs/research.md`
- [x] T005 [P] Run Research Task 2 (WSCPE method verification) — execute all 5 queries from `specs/009-new-arca-docs/research.md` §Task 2 against `arca_dev_guides` collection and populate findings (confirmed method name, full state machine, XML field catalog, error codes) in `specs/009-new-arca-docs/research.md`
- [x] T006 [P] Run Research Task 3 (WSLPG Form 1116-B/C + SISA tiers) — execute all 5 queries from `specs/009-new-arca-docs/research.md` §Task 3 against `arca_dev_guides` collection and populate findings (Form 1116-B/C field tables, **SISA retention tier table with exact IVA% and Ganancias%**, error codes) in `specs/009-new-arca-docs/research.md`
- [x] T007 [P] Run Research Task 4 (SIRE General + IVA) — execute all 6 queries from `specs/009-new-arca-docs/research.md` §Task 4 against `arca_dev_guides` and `arca_api_specs` collections and populate findings (SIRE SOAP methods, SIRE IVA SOAP methods, batch lote format) in `specs/009-new-arca-docs/research.md`
- [x] T008 [P] Run Research Task 5 (WSCDC) — execute all 7 queries from `specs/009-new-arca-docs/research.md` §Task 5 against `arca_dev_guides` collection and populate findings (legal basis, primary SOAP method name, full XML field catalog, lifecycle states, error codes, trigger timing confirmation) in `specs/009-new-arca-docs/research.md`
- [x] T009 [P] Run Research Task 6 (WS Padrón A4 + Constancia Inscripción) — execute all 5 queries from `specs/009-new-arca-docs/research.md` §Task 6 against `arca_api_specs` collection and populate findings (getPersona method signature, response field catalog, SISA category field name, WS Constancia method name, validation workflow) in `specs/009-new-arca-docs/research.md`

> **Research gate**: Before proceeding to Phase 3, confirm the SISA % values in T006 and T007 findings match. If they differ, use WSLPG (T006) as authoritative and note discrepancy in `research.md`.

---

## Phase 3 — US1: ARCA Guide Enrichment

**Story**: As the implementation team lead, I need the ARCA Grain Integration Guide to contain authoritative SOAP method names, XML field catalogs, and error codes from official ARCA developer manuals.

**Independent test**: All 11 ARCA Guide checkpoint commands in `plan.md §Step 1.5` pass:
- `grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` → 0
- `grep -i "AFIPRootCA\|AC_Raiz" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` → ≥2 matches
- `grep -c "Error Code\|error code" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` → ≥3

**Depends on**: Phase 2 complete (all 6 research tasks populated)

- [x] T010 [US1] Verify baseline: run `grep -n "^## " "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` and confirm current headings §1–§9 are intact before editing
- [x] T011 [US1] Renumber existing §6→§10, §7→§11, §8→§12, §9→§13 in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` — update all heading texts and any internal cross-references that mention these section numbers
- [x] T012 [US1] Update §2 Service Overview table in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` — add rows for WSCDC (Grain Deposit Certificate), SIRE IVA (IVA Retention), WS Padrón A4 (CUIT/SISA Lookup), and WS Constancia Inscripción; verify all 8 services are represented
- [x] T013 [US1] Enrich §3 WSAA in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` — add production cert chain table, homologación cert chain table, CSR DN fields table, TLS minimum version subsection, and ADMINREL DelegarWS numbered workflow using findings from T004 in `specs/009-new-arca-docs/research.md`
- [x] T014 [US1] Enrich §4 WSLPG in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` — add Form 1116-B field table (name, type, length, required), Form 1116-C field table, SISA retention tier table (exact IVA% and Ganancias% from T006), and WSLPG error code table using findings from T006
- [x] T015 [US1] Enrich §5 WSCPE in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` — add CPE state machine table (state, valid transitions, trigger method), XML field catalog table, and WSCPE error code table using findings from T005; verify `confirmarDescargaCPE` is used throughout §5
- [x] T016 [US1] Write new §6 SIRE section in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` with subsections: 6.1 Overview, 6.2 SIRE General SOAP methods table, 6.3 SIRE IVA SOAP methods table, 6.4 Batch Lote Import Format description, 6.5 Retention Tier Table (values must match §4 WSLPG SISA table exactly) using findings from T007
- [x] T017 [US1] Write new §7 WSCDC section in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` with subsections: 7.1 Legal Obligation (regulatory basis, who must use it), 7.2 Certificate Lifecycle (states + transitions table), 7.3 SOAP Methods table, 7.4 XML Field Catalog table (especie, kg, humidity, establishment + all RAG fields), 7.5 Error Codes table, 7.6 Integration Pattern (concurrent with WSCPE confirmarDescargaCPE at romaneo time) using findings from T008
- [x] T018 [US1] Write new §8 WS Padrón A4 & WS Constancia Inscripción section in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` with subsections: 8.1 Purpose, 8.2 WS Padrón A4 getPersona method + response field catalog table, 8.3 WS Constancia Inscripción method, 8.4 SISA Validation Workflow (numbered steps: getPersona → extract SISA → map to retention tier) using findings from T009
- [x] T019 [US1] Write new §9 Cross-Service Error Code Catalog in `Docs/Project Blueprint/ARCA Grain Integration Guide.md` with subsections: 9.1 WSCPE Error Codes (from §5), 9.2 WSLPG Error Codes (from §4), 9.3 WSCDC Error Codes (from §7); add §9.4 SIRE if RAG returned error codes in T007
- [x] T020 [US1] Run ARCA Guide checkpoint: execute all 5 verification commands from `plan.md §Step 1.5`; confirm SC-001 (≥8 services), SC-002 (0 wrong method), SC-005 (≥3 error code sections), SC-006 (TLS documented), SC-010 (CA chain names present) all pass before proceeding

---

## Phase 4 — US2: WSCDC Integration Across Blueprint Suite

**Story**: As the implementation team lead, I need WSCDC documented across 5 mandatory blueprint documents so the romaneo spec (spec-11) has complete requirements.

**Independent test**: `for f in "ARCA Grain Integration Guide.md" "Data Model & Domain Model.md" "High-Level Design (HLD).md" "Architecture Decision Records (ADR).md" "Software Requirements Specification (SRS).md"; do echo "$f: $(grep -c "WSCDC" "Docs/Project Blueprint/$f")"; done` → each file shows ≥1

**Depends on**: Phase 3 complete (ARCA Guide §7 WSCDC section written — serves as content reference)

- [x] T021 [P] [US2] Audit then add WSCDC requirements to `Docs/Project Blueprint/Software Requirements Specification (SRS).md` — first grep for generic "ARCA integration" / "ARCA system" wording (`grep -in "ARCA integration\|ARCA system" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"`) and update each match to reference the specific service name (e.g., "WSAA + WSCPE integration" or "WSLPG liquidation"); then add WSCDC requirements block: WSCDC-REQ-01 (invoke WSCDC on romaneo confirmation), WSCDC-REQ-02 (persist arca_nro_certificado), WSCDC-REQ-03 (WSCDC errors non-blocking for romaneo record); each requirement must have an ID and 1–3 sentence description per SC-003
- [x] T022 [P] [US2] Add WSCDC to §6 ARCA Integration Architecture in `Docs/Project Blueprint/High-Level Design (HLD).md` — add WSCDC row to integration table (exact SOAP method from T008 findings, trigger: romaneo reception, response: nro_certificado), add WSCDC node to Mermaid diagram if present, add note "fires concurrent with WSCPE confirmarDescargaCPE"
- [x] T023 [P] [US2] Add `CertificadoDepositoCereal` entity to `Docs/Project Blueprint/Data Model & Domain Model.md` near Romaneo entity — include full field table from `specs/009-new-arca-docs/data-model.md`, state transitions, relationship note "Romaneo 1 → 0..1 CertificadoDepositoCereal", and module assignment (gravitea_acopio)
- [x] T024 [US2] Write ADR-036 WSCDC Integration Decision in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` after ADR-035 — include Date: 2026-03-18, Status: Accepted, Context (legal obligation, trigger point, absence from specs 01-08), Decision (invoke WSCDC [exact method] concurrent with WSCPE at romaneo reception, non-blocking error handling), Consequences (spec-11 dependency, CertificadoDepositoCereal entity, REST proxy endpoint), References using T008 RAG findings
- [x] T025 [US2] Run WSCDC coverage checkpoint: verify SC-003 by checking each of the 5 mandatory docs has substantive WSCDC content (≥1 requirement ID or entity field + 1–3 sentence description); run `grep -c "WSCDC" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"` → ≥2

---

## Phase 5 — US3: Cross-Document Method Name Correction

**Story**: As a technical architect reviewing blueprints before implementation, I need all ARCA method names to be consistent and correct across all documents.

**Independent test**: `grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"` → empty output (0 files)

**Depends on**: Phase 3 (confirms ARCA Guide uses correct name); Phase 4 T022 (HLD WSCDC addition should already use correct name)
**Note**: Tasks T026–T029 edit the same file (HLD) — run sequentially within a single session.

- [x] T026 [US3] Fix `descargadoDestinoCPE` → `confirmarDescargaCPE` at line 142 in `Docs/Project Blueprint/High-Level Design (HLD).md` — table row context: "CPE lifecycle calls (confirmarArriboCPE, descargadoDestinoCPE, confirmacionDefinitivaCPEAutomotor)"; replace only `descargadoDestinoCPE` in this string
- [x] T027 [US3] Fix `descargadoDestinoCPE` → `confirmarDescargaCPE` at line 264 in `Docs/Project Blueprint/High-Level Design (HLD).md` — Mermaid diagram node: `descargadoDestinoCPE`; update the node label only, preserve Mermaid syntax
- [x] T028 [US3] Fix `descargadoDestinoCPE` → `confirmarDescargaCPE` at line 341 in `Docs/Project Blueprint/High-Level Design (HLD).md` — state machine prose: "→ Descargada (descargadoDestinoCPE — grain unloaded at destination)"; update method name only, preserve surrounding text
- [x] T029 [US3] Fix `descargadoDestinoCPE` → `confirmarDescargaCPE` at line 539 in `Docs/Project Blueprint/High-Level Design (HLD).md` — numbered list: "2. `descargadoDestinoCPE` — grain discharge at destination"; update method name only
- [x] T030 [US3] Run SC-002 verification: `grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"` → must return empty; if any file returned, fix remaining occurrences before proceeding

---

## Phase 6 — US4: SIRE Retention and WS Padrón Documentation

**Story**: As the producer accounts module designer, I need SIRE SOAP methods, batch format, and WS Padrón SISA lookup documented so that spec-13 Producer Accounts has exact API references.

**Independent test**:
- `grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"` → ≥2
- SISA % values identical in ARCA Guide §6.5, ADR-027, and SRS (SC-007)

**Depends on**: T006 (SISA tier values settled in research.md); T007 (SIRE methods); T009 (WS Padrón method); T016 (ARCA Guide §6 SIRE written as reference)

- [x] T031 [P] [US4] Add WS Padrón requirements block to `Docs/Project Blueprint/Software Requirements Specification (SRS).md` — add PADRON-REQ-01 (query getPersona(CUIT) at romaneo time), PADRON-REQ-02 (use SISA category for WSLPG retention %s), PADRON-REQ-03 (cache WS Padrón responses 24h per CUIT); each requirement must have ID + 1–3 sentence description
- [x] T032 [P] [US4] Add SISA retention tier table to `Docs/Project Blueprint/Software Requirements Specification (SRS).md` — exact IVA% and Ganancias% values from T006 research findings; table must be identical to ARCA Guide §6.5 values (SC-007)
- [x] T033 [P] [US4] Add `POST /api/v1/arca/wscdc/deposit-certificate` endpoint to `Docs/Project Blueprint/REST API Design.md` — include request body fields (romaneo_id, grain_species, kg_received, humidity_percent, establishment_id), response fields (certificado_id, nro_certificado, estado, created_at), error responses (400/404/409/422/503) per `specs/009-new-arca-docs/contracts/api-contract.md`
- [x] T034 [P] [US4] Add `GET /api/v1/arca/padron/sisa-status/{cuit}` endpoint to `Docs/Project Blueprint/REST API Design.md` — include path parameter (cuit, 11 digits), response fields (cuit, sisa_category, iva_retention_percent, ganancias_retention_percent, inscripto, cache_expires_at, source), error responses (400/404/503) per `specs/009-new-arca-docs/contracts/api-contract.md`
- [x] T035 [US4] Write ADR-037 WS Padrón A4 SISA Tier Lookup Decision in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` after ADR-036 — include Date: 2026-03-18, Status: Accepted, Context (SISA tier required for WSLPG retention calculation, need authoritative source at romaneo time), Decision (query getPersona(CUIT) via WS Padrón A4, cache 24h per CUIT in Redis, use SISA category → tier lookup at liquidation), Consequences (REST endpoint, Redis cache, spec-13 dependency), References
- [x] T036 [US4] Run US4 checkpoint: SC-007 (`grep -i "Ganancias.*%" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` values must match ADR-027 and SRS exactly — manual visual comparison); SC-011 (`grep -c "wscdc\|sisa-status" "Docs/Project Blueprint/REST API Design.md"` → ≥2)

---

## Phase 7 — US5: WSAA Certificate Chain and TLS Documentation

**Story**: As the security architect, I need WSAA certificate lifecycle, ADMINREL delegation, and TLS requirements precisely documented so multi-tenant certificate management is built correctly.

**Independent test**:
- `grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` → ≥2 matches (SC-010)
- `grep -i "TLS" "Docs/Project Blueprint/High-Level Design (HLD).md"` → ≥1 match with version number (SC-006)

**Depends on**: T004 (WSAA cert chain research findings); T013 (ARCA Guide §3 WSAA enriched — serves as reference)

- [x] T037 [US5] Fix ADR-027 label in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — change `"SISA-Tier Retention Calculation at LPG Filing Time"` to `"SISA-Tier Retention Calculation at WSLPG Filing Time"` (exact text per SC-009); update heading text only, do not alter ADR-027 content
- [x] T038 [US5] Enrich ADR-007 (WSAA) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — add production CA chain (AFIPRootCA2 → Computadores, with validity dates from T004), homologación chain (AC_Raiz_Homo → ComputadoresTest, with validity dates), and ADMINREL delegation rationale using T004 findings
- [x] T039 [US5] Enrich ADR-018 (WSCPE) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — add statement confirming `confirmarDescargaCPE` is the WSDL-authoritative method name, note that `descargadoDestinoCPE` was an error in earlier docs (now corrected), and cross-reference ARCA Guide §5 for full state machine
- [x] T040 [US5] Enrich ADR-027 (SIRE/WSLPG retention) in `Docs/Project Blueprint/Architecture Decision Records (ADR).md` — add exact SISA tier retention percentages (from T006, must match ARCA Guide §6.5 and SRS exactly per SC-007), add reference to SIRE SOAP methods `emitirRetencion` and `emitirRetencionIVA` from T007 findings
- [x] T041 [P] [US5] Add TLS minimum version to security section of `Docs/Project Blueprint/High-Level Design (HLD).md` — first run `grep -n "^## [0-9].*[Ss]ecur" "Docs/Project Blueprint/High-Level Design (HLD).md"` to find exact section, then add note "ARCA production connections require a minimum TLS version of [VERSION FROM T004] as per ARCA TLS migration schedule"
- [x] T041b [US5] Add WSAA certificate chain CA names and validity dates to the HLD security section in `Docs/Project Blueprint/High-Level Design (HLD).md` — in the same section found by T041's grep, insert a "WSAA Certificate Chain" subsection (or table) documenting production chain (AFIPRootCA2 → Computadores, validity dates from T004 findings) and homologación chain (AC_Raiz_Homo → ComputadoresTest, validity dates from T004); this satisfies the HLD half of FR-011 and SC-010
- [x] T042 [US5] Run US5 checkpoint: SC-009 (`grep "SISA-Tier Retention Calculation at WSLPG Filing Time" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"` → 1 match), SC-010 CA chain in ARCA Guide (`grep -i "AFIPRootCA\|AC_Raiz" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"` → ≥2) **AND** in HLD (`grep -i "AFIPRootCA\|AC_Raiz" "Docs/Project Blueprint/High-Level Design (HLD).md"` → ≥2), SC-006 (TLS in HLD → ≥1), SC-007 (manual SISA % cross-check across ARCA Guide/ADR-027/SRS → identical)

---

## Phase 8: Polish & Final SC Sweep

> Resolve any remaining gaps and run the complete 11-SC verification sweep before PR.

- [x] T043 Optional — check `Docs/Project Blueprint/Roadmap.md` for ARCA/romaneo mentions: run `grep -n "romaneo\|ARCA\|WSCPE\|Phase 1\|MVP" "Docs/Project Blueprint/Roadmap.md"` and if found, add one sentence about WSCDC legal obligation at romaneo reception; do NOT add new sections
- [x] T044 Optional — check `Docs/Project Blueprint/PRD.md` for ARCA/romaneo mentions using same approach as T043; add one sentence if natural fit exists
- [x] T045 Resolve any remaining TBD/TODO/approximate markers in ARCA sections: run `grep -rni "TBD\|TODO\|approximate" "Docs/Project Blueprint/"` and replace each ARCA-related marker using research.md findings; confirm 0 ARCA-related markers remain (SC-004)
- [x] T046 Run complete final verification sweep — execute all 11 SC commands from `specs/009-new-arca-docs/quickstart.md §Final Verification Commands` and record PASS/FAIL for each SC-001 through SC-011; all must PASS before creating PR
- [x] T047 Create PR: `git add "Docs/Project Blueprint/"` then commit with message "spec-09: ARCA blueprint enrichment complete — WSCDC, SIRE, WS Padrón; 11 SC verified"; then `gh pr create --title "spec-09: ARCA Blueprint Knowledge Update" --body "Enriches 9 blueprint docs with ARCA RAG facts. Adds WSCDC (ADR-036), WS Padrón (ADR-037), SIRE section. Fixes confirmarDescargaCPE in HLD. CertificadoDepositoCereal entity. 2 new REST endpoints. SC-001–SC-011 verified."`

---

## Dependencies

```text
Phase 1 (Setup)
    └─► Phase 2 (Foundational Research — T004–T009 parallelizable)
           └─► Phase 3 (US1: ARCA Guide — T010–T020 sequential, same file)
                  ├─► Phase 4 (US2: WSCDC Suite — T021/T022/T023 parallelizable)
                  │      └─► T024 ADR-036 (needs T021/T022/T023 context)
                  ├─► Phase 5 (US3: Method Name Fixes — independent of Phase 4)
                  ├─► Phase 6 (US4: SIRE/WS Padrón — T031/T032/T033/T034 parallelizable)
                  │      └─► T035 ADR-037 (needs T031/T032/T033/T034 context)
                  └─► Phase 7 (US5: WSAA Certs — T037–T040 sequential same file, T041 parallel)
                         └─► Phase 8 (Polish + Final SC Sweep)
```

**Key dependency notes**:
- T006 WSLPG/SISA research → T014 (ARCA Guide §4), T032 (SRS SISA table), T040 (ADR-027 enrichment) — same % values must propagate identically
- T013 ARCA Guide §3 WSAA → T038 ADR-007 — same cert chain facts
- T017 ARCA Guide §7 WSCDC → T024 ADR-036 — WSCDC section as content reference
- T022 HLD WSCDC + T026-T029 method fixes both touch HLD — run T026-T029 AFTER T022 is complete

---

## Parallel Execution Examples

### Phase 2 Research (all 6 in parallel)
Open 6 terminal windows or run in background:
```bash
# Terminal 1
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA production certificate chain AFIPRootCA' -c arca_setup_certs -l 5

# Terminal 2
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCPE confirmarDescargaCPE method name WSDL' -c arca_dev_guides -l 5

# Terminal 3
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG SISA retention tier percentages IVA Ganancias' -c arca_dev_guides -l 5

# Terminal 4
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'SIRE emitirRetencion SOAP method parametros' -c arca_dev_guides -l 5

# Terminal 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSCDC SOAP methods informar deposito cereal' -c arca_dev_guides -l 5

# Terminal 6
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WS Padron A4 getPersona CUIT method SOAP' -c arca_api_specs -l 5
```

### After Phase 3 — Documents can be edited in parallel (different files)
| Parallel Batch | Tasks | Files Touched |
|---------------|-------|--------------|
| Batch A | T021, T022, T023 | SRS + HLD + Data Model |
| Batch B | T026–T029 | HLD only (sequential within batch) |
| Batch C | T031, T032, T033, T034 | SRS + REST API Design |

**Note**: T021 (SRS WSCDC) and T031/T032 (SRS WS Padrón) touch the same file — run T021 first (Phase 4) then T031/T032 (Phase 6).

---

## Implementation Strategy

**MVP Scope** (minimum to unblock specs 10–13):
- Phase 1 + Phase 2 (research) — REQUIRED
- Phase 3 (ARCA Guide) — US1 P1: highest value, blocks all others
- Phase 4 T021 + T023 + T024 (SRS WSCDC req + Data Model entity + ADR-036) — minimum WSCDC coverage for SC-003

**Full delivery** adds Phases 5–8 for method name corrections, REST API endpoints, ADR enrichments, TLS documentation, and final SC verification.

**Session mapping** (from `quickstart.md`):
| Session | Phases | Tasks |
|---------|--------|-------|
| Session A | 1 + 2 + 3 | T001–T020 |
| Session B | 4 + 5 | T021–T030 |
| Session C | 6 + 7 | T031–T042 |
| Session D | 8 | T043–T047 |
