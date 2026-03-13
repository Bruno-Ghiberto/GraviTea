# Speckit Context: Fiscal Compute Engine (SPEC-019)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: HIGH | **Wave**: 3 (parallel with SPEC-022)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete
> **Follows patterns from**: SPEC-018 (Crypto Acceleration) — fallback dispatch, `_internal` test functions, error type mapping, backward-compat wrappers

---

## Mission Statement

Implement Rust versions of ARCA fiscal calculations, IVA breakdown computation, stock aggregation, and CUIT Modulo-11 validation. This bundles the Integration Guide Module 2 with OPP-006 (CUIT validation), consolidating duplicated fiscal math from multiple Django apps into a single, precise Rust module.

## Why This Matters Now

- **Decimal boundary crossing** is the defining technical challenge for all subsequent Rust specs that handle money
- **validate_importes** runs on every invoice emission — ARCA rejects mismatches at the centavo level
- **CUIT validation** is duplicated in 2+ files — Rust consolidates it into one authoritative function
- **Stock aggregation** with GIL release lets other Django threads serve requests during batch computation

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Decimal transport | `str` across FFI boundary | Same pattern as PostgreSQL drivers: Python `Decimal` → `str()` → Rust `rust_decimal` → `.to_string()` → Python `Decimal(result)` |
| Crate for decimals | `rust_decimal 1.36` | 28 significant digits, sufficient for DECIMAL(17,3) |
| IVA rate mapping | Compiled `match` expression | Faster than Python dict lookup; all 6 ARCA rates (0, 2.5, 5, 10.5, 21, 27) |
| Tolerance | ABSOLUTE=0.01, RELATIVE=0.0001 | Matches ARCA acceptance rules |
| GIL handling | Released for `aggregate_stock_levels` only | Batch operation benefits; others are sub-ms |
| CUIT location | In this module (fiscal compute) | Consolidates from ventas/validators.py + facturacion/serializers.py |
| Default IVA | ID=5 (21%) for unknown rates | Mirrors Python logic |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| `validate_importes` | `backend/apps/facturacion/validators.py:58` — ARCA master amount equation (6 Decimal args) |
| `validate_iva_breakdown` | `backend/apps/facturacion/validators.py:89` — AlicIva entries vs header amounts (FR-008) |
| `calculate_iva_breakdown` | NEW — no single Python function exists. `sale_service.py:480 _calculate_amounts()` assembles pre-computed totals but does NOT compute per-rate IVA. The new Rust function computes AlicIva breakdown from line items + rates. |
| `aggregate_stock_levels` | NEW batch function. `StockService.get_product_stock_summary` (`inventario/services/stock_service.py:765`) is per-product; the new Rust function aggregates across multiple products in one pass. |
| `validate_cuit` | Duplicated: `ventas/validators.py:10` (model-level) + `facturacion/serializers.py:51` (`_validate_cuit`, serializer-level) |
| **Call frequency** | Every invoice emission (validate_importes, validate_iva_breakdown), every sale (IVA calc), every stock view (aggregate) |

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs              # Add compute submodule + re-exports
├── compute.rs          # NEW — fiscal math + stock aggregation
└── decimal_utils.rs    # NEW — shared Decimal↔str conversion helpers
```

### Functions to Implement

| Function | Replaces / Creates | Speedup | GIL Released |
|----------|-------------------|---------|-------------|
| `validate_importes` | Replaces `facturacion/validators.py:58` | ~5x | No |
| `validate_iva_breakdown` | Replaces `facturacion/validators.py:89` | ~3x | No |
| `calculate_iva_breakdown` | NEW — computes per-rate AlicIva from line items | ~3x | No |
| `aggregate_stock_levels` | NEW batch — replaces per-product ORM calls | ~4x | **Yes** |
| `validate_cuit` | Consolidates 2 files (DRY) | 10-20x (negligible abs.) | No |

### Cargo.toml Additions

```toml
rust_decimal = "1.36"
rust_decimal_macros = "1.36"
```

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| 6 × ~10 char strings (Decimal args) | ~60 bytes | ~0.6μs | ~20μs | ~3μs | **+16.4μs** |

## Critical Caveats

1. **str() conversion overhead**: Every `Decimal` argument crosses as string. 6 args = 6 string allocations. Still net-positive.
2. **rust_decimal precision**: 28 significant digits vs Python unlimited. GRAVITEA uses DECIMAL(17,3) — well within range. Document this limit.
3. **IVA rate match**: Must handle ALL known ARCA rates (0, 2.5, 5, 10.5, 21, 27). Default to IVA_21 (id=5).
4. **Stock input format**: Django QuerySet `.values()` returns Decimal objects. Python wrapper must convert to str. UUID fields as hex strings.
5. **AlicIva ID mapping**: Rate-to-ARCA-ID (`21% → 5`, `10.5% → 4`, etc.) compiled into Rust match.
6. **SPEC-018 error mapping lesson**: Rust `GraviteaError` maps to `PyRuntimeError` via PyO3, but existing callers expect `ValueError`. Python wrappers MUST catch `RuntimeError` and re-raise as `ValueError` for backward compatibility. See `utils.py` decrypt_value wrapper.
7. **SPEC-018 testing pattern**: Use `_internal` suffix functions (e.g., `validate_importes_internal`) returning `Result<T, GraviteaError>` for Rust-side `cargo test`. PyO3 `PyResult` requires a Python interpreter.
8. **Whitespace/empty guards**: Python wrappers must guard empty/whitespace-only inputs BEFORE dispatching to Rust, matching existing Python behavior (see SPEC-018 `compute_blind_index` fix).

## Success Criteria

1. `cargo test` passes with ≥10 compute-specific tests (each function + edge cases)
2. Equivalence tests pass against known ARCA test vectors
3. `validate_cuit` consolidated from 2 files into single Rust function
4. `aggregate_stock_levels` releases GIL during computation
5. Decimal precision matches Python for all GRAVITEA field sizes
6. Fallback works: Python implementations still functional without Rust
7. Docker image builds with compute functions available
8. Full test suite passes with 0 regressions

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | Spec details, FFI analysis | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §5 |
| Integration Guide | Module 2 code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §6 |
| ARCA validators | `validate_importes` + `validate_iva_breakdown` | `backend/apps/facturacion/validators.py` |
| Sale service | `_calculate_amounts` (amount assembly) | `backend/apps/ventas/services/sale_service.py:480` |
| CUIT validator | Modulo-11 algorithm | `backend/apps/ventas/validators.py:10` |
| CUIT serializer | Serializer-level CUIT check | `backend/apps/facturacion/serializers.py:51` (`_validate_cuit`) |
| StockService | Per-product stock summary | `backend/apps/inventario/services/stock_service.py:765` |
| Invoice skill | ARCA fiscal patterns | `skills/gravitea-invoice/SKILL.md` |
| SPEC-018 impl | Rust/PyO3 patterns to follow | `rust/gravitea-core/src/crypto.rs` + `backend/apps/core/encryption/utils.py` |
