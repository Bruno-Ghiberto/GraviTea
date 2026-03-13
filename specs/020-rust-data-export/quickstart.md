# Quick Start: Rust Data Export Pipeline (SPEC-020)

**Branch**: `020-rust-data-export`

## Prerequisites

- Rust 1.93.1+ with `maturin` 1.12.4+ installed
- Python 3.14 venv at `backend/venv-wsl/`
- SPEC-017 (Rust toolchain bootstrap) complete and committed

## Build

```bash
# From repo root — build Rust extension into WSL venv
VIRTUAL_ENV=$(pwd)/backend/venv-wsl backend/venv-wsl/bin/maturin develop \
  --manifest-path rust/gravitea-core/Cargo.toml --release
```

## Run Rust Tests

```bash
cd rust/gravitea-core && cargo test -- --nocapture
# Expected: 60 tests passing (10 export-specific)
```

## Run Python Tests

```bash
# Export tests (authoritative location)
cd backend && venv-wsl/bin/python -m pytest tests/rust_integration/test_export_020.py \
  -p no:django --tb=short -q
# Expected: 17 passed in ~5s
```

## Usage (Python)

```python
from apps.reportes.export_engine import generate_csv, generate_xlsx

rows = [
    {"Producto": "Yerba Mate", "Precio": "1250.50", "Cantidad": "10"},
    {"Producto": "Dulce de Leche", "Precio": "890.00", "Cantidad": "5"},
]
headers = ["Producto", "Precio", "Cantidad"]

# CSV with UTF-8 BOM
csv_bytes = generate_csv(rows, headers)

# XLSX with custom column widths
xlsx_bytes = generate_xlsx(rows, headers, column_widths={"Producto": 30.0, "Precio": 12.0})

# Write to file
with open("export.csv", "wb") as f:
    f.write(csv_bytes)
with open("export.xlsx", "wb") as f:
    f.write(xlsx_bytes)
```

## File Layout

```
rust/gravitea-core/src/export.rs          # Rust export engine (315 lines)
backend/apps/reportes/export_engine.py    # Python wrapper with fallback
backend/tests/rust_integration/test_export_020.py  # Integration tests (authoritative)
backend/tests/reportes/test_export_020.py # Mirror copy
backend/gravitea_rust.pyi                 # Type stubs (updated)
```

## Key Decisions

| Decision | Choice |
|----------|--------|
| CSV crate | `csv 1` (1.4.0 resolved) |
| XLSX crate | `rust_xlsxwriter 0.92` (0.92.4 resolved) |
| Input format | `Vec<HashMap<String, String>>` (native PyO3 extraction) |
| GIL handling | Released during generation via `py.detach()` (PyO3 0.28 API) |
| Numeric detection | `parse::<f64>()` — success writes number, failure writes text |
| UTF-8 BOM | Always prepended to CSV output |
| Column widths | `autofit()` + explicit overrides, character-width units |
| Python fallback | `csv` stdlib + `openpyxl` when Rust extension unavailable |

## Implementation Results (2026-02-26)

| Metric | Result |
|--------|--------|
| Cargo tests | 60 total (10 export-specific) |
| Pytest tests | 17 total (6 CSV + 6 XLSX + 3 performance + 2 fallback) |
| Docker import | PASS — both functions importable in container |
| Regression | 0 new failures from SPEC-020 |
| 10K CSV benchmark | < 2s PASS |
| 10K XLSX benchmark | < 2s PASS |
| GIL release | PASS — concurrent threading confirmed |
| Fallback CSV | PASS — BOM present, content valid |
| Fallback XLSX | PASS — PK signature, non-empty |
| Wheel size | ~188 KB (incremental from SPEC-018/019) |
| Build time | ~16s release build |

## Agents Used

| Agent | Model | Tasks | Outcome |
|-------|-------|-------|---------|
| LEAD | Opus 4.6 | T001-T003, T023-T025 | Setup + polish |
| RUST-EXPERT | Opus 4.6 | T004-T007, T011-T014 | 10 Rust tests, TDD |
| BACKEND-CODER | Sonnet 4.6 | T008-T010, T015-T017 | 12 Python tests |
| QA | Sonnet 4.6 | T018-T022 | 5 benchmark/fallback tests |
