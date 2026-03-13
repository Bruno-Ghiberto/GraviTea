# Speckit Context: Custom Field Validator — PLAN Phase (SPEC-025)

> **Phase**: PLAN — Design implementation plan, research decisions, task breakdown
> **Priority**: MEDIUM | **Wave**: 5 (after SPEC-024)
> **Produces**: `plan.md`, `research.md`, `quickstart.md`
> **Does NOT produce**: data-model.md, api-contract.md (pure computation, no persistence)
> **Depends on**: SPEC-017 (Rust Bootstrap) MUST be complete
> **Benefits from**: SPEC-023/024 (shares `serde`, `serde_json`, dispatcher pattern)

---

## Mission

Design the implementation plan for replacing the type validation loop in `CustomFieldsMixin.validate()` (lines 80-91 of `customization.py`) with a Rust/PyO3 single-pass validator. Follows established dispatcher pattern from SPEC-023 (`sync_engine.py`) and SPEC-024 (`caea_engine.py`). Zero new Cargo dependencies. No Rust-side caching.

**Scope boundary**: Rust replaces ONLY the type validation loop (the `for key, value in custom_data.items()` block). Required field checking, merge semantics, cache lookup, default injection, and `ValidationError` raising all remain in Python. The `_validate_field_value()` static method is preserved for backward compatibility.

## Team Architecture

| Agent | Subagent Type | Model | Role |
|-------|--------------|-------|------|
| ORCHESTRATOR (LEAD) | system-architect | Opus 4.6 | Coordinates, validates, documentation, T001/T002/T009/T016-T020 |
| RUST-EXPERT | general-purpose | Opus 4.6 | Implements validation.rs (T003-T006) |
| QA | quality-engineer | Sonnet 4.6 | Python integration (T007-T008), tests (T010-T015), type stubs |

**Note**: BACKEND-CODER agent is unnecessary per SPEC-024 lesson — QA handles Python dispatcher integration using established patterns.

### Sequential-Thinking MCP

- **NOT mandatory**: No caching architecture or novel patterns. Validation logic is a straightforward port of `_validate_field_value()` from Python to Rust.
- **Optional**: RUST-EXPERT may use for select error format parity reasoning.

## Architecture Decisions (FINAL — from instruction-specify.md)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Serialization | `serde_json` (already in Cargo.toml) | JSON boundary for field definitions + custom_data |
| Schema caching | **NONE in Rust** | Python-side 60s TTL cache sufficient; Rust-side would need `DashMap` for thread-safe per-tenant caching — over-engineering for sub-millisecond ops |
| Field types | 6: text, integer, decimal, boolean, date, select | Matches Python `FieldType` TextChoices |
| Select lookup | `HashSet<String>` per-call | O(1) vs O(n) for large choice lists |
| Date validation | Format-only regex `^\d{4}-\d{2}-\d{2}$` | Matches Python `DATE_RE` exactly — NO calendar/leap year validation |
| Error format | `HashMap<String, Vec<String>>` → JSON | Matches DRF serializer error structure `{"field_key": ["error msg"]}` |
| GIL handling | **NOT released** | Sub-millisecond for typical field counts; FFI overhead dominates |
| Threshold | >5 fields → Rust path | Below 5, FFI overhead (~15-30μs) negates validation gain |
| Cargo deps | **Zero new dependencies** | `serde`, `serde_json`, `regex` all already present |
| Error variant | `ValidationFieldError(String)` | New variant in `errors.rs`, maps to `PyValueError` (not `PyRuntimeError`) |

### Corrections from Original Draft

| Original Claim | Correction | Evidence |
|----------------|------------|----------|
| `once_cell 1.19` needed | **NOT needed** — no Rust-side caching | Python 60s TTL sufficient; Rust compilation per-call <1μs |
| "Schema compilation with caching" | **NOT cached** in Rust | Per-call HashSet construction is trivial; no DashMap needed |
| "Novel caching architecture" | **Standard dispatcher** | Same pattern as SPEC-023/024 — no novel patterns |
| BACKEND-CODER agent needed | **NOT needed** | QA handles Python dispatcher per SPEC-024 pattern |
| Modify `_validate_field_value()` | **Modify the loop in `validate()`** | The static method is preserved; the calling loop at lines 80-91 is replaced |
| R-001 once_cell vs LazyLock | **Irrelevant** | No Rust-side caching needed |
| R-002 Cache invalidation | **Irrelevant** | No Rust-side caching needed |

## Implementation Phases

### Phase 1: Setup (LEAD)
- **Risk**: LOW
- Tasks:
  1. Add `ValidationFieldError(String)` variant to `rust/gravitea-core/src/errors.rs` mapping to `PyValueError`
  2. Register `mod validation;` and `#[pymodule_export] use super::validation::validate_custom_fields;` in `rust/gravitea-core/src/lib.rs`

### Phase 2: Rust Core (RUST-EXPERT)
- **Risk**: MEDIUM (select error format parity requires careful string construction)
- **Depends on**: Phase 1 complete
- Tasks:
  1. Create `rust/gravitea-core/src/validation.rs` with `FieldDefinition` serde input struct
  2. Implement `validate_custom_fields(field_definitions_json: &str, custom_data_json: &str) -> PyResult<String>` with:
     - `HashMap<&str, &FieldDefinition>` lookup by field_key
     - Skip `Value::Null` values (defensive guard)
     - Skip undefined keys (not in definitions)
     - Validate each field type (6 validators)
     - Return `serde_json::to_string(&errors)?` (empty `{}` = valid)
  3. Implement all 6 field type validators:
     - `text`: `value.is_string()`
     - `integer`: `Value::Number(n) if n.is_i64()` (NOT `is_f64()`, NOT `is_boolean()`)
     - `decimal`: `Value::Number(_)` (any number, NOT `Value::Bool`)
     - `boolean`: `value.is_boolean()`
     - `date`: `value.as_str()` + `Regex::new(r"^\d{4}-\d{2}-\d{2}$")` — format-only, NO calendar validation
     - `select`: `HashSet<&str>` from `choices`, `value.as_str()` membership check; error must produce `['choice1', 'choice2']` with single quotes matching Python list repr
  4. Write ≥10 cargo tests covering: each field type valid/invalid, bool rejected for integer, bool rejected for decimal, int accepted for decimal, date format-only (accepts `2026-02-29`), select with large choice list, select error format with single quotes, empty custom_data, unknown field type passthrough, null value skip

**Checkpoint**: `cargo test` passes with ≥10 tests. Rust function ready for Python integration.

### Phase 3: Python Integration (QA)
- **Risk**: LOW (follows established pattern from SPEC-024)
- **Depends on**: Phase 2 complete (cargo test passes)
- Tasks:
  1. Create `backend/apps/core/serializers/validation_engine.py` with:
     - `_USE_RUST` flag (import guard)
     - `_RUST_FIELD_THRESHOLD = 5`
     - `validate_fields(definitions, custom_data)` dispatcher
     - `_validate_rust()` wrapper: serialize definitions to JSON (`[{field_key, field_type, choices}]`), filter nulls, serialize custom_data with `_DecimalEncoder`, call Rust FFI, deserialize result
     - `_validate_python()` fallback: extracted validation loop logic from `_validate_field_value()` (self-contained, no instance dependency)
  2. Modify `backend/apps/core/serializers/customization.py` `validate()` method:
     - Replace lines 80-91 (the validation loop) with `from .validation_engine import validate_fields` + `errors = validate_fields(definitions, custom_data)`
     - Keep `_validate_field_value()` static method unchanged (backward compatibility)
  3. Add `validate_custom_fields(field_definitions_json: str, custom_data_json: str) -> str` stub to `backend/gravitea_rust.pyi`

**Checkpoint**: Maturin develop + basic smoke test passes.

### Phase 4: Tests (QA)
- **Risk**: LOW
- **Depends on**: Phase 3 complete
- Tasks:
  1. Write parity tests in `backend/tests/rust_integration/test_custom_fields_025.py`:
     - All 6 field types: valid values → both paths return `{}`
     - All 6 field types: invalid values → both paths return identical error messages
     - Select error format: single-quoted list `['acero', 'aluminio']`
     - Bool rejected for integer field (both paths)
     - Bool rejected for decimal field (both paths)
     - Int accepted for decimal field (both paths)
     - Null values skipped (both paths)
     - Undefined keys ignored (both paths)
     - Unknown field type passes silently (both paths)
     - Empty custom_data → no errors (both paths)
     - Empty definitions list → no errors (both paths)
     - Select with empty choices → any value invalid (both paths)
     - Select with null choices → any value invalid (both paths)
     - Date "2026-02-29" accepted (format-only, both paths)
     - Date "not-a-date" rejected (both paths)
  2. Write threshold guard tests:
     - 3 definitions → Python path used
     - 5 definitions → Python path used (threshold is >5, not >=5)
     - 6 definitions → Rust path used
  3. Write fallback tests:
     - `_USE_RUST = False` → correct output for 20 fields
     - Warning logged at module initialization
     - No errors raised
  4. Write benchmark test:
     - 25 fields (mix of all 6 types, select with 50+ choices) completes in <2ms via Rust (SC-001)

**Checkpoint**: All pytest integration tests pass. SC-003 coverage met (≥10 cargo + ≥15 pytest).

### Phase 5: Docker + Regression (LEAD)
- **Risk**: LOW
- **Depends on**: Phase 4 complete
- Tasks:
  1. Docker build: `docker compose build web`
  2. Docker import check: `from gravitea_rust import validate_custom_fields` succeeds
  3. Run SPEC-025 tests inside Docker container
  4. Full regression test suite — 0 new failures (existing 40+ custom field tests MUST pass unchanged)
  5. Update `specs/025-rust-custom-field-validator/quickstart.md` with final results

## Research Topics (for research.md)

| ID | Topic | Decision Needed | Assigned To |
|----|-------|----------------|-------------|
| R-001 | DATE_RE regex: Rust `regex` crate vs Python `re` | Verify pattern `^\d{4}-\d{2}-\d{2}$` behaves identically | QA |
| R-002 | Select error format: single-quote list repr | How to produce `['acero', 'aluminio']` from Rust (Python list repr uses single quotes; Rust Debug uses double quotes) | RUST-EXPERT |
| R-003 | `_DecimalEncoder` for custom_data | Verify Decimal→float conversion preserves parity across FFI | QA |
| R-004 | Existing test files: which tests exercise the validation loop directly | Map test coverage to determine regression risk | QA |

**Pre-resolved topics** (from instruction-specify.md):
- ~~once_cell vs LazyLock~~ → NOT NEEDED (no Rust-side caching)
- ~~Cache invalidation strategy~~ → NOT NEEDED (no Rust-side caching)
- ~~HashSet vs BTreeSet~~ → HashSet (O(1), per-call construction is trivial)

## Crate Dependencies

| Crate | Version | New/Shared | Purpose |
|-------|---------|-----------|---------|
| `serde` | 1.0 | SHARED (SPEC-023+) | Deserialization of field definitions |
| `serde_json` | 1.0 | SHARED (SPEC-023+) | JSON parsing for field_defs + custom_data |
| `regex` | 1.10 | SHARED (SPEC-021) | Date format validation `^\d{4}-\d{2}-\d{2}$` |
| `pyo3` | 0.28 | SHARED (SPEC-017+) | Python FFI |
| `thiserror` | 2.0 | SHARED (SPEC-017+) | Error variant definition |

**Zero new dependencies.** All crates already in `Cargo.toml`.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────┐
│ CustomFieldsMixin.validate()                         │
│                                                      │
│  definitions = self._get_field_definitions(...)      │
│  custom_data = data.get("custom_data", {})           │
│                    │                                 │
│                    ▼                                 │
│  ┌────────────────────────────────────┐              │
│  │ validation_engine.validate_fields()│              │
│  │                                    │              │
│  │  len(definitions) > 5             │              │
│  │  AND _USE_RUST?                   │              │
│  │     ├── YES → _validate_rust()    │              │
│  │     │    json.dumps → Rust FFI    │              │
│  │     │    → json.loads → errors    │              │
│  │     └── NO  → _validate_python()  │              │
│  │          (extracted loop logic)    │              │
│  └────────────────────────────────────┘              │
│                    │                                 │
│                    ▼                                 │
│  if errors:                                          │
│    raise ValidationError({"custom_data": errors})    │
│                                                      │
│  # Required field checking (unchanged, stays here)   │
│  # Default value injection (unchanged, stays here)   │
└──────────────────────────────────────────────────────┘
```

## Project Structure

### Documentation (this feature)

```text
specs/025-rust-custom-field-validator/
├── spec.md              # Feature specification (15 FRs, 6 SCs)
├── plan.md              # Generated from this context
├── research.md          # Phase 0 output — decisions resolved
├── quickstart.md        # Developer setup guide
└── checklists/
    └── requirements.md  # Quality checklist (16/16 passing)
```

### Source Code (repository root)

```text
rust/gravitea-core/src/
├── lib.rs               # MODIFIED — +mod validation, +1 pymodule_export
├── errors.rs            # MODIFIED — +ValidationFieldError variant → PyValueError
└── validation.rs        # NEW — validate_custom_fields (~200-300 lines)

backend/apps/core/serializers/
├── customization.py     # MODIFIED — replace validation loop with dispatcher call
└── validation_engine.py # NEW — dispatcher (Rust/Python fallback, ~80-100 lines)

backend/gravitea_rust.pyi  # MODIFIED — +1 function stub

backend/tests/rust_integration/
└── test_custom_fields_025.py  # NEW — parity, threshold, fallback, benchmark tests
```

**Structure Decision**: Follows established pattern from SPEC-018 through SPEC-024. Rust source in `rust/gravitea-core/src/`, Python dispatcher in the same package as the target file (`serializers/`), integration tests in `tests/rust_integration/`.

## Critical Path

```
Phase 1: T001 → T002 (Setup — LEAD)
                ↓
Phase 2: T003 → T004 → T005 → T006 (Rust core — RUST-EXPERT)
                                ↓
Phase 3: T007 → T008 → T009 (Python integration — QA)
                         ↓
Phase 4: T010 → T011 → T012 → T013 (Tests — QA)
                                ↓
Phase 5: T014 → T015 → T016 → T017 → T018 (Docker + regression — LEAD)
```

**Parallelization opportunities**:
- T009 (type stubs) can run parallel with T007-T008 (different file)
- T011 (threshold tests) + T012 (fallback tests) can run parallel with T010 (parity tests complete first)
- Phase 2 (Rust core) and T009 (type stubs) can overlap with different agents

## Team Allocation

| Agent | Tasks | Model |
|-------|-------|-------|
| LEAD (ORCHESTRATOR) | T001, T002, T014-T018, coordination | Opus 4.6 |
| RUST-EXPERT | T003-T006 | Opus 4.6 |
| QA | T007-T013 | Sonnet 4.6 |

## Testing Standards

1. **Rust-native**: ≥10 cargo tests — each field type (valid + invalid), bool/int/decimal edge cases, date format-only, select error format with single quotes, empty/null cases, unknown type passthrough
2. **Python parity**: ≥15 pytest tests — Rust vs Python produce identical output for all field types and edge cases
3. **Threshold**: 3 tests — correct routing for field counts 3, 5, and 6
4. **Fallback**: 3 tests — correct output when `_USE_RUST = False`, warning logged, no errors
5. **Benchmark**: 1 test — 25 fields with all types and 50+ select choices completes in <2ms
6. **Regression**: Full suite 0 new failures; existing 40+ custom field tests pass unchanged

## Critical Caveats (from instruction-specify.md)

1. **Python `DATE_RE` is format-only**: `re.compile(r"^\d{4}-\d{2}-\d{2}$")`. Rust must use `regex::Regex` with the same pattern. Both accept `2026-02-29`. Do NOT add leap year validation.

2. **Select error format parity**: Python produces `f"Invalid choice. Allowed: {allowed}"` which renders as `"Invalid choice. Allowed: ['acero', 'aluminio']"` (Python list repr with single quotes). Rust must produce the same string format. Use explicit string building, NOT Rust's `Debug` trait (which uses double quotes).

3. **Decimal in custom_data**: `json.dumps(Decimal("9.99"))` raises `TypeError`. The dispatcher's `_DecimalEncoder` converts to `float`. Rust sees `9.99` as `f64`, valid for decimal fields.

4. **Integer vs float in JSON**: `json.dumps(5)` → `5` (serde: `i64`), `json.dumps(5.0)` → `5.0` (serde: `f64`). For integer fields, Rust must check `n.is_i64()`. Value `5.0` must FAIL integer validation.

5. **Null values filtered pre-FFI**: Dispatcher filters `None` values before `json.dumps()`. Rust should still guard against `Value::Null` defensively.

6. **Undefined keys silently ignored**: Keys in `custom_data` not in `definitions` are NOT errors.

7. **`_validate_field_value()` backward compat**: Static method remains. Direct callers (unit tests) continue to work. Only the loop in `validate()` changes.

8. **Required field checking stays in Python**: Lines 100-102 use `check_data` with merged existing data from `self.instance`. This ORM context stays in Python.

## FFI Boundary Analysis

| Input | Typical Size | FFI Overhead | Python Work | Rust Work | Net Gain |
|-------|-------------|-------------|-------------|-----------|----------|
| 5 fields, no select | ~0.5KB x 2 | ~15-30μs | ~15-50μs | ~2-5μs | **~0μs** (threshold guard) |
| 20 fields, 2 selects | ~3KB x 2 | ~15-30μs | ~50-200μs | ~5-20μs | **+15-150μs** |
| 50 fields, 10 selects (50 choices) | ~15KB x 2 | ~20-40μs | ~200-800μs | ~10-40μs | **+150-720μs** |

## Blast Radius (from GitNexus — instruction-specify.md)

**Impact**: HIGH (5 production serializers, 3 modules) — but **contained** because the change is internal to the validation loop, not the mixin interface.

### Direct Dependents (depth=1, EXTENDS)

| Serializer | Module | File |
|------------|--------|------|
| `CustomerSerializer` | ventas | `backend/apps/ventas/serializers.py` |
| `SaleOrderSerializer` | ventas | `backend/apps/ventas/serializers.py` |
| `ProductCreateSerializer` | inventario | `backend/apps/inventario/serializers.py` |
| `SupplierCreateSerializer` | compras | `backend/apps/compras/serializers.py` |
| `PurchaseOrderSerializer` | compras | `backend/apps/compras/serializers.py` |

### Existing Test Coverage (40+ tests across 4 files)

| Test File | Tests | Scope |
|-----------|-------|-------|
| `tests/core/test_custom_fields_mixin.py` | ~30 | Unit + integration: all 6 types, merge, defaults, cache, required |
| `tests/core/test_cross_entity_validation.py` | ~10 | Cross-entity isolation, cache key scoping, MRO chain |
| `tests/integration/test_custom_fields_e2e.py` | ~5 | End-to-end with API client |
| `tests/compras/test_custom_fields.py` | ~10 | Supplier/PurchaseOrder custom fields |

## Reference Documents

| Document | Purpose | Path |
|----------|---------|------|
| Specify context (solidified) | Architecture decisions, caveats, pseudocode | `Docs/Temp-prompting/025/instruction-specify.md` |
| Feature spec | User stories, FRs, SCs, edge cases | `specs/025-rust-custom-field-validator/spec.md` |
| SPEC-024 plan (reference format) | Established plan template | `specs/024-rust-arca-batch/plan.md` |
| SPEC-024 tasks (reference format) | Established tasks template | `specs/024-rust-arca-batch/tasks.md` |
| Current mixin | Python implementation | `backend/apps/core/serializers/customization.py` |
| SPEC-024 dispatcher | Pattern to follow | `backend/apps/facturacion/arca/caea_engine.py` |
| SPEC-023 dispatcher | Pattern to follow | `backend/apps/sync/sync_engine.py` |
| Roadmap | OPP-009 details | `Docs/Brainstorming/rust-pyo3-speckit-roadmap.md` §11 |
| Tenant customization | Feature spec | `specs/014-tenant-customization/spec.md` |
