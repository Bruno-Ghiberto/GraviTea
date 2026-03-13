# Quickstart: Fiscal Compute Engine (SPEC-019)

**Branch**: `019-rust-fiscal-compute` | **Date**: 2026-02-26

---

## Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Rust (rustup) | 1.93.1+ | `rustc --version` |
| Maturin | 1.12.4+ | `maturin --version` |
| Python venv (WSL2) | 3.14.3 | `backend/venv-wsl/bin/python --version` |
| Docker | Any | `docker --version` |

> SPEC-017 + SPEC-018 must be complete. Verify: `backend/venv-wsl/bin/python -c "import gravitea_rust; print(gravitea_rust.hello()); gravitea_rust.encrypt_value('test', b'0'*32)"` should succeed without error.

---

## 1. Add Crate Dependencies

```bash
# From repo root (WSL2)
# Edit rust/gravitea-core/Cargo.toml — add to [dependencies]:
# rust_decimal = "1.36"
# rust_decimal_macros = "1.36"
# serde = { version = "1.0", features = ["derive"] }
# serde_json = "1.0"
```

---

## 2. Build the Rust Extension

```bash
# From repo root (WSL2)
cd rust/gravitea-core

# Run Rust tests first
cargo test

# Build and install into WSL venv
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
maturin develop -m rust/gravitea-core/Cargo.toml \
  --interpreter backend/venv-wsl/bin/python
```

**Expected output**:
```
🔗 Found pyo3 bindings with abi3 support for Python ≥ 3.8
📦 Built wheel for abi3 Python ≥ 3.8: [wheel path]
✅ Installed gravitea_rust-0.x.x
```

---

## 3. Verify the Build

```bash
backend/venv-wsl/bin/python -c "
import gravitea_rust, json

# Test validate_importes (valid amounts)
gravitea_rust.validate_importes('121.00', '100.00', '21.00', '0.00', '0.00', '0.00')
print('validate_importes OK')

# Test calculate_iva_breakdown
items = json.dumps([
    {'price': '100.00', 'quantity': '1', 'iva_rate': '21.00'}
])
result = json.loads(gravitea_rust.calculate_iva_breakdown(items))
assert result[0]['iva_id'] == 5  # IVA 21%
print(f'calculate_iva_breakdown OK: {result}')

# Test validate_cuit (known valid CUIT)
gravitea_rust.validate_cuit('27000000006')
print('validate_cuit OK')

# Test aggregate_stock_levels
movements = json.dumps([
    {'product_id': 'p1', 'branch_id': 'b1', 'quantity': '10.000', 'movement_type': 'IN'},
    {'product_id': 'p1', 'branch_id': 'b1', 'quantity': '3.000', 'movement_type': 'OUT'},
])
stock = json.loads(gravitea_rust.aggregate_stock_levels(movements))
print(f'aggregate_stock_levels OK: {stock}')

print('All 019 compute functions verified!')
"
```

---

## 4. Run Cargo Tests

```bash
cd rust/gravitea-core
cargo test -- --nocapture 2>&1 | tail -40
```

**Actual result**: `test result: ok. 50 passed; 0 failed; 0 ignored` (4 decimal_utils + 29 compute + 17 crypto).

Target: ≥12 new tests (4 decimal + 8 compute) → **Achieved: 33 new tests**.

---

## 5. Run Integration Tests

```bash
# Compute-specific tests (requires postgres-test on port 5433)
docker compose --profile test up -d postgres-test redis-test
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres \
  venv-wsl/bin/python -m pytest tests/rust_integration/test_compute_019.py \
  --tb=short -q --no-header --no-cov
```

**Actual result**: `65 passed in 6.11s`.

---

## 6. Test the Fallback Path

```bash
# Temporarily disable the Rust path:
# In backend/apps/facturacion/validators.py, set _USE_RUST = False
# In backend/apps/ventas/validators.py, set _USE_RUST = False
# In backend/apps/ventas/services/sale_service.py, set _USE_RUST = False
# In backend/apps/inventario/services/stock_service.py, set _USE_RUST = False

backend/venv-wsl/bin/python -m pytest backend/tests/ \
  --tb=short -q --no-header 2>&1 | tail -20

# All tests must still pass with Rust disabled
```

---

## 7. Docker Build Verification

```bash
# Rebuild image (includes Maturin build step)
docker compose build web

# Test compute availability inside container
docker compose run --rm web python -c "
import gravitea_rust, json
gravitea_rust.validate_importes('121.00', '100.00', '21.00', '0.00', '0.00', '0.00')
gravitea_rust.validate_cuit('27000000006')
items = json.dumps([{'price': '100.00', 'quantity': '1', 'iva_rate': '21.00'}])
result = gravitea_rust.calculate_iva_breakdown(items)
print(f'Docker compute OK: {result}')
"
```

---

## 8. Full Regression

```bash
scripts/run-tests-external.sh \
  "backend/venv-wsl/bin/python -m pytest backend/tests/ --tb=short -q --no-header"
# Then read: .claude-test-results.txt
```

Target: 0 new failures vs SPEC-018 baseline.

## 9. Benchmark Results (WSL2)

| Function | Iterations | Rust | Python | Speedup |
|---|---|---|---|---|
| `validate_importes` | 2000x | 0.001s | 0.002s | **2.7x** |
| `calculate_iva_breakdown` | 500x (20 items) | 0.004s | 0.016s | **4.4x** |
| `validate_cuit` | 5000x | 0.001s | 0.003s | **3.1x** |
| `aggregate_stock_levels` | 100x (500 mvts) | 0.021s | 0.046s | **2.1x** |

Note: These scalar validations are sub-millisecond per call. The speedup becomes more significant with larger payloads (IVA breakdown, stock aggregation). The JSON serialization boundary (str↔Decimal) adds overhead that wouldn't exist in a pure-Rust pipeline.

---

## File Reference

| File | Change |
|------|--------|
| `rust/gravitea-core/Cargo.toml` | +4 crate deps (rust_decimal, rust_decimal_macros, serde, serde_json) |
| `rust/gravitea-core/src/lib.rs` | +2 `mod` lines (compute, decimal_utils) + 5 `#[pymodule_export]` |
| `rust/gravitea-core/src/decimal_utils.rs` | NEW: str↔Decimal helpers (parse, format, tolerance) |
| `rust/gravitea-core/src/compute.rs` | NEW: 5 pyfunction exports |
| `backend/apps/facturacion/validators.py` | +`_USE_RUST` dispatch for validate_importes + validate_iva_breakdown |
| `backend/apps/ventas/validators.py` | +`_USE_RUST` dispatch for validate_cuit |
| `backend/apps/ventas/services/sale_service.py` | +`_USE_RUST` dispatch for _create_alic_iva |
| `backend/apps/inventario/services/stock_service.py` | +`_USE_RUST` dispatch for aggregate_stock_levels |
| `backend/gravitea_rust.pyi` | +5 function stubs |
| `backend/tests/rust_integration/test_compute_019.py` | NEW: all fiscal compute tests |

---

## Troubleshooting

**`ImportError: No module named 'gravitea_rust'`**
→ Run `maturin develop` (step 2 above). Fallback activates automatically if import fails.

**`ValueError: Invalid decimal string`**
→ All monetary values must be passed as strings (e.g., `"121.00"`, not `121.00`). The Rust functions parse strings to `rust_decimal::Decimal` internally.

**`ValueError: Amount equation does not balance`**
→ Check that `imp_total == imp_neto + imp_op_ex + imp_iva + imp_trib + imp_tot_conc` within tolerance (0.01 absolute or 0.01% relative). Common cause: rounding differences in intermediate calculations.

**`ValueError: CUIT check digit is invalid`**
→ Verify the CUIT passes Modulo-11. Weight sequence: [5,4,3,2,7,6,5,4,3,2]. Special cases: remainder=0→digit=0, remainder=1→digit=9.

**`serde_json` parse error on compute functions**
→ Ensure JSON input matches expected format. For `calculate_iva_breakdown`: `[{"price":"str","quantity":"str","iva_rate":"str"}]`. For `aggregate_stock_levels`: `[{"product_id":"str","branch_id":"str","quantity":"str","movement_type":"IN|OUT|..."}]`.

**GIL not released / no concurrency benefit**
→ Only `aggregate_stock_levels` releases the GIL via `py.detach()` (PyO3 0.28 API). Other functions are sub-millisecond and don't benefit from GIL release.

**Tests fail with `TenantContextError` / `near "SET": syntax error`**
→ The SPEC-019 tests require PostgreSQL (not SQLite). Use `DJANGO_SETTINGS_MODULE=gravitea.settings.test_postgres` and ensure `docker compose --profile test up -d postgres-test redis-test` is running.
