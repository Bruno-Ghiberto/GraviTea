# Tasks: Custom Field Type Validator Acceleration

**Input**: Design documents from `/specs/025-rust-custom-field-validator/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

**Tests**: Tests ARE included — SC-003 requires ≥10 cargo tests + ≥15 pytest integration tests.

**Organization**: Tasks grouped by user story. US1 and US2 are P1 (co-priority — core acceleration and parity guarantee). US3 and US4 are P2 (threshold routing and fallback). Docker/regression is the final polish phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add error variant and module registration — prerequisites for all Rust code

- [X] T001 Add `ValidationFieldError(String)` variant to `rust/gravitea-core/src/errors.rs` mapping to `PyValueError`
- [X] T002 Register `mod validation;` in `rust/gravitea-core/src/lib.rs` and add `#[pymodule_export]` for `validate_custom_fields`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the Rust validation module with all 6 field type validators — blocks all user story testing

**⚠️ CRITICAL**: No user story tests can pass until this phase is complete

- [X] T003 Create `rust/gravitea-core/src/validation.rs` with `FieldDefinition` serde input struct (`field_key: String`, `field_type: String`, `choices: Option<Vec<String>>`) and `validate_custom_fields` PyO3 function signature accepting `defs_json: &str, data_json: &str` returning `PyResult<String>` (JSON dict of errors)
- [X] T004 Implement 6 field type validators in `rust/gravitea-core/src/validation.rs`: text (`Value::String`), integer (`Value::Number` with `as_i64()` + reject `Value::Bool`), decimal (`Value::Number` with `as_f64()` + reject `Value::Bool`), boolean (`Value::Bool` only), date (`Regex::new(r"^\d{4}-\d{2}-\d{2}$")` on `Value::String`), select (`HashSet` lookup on `Value::String`)
- [X] T005 Implement select error format in `rust/gravitea-core/src/validation.rs` using `format!("[{}]", choices.iter().map(|s| format!("'{}'", s)).collect::<Vec<_>>().join(", "))` to produce `['acero', 'aluminio', 'bronce']` with single quotes matching Python `str()` output
- [X] T006 Write ≥10 cargo tests in `rust/gravitea-core/src/validation.rs` (`#[cfg(test)] mod tests`) covering: each type valid/invalid, bool rejected for int/decimal, integer accepted for decimal, date format-only (accepts `2026-02-29`, rejects `not-a-date`), select error format with single quotes, null values skipped, undefined keys ignored, unknown field type passes, empty custom_data returns empty errors, empty definitions returns empty errors

**Checkpoint**: `cargo test validation` passes with ≥10 tests. Rust core is ready for Python integration.

---

## Phase 3: User Story 1 — Accelerated Batch Validation (Priority: P1) 🎯 MVP

**Goal**: Replace the type-checking loop in `customization.py:80-91` with a dispatcher that calls Rust for >5 fields

**Independent Test**: Submit 25 custom fields (all 6 types + select with 50 choices) → all validate correctly via Rust path, faster than Python

### Implementation for User Story 1

- [X] T007 [US1] Create `backend/apps/core/serializers/validation_engine.py` with: `_USE_RUST` flag via try/except import of `gravitea_rust.validate_custom_fields`, `_RUST_FIELD_THRESHOLD = 5`, `_DecimalEncoder(json.JSONEncoder)` with `default` method converting `Decimal` to `float`, `validate_fields(definitions, custom_data)` dispatcher function, `_validate_rust(definitions, custom_data)` calling `json.dumps` → Rust FFI → `json.loads`, `_validate_python(definitions, custom_data)` extracting the existing loop logic from `customization.py:80-91`
- [X] T008 [US1] Modify `backend/apps/core/serializers/customization.py` — replace lines 80-91 (the `errors = {}` / `for key, value in custom_data.items()` loop) with `from .validation_engine import validate_fields` and `errors = validate_fields(definitions, custom_data)`. Keep `_validate_field_value()` static method unchanged (FR-013). Keep required field checking (lines 93-102) and default injection (lines 104-107) unchanged (FR-014).
- [X] T009 [P] [US1] Update `backend/gravitea_rust.pyi` — add stub: `def validate_custom_fields(defs_json: str, data_json: str) -> str: ...`

### Tests for User Story 1

- [X] T010 [US1] Write parity tests in `backend/tests/rust_integration/test_custom_fields_025.py` — for all 6 field types (valid + invalid), verify Rust path and Python path produce identical error dicts. Use `validation_engine._validate_rust()` and `validation_engine._validate_python()` directly. Cover: text valid/invalid, integer valid/invalid/bool-rejected, decimal valid/invalid/bool-rejected/int-accepted, boolean valid/invalid, date valid/invalid/format-only, select valid/invalid/error-format
- [X] T011 [US1] Write benchmark test in `backend/tests/rust_integration/test_custom_fields_025.py` — 25 fields (all 6 types including select with 50 choices), assert Rust path completes in < 2ms (SC-001 proxy)

**Checkpoint**: Parity tests pass, benchmark passes. US1 is complete — Rust path validates all 6 types with identical output.

---

## Phase 4: User Story 2 — Output Parity Guarantee (Priority: P1)

**Goal**: Verify byte-identical error output between Rust and Python paths for all edge cases

**Independent Test**: Run same field definitions + custom data through both paths, compare character-by-character

### Tests for User Story 2

- [X] T012 [US2] Write edge case parity tests in `backend/tests/rust_integration/test_custom_fields_025.py` — null values skipped, undefined keys ignored, bool for integer rejected, bool for decimal rejected, `Decimal("9.99")` accepted for decimal, integer accepted for decimal, select with empty choices, select with null choices, empty custom_data, empty definitions, unknown field type passes silently
- [X] T013 [US2] Write select error format parity test in `backend/tests/rust_integration/test_custom_fields_025.py` — verify `Invalid choice. Allowed: ['acero', 'aluminio', 'bronce']` is byte-identical between Rust and Python paths (single quotes, comma-space separator, square brackets)

**Checkpoint**: All parity tests pass (SC-002: 0 parity differences). US2 confirms both paths are interchangeable.

---

## Phase 5: User Story 3 — Small Field Set Fallback (Priority: P2)

**Goal**: Verify threshold routing — ≤5 fields → Python path, >5 fields → Rust path

**Independent Test**: Submit with 3, 5, and 6 field definitions, verify correct path selection

### Tests for User Story 3

- [X] T014 [US3] Write threshold guard tests in `backend/tests/rust_integration/test_custom_fields_025.py` — mock or inspect to verify: 3 definitions → Python path used, 5 definitions → Python path used (threshold is >5, not >=5), 6 definitions → Rust path used. Use `unittest.mock.patch` on `validation_engine._validate_rust` and `validation_engine._validate_python` to verify routing.

**Checkpoint**: Threshold routing verified (SC-005). US3 confirms small tenants use Python, large tenants use Rust.

---

## Phase 6: User Story 4 — Graceful Degradation (Priority: P2)

**Goal**: Verify fallback when Rust module unavailable — Python path used with warning logged

**Independent Test**: Simulate import failure, submit 20 fields, verify correct output and warning

### Tests for User Story 4

- [X] T015 [US4] Write fallback tests in `backend/tests/rust_integration/test_custom_fields_025.py` — patch `validation_engine._USE_RUST = False`, verify: 20 fields validated correctly via Python path, warning logged at module level (check `logger.warning` was called or `_USE_RUST` is `False`), no exceptions raised

**Checkpoint**: Fallback verified (SC-006). US4 confirms production resilience without Rust module.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docker validation, regression testing, documentation

- [X] T016 Build Docker image: `docker compose build web` — Rust wheel compiles and installs successfully
- [X] T017 Docker import check: `from gravitea_rust import validate_custom_fields` — OK in container
- [X] T018 Run SPEC-025 tests in Docker: 31/31 passed in 0.38s — all pass
- [X] T019 Full regression: 131 passed, 0 failures in 36.55s — 0 new regressions (SC-004 PASS)
- [X] T020 Update `specs/025-rust-custom-field-validator/quickstart.md` with final test results and verification checklist status

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup (T001, T002) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (T003-T006) — core acceleration
- **US2 (Phase 4)**: Depends on US1 (T007-T008 must exist for parity testing)
- **US3 (Phase 5)**: Depends on US1 (T007 dispatcher must exist for threshold testing)
- **US4 (Phase 6)**: Depends on US1 (T007 dispatcher must exist for fallback testing)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 — implements core Rust path + dispatcher
- **US2 (P1)**: Depends on US1 — tests parity using dispatcher internals
- **US3 (P2)**: Depends on US1 — tests threshold routing in dispatcher
- **US4 (P2)**: Depends on US1 — tests fallback when Rust unavailable

### Within Each Phase

- T001 → T002 (error variant before module registration)
- T003 → T004 → T005 → T006 (struct → validators → select format → tests)
- T007 → T008 (dispatcher before customization.py modification)
- T009 can run parallel with T007-T008 (different file)
- T010, T011 after T008 (need dispatcher integrated)
- T012, T013, T014, T015 can run parallel after T010 (all in same test file but independent test classes)
- T016 → T017 → T018 → T019 → T020 (sequential Docker pipeline)

### Parallel Opportunities

- T009 (type stubs) ‖ T007-T008 (dispatcher + customization.py)
- T012-T015 (US2/US3/US4 tests) can run in parallel after US1 implementation
- Phase 2 Rust work (T003-T006) is independent of Python files

---

## Parallel Example: Phase 2 + US1

```bash
# Sequential (Rust core):
T003 → T004 → T005 → T006

# Then parallel (Python integration):
Agent A: T007 → T008 (dispatcher + customization.py modification)
Agent B: T009 (type stubs — different file, no dependency)

# Then US1 tests (after T008):
T010 → T011
```

## Parallel Example: US2/US3/US4 Tests

```bash
# After US1 complete (T007-T011), these can run in parallel:
Agent A: T012, T013 (US2 parity + edge cases)
Agent B: T014 (US3 threshold tests)
Agent C: T015 (US4 fallback tests)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T006)
3. Complete Phase 3: User Story 1 (T007-T011)
4. **STOP and VALIDATE**: `cargo test validation` + `test_custom_fields_025.py` parity + benchmark
5. Rust path works for all 6 types with correct error output

### Incremental Delivery

1. Setup + Foundational → Rust core ready
2. US1 → Accelerated validation works → Test parity + benchmark (MVP!)
3. US2 → Edge case parity verified → Confidence in production readiness
4. US3 → Threshold routing verified → Small tenants unaffected
5. US4 → Fallback verified → Production resilience confirmed
6. Polish → Docker + regression → Deployment ready

### Team Allocation

| Agent | Tasks | Model |
|-------|-------|-------|
| LEAD (Orchestrator) | T001, T002, T016-T020, coordination | Opus 4.6 |
| RUST-EXPERT | T003-T006 | Opus 4.6 |
| QA | T007-T015 | Sonnet 4.6 |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- `_validate_field_value()` MUST remain unchanged (FR-013) — backward compatibility
- Required field checking (lines 93-102) and default injection (lines 104-107) MUST NOT be modified (FR-014)
- All 69 existing tests MUST pass with zero modifications (SC-004)
- DATE_RE regex is format-only — no calendar/leap year validation (FR-009)
- Select error format uses single quotes: `['acero', 'aluminio', 'bronce']` (R-002)
- `_DecimalEncoder` converts `Decimal` → `float` before JSON serialization (R-003)
- Threshold is `>5` (not `>=5`) — 5 fields → Python, 6 fields → Rust (FR-011)
