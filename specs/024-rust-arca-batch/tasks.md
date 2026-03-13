# Tasks: ARCA CAEA Batch Builder Acceleration

**Input**: Design documents from `/specs/024-rust-arca-batch/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md, instruction-plan.md

**Tests**: Included — spec SC-003 requires ≥10 cargo tests + ≥15 pytest integration tests.

**Organization**: Tasks grouped by user story for independent implementation and testing.

**Note**: Task IDs in this file (T001-T023) supersede plan.md IDs (T001-T020) for execution. The renumbering reflects user-story-centric reorganization; the actual work is equivalent.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Error variant and module registration — prerequisites for Rust core.

- [X] T001 Add `ARCABuildError(String)` variant to `rust/gravitea-core/src/errors.rs` mapping to `PyRuntimeError`
- [X] T002 Register `mod arca;` and `#[pymodule_export] use super::arca::build_caea_batch_request;` in `rust/gravitea-core/src/lib.rs`

---

## Phase 2: Foundational (Rust Core — Blocking Prerequisites)

**Purpose**: Serde structs and `build_caea_batch_request` PyO3 function. MUST complete before any Python integration.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. Read `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design before starting.

- [X] T003 Create input serde structs (`ComprobanteInput`, `AlicIvaInput`, `TributoInput`, `CbteAsocInput`) with `#[derive(Deserialize)]` in `rust/gravitea-core/src/arca.rs`
- [X] T004 Create output serde structs (`FECAEADetRequest`, `IvaWrapper`, `AlicIvaOutput`, `TributosWrapper`, `TributoOutput`, `CbtesAsocWrapper`, `CbteAsocOutput`) with `#[derive(Serialize)]` and exact key renames (`ImpIVA`, `CAEA`) in `rust/gravitea-core/src/arca.rs`
- [X] T005 Implement `build_caea_batch_request(comprobantes_json: &str, caea: &str, default_cuit: &str) -> PyResult<String>` with all conversion logic (str→f64, concepto guard, tributos guard, CUIT fallback, empty array handling, GIL release via `py.detach()`) in `rust/gravitea-core/src/arca.rs`
- [X] T006 Write ≥10 cargo tests covering: basic comprobante (Concepto 1), service dates (Concepto 2/3), IVA breakdown (single/multi rate), tributos (imp_trib>0 and imp_trib=0), CbtesAsoc (with/without cuit), empty optional arrays, defaults (mon_id→PES, mon_cotiz→1.0), large batch (100 items), negative imp_trib, large float values in `rust/gravitea-core/src/arca.rs`

**Checkpoint**: `cargo test` passes with ≥10 tests — Rust function ready for Python integration.

---

## Phase 3: User Story 1 — CAEA Batch Reporting Under Deadline (Priority: P1) 🎯 MVP

**Goal**: Build batch request structure for 20-100 comprobantes with Rust acceleration, producing exact ARCA SOAP dict structures.

**Independent Test**: Provide 50 sample comprobantes with IVA and tributos, verify output matches ARCA structure with correct key names and float values, accelerated path completes in <5ms.

### Implementation for User Story 1

- [X] T007 [US1] Create `backend/apps/facturacion/arca/caea_engine.py` with `_USE_RUST` flag, `_RUST_BATCH_THRESHOLD = 10`, `build_det_list()` dispatcher, `_build_rust()` wrapper (json.dumps→Rust FFI→json.loads) following `sync_engine.py` pattern
- [X] T008 [US1] Extract Python inner loop from `caea.py` lines 232-302 into `_build_python()` fallback in `backend/apps/facturacion/arca/caea_engine.py` using `default_cuit` parameter instead of `self.cuit`
- [X] T009 [US1] Replace inner loop in `backend/apps/facturacion/arca/caea.py` `informar_comprobantes()` (lines 231-302) with `from .caea_engine import build_det_list` + single call `build_det_list(comprobantes, caea, self.cuit)`
- [X] T010 [P] [US1] Add `build_caea_batch_request(comprobantes_json: str, caea: str, default_cuit: str) -> str` stub to `backend/gravitea_rust.pyi`
- [X] T011 [US1] Write integration test: 50 comprobantes with IVA + tributos, verify correct ARCA key names and structure in `backend/tests/rust_integration/test_arca_024.py`

**Checkpoint**: US1 functional — batch of 50 comprobantes builds correctly via Rust path with exact ARCA structure.

---

## Phase 4: User Story 4 — Output Parity Guarantee (Priority: P1)

**Goal**: Verify both processing paths (Rust and Python) produce identical output for any given input.

**Independent Test**: Run same batch through both paths and compare JSON output character-by-character.

### Tests for User Story 4

- [X] T012 [US4] Write parity tests: Rust vs Python fallback for basic comprobante (all required fields, no optionals) in `backend/tests/rust_integration/test_arca_024.py`
- [X] T013 [P] [US4] Write parity tests: service dates present (Concepto 2) vs absent (Concepto 1) in `backend/tests/rust_integration/test_arca_024.py`
- [X] T014 [P] [US4] Write parity tests: nested IVA breakdown (single + multi rate), tributos (present + guarded), CbtesAsoc (with + without CUIT fallback) in `backend/tests/rust_integration/test_arca_024.py`
- [X] T015 [US4] Write edge case parity tests: empty `alic_iva: []` → IVA omitted, `imp_trib: "0"` → tributos omitted, absent `mon_id` → "PES", absent `mon_cotiz` → 1.0, negative `imp_trib`, large floats `"99999999.99"` in `backend/tests/rust_integration/test_arca_024.py`

**Checkpoint**: All parity tests pass — Rust and Python paths produce identical output for every test vector.

---

## Phase 5: User Story 2 — Small Batch Fallback (Priority: P2)

**Goal**: Batches ≤10 use standard Python path; batches >10 use Rust path.

**Independent Test**: Send batch of 5 comprobantes and verify Python path used; send batch of 11 and verify Rust path used.

### Tests for User Story 2

- [X] T016 [US2] Write threshold guard tests: batch of 5 → Python path, batch of 11 → Rust path, batch of exactly 10 → Python path (threshold is >10 not >=10) in `backend/tests/rust_integration/test_arca_024.py`

**Checkpoint**: Threshold guard verified — correct routing for all batch sizes.

---

## Phase 6: User Story 3 — Graceful Degradation (Priority: P2)

**Goal**: System falls back to Python when Rust extension is unavailable, with a logged warning.

**Independent Test**: Simulate Rust extension absence, verify batch builds correctly via fallback and warning is logged.

### Tests for User Story 3

- [X] T017 [US3] Write fallback tests: `_USE_RUST = False` → correct output for 50 comprobantes, warning logged at module initialization, no errors raised in `backend/tests/rust_integration/test_arca_024.py`

**Checkpoint**: Fallback verified — system works correctly without Rust extension.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance benchmark, Docker validation, regression testing.

- [X] T018 Write benchmark test: 50 comprobantes with IVA + tributos completes in <5ms via Rust path (SC-001) in `backend/tests/rust_integration/test_arca_024.py`
- [ ] T019 Docker build: `docker compose build web` succeeds with SPEC-024 changes (BLOCKED: Docker Desktop not running)
- [ ] T020 Docker import check: `from gravitea_rust import build_caea_batch_request` succeeds inside container (BLOCKED: Docker Desktop not running)
- [ ] T021 Run SPEC-024 tests inside Docker container: all tests/rust_integration/test_arca_024.py pass (BLOCKED: Docker Desktop not running)
- [X] T022 Full regression test suite — 0 new failures from SPEC-024 changes (40/40 SPEC-024 pass, 248 other rust_integration pass, 172 pre-existing failures in SPEC-022 + import ordering)
- [X] T023 Update `specs/024-rust-arca-batch/quickstart.md` with final test results and benchmarks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (T001, T002) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 completion (T003-T006 pass cargo test)
- **US4 (Phase 4)**: Depends on US1 (Phase 3) — needs both Rust and Python paths functional
- **US2 (Phase 5)**: Depends on US1 (Phase 3) — needs dispatcher with threshold logic
- **US3 (Phase 6)**: Depends on US1 (Phase 3) — needs dispatcher with `_USE_RUST` flag
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US4 (P1)**: Depends on US1 — needs both paths working to compare outputs
- **US2 (P2)**: Depends on US1 — needs dispatcher to test threshold routing
- **US3 (P2)**: Depends on US1 — needs dispatcher to test fallback mechanism
- **US2 and US3**: Independent of each other — can run in parallel after US1

### Within Each Phase

```
Phase 1: T001 → T002 (sequential — T002 needs arca module, T001 needs error variant)
Phase 2: T003 → T004 → T005 → T006 (sequential — structs before function before tests)
Phase 3: T007 → T008 → T009 → T011 (sequential); T010 parallel with T007-T009
Phase 4: T012 → T013 [P] T014 [P] → T015 (T013/T014 parallel, T015 after both)
Phase 5: T016 (standalone)
Phase 6: T017 (standalone)
Phase 7: T018 → T019 → T020 → T021 → T022 → T023 (sequential — Docker chain)
```

### Parallel Opportunities

- **T010** (type stubs) can run parallel with T007-T009 (different file)
- **T013 + T014** (parity tests) can run in parallel (test different aspects in same file)
- **US2 (T016) + US3 (T017)** can run in parallel after US1 completion
- **Phase 2 (Rust core)** and **T010 (type stubs)** can overlap with different agents

---

## Parallel Example: Foundational Phase

```bash
# RUST-EXPERT agent works on Rust core (sequential dependency chain):
T003: Input serde structs in arca.rs
T004: Output serde structs in arca.rs
T005: build_caea_batch_request function in arca.rs
T006: Cargo tests in arca.rs

# QA agent can start T010 in parallel once T005/T006 signature is known:
T010: Type stub in gravitea_rust.pyi
```

## Parallel Example: After US1

```bash
# After US1 (Phase 3) completes, these can all run in parallel:
Agent A: T012-T015 (US4 parity tests)
Agent B: T016 (US2 threshold tests) + T017 (US3 fallback tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational — Rust core (T003-T006)
3. Complete Phase 3: US1 — Python integration (T007-T011)
4. **STOP and VALIDATE**: `cargo test` + basic pytest pass
5. Proceed to parity verification (US4)

### Incremental Delivery

1. Setup + Foundational → Rust function compiles and passes cargo tests
2. Add US1 → End-to-end Rust path working → Validate with basic integration test
3. Add US4 → Parity verified → Confidence that ARCA output is correct
4. Add US2 + US3 → Threshold + fallback verified → Production-ready
5. Polish → Docker validated, regression clean, benchmarks documented

### Team Allocation

| Agent | Tasks | Model |
|-------|-------|-------|
| LEAD (Orchestrator) | T001, T002, T009, T019-T023, coordination | Opus 4.6 |
| RUST-EXPERT | T003, T004, T005, T006 | Opus 4.6 |
| QA | T007, T008, T010, T011-T018 | Sonnet 4.6 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All tests go in single file: `backend/tests/rust_integration/test_arca_024.py`
- Cargo tests are inline in `rust/gravitea-core/src/arca.rs` (#[cfg(test)] mod)
- The complete dispatcher code is in `Docs/Temp-prompting/024/instruction-plan.md` §Dispatcher Pattern
- Serde struct designs are in `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design
- Critical caveats (8 implementation guards) are in `instruction-plan.md` §Critical Caveats
- Zero new Cargo dependencies — all crates already in Cargo.toml
