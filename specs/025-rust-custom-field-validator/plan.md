# Implementation Plan: Custom Field Type Validator Acceleration

**Branch**: `025-rust-custom-field-validator` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/025-rust-custom-field-validator/spec.md`

## Summary

Replace the type validation loop in `CustomFieldsMixin.validate()` (lines 80-91 of `customization.py`) with a Rust/PyO3 single-pass validator that receives field definitions + custom_data as JSON, validates all 6 field types, and returns errors in DRF-compatible format. Dispatches to Rust when field definition count >5; falls back to Python otherwise. Zero new Cargo dependencies.

## Technical Context

**Language/Version**: Rust 1.93.1 (PyO3 0.28, Maturin 1.12.4) + Python 3.14.3 (Django 5.2.x)
**Primary Dependencies**: `serde 1.0`, `serde_json 1.0`, `regex 1.10`, `pyo3 0.28`, `thiserror 2.0` (all already in Cargo.toml)
**Storage**: N/A — pure computation, no persistence
**Testing**: `cargo test` (Rust-native) + `pytest` (Python integration) via external test runner
**Target Platform**: Linux (WSL2 development, Docker production)
**Project Type**: Library extension (PyO3 shared library `gravitea_rust`)
**Performance Goals**: 20+ custom fields validated at least 2x faster via Rust path (SC-001)
**Constraints**: Both validation paths must produce byte-identical error output for any input (parity guarantee)
**Scale/Scope**: 5-50 custom fields per tenant per entity type; 5 production serializers across 3 modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | N/A | No database changes — pure computation |
| II. Multi-Tenant Isolation | N/A | No tenant data access — validation logic operates on pre-fetched, pre-scoped definitions |
| III. Modular Django Architecture | PASS | Changes within `core` module boundaries; dispatcher in same package as target file |
| IV. Application-Level Encryption | N/A | No PII handling in field type validation |
| V. Secure Authentication | N/A | No auth changes |
| VI. Fiscal Compliance (ARCA) | N/A | No fiscal integration |
| VII. Offline-First | N/A | No sync changes |
| VIII. Query Optimization | N/A | No database queries (definitions already cached by Python-side 60s TTL) |
| IX. Secure Data Operations | N/A | No model mutations |
| X. Test-Driven Development | PASS | ≥10 cargo tests + ≥15 pytest tests planned (SC-003); existing 40+ tests must pass unchanged (SC-004) |
| XI-XIV | N/A | No auth/pagination/API changes |

**Gate result**: PASS — no violations, no complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/025-rust-custom-field-validator/
├── spec.md              # Feature specification (15 FRs, 6 SCs)
├── plan.md              # This file
├── research.md          # Phase 0 output — all decisions resolved
├── quickstart.md        # Phase 1 output — developer setup guide
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
├── customization.py     # MODIFIED — replace validation loop (lines 80-91) with dispatcher call
└── validation_engine.py # NEW — dispatcher (Rust/Python fallback, ~80-100 lines)

backend/gravitea_rust.pyi  # MODIFIED — +1 function stub

backend/tests/rust_integration/
└── test_custom_fields_025.py  # NEW — parity, threshold, fallback, benchmark tests
```

**Structure Decision**: Follows established pattern from SPEC-018 through SPEC-024. Rust source in `rust/gravitea-core/src/`, Python dispatcher in the same package as the target file (`serializers/`), integration tests in `tests/rust_integration/`.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.

## Phase 0: Research

All research topics were resolved during the specify and plan phases via source code analysis, GitNexus blast radius checks, and targeted investigations. See [research.md](research.md) for the complete decision log.

**Key decisions**:
- Zero new Cargo dependencies (serde, serde_json, regex all already present)
- No Rust-side caching (Python 60s TTL sufficient)
- Date validation is format-only regex (matches Python `DATE_RE` exactly)
- Select error format uses explicit single-quote string construction (not Rust `Debug` trait)
- `ValidationFieldError` maps to `PyValueError` (not `PyRuntimeError`)

## Phase 1: Design

### Data Model

No data model changes. This feature is a pure computation acceleration — no new database tables, no model changes, no migrations. The input is pre-fetched `TenantFieldDefinition` ORM objects (cached by Python-side 60s TTL); the output is a dict of error messages.

Input/output contracts and Rust pseudocode are fully specified in `Docs/Temp-prompting/025/instruction-specify.md`.

### Contracts

No new external interfaces. The Rust function is internal to the `core/serializers` module. The error format is dictated by DRF's `ValidationError` structure — the Rust function must produce the same `{"field_key": ["error msg"]}` dict that the existing Python loop produces. This is verified by parity tests.

### Architecture

```
┌──────────────────────────────────────────────────────┐
│ CustomFieldsMixin.validate()                         │
│                                                      │
│  definitions = self._get_field_definitions(...)      │
│  custom_data = attrs.get("custom_data", {})          │
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

### Implementation Phases

#### Phase 1: Setup (LEAD)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T001 | Add `ValidationFieldError(String)` variant to `errors.rs` mapping to `PyValueError` | LOW | — |
| T002 | Register `mod validation;` + `#[pymodule_export]` in `lib.rs` | LOW | T001 |

#### Phase 2: Rust Core (RUST-EXPERT)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T003 | Create `validation.rs` with `FieldDefinition` serde input struct + `validate_custom_fields` PyO3 function | MEDIUM | T002 |
| T004 | Implement 6 field type validators (text, integer, decimal, boolean, date, select) with exact error messages | MEDIUM | T003 |
| T005 | Implement select error format with single-quote Python list repr parity | MEDIUM | T004 |
| T006 | Write ≥10 cargo tests (each type valid/invalid, bool/int/decimal edge cases, date format-only, select error format, empty/null/unknown) | MEDIUM | T005 |

#### Phase 3: Python Integration (QA)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T007 | Create `validation_engine.py` dispatcher with `_USE_RUST` flag, threshold guard (>5), `_DecimalEncoder`, Rust/Python paths | LOW | T006 |
| T008 | Modify `customization.py` `validate()` method — replace lines 80-91 with `validate_fields()` call | LOW | T007 |
| T009 | Update `gravitea_rust.pyi` with `validate_custom_fields` stub | LOW | T006 |

#### Phase 4: Tests (QA)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T010 | Write parity tests: all 6 field types valid/invalid, edge cases (bool/int, Decimal, null, undefined, unknown, empty) | LOW | T008 |
| T011 | Write threshold guard tests: 3→Python, 5→Python, 6→Rust | LOW | T008 |
| T012 | Write fallback tests: `_USE_RUST=False` → correct output, warning logged | LOW | T008 |
| T013 | Write benchmark test: 25 fields with all types + 50-choice select < 2ms | LOW | T010 |

#### Phase 5: Docker + Regression (LEAD)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T014 | Docker build: `docker compose build web` | LOW | T013 |
| T015 | Docker import check: `from gravitea_rust import validate_custom_fields` | LOW | T014 |
| T016 | Run SPEC-025 tests in Docker container | LOW | T015 |
| T017 | Full regression test suite — 0 new failures | LOW | T016 |
| T018 | Update quickstart.md with final results | LOW | T017 |

### Critical Path

```
T001 → T002 → T003 → T004 → T005 → T006 (Rust core)
                                      ↓
T007 → T008 → T009 (Python integration)
         ↓
T010 → T011 → T012 → T013 (Testing)
                       ↓
T014 → T015 → T016 → T017 → T018 (Docker + regression)
```

**Parallelization opportunities**:
- T009 (type stubs) can run parallel with T007-T008 (different file)
- T011 + T012 (threshold/fallback) can run parallel after T008
- Phase 2 (Rust core) and T009 (type stubs) can overlap with different agents

### Team Allocation

| Agent | Tasks | Model |
|-------|-------|-------|
| LEAD (ORCHESTRATOR) | T001, T002, T014-T018, coordination | Opus 4.6 |
| RUST-EXPERT | T003-T006 | Opus 4.6 |
| QA | T007-T013 | Sonnet 4.6 |
