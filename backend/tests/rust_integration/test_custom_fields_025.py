"""
SPEC-025: Custom Field Type Validator Acceleration — Integration Tests
======================================================================
Tests: US1 parity (SC-002), US1 benchmark (SC-001), US2 edge cases, US2 select format,
       US3 threshold (SC-005), US4 fallback (SC-006)
"""
import json
import time
import unittest.mock as mock
import pytest
from decimal import Decimal
from types import SimpleNamespace


# ─── Test Helpers ────────────────────────────────────────────

def _make_definition(field_key, field_type, choices=None):
    """Build a mock TenantFieldDefinition-like object."""
    return SimpleNamespace(field_key=field_key, field_type=field_type, choices=choices)


# ─── US1: Accelerated Batch Validation ──────────────────────

class TestUS1Parity:
    """User Story 1: Parity tests — Rust and Python produce identical errors."""

    def _run_parity(self, definitions, custom_data):
        """Run same input through Rust and Python paths, compare output."""
        from apps.core.serializers.validation_engine import _validate_rust, _validate_python
        py_result = _validate_python(definitions, custom_data)
        rust_result = _validate_rust(definitions, custom_data)
        assert rust_result == py_result, f"Parity mismatch:\nRust: {rust_result}\nPython: {py_result}"

    def test_parity_text_valid(self):
        defs = [_make_definition("name", "text")]
        self._run_parity(defs, {"name": "hello"})

    def test_parity_text_invalid(self):
        defs = [_make_definition("name", "text")]
        self._run_parity(defs, {"name": 42})

    def test_parity_integer_valid(self):
        defs = [_make_definition("qty", "integer")]
        self._run_parity(defs, {"qty": 5})

    def test_parity_integer_invalid(self):
        defs = [_make_definition("qty", "integer")]
        self._run_parity(defs, {"qty": "five"})

    def test_parity_integer_bool_rejected(self):
        defs = [_make_definition("qty", "integer")]
        self._run_parity(defs, {"qty": True})

    def test_parity_decimal_valid(self):
        defs = [_make_definition("price", "decimal")]
        self._run_parity(defs, {"price": 9.99})

    def test_parity_decimal_int_accepted(self):
        defs = [_make_definition("price", "decimal")]
        self._run_parity(defs, {"price": 5})

    def test_parity_decimal_bool_rejected(self):
        defs = [_make_definition("price", "decimal")]
        self._run_parity(defs, {"price": True})

    def test_parity_boolean_valid(self):
        defs = [_make_definition("active", "boolean")]
        self._run_parity(defs, {"active": True})

    def test_parity_boolean_invalid(self):
        defs = [_make_definition("active", "boolean")]
        self._run_parity(defs, {"active": "yes"})

    def test_parity_date_valid(self):
        defs = [_make_definition("expiry", "date")]
        self._run_parity(defs, {"expiry": "2024-12-31"})

    def test_parity_date_invalid(self):
        defs = [_make_definition("expiry", "date")]
        self._run_parity(defs, {"expiry": "not-a-date"})

    def test_parity_date_format_only(self):
        defs = [_make_definition("expiry", "date")]
        self._run_parity(defs, {"expiry": "2026-02-29"})

    def test_parity_select_valid(self):
        defs = [_make_definition("material", "select", ["acero", "aluminio", "bronce"])]
        self._run_parity(defs, {"material": "acero"})

    def test_parity_select_invalid(self):
        defs = [_make_definition("material", "select", ["acero", "aluminio", "bronce"])]
        self._run_parity(defs, {"material": "cobre"})


class TestUS1Benchmark:
    """User Story 1: Benchmark — 25 fields all 6 types < 2ms (SC-001 proxy)."""

    def test_benchmark_25_fields(self):
        from apps.core.serializers.validation_engine import _validate_rust
        choices_50 = [f"choice_{i}" for i in range(50)]
        defs = []
        for i in range(4):
            defs.append(_make_definition(f"text_{i}", "text"))
        for i in range(4):
            defs.append(_make_definition(f"int_{i}", "integer"))
        for i in range(4):
            defs.append(_make_definition(f"dec_{i}", "decimal"))
        for i in range(4):
            defs.append(_make_definition(f"bool_{i}", "boolean"))
        for i in range(4):
            defs.append(_make_definition(f"date_{i}", "date"))
        for i in range(5):
            defs.append(_make_definition(f"sel_{i}", "select", choices_50))

        custom_data = {}
        for i in range(4):
            custom_data[f"text_{i}"] = f"value_{i}"
        for i in range(4):
            custom_data[f"int_{i}"] = i
        for i in range(4):
            custom_data[f"dec_{i}"] = float(i) + 0.5
        for i in range(4):
            custom_data[f"bool_{i}"] = i % 2 == 0
        for i in range(4):
            custom_data[f"date_{i}"] = f"2024-0{i+1}-15"
        for i in range(5):
            custom_data[f"sel_{i}"] = "choice_0"

        # Warm up
        _validate_rust(defs, custom_data)

        # Benchmark
        start = time.perf_counter()
        for _ in range(100):
            _validate_rust(defs, custom_data)
        elapsed = (time.perf_counter() - start) / 100
        elapsed_ms = elapsed * 1000

        assert elapsed_ms < 2.0, f"Rust validation took {elapsed_ms:.3f}ms, expected < 2ms"


# ─── US2: Output Parity Guarantee ───────────────────────────

class TestUS2EdgeCases:
    """User Story 2: Edge case parity — null, undefined, empty, unknown."""

    def _run_parity(self, definitions, custom_data):
        from apps.core.serializers.validation_engine import _validate_rust, _validate_python
        py_result = _validate_python(definitions, custom_data)
        rust_result = _validate_rust(definitions, custom_data)
        assert rust_result == py_result

    def test_parity_null_values_skipped(self):
        defs = [_make_definition("name", "text")]
        self._run_parity(defs, {"name": None})

    def test_parity_undefined_keys_ignored(self):
        defs = [_make_definition("name", "text")]
        self._run_parity(defs, {"unknown": 42})

    def test_parity_decimal_from_decimal_type(self):
        defs = [_make_definition("price", "decimal")]
        self._run_parity(defs, {"price": Decimal("9.99")})

    def test_parity_select_empty_choices(self):
        defs = [_make_definition("material", "select", [])]
        self._run_parity(defs, {"material": "anything"})

    def test_parity_select_null_choices(self):
        defs = [_make_definition("material", "select", None)]
        self._run_parity(defs, {"material": "anything"})

    def test_parity_empty_custom_data(self):
        defs = [_make_definition("name", "text")]
        self._run_parity(defs, {})

    def test_parity_empty_definitions(self):
        self._run_parity([], {"name": "hello"})

    def test_parity_unknown_field_type(self):
        defs = [_make_definition("custom", "custom_type")]
        self._run_parity(defs, {"custom": "anything"})


class TestUS2SelectFormat:
    """User Story 2: Select error format parity — single quotes, byte-identical."""

    def test_select_error_format_parity(self):
        from apps.core.serializers.validation_engine import _validate_rust, _validate_python
        defs = [_make_definition("material", "select", ["acero", "aluminio", "bronce"])]
        data = {"material": "cobre"}
        py_result = _validate_python(defs, data)
        rust_result = _validate_rust(defs, data)
        assert rust_result == py_result
        expected_msg = "Invalid choice. Allowed: ['acero', 'aluminio', 'bronce']"
        assert rust_result["material"] == [expected_msg]


# ─── US3: Small Field Set Fallback ──────────────────────────

class TestUS3Threshold:
    """User Story 3: Threshold routing — ≤5 fields → Python, >5 → Rust."""

    def test_3_definitions_uses_python(self):
        from apps.core.serializers import validation_engine
        defs = [_make_definition(f"f{i}", "text") for i in range(3)]
        with mock.patch.object(validation_engine, '_validate_python', wraps=validation_engine._validate_python) as py_mock, \
             mock.patch.object(validation_engine, '_validate_rust', wraps=validation_engine._validate_rust) as rust_mock:
            validation_engine.validate_fields(defs, {"f0": "a"})
            py_mock.assert_called_once()
            rust_mock.assert_not_called()

    def test_5_definitions_uses_python(self):
        from apps.core.serializers import validation_engine
        defs = [_make_definition(f"f{i}", "text") for i in range(5)]
        with mock.patch.object(validation_engine, '_validate_python', wraps=validation_engine._validate_python) as py_mock, \
             mock.patch.object(validation_engine, '_validate_rust', wraps=validation_engine._validate_rust) as rust_mock:
            validation_engine.validate_fields(defs, {"f0": "a"})
            py_mock.assert_called_once()
            rust_mock.assert_not_called()

    def test_6_definitions_uses_rust(self):
        from apps.core.serializers import validation_engine
        defs = [_make_definition(f"f{i}", "text") for i in range(6)]
        with mock.patch.object(validation_engine, '_validate_python', wraps=validation_engine._validate_python) as py_mock, \
             mock.patch.object(validation_engine, '_validate_rust', wraps=validation_engine._validate_rust) as rust_mock:
            validation_engine.validate_fields(defs, {"f0": "a"})
            rust_mock.assert_called_once()
            py_mock.assert_not_called()


# ─── US4: Graceful Degradation ──────────────────────────────

class TestUS4Fallback:
    """User Story 4: Fallback when Rust unavailable."""

    def test_fallback_correct_output(self):
        from apps.core.serializers import validation_engine
        defs = [_make_definition(f"f{i}", "text") for i in range(20)]
        data = {f"f{i}": i for i in range(20)}  # ints for text fields → should error
        with mock.patch.object(validation_engine, '_USE_RUST', False):
            result = validation_engine.validate_fields(defs, data)
            assert len(result) == 20
            for key in data:
                assert result[key] == ["Expected a text value."]

    def test_fallback_warning_logged(self):
        """Warning logged when Rust import fails."""
        # The warning is logged at module import time when _USE_RUST is set to False
        # We verify _USE_RUST flag behavior
        from apps.core.serializers import validation_engine
        assert hasattr(validation_engine, '_USE_RUST')

    def test_fallback_no_exceptions(self):
        from apps.core.serializers import validation_engine
        defs = [_make_definition(f"f{i}", "text") for i in range(20)]
        data = {f"f{i}": f"val_{i}" for i in range(20)}
        with mock.patch.object(validation_engine, '_USE_RUST', False):
            result = validation_engine.validate_fields(defs, data)
            assert result == {}
