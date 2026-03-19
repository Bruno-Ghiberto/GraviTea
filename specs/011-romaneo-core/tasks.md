# Tasks: Romaneo Core

**Input**: Design documents from `/specs/011-romaneo-core/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: INCLUDED — spec requires 40+ tests, 90%+ coverage (AC-011-014, SC-008).

**Organization**: Tasks organized by user story. Due to tight interdependency between romaneo models, state machine, quality analysis, and merma calculation, the Foundational phase (Phase 2) creates ALL models and the Rust engine. User story phases then add serializers, views, and endpoints incrementally.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US8)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: App scaffolding and package initialization

- [X] T001 Create `backend/apps/acopio/services/__init__.py` empty package init
- [X] T002 Verify `backend/apps/acopio/` app is registered in INSTALLED_APPS and URL routing at `/api/v1/acopio/` (from spec-10)

**Checkpoint**: Services directory exists, acopio app functional from spec-10

---

## Phase 2: Foundational (Models + Rust Engine)

**Purpose**: ALL 3 Django models and the Rust merma engine. BLOCKS all user story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. Models are tightly interdependent — Romaneo references QualityAnalysis and MermaCalculation via OneToOne, and the Rust engine is needed for the merma service.

### Models (A1 agent scope)

- [X] T003 [P] Create Romaneo model with 31 fields across 7 groups, 6-state TextChoices, `save()` override with state machine validation and CONFORME/CERRADO immutability gate, and `_generate_romaneo_number()` helper in `backend/apps/acopio/models/romaneo.py`
- [X] T004 [P] Create QualityAnalysis model with OneToOneField to Romaneo, 9+ quality parameters (6 common + 3 grain-specific nullable), analysis_timestamp, and sample_reference in `backend/apps/acopio/models/quality_analysis.py`
- [X] T005 [P] Create MermaCalculation model with OneToOneField to Romaneo, all merma inputs/intermediates/final weight fields, `save()` and `delete()` overrides enforcing full immutability, and calculated_by FK in `backend/apps/acopio/models/merma_calculation.py`
- [X] T006 Update `backend/apps/acopio/models/__init__.py` to re-export Romaneo, QualityAnalysis, MermaCalculation
- [X] T007 Run `makemigrations gravitea_acopio` to generate `backend/apps/acopio/migrations/0002_romaneo_core.py` and verify migration applies
- [X] T008 [P] Update `backend/apps/acopio/admin.py` with RomaneoAdmin, QualityAnalysisAdmin, MermaCalculationAdmin registrations with list_display, list_filter, search_fields, and readonly_fields
- [X] T009 [P] Update `backend/database/sql/acopio_rls.sql` with RLS policies for acopio_romaneo, acopio_qualityanalysis, acopio_mermacalculation tables (ENABLE + FORCE + tenant_isolation policy + GRANT)

### Rust Merma Engine (A2 agent scope)

- [X] T010 [P] Create `rust/gravitea-core/src/merma.rs` with MermaInput/MermaOutput serde structs, `calculate_merma_internal()` implementing sequential formula (zarandeo→secado→manipuleo→volatil) using rust_decimal, input validation, and `#[pyfunction] pub fn calculate_merma()` PyO3 wrapper
- [X] T011 Add `mod merma;` declaration and `#[pymodule_export] use super::merma::calculate_merma;` to `rust/gravitea-core/src/lib.rs`
- [X] T012 [P] Add Rust unit tests in `merma.rs` (#[cfg(test)] module) covering: trigo reference vector, soja dry case (Hi<=Hf), zero foreign matter, negative weight rejection, invalid JSON rejection (minimum 10 tests)
- [X] T013 Build Rust module with `maturin develop --release` and verify `from gravitea_rust import calculate_merma` works from Python

### Python Merma Service (A3 agent scope)

- [X] T014 Create `backend/apps/acopio/services/merma_engine.py` with: `try/except ImportError` Rust FFI wrapper, `_python_calculate_merma()` pure-Python fallback implementation, `calculate_merma_deductions()` public API function in `backend/apps/acopio/services/merma_engine.py`

**Checkpoint (Gate 1+2)**: All 3 models importable, TenantBoundModel inheritance verified, migration applies, Rust builds + tests pass, merma service returns valid results for test vector

---

## Phase 3: User Story 1 + User Story 6 — Register Romaneo & State Machine (Priority: P1) 🎯 MVP

**Goal**: Create a romaneo in PENDIENTE status with auto-generated number, and enforce the 6-state linear lifecycle with state transition endpoints.

**Independent Test**: Create a romaneo, verify auto-number generation, then walk through all 6 state transitions in sequence verifying each succeeds and out-of-order transitions are rejected.

- [X] T015 [P] [US1] Create RomaneoSerializer (list/create) and RomaneoDetailSerializer (retrieve with nested quality_analysis + merma_calculation) in `backend/apps/acopio/serializers/romaneo.py`
- [X] T016 [P] [US1] Create QualityAnalysisSerializer and MermaCalculationSerializer (read-only nested) in `backend/apps/acopio/serializers/romaneo.py`
- [X] T017 [US1] Create RomaneoViewSet with CRUD (list, create, retrieve, partial_update) and PATCH guard returning 409 for CONFORME/CERRADO in `backend/apps/acopio/views/romaneo.py`
- [X] T018 [US6] Add `confirmar_arribo` action endpoint (POST, PENDIENTE→EN_PROCESO, returns 202) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`
- [X] T019 [P] [US1] Create RomaneoPagination class (PageNumberPagination, page_size=25, max=100) in `backend/apps/acopio/pagination.py`
- [X] T020 [US1] Update `backend/apps/acopio/serializers/__init__.py` to re-export all new serializer classes
- [X] T021 [US1] Update `backend/apps/acopio/views/__init__.py` to re-export RomaneoViewSet, QualityAnalysisViewSet
- [X] T022 [US1] Register `romaneos` route on the DRF router in `backend/apps/acopio/urls.py`

**Checkpoint**: Can create romaneo via POST, list via GET, retrieve via GET with nested QA/MC, confirm arrival via POST action. PATCH blocked on CONFORME/CERRADO.

---

## Phase 4: User Story 2 — Capture Weights (Priority: P1)

**Goal**: Capture gross weight (peso_bruto) during EN_PROCESO→PESADO and tare weight while CONFORME, computing peso_neto_bruto.

**Independent Test**: Record gross weight on EN_PROCESO romaneo (transitions to PESADO), later record tare on CONFORME romaneo (computes net weight).

- [X] T023 [P] [US2] Create PesoBrutoSerializer (peso_bruto_kg required, positive validation) and TaraSerializer (tara_kg required, positive validation) in `backend/apps/acopio/serializers/romaneo.py`
- [X] T024 [US2] Add `peso_bruto` action endpoint (POST, EN_PROCESO→PESADO, sets peso_bruto_kg + ts_pesada_bruta) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`
- [X] T025 [US2] Add `tara` action endpoint (POST, CONFORME only, sets tara_kg + ts_tara, computes peso_neto_bruto_kg, validates bruto > tara) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`

**Checkpoint**: Can record gross weight (→PESADO) and tare weight (while CONFORME), with net weight auto-computed.

---

## Phase 5: User Story 3 — Record Quality Analysis (Priority: P1)

**Goal**: Create, retrieve, and update quality analysis as a 1:1 satellite of romaneo. Transitions romaneo to ANALIZADO.

**Independent Test**: Create QA on a PESADO romaneo with all 9 parameters, verify transition to ANALIZADO, verify update allowed in ANALIZADO but blocked in CONFORME.

- [X] T026 [P] [US3] Create AnalizarSerializer (inline 9+ quality parameter fields) in `backend/apps/acopio/serializers/romaneo.py`
- [X] T027 [US3] Add `analizar` action endpoint (POST, PESADO→ANALIZADO, creates QualityAnalysis record, sets ts_analisis) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`
- [X] T028 [US3] Create QualityAnalysisViewSet (CreateModelMixin + RetrieveModelMixin + UpdateModelMixin + GenericViewSet) nested under romaneo with state guards (create: EN_PROCESO/PESADO, update: ANALIZADO only) in `backend/apps/acopio/views/romaneo.py`
- [X] T029 [US3] Add nested QA URL route (`romaneos/<uuid:romaneo_pk>/quality-analysis/`) in `backend/apps/acopio/urls.py`

**Checkpoint**: Can create QA via analizar action or nested POST, retrieve via nested GET, update via nested PATCH (ANALIZADO only).

---

## Phase 6: User Story 4 + User Story 7 — Calculate Merma & Assign Grade (Priority: P1/P2)

**Goal**: On confirmation (ANALIZADO→CONFORME), calculate sequential merma via Rust engine, create immutable MermaCalculation record, assign grade with bonificacion/rebaja, pin tolerance table version. **IMMUTABILITY GATE**.

**Independent Test**: Confirm a romaneo with known quality params, verify all intermediate merma values match hand-calculated reference, verify MermaCalculation immutable, verify tolerance table version pinned.

- [X] T030 [P] [US4] Create ConfirmarSerializer (grado_asignado required for cereals, optional for oleaginosas) in `backend/apps/acopio/serializers/romaneo.py`
- [X] T031 [US4] Add merma service integration: MermaTable lookup by grain_type + materias_extranas_pct + ts_entrada, input JSON construction, and `calculate_merma_deductions()` call to `backend/apps/acopio/services/merma_engine.py`
- [X] T032 [US4] Add `confirmar` action endpoint (POST, ANALIZADO→CONFORME) that: looks up MermaTable version, calls merma service, creates MermaCalculation record, sets grado_asignado/bonificacion_rebaja_pct/tolerance_table_version/peso_neto_conforme_kg on Romaneo, in `backend/apps/acopio/views/romaneo.py`
- [X] T033 [US7] Add grade assignment logic: GRADO system (cereals: 1/2/3 with bonificacion/rebaja lookup from ToleranceTable) and TOLERANCE system (oleaginosas: grado_asignado=0, progressive rebaja) integrated into the confirmar action in `backend/apps/acopio/views/romaneo.py`

**Checkpoint**: Can confirm romaneo with grade, merma calculated correctly, MermaCalculation immutable, tolerance version pinned. This is the IMMUTABILITY GATE — romaneo locked after this point.

---

## Phase 7: User Story 5 — Merma Preview (Priority: P2)

**Goal**: Non-persisting merma projection without creating MermaCalculation record.

**Independent Test**: Request merma preview on ANALIZADO romaneo, verify projected values returned, verify no database record created.

- [X] T034 [US5] Add `merma_preview` action endpoint (GET, available when PESADO/ANALIZADO with QA, calls merma service without persisting, returns projected deductions) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`

**Checkpoint**: Can preview merma deductions without committing to confirmation.

---

## Phase 8: User Story 8 — Close Romaneo (Priority: P2)

**Goal**: Close romaneo (CONFORME→CERRADO) after tare captured. Returns 202 (async WSCPE).

**Independent Test**: Close a CONFORME romaneo with tara_kg present, verify transition to CERRADO with 202 response. Verify closure rejected without tara_kg.

- [X] T035 [US8] Add `cerrar` action endpoint (POST, CONFORME→CERRADO, requires tara_kg present, returns 202 Accepted) to RomaneoViewSet in `backend/apps/acopio/views/romaneo.py`

**Checkpoint**: Full romaneo lifecycle complete — PENDIENTE through CERRADO.

---

## Phase 9: Test Suite

**Purpose**: Comprehensive test coverage for all models, API endpoints, merma correctness, and tenant isolation.

### Test Fixtures

- [X] T036 Update `backend/tests/acopio/conftest.py` with romaneo fixtures: romaneo_factory (with user_factory for operator_id), romaneo_en_proceso, romaneo_pesado, romaneo_analizado, romaneo_conforme, quality_analysis_factory, merma_table_factory, tolerance_table_factory

### Model Tests

- [X] T037 [P] Create model unit tests in `backend/tests/acopio/test_romaneo_models.py`: romaneo creation (31 fields), state machine (6 valid transitions + 5 invalid rejections), CONFORME immutability gate (field changes blocked except tare), CERRADO full immutability, romaneo_number auto-generation (per-branch sequential, ROM-YYYY-NNNNN format), state transition timestamps (ts_entrada, ts_pesada_bruta, ts_analisis, ts_tara)

### Quality Analysis Tests

- [X] T038 [P] Create QA tests in `backend/tests/acopio/test_quality_analysis.py`: QA creation with all 9 parameters at correct precision, OneToOne constraint (duplicate rejected with IntegrityError), grain-specific nullable fields (hectolitre cereals only, protein trigo only, green soja only), update guard (ANALIZADO only, 409 for CONFORME/CERRADO)

### Merma Calculation Tests

- [X] T039 [P] Create merma correctness tests in `backend/tests/acopio/test_merma_calculation.py`: trigo reference vector (Hi=15.2%, Hf=13.5%, ME=1.8%, verify all intermediates), soja dry case (Hi=12.0%, Hf=12.5%, secado=0, manipuleo NOT applied), edge case (all parameters zero, only volatil applied), Hf vs humedad_base assertion (~168 kg error on 30t truck), MermaCalculation immutability (save raises ValueError, delete raises ValueError), tolerance table version pinning (table update does not change existing romaneo grade), merma band not found (foreign matter % outside all MermaTable bands returns clear error)

### Rust FFI Tests

- [X] T040 [P] Create Rust FFI parity tests in `backend/tests/acopio/test_merma_rust.py`: 10+ test vectors comparing Rust `calculate_merma()` output with Python `_python_calculate_merma()` for identical inputs (trigo, maiz, soja, girasol, sorgo, cebada), error handling (invalid JSON, negative weights, out-of-range percentages)

### API Integration Tests

- [X] T041 [P] Create API integration tests in `backend/tests/acopio/test_romaneo_api.py`: POST create romaneo (201, auto-number), GET list (200, paginated, tenant-filtered), GET retrieve with nested QA+MC (200), PATCH update (200 for PENDIENTE, 409 for CONFORME), 6 state transition actions (correct status codes: 202 for confirmar-arribo/cerrar, 200 for others), merma-preview (200 with projected values), 3 QA nested endpoints (201 create, 200 retrieve, 200/409 update), tenant isolation (cross-tenant 404), invalid state transition (409 with type/current_status/attempted_transition)

### Test Execution

- [X] T042 Run full test suite via `bash scripts/run-tests-external.sh -n spec11-final tests/acopio/` and verify: status=PASSED, 40+ tests collected, 0 failures, 90%+ coverage on new code

**Checkpoint (Gate 4)**: All tests green, minimum 40 tests, 90%+ coverage.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [X] T043 Verify all 14 API endpoints return correct HTTP status codes per contracts/api.md
- [X] T044 Verify all 14 acceptance criteria (AC-011-001 through AC-011-014) pass per 11-specify.md
- [X] T045 [P] Run quickstart.md setup commands to verify end-to-end workflow
- [X] T046 Verify composite indexes exist on acopio_romaneo table: (tenant_id, status, ts_entrada), (tenant_id, branch_id, ts_entrada), (tenant_id, campaign_id, grain_type_id)
- [X] T047 Verify UniqueConstraints: (tenant, cpe_numero) and (tenant, romaneo_number) enforced

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1+US6 (Phase 3)**: Depends on Foundational — first user story increment
- **US2 (Phase 4)**: Depends on Phase 3 (needs RomaneoViewSet)
- **US3 (Phase 5)**: Depends on Phase 3 (needs RomaneoViewSet + URLs)
- **US4+US7 (Phase 6)**: Depends on Phase 5 (needs QualityAnalysis created)
- **US5 (Phase 7)**: Depends on Phase 5 (needs QA for preview data)
- **US8 (Phase 8)**: Depends on Phase 4 (needs tara endpoint) + Phase 6 (needs CONFORME state)
- **Tests (Phase 9)**: Depends on ALL implementation phases complete
- **Polish (Phase 10)**: Depends on Phase 9 (tests green)

### Agent Team Mapping

| Phase | Primary Agent | Parallel Agents |
|-------|--------------|-----------------|
| 2 (Models) | A1 | A2 (Rust), A3 (service) in parallel |
| 3-8 (API) | A4 (serializers), A5 (views) | Sequential within each phase |
| 9 (Tests) | A6 | All test files in parallel |

### Within Each User Story Phase

1. Serializers before views (views depend on serializers)
2. Views before URL registration
3. State transition actions after CRUD base

### Parallel Opportunities

Within Phase 2 (Foundational):
```
T003 (Romaneo model)  |  T004 (QA model)  |  T005 (MC model)     ← all [P]
T008 (admin.py)       |  T009 (RLS)       |  T010 (Rust merma)   ← all [P]
T012 (Rust tests)     |  T014 (Python merma service)             ← all [P]
```

Within Phase 9 (Tests):
```
T037 (model tests) | T038 (QA tests) | T039 (merma tests) | T040 (Rust FFI) | T041 (API tests) ← all [P]
```

---

## Implementation Strategy

### MVP First (Phase 1-3: Setup + Foundational + US1/US6)

1. Complete Phase 1: Setup (1 task)
2. Complete Phase 2: Foundational — models + Rust + merma service (14 tasks)
3. Complete Phase 3: US1+US6 — create romaneo + state machine endpoints (8 tasks)
4. **STOP and VALIDATE**: Create a romaneo, walk through all state transitions
5. This gives a functional romaneo lifecycle without quality analysis or merma

### Full Implementation (Phase 4-8)

6. Phase 4: US2 — weight capture (3 tasks)
7. Phase 5: US3 — quality analysis (4 tasks)
8. Phase 6: US4+US7 — merma calculation + grading (4 tasks)
9. Phase 7: US5 — merma preview (1 task)
10. Phase 8: US8 — close romaneo (1 task)

### Verification (Phase 9-10)

11. Phase 9: Full test suite (7 tasks)
12. Phase 10: Polish and final validation (5 tasks)

### 6-Agent Team Execution

When using the tmux multi-agent team from 11-plan.md:
- **Wave 1**: A1 (T003-T009) + A2 (T010-T013) in parallel → Gate 1
- **Wave 2**: A3 (T014) + A4 (T015-T016, T023, T026, T030) in parallel → Gate 2
- **Wave 3**: A5 (T017-T022, T024-T025, T027-T029, T031-T035) sequential → Gate 3
- **Wave 4**: A6 (T036-T042) → Gate 4
- **Wave 5**: All verify (T043-T047)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 and US6 are combined (romaneo creation and state machine are inseparable)
- US4 and US7 are combined (merma calculation and grade assignment happen in the same confirmar action)
- All tests use `scripts/run-tests-external.sh` — NEVER run pytest inside Claude Code
- Commit after each phase completion
- Stop at any checkpoint to validate independently
