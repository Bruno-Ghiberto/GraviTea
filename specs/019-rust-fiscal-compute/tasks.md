# Tasks: Fiscal Compute Engine

**Input**: Design documents from `/specs/019-rust-fiscal-compute/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Tests**: Included — spec requires equivalence tests (SC-001), benchmarks (SC-002, SC-003),
fallback verification (SC-006), and full regression (SC-007).

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Can run in parallel (different files / independent logic within same file)
- **[Story]**: Which user story this task serves (US1–US5)
- Exact file paths required in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify SPEC-017 + SPEC-018 foundation, add crate dependencies, scaffold test file

- [x] T001 Verify SPEC-017 + SPEC-018 foundation: run `backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello()); gravitea_rust.encrypt_value('test', b'0'*32); print('Foundation OK')"` — if this fails, stop and fix prerequisites before proceeding
- [x] T002 Add 4 crate dependencies to `[dependencies]` section of `rust/gravitea-core/Cargo.toml`: `rust_decimal = "1.36"`, `rust_decimal_macros = "1.36"`, `serde = { version = "1.0", features = ["derive"] }`, `serde_json = "1.0"`
- [x] T003 [P] Create `backend/tests/rust_integration/test_compute_019.py` with: module-level imports (`pytest`, `json`, `decimal.Decimal`), a `_USE_RUST` toggle helper, and an empty `pass` body — file must be importable

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create decimal_utils.rs shared infrastructure and wire compute module into PyO3

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create `rust/gravitea-core/src/decimal_utils.rs` with 3 helper functions: `parse_decimal(s: &str) -> Result<Decimal, GraviteaError>` (wraps `Decimal::from_str` with `GraviteaError::ComputeError` mapping), `decimal_to_string(d: &Decimal) -> String` (calls `d.normalize().to_string()`), and `dual_tolerance_eq(expected: &Decimal, actual: &Decimal, abs_tol: &Decimal, rel_tol: &Decimal) -> bool` (returns true if `|diff| <= abs_tol` OR `|diff| <= rel_tol * |expected|`); add `use rust_decimal::Decimal; use std::str::FromStr;` and import `GraviteaError` from `super::errors`; add `#[cfg(test)] mod tests` block with ≥4 tests: `test_parse_valid_decimals` (0, 0.001, 99999999999999.999, -1234.567), `test_parse_invalid_string` ("abc" → ComputeError), `test_roundtrip_normalize` (Decimal("10.500") → "10.5", Decimal("0.000") → "0"), `test_dual_tolerance_boundary` (0.01 abs passes, 0.011 abs fails on small values, relative tolerance kicks in on large values)
- [x] T005 Create `rust/gravitea-core/src/compute.rs` with: `use pyo3::prelude::*; use pyo3::exceptions::PyValueError;` imports, `use super::decimal_utils::*; use super::errors::GraviteaError;` imports, `use rust_decimal::prelude::*; use rust_decimal_macros::dec;` imports, `use serde::{Deserialize, Serialize}; use serde_json;` imports, and 5 `#[pyfunction]` stubs that each return `Err(GraviteaError::ComputeError { msg: "not implemented".to_string() }.into())` — module must compile: `validate_importes`, `calculate_iva_breakdown`, `validate_iva_breakdown`, `aggregate_stock_levels`, `validate_cuit`
- [x] T006 Wire modules in `rust/gravitea-core/src/lib.rs`: add `mod decimal_utils;` and `mod compute;` declarations at the top (after existing `mod crypto;`); add 5 `#[pymodule_export]` lines inside the existing `mod gravitea_rust` block: `use super::compute::validate_importes;`, `use super::compute::calculate_iva_breakdown;`, `use super::compute::validate_iva_breakdown;`, `use super::compute::aggregate_stock_levels;`, `use super::compute::validate_cuit;` — follow the existing `use super::crypto::*` pattern exactly
- [x] T007 Run `cargo check` from `rust/gravitea-core/` and confirm it exits 0 with all 4 new crates resolved; fix any dependency version conflicts or import errors before proceeding

**Checkpoint**: `cargo check` passes with decimal_utils + compute stubs compiled — user story implementation can now begin

---

## Phase 3: User Story 1 — ARCA Amount Validation (Priority: P1) 🎯 MVP

**Goal**: Rust `validate_importes` validates the ARCA master amount equation with dual-tolerance;
Python dispatch falls through to Rust; equivalence with Python implementation proven.

**Independent Test**: `backend/venv-wsl/bin/python -c "import gravitea_rust; gravitea_rust.validate_importes('121.00','100.00','21.00','0.00','0.00','0.00'); print('US1 OK')"` — must print `US1 OK` without importing Django.

### Rust Implementation

- [x] T008 [US1] Write `#[cfg(test)]` tests for `validate_importes` in `rust/gravitea-core/src/compute.rs`: `test_validate_importes_valid` (121.00 = 100.00 + 0.00 + 21.00 + 0.00 + 0.00 passes), `test_validate_importes_invalid` (122.00 ≠ expected → ComputeError with "Amount equation does not balance" message), `test_validate_importes_zero_comprobante` (all 6 fields = "0.00" passes — valid zero-value comprobante), `test_validate_importes_tolerance_absolute` (imp_total="121.005" vs expected=121.00 passes within 0.01 tolerance), `test_validate_importes_tolerance_fails` (imp_total="121.02" vs expected=121.00 fails — beyond both tolerances)
- [x] T009 [US1] Implement `validate_importes(imp_total: &str, imp_neto: &str, imp_iva: &str, imp_trib: &str, imp_op_ex: &str, imp_tot_conc: &str) -> PyResult<()>` in `rust/gravitea-core/src/compute.rs`: parse all 6 args via `parse_decimal()`; compute `expected = imp_neto + imp_op_ex + imp_iva + imp_trib + imp_tot_conc`; call `dual_tolerance_eq(expected, parsed_total, dec!(0.01), dec!(0.0001))`; on mismatch → `Err(GraviteaError::ComputeError { msg: format!("Amount equation does not balance: ImpTotal ({}) != ... = {}. Difference: {}.", ...) })` matching the Python error format exactly
- [x] T010 [US1] Run `cargo test` from `rust/gravitea-core/` and confirm ≥4 decimal tests (T004) + ≥5 validate_importes tests (T008) all pass; fix any failures before proceeding

### Python Integration

- [x] T011 [US1] Add `_USE_RUST` dispatch for `validate_importes` to `backend/apps/facturacion/validators.py`: add `try: from gravitea_rust import validate_importes as _rust_validate_importes; _USE_RUST_COMPUTE = True` / `except (ImportError, OSError): _USE_RUST_COMPUTE = False` block at module top; inside `validate_importes()`, before the existing Python body, add `if _USE_RUST_COMPUTE:` block that converts all 6 Decimal args to `str()`, calls `_rust_validate_importes(...)`, wraps any `RuntimeError` → `ValidationError` for backward compatibility, and returns on success; the existing Python body is the fallback (unchanged)
- [x] T012 [P] [US1] Write test `test_validate_importes_arca_vectors` in `backend/tests/rust_integration/test_compute_019.py`: define ≥10 known ARCA test vectors (valid and invalid amount sets including zero-value comprobante, tolerance boundary cases); for each, call `gravitea_rust.validate_importes(...)` directly; assert that valid vectors pass and invalid vectors raise RuntimeError with expected message substring
- [x] T013 [P] [US1] Write tests `test_validate_importes_fallback` and `test_validate_importes_benchmark` in `backend/tests/rust_integration/test_compute_019.py`: fallback test monkeypatches `_USE_RUST_COMPUTE=False` and verifies Python path produces identical accept/reject decisions for all 10 vectors; benchmark test uses `pytest-benchmark` with `@pytest.mark.slow` on 1000 iterations of a typical 6-field validation

**Checkpoint**: `cargo test` ≥9 passing; validate_importes callable from Python with fallback intact

---

## Phase 4: User Story 2 — IVA Breakdown Computation (Priority: P1)

**Goal**: Rust `calculate_iva_breakdown` groups line items by IVA rate, computes per-rate
base_imp and importe, maps rates to ARCA AlicIvaId codes; output JSON matches expected structure.

**Independent Test**: `backend/venv-wsl/bin/python -c "import gravitea_rust, json; items=json.dumps([{'price':'100.00','quantity':'2','iva_rate':'21.00'}]); r=json.loads(gravitea_rust.calculate_iva_breakdown(items)); assert r[0]['iva_id']==5; print('US2 OK')"` — must print `US2 OK`.

### Rust Implementation

- [x] T014 [US2] Write `#[cfg(test)]` tests for `calculate_iva_breakdown` in `rust/gravitea-core/src/compute.rs`: `test_iva_single_rate_21` (1 item at 21% → iva_id=5, base_imp=price*qty, importe=base*0.21), `test_iva_all_6_rates` (6 items each at 0%, 2.5%, 5%, 10.5%, 21%, 27% → verify all 6 AlicIva entries with correct iva_ids [3,9,8,4,5,6]), `test_iva_grouping` (3 items all at 21% → single entry with aggregated amounts), `test_iva_unknown_rate_defaults` (item at 15% → defaults to iva_id=5), `test_iva_empty_items` (empty JSON array → empty result array), `test_iva_negative_quantity` (negative qty for credit note → negative base_imp and importe, no error)
- [x] T015 [US2] Define serde structs in `rust/gravitea-core/src/compute.rs`: `#[derive(Deserialize)] struct LineItem { price: String, quantity: String, iva_rate: String }` and `#[derive(Serialize)] struct AlicIvaResult { iva_id: i32, base_imp: String, importe: String }`; implement `calculate_iva_breakdown(items_json: &str) -> PyResult<String>`: deserialize JSON array of `LineItem`; group by `iva_rate`; for each group compute `base_imp = sum(price * qty)` and `importe = base_imp * rate / 100`; map rate→iva_id using normalized Decimal comparison (dec!(0)→3, dec!(2.5)→9, dec!(5)→8, dec!(10.5)→4, dec!(21)→5, dec!(27)→6, _→5); serialize result array to JSON string
- [x] T016 [US2] Run `cargo test` and confirm all IVA breakdown calculation tests (T014) pass; verify all 6 rates produce correct iva_id values

### Python Integration

- [x] T017 [US2] Add `_USE_RUST` dispatch to `backend/apps/ventas/services/sale_service.py` for `_create_alic_iva`: add the `try: from gravitea_rust import calculate_iva_breakdown as _rust_calculate_iva; _USE_RUST_COMPUTE = True` / `except` block at module top; inside `_create_alic_iva`, add Rust branch that: (a) serializes `items` list to JSON `[{"price": str(item.subtotal), "quantity": "1", "iva_rate": str(item.tax_rate)}]`, (b) calls `_rust_calculate_iva(items_json)`, (c) deserializes result, (d) creates `AlicIva` ORM objects from the result; the existing Python body is the fallback (unchanged)
- [x] T018 [P] [US2] Write test `test_calculate_iva_all_rates` in `backend/tests/rust_integration/test_compute_019.py`: construct line items for all 6 IVA rates (0%, 2.5%, 5%, 10.5%, 21%, 27%), call `gravitea_rust.calculate_iva_breakdown(...)`, deserialize result, and assert each entry has the correct `iva_id` and that `base_imp * rate / 100 ≈ importe` within tolerance; also test mixed-rate orders (3 items across 2 rates) and negative quantities (credit notes)
- [x] T019 [P] [US2] Write tests `test_calculate_iva_fallback` and `test_calculate_iva_benchmark` in `backend/tests/rust_integration/test_compute_019.py`: fallback test verifies Python path produces equivalent AlicIva structure; benchmark uses `pytest-benchmark` with `@pytest.mark.slow` on 20-item invoices (target: ≥3× speedup, SC-002)

**Checkpoint**: All IVA rate-to-ID mappings verified; US1 + US2 both independently functional

---

## Phase 5: User Story 3 — CUIT Validation Consolidation (Priority: P2)

**Goal**: Rust `validate_cuit` implements Modulo-11 with all edge cases; replaces duplicate
Python implementations in `ventas/validators.py` and `facturacion/serializers.py`.

**Independent Test**: `backend/venv-wsl/bin/python -c "import gravitea_rust; gravitea_rust.validate_cuit('27000000006'); print('US3 OK')"` — must print `US3 OK`.

### Rust Implementation

- [x] T020 [US3] Write `#[cfg(test)]` tests for `validate_cuit` in `rust/gravitea-core/src/compute.rs`: `test_cuit_valid` (known valid CUIT "27000000006" passes — verify: 5×2+4×7=38, 38%11=5, 11-5=6, digit[10]=6 ✅), `test_cuit_invalid_check` (change last digit of valid CUIT → ComputeError), `test_cuit_too_short` (10 digits → ComputeError "must be exactly 11 digits"), `test_cuit_too_long` (12 digits → ComputeError), `test_cuit_non_numeric` ("2012345678a" → ComputeError), `test_cuit_check_11_becomes_0` (construct CUIT where sum%11=0 → check digit=0), `test_cuit_check_10_becomes_9` (construct CUIT where sum%11=1 → check digit=9)
- [x] T021 [US3] Implement `validate_cuit(cuit: &str) -> PyResult<()>` in `rust/gravitea-core/src/compute.rs`: validate length==11 and all ASCII digits; apply weights [5,4,3,2,7,6,5,4,3,2] on first 10 digits; compute `check = 11 - (sum % 11)`; map: 11→0, 10→9; compare with cuit[10]; on mismatch → `Err(GraviteaError::ComputeError { msg: "CUIT check digit is invalid.".to_string() })`
- [x] T022 [US3] Run `cargo test` and confirm all 7 CUIT tests pass including both special-case edge cases

### Python Integration

- [x] T023 [US3] Add `_USE_RUST` dispatch to `backend/apps/ventas/validators.py` for `validate_cuit`: add `try: from gravitea_rust import validate_cuit as _rust_validate_cuit; _USE_RUST_COMPUTE = True` / `except` block; inside `validate_cuit()`, add `if _USE_RUST_COMPUTE: try: _rust_validate_cuit(cuit); return` / `except RuntimeError as e: raise ValidationError(str(e))` before existing Python body
- [x] T024 [US3] Add `_USE_RUST` dispatch to `backend/apps/facturacion/serializers.py` for `_validate_cuit` (line ~51): point to the same Rust function via same import pattern; this consolidates the duplicate implementation (SC-004) — both call sites now use the single Rust function with Python fallback
- [x] T025 [P] [US3] Write tests `test_validate_cuit_corpus` in `backend/tests/rust_integration/test_compute_019.py`: define corpus of ≥10 CUITs (5 valid, 5 invalid — including short, long, non-numeric, bad check digit, and check=10→9 special case); for each, call `gravitea_rust.validate_cuit(...)` directly and assert expected outcome
- [x] T026 [P] [US3] Write test `test_validate_cuit_fallback` in `backend/tests/rust_integration/test_compute_019.py`: monkeypatch `_USE_RUST_COMPUTE=False` in both `ventas/validators.py` and `facturacion/serializers.py`; verify Python path produces identical accept/reject decisions for the 10-CUIT corpus

**Checkpoint**: CUIT consolidation complete; single Rust function replaces 2 Python implementations; US1-US3 independently functional

---

## Phase 6: User Story 4 — Batch Stock Aggregation with Concurrency (Priority: P2)

**Goal**: Rust `aggregate_stock_levels` processes batch stock movements with GIL released;
outputs per-(product, branch) totals including total, reserved, and available quantities.

**Independent Test**: `backend/venv-wsl/bin/python -c "import gravitea_rust, json; m=json.dumps([{'product_id':'p1','branch_id':'b1','quantity':'10.000','movement_type':'IN'},{'product_id':'p1','branch_id':'b1','quantity':'3.000','movement_type':'OUT'}]); r=json.loads(gravitea_rust.aggregate_stock_levels(m)); assert r['p1']['b1']['available']=='7'; print('US4 OK')"` — must print `US4 OK`.

### Rust Implementation

- [x] T027 [US4] Define serde structs in `rust/gravitea-core/src/compute.rs`: `#[derive(Deserialize)] struct StockMovement { product_id: String, branch_id: String, quantity: String, movement_type: String }` and output struct for serialization; write `#[cfg(test)]` tests: `test_aggregate_single_product` (3 IN + 1 OUT → correct total and available), `test_aggregate_multi_product_multi_branch` (2 products × 2 branches → verify independent grouping), `test_aggregate_empty_input` (empty JSON array → empty JSON object), `test_aggregate_decimal_precision` (quantities with 4 decimal places preserved), `test_aggregate_all_movement_types` (IN, OUT, ADJUSTMENT, TRANSFER_IN, TRANSFER_OUT, RESERVED, RELEASED all handled correctly)
- [x] T028 [US4] Implement `aggregate_stock_levels(py: Python<'_>, movements_json: &str) -> PyResult<String>` in `rust/gravitea-core/src/compute.rs`: deserialize JSON array; use `py.allow_threads(|| { ... })` to release GIL; inside the closure: group by (product_id, branch_id), for each group compute `total = sum(IN + ADJUSTMENT + TRANSFER_IN) - sum(OUT + TRANSFER_OUT)`, `reserved = sum(RESERVED) - sum(RELEASED)`, `available = total - reserved`; serialize nested JSON `{product_id: {branch_id: {total, reserved, available}}}` and return
- [x] T029 [US4] Run `cargo test` and confirm all 5 aggregation tests pass; verify that the function signature includes `py: Python<'_>` for GIL release

### Python Integration

- [x] T030 [US4] Add `_USE_RUST` dispatch to `backend/apps/inventario/services/stock_service.py`: add import block; create new method or standalone function `aggregate_stock_levels_batch(movements_qs)` that serializes QuerySet to JSON `[{"product_id": str(m.product_id), "branch_id": str(m.branch_id), "quantity": str(m.quantity), "movement_type": m.movement_type}]`, calls Rust function, deserializes result; Python fallback iterates and aggregates using Python loops
- [x] T031 [P] [US4] Write test `test_aggregate_stock_shaped_data` in `backend/tests/rust_integration/test_compute_019.py`: generate 500 movement records across 50 products × 3 branches with mixed movement types; call `gravitea_rust.aggregate_stock_levels(...)` directly; verify per-product-branch totals match manual Python computation (SC-003)
- [x] T032 [P] [US4] Write tests `test_aggregate_stock_benchmark` and `test_aggregate_stock_empty` in `backend/tests/rust_integration/test_compute_019.py`: benchmark uses `pytest-benchmark` with `@pytest.mark.slow` on 500-record batch (target: ≥3× speedup, SC-003); empty test verifies empty input returns empty JSON object `{}`

**Checkpoint**: GIL-released batch aggregation working; US1-US4 independently functional

---

## Phase 7: User Story 5 — IVA Breakdown Validation (Priority: P3)

**Goal**: Rust `validate_iva_breakdown` enforces comprobante type rules (A/B/M mandatory,
C prohibited) and validates sum consistency (AlicIva importe sum ≈ imp_iva, base_imp sum ≈ imp_neto).

**Independent Test**: `backend/venv-wsl/bin/python -c "import gravitea_rust, json; aliciva=json.dumps([{'iva_id':5,'base_imp':'100.00','importe':'21.00'}]); gravitea_rust.validate_iva_breakdown(1, aliciva, '21.00', '100.00'); print('US5 OK')"` — must print `US5 OK`.

### Rust Implementation

- [x] T033 [US5] Define serde struct `#[derive(Deserialize)] struct AlicIvaEntry { iva_id: i32, base_imp: String, importe: String }` in `rust/gravitea-core/src/compute.rs`; write `#[cfg(test)]` tests: `test_iva_validation_type_a_mandatory` (cbte_tipo=1, empty AlicIva → ComputeError "mandatory"), `test_iva_validation_type_c_prohibited` (cbte_tipo=11, non-empty AlicIva → ComputeError "prohibited"), `test_iva_validation_sum_match` (cbte_tipo=1, AlicIva importe sums to imp_iva → passes), `test_iva_validation_importe_mismatch` (sum of importe ≠ imp_iva beyond tolerance → ComputeError), `test_iva_validation_base_imp_mismatch` (sum of base_imp ≠ imp_neto beyond tolerance → ComputeError), `test_iva_validation_type_b_mandatory` (cbte_tipo=6 → mandatory, same as A)
- [x] T034 [US5] Implement `validate_iva_breakdown(cbte_tipo: i32, aliciva_json: &str, imp_iva: &str, imp_neto: &str) -> PyResult<()>` in `rust/gravitea-core/src/compute.rs`: define IVA-required CbteTipo codes `[1,2,3,6,7,8,51,52,53]` (A/B/M types) and IVA-prohibited codes `[11,12,13]` (C types); parse AlicIva JSON array; enforce mandatory/prohibited rules; sum importe and base_imp; use `dual_tolerance_eq` to check sums against imp_iva and imp_neto; on failure → `Err(GraviteaError::ComputeError { msg: ... })` with message matching Python format
- [x] T035 [US5] Run `cargo test` and confirm all 6 IVA validation tests pass; verify both mandatory and prohibited paths are covered

### Python Integration

- [x] T036 [US5] Add `_USE_RUST` dispatch for `validate_iva_breakdown` to `backend/apps/facturacion/validators.py`: inside `validate_iva_breakdown()`, before the existing Python body, add `if _USE_RUST_COMPUTE:` block that converts `aliciva_list` to JSON string `[{"iva_id": item["iva_id"], "base_imp": str(item["base_imp"]), "importe": str(item["importe"])}]`, converts Decimal args to `str()`, calls `_rust_validate_iva_breakdown(cbte_tipo, aliciva_json, str(imp_iva), str(imp_neto))`, wraps `RuntimeError` → `ValidationError`; note: this modifies the same file as T011 — add to the existing `_USE_RUST_COMPUTE` import and dispatch pattern
- [x] T037 [P] [US5] Write tests in `backend/tests/rust_integration/test_compute_019.py`: `test_validate_iva_breakdown_type_rules` (Type A mandatory, Type C prohibited, Type B mandatory, Type M mandatory — test cbte_tipo codes 1, 6, 11, 51), `test_validate_iva_sum_checks` (importe sum mismatch, base_imp sum mismatch, both matching), `test_validate_iva_fallback` (monkeypatch `_USE_RUST_COMPUTE=False`, verify Python path identical)

**Checkpoint**: All 5 user stories fully implemented and independently verifiable

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: ARCA expert review, type stubs, Docker build, regression, benchmarks, documentation

- [x] T038 ARCA expert review of all fiscal logic in `rust/gravitea-core/src/compute.rs`: verify (a) all 6 IVA rates mapped correctly to ARCA IDs (0%→3, 2.5%→9, 5%→8, 10.5%→4, 21%→5, 27%→6), (b) tolerance values match ARCA acceptance rules (ABSOLUTE=0.01, RELATIVE=0.0001), (c) CUIT Modulo-11 weight sequence is [5,4,3,2,7,6,5,4,3,2] with special cases 11→0 and 10→9, (d) validate_importes checks all 6 required ARCA amount fields, (e) validate_iva_breakdown enforces correct comprobante type rules — query Qdrant `backend/venv-wsl/bin/python scripts/qdrant/qdrant_search.py -q "AlicIva IVA rates IvaId" -c arca_api_specs -l 5` to cross-reference; report APPROVED or CHANGES_REQUIRED
- [x] T039 [P] Update `backend/gravitea_rust.pyi` with 5 new function signatures: `def validate_importes(imp_total: str, imp_neto: str, imp_iva: str, imp_trib: str, imp_op_ex: str, imp_tot_conc: str) -> None: ...`, `def calculate_iva_breakdown(items_json: str) -> str: ...`, `def validate_iva_breakdown(cbte_tipo: int, aliciva_json: str, imp_iva: str, imp_neto: str) -> None: ...`, `def aggregate_stock_levels(movements_json: str) -> str: ...`, `def validate_cuit(cuit: str) -> None: ...`
- [x] T040 [P] Run full `cargo test` from `rust/gravitea-core/` — confirm ≥12 new compute tests + ≥4 decimal tests + all existing crypto tests pass; document total test count
- [x] T041 [P] Rebuild Docker image: run `docker compose build web`; then run `docker compose run --rm web python -c "import gravitea_rust, json; gravitea_rust.validate_importes('121.00','100.00','21.00','0.00','0.00','0.00'); gravitea_rust.validate_cuit('27000000006'); items=json.dumps([{'price':'100.00','quantity':'1','iva_rate':'21.00'}]); r=gravitea_rust.calculate_iva_breakdown(items); print(f'Docker compute OK: {r}')"` — must succeed (SC-008)
- [x] T042 Run compute integration tests inside Docker container: `docker compose exec web python -m pytest backend/tests/rust_integration/test_compute_019.py -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q`; confirm all tests pass in container environment
- [x] T043 Run full test suite regression via `scripts/run-tests-external.sh "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"`; read `.summary` file and confirm 0 new failures vs SPEC-018 baseline (SC-007)
- [x] T044 [P] Run benchmark tests: `backend/venv-wsl/bin/python -m pytest backend/tests/rust_integration/test_compute_019.py -m slow -p no:django --confcutdir=backend/tests/rust_integration -o "addopts=" --tb=short -q`; document measured Rust/Python speedup ratios per function in `specs/019-rust-fiscal-compute/research.md` under a new "Benchmark Results" section (targets: ≥3× per function, SC-002, SC-003)
- [x] T045 [P] Update `specs/019-rust-fiscal-compute/quickstart.md` with actual build output examples, confirmed test counts, benchmark figures, and any platform-specific notes discovered during Docker validation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (T001–T003)      → No dependencies
Phase 2 (T004–T007)      → Requires T001 (foundation verified), T002 (deps added)
Phase 3 (T008–T013)      → Requires Phase 2 complete (cargo check passes)
                            TDD order: T008 (tests) → T009 (impl) → T010 (cargo test) → T011 (dispatch) → T012+T013
Phase 4 (T014–T019)      → Requires T004 (decimal_utils) + T005 (compute.rs exists) + T006 (lib.rs wired)
                            TDD order: T014 (tests) → T015 (impl) → T016 (cargo test) → T017 (dispatch) → T018+T019
Phase 5 (T020–T026)      → Requires T004 (decimal_utils) + T005 (compute.rs exists)
                            TDD order: T020 (tests) → T021 (impl) → T022 (cargo test) → T023+T024 (dispatch) → T025+T026
Phase 6 (T027–T032)      → Requires T004 (decimal_utils) + T005 (compute.rs with serde structs)
                            TDD order: T027 (tests+structs) → T028 (impl) → T029 (cargo test) → T030 (dispatch) → T031+T032
Phase 7 (T033–T037)      → Requires T004 (dual_tolerance_eq) + T005 (compute.rs with AlicIva structs)
                            TDD order: T033 (tests) → T034 (impl) → T035 (cargo test) → T036 (dispatch) → T037
Phase 8 (T038–T045)      → Requires all Phase 3–7 tasks complete
```

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 — no dependency on US2-US5
- **US2 (P1)**: Starts after Phase 2 — no dependency on US1/US3-US5 (different function in compute.rs)
- **US3 (P2)**: Starts after Phase 2 — no dependency on US1/US2/US4/US5
- **US4 (P2)**: Starts after Phase 2 — no dependency on US1-US3/US5
- **US5 (P3)**: Starts after Phase 2 — may reuse US2's AlicIva serde structs but is independently testable

**File conflict note**: US1 (T011) and US5 (T036) both modify `backend/apps/facturacion/validators.py`. If executed in parallel, coordinate: US1 adds the `_USE_RUST_COMPUTE` import + `validate_importes` dispatch; US5 adds `validate_iva_breakdown` dispatch to the same import block.

### Within Each User Story (TDD order — §X constitution)

```
Rust tests written → Rust implementation → cargo test pass → Python dispatch → Python tests
```

### Parallel Opportunities

- T003 (test file scaffold) with T004 (decimal_utils) — different directories
- T005 + T006 can run after T004 — T005 (compute stubs) and T006 (lib.rs wiring) are sequential
- **US1 + US2 + US3 + US4 + US5 Rust implementations** (Phases 3–7): All modify different functions in compute.rs — can be parallelized if agents coordinate on the shared file. With a single agent, execute sequentially in priority order (P1 → P2 → P3).
- T012 + T013 (US1 Python tests) — independent test functions
- T018 + T019 (US2 Python tests) — independent test functions
- T025 + T026 (US3 Python tests) — independent test functions
- T031 + T032 (US4 Python tests) — independent test functions
- T039 + T040 + T041 + T044 + T045 (Polish) — fully independent tasks

---

## Parallel Execution Examples

### Phase 2 (Foundational): Sequential Build

```
Sequential: T004 (decimal_utils.rs) → T005 (compute.rs stubs) → T006 (lib.rs wiring) → T007 (cargo check)
```

### Phase 3 (US1) + Phase 4 (US2): With Single Agent (Sequential)

```
US1: T008 (tests) → T009 (impl) → T010 (cargo test)
→ US2: T014 (tests) → T015 (impl) → T016 (cargo test)
→ US1 Python: T011 (dispatch) → T012+T013 (tests, parallel)
→ US2 Python: T017 (dispatch) → T018+T019 (tests, parallel)
```

### Phase 3–7: With Agent Team (Parallel Rust then Sequential Python)

```
RUST-EXPERT (all Rust implementation):
  T004 → T005+T006 → T007
  → T008+T009+T010 (US1 Rust)
  → T014+T015+T016 (US2 Rust)
  → T020+T021+T022 (US3 Rust)
  → T027+T028+T029 (US4 Rust)
  → T033+T034+T035 (US5 Rust)

ARCA-EXPERT (review, after RUST-EXPERT completes):
  T038 (fiscal review of compute.rs)

QA (Python integration, after ARCA-EXPERT sign-off):
  Parallel: T011 + T017 + T023+T024 + T030 + T036  (all dispatch modifications)
  → Parallel: T012+T013 + T018+T019 + T025+T026 + T031+T032 + T037  (all Python tests)
```

### Phase 8 (Polish): Mostly Parallel

```
Parallel A: T039 — type stub update
Parallel B: T040 — full cargo test
Parallel C: T041 — Docker rebuild
Parallel D: T044 — benchmark tests
Parallel E: T045 — quickstart update
→ Sequential: T042 (Docker tests, needs T041) → T043 (full regression)
```

---

## Implementation Strategy

### MVP First (US1 + US2 Only — both P1)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T007)
3. Complete Phase 3: US1 — ARCA Amount Validation (T008–T013)
4. **VALIDATE**: `python -c "from gravitea_rust import validate_importes; ..."` — Rust path live
5. Complete Phase 4: US2 — IVA Breakdown Computation (T014–T019)
6. **VALIDATE**: All 6 IVA rate mappings verified — ARCA compliance for invoice emission
7. **STOP** — fiscal invoice emission path accelerated (US3-US5 are P2/P3)

### Incremental Delivery

1. Setup + Foundational → compile verified
2. US1 → validate_importes live → **Demo: ARCA equation validated in Rust**
3. US2 → calculate_iva_breakdown live → **Demo: AlicIva computation ≥3× faster**
4. US3 → validate_cuit consolidated → **Deploy: DRY — 2 files → 1 function**
5. US4 → aggregate_stock_levels live → **Deploy: GIL released for stock dashboards**
6. US5 → validate_iva_breakdown live → **Complete: all 5 fiscal compute functions**
7. Polish → ARCA review + Docker + regression → **Release**

### Parallel Team Strategy

With multiple agents (matching instruction-implement.md team):

```
RUST-EXPERT:  Phase 2 → Phase 3–7 Rust tasks (T004–T035)
ARCA-EXPERT:  Phase 8 (T038 review) — after RUST-EXPERT completes
QA:           Phase 3–7 Python tasks (T011–T037 dispatch + tests) — after ARCA sign-off
WIKI-EXPERT:  On-demand — spawned when any agent is blocked on documentation
LEAD:         Phase 1 (Setup) + Phase 8 (T039–T045 polish) + orchestration
```

---

## Notes

- **[P]** tasks operate on different logical units (separate functions, independent test cases) — parallelizable within their phase
- **[Story]** label maps each task to the user story it serves for traceability
- **TDD enforced (§X)**: Test tasks precede implementation tasks within each user story
- `cargo test` is the gate between Rust implementation and Python integration
- The ARCA expert review at T038 is a required gate before Docker release — but NOT a gate for Python integration (QA can start Python dispatch after cargo tests pass if needed)
- All monetary values cross FFI as `&str` — NEVER as `f64` or `i64` (FR-009, research.md R-001)
- JSON boundary for collection parameters (items, AlicIva entries, stock movements) — `&str` for scalar parameters (research.md R-005)
- GIL release ONLY for `aggregate_stock_levels` (FR-007) — other functions are sub-millisecond
- Error mapping: Rust `GraviteaError::ComputeError` → `PyRuntimeError` → Python wrapper catches and re-raises as `ValidationError` for backward compatibility with DRF serializer error handling (FR-011)
- Whitespace/empty guards in Python wrappers ONLY (not in Rust) — per SPEC-018 pattern (FR-012)
- All pytest runs use external runner for agents: `scripts/run-tests-external.sh`
- WIKI-EXPERT available on-demand for RAG queries — see `Docs/Temp-prompting/agents/agent-WIKI-EXPERT.md`
- Commit after each user story checkpoint
