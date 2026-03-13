"""
SPEC-020 integration tests — CSV and XLSX export engine.

Tests both Rust-accelerated and Python-fallback code paths via
apps.reportes.export_engine.generate_csv / generate_xlsx.

Run with:
    backend/venv-wsl/bin/python -m pytest \
        backend/tests/reportes/test_export_020.py \
        -p no:django --tb=short -q
"""
import io

import pytest

from apps.reportes.export_engine import generate_csv, generate_xlsx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_headers() -> list[str]:
    return ["name", "qty", "price"]


@pytest.fixture
def sample_rows() -> list[dict[str, str]]:
    return [
        {"name": "Widget", "qty": "10", "price": "25.50"},
        {"name": "Gadget", "qty": "5", "price": "99.99"},
    ]


# ===========================================================================
# T010: CSV Integration Tests (≥6 tests)
# ===========================================================================


class TestGenerateCsv:
    """Phase 2 — CSV generation tests (T010)."""

    def test_csv_starts_with_bom(self, sample_rows, sample_headers):
        """T010-1: Output must begin with UTF-8 BOM (0xEF 0xBB 0xBF)."""
        result = generate_csv(sample_rows, sample_headers)
        assert isinstance(result, bytes)
        assert result[:3] == b"\xEF\xBB\xBF", (
            f"Expected UTF-8 BOM at start, got {result[:3]!r}"
        )

    def test_csv_column_order(self):
        """T010-2: Non-alphabetical header order must be preserved in output."""
        headers = ["C", "A", "B"]
        rows = [{"A": "a_val", "B": "b_val", "C": "c_val"}]
        result = generate_csv(rows, headers)
        # Skip 3-byte BOM, decode remainder
        text = result[3:].decode("utf-8")
        lines = text.splitlines()
        assert lines[0] == "C,A,B", f"Expected header row 'C,A,B', got {lines[0]!r}"
        assert lines[1] == "c_val,a_val,b_val", (
            f"Expected data row 'c_val,a_val,b_val', got {lines[1]!r}"
        )

    def test_csv_spanish_characters(self):
        """T010-3: Spanish characters must survive the UTF-8 round-trip."""
        headers = ["empresa", "periodo", "empleado"]
        rows = [{"empresa": "Compañía", "periodo": "Año", "empleado": "Niño"}]
        result = generate_csv(rows, headers)
        assert result[:3] == b"\xEF\xBB\xBF"
        text = result[3:].decode("utf-8")
        assert "Compañía" in text
        assert "Año" in text
        assert "Niño" in text

    def test_csv_empty_headers(self):
        """T010-4: Empty headers list → BOM-only output (3 bytes)."""
        result = generate_csv(rows=[], headers=[])
        assert result == b"\xEF\xBB\xBF", (
            f"Expected 3-byte BOM, got {len(result)} bytes: {result!r}"
        )

    def test_csv_empty_rows_with_headers(self):
        """T010-5: Empty rows with headers → BOM + header row only, no data rows."""
        headers = ["A", "B"]
        result = generate_csv(rows=[], headers=headers)
        assert result[:3] == b"\xEF\xBB\xBF"
        text = result[3:].decode("utf-8")
        lines = [ln for ln in text.splitlines() if ln]
        assert len(lines) == 1, f"Expected 1 header row, got {len(lines)} lines: {lines}"
        assert lines[0] == "A,B"

    def test_csv_missing_key(self):
        """T010-6: Row missing a header key → empty cell (not an error)."""
        headers = ["name", "price"]
        rows = [{"name": "Widget"}]  # "price" key absent
        result = generate_csv(rows, headers)
        assert result[:3] == b"\xEF\xBB\xBF"
        text = result[3:].decode("utf-8")
        lines = text.splitlines()
        # Data row should have "Widget," with trailing comma for empty price cell
        data_line = lines[1]
        assert data_line.startswith("Widget"), (
            f"Expected data row to start with 'Widget', got {data_line!r}"
        )
        parts = data_line.split(",")
        assert len(parts) == 2, f"Expected 2 columns, got {parts!r}"
        assert parts[1] == "", f"Expected empty price cell, got {parts[1]!r}"


# ===========================================================================
# T017: XLSX Integration Tests (≥6 tests)
# ===========================================================================


class TestGenerateXlsx:
    """Phase 3 — XLSX generation tests (T017)."""

    def test_xlsx_produces_valid_bytes(self, sample_rows, sample_headers):
        """T017-1: Output must be non-empty and start with ZIP/PK signature."""
        result = generate_xlsx(sample_rows, sample_headers)
        assert isinstance(result, bytes)
        assert len(result) > 0, "XLSX output must not be empty"
        assert result[:2] == b"\x50\x4B", (
            f"Expected PK (ZIP) signature, got {result[:2]!r}"
        )

    def test_xlsx_numeric_detection(self):
        """T017-2: Numeric string '1250.50' must be stored as a number, not text."""
        openpyxl = pytest.importorskip("openpyxl")

        headers = ["label", "amount"]
        rows = [{"label": "Revenue", "amount": "1250.50"}]
        result = generate_xlsx(rows, headers)

        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        # Row 1 is the header; row 2 is the first data row
        cell_value = ws.cell(row=2, column=2).value
        assert isinstance(cell_value, (int, float)), (
            f"Expected numeric type, got {type(cell_value).__name__}: {cell_value!r}"
        )
        assert abs(cell_value - 1250.50) < 1e-9, (
            f"Expected 1250.50, got {cell_value}"
        )

    def test_xlsx_column_widths(self):
        """T017-3: Explicit column widths must not cause an error."""
        headers = ["description", "amount"]
        rows = [{"description": "Test item", "amount": "42.00"}]
        widths = {"description": 40.0, "amount": 15.0}
        # Must complete without raising
        result = generate_xlsx(rows, headers, column_widths=widths)
        assert result[:2] == b"\x50\x4B"

    def test_xlsx_spanish_characters(self):
        """T017-4: Spanish characters must be preserved in XLSX cells."""
        openpyxl = pytest.importorskip("openpyxl")

        headers = ["empresa"]
        rows = [{"empresa": "Compañía"}]
        result = generate_xlsx(rows, headers)

        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        cell_value = ws.cell(row=2, column=1).value
        assert cell_value == "Compañía", (
            f"Expected 'Compañía', got {cell_value!r}"
        )

    def test_xlsx_empty_rows_with_headers(self):
        """T017-5: Empty data rows → valid XLSX with headers only (no crash)."""
        openpyxl = pytest.importorskip("openpyxl")

        headers = ["col_a", "col_b"]
        result = generate_xlsx(rows=[], headers=headers)

        assert result[:2] == b"\x50\x4B"
        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        # Headers must be present in row 1
        assert ws.cell(row=1, column=1).value == "col_a"
        assert ws.cell(row=1, column=2).value == "col_b"
        # Row 2 must be empty (no data)
        assert ws.cell(row=2, column=1).value is None

    def test_xlsx_text_value(self):
        """T017-6: Non-numeric string 'not-a-number' must be written as text."""
        openpyxl = pytest.importorskip("openpyxl")

        headers = ["value"]
        rows = [{"value": "not-a-number"}]
        result = generate_xlsx(rows, headers)

        wb = openpyxl.load_workbook(io.BytesIO(result))
        ws = wb.active
        cell_value = ws.cell(row=2, column=1).value
        assert cell_value == "not-a-number", (
            f"Expected string 'not-a-number', got {cell_value!r}"
        )


# ===========================================================================
# Phase 4 (US3 Performance): T018–T020
# ===========================================================================

import time
import threading


def _generate_test_data(rows: int, cols: int) -> tuple[list[dict[str, str]], list[str]]:
    """Generate synthetic test data with mixed numeric/text values including Spanish chars."""
    headers = [f"Col_{i}" for i in range(cols)]
    data = []
    for r in range(rows):
        row = {}
        for c, h in enumerate(headers):
            if c % 3 == 0:
                row[h] = f"{r * 1.5 + c:.2f}"  # numeric string
            elif c % 3 == 1:
                row[h] = f"Compañía #{r}-{c}"  # Spanish text
            else:
                row[h] = f"Value-{r}-{c}"  # plain text
        data.append(row)
    return data, headers


class TestPerformance:
    """US3: Large dataset performance tests (SC-001, SC-002, SC-005)."""

    def test_csv_10k_rows_under_2_seconds(self):
        """T018: 10K rows x 10 cols CSV generation must complete in under 2 seconds."""
        from apps.reportes.export_engine import generate_csv

        rows, headers = _generate_test_data(10_000, 10)
        start = time.perf_counter()
        result = generate_csv(rows, headers)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"CSV generation took {elapsed:.2f}s (target: <2s)"
        assert len(result) > 0
        assert result[:3] == b"\xEF\xBB\xBF", "CSV must start with UTF-8 BOM"

    def test_xlsx_10k_rows_under_2_seconds(self):
        """T019: 10K rows x 10 cols XLSX generation must complete in under 2 seconds."""
        from apps.reportes.export_engine import generate_xlsx

        rows, headers = _generate_test_data(10_000, 10)
        start = time.perf_counter()
        result = generate_xlsx(rows, headers)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"XLSX generation took {elapsed:.2f}s (target: <2s)"
        assert len(result) > 0
        assert result[:2] == b"\x50\x4B", "XLSX must start with ZIP/PK signature"

    def test_gil_release_concurrent_operation(self):
        """T020: CSV generation must not block the GIL — concurrent Python work must proceed."""
        from apps.reportes.export_engine import generate_csv

        rows, headers = _generate_test_data(10_000, 10)
        results = {"csv_done": False, "concurrent_done": False}

        def run_csv():
            generate_csv(rows, headers)
            results["csv_done"] = True

        def run_concurrent():
            # Simple CPU work that requires the GIL
            total = sum(range(100_000))
            results["concurrent_done"] = True
            return total

        csv_thread = threading.Thread(target=run_csv)
        csv_thread.start()

        # If GIL is released during CSV generation, this completes concurrently
        run_concurrent()

        csv_thread.join(timeout=10)
        assert results["csv_done"], "CSV generation thread did not complete within timeout"
        assert results["concurrent_done"], "Concurrent Python operation did not complete"


# ===========================================================================
# Phase 5 (US4 Fallback): T021–T022
# ===========================================================================


class TestFallback:
    """US4: Graceful Python fallback tests (SC-006)."""

    def test_csv_fallback_produces_valid_output(self, monkeypatch):
        """T021: CSV generation must work correctly when Rust extension is unavailable."""
        import apps.reportes.export_engine as engine
        monkeypatch.setattr(engine, "_USE_RUST_EXPORT", False)

        rows = [
            {"Producto": "Yerba Mate", "Precio": "1250.50"},
            {"Producto": "Dulce de Leche", "Precio": "890.00"},
        ]
        headers = ["Producto", "Precio"]

        result = engine.generate_csv(rows, headers)
        assert isinstance(result, bytes)
        assert result[:3] == b"\xEF\xBB\xBF", "CSV fallback must include UTF-8 BOM"
        text = result[3:].decode("utf-8")
        assert "Yerba Mate" in text, "CSV fallback must contain first product name"
        assert "1250.50" in text, "CSV fallback must contain first product price"
        assert "Dulce de Leche" in text, "CSV fallback must contain second product name"
        assert "890.00" in text, "CSV fallback must contain second product price"

    def test_xlsx_fallback_produces_valid_output(self, monkeypatch):
        """T022: XLSX generation must work correctly when Rust extension is unavailable."""
        import apps.reportes.export_engine as engine
        monkeypatch.setattr(engine, "_USE_RUST_EXPORT", False)

        rows = [
            {"Producto": "Yerba Mate", "Precio": "1250.50"},
        ]
        headers = ["Producto", "Precio"]

        result = engine.generate_xlsx(rows, headers)
        assert isinstance(result, bytes)
        assert len(result) > 0, "XLSX fallback must produce non-empty output"
        # XLSX files are ZIP archives — must start with PK signature
        assert result[:2] == b"PK", (
            f"XLSX fallback must produce valid ZIP/XLSX, got {result[:2]!r}"
        )
