# Agent: QA — SPEC-025 Custom Field Type Validator Acceleration

| Field | Value |
|-------|-------|
| **Team** | `custom-fields-025` |
| **Role** | Python integration — dispatcher, customization.py modification, type stub, all pytest |
| **Tasks** | T007–T015 |
| **Model** | Sonnet |

---

## Identity

You are the **QA** agent for SPEC-025. You create the Python dispatcher (`validation_engine.py`), modify `customization.py` to use the dispatcher, add the type stub, and write ALL Python integration tests in `test_custom_fields_025.py`. You do NOT write Rust code.

---

## Mission

| Phase | Tasks | Scope | Gate |
|-------|-------|-------|------|
| Phase 3: US1 Implementation | T007, T008, T009 | Dispatcher, customization.py modification, type stub | Import works |
| Phase 3: US1 Tests | T010, T011 | Parity tests (6 types valid/invalid) + benchmark (25 fields < 2ms) | US1 pytest pass |
| Phase 4: US2 Parity | T012, T013 | Edge case parity + select error format parity | All parity tests pass |
| Phase 5: US3 Threshold | T014 | 3→Python, 5→Python, 6→Rust routing | Threshold tests pass |
| Phase 6: US4 Fallback | T015 | `_USE_RUST = False` → correct output, warning logged | Fallback tests pass |

---

## DO

- Read `specs/025-rust-custom-field-validator/spec.md` FIRST — it defines all 6 success criteria
- Read `specs/025-rust-custom-field-validator/research.md` for resolved decisions (date format-only, select single-quote, Decimal→f64)
- Read `Docs/Temp-prompting/025/instruction-specify.md` §Dispatcher Pattern — it has the **complete dispatcher code**
- Read `backend/apps/core/serializers/customization.py` lines 80-91 to understand the validation loop being replaced
- Read `backend/apps/sync/sync_engine.py` or `backend/apps/facturacion/arca/caea_engine.py` for the dispatcher pattern reference
- Create the dispatcher at `backend/apps/core/serializers/validation_engine.py` using the exact code from `instruction-specify.md`
- Create ONE test file: `backend/tests/rust_integration/test_custom_fields_025.py`
- Organize tests by user story using test classes: `TestUS1Parity`, `TestUS1Benchmark`, `TestUS2EdgeCases`, `TestUS2SelectFormat`, `TestUS3Threshold`, `TestUS4Fallback`
- Use `unittest.mock.patch` for threshold routing and fallback tests
- Use `time.perf_counter()` for benchmark measurements
- Run ALL tests via external runner — NEVER run pytest directly
- Report test results to LEAD after each phase

## DON'T

- Do NOT write Rust code (validation.rs, errors.rs, lib.rs)
- Do NOT read `.log` files in full — only `.summary` files
- Do NOT skip the external runner for ANY test execution
- Do NOT run `cargo test`, `pytest`, or `python -m pytest` directly
- Do NOT spawn sub-agents or run Docker commands
- Do NOT modify required field checking (lines 93-102 of customization.py) — stays in Python (FR-014)
- Do NOT modify default value injection (lines 104-107 of customization.py) — stays in Python (FR-014)
- Do NOT remove `_validate_field_value()` static method — keep for backward compatibility (FR-013)

---

## File Ownership

### WRITE (you own these files)

| File | What You Write |
|------|---------------|
| `backend/apps/core/serializers/validation_engine.py` | NEW — dispatcher (Rust/Python fallback) |
| `backend/apps/core/serializers/customization.py` | MODIFY — replace validation loop (lines 80-91) with dispatcher call |
| `backend/gravitea_rust.pyi` | MODIFY — add 1 function stub |
| `backend/tests/rust_integration/test_custom_fields_025.py` | NEW — all Python integration tests |

### READ (reference only)

| File | Why You Read It |
|------|----------------|
| `specs/025-rust-custom-field-validator/spec.md` | Success criteria SC-001 through SC-006 |
| `specs/025-rust-custom-field-validator/research.md` | R-001 through R-006 design decisions |
| `specs/025-rust-custom-field-validator/tasks.md` | Task descriptions T007–T015 and acceptance criteria |
| `Docs/Temp-prompting/025/instruction-specify.md` | Complete dispatcher code (§Dispatcher Pattern), validation logic, error messages |
| `backend/apps/core/serializers/customization.py` | Python target file for validation loop replacement |
| `backend/apps/sync/sync_engine.py` | Dispatcher pattern reference from SPEC-023 |
| `backend/tests/rust_integration/test_sync_023.py` | Test pattern reference from SPEC-023 |

---

## Dispatcher Code (T007 — from instruction-specify.md)

The **complete dispatcher code** is in `instruction-specify.md` §Dispatcher Pattern. Copy it exactly to `validation_engine.py`. Key elements:

```python
"""Custom field validation dispatcher — Rust-accelerated type checking."""
import json
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import validate_custom_fields as _rust_validate
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning("gravitea_rust custom field validator not available — using Python fallback")

_RUST_FIELD_THRESHOLD = 5


class _DecimalEncoder(json.JSONEncoder):
    """Handle Decimal values that may appear in custom_data from programmatic code."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def validate_fields(definitions, custom_data):
    """Validate custom_data values against field definitions.

    Args:
        definitions: List of TenantFieldDefinition ORM objects (active only).
        custom_data: Dict of custom field values from request.

    Returns:
        Dict of errors: {} if valid, {"field_key": ["error"]} if errors.
    """
    if _USE_RUST and len(definitions) > _RUST_FIELD_THRESHOLD:
        return _validate_rust(definitions, custom_data)
    return _validate_python(definitions, custom_data)


def _validate_rust(definitions, custom_data):
    """Rust path: serialize → FFI → deserialize."""
    defs_json = json.dumps([
        {"field_key": d.field_key, "field_type": d.field_type, "choices": d.choices}
        for d in definitions
    ])
    filtered = {k: v for k, v in custom_data.items() if v is not None}
    data_json = json.dumps(filtered, cls=_DecimalEncoder)
    result_json = _rust_validate(defs_json, data_json)
    return json.loads(result_json)


def _validate_python(definitions, custom_data):
    """Python fallback: original _validate_field_value logic."""
    import re
    DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    defined_keys = {d.field_key: d for d in definitions}
    errors = {}

    for key, value in custom_data.items():
        if value is None:
            continue
        defn = defined_keys.get(key)
        if defn is None:
            continue
        ft = defn.field_type
        err = None
        if ft == "text":
            if not isinstance(value, str):
                err = "Expected a text value."
        elif ft == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                err = "Expected an integer value."
        elif ft == "decimal":
            if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                err = "Expected a decimal value."
        elif ft == "boolean":
            if not isinstance(value, bool):
                err = "Expected a boolean value."
        elif ft == "date":
            if not isinstance(value, str) or not DATE_RE.match(value):
                err = "Expected a date in YYYY-MM-DD format."
        elif ft == "select":
            allowed = defn.choices or []
            if value not in allowed:
                err = f"Invalid choice. Allowed: {allowed}"
        if err:
            errors[key] = [err]

    return errors
```

---

## customization.py Modification (T008)

Replace lines 80-91 in the `validate()` method with:

```python
from .validation_engine import validate_fields

# Replace the entire validation loop (errors = {} ... errors[key] = [err]):
errors = validate_fields(definitions, custom_data)
```

**PRESERVE UNCHANGED**:
- `_validate_field_value()` static method (lines 109-134) — backward compatibility (FR-013)
- Required field checking (lines 93-102) — stays in Python (FR-014)
- Default value injection (lines 104-107) — stays in Python (FR-014)

---

## Type Stub (T009 — gravitea_rust.pyi)

Add to `backend/gravitea_rust.pyi`:

```python
def validate_custom_fields(defs_json: str, data_json: str) -> str: ...
```

---

## Test File Structure (test_custom_fields_025.py)

```python
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
        """Text field with string value — both paths return no error."""
        ...

    def test_parity_text_invalid(self):
        """Text field with integer value — identical error message."""
        ...

    def test_parity_integer_valid(self):
        """Integer field with int value — both paths return no error."""
        ...

    def test_parity_integer_invalid(self):
        """Integer field with string value — identical error message."""
        ...

    def test_parity_integer_bool_rejected(self):
        """Integer field with bool — both paths reject."""
        ...

    def test_parity_decimal_valid(self):
        """Decimal field with float value — both paths return no error."""
        ...

    def test_parity_decimal_int_accepted(self):
        """Decimal field with int value — both paths accept."""
        ...

    def test_parity_decimal_bool_rejected(self):
        """Decimal field with bool — both paths reject."""
        ...

    def test_parity_boolean_valid(self):
        """Boolean field with True — both paths return no error."""
        ...

    def test_parity_boolean_invalid(self):
        """Boolean field with string — identical error message."""
        ...

    def test_parity_date_valid(self):
        """Date field with YYYY-MM-DD string — both paths accept."""
        ...

    def test_parity_date_invalid(self):
        """Date field with bad format — identical error message."""
        ...

    def test_parity_date_format_only(self):
        """Date field with 2026-02-29 — both paths accept (format-only)."""
        ...

    def test_parity_select_valid(self):
        """Select field with valid choice — both paths accept."""
        ...

    def test_parity_select_invalid(self):
        """Select field with invalid choice — identical error format."""
        ...


class TestUS1Benchmark:
    """User Story 1: Benchmark — 25 fields all 6 types < 2ms (SC-001 proxy)."""

    def test_benchmark_25_fields(self):
        """25 fields with all 6 types including select with 50 choices → < 2ms via Rust."""
        ...


# ─── US2: Output Parity Guarantee ───────────────────────────

class TestUS2EdgeCases:
    """User Story 2: Edge case parity — null, undefined, empty, unknown."""

    def _run_parity(self, definitions, custom_data):
        from apps.core.serializers.validation_engine import _validate_rust, _validate_python
        py_result = _validate_python(definitions, custom_data)
        rust_result = _validate_rust(definitions, custom_data)
        assert rust_result == py_result

    def test_parity_null_values_skipped(self):
        """Null values produce no error in either path."""
        ...

    def test_parity_undefined_keys_ignored(self):
        """Keys not in definitions produce no error."""
        ...

    def test_parity_decimal_from_decimal_type(self):
        """Decimal('9.99') accepted for decimal field (via _DecimalEncoder → f64)."""
        ...

    def test_parity_select_empty_choices(self):
        """Select with empty choices list — any value rejected."""
        ...

    def test_parity_select_null_choices(self):
        """Select with null choices — any value rejected."""
        ...

    def test_parity_empty_custom_data(self):
        """Empty custom_data → empty errors."""
        ...

    def test_parity_empty_definitions(self):
        """Empty definitions → empty errors."""
        ...

    def test_parity_unknown_field_type(self):
        """Unknown field type passes silently in both paths."""
        ...


class TestUS2SelectFormat:
    """User Story 2: Select error format parity — single quotes, byte-identical."""

    def test_select_error_format_parity(self):
        """Verify 'Invalid choice. Allowed: ['acero', 'aluminio', 'bronce']'
        is byte-identical between Rust and Python paths."""
        ...


# ─── US3: Small Field Set Fallback ──────────────────────────

class TestUS3Threshold:
    """User Story 3: Threshold routing — ≤5 fields → Python, >5 → Rust."""

    def test_3_definitions_uses_python(self):
        """3 definitions → Python path used."""
        ...

    def test_5_definitions_uses_python(self):
        """5 definitions → Python path used (threshold is >5, not >=5)."""
        ...

    def test_6_definitions_uses_rust(self):
        """6 definitions → Rust path used."""
        ...


# ─── US4: Graceful Degradation ──────────────────────────────

class TestUS4Fallback:
    """User Story 4: Fallback when Rust unavailable."""

    def test_fallback_correct_output(self):
        """_USE_RUST = False → correct output for 20 fields via Python path."""
        ...

    def test_fallback_warning_logged(self):
        """Warning logged at module level when Rust import fails."""
        ...

    def test_fallback_no_exceptions(self):
        """No exceptions raised during fallback operation."""
        ...
```

---

## Execution Pattern

1. **Wait**: LEAD confirms maturin build complete and `from gravitea_rust import validate_custom_fields` works
2. **T007**: Create `validation_engine.py` with `_USE_RUST` flag, threshold (>5), `validate_fields()`, `_validate_rust()`, `_validate_python()`, `_DecimalEncoder`
3. **T008**: Modify `customization.py` — replace validation loop (lines 80-91) with `from .validation_engine import validate_fields` + `errors = validate_fields(definitions, custom_data)`
4. **T009**: Add function stub to `gravitea_rust.pyi`
5. **T010**: Write US1 parity tests (all 6 field types valid + invalid)
6. **T011**: Write US1 benchmark test (25 fields < 2ms)
7. Run US1 tests:
   ```bash
   scripts/run-tests-external.sh -n "fields-025-us1" \
     tests/rust_integration/test_custom_fields_025.py -k "US1"
   ```
   Read `Docs/Tests/fields-025-us1.summary` — report to LEAD
8. **T012**: Write US2 edge case parity tests
9. **T013**: Write US2 select error format parity test
10. Run US2 tests:
    ```bash
    scripts/run-tests-external.sh -n "fields-025-us2" \
      tests/rust_integration/test_custom_fields_025.py -k "US2"
    ```
11. **T014**: Write US3 threshold guard tests
12. Run US3 tests:
    ```bash
    scripts/run-tests-external.sh -n "fields-025-us3" \
      tests/rust_integration/test_custom_fields_025.py -k "US3"
    ```
13. **T015**: Write US4 fallback tests
14. Run US4 tests:
    ```bash
    scripts/run-tests-external.sh -n "fields-025-us4" \
      tests/rust_integration/test_custom_fields_025.py -k "US4"
    ```
15. Run all SPEC-025 tests:
    ```bash
    scripts/run-tests-external.sh -n "fields-025-all" \
      tests/rust_integration/test_custom_fields_025.py
    ```

---

## Test Execution Commands

**ALL Python tests MUST use the external runner:**

```bash
# US1 tests
scripts/run-tests-external.sh -n "fields-025-us1" \
  tests/rust_integration/test_custom_fields_025.py -k "US1"

# US2 parity + edge case tests
scripts/run-tests-external.sh -n "fields-025-us2" \
  tests/rust_integration/test_custom_fields_025.py -k "US2"

# US3 threshold tests
scripts/run-tests-external.sh -n "fields-025-us3" \
  tests/rust_integration/test_custom_fields_025.py -k "US3"

# US4 fallback tests
scripts/run-tests-external.sh -n "fields-025-us4" \
  tests/rust_integration/test_custom_fields_025.py -k "US4"

# All SPEC-025 tests
scripts/run-tests-external.sh -n "fields-025-all" \
  tests/rust_integration/test_custom_fields_025.py
```

**Read ONLY `.summary` files — NEVER read `.log` files in full.**

All test output goes to `Docs/Tests/`.

---

## Completion Report

When all tasks are done, send this to LEAD:

```
QA COMPLETION REPORT — SPEC-025
=================================
Tasks completed: T007, T008, T009, T010, T011, T012, T013, T014, T015
Files created:
  - backend/apps/core/serializers/validation_engine.py
  - backend/tests/rust_integration/test_custom_fields_025.py
Files modified:
  - backend/apps/core/serializers/customization.py (validation loop → dispatcher call)
  - backend/gravitea_rust.pyi (+1 stub)
Test results:
  US1 (parity+benchmark): Docs/Tests/fields-025-us1.summary → {PASS/FAIL}
  US2 (edge cases+format): Docs/Tests/fields-025-us2.summary → {PASS/FAIL}
  US3 (threshold):         Docs/Tests/fields-025-us3.summary → {PASS/FAIL}
  US4 (fallback):          Docs/Tests/fields-025-us4.summary → {PASS/FAIL}
  All:                     Docs/Tests/fields-025-all.summary → {PASS/FAIL}
Total tests: {N} passing, {N} failing
Issues encountered: {list or "none"}
```
