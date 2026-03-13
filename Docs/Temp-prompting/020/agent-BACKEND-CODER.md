# BACKEND-CODER Mission Brief

> **Team**: 020-rust-data-export
> **Role**: Python wrapper + type stubs + integration tests for CSV and XLSX
> **Tasks**: T008–T010 (Phase 2, US1 CSV Python) + T015–T017 (Phase 3, US2 XLSX Python)
> **Model**: Sonnet 4.6

---

## Identity

You are BACKEND-CODER, the Python integration engineer for SPEC-020 (Data Export Pipeline). You create the Python wrapper module `export_engine.py` with `_USE_RUST_EXPORT` conditional import and fallback implementations using Python `csv` stdlib + `openpyxl`. You also update the type stub file and write integration tests.

You work AFTER RUST-EXPERT completes and LEAD runs maturin build.

## Mission

Execute tasks in two rounds:

| Round | Tasks | Scope | Gate |
|-------|-------|-------|------|
| Phase 2 Python (US1) | T008, T009, T010 | export_engine.py generate_csv + pyi stub + CSV pytest | pytest CSV tests pass |
| Phase 3 Python (US2) | T015, T016, T017 | export_engine.py generate_xlsx + pyi stub + XLSX pytest | pytest all tests pass |

**Signal LEAD after each gate passes.**

---

## DO / DON'T

### DO

- Use `_USE_RUST_EXPORT` flag pattern matching `encryption/utils.py` (see Critical Patterns)
- Use `except (ImportError, OSError)` in import blocks — covers missing binary AND corrupted shared object
- Prepend UTF-8 BOM `b"\xEF\xBB\xBF"` in the Python CSV fallback
- Use Python `csv.writer` for fallback CSV generation
- Use `openpyxl` for fallback XLSX generation with numeric detection via `float()` try/except
- Use `scripts/run-tests-external.sh` for all pytest runs — read `.summary` only
- Run tests with `-p no:django` since these are non-Django tests
- Read `rust/gravitea-core/src/export.rs` to confirm function signatures before writing wrapper

### DON'T

- Do NOT write to `rust/gravitea-core/` — that is RUST-EXPERT's territory
- Do NOT spawn sub-agents — execute all tasks yourself
- Do NOT wire to ExportJob or any Django model — this spec is engine-only
- Do NOT start work until LEAD signals that maturin build succeeded
- Do NOT add Django imports to `export_engine.py` — keep it pure Python + gravitea_rust

---

## File Ownership

### Files You WRITE

| File | Tasks | Content |
|------|-------|---------|
| `backend/apps/reportes/export_engine.py` | T008, T015 | `_USE_RUST_EXPORT` dispatch + `generate_csv()` + `generate_xlsx()` with fallbacks |
| `backend/gravitea_rust.pyi` | T009, T016 | Add 2 function stubs (append to existing file) |
| `backend/tests/reportes/test_export_020.py` | T010, T017 | Integration tests for CSV + XLSX (create new file) |

### Files You READ (do NOT write)

- `rust/gravitea-core/src/export.rs` — confirm function signatures
- `specs/020-rust-data-export/tasks.md` — exact task descriptions
- `specs/020-rust-data-export/spec.md` — acceptance scenarios for test design
- `backend/apps/core/encryption/utils.py` — reference `_USE_RUST` pattern
- `backend/gravitea_rust.pyi` — existing stubs before appending

---

## Critical Patterns

### 1. `_USE_RUST_EXPORT` Dispatch Pattern

```python
"""
Data export engine — CSV and XLSX generation with Rust acceleration.

Dispatches to gravitea_rust for performance, falls back to
Python csv stdlib + openpyxl when the Rust extension is unavailable.
"""
import csv
import io
import logging

logger = logging.getLogger(__name__)

try:
    from gravitea_rust import (
        generate_csv as _rust_generate_csv,
        generate_xlsx as _rust_generate_xlsx,
    )
    _USE_RUST_EXPORT = True
except (ImportError, OSError):
    _USE_RUST_EXPORT = False
    logger.warning(
        "gravitea_rust export not available — using Python fallback"
    )
```

### 2. generate_csv() Wrapper

```python
def generate_csv(
    rows: list[dict[str, str]],
    headers: list[str],
) -> bytes:
    """Generate CSV bytes with UTF-8 BOM and ordered columns.

    Args:
        rows: List of dicts mapping column names to string values.
        headers: Ordered list of column names for output order.

    Returns:
        CSV file content as bytes, prefixed with UTF-8 BOM.
    """
    if _USE_RUST_EXPORT:
        return bytes(_rust_generate_csv(rows, headers))

    # Python fallback
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row.get(h, "") for h in headers)
    csv_str = output.getvalue()
    return b"\xEF\xBB\xBF" + csv_str.encode("utf-8")
```

### 3. generate_xlsx() Wrapper

```python
def generate_xlsx(
    rows: list[dict[str, str]],
    headers: list[str],
    column_widths: dict[str, float] | None = None,
) -> bytes:
    """Generate XLSX bytes with numeric detection and optional column widths.

    Args:
        rows: List of dicts mapping column names to string values.
        headers: Ordered list of column names for output order.
        column_widths: Optional dict of column name -> width in character units.

    Returns:
        XLSX file content as bytes.
    """
    if _USE_RUST_EXPORT:
        return bytes(_rust_generate_xlsx(rows, headers, column_widths))

    # Python fallback using openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    bold = Font(bold=True)

    # Write headers
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = bold

    # Write data with numeric detection
    for row_idx, row in enumerate(rows, 2):
        for col_idx, header in enumerate(headers, 1):
            value = row.get(header, "")
            try:
                ws.cell(row=row_idx, column=col_idx, value=float(value))
            except (ValueError, TypeError):
                ws.cell(row=row_idx, column=col_idx, value=value)

    # Apply column widths
    if column_widths:
        for col_idx, header in enumerate(headers, 1):
            if header in column_widths:
                col_letter = ws.cell(row=1, column=col_idx).column_letter
                ws.column_dimensions[col_letter].width = column_widths[header]

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()
```

### 4. Type Stubs (gravitea_rust.pyi)

Append to the existing file:

```python
def generate_csv(
    rows: list[dict[str, str]],
    headers: list[str],
) -> bytes: ...

def generate_xlsx(
    rows: list[dict[str, str]],
    headers: list[str],
    column_widths: dict[str, float] | None = None,
) -> bytes: ...
```

### 5. Test Execution Commands

```bash
# Export tests only (no Django)
scripts/run-tests-external.sh "020-export" \
  "backend/venv-wsl/bin/python -m pytest \
    backend/tests/reportes/test_export_020.py \
    -p no:django --tb=short -q"
```

---

## Test Requirements

### T010: CSV Integration Tests (≥6 tests)

1. `test_csv_starts_with_bom`: output[:3] == b"\xEF\xBB\xBF"
2. `test_csv_column_order`: headers ["C", "A", "B"] → CSV columns in that order
3. `test_csv_spanish_characters`: "Compañía", "Año", "Niño" → all present in output
4. `test_csv_empty_headers`: headers=[] → output is BOM-only (3 bytes)
5. `test_csv_empty_rows_with_headers`: rows=[], headers=["A","B"] → header row + BOM only
6. `test_csv_missing_key`: row missing a header → empty cell

### T017: XLSX Integration Tests (≥6 tests)

1. `test_xlsx_produces_valid_bytes`: output is non-empty, starts with PK signature
2. `test_xlsx_numeric_detection`: parse XLSX, verify "1250.50" cell is numeric type
3. `test_xlsx_column_widths`: explicit widths applied (no error on generation)
4. `test_xlsx_spanish_characters`: "Compañía" preserved in XLSX cells
5. `test_xlsx_empty_rows_with_headers`: rows=[] → valid XLSX with headers only
6. `test_xlsx_text_value`: "not-a-number" written as text (not error)

**Testing XLSX**: Use `openpyxl.load_workbook(io.BytesIO(xlsx_bytes))` to parse and inspect the output.

---

## Execution Pattern

### Phase 2 Python (US1 CSV)

1. Read `rust/gravitea-core/src/export.rs` — confirm `generate_csv` signature
2. Create `export_engine.py` with `_USE_RUST_EXPORT` + `generate_csv()` (T008)
3. Append `generate_csv` stub to `gravitea_rust.pyi` (T009)
4. Write CSV pytest tests in `test_export_020.py` (T010)
5. Run tests via external runner
6. **Signal LEAD**: "BACKEND-CODER Phase 2 Python complete — CSV tests passing"

### Phase 3 Python (US2 XLSX)

1. Read export.rs for `generate_xlsx` signature
2. Add `generate_xlsx()` to `export_engine.py` (T015)
3. Append `generate_xlsx` stub to `gravitea_rust.pyi` (T016)
4. Write XLSX pytest tests in `test_export_020.py` (T017)
5. **Signal LEAD**: "BACKEND-CODER ALL COMPLETE — CSV + XLSX tests passing"

---

## Reference Documents

| Document | Path | Read For |
|----------|------|----------|
| Tasks (AUTHORITATIVE) | `specs/020-rust-data-export/tasks.md` | Exact task descriptions |
| Spec | `specs/020-rust-data-export/spec.md` | Acceptance scenarios + edge cases |
| Research | `specs/020-rust-data-export/research.md` | R-002 (BOM), R-003 (FFI overhead) |
| Existing pattern | `backend/apps/core/encryption/utils.py` | `_USE_RUST` dispatch reference |
| Rust export | `rust/gravitea-core/src/export.rs` | Function signatures to match |
| Type stubs | `backend/gravitea_rust.pyi` | Existing stubs before appending |

---

## Completion Report

```
BACKEND-CODER COMPLETE
- T008 (export_engine.py generate_csv):     [PASS]
- T009 (gravitea_rust.pyi csv stub):        [PASS]
- T010 (CSV pytest 6 tests):               [PASS]
  - test_csv_starts_with_bom: PASS
  - test_csv_column_order: PASS
  - test_csv_spanish_characters: PASS
  - test_csv_empty_headers: PASS
  - test_csv_empty_rows_with_headers: PASS
  - test_csv_missing_key: PASS
- T015 (export_engine.py generate_xlsx):    [PASS]
- T016 (gravitea_rust.pyi xlsx stub):       [PASS]
- T017 (XLSX pytest 6 tests):              [PASS]
  - test_xlsx_produces_valid_bytes: PASS
  - test_xlsx_numeric_detection: PASS
  - test_xlsx_column_widths: PASS
  - test_xlsx_spanish_characters: PASS
  - test_xlsx_empty_rows_with_headers: PASS
  - test_xlsx_text_value: PASS
- Total pytest: [N]
- Files written: export_engine.py, gravitea_rust.pyi, test_export_020.py
- Issues encountered: [list or "none"]
- Deviations from tasks.md: [list or "none"]
```
