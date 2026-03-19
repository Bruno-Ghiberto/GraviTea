# Implementation Plan: Grain Reference Data

**Branch**: `010-grain-reference` | **Date**: 2026-03-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-grain-reference/spec.md`

## Summary

Implement the grain reference data layer for the acopio (grain elevator) module: 4 Django models (`GrainType`, `ToleranceTable`, `MermaTable` as global entities; `CampanaConfig` as tenant-scoped), seed fixtures with official ARCA grain species codes and regulatory values, an idempotent management command, 4 DRF API endpoints (read-only for global tables, full CRUD for campaigns), and a comprehensive test suite. This is the foundational data layer that all downstream acopio specs (11-13) depend on.

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework, djangorestframework-simplejwt, PostgreSQL 18.1
**Storage**: PostgreSQL 18.1 (Cloud SQL Enterprise Plus)
**Testing**: pytest + pytest-django via `scripts/run-tests-external.sh` (NEVER inside Claude Code)
**Target Platform**: Linux server (Docker/Kubernetes on GCP)
**Project Type**: Web service (multi-tenant ERP backend)
**Performance Goals**: Reference data lookups in < 5ms; tolerance/merma versioned lookups via composite indexes
**Constraints**: Multi-tenant isolation via RLS for tenant-scoped tables; global reference tables shared across all tenants (ADR-010)
**Scale/Scope**: ~18 grain types, ~100 tolerance entries, ~50 merma bands, unlimited campaigns per tenant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Ironclad Data Model | **PASS** | `DECIMAL(5,2)` for percentages (not financial). `DECIMAL(17,3)` reserved for weight/money fields (not in scope for spec-10). `ON DELETE PROTECT` on all FKs. No ledger pattern needed (reference data, not transactions). |
| II. Multi-Tenant Isolation | **PASS** | CampanaConfig gets RLS policy + TenantBoundManager. GrainType/ToleranceTable/MermaTable are GLOBAL per ADR-010 — no tenant FK, no RLS. This is an intentional architectural decision for government-mandated reference data shared across all tenants. |
| III. Modular Django Architecture | **PASS** | `acopio` module listed in constitution as planned vertical. App label `gravitea_acopio` follows convention. |
| IV. Application-Level Encryption | **N/A** | No PII or sensitive data in grain reference tables. |
| V. Secure Authentication | **PASS** | All endpoints require JWT `IsAuthenticated`. Tenant context extracted from JWT claims. |
| VI. Fiscal Compliance | **N/A** | Spec-10 is reference data only. ARCA integration is downstream (spec-11+). |
| VII. Offline-First | **N/A** | Reference data is read-mostly. Sync not in scope for spec-10. |
| VIII. Query Optimization | **PASS** | ViewSets use `select_related("grain_type")` for ToleranceTable/MermaTable FK joins. Composite indexes on versioned lookups. |
| IX. Secure Data Operations | **PASS** | Serializers use explicit `fields` lists (no `__all__`). CampanaConfig CRUD validates tenant ownership. |
| X. Test-Driven Development | **PASS** | 90% coverage target (exceeds 80% minimum). 20+ tests across 3 categories. |
| XI. JWT Authentication | **PASS** | JWT claims provide `tenant_id` for CampanaConfig scoping. |
| XII. Rate Limiting | **N/A** | Reference data endpoints are read-mostly, low-volume. Not a brute-force target. |
| XIII. Cursor-Based Pagination | **JUSTIFIED DEVIATION** | Constitution mandates cursor-based, but REST API Design v1.0 Section 2.6 specifies page-number pagination with `count`/`next`/`previous` envelope. Cursor pagination does not support total count. For reference data (< 100 rows per endpoint), page-number is appropriate and matches the approved API specification. |
| XIV. API Documentation | **PASS** | Serializers and viewsets will have docstrings for `drf-spectacular` auto-generation. |

## Project Structure

### Documentation (this feature)

```text
specs/010-grain-reference/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # API contract (4 endpoints)
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── acopio/                          # NEW — entire app created by spec-10
│       ├── __init__.py
│       ├── apps.py                      # AcopioConfig (label: gravitea_acopio)
│       ├── models/
│       │   ├── __init__.py              # Re-export all 4 models
│       │   ├── grain_type.py            # GrainType (GLOBAL)
│       │   ├── campana_config.py        # CampanaConfig (TenantBound)
│       │   ├── tolerance_table.py       # ToleranceTable (GLOBAL)
│       │   └── merma_table.py           # MermaTable (GLOBAL)
│       ├── serializers/
│       │   ├── __init__.py
│       │   └── reference_data.py        # All 4 serializers
│       ├── views/
│       │   ├── __init__.py
│       │   └── reference_data.py        # All 4 viewsets
│       ├── urls.py                      # DRF DefaultRouter
│       ├── admin.py                     # Admin registration
│       ├── fixtures/
│       │   ├── grain_types.json         # 7 primary grains
│       │   ├── tolerance_tables.json    # 5 grains x parameters
│       │   └── merma_tables.json        # 5 grains x zarandeo bands
│       ├── management/
│       │   └── commands/
│       │       └── seed_grain_reference.py  # Idempotent loader
│       └── migrations/
│           └── 0001_initial.py          # Auto-generated
├── database/
│   └── sql/
│       └── acopio_rls.sql              # RLS for CampanaConfig only
├── gravitea/
│   ├── settings/
│   │   └── base.py                     # MODIFIED: add "apps.acopio" to INSTALLED_APPS
│   └── urls.py                         # MODIFIED: add acopio URL include
└── tests/
    └── acopio/                          # NEW — test suite
        ├── __init__.py
        ├── conftest.py                  # Acopio-specific fixtures
        ├── test_models.py               # Model unit tests (8-10 tests)
        ├── test_api.py                  # API integration tests (8-10 tests)
        └── test_fixtures.py             # Fixture/seed tests (4-6 tests)
```

**Structure Decision**: Single new Django app (`apps.acopio`) following the existing modular pattern. Models in `models/` subdirectory with `__init__.py` re-exports, matching the `apps.core.models` pattern. Tests in `tests/acopio/` matching existing test directory structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Page-number pagination (vs cursor-based) | REST API Design v1.0 Section 2.6 specifies page-number with `count` field. Reference data is < 100 rows. | Cursor pagination cannot provide total count needed by the API contract. Dataset is small enough that offset performance is not a concern. |
