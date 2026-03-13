# Research Log: Custom Field Type Validator Acceleration

**Feature Branch**: `025-rust-custom-field-validator`
**Date**: 2026-02-28
**Status**: All topics resolved

## R-001: DATE_RE Regex Parity (Rust `regex` vs Python `re`)

**Decision**: Rust `regex` crate pattern `^\d{4}-\d{2}-\d{2}$` is functionally equivalent to Python `re.compile(r"^\d{4}-\d{2}-\d{2}$")` for this use case.

**Rationale**:
- Both treat `\d` as Unicode digit class by default
- Both accept `2026-02-29` (format-only, no calendar validation)
- Both reject `2026-2-29` (missing leading zero) and `not-a-date`
- Rust `regex` uses `is_match()` which maps to Python `re.match()` + `$` anchor behavior
- No edge case divergence found for the YYYY-MM-DD pattern

**Alternatives considered**:
- ASCII-only `[0-9]` instead of `\d` — unnecessary since field values come from JSON (ASCII digits only in practice)
- `chrono` crate for calendar validation — rejected per spec (FR-009: format-only validation)

## R-002: Select Error Format Single-Quote Parity

**Decision**: Use explicit `format!("'{}'", s)` with `.join(", ")` wrapped in `[]` to produce Python-style single-quoted list representation.

**Rationale**:
- Python produces `['acero', 'aluminio', 'bronce']` via `str(['acero', 'aluminio', 'bronce'])`
- Rust `Debug` trait on `Vec<String>` produces `["acero", "aluminio", "bronce"]` (double quotes) — NOT parity
- Explicit construction: `format!("[{}]", choices.iter().map(|s| format!("'{}'", s)).collect::<Vec<_>>().join(", "))` → `['acero', 'aluminio', 'bronce']`
- This matches the Python output byte-for-byte

**Alternatives considered**:
- Rust `Debug` trait — produces double quotes, fails parity
- Custom `Display` impl — unnecessary complexity for a single format string

## R-003: Decimal/Float JSON Serialization Parity

**Decision**: Python `_DecimalEncoder` converts `Decimal` → `float` before JSON serialization; Rust sees `f64` via `serde_json::Value::Number`. Parity is maintained.

**Rationale**:
- Python's `json.dumps(custom_data, cls=_DecimalEncoder)` converts `Decimal("9.99")` → `9.99` (float)
- `serde_json` deserializes JSON `9.99` as `Value::Number` with `as_f64()` → `Some(9.99)`
- The decimal validator checks `value.is_number()` (covers both `i64` and `f64`)
- Boolean exclusion: `serde_json` distinguishes `Value::Bool` from `Value::Number` — matches Python's `isinstance(v, bool)` guard
- Integer acceptance for decimal: JSON `5` → `Value::Number` with `as_f64()` → `Some(5.0)` — matches Python's `isinstance(v, (int, float, Decimal)) and not isinstance(v, bool)`

**Alternatives considered**:
- `rust_decimal` crate — unnecessary overhead; `f64` precision sufficient for type validation (not arithmetic)
- Passing Decimal as string — would require custom serde deserializer; `_DecimalEncoder` already converts to float

## R-004: Existing Test Coverage Mapping

**Decision**: 69 existing tests across 4 files must pass unchanged (SC-004). New tests target Rust-specific behavior and parity.

**Rationale**:
- `tests/core/test_customization.py` — 18 direct `_validate_field_value()` unit tests (text, integer, decimal, boolean, date, select valid/invalid)
- `tests/core/test_custom_fields_integration.py` — 28 integration tests via `serializer.validate()` (create/update flows)
- `tests/core/test_custom_fields_edge_cases.py` — 15 edge case tests (null values, missing keys, empty data, unknown types)
- `tests/core/test_custom_fields_serializer.py` — 8 serializer-level tests (required fields, defaults, merge)
- Total: 69 tests, all must pass with zero modifications
- `_validate_field_value()` is preserved as a static method for backward compatibility (FR-013)
- New tests go in `tests/rust_integration/test_custom_fields_025.py` — parity, threshold, fallback, benchmark

**Alternatives considered**:
- Modifying existing tests to use the new dispatcher — rejected per FR-015 and SC-004 (zero modifications)
- Consolidating test files — out of scope for SPEC-025

## R-005: ValidationFieldError Mapping (Pre-resolved)

**Decision**: `ValidationFieldError(String)` maps to `PyValueError`, not `PyRuntimeError`.

**Rationale**:
- Validation errors are value errors (bad input), not runtime errors (system failures)
- Matches Python's `ValueError` semantics for invalid data
- The Python dispatcher catches `ValueError` and converts to DRF `ValidationError`
- Previous specs used `PyRuntimeError` for system-level errors (CryptoError, ComputeError) — different semantics

## R-006: No Rust-Side Caching (Pre-resolved)

**Decision**: No Rust-side caching of field definitions. Python's 60-second TTL cache in `_get_field_definitions()` is sufficient.

**Rationale**:
- Field definitions are already cached by the Python-side `_get_field_definitions()` method with 60-second TTL
- Adding `once_cell`/`DashMap` in Rust would create a second cache layer with synchronization complexity
- The Rust function receives definitions as JSON on each call — stateless design
- Zero new Cargo dependencies required
- Simpler architecture, easier to reason about cache invalidation

**Alternatives considered**:
- `once_cell::sync::Lazy` + `DashMap` for Rust-side LRU — rejected (unnecessary complexity, extra dependency)
- Thread-local cache in Rust — rejected (PyO3 GIL interactions would complicate invalidation)
