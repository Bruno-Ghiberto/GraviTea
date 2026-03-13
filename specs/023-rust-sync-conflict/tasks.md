# Tasks: Rust Sync Conflict Engine

**Input**: Design documents from `/specs/023-rust-sync-conflict/`
**Prerequisites**: plan.md (required), spec.md (required), research.md (resolved)

**Tests**: Explicitly required — spec mandates ≥8 Rust-native tests (SC-006), equivalence tests (SC-001), merge log parity (SC-007), batch benchmark (SC-002), GIL concurrency (SC-003), SyncError (SC-008), fallback (SC-005), threshold (SC-004), Docker (SC-009), regression (SC-010).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing crate dependencies and add new error variant + module registration

- [X] T001 Verify serde 1.0 + serde_json 1.0 already present in rust/gravitea-core/Cargo.toml (no additions needed — present since SPEC-019)
- [X] T002 [P] Add SyncError(String) variant mapped to PyRuntimeError in rust/gravitea-core/src/errors.rs (follows CryptoError/ComputeError/ExportError/SecurityError pattern)
- [X] T003 [P] Register `mod sync;` in rust/gravitea-core/src/lib.rs (module declaration only, exports added later)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the core Rust merge function that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase compiles successfully

- [X] T004 Create rust/gravitea-core/src/sync.rs with normalize_value helper: whitespace-only strings (.trim().is_empty()) → Value::Null; empty lists/dicts/numbers/bools left as-is (research.md R-002)
- [X] T005 Implement compare_completeness helper in rust/gravitea-core/src/sync.rs: String by trimmed len, Array by len, Object by key count; all other types (Bool, Number, mixed) → server wins (research.md R-001)
- [X] T006 Implement merge_most_complete #[pyfunction] in rust/gravitea-core/src/sync.rs: deserialize server_json + client_json + metadata_fields_json, key union, metadata passthrough via HashSet, normalize → compare → build merged Value + merge_log JSON with 5 categories (client_won, server_won, tied_server_won, both_null, empty_string_normalized). Returns PyResult<(String, String)>. GIL NOT released.
- [X] T007 Add `#[pymodule_export]` for merge_most_complete in rust/gravitea-core/src/lib.rs and run `cargo build` to verify compilation

**Checkpoint**: Core Rust merge function compiles. User story implementation can now begin.

---

## Phase 3: User Story 1 — Single Conflict Resolution Parity (Priority: P1) MVP

**Goal**: Prove byte-identical merge output and identical merge decision logs between Rust and Python for all payload types

**Independent Test**: `cargo test sync -- --nocapture` (≥8 Rust tests) + `pytest tests/rust_integration/test_sync_023.py -k "parity or equivalence or merge_log or sync_error"` (Python equivalence)

### Tests for User Story 1

- [X] T008 [P] [US1] Write ≥8 Rust-native tests in rust/gravitea-core/src/sync.rs: basic merge with overlapping fields, deep nesting (nested dict key count comparison), null handling (both null, one null, whitespace normalization), each type comparison (str/str, list/list, dict/dict), both-empty payloads → SyncError (FR-012: new guard clause, not parity with Python), metadata field passthrough (id/created_at/updated_at/sync_version always server), mixed types (str vs number → server wins), invalid JSON → SyncError
- [X] T009 [US1] Run `cargo test sync -- --nocapture` in rust/gravitea-core/ and verify ≥8 tests pass (SC-006)

### Implementation for User Story 1

- [X] T010 [US1] Build wheel: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release` and verify `from gravitea_rust import merge_most_complete` works in Python
- [X] T011 [US1] Write Python equivalence + merge_log parity + SyncError tests in backend/tests/rust_integration/test_sync_023.py: 10+ payload pairs comparing Rust merge_most_complete vs Python _resolve_most_complete_wins (SC-001), merge_log 5-category field-by-field parity (SC-007), invalid JSON → RuntimeError (SC-008). Use sorted list comparison for merge_log arrays (research.md R-005 — HashMap iteration order differs)
- [X] T012 [US1] Run pytest tests/rust_integration/test_sync_023.py via external runner and verify all US1 tests pass

**Checkpoint**: Single merge parity proven — merged payloads and merge logs identical. MVP complete.

---

## Phase 4: User Story 2 — Batch Sync Acceleration (Priority: P2)

**Goal**: Process 100+ conflict pairs in a single Rust call with GIL released, achieving ≥3x speedup over sequential Python

**Independent Test**: `pytest tests/rust_integration/test_sync_023.py -k "batch or gil"` (benchmark + concurrency)

### Implementation for User Story 2

- [X] T013 [US2] Implement merge_most_complete_batch #[pyfunction] in rust/gravitea-core/src/sync.rs: accepts pairs_json (JSON array of {server, client} objects) + metadata_fields_json, GIL released via py.allow_threads(), returns PyResult<String> (JSON array of {merged, merge_log} objects). Reuses merge logic from T006.
- [X] T014 [US2] Add `#[pymodule_export]` for merge_most_complete_batch in rust/gravitea-core/src/lib.rs
- [X] T015 [P] [US2] Write Rust-native batch test in rust/gravitea-core/src/sync.rs: batch of 3 pairs, verify JSON array output with correct merged + merge_log for each pair
- [X] T016 [US2] Rebuild wheel with maturin develop (includes new batch function from T013) and verify `from gravitea_rust import merge_most_complete_batch` works in Python
- [X] T017 [US2] Write batch benchmark test (100 pairs, 50 fields each, ≥3x speedup over sequential Python) + GIL release concurrency test (threading.Thread runs during batch) in backend/tests/rust_integration/test_sync_023.py (SC-002, SC-003)
- [X] T018 [US2] Run pytest batch/GIL tests via external runner and verify pass

**Checkpoint**: Batch acceleration proven — ≥3x speedup, GIL released during batch.

---

## Phase 5: User Story 3 — Graceful Fallback (Priority: P2)

**Goal**: System works identically when Rust module is unavailable, falling back to Python with a logged warning

**Independent Test**: `pytest tests/rust_integration/test_sync_023.py -k "fallback"` (mock Rust unavailable)

### Implementation for User Story 3

- [X] T019 [US3] Create backend/apps/sync/sync_engine.py dispatcher following ssrf_engine.py pattern: try import gravitea_rust → _USE_RUST = True; except (ImportError, OSError) → _USE_RUST = False + logging.warning. Public merge_most_complete() and merge_most_complete_batch() functions that delegate to Rust or Python based on _USE_RUST flag. Include _DEFAULT_METADATA_FIELDS JSON constant.
- [X] T020 [US3] Write fallback tests in backend/tests/rust_integration/test_sync_023.py: mock gravitea_rust unavailable via unittest.mock.patch.dict('sys.modules'), verify _USE_RUST is False, verify merge still works via Python path, verify warning is logged (SC-005)
- [X] T021 [US3] Run pytest fallback tests via external runner and verify pass

**Checkpoint**: Fallback works — system operates correctly when Rust is unavailable.

---

## Phase 6: User Story 4 — Small Payload Efficiency Guard (Priority: P3)

**Goal**: Payloads with <20 fields route to Python (avoiding FFI overhead), ≥20 fields route to Rust

**Independent Test**: `pytest tests/rust_integration/test_sync_023.py -k "threshold"` (routing verification)

### Implementation for User Story 4

- [X] T022 [US4] Add _RUST_FIELD_THRESHOLD = 20 constant and threshold routing logic in backend/apps/sync/sync_engine.py: merge_most_complete() checks max(len(server), len(client)) < threshold → Python path; ≥ threshold → Rust path. Batch function always uses Rust if available (no threshold — amortized FFI).
- [X] T023 [US4] Write threshold guard tests in backend/tests/rust_integration/test_sync_023.py: 5-field payload → Python path (verify via mock), 25-field payload → Rust path, exact boundary 20-field → Rust path (SC-004)
- [X] T024 [US4] Run pytest threshold tests via external runner and verify pass

**Checkpoint**: Threshold guard working — small payloads avoid FFI overhead.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration into existing codebase, type stubs, Docker validation, regression

- [X] T025 Modify backend/apps/sync/conflict_resolver.py to import merge_most_complete from apps.sync.sync_engine instead of inline implementation (callers use dispatcher, not direct Rust import)
- [X] T026 [P] Update backend/gravitea_rust.pyi with type stubs: merge_most_complete(server_json: str, client_json: str, metadata_fields_json: str) -> tuple[str, str] and merge_most_complete_batch(pairs_json: str, metadata_fields_json: str) -> str
- [X] T027 Docker validation: `docker compose build web` then verify import with `docker compose run --rm --entrypoint python web -c "from gravitea_rust import merge_most_complete, merge_most_complete_batch; print('OK')"` (SC-009)
- [X] T028 Full regression test: run entire test suite via external runner `scripts/run-tests-external.sh "regression-023"` and verify 0 new failures (SC-010)
- [X] T029 Run quickstart.md validation: execute all commands from specs/023-rust-sync-conflict/quickstart.md and verify expected outcomes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T004-T007) — MVP target
- **US2 (Phase 4)**: Depends on Foundational (T004-T007) — can run in parallel with US1 after Foundational
- **US3 (Phase 5)**: Depends on US1 or US2 (needs working Rust wheel to test dispatcher) — can start after T010 or T016
- **US4 (Phase 6)**: Depends on US3 (needs sync_engine.py from T019)
- **Polish (Phase 7)**: Depends on US3 + US4 (T019-T024 must complete before T025 modifies conflict_resolver.py)

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories
- **US2 (P2)**: Can start after Foundational — independent of US1 (adds batch function to same Rust file)
- **US3 (P2)**: Needs working Rust wheel (US1 T010 or US2 T016) — creates the dispatcher
- **US4 (P3)**: Needs dispatcher from US3 (T019) — adds threshold routing to it

### Within Each User Story

- Rust implementation before Rust tests
- Rust tests pass before Python integration tests
- Maturin build (wheel) before Python tests
- Core implementation before integration

### Parallel Opportunities

- T002 + T003 in Setup can run in parallel (different files)
- US1 (Phase 3) and US2 (Phase 4) can start in parallel after Foundational completes
- T008 (Rust tests in sync.rs) can run in parallel with US2 Rust tasks (T013-T015) — different stories, same file but different functions
- T015 (Rust batch test) can run in parallel with US1 Python test writing (T011) — different files
- T026 (.pyi stubs) can run in parallel with T025 (conflict_resolver.py) and T027 (Docker)

---

## Parallel Example: Foundational + US1 + US2

```bash
# After Phase 2 completes, launch US1 and US2 Rust work in parallel:

# Agent A (US1 — Rust tests):
Task: "Write ≥8 Rust-native tests in rust/gravitea-core/src/sync.rs"  # T008
Task: "Run cargo test sync -- --nocapture"                              # T009

# Agent B (US2 — Batch function in same sync.rs):
Task: "Implement merge_most_complete_batch in rust/gravitea-core/src/sync.rs"  # T013
Task: "Add #[pymodule_export] for batch in lib.rs"                             # T014
Task: "Write Rust-native batch test in sync.rs"                                # T015

# After BOTH Agent A and Agent B complete, single maturin build:
Task: "Build wheel with maturin develop"  # T010 (covers both single + batch)

# Then Python tests for both stories in parallel (different test classes, same file):
# Agent A: equivalence + merge_log + SyncError tests (T011)
# Agent B: batch benchmark + GIL concurrency tests (T017)
```

**Note**: If US1 needs Python tests before US2 batch is ready, T010 can build an intermediate wheel (single function only). T016 rebuilds after batch is added.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: User Story 1 (T008-T012)
4. **STOP and VALIDATE**: cargo test ≥8 pass + pytest equivalence tests pass
5. Single merge parity is proven — safe to continue

### Incremental Delivery

1. Setup + Foundational → Rust core compiles
2. Add US1 → Single parity proven → **MVP!**
3. Add US2 → Batch acceleration proven (≥3x speedup)
4. Add US3 → Fallback works when Rust unavailable
5. Add US4 → Small payloads route efficiently
6. Polish → Full integration, Docker, regression gate

### Parallel Team Strategy (4 agents)

1. **LEAD**: Setup (Phase 1) — sequential, 3 tasks
2. **All**: Foundational (Phase 2) — LEAD writes core, all verify
3. After Foundational:
   - **RUST-EXPERT**: US1 Rust tests (T008-T009) + US2 batch function (T013-T015)
   - **BACKEND-CODER**: US3 dispatcher (T019) + US4 threshold (T022-T023)
   - **QA**: US1 Python tests (T011) + US2 Python tests (T017) after maturin build
   - **LEAD**: Docker validation (T027) + regression (T028)

---

## Notes

- [P] tasks = different files, no dependencies between them
- [Story] label maps task to specific user story for traceability
- Each user story independently testable after completion
- External test runner mandatory: `scripts/run-tests-external.sh "name" "cmd"`
- Maturin build: T010 for US1 (single function), T016 for US2 (adds batch function) — rebuild needed when new Rust code is added
- Merge_log array comparison: use sorted lists or set equality (HashMap iteration order differs from Python dict)
- FR-012 (both-empty rejection): new guard clause — equivalence tests (SC-001) must exclude this edge case
- Commit after each phase checkpoint for restore points
