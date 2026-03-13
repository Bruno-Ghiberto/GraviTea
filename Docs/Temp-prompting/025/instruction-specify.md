# Speckit Context: Custom Field Validator (SPEC-025)

> **Phase**: SPECIFY — Define what we're accelerating and why
> **Priority**: MEDIUM | **Wave**: 5
> **Depends on**: SPEC-017 (Rust Toolchain Bootstrap) MUST be complete
> **Benefits from**: SPEC-023/024 (shares `serde`, `serde_json`, dispatcher pattern)

---

## Mission Statement

Replace the `_validate_field_value()` type-checking loop (lines 81-91) in `backend/apps/core/serializers/customization.py` with a Rust/PyO3 validator that receives field definitions + custom_data as JSON, validates all fields in a single pass, and returns errors in DRF-compatible format.

**Scope boundary**: Rust replaces ONLY the type validation loop. Required field checking, merge semantics, cache lookup, default injection, and `ValidationError` raising all remain in Python.

## Why This Matters Now

- **2-4x for 20+ fields**: Each field does isinstance + regex + list membership in Python
- **HashSet for select validation**: O(1) vs Python's O(n) list membership — significant for 50+ choices
- **Single FFI call**: One JSON-in/JSON-out call replaces N Python `_validate_field_value()` calls
- **Consistency**: Follows established dispatcher pattern from SPEC-023 (`sync_engine.py`) and SPEC-024 (`caea_engine.py`)

## Blast Radius Analysis (from GitNexus)

**Impact**: HIGH (5 production serializers, 3 modules) — but **contained** because the change is internal to the validation loop, not the mixin interface.

### Direct Dependents (depth=1, EXTENDS)

| Serializer | Module | File |
|------------|--------|------|
| `CustomerSerializer` | ventas | `backend/apps/ventas/serializers.py` |
| `SaleOrderSerializer` | ventas | `backend/apps/ventas/serializers.py` |
| `ProductCreateSerializer` | inventario | `backend/apps/inventario/serializers.py` |
| `SupplierCreateSerializer` | compras | `backend/apps/compras/serializers.py` |
| `PurchaseOrderSerializer` | compras | `backend/apps/compras/serializers.py` |

### Indirect Dependents (depth=2)

| Symbol | File | Relation |
|--------|------|----------|
| `SaleOrderDetailSerializer` | `ventas/serializers.py` | EXTENDS SaleOrderSerializer |
| `confirm()` | `compras/views.py` | CALLS PurchaseOrderSerializer |
| `cancel()` | `compras/views.py` | CALLS PurchaseOrderSerializer |
| `schema.py` | `ventas/schema.py` | CALLS SaleOrderSerializer |

### Existing Test Coverage (40+ tests across 4 files)

| Test File | Tests | Scope |
|-----------|-------|-------|
| `tests/core/test_custom_fields_mixin.py` | ~30 | Unit + integration: all 6 types, merge, defaults, cache, required |
| `tests/core/test_cross_entity_validation.py` | ~10 | Cross-entity isolation, cache key scoping, MRO chain |
| `tests/integration/test_custom_fields_e2e.py` | ~5 | End-to-end with API client |
| `tests/compras/test_custom_fields.py` | ~10 | Supplier/PurchaseOrder custom fields |

**Safety net**: Existing tests validate Python behavior. SPEC-025 parity tests in `tests/rust_integration/` will verify Rust matches Python exactly.

## Architecture Decisions (FINAL — Do Not Re-Debate)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Serialization | `serde_json` (already in Cargo.toml) | JSON boundary for field definitions + custom_data |
| Schema caching | **NONE in Rust** | Python-side 60s TTL cache is sufficient; Rust-side would need `DashMap` for thread-safe per-tenant caching — adds complexity without meaningful gain for sub-millisecond operations |
| Field types | 6: text, integer, decimal, boolean, date, select | Matches Python `FieldType` TextChoices exactly |
| Select lookup | `HashSet<String>` per-call | O(1) vs O(n) for large choice lists; compiled fresh each call (fast enough) |
| Date validation | **Format-only regex** `^\d{4}-\d{2}-\d{2}$` | Matches Python `DATE_RE` exactly — NO calendar/leap year validation (Python doesn't do it either) |
| Error format | `HashMap<String, Vec<String>>` → JSON | Matches DRF serializer error structure `{"field_key": ["error msg"]}` |
| GIL handling | **NOT released** | Sub-millisecond for typical field counts; FFI overhead dominates |
| Threshold | >5 fields → Rust path | Below 5, FFI overhead (~15-30μs) negates validation gain |
| Cargo deps | **Zero new dependencies** | `serde`, `serde_json`, `regex` all already present |
| Error variant | `ValidationFieldError(String)` | New variant in `errors.rs`, maps to `PyValueError` (not `PyRuntimeError`) |

### Corrections from Original Draft

| Original Claim | Correction | Evidence |
|----------------|------------|----------|
| `once_cell 1.19` needed | **NOT needed** — no Rust-side caching | Python 60s TTL sufficient; Rust compilation per-call is <1μs for typical schemas |
| Date regex tests leap years | **NO** — Python `DATE_RE` is format-only | `re.compile(r"^\d{4}-\d{2}-\d{2}$")` at `customization.py:16` accepts `2026-02-29` |
| Schema compilation cached | **NOT cached** in Rust | Per-call HashSet construction is trivial; DashMap would be over-engineering |

## Current State (What Exists Today)

| Item | Details |
|------|---------|
| **File** | `backend/apps/core/serializers/customization.py` |
| **Target function** | `_validate_field_value()` static method (lines 109-134) |
| **Call site** | `validate()` method loop (lines 81-91) |
| **Loop pattern** | `for key, value in custom_data.items(): err = self._validate_field_value(defn, value)` |
| **Null handling** | `if value is None: continue` (null = remove key in merge semantics) |
| **Undefined keys** | Silently ignored (not in `defined_keys` dict) |
| **Error collection** | `errors[key] = [err]` → `raise serializers.ValidationError({"custom_data": errors})` |
| **Call frequency** | Per request, per custom field (scales with tenant customization adoption) |
| **Current cost** | ~50-200μs for 20 fields (isinstance + regex + list membership) |
| **Cache** | Python-side 60s TTL per `TenantFieldDefinition` queryset |

### Python Type Semantics (Critical for Parity)

The `_validate_field_value()` function uses Python `isinstance()` checks with specific bool/int handling:

```python
# integer: rejects bool (bool IS subclass of int in Python)
if not isinstance(value, int) or isinstance(value, bool):

# decimal: rejects bool, accepts int/float/Decimal
if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):

# boolean: only accepts bool
if not isinstance(value, bool):
```

In JSON (`serde_json::Value`), `Bool` and `Number` are distinct variants, so Rust naturally enforces the bool/int distinction. No special handling needed.

### JSON Boundary Type Mapping

Since `custom_data` originates from HTTP request JSON (parsed by DRF), values crossing the FFI boundary via `json.dumps()` will be:

| Python Type | JSON | serde_json::Value | Notes |
|-------------|------|-------------------|-------|
| `str` | `"hello"` | `Value::String` | |
| `int` | `5` | `Value::Number(i64)` | `n.is_i64() == true` |
| `float` | `3.14` | `Value::Number(f64)` | `n.is_f64() == true` |
| `bool` | `true` | `Value::Bool` | Distinct from Number |
| `None` | `null` | `Value::Null` | Skipped before Rust call |
| `Decimal` | N/A | N/A | `json.dumps` fails — use `default=str` in dispatcher |

## Target Architecture

### New Rust Source

```
rust/gravitea-core/src/
├── lib.rs              # Add: mod validation; + #[pymodule_export]
├── errors.rs           # Add: ValidationFieldError(String) variant → PyValueError
└── validation.rs       # NEW — validate_custom_fields (~200-300 lines)
```

### New Python Source

```
backend/apps/core/serializers/
├── customization.py    # MODIFY: import from validation_engine, call in validate()
└── validation_engine.py  # NEW — dispatcher (Rust/Python fallback, ~80 lines)
```

### Functions to Implement

| Function | Signature | Notes |
|----------|-----------|-------|
| `validate_custom_fields` | `(field_definitions_json: &str, custom_data_json: &str) -> PyResult<String>` | Returns JSON: `{}` = valid, `{"field": ["error"]}` = errors |

### Input: `field_definitions_json`

JSON array of objects. Only the fields needed for validation are serialized (not the full ORM model):

```json
[
  {"field_key": "color", "field_type": "text", "choices": null},
  {"field_key": "weight_kg", "field_type": "integer", "choices": null},
  {"field_key": "material", "field_type": "select", "choices": ["acero", "aluminio", "bronce"]},
  {"field_key": "expiry", "field_type": "date", "choices": null}
]
```

### Input: `custom_data_json`

JSON object of the custom_data dict. Null values already filtered out by Python before calling Rust:

```json
{"color": "red", "weight_kg": 5, "material": "acero", "expiry": "2024-12-31"}
```

### Output

JSON string. Empty object `{}` means all valid. Non-empty means errors:

```json
{"color": ["Expected a text value."], "weight_kg": ["Expected an integer value."]}
```

### Error Messages (Must Match Python Exactly)

| Field Type | Error Message |
|------------|---------------|
| text | `"Expected a text value."` |
| integer | `"Expected an integer value."` |
| decimal | `"Expected a decimal value."` |
| boolean | `"Expected a boolean value."` |
| date | `"Expected a date in YYYY-MM-DD format."` |
| select | `"Invalid choice. Allowed: [\"acero\", \"aluminio\"]"` |

**Note on select error**: The Python code uses `f"Invalid choice. Allowed: {allowed}"` which produces Python list repr (with single quotes). The Rust implementation should match this exact format using `format!("Invalid choice. Allowed: {:?}", choices_vec)` or construct the string to match Python's `['acero', 'aluminio']` output.

### Serde Structs

```rust
#[derive(Deserialize)]
struct FieldDefinition {
    field_key: String,
    field_type: String,
    choices: Option<Vec<String>>,
}
```

No output serde structs needed — build the error HashMap and serialize with `serde_json::to_string()`.

### Validation Logic (Pseudocode)

```rust
fn validate_custom_fields(field_defs_json: &str, custom_data_json: &str) -> PyResult<String> {
    let definitions: Vec<FieldDefinition> = serde_json::from_str(field_defs_json)?;
    let custom_data: HashMap<String, Value> = serde_json::from_str(custom_data_json)?;

    // Build lookup: field_key → definition
    let defined: HashMap<&str, &FieldDefinition> = definitions.iter()
        .map(|d| (d.field_key.as_str(), d))
        .collect();

    let mut errors: HashMap<String, Vec<String>> = HashMap::new();

    for (key, value) in &custom_data {
        // Skip null values (Python filters these, but guard anyway)
        if value.is_null() { continue; }

        // Skip undefined keys (not in definitions)
        let Some(defn) = defined.get(key.as_str()) else { continue; };

        // Validate type
        if let Some(err) = validate_field_value(defn, value) {
            errors.insert(key.clone(), vec![err]);
        }
    }

    Ok(serde_json::to_string(&errors)?)
}

fn validate_field_value(defn: &FieldDefinition, value: &Value) -> Option<String> {
    match defn.field_type.as_str() {
        "text" => if !value.is_string() { Some("Expected a text value.".into()) } else { None },
        "integer" => {
            match value {
                Value::Number(n) if n.is_i64() => None,
                _ => Some("Expected an integer value.".into()),
            }
        },
        "decimal" => {
            match value {
                Value::Number(_) => None,
                _ => Some("Expected a decimal value.".into()),
            }
        },
        "boolean" => if !value.is_boolean() { Some("Expected a boolean value.".into()) } else { None },
        "date" => {
            match value.as_str() {
                Some(s) if DATE_RE.is_match(s) => None,
                _ => Some("Expected a date in YYYY-MM-DD format.".into()),
            }
        },
        "select" => {
            let choices: HashSet<&str> = defn.choices.as_ref()
                .map(|c| c.iter().map(|s| s.as_str()).collect())
                .unwrap_or_default();
            match value.as_str() {
                Some(s) if choices.contains(s) => None,
                _ => {
                    let allowed = defn.choices.as_ref().map(|c| format!("{:?}", c)).unwrap_or_else(|| "[]".into());
                    Some(format!("Invalid choice. Allowed: {}", allowed))
                }
            }
        },
        _ => None, // Unknown field types silently pass (match Python behavior)
    }
}
```

### Dispatcher Pattern (`validation_engine.py`)

Follow established pattern from `caea_engine.py` (SPEC-024):

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
    # Filter null values before crossing FFI (match Python skip behavior)
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

### Integration Point (`customization.py` Modification)

Replace lines 77-91 in `validate()` method:

```python
# BEFORE (lines 77-91):
errors = {}
defined_keys = {d.field_key: d for d in definitions}
for key, value in custom_data.items():
    if value is None:
        continue
    defn = defined_keys.get(key)
    if defn is None:
        continue
    err = self._validate_field_value(defn, value)
    if err:
        errors[key] = [err]

# AFTER:
from .validation_engine import validate_fields
errors = validate_fields(definitions, custom_data)
```

The `_validate_field_value()` static method remains for backward compatibility but is no longer called by the mixin's `validate()` method.

## FFI Boundary Analysis

| Input | Typical Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|-------------|-------------|-------------|-----------|----------|
| 5 fields, no select | ~0.5KB × 2 | ~15-30μs | ~15-50μs | ~2-5μs | **~0μs** (threshold guard) |
| 20 fields, 2 selects | ~3KB × 2 | ~15-30μs | ~50-200μs | ~5-20μs | **+15-150μs** |
| 50 fields, 10 selects (50 choices each) | ~15KB × 2 | ~20-40μs | ~200-800μs | ~10-40μs | **+150-720μs** |

## Critical Caveats

1. **Python `DATE_RE` is format-only**: `re.compile(r"^\d{4}-\d{2}-\d{2}$")`. Rust must use `regex::Regex` with the same pattern. Both accept `2026-02-29` (invalid calendar date). Do NOT add leap year validation — it would break parity.

2. **Select error format parity**: Python produces `f"Invalid choice. Allowed: {allowed}"` which renders as `"Invalid choice. Allowed: ['acero', 'aluminio']"` (Python list repr with single quotes). Rust must produce the same string format. Use explicit string building, NOT Rust's `Debug` trait (which uses double quotes).

3. **Decimal in custom_data**: `json.dumps(Decimal("9.99"))` raises `TypeError`. The dispatcher's `_DecimalEncoder` converts to `float`. This means Rust sees `9.99` as `f64`, which is valid for decimal fields. Parity with Python's `isinstance(value, Decimal)` check is maintained because Decimal→float→Number in serde.

4. **Integer vs float in JSON**: Python `json.dumps(5)` → `5` (serde: `i64`), `json.dumps(5.0)` → `5.0` (serde: `f64`). For integer fields, Rust must check `n.is_i64()` to match Python's `isinstance(value, int)`. Value `5.0` must FAIL integer validation (it's a float in JSON).

5. **Null values filtered pre-FFI**: The dispatcher filters `None` values before `json.dumps()`. Rust's validation loop should still guard against `Value::Null` defensively.

6. **Undefined keys silently ignored**: Keys in `custom_data` not present in `definitions` are NOT errors. Both Python and Rust skip them.

7. **`_validate_field_value()` backward compat**: The static method remains on the class. Direct callers (unit tests call it) continue to work. Only the internal loop in `validate()` changes.

8. **Required field checking stays in Python**: The required field check (lines 100-102) uses `check_data` which may include merged existing data from `self.instance`. This merge logic requires ORM context and stays in Python.

## Success Criteria

1. `cargo test` passes with ≥10 validation tests (each field type × valid/invalid + edge cases + error format)
2. All 6 field types validate identically to Python implementation (parity tests)
3. Date validation uses format-only regex matching Python `DATE_RE` exactly
4. Select validation uses `HashSet` (O(1) for large choice lists)
5. Select error format matches Python's list repr with single quotes
6. Error format matches DRF serializer expectations: `{"field_key": ["error msg"]}`
7. Threshold guard: ≤5 definition fields → Python path, >5 → Rust path
8. Fallback works without Rust extension (warning logged)
9. `_validate_field_value()` static method preserved for backward compatibility
10. Docker builds with validation function available
11. Full test suite passes with 0 new regressions
12. Existing 40+ custom field tests continue to pass unchanged

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Roadmap | OPP-009 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §11 |
| Acceleration opps | Deep analysis | `Docs/Brainstorming/rust-acceleration-opportunities.md` |
| Current mixin | Python implementation | `backend/apps/core/serializers/customization.py` |
| Model definition | TenantFieldDefinition ORM model | `backend/apps/core/models/customization.py` |
| Tenant customization spec | Full feature spec | `specs/014-tenant-customization/spec.md` |
| Unit tests | Existing validation coverage | `backend/tests/core/test_custom_fields_mixin.py` |
| Cross-entity tests | Entity isolation tests | `backend/tests/core/test_cross_entity_validation.py` |
| E2E tests | Integration tests | `backend/tests/integration/test_custom_fields_e2e.py` |
| SPEC-024 dispatcher | Pattern to follow | `backend/apps/facturacion/arca/caea_engine.py` |
| SPEC-023 dispatcher | Pattern to follow | `backend/apps/sync/sync_engine.py` |
