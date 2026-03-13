# Implementation Plan: ARCA CAEA Batch Builder Acceleration

**Branch**: `024-rust-arca-batch` | **Date**: 2026-02-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-rust-arca-batch/spec.md`

## Summary

Replace the inner loop of `CAEAService.informar_comprobantes()` (caea.py lines 232-302) with a Rust/PyO3 function that serializes 20-100 comprobantes into ARCA SOAP-compatible dict structures. Uses serde for JSON serialization with exact key naming via `#[serde(rename)]`. Dispatches to Rust when batch size >10 comprobantes; falls back to Python otherwise. Zero new Cargo dependencies.

## Technical Context

**Language/Version**: Rust 1.93.1 (PyO3 0.28, Maturin 1.12.4) + Python 3.14.3 (Django 5.2.x)
**Primary Dependencies**: `serde 1.0`, `serde_json 1.0`, `pyo3 0.28`, `thiserror 2.0` (all already in Cargo.toml)
**Storage**: N/A — pure computation, no persistence
**Testing**: `cargo test` (Rust-native) + `pytest` (Python integration) via external test runner
**Target Platform**: Linux (WSL2 development, Docker production)
**Project Type**: Library extension (PyO3 shared library `gravitea_rust`)
**Performance Goals**: 50 comprobantes with IVA + tributos in <5ms (Rust path)
**Constraints**: Output must be byte-identical to Python fallback for any input (parity guarantee FR-017)
**Scale/Scope**: 20-100 comprobantes per CAEA quincena per punto de venta

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | N/A | No database changes — pure computation |
| II. Multi-Tenant Isolation | N/A | No tenant data access — dict transformation only |
| III. Modular Django Architecture | PASS | Changes within `facturacion` module boundaries |
| IV. Application-Level Encryption | N/A | No PII handling in batch builder |
| V. Secure Authentication | N/A | No auth changes |
| VI. Fiscal Compliance (ARCA) | PASS | Parity guarantee (FR-017) ensures ARCA output is identical. Output structure dictated by ARCA WSDL — Rust must match exactly. |
| VII. Offline-First | N/A | CAEA is already offline-first; we accelerate batch reporting, not sync |
| VIII. Query Optimization | N/A | No database queries |
| IX. Secure Data Operations | N/A | No model mutations |
| X. Test-Driven Development | PASS | ≥10 cargo tests + ≥15 pytest tests planned (SC-003) |
| XI-XIV | N/A | No auth/pagination/API changes |

**Gate result**: PASS — no violations, no complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/024-rust-arca-batch/
├── spec.md              # Feature specification (17 FRs, 6 SCs)
├── plan.md              # This file
├── research.md          # Phase 0 output — all decisions resolved
├── quickstart.md        # Phase 1 output — developer setup guide
└── checklists/
    └── requirements.md  # Quality checklist (12/12 passing)
```

### Source Code (repository root)

```text
rust/gravitea-core/src/
├── lib.rs               # MODIFIED — +mod arca, +1 pymodule_export
├── errors.rs            # MODIFIED — +ARCABuildError variant
└── arca.rs              # NEW — serde structs + build_caea_batch_request

backend/apps/facturacion/arca/
├── caea.py              # MODIFIED — replace inner loop with dispatcher call
└── caea_engine.py       # NEW — dispatcher (Rust/Python fallback)

backend/gravitea_rust.pyi  # MODIFIED — +1 function stub

backend/tests/rust_integration/
└── test_arca_024.py     # NEW — parity, threshold, fallback, benchmark tests
```

**Structure Decision**: Follows established pattern from SPEC-018 through SPEC-023. Rust source in `rust/gravitea-core/src/`, Python dispatcher in the same package as the target file, integration tests in `tests/rust_integration/`.

## Complexity Tracking

> No constitution violations. No complexity justifications needed.

## Phase 0: Research

All research topics were resolved during the specify phase via source code analysis and GitNexus blast radius checks. See [research.md](research.md) for the complete decision log.

**Key decisions**:
- Zero new Cargo dependencies (chrono and rust_decimal eliminated)
- ARCA-EXPERT agent eliminated (structure fully documented from source)
- All 6 research topics pre-resolved from `caea.py` source code

## Phase 1: Design

### Data Model

No data model changes. This feature is a pure computation acceleration — no new database tables, no model changes, no migrations. The input and output are in-memory dict/JSON structures dictated by the existing ARCA SOAP integration.

Input/output struct designs are fully specified in `Docs/Temp-prompting/024/instruction-specify.md` §Serde Struct Design.

### Contracts

No new external interfaces. The Rust function is internal to the `facturacion` module. The output format is dictated by ARCA's WSFEv1 WSDL — the Rust function must produce the same dict structure that the existing Python inner loop produces. This is verified by the parity guarantee (FR-017).

### Architecture

```
┌─────────────────────────────────────────────────────┐
│ CAEAService.informar_comprobantes()                 │
│                                                     │
│  fe_cab_req = { CantReg, PtoVta, CbteTipo }        │
│                     │                               │
│                     ▼                               │
│  ┌─────────────────────────────────────┐            │
│  │ caea_engine.build_det_list()        │            │
│  │                                     │            │
│  │  len(comprobantes) > 10             │            │
│  │  AND _USE_RUST?                     │            │
│  │     ├── YES → _build_rust()         │            │
│  │     │    json.dumps → Rust FFI      │            │
│  │     │    → json.loads → det_list    │            │
│  │     └── NO  → _build_python()       │            │
│  │          (extracted inner loop)      │            │
│  └─────────────────────────────────────┘            │
│                     │                               │
│                     ▼                               │
│  fe_det_req = { FECAEADetRequest: det_list }        │
│  → zeep SOAP call → parse response                  │
└─────────────────────────────────────────────────────┘
```

### Implementation Phases

#### Phase 1: Rust Core (RUST-EXPERT)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T001 | Add `ARCABuildError(String)` to `errors.rs` | LOW | — |
| T002 | Create `arca.rs` with input serde structs (`ComprobanteInput`, `AlicIvaInput`, `TributoInput`, `CbteAsocInput`) | MEDIUM | T001 |
| T003 | Create output serde structs (`FECAEADetRequest`, `IvaWrapper`, `TributosWrapper`, `CbtesAsocWrapper` + inner types) | HIGH | T002 |
| T004 | Implement `build_caea_batch_request` PyO3 function with GIL release | HIGH | T003 |
| T005 | Implement conversion logic: str→f64, concepto guard, tributos guard, CUIT fallback, empty array handling | HIGH | T004 |
| T006 | Register `mod arca` + `pymodule_export` in `lib.rs` | LOW | T004 |
| T007 | Write ≥10 cargo tests (all spec edge cases) | MEDIUM | T005 |

#### Phase 2: Python Integration (QA + LEAD)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T008 | Create `caea_engine.py` dispatcher with `_USE_RUST` flag and threshold guard | MEDIUM | T006 |
| T009 | Extract Python inner loop into `_build_python()` fallback | LOW | T008 |
| T010 | Modify `caea.py` to use `caea_engine.build_det_list()` | LOW | T009 |
| T011 | Update `gravitea_rust.pyi` with function stub | LOW | T006 |
| T012 | Write parity tests (Rust == Python for all test vectors) | HIGH | T010 |
| T013 | Write threshold guard tests (≤10 → Python, >10 → Rust) | MEDIUM | T010 |
| T014 | Write fallback tests (`_USE_RUST = False`) | LOW | T010 |
| T015 | Write benchmark test (50 comprobantes <5ms) | LOW | T012 |

#### Phase 3: Docker + Regression (LEAD)

| # | Task | Risk | Depends On |
|---|------|------|------------|
| T016 | Docker build: `docker compose build web` | LOW | T015 |
| T017 | Docker import check: `build_caea_batch_request` importable | LOW | T016 |
| T018 | Run SPEC-024 tests in Docker container | LOW | T017 |
| T019 | Full regression test suite — 0 new failures | LOW | T018 |
| T020 | Update quickstart.md with final results | LOW | T019 |

### Critical Path

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 (Rust core)
                                       ↓
T008 → T009 → T010 → T011 (Python integration)
                 ↓
T012 → T013 → T014 → T015 (Testing)
                        ↓
T016 → T017 → T018 → T019 → T020 (Docker + regression)
```

**Parallelization opportunities**:
- T011 (type stubs) can run parallel with T008-T010
- T013 + T014 can run parallel with T012
- T007 (cargo tests) can overlap with T008 start (different agents)

### Team Allocation

| Agent | Tasks | Model |
|-------|-------|-------|
| LEAD (ORCHESTRATOR) | T001, T006, T010, T016-T020, coordination | Opus 4.6 |
| RUST-EXPERT | T002-T005, T007 | Opus 4.6 |
| QA | T008-T009, T011-T015 | Sonnet 4.6 |
