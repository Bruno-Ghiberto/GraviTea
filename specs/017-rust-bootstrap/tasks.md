# Tasks: Rust Toolchain Bootstrap (SPEC-017)

**Input**: Design documents from `specs/017-rust-bootstrap/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md

**Tests**: Included — spec explicitly requires Rust-native tests (FR-011, SC-007) and Python integration tests (FR-012, SC-008).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US5) this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the Rust project skeleton and directory structure.

- [x] T001 Create directory structure `rust/gravitea-core/src/`
- [x] T002 [P] Write `rust/gravitea-core/Cargo.toml` — package `gravitea-core`, `[lib] name = "gravitea_rust"`, crate-type `["cdylib", "rlib"]`, `pyo3 = "0.28"` (no feature flags), `thiserror = "2.0"`, edition 2021, release profile (`opt-level = "z"`, `lto = true`, `codegen-units = 1`, `strip = true`, `panic = "abort"`)
- [x] T003 [P] Write `rust/gravitea-core/pyproject.toml` — `requires = ["maturin>=1.12,<2.0"]`, build-backend `"maturin"`, `requires-python = ">=3.12"`, `[tool.maturin] strip = true`
- [x] T004 [P] Create `backend/tests/rust_integration/__init__.py` (empty file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Rust source code that MUST compile before any user story work.

**CRITICAL**: No user story work can begin until this phase compiles successfully.

- [x] T005 Write `rust/gravitea-core/src/lib.rs` — declarative `#[pymodule] mod gravitea_rust` with `#[pyfunction] fn hello() -> String` returning `"Hello from Rust"`, `mod errors; pub use errors::*;`
- [x] T006 Write `rust/gravitea-core/src/errors.rs` — `#[derive(Error, Debug)] pub enum GraviteaError` with variants `InvalidInput(String)`, `CryptoError(String)`, `IoError(#[from] std::io::Error)` and `impl From<GraviteaError> for PyErr` mapping to `PyValueError`, `PyRuntimeError`, `PyIOError`
- [x] T007 Generate `rust/gravitea-core/Cargo.lock` via `cargo generate-lockfile` in `rust/gravitea-core/`
- [x] T008 Verify `cargo build --release` succeeds in `rust/gravitea-core/`

**Checkpoint**: Rust crate compiles — user story implementation can now begin.

---

## Phase 3: User Story 1 — Developer Builds and Imports the Rust Extension (Priority: P1) MVP

**Goal**: Developer runs `maturin develop --release`, imports the extension in Python, and calls `hello()`.

**Independent Test**: `python -c "from gravitea_rust import hello; print(hello())"` outputs `Hello from Rust`.

### Build Validation (US1)

- [x] T009 [US1] Run `maturin develop --release` from `rust/gravitea-core/` — verify wheel installs into active venv
- [x] T010 [US1] Verify `python -c "from gravitea_rust import hello; print(hello())"` outputs `Hello from Rust`
- [x] T011 [US1] Verify `.pyd` (Windows) or `.so` (Linux) exists in venv `site-packages/` with name `gravitea_rust`

### Rust-Native Tests (US1)

- [x] T012 [P] [US1] Write Rust test for `hello()` return value in `rust/gravitea-core/src/lib.rs` — `#[cfg(test)] mod tests` with `#[test] fn test_hello()`
- [x] T013 [P] [US1] Write Rust tests for `GraviteaError` in `rust/gravitea-core/src/errors.rs` — `#[cfg(test)] mod tests` with `test_error_display()` (InvalidInput variant) and `test_io_error_from()` (From conversion)
- [x] T014 [US1] Verify `cargo test` passes in `rust/gravitea-core/` — minimum 3 tests green (hello, error display, error from)

### Python Integration Test (US1)

- [x] T015 [US1] Write `backend/tests/rust_integration/test_rust_import.py` — `test_import_succeeds()`, `test_hello_returns_expected_string()`, `test_hello_consistent_across_calls()` (1000 calls)
- [x] T016 [US1] Verify pytest passes for `backend/tests/rust_integration/test_rust_import.py`

**Checkpoint**: Extension builds, imports, returns correct values. 3+ Rust tests and 2+ Python tests pass.

---

## Phase 4: User Story 2 — Backend Runs Without the Rust Extension (Priority: P1)

**Goal**: Backend functions identically without the Rust extension. Fallback pattern silently catches ImportError.

**Independent Test**: Simulate missing extension (monkeypatch), verify `_USE_RUST` flag is False and fallback function returns Python-based result.

### Implementation (US2)

- [x] T017 [US2] Write `backend/tests/rust_integration/test_rust_fallback.py` — test the `try/except ImportError` pattern: verify `_USE_RUST` flag toggling, verify fallback function produces identical output to Rust version, verify no errors/warnings in operation
- [x] T018 [US2] Verify pytest passes for `backend/tests/rust_integration/test_rust_fallback.py`

**Checkpoint**: Fallback pattern works — backend doesn't require Rust extension to run.

---

## Phase 5: User Story 5 — Shared Error Mapping (Priority: P2)

**Goal**: `GraviteaError` enum maps each Rust error variant to the correct Python exception type.

**Independent Test**: `cargo test` error tests verify Display messages for all 3 variants and `From<std::io::Error>` conversion.

### Validation (US5)

- [x] T019 [US5] Verify `rust/gravitea-core/src/errors.rs` has all 3 required variants: `InvalidInput(String)` maps to `PyValueError`, `CryptoError(String)` maps to `PyRuntimeError`, `IoError(#[from] std::io::Error)` maps to `PyIOError`
- [x] T020 [US5] Verify `cargo test` passes error-specific tests in `rust/gravitea-core/` — Display formatting for each variant, From conversion for io::Error

**Checkpoint**: Error mapping convention established and tested for all 3 error categories.

---

## Phase 6: User Story 3 — Docker Image Includes the Compiled Rust Extension (Priority: P2)

**Goal**: Docker build compiles Rust, packages into wheel, installs in runtime image. No Rust compiler in final image.

**Independent Test**: `docker compose build web` succeeds, then `docker compose exec web python -c "from gravitea_rust import hello; print(hello())"` outputs `Hello from Rust`.

### Implementation (US3)

- [x] T021 [US3] Add `rust-builder` stage to `backend/Dockerfile` — `FROM python:3.14.3-slim AS rust-builder` + rustup (deviation: glibc incompatibility with rust:1.85-slim-bookworm)
- [x] T022 [US3] Implement dependency caching in `backend/Dockerfile` — copy `Cargo.toml` + `Cargo.lock`, dummy `lib.rs` with valid `#[pymodule]`, BuildKit cache mounts for `/usr/local/cargo/registry` and `/build/target`
- [x] T023 [US3] Build real source in `backend/Dockerfile` — remove dummy `src/`, copy real `rust/gravitea-core/` source, `maturin build --release --out /wheels` with cache mounts
- [x] T024 [US3] Copy wheel from `rust-builder` to Python runtime stage in `backend/Dockerfile` — `COPY --from=rust-builder /wheels/*.whl /tmp/wheels/`, `pip install --no-cache-dir /tmp/wheels/*.whl`
- [x] T025 [US3] Update `docker-compose.yml` build context for `web` service to include `rust/` directory — change `context: ./backend` to `context: .` with `dockerfile: backend/Dockerfile`
- [x] T026 [US3] Verify `docker compose build web` succeeds (exit code 0)
- [x] T027 [US3] Verify `docker compose up -d` — web service healthy, all existing services (db, redis) unaffected
- [x] T028 [US3] Verify `docker compose exec web python -c "from gravitea_rust import hello; print(hello())"` outputs `Hello from Rust`

**Checkpoint**: Docker build includes Rust extension, all services healthy, import works in container.

---

## Phase 7: User Story 4 — Developer Receives Autocomplete for Rust Functions (Priority: P3)

**Goal**: Type stub file provides IDE autocomplete and static type checking for all Rust-exposed functions.

**Independent Test**: `python -c "import ast; ast.parse(open('backend/gravitea_rust.pyi').read())"` succeeds — valid Python syntax.

### Implementation (US4)

- [x] T029 [US4] Write `backend/gravitea_rust.pyi` — type stub declaring `def hello() -> str: ...` and `class GraviteaError(Exception): ...` with docstrings for each error variant
- [x] T030 [US4] Verify type stub has valid Python syntax and passes type checking — `python -c "import ast; ast.parse(open('backend/gravitea_rust.pyi').read())"` and `python -m mypy backend/gravitea_rust.pyi --no-error-summary`

**Checkpoint**: IDE autocomplete works for Rust extension functions.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation verification, regression validation, and performance measurements.

### Documentation Verification

- [x] T031 [P] Verify `specs/017-rust-bootstrap/quickstart.md` covers: prerequisites, build, test, Docker, WSL2, troubleshooting
- [x] T032 [P] Verify fallback pattern convention documented in `specs/017-rust-bootstrap/quickstart.md`
- [x] T033 [P] Verify error mapping convention documented in `specs/017-rust-bootstrap/research.md` (R-010)

### Regression & Final Validation

- [x] T034 Run full existing Python test suite in `backend/` — `pytest --tb=short -q --no-header` — 0 new failures (pre-existing DB connection error only — PostgreSQL not running in WSL2)
- [x] T035 Verify `cargo test` passes in `rust/gravitea-core/` — all 3+ tests green (3/3 pass)
- [x] T036 Verify pytest passes for all `backend/tests/rust_integration/` tests (6/6 pass)
- [x] T037 Verify Docker build + import — `docker compose build web && docker compose exec web python -c "from gravitea_rust import hello"` — "Hello from Rust" confirmed
- [x] T038 Measure runtime Docker image size increase — 553 MB (was 621 MB, delta -68 MB, wheel 188 KB)
- [x] T039 Measure build times — incremental build 6.8s (<30s target), first build ~45s (<60s target)
- [x] T040 Verify `rust/gravitea-core/Cargo.lock` exists (3,909 bytes) — untracked, .gitignore exception in place, will be committed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — first to implement
- **US2 (Phase 4)**: Depends on Foundational — can run in parallel with US1
- **US5 (Phase 5)**: Depends on Foundational (errors.rs created in T006) — validation only
- **US3 (Phase 6)**: Depends on US1 completion (needs working Rust code to Docker-ize)
- **US4 (Phase 7)**: Depends on Foundational — can run in parallel with US1/US2/US5
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
├── US1 (Phase 3) — Build & Import [no cross-story deps]
│   └── US3 (Phase 6) — Docker Integration [depends on US1]
├── US2 (Phase 4) — Fallback Pattern [no cross-story deps]
├── US5 (Phase 5) — Error Mapping [no cross-story deps, validation only]
└── US4 (Phase 7) — Type Stubs [no cross-story deps]
```

### Within Each User Story

- Build/compile validation before test writing
- Rust-native tests before Python integration tests
- Local validation before Docker integration

### Parallel Opportunities

- **Setup**: T002, T003, T004 — all different files, run in parallel
- **US1 Rust tests**: T012, T013 — different source files, run in parallel
- **After Foundational**: US1, US2, US4, US5 can all start in parallel
- **Polish docs**: T031, T032, T033 — independent verification checks

---

## Parallel Example: After Foundational Phase

```bash
# These can start simultaneously after Phase 2 completes:
# Agent RUST-EXPERT: US1 — Build validation + Rust tests (T009-T016)
# Agent RUST-EXPERT: US2 — Fallback pattern test (T017-T018) [after US1 or in parallel]
# Agent RUST-EXPERT: US4 — Type stub (T029-T030) [independent]

# US3 (Docker) MUST wait for US1:
# Agent DEVOPS: US3 — Docker integration (T021-T028) [after T014 confirms cargo test passes]

# ORCHESTRATOR handles Phase 8 (Polish) after all stories complete.
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: US1 — Build & Import (T009-T016)
4. **STOP and VALIDATE**: Extension builds, imports, hello() works, 3+ Rust tests + 2+ Python tests pass
5. This alone proves the entire Rust/PyO3/Maturin toolchain works end-to-end

### Incremental Delivery

1. Setup + Foundational → Crate compiles
2. **US1** → Extension builds and imports → **MVP complete**
3. **US2** → Fallback pattern verified → Safe for non-Rust developers
4. **US5** → Error conventions tested → Convention ready for SPEC-018+
5. **US3** → Docker integration → Production deployment ready
6. **US4** → Type stubs → Full developer experience
7. **Polish** → Regression suite, docs, size/timing validation → **Spec complete**

### Team Strategy (3 Agents from plan.md)

| Agent | Phases | Tasks |
|-------|--------|-------|
| **RUST-EXPERT** (Opus 4.6) | Setup → Foundational → US1 → US2 → US5 → US4 | T001-T020, T029-T030 |
| **DEVOPS** (Sonnet 4.6) | US3 (after US1 completes) | T021-T028 |
| **ORCHESTRATOR** (Opus 4.6) | Polish | T031-T040 |

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work
- [Story] label maps task to specific user story for traceability
- This spec has NO database models, NO API endpoints, NO frontend changes
- `cargo test` requires dual crate-type `["cdylib", "rlib"]` — see research.md R-EXTRA
- PyO3 `extension-module` feature is DEPRECATED — maturin handles it automatically — see research.md R-001
- `pyo3 = "0.28"` with NO feature flags — see research.md R-001
- The `hello()` function is deliberately trivial — it proves the toolchain, not business logic
- All 8 subsequent specs (SPEC-018 through SPEC-025) depend on this bootstrap completing successfully
