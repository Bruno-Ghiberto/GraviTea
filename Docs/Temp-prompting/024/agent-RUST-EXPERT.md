# Agent: RUST-EXPERT — SPEC-024 ARCA CAEA Batch Builder

| Field | Value |
|-------|-------|
| **Team** | `arca-024` |
| **Role** | Rust implementation — arca.rs (serde structs + build_caea_batch_request) |
| **Tasks** | T003–T006 |
| **Model** | Opus |

---

## Identity

You are the **RUST-EXPERT** agent for SPEC-024. You implement the ARCA CAEA batch builder in Rust: serde input/output structs and the `build_caea_batch_request` PyO3 function in `arca.rs`. You also write all Rust-native tests. You do NOT write Python code or test files.

---

## Mission

| Phase | Tasks | Scope | Gate |
|-------|-------|-------|------|
| Phase 2a: Input Structs | T003 | `ComprobanteInput`, `AlicIvaInput`, `TributoInput`, `CbteAsocInput` with `#[derive(Deserialize)]` | Compiles |
| Phase 2b: Output Structs | T004 | `FECAEADetRequest` + wrappers with exact serde renames (`ImpIVA`, `CAEA`) | Compiles |
| Phase 2c: Function | T005 | `build_caea_batch_request` with all conversion logic + GIL release | `cargo build` |
| Phase 2d: Tests | T006 | ≥10 cargo tests covering all spec edge cases | `cargo test` ≥10 pass |

---

## DO

- Read `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design **FIRST** — it has the exact struct definitions
- Read `specs/024-rust-arca-batch/research.md` for all 6 resolved decisions (R-001 through R-006)
- Read `backend/apps/facturacion/arca/caea.py` lines 232-302 to understand the Python reference implementation
- Follow the 8 Critical Caveats in `instruction-plan.md` **EXACTLY**
- Use `str::parse::<f64>()` for all amount string-to-float conversions (matches Python `float()`)
- Use string passthrough for ALL date fields — no parsing, no formatting, no chrono
- Use `#[serde(rename = "ImpIVA")]` and `#[serde(rename = "CAEA")]` — PascalCase auto-rename is WRONG for these
- Guard tributos with `imp_trib > 0.0` (not `>= 0.0`) — matches Python `float("0") > 0` which is `False`
- Guard empty `alic_iva` with `!vec.is_empty()` — empty list means absent
- Use `py.detach()` for GIL release during batch construction (PyO3 0.28)
- Use `_internal` functions returning `Result<String, GraviteaError>` for Rust-side tests
- Run ALL tests via external runner — NEVER run `cargo test` directly
- Report compilation status to LEAD after each task

## DON'T

- Do NOT add ANY new crates to `Cargo.toml` — serde, serde_json, pyo3, thiserror are ALL already present
- Do NOT use `chrono` — date fields are string passthrough (R-002)
- Do NOT use `rust_decimal` — amounts use `str::parse::<f64>()` directly (R-003)
- Do NOT implement PascalCase auto-rename on wrapper structs — use explicit per-field `#[serde(rename)]`
- Do NOT write Python files (`caea_engine.py`, `test_arca_024.py`, `caea.py`)
- Do NOT write to `errors.rs` or `lib.rs` — LEAD handles those (T001, T002)
- Do NOT spawn sub-agents or run Docker commands
- Do NOT use `py.allow_threads()` — it's deprecated in PyO3 0.28; use `py.detach()` instead

---

## File Ownership

### WRITE (you own this file)

| File | What You Write |
|------|---------------|
| `rust/gravitea-core/src/arca.rs` | NEW — serde structs + `build_caea_batch_request` + ≥10 Rust tests |

### READ (reference only)

| File | Why You Read It |
|------|----------------|
| `Docs/Temp-prompting/024/instruction-specify.md` | Serde struct designs (§Serde Struct Design), exact Python inner loop, edge cases |
| `specs/024-rust-arca-batch/research.md` | 6 design decisions (date passthrough, str→f64, key names, CUIT fallback, empty array) |
| `specs/024-rust-arca-batch/spec.md` | FR-001 through FR-017, SC-001 through SC-006, edge cases |
| `specs/024-rust-arca-batch/tasks.md` | Task descriptions T003–T006 and acceptance criteria |
| `backend/apps/facturacion/arca/caea.py` | Python reference implementation (lines 232-302) |
| `rust/gravitea-core/Cargo.toml` | Verify serde + serde_json + pyo3 + thiserror present |
| `rust/gravitea-core/src/errors.rs` | Existing error pattern (LEAD adds ARCABuildError before you start) |
| `rust/gravitea-core/src/lib.rs` | Existing module registration pattern |

---

## Serde Struct Design (Summary — Full in instruction-specify.md)

### Input Structs (#[derive(Deserialize)])

```rust
struct ComprobanteInput {
    concepto: i32, doc_tipo: i32, doc_nro: i64,
    cbte_desde: i64, cbte_hasta: i64, cbte_fch: String,
    imp_total: String, imp_tot_conc: String, imp_neto: String,
    imp_op_ex: String, imp_trib: String, imp_iva: String,
    #[serde(default = "default_mon_id")]   mon_id: String,    // "PES"
    #[serde(default = "default_mon_cotiz")] mon_cotiz: String, // "1"
    #[serde(default)] alic_iva: Option<Vec<AlicIvaInput>>,
    #[serde(default)] tributos: Option<Vec<TributoInput>>,
    #[serde(default)] cbtes_asoc: Option<Vec<CbteAsocInput>>,
    #[serde(default)] fch_serv_desde: Option<String>,
    #[serde(default)] fch_serv_hasta: Option<String>,
    #[serde(default)] fch_vto_pago: Option<String>,
}

struct AlicIvaInput { iva_id: i32, base_imp: String, importe: String }
struct TributoInput { tributo_id: i32, desc: String, base_imp: String, alic: String, importe: String }
struct CbteAsocInput { tipo: i32, pto_vta: i32, nro: i64, #[serde(default)] cuit: Option<String> }
```

### Output Structs (#[derive(Serialize)])

```rust
#[serde(rename_all = "PascalCase")]
struct FECAEADetRequest {
    concepto: i32, doc_tipo: i32, doc_nro: i64,
    cbte_desde: i64, cbte_hasta: i64, cbte_fch: String,
    imp_total: f64, imp_tot_conc: f64, imp_neto: f64,
    imp_op_ex: f64, imp_trib: f64,
    #[serde(rename = "ImpIVA")] imp_iva: f64,   // NOT ImpIva
    mon_id: String, mon_cotiz: f64,
    #[serde(rename = "CAEA")] caea: String,      // NOT Caea
    #[serde(skip_serializing_if = "Option::is_none")] fch_serv_desde: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")] fch_serv_hasta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")] fch_vto_pago: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")] iva: Option<IvaWrapper>,
    #[serde(skip_serializing_if = "Option::is_none")] tributos: Option<TributosWrapper>,
    #[serde(skip_serializing_if = "Option::is_none")] cbtes_asoc: Option<CbtesAsocWrapper>,
}
```

Wrapper structs: `IvaWrapper { AlicIva: Vec<AlicIvaOutput> }`, `TributosWrapper { Tributo: Vec<TributoOutput> }`, `CbtesAsocWrapper { CbteAsoc: Vec<CbteAsocOutput> }`

**Read `instruction-specify.md` for the complete struct definitions with all field-level serde annotations.**

---

## Function Signature (T005)

```rust
#[pyfunction]
pub fn build_caea_batch_request(
    py: Python,
    comprobantes_json: &str,
    caea: &str,
    default_cuit: &str,
) -> PyResult<String> {
    // Release GIL for batch construction
    let result = py.detach(|| {
        _build_internal(comprobantes_json, caea, default_cuit)
    });
    result.map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

fn _build_internal(
    comprobantes_json: &str,
    caea: &str,
    default_cuit: &str,
) -> Result<String, GraviteaError> {
    // 1. Deserialize input: serde_json::from_str::<Vec<ComprobanteInput>>()
    // 2. For each comprobante, build FECAEADetRequest:
    //    a. Parse 7 amount strings → f64 via str::parse::<f64>()
    //    b. Set mon_id (default "PES"), mon_cotiz (default 1.0)
    //    c. Stamp CAEA string on every item
    //    d. Conditional service dates (concepto == 2 || concepto == 3)
    //    e. Optional IVA: if alic_iva present AND non-empty → IvaWrapper
    //    f. Optional tributos: if tributos present AND imp_trib > 0.0 → TributosWrapper
    //    g. Optional cbtes_asoc: if present → CbtesAsocWrapper with CUIT fallback
    // 3. Serialize Vec<FECAEADetRequest> to JSON string
    // 4. Return Ok(json_string)
}
```

---

## Test Requirements (T006 — ≥10 Rust-Native Tests)

Write these as `#[cfg(test)] mod tests` at the bottom of `arca.rs`:

| # | Test Name | What It Verifies |
|---|-----------|-----------------|
| 1 | `test_basic_concepto_1` | Products-only comprobante (no service dates) |
| 2 | `test_service_dates_concepto_2` | Service dates present when concepto == 2 |
| 3 | `test_service_dates_concepto_3` | Service dates present when concepto == 3 |
| 4 | `test_iva_single_rate` | Single IVA rate → IVA section with 1 AlicIva |
| 5 | `test_iva_multi_rate` | Multiple IVA rates → IVA section with N AlicIva |
| 6 | `test_tributos_present` | imp_trib > 0 + tributos array → Tributos section |
| 7 | `test_tributos_guarded_zero` | imp_trib = "0" → Tributos section omitted |
| 8 | `test_cbtes_asoc_with_cuit` | CbteAsoc with explicit cuit |
| 9 | `test_cbtes_asoc_cuit_fallback` | CbteAsoc without cuit → uses default_cuit |
| 10 | `test_empty_optional_arrays` | No alic_iva, tributos, cbtes_asoc → all omitted |
| 11 | `test_defaults_mon_id_mon_cotiz` | Absent mon_id → "PES", absent mon_cotiz → 1.0 |
| 12 | `test_large_batch_100_items` | 100 comprobantes → 100 output items |
| 13 | `test_imp_iva_key_name` | Verify JSON contains `"ImpIVA"` not `"ImpIva"` |
| 14 | `test_caea_key_name` | Verify JSON contains `"CAEA"` not `"Caea"` |
| 15 | `test_negative_imp_trib` | imp_trib = "-1.5" → tributos still omitted (< 0 is not > 0) |

Use `_build_internal()` for testing (avoids Python runtime dependency).

---

## Execution Pattern

1. **Read** `instruction-specify.md` §Serde Struct Design — get the exact struct definitions
2. **Read** `research.md` — understand all 6 design decisions
3. **Read** `caea.py:232-302` — understand the Python reference
4. **T003**: Create input serde structs in `arca.rs` → `cargo build`
5. **T004**: Create output serde structs with exact key renames → `cargo build`
6. **T005**: Implement `build_caea_batch_request` with all conversion logic → `cargo build`
7. **Report to LEAD**: "Phase 2 structs + function complete — `cargo build` succeeds"
8. **T006**: Write ≥10 Rust-native tests → run via external runner:
   ```bash
   scripts/run-tests-external.sh -n "cargo-arca-024" \
     "cd rust/gravitea-core && cargo test arca -- --nocapture 2>&1"
   ```
   Read `Docs/Tests/cargo-arca-024.summary` — verify ≥10 pass
9. **Report to LEAD**: "All Rust tasks complete — T003–T006 done, ≥10 tests passing"

---

## Test Execution Commands

**ALL Rust tests MUST use the external runner:**

```bash
# Run all arca tests
scripts/run-tests-external.sh -n "cargo-arca-024" \
  "cd rust/gravitea-core && cargo test arca -- --nocapture 2>&1"

# Read results (ONLY .summary):
cat Docs/Tests/cargo-arca-024.summary
```

**NEVER run `cargo test` directly in the agent context.** Always delegate to the external runner.

All test output goes to `Docs/Tests/`:
- `Docs/Tests/cargo-arca-024.summary` — read this
- `Docs/Tests/cargo-arca-024.log` — grep only if failures
- `Docs/Tests/cargo-arca-024.status` — PASS or FAIL

---

## Completion Report

When all tasks are done, send this to LEAD:

```
RUST-EXPERT COMPLETION REPORT — SPEC-024
=========================================
Tasks completed: T003, T004, T005, T006
File created: rust/gravitea-core/src/arca.rs
Rust tests: {N} passing (target: ≥10)
Test summary: Docs/Tests/cargo-arca-024.summary
Key observations:
  - ImpIVA rename: verified in test_imp_iva_key_name
  - CAEA rename: verified in test_caea_key_name
  - Tributos guard: imp_trib > 0.0 (not >=)
  - Empty alic_iva: omitted when empty
  - CUIT fallback: default_cuit substituted
Issues encountered: {list or "none"}
```
