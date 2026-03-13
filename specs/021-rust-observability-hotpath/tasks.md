# Tasks: Rust Observability Hot Path Acceleration

**Input**: Design documents from `/specs/021-rust-observability-hotpath/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md

**Tests**: Included — spec explicitly requires Rust-native tests (20+), Python parity tests, benchmark, and fallback tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add regex dependency to Rust crate and register the new module

- [X] T001 Add `regex = "1.10"` dependency to `rust/gravitea-core/Cargo.toml`
- [X] T002 Add `pub mod observability;` and 2 `#[pymodule_export]` entries in `rust/gravitea-core/src/lib.rs`

---

## Phase 2: Foundational (Rust Observability Module)

**Purpose**: Implement the core Rust engine with all 24 `LazyLock<Regex>` patterns and both exported functions. MUST be complete before any Python integration or testing.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `rust/gravitea-core/src/observability.rs` with 24 `LazyLock<Regex>` statics: 2 path normalizers (`RE_UUID`, `RE_INT_ID`) + 16 sensitive endpoint patterns (all `(?i)`) + 6 fallback word-boundary patterns (all `(?i)` + `\b`)
- [X] T004 Implement `normalize_path(path: &str) -> String` in `rust/gravitea-core/src/observability.rs`: strip query params (split on `?`), apply UUID replacement `/{id}`, apply integer ID replacement `/{id}`
- [X] T005 Implement `sanitize_endpoint_label(endpoint: &str) -> String` in `rust/gravitea-core/src/observability.rs`: apply 16 compiled patterns in order, then 6 fallback word-boundary patterns in order
- [X] T006 Add `#[pyfunction]` wrappers for `normalize_path` and `sanitize_endpoint_label` (NO GIL release) in `rust/gravitea-core/src/observability.rs`
- [X] T007 Write Rust-native tests (target 20+) in `rust/gravitea-core/src/observability.rs`: each of 24 patterns individually, combined scenarios (UUID + sensitive keyword), edge cases (empty string, root `/`, >1000 chars, Unicode passthrough, double slashes)

**Checkpoint**: `cargo test observability` passes with 20+ tests. Both functions compile and produce correct output.

---

## Phase 3: User Story 1 + User Story 2 — Path Normalization & Endpoint Sanitization Parity (Priority: P1)

**Goal**: Python dispatcher routes to Rust implementation; `record_request()` uses dispatcher; byte-for-byte parity with Python for all 24 patterns.

**Independent Test**: Run parity tests comparing Rust output against expected Python output for 50+ diverse URL paths.

### Tests for US1 + US2

- [X] T008 [P] [US1] Write pattern parity tests for `normalize_path`: UUID replacement, integer ID replacement, query param stripping, multiple IDs, no-ID passthrough, empty/root paths in `backend/tests/rust_integration/test_observability_021.py`
- [X] T009 [P] [US2] Write pattern parity tests for `sanitize_endpoint_label`: each of 16 sensitive patterns individually + 6 fallback patterns individually in `backend/tests/rust_integration/test_observability_021.py`
- [X] T010 [P] [US2] Write combined scenario tests: paths with UUID + sensitive keyword, multiple sensitive matches, nested patterns, case variations in `backend/tests/rust_integration/test_observability_021.py`
- [X] T011 [P] [US1] Write edge case tests: empty string, root path `/`, >1000 chars, Unicode passthrough, double slashes, `None` handling in `backend/tests/rust_integration/test_observability_021.py`

### Implementation for US1 + US2

- [X] T012 [P] [US1] Create `backend/apps/core/observability/observability_engine.py` — dispatcher: try Rust import, fallback to Python functions from `metrics.py`
- [X] T013 [P] [US1] Add `normalize_path` and `sanitize_endpoint_label` type stubs to `backend/gravitea_rust.pyi`
- [X] T014 [US1] Modify `record_request()` in `backend/apps/core/observability/metrics.py` to import from `observability_engine` instead of calling local functions directly
- [X] T015 [US1] Build Rust extension with maturin and verify both functions importable: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`
- [X] T016 [US1] Run all parity tests (T008-T011) via external test runner and verify 0 failures
- [X] T017 [US2] Verify existing 13 observability tests in `backend/tests/unit/observability/test_metrics.py` pass unchanged (regression check)

**Checkpoint**: All 24 patterns produce identical output to Python. Existing observability tests pass. Dispatcher routes to Rust.

---

## Phase 4: User Story 3 — Accelerated Processing Under Load (Priority: P2)

**Goal**: Demonstrate 5x+ speedup over Python regex cascade on 1,000 URL paths.

**Independent Test**: Run benchmark test; assert Rust path < Python path / 5.

### Tests for US3

- [X] T018 [US3] Write benchmark test: generate 1,000 realistic URL paths, time both Rust and Python implementations, assert speedup in `backend/tests/rust_integration/test_observability_021.py`

### Implementation for US3

No additional code needed — the Rust implementation from Phase 2 already provides the speedup. This phase validates the performance claim.

- [X] T019 [US3] Run benchmark via external test runner and record actual speedup ratio

**Checkpoint**: Benchmark proves 5x+ speedup. Performance requirement (SC-001) met.

---

## Phase 5: User Story 4 — Graceful Fallback (Priority: P3)

**Goal**: When Rust extension is unavailable, Python fallback produces identical output with no errors or data loss.

**Independent Test**: Simulate missing Rust extension, verify Python fallback produces identical output.

### Tests for US4

- [X] T020 [US4] Write fallback tests: mock `ImportError` for `gravitea_rust`, verify `_USE_RUST = False`, verify Python functions produce identical output to expected values in `backend/tests/rust_integration/test_observability_021.py`

### Implementation for US4

No additional code needed — the dispatcher from T012 already handles fallback. This phase validates the fallback behavior.

- [X] T021 [US4] Run fallback tests via external test runner and verify 0 failures

**Checkpoint**: Fallback behavior verified. No data loss when Rust unavailable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docker verification, full regression, and documentation finalization

- [X] T022 Rebuild Docker image and verify `normalize_path` and `sanitize_endpoint_label` importable in container: `docker compose build web`
- [X] T023 Run observability-specific tests inside Docker container
- [X] T024 Run full test suite in container — 0 SPEC-021 regressions (2410 passed, 18 pre-existing failures from other specs)
- [X] T025 Update `specs/021-rust-observability-hotpath/quickstart.md` with final results, verification status, and actual benchmark numbers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1+US2 (Phase 3)**: Depends on Phase 2 (Rust module must compile and pass cargo tests)
- **US3 (Phase 4)**: Depends on Phase 3 (needs working Rust + Python integration for benchmarking)
- **US4 (Phase 5)**: Depends on Phase 3 (needs dispatcher for fallback testing)
  - US3 and US4 can run in parallel after Phase 3
- **Polish (Phase 6)**: Depends on Phases 3, 4, and 5

### Within Each Phase

- Phase 2: T003 → T004+T005 (parallel) → T006 → T007
- Phase 3: T008-T011 tests (parallel) + T012-T013 impl (parallel) → T014 → T015 → T016+T017 (parallel)
- Phase 4: T018 → T019
- Phase 5: T020 → T021
- Phase 6: T022 → T023+T024 (parallel) → T025

### Parallel Opportunities

- **Phase 2**: T004 and T005 can be written in parallel (different functions, same file — no conflict if one agent writes both)
- **Phase 3 tests**: T008, T009, T010, T011 can all be written in parallel (same file but independent test classes)
- **Phase 3 impl**: T012 and T013 can be written in parallel (different files)
- **Phase 4+5**: Can run in parallel after Phase 3 completes (independent test scenarios)
- **Phase 6**: T023 and T024 can run in parallel (different test scopes)

---

## Parallel Example: Phase 3

```bash
# Launch all tests in parallel (independent test functions, same file):
Task: "Pattern parity tests for normalize_path in test_observability_021.py"
Task: "Pattern parity tests for sanitize_endpoint_label in test_observability_021.py"
Task: "Combined scenario tests in test_observability_021.py"
Task: "Edge case tests in test_observability_021.py"

# Launch dispatcher + stubs in parallel (different files):
Task: "Create observability_engine.py dispatcher"
Task: "Add type stubs to gravitea_rust.pyi"
```

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2 + Phase 3)

1. Complete Phase 1: Setup (Cargo.toml + lib.rs)
2. Complete Phase 2: Foundational (observability.rs with 24 patterns + 20 Rust tests)
3. Complete Phase 3: US1+US2 (dispatcher, parity tests, metrics.py integration)
4. **STOP and VALIDATE**: All 24 patterns produce identical output; existing tests pass
5. Deploy/demo if ready — Prometheus dashboards should show no change in label format

### Incremental Delivery

1. Phase 1+2 → Rust engine compiles and passes cargo tests
2. Phase 3 → Python integration complete, parity proven → **MVP delivered**
3. Phase 4 → Performance claim validated (5x+ speedup)
4. Phase 5 → Fallback safety net validated
5. Phase 6 → Docker + regression + docs finalized

### Team Strategy (from plan.md)

| Agent | Phases | Tasks |
|-------|--------|-------|
| RUST-EXPERT (Opus 4.6) | Phase 1+2 | T001-T007 |
| BACKEND-CODER (Sonnet 4.6) | Phase 3 impl | T012-T015 |
| QA (Sonnet 4.6) | Phase 3-5 tests | T008-T011, T016-T021 |
| LEAD (Opus 4.6) | Phase 6 | T022-T025 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US1 (Path Normalization) and US2 (Endpoint Sanitization) are combined in Phase 3 because they share the same dispatcher and test file
- All pytest must use external test runner: `scripts/run-tests-external.sh`
- Maturin build: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`
- Test location: `backend/tests/rust_integration/test_observability_021.py` (NOT `tests/unit/observability/`)
- Commit after each phase completion
- Stop at any checkpoint to validate independently
