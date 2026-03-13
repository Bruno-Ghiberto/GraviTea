# Tasks: Rust Data Export Pipeline (SPEC-020)

**Input**: Design documents from `/specs/020-rust-data-export/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md
**Branch**: `020-rust-data-export`

**Tests**: Included — plan.md Phase 3 explicitly defines test tasks (Rust-native + pytest integration).

**Organization**: Tasks grouped by user story. US1 (CSV) and US2 (XLSX) are both P1 but sequenced since they share `export.rs` and `export_engine.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in all descriptions

## Path Conventions

- **Rust source**: `rust/gravitea-core/src/`
- **Rust config**: `rust/gravitea-core/Cargo.toml`
- **Python wrapper**: `backend/apps/reportes/`
- **Python tests**: `backend/tests/reportes/`
- **Type stubs**: `backend/gravitea_rust.pyi`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add crate dependencies, error variant, and module skeleton needed by all user stories

- [x] T001 [P] Add `csv = "1"` and `rust_xlsxwriter = "0.92"` dependencies to `rust/gravitea-core/Cargo.toml`
- [x] T002 [P] Add `ExportError(String)` variant to `GraviteaError` enum in `rust/gravitea-core/src/errors.rs` with `#[error("Export error: {0}")]` and map to `PyRuntimeError`
- [x] T003 Create `rust/gravitea-core/src/export.rs` module file and add `mod export;` declaration to `rust/gravitea-core/src/lib.rs`

**Checkpoint**: `cargo check` passes with new deps and empty export module

---

## Phase 2: User Story 1 — CSV Export Generation (Priority: P1) MVP

**Goal**: Generate CSV byte arrays with UTF-8 BOM, ordered columns, Spanish character support, and RFC 4180 escaping

**Independent Test**: Provide rows with Spanish text → verify output starts with BOM (`\xEF\xBB\xBF`) and contains correctly ordered, properly escaped CSV content

### Rust Implementation for US1

- [x] T004 [US1] Implement `generate_csv_internal(rows: &[HashMap<String, String>], headers: &[String]) -> Result<Vec<u8>, GraviteaError>` in `rust/gravitea-core/src/export.rs` — prepend UTF-8 BOM, use `csv::WriterBuilder::new().from_writer(Vec::new())`, write header row then data rows with missing keys as empty strings
- [x] T005 [US1] Add `#[pyfunction] fn generate_csv(py: Python, rows: Vec<HashMap<String, String>>, headers: Vec<String>) -> PyResult<Vec<u8>>` wrapper with `py.detach()` GIL release in `rust/gravitea-core/src/export.rs`
- [x] T006 [US1] Add `#[pymodule_export] use super::export::generate_csv;` to the `gravitea_rust` module in `rust/gravitea-core/src/lib.rs`
- [x] T007 [US1] Write Rust-native tests in `rust/gravitea-core/src/export.rs`: (1) CSV roundtrip with 3 rows, (2) BOM presence check, (3) empty headers produces BOM-only, (4) RFC 4180 escaping for commas/quotes/newlines, (5) missing key produces empty cell

### Python Integration for US1

- [x] T008 [US1] Create `backend/apps/reportes/export_engine.py` with `_USE_RUST_EXPORT` conditional import and `generate_csv()` public function that dispatches to Rust or falls back to Python `csv` stdlib with BOM
- [x] T009 [P] [US1] Add `generate_csv` function stub to `backend/gravitea_rust.pyi`: `def generate_csv(rows: list[dict[str, str]], headers: list[str]) -> bytes: ...`

### Tests for US1

- [x] T010 [US1] Write pytest tests in `backend/tests/reportes/test_export_020.py`: (1) CSV starts with UTF-8 BOM, (2) column order matches header list, (3) Spanish characters preserved (á, é, ñ, ü), (4) empty headers returns BOM-only, (5) empty rows with headers returns header-only CSV, (6) missing key in row produces empty cell

**Checkpoint**: `cargo test` passes CSV tests + `pytest test_export_020.py` passes CSV tests. Maturin build succeeds.

---

## Phase 3: User Story 2 — XLSX Export Generation (Priority: P1)

**Goal**: Generate XLSX byte arrays with auto-detected numeric cells, optional column width overrides, and Spanish character support

**Independent Test**: Provide rows with mixed string/numeric values → verify XLSX contains number-typed cells for parseable values and text for others

### Rust Implementation for US2

- [x] T011 [US2] Implement `generate_xlsx_internal(rows: &[HashMap<String, String>], headers: &[String], column_widths: &HashMap<String, f64>) -> Result<Vec<u8>, GraviteaError>` in `rust/gravitea-core/src/export.rs` — write headers as bold row 0, detect numeric values via `parse::<f64>()`, call `worksheet.autofit()` then apply explicit `set_column_width()` overrides
- [x] T012 [US2] Add `#[pyfunction] fn generate_xlsx(py: Python, rows: Vec<HashMap<String, String>>, headers: Vec<String>, column_widths: Option<HashMap<String, f64>>) -> PyResult<Vec<u8>>` wrapper with `py.detach()` GIL release in `rust/gravitea-core/src/export.rs`
- [x] T013 [US2] Add `#[pymodule_export] use super::export::generate_xlsx;` to the `gravitea_rust` module in `rust/gravitea-core/src/lib.rs`
- [x] T014 [US2] Write Rust-native tests in `rust/gravitea-core/src/export.rs`: (1) XLSX roundtrip produces valid bytes, (2) numeric detection — "1250.50" written as number, "abc" as text, (3) column widths override applied, (4) empty data produces headers-only XLSX, (5) orphan column width key silently ignored

### Python Integration for US2

- [x] T015 [US2] Add `generate_xlsx()` public function to `backend/apps/reportes/export_engine.py` that dispatches to Rust or falls back to `openpyxl` with numeric detection and column widths
- [x] T016 [P] [US2] Add `generate_xlsx` function stub to `backend/gravitea_rust.pyi`: `def generate_xlsx(rows: list[dict[str, str]], headers: list[str], column_widths: dict[str, float] | None = None) -> bytes: ...`

### Tests for US2

- [x] T017 [US2] Write pytest tests in `backend/tests/reportes/test_export_020.py`: (1) XLSX output is valid (non-empty bytes), (2) numeric cell contains float value not string, (3) column widths applied correctly, (4) Spanish characters preserved in XLSX, (5) empty rows with headers produces headers-only XLSX, (6) non-numeric value written as text

**Checkpoint**: `cargo test` passes all CSV + XLSX tests + `pytest test_export_020.py` passes all CSV + XLSX tests.

---

## Phase 4: User Story 3 — Large Dataset Performance (Priority: P2)

**Goal**: Verify 10K-row exports complete under 2 seconds and GIL release enables concurrent request handling

**Independent Test**: Generate 10K rows x 10 cols dataset, time both CSV and XLSX generation, verify < 2s each

- [x] T018 [P] [US3] Write benchmark test in `backend/tests/reportes/test_export_020.py`: generate 10K rows x 10 columns CSV — assert completes in < 2 seconds
- [x] T019 [P] [US3] Write benchmark test in `backend/tests/reportes/test_export_020.py`: generate 10K rows x 10 columns XLSX — assert completes in < 2 seconds
- [x] T020 [US3] Write GIL release test in `backend/tests/reportes/test_export_020.py`: launch CSV generation in a thread, verify a concurrent Python operation completes without blocking

**Checkpoint**: All performance benchmarks pass. GIL release confirmed.

---

## Phase 5: User Story 4 — Graceful Fallback (Priority: P3)

**Goal**: When Rust extension is unavailable, Python fallback produces valid CSV (with BOM) and XLSX output

**Independent Test**: Mock `gravitea_rust` import failure, call `generate_csv()` and `generate_xlsx()`, verify output is valid

- [x] T021 [P] [US4] Write pytest test in `backend/tests/reportes/test_export_020.py`: patch `_USE_RUST_EXPORT = False`, call `generate_csv()` — assert output starts with BOM and contains correct CSV
- [x] T022 [P] [US4] Write pytest test in `backend/tests/reportes/test_export_020.py`: patch `_USE_RUST_EXPORT = False`, call `generate_xlsx()` — assert output is valid XLSX bytes

**Checkpoint**: Fallback mode produces valid output for both formats.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docker validation, regression testing, documentation update

- [x] T023 Rebuild Docker image and verify `from gravitea_rust import generate_csv, generate_xlsx` succeeds inside container
- [x] T024 Run full test suite (`pytest --tb=short -q`) — assert 0 regressions from SPEC-020 changes (17 SPEC-020 tests pass, 5 pre-existing failures in SPEC-017 conftest)
- [x] T025 Update `specs/020-rust-data-export/quickstart.md` with final build results and test counts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **US1 CSV (Phase 2)**: Depends on Phase 1 completion (Cargo.toml + errors.rs + module skeleton)
- **US2 XLSX (Phase 3)**: Depends on Phase 2 completion (shared `export.rs` file, shared `export_engine.py`)
- **US3 Performance (Phase 4)**: Depends on Phase 2 + Phase 3 (both formats must exist)
- **US4 Fallback (Phase 5)**: Depends on Phase 2 + Phase 3 (both wrapper functions must exist)
- **Polish (Phase 6)**: Depends on all previous phases

### Within Each Phase

- Rust implementation before Python integration (Rust produces the `.so` that Python imports)
- Internal functions before `#[pyfunction]` wrappers
- PyO3 wrappers before `lib.rs` registration
- All implementation before tests (tests need working functions)
- Type stubs [P] — independent of implementation, can run in parallel

### Parallel Opportunities

**Within Phase 1** (Setup):
```
T001 (Cargo.toml) || T002 (errors.rs)  → T003 (export.rs skeleton)
```

**Within Phase 2** (US1 — CSV):
```
T004 → T005 → T006 (sequential: internal → pyfunction → lib.rs)
T007 (Rust tests, after T004)
T008 (Python wrapper, after T006 + maturin build)
T009 (type stubs, parallel with any task)
T010 (pytest, after T008)
```

**Within Phase 3** (US2 — XLSX):
```
T011 → T012 → T013 (sequential: internal → pyfunction → lib.rs)
T014 (Rust tests, after T011)
T015 (Python wrapper, after T013 + maturin build)
T016 (type stubs, parallel with any task)
T017 (pytest, after T015)
```

**Phase 4** (Performance): T018 || T019, then T020

**Phase 5** (Fallback): T021 || T022

---

## Parallel Example: Phase 1 Setup

```bash
# These two tasks touch different files — run in parallel:
Agent A: "Add csv + rust_xlsxwriter to Cargo.toml"          # T001
Agent B: "Add ExportError variant to errors.rs"               # T002
# Then sequentially:
Agent A: "Create export.rs skeleton + mod declaration"        # T003
```

## Parallel Example: Phase 2 US1 — CSV

```bash
# Rust implementation chain (sequential — same file):
T004 → T005 → T006 → maturin build

# In parallel with the above:
T009: "Add generate_csv stub to gravitea_rust.pyi"

# After maturin build:
T007: "Run cargo test for CSV tests"
T008: "Create export_engine.py with CSV wrapper"
T010: "Run pytest CSV tests" (after T008)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: US1 CSV (T004–T010)
3. **STOP and VALIDATE**: `cargo test` + `pytest test_export_020.py -k csv`
4. Users get working CSV exports — immediate value

### Incremental Delivery

1. Setup → US1 CSV → Test independently → **MVP!**
2. Add US2 XLSX → Test independently → CSV + XLSX available
3. Add US3 Performance → Verify benchmarks → Production-ready confidence
4. Add US4 Fallback → Verify resilience → Deployment safety
5. Polish → Docker + regression → Ship

### Team Strategy (from plan.md)

| Agent | Phase | Tasks |
|-------|-------|-------|
| RUST-EXPERT (Opus) | Phase 1 + Rust parts of Phase 2–3 | T001–T007, T011–T014 |
| BACKEND-CODER (Sonnet) | Python parts of Phase 2–3 | T008–T010, T015–T017 |
| QA (Sonnet) | Phase 4 + Phase 5 | T018–T022 |
| LEAD (Opus) | Phase 6 | T023–T025 |

Sequential handoff: RUST-EXPERT → maturin build → BACKEND-CODER → QA → LEAD

---

## Notes

- [P] tasks = different files, no dependencies on in-progress work
- [Story] label maps task to specific user story for traceability
- US1 and US2 are both P1 but sequenced due to shared files (`export.rs`, `export_engine.py`)
- US3 and US4 can start as soon as both US1 and US2 complete
- Maturin build required between Rust implementation and Python integration
- Build command: `VIRTUAL_ENV=$(pwd)/backend/venv-wsl maturin develop --manifest-path rust/gravitea-core/Cargo.toml --release`
- Commit after each phase checkpoint
- Run `cargo test` after Rust changes, `pytest` after Python changes
