# Implementation Plan: Fiscal Compute Engine

**Branch**: `019-rust-fiscal-compute` | **Date**: 2026-02-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/019-rust-fiscal-compute/spec.md`

## Summary

Implement Rust versions of 5 fiscal and stock computation functions in a new
`rust/gravitea-core/src/compute.rs` module: `validate_importes` (ARCA master
equation), `calculate_iva_breakdown` (AlicIva array generation),
`validate_iva_breakdown` (sum + comprobante type checks),
`aggregate_stock_levels` (batch GIL-released aggregation), and `validate_cuit`
(Modulo-11 consolidation). All monetary values cross the FFI boundary as
`&str` → `rust_decimal::Decimal` → `String`, never as float. A shared
`decimal_utils.rs` module provides str↔Decimal conversion helpers that
subsequent money-handling Rust specs (020, 024) will reuse.

## Technical Context

**Language/Version**: Python 3.14.3 (host) + Rust 1.93.1 (acceleration layer)
**Primary Dependencies**: PyO3 0.28, Maturin 1.12.4; `rust_decimal 1.36`, `rust_decimal_macros 1.36` (new); existing `base64`, `hex`, etc. from SPEC-018
**Storage**: N/A — no new Django models or database migrations
**Testing**: `cargo test` (Rust-native) + `pytest` (Python integration + equivalence)
**Target Platform**: Linux (Docker container, WSL2 development)
**Project Type**: Single project — Rust FFI extension into existing Django backend
**Performance Goals**: ≥3× speedup per function vs Python equivalents (SC-002, SC-003)
**Constraints**: str↔Decimal boundary for all monetary values (no float); ARCA tolerance ABSOLUTE=0.01, RELATIVE=0.0001; GIL release ONLY for `aggregate_stock_levels`; Python fallback mandatory
**Scale/Scope**: Affects invoice emission (validate_importes, calculate/validate_iva_breakdown), customer/supplier creation (validate_cuit), and warehouse dashboard (aggregate_stock_levels); 2 new Rust source files, 3-5 modified Python files, 1 new test file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **§I — Ironclad Data Model** | ✅ PASS | No schema changes; DECIMAL(17,3) precision preserved via rust_decimal (28 sig digits) |
| **§II — Multi-Tenant Isolation** | ✅ PASS | No model or RLS changes; fiscal validation is tenant-agnostic pure compute |
| **§III — Modular Django Architecture** | ✅ PASS | Changes confined to `facturacion/validators.py`, `ventas/validators.py`, `ventas/services/sale_service.py`, `inventario/services/stock_service.py`; no new Django apps |
| **§IV — Application-Level Encryption** | ✅ PASS | No encryption changes |
| **§V — Secure Authentication** | ✅ PASS | No auth changes |
| **§VI — Fiscal Compliance (ARCA)** | ✅ PASS — Direct implementation | This feature strengthens §VI: Rust compute matches ARCA rules exactly (IVA rates, tolerances, CUIT Modulo-11) with equivalence tests against known ARCA test vectors |
| **§IX — Secure Data Operations** | ✅ PASS | No mass assignment or permission changes |
| **§X — Test-Driven Development** | ✅ PASS | ≥12 Rust-native tests + pytest integration + equivalence tests with ARCA vectors |
| **§XIV — API Documentation** | ✅ PASS | No new endpoints; `gravitea_rust.pyi` stub updated |

**Gate result**: PASS — No constitution violations. Proceed to Phase 0.

**Post-design re-check**: After Phase 1 design, verify that all Python wrapper changes preserve existing function signatures. Verify that `validate_importes` and `validate_iva_breakdown` raise `ValueError` (not `RuntimeError`) for backward compatibility with the `ComprobanteEmitirSerializer.validate()` orchestrator at `facturacion/serializers.py:599`.

## Project Structure

### Documentation (this feature)

```text
specs/019-rust-fiscal-compute/
├── spec.md              ✅ (speckit.specify output)
├── checklists/
│   └── requirements.md  ✅ (speckit.specify output)
├── plan.md              ← This file
├── research.md          ← Phase 0 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             (speckit.tasks command — NOT created by speckit.plan)
```

### Source Code (concrete paths modified by this feature)

```text
rust/gravitea-core/
├── Cargo.toml                    MODIFY — add rust_decimal + rust_decimal_macros
└── src/
    ├── lib.rs                    MODIFY — add mod compute, mod decimal_utils; 5 #[pymodule_export]
    ├── errors.rs                 UNCHANGED
    ├── crypto.rs                 UNCHANGED (SPEC-018)
    ├── decimal_utils.rs          NEW — str↔Decimal helpers (shared infrastructure)
    └── compute.rs                NEW — 5 #[pyfunction] exports

backend/
├── gravitea_rust.pyi             MODIFY — add 5 function stubs
├── apps/facturacion/
│   └── validators.py             MODIFY — add _USE_RUST dispatch for validate_importes + validate_iva_breakdown
├── apps/ventas/
│   ├── validators.py             MODIFY — redirect validate_cuit to Rust
│   └── services/sale_service.py  MODIFY — add _USE_RUST dispatch for _create_alic_iva → calculate_iva_breakdown
├── apps/inventario/services/
│   └── stock_service.py          MODIFY — add aggregate_stock_levels Rust dispatch
└── tests/
    └── rust_integration/
        ├── conftest.py            UNCHANGED (from SPEC-018)
        └── test_compute_019.py    NEW — all fiscal compute integration tests
```

**Structure Decision**: Single project (Option 1 variant). No new top-level directories. All Rust source in the existing `rust/gravitea-core/` crate. `decimal_utils.rs` is a shared Rust module — not a pymodule, just internal helpers used by `compute.rs` (and future specs like 020, 024).

---

## Implementation Phases

### Phase 1: Decimal Infrastructure (RUST-EXPERT)

**Risk**: HIGH (Decimal precision is foundational — every subsequent phase depends on this)
**Depends on**: SPEC-017 + SPEC-018 complete, `gravitea_rust` module loadable

Tasks:
1. Add `rust_decimal = "1.36"` and `rust_decimal_macros = "1.36"` to `Cargo.toml` `[dependencies]`
2. Create `rust/gravitea-core/src/decimal_utils.rs` with shared helpers:
   - `parse_decimal(s: &str) -> Result<Decimal, GraviteaError>` — wraps `Decimal::from_str()` with error mapping
   - `decimal_to_string(d: &Decimal) -> String` — normalizes trailing zeros for Python roundtrip
   - `dual_tolerance_eq(expected: &Decimal, actual: &Decimal, abs_tol: &Decimal, rel_tol: &Decimal) -> bool` — reusable tolerance comparison
3. Add `mod decimal_utils;` to `lib.rs` (private module, no pymodule_export)
4. Write ≥4 Rust-native tests: parse edge cases (very small `0.001`, very large `99999999999999.999`, negative, zero, invalid string), string roundtrip (Decimal→str→Decimal identity), tolerance comparison boundary cases
5. Run `cargo test` — all decimal tests pass
6. Document: `rust_decimal` supports 28 significant digits; GRAVITEA's `DECIMAL(17,3)` max is `99999999999999.999` (17 sig digits) — well within range

### Phase 2: Fiscal Functions (RUST-EXPERT)

**Risk**: HIGH (ARCA rejection on centavo-level mismatch)
**Depends on**: Phase 1 (decimal_utils.rs) complete

Tasks:
1. Create `rust/gravitea-core/src/compute.rs` with 5 `#[pyfunction]` exports
2. Implement `validate_importes(imp_total: &str, imp_neto: &str, imp_iva: &str, imp_trib: &str, imp_op_ex: &str, imp_tot_conc: &str) -> PyResult<()>`
   - Parse all 6 arguments via `parse_decimal()`
   - Compute expected = imp_neto + imp_op_ex + imp_iva + imp_trib + imp_tot_conc
   - Compare expected vs imp_total using `dual_tolerance_eq(expected, imp_total, 0.01, 0.0001)`
   - On mismatch: return `PyValueError` with same message format as Python
3. Implement `calculate_iva_breakdown(items_json: &str) -> PyResult<String>`
   - Input: JSON array of `{price: str, quantity: str, iva_rate: str}` objects
   - Group items by iva_rate; for each group: compute base_imp = sum(price × quantity), importe = base_imp × rate
   - Map rate → AlicIva ID: 0%→3, 2.5%→9, 5%→8, 10.5%→4, 21%→5, 27%→6; unknown→5
   - Output: JSON array of `{iva_id: int, base_imp: str, importe: str}` objects
4. Implement `validate_iva_breakdown(cbte_tipo: i32, aliciva_json: &str, imp_iva: &str, imp_neto: &str) -> PyResult<()>`
   - Parse AlicIva array from JSON; parse imp_iva and imp_neto as Decimals
   - Type A/B/M (cbte_tipo in [1,6,11,51,201,206,211]): AlicIva mandatory — error if empty
   - Type C (cbte_tipo in [11,211]): AlicIva prohibited — error if non-empty
   - Sum checks: sum(aliciva.importe) must equal imp_iva within tolerance; sum(aliciva.base_imp) must equal imp_neto within tolerance
5. Implement `aggregate_stock_levels(movements_json: &str) -> PyResult<String>`
   - Input: JSON array of `{product_id: str, branch_id: str, quantity: str, movement_type: str}` objects
   - **Release GIL**: `py.allow_threads(|| { ... })`
   - Group by (product_id, branch_id); sum quantities per type (in/out/adjustment)
   - Output: JSON object of `{product_id: {branch_id: {total: str, reserved: str, available: str}}}`
6. Implement `validate_cuit(cuit: &str) -> PyResult<()>`
   - Validate: exactly 11 digits, all numeric
   - Modulo-11: weights [5,4,3,2,7,6,5,4,3,2] on first 10 digits
   - check = 11 - (weighted_sum % 11); special cases: 11→0, 10→9
   - Compare computed check digit with cuit[10]; on mismatch → `PyValueError`
7. Add `mod compute;` and 5 `#[pymodule_export]` lines to `lib.rs`
8. Write ≥8 additional Rust-native tests: each function's happy path + error path + all 6 IVA rates in calculate_iva_breakdown + CUIT edge cases (check=10→9, check=11→0)
9. Run `cargo test` — all compute + decimal tests pass

### Phase 3: ARCA Validation (ARCA-EXPERT)

**Risk**: HIGH (fiscal compliance — ARCA rejection breaks invoice emission for all tenants)
**Depends on**: Phase 2 complete

Tasks:
1. Read `rust/gravitea-core/src/compute.rs` — review all fiscal logic
2. Query Qdrant: `backend/venv-wsl/bin/python scripts/qdrant/qdrant_search.py -q "AlicIva IVA rates IvaId" -c arca_api_specs -l 5`
3. Also read `skills/gravitea-invoice/SKILL.md` for ARCA patterns
4. **Review checklist**:
   - All 6 IVA rates mapped correctly to ARCA IDs (0%→3, 2.5%→9, 5%→8, 10.5%→4, 21%→5, 27%→6)
   - Tolerance values match ARCA acceptance rules (ABSOLUTE=0.01, RELATIVE=0.0001)
   - CUIT Modulo-11 weight sequence is [5,4,3,2,7,6,5,4,3,2]
   - validate_importes checks all 6 required ARCA amount fields
   - validate_iva_breakdown enforces correct comprobante type rules (A/B/M mandatory, C prohibited)
5. Sign off: APPROVED or CHANGES_REQUIRED

### Phase 4: Python Integration (QA)

**Risk**: MEDIUM (FFI boundary; backward compatibility of error types)
**Depends on**: Phase 3 sign-off

Tasks:
1. Modify `backend/apps/facturacion/validators.py` — add `_USE_RUST` dispatch for `validate_importes` and `validate_iva_breakdown`; Python fallback wraps Rust `RuntimeError` → `ValueError` for backward compat (per SPEC-018 pattern)
2. Modify `backend/apps/ventas/validators.py` — redirect `validate_cuit` to Rust with fallback
3. Modify `backend/apps/ventas/services/sale_service.py` — add `_USE_RUST` dispatch for `_create_alic_iva` → `calculate_iva_breakdown` (convert ORM items to JSON input for Rust)
4. Modify `backend/apps/inventario/services/stock_service.py` — add `aggregate_stock_levels` Rust dispatch with JSON serialization wrapper
5. Update `backend/gravitea_rust.pyi` with 5 function stubs
6. Create `backend/tests/rust_integration/test_compute_019.py`:
   - Known ARCA test vectors for validate_importes (valid + invalid amount sets, zero-value comprobante)
   - IVA breakdown computation for all 6 rates + mixed-rate orders + negative quantities (credit notes)
   - IVA breakdown validation (sum mismatch, comprobante type A/C rules)
   - Stock aggregation with 50+ product × 3 branch shaped data
   - CUIT validation: valid CUITs, invalid check digit, length errors, non-numeric, check=10 special case
   - Fallback tests: with `_USE_RUST = False`, all functions produce identical results
   - Benchmark each function: target ≥3× speedup
7. Run all tests via external runner

### Phase 5: Docker + Regression (LEAD)

**Risk**: LOW
**Depends on**: Phase 4 tests passing

Tasks:
1. Rebuild Docker image (`docker compose build`) — verify compute functions importable inside container
2. Run compute integration tests inside container
3. Run full test suite — target 0 new failures
4. Verify fallback: set `_USE_RUST = False` and confirm all tests pass
5. Update `specs/019-rust-fiscal-compute/quickstart.md` with build-time findings
6. Confirm: `cargo test` passes, Docker builds, benchmarks documented in research.md

---

## Research Topics (resolved in research.md)

| ID | Topic | Status |
|----|-------|--------|
| R-001 | `rust_decimal` precision limits vs Python Decimal for GRAVITEA field sizes | ✅ Resolved |
| R-002 | AlicIva ID mapping — complete ARCA rate table verification | ✅ Resolved |
| R-003 | CUIT Modulo-11 reference algorithm and edge cases | ✅ Resolved |
| R-004 | Stock aggregation input format — QuerySet→JSON serialization design | ✅ Resolved |
| R-005 | JSON serialization overhead vs individual `&str` parameters trade-off | ✅ Resolved |

## Crate Dependencies

| Crate | Version | New/Existing | Purpose |
|-------|---------|-------------|---------|
| `rust_decimal` | 1.36 | NEW | Arbitrary-precision Decimal arithmetic (28 sig digits) |
| `rust_decimal_macros` | 1.36 | NEW | Compile-time Decimal literal macros (e.g., `dec!(0.01)`) |
| `serde` | 1.0 | NEW | JSON serialization framework (features = ["derive"]) |
| `serde_json` | 1.0 | NEW | JSON parsing for compute function I/O |

> Note: `serde` + `serde_json` are added here but will also be used by SPEC-023, 024, 025. Adding them now avoids re-adding later.

## Testing Standards

| Category | Framework | Target |
|----------|-----------|--------|
| Rust-native | `cargo test` | ≥12 tests: decimal edge cases (4), validate_importes (2), calculate_iva_breakdown with all 6 rates (2), validate_iva_breakdown (2), aggregate_stock_levels (1), validate_cuit with edge cases (2) |
| Equivalence | `pytest` | Each Rust function produces identical results to Python equivalent for same inputs |
| ARCA vectors | `pytest` | Known valid/invalid invoice amount sets — verify accept/reject decisions match |
| Fallback | `pytest` | With Rust disabled, all functions produce identical results |
| Benchmark | `pytest-benchmark` | ≥3× speedup per function; `@pytest.mark.slow` |
| Docker | container exec | All 5 compute functions callable inside container |
| Regression | `pytest` | Full suite 0 new failures |

## Constraints

1. SPEC-017 + SPEC-018 complete — `gravitea_rust` module loadable with crypto functions
2. str↔Decimal boundary for ALL monetary values — **never float**
3. ARCA tolerance: ABSOLUTE=0.01, RELATIVE=0.0001 (used in validate_importes and validate_iva_breakdown)
4. GIL release ONLY for `aggregate_stock_levels` — other functions are sub-millisecond
5. CUIT validation consolidated from `ventas/validators.py:10` + `facturacion/serializers.py:51` → single Rust function
6. No Django model changes, no migrations
7. Python fallback mandatory — `_USE_RUST` dispatch pattern (per SPEC-018)
8. Error mapping: Rust `GraviteaError` → `PyRuntimeError`, but Python wrappers catch and re-raise as `ValueError` for backward compatibility with DRF serializer error handling
9. Whitespace/empty guards in Python wrappers only (per SPEC-018 pattern)
10. External test runner for all pytest: `scripts/run-tests-external.sh`
11. WIKI-EXPERT available on-demand for RAG queries — see `Docs/Temp-prompting/agents/agent-WIKI-EXPERT.md`

## Success Criteria

| # | Criterion | Target |
|---|-----------|--------|
| 1 | `cargo test` compute + decimal tests | ≥12 pass |
| 2 | Equivalence: Rust vs Python for all 5 functions | Identical outputs for 100+ test vectors (SC-001) |
| 3 | Benchmark: validate_importes + calculate_iva_breakdown | ≥3× speedup (SC-002) |
| 4 | Benchmark: aggregate_stock_levels (500 records) | ≥3× speedup + GIL released (SC-003) |
| 5 | CUIT consolidation | Single Rust function replaces 2 Python implementations (SC-004) |
| 6 | Decimal precision | No rounding drift for DECIMAL(17,3) values (SC-005) |
| 7 | Fallback mode | All tests pass with Rust disabled (SC-006) |
| 8 | Regression | Full suite 0 new failures (SC-007) |
| 9 | Docker | Image builds; compute functions callable inside container (SC-008) |
| 10 | Type stubs | `gravitea_rust.pyi` updated with 5 new signatures |
