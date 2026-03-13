# Speckit Context: Data Export Pipeline (SPEC-020)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: MEDIUM | **Wave**: 4 (parallel with SPEC-023)
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete

---

## Mission Statement

Implement Rust CSV and Excel (.xlsx) generation engine for the `reportes` app's `ExportJob` processing. This spec creates the Rust export engine; the Django views/tasks connecting it to `ExportJob` are part of the `reportes` app spec, not this Rust spec.

## Why This Matters Now

- **10,000 rows under 2 seconds** target (vs Python `csv` module at ~4-8s)
- **GIL released** during generation — other Django threads continue serving requests during large exports
- **Streaming write**: Memory proportional to largest row, not total dataset
- **Excel compatibility**: UTF-8 BOM for Spanish characters (á, é, ñ, ü)

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| CSV crate | `csv 1` (latest 1.x) | Standard Rust CSV writer, streaming capable |
| XLSX crate | `rust_xlsxwriter 0.92` | Feature-rich, maintained, no external deps |
| GIL handling | Released for both functions | Large batch operations benefit from parallelism |
| Input format | `Vec<HashMap<String, String>>` | Universal row format; Python converts all values to str |
| Column ordering | Determined by `headers` list, not dict key order | Predictable output |
| UTF-8 BOM | Prepended to CSV output | Excel opens CSV with correct Spanish encoding |
| Numeric detection | Auto-detect via `parse::<f64>()` | XLSX numbers use `General` format; currency columns use `#,##0.00` |
| PDF | EXCLUDED — stays in Python | PDF depends on HTML templates (Django domain) |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| `reportes` app | Skeleton exists — `ReportService` models but no generation logic |
| Export format | No Rust export capability; Python would use `csv` stdlib + `openpyxl` |
| Call frequency | Per export job (user-initiated, batch reports) |

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs          # Add export submodule + re-exports
└── export.rs       # NEW — generate_csv, generate_xlsx
```

### Functions to Implement

| Function | Signature | Output | GIL Released | Target |
|----------|-----------|--------|-------------|--------|
| `generate_csv` | `(rows: Vec<HashMap<String, String>>, headers: Vec<String>) -> PyResult<Vec<u8>>` | UTF-8 bytes with BOM | Yes | 10K rows < 1s |
| `generate_xlsx` | `(rows: Vec<HashMap<String, String>>, headers: Vec<String>, column_widths: Option<HashMap<String, f64>>) -> PyResult<Vec<u8>>` | .xlsx file bytes | Yes | 10K rows < 2s |

**Parameter details:**
- `rows`: Each row is a `HashMap` keyed by column name. All values are strings; Python converts Decimals/dates/booleans to `str` before calling Rust.
- `headers`: Ordered list of column names determining output column order. Empty headers → empty file (BOM only for CSV, empty workbook for XLSX).
- `column_widths` (XLSX only): Optional per-column width overrides keyed by column name. Columns not in the map get auto-width.

**XLSX numeric detection:** Values that pass `parse::<f64>()` are written as Excel numbers with `General` format. The Python caller can optionally pass a `number_format` hint in the future, but for now `General` is the default (Excel auto-formats based on cell content). Currency columns typically display correctly with `General` since Excel infers 2-decimal formatting from the data.

### Cargo.toml Additions

```toml
csv = "1"
rust_xlsxwriter = "0.92"
```

## FFI Boundary Analysis

| Input | Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|------|-------------|-------------|-----------|----------|
| 10K rows × 10 cols | ~100K entries | ~50-100ms | ~4-8s | ~0.5-1s | **+3-7s** |

## Critical Caveats

1. **Large dataset serialization**: 10K rows × 10 columns = 100K dict entries crossing FFI. The `Vec<HashMap<String, String>>` conversion cost is ~50-100ms. This is the bottleneck, not the writing itself.
2. **`reportes` app is skeleton**: This spec creates the engine only. Django views/tasks connecting to `ExportJob` are separate.
3. **Column widths**: Python passes `HashMap<String, f64>` for per-column width settings (XLSX only).
4. **Column ordering**: CSV/XLSX column order determined by `headers` list, not dict key order.

## Success Criteria

1. `cargo test` passes with ≥6 export-specific tests (CSV roundtrip, XLSX roundtrip, BOM presence, empty data, large dataset, numeric detection)
2. Generated CSV opens correctly in Excel with Spanish characters
3. Generated XLSX opens correctly in Excel with number formatting
4. 10K rows × 10 columns generates in < 2 seconds (both formats)
5. GIL released during generation (verify with threading test)
6. Fallback pattern works without Rust extension
7. Docker image builds with export functions available
8. Full test suite passes with 0 regressions

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | Spec details, FFI analysis | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §6 |
| Integration Guide | Module 3 code examples | `Docs/Brainstorming/rust-pyo3-integration-guide.md` §7 |
| Reportes app | Skeleton models | `backend/apps/reportes/` |
