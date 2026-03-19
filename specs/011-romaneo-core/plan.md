# Implementation Plan: Romaneo Core

**Branch**: `011-romaneo-core` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/011-romaneo-core/spec.md`

## Summary

Implement the romaneo (grain reception document) lifecycle -- the central transactional workflow of the acopio operation. This adds 3 tenant-scoped Django models (Romaneo with 31 fields and 6-state machine, QualityAnalysis satellite, MermaCalculation immutable satellite), a Rust merma calculation engine with PyO3 bindings, DRF API layer with 14 endpoints, and a comprehensive test suite. Builds on spec-10's reference data models (GrainType, ToleranceTable, MermaTable, CampanaConfig).

## Technical Context

**Language/Version**: Python 3.14.3 + Rust 1.93.1 (PyO3 0.28, Maturin 1.12.4)
**Primary Dependencies**: Django 5.2.x, DRF, djangorestframework-simplejwt, rust_decimal, serde, serde_json, pyo3, thiserror
**Storage**: PostgreSQL 18.1 with RLS policies for all 3 new tenant-scoped models
**Testing**: pytest + pytest-django (Python), cargo test (Rust), scripts/run-tests-external.sh (execution)
**Target Platform**: Linux server (Docker/GKE)
**Project Type**: Multi-tenant ERP web service (acopio vertical)
**Performance Goals**: Romaneo save (including merma calculation) within 3 seconds under normal load (50 concurrent users per tenant)
**Constraints**: Immutability after CONFORME status, sequential merma formula precision (Decimal, no float), Hf vs humedad_base_pct distinction
**Scale/Scope**: 6-agent team, 14 new files, 9 modified files, 40+ tests, 90%+ coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Ironclad Data Model | PASS | DecimalField(17,3) for weights, (5,2) for percentages. Immutable MermaCalculation follows append-only ledger pattern. No FLOAT/DOUBLE. |
| II | Multi-Tenant Isolation (RLS) | PASS | All 3 models inherit TenantBoundModel. RLS policies added. TenantBoundManager fail-closed. |
| III | Modular Django Architecture | PASS | Extends existing `acopio` app (spec-10). Views orchestrate only; merma logic in service layer (`merma_engine.py`). |
| IV | Application-Level Encryption | N/A | No PII fields encrypted in spec-11. driver_name/driver_dni are operational fields for delivery receipts. NOTE: Legal review recommended to confirm these do not require encryption under Argentine data protection law. If required, encryption can be added in a future spec without schema changes (application-level AES-256-GCM). |
| V | Secure Authentication & Sessions | PASS | JWT-authenticated endpoints. Tenant context from JWT claims. IDOR prevented by TenantBoundManager. |
| VI | Fiscal Compliance (ARCA) | PASS | WSCPE operations (confirmarArriboCPE, confirmarDescargaCPE) via async store-and-forward. HTTP 202. |
| VII | Offline-First & Contingency | PASS | Romaneo number uses `server_assigns_final` pattern. Tolerance table version pinned at ts_entrada (local time). |
| VIII | Query Optimization | PASS | Composite indexes on (tenant_id, status, ts_entrada), (tenant_id, branch_id, ts_entrada), (tenant_id, campaign_id, grain_type_id). select_related for FK joins. |
| IX | Secure Data Operations | PASS | Serializers define explicit fields. No `fields = '__all__'`. State transition actions validate before mutation. |
| X | Test-Driven Development | PASS | 40+ tests planned. 90%+ coverage target. Merma correctness verified with hand-calculated vectors. |
| XI | JWT Authentication | PASS | All endpoints require IsAuthenticated. Tenant/branch context from JWT custom claims. |
| XII | Rate Limiting | N/A | No authentication endpoints in this spec. Existing rate limiting infrastructure applies. |
| XIII | Cursor-Based Pagination | DEVIATION | Romaneo list uses PageNumberPagination (not cursor). Romaneo lacks `created_at` field required by cursor pagination. Uses `ts_entrada` ordering instead. Justified: reference data pagination pattern from spec-10. |
| XIV | API Documentation | PASS | DRF viewsets auto-generate OpenAPI schema via drf-spectacular. Action endpoints require explicit schema annotation. |

**GATE RESULT**: PASS (1 justified deviation: pagination)

## Project Structure

### Documentation (this feature)

```text
specs/011-romaneo-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── api.md           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/apps/acopio/
├── models/
│   ├── __init__.py            # Modified: re-export new models
│   ├── romaneo.py             # NEW: Romaneo (31 fields, state machine)
│   ├── quality_analysis.py    # NEW: QualityAnalysis (1:1 satellite)
│   └── merma_calculation.py   # NEW: MermaCalculation (1:1 immutable)
├── serializers/
│   ├── __init__.py            # Modified: re-export new serializers
│   └── romaneo.py             # NEW: all romaneo serializers
├── views/
│   ├── __init__.py            # Modified: re-export new viewsets
│   └── romaneo.py             # NEW: RomaneoViewSet + QualityAnalysisViewSet
├── services/
│   ├── __init__.py            # NEW: package init
│   └── merma_engine.py        # NEW: Rust FFI wrapper + Python fallback
├── admin.py                   # Modified: register 3 new models
├── urls.py                    # Modified: register romaneo routes
├── pagination.py              # Modified: add RomaneoPagination
└── migrations/
    └── 0002_romaneo_core.py   # NEW: migration for 3 models

rust/gravitea-core/src/
├── merma.rs                   # NEW: Rust merma engine
└── lib.rs                     # Modified: register calculate_merma

backend/database/sql/
└── acopio_rls.sql             # Modified: add RLS for 3 new tables

backend/tests/acopio/
├── conftest.py                # Modified: add romaneo fixtures
├── test_romaneo_models.py     # NEW: model + state machine tests
├── test_romaneo_api.py        # NEW: API endpoint tests
├── test_quality_analysis.py   # NEW: QA model + API tests
├── test_merma_calculation.py  # NEW: merma correctness tests
└── test_merma_rust.py         # NEW: Rust FFI + parity tests
```

**Structure Decision**: Extends the existing `backend/apps/acopio/` Django app established by spec-10. New models, serializers, views, and services follow the same modular file-per-concern pattern. Rust module added to the existing `rust/gravitea-core/` crate.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| PageNumberPagination instead of CursorPagination (Constitution XIII) | Romaneo has no `created_at` field; ordering is by `ts_entrada` (arrival timestamp). Cursor pagination requires a unique, sequential ordering field. | Could add `created_at` but it would be redundant with `ts_entrada` and spec-10 already established PageNumberPagination for acopio models. Consistency within the acopio vertical takes precedence. |
