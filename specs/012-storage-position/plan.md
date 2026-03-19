# Implementation Plan: Storage & Position

**Branch**: `012-storage-position` | **Date**: 2026-03-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-storage-position/spec.md`

**Note**: This file was produced by the `/speckit.plan` command.

---

## Summary

Implement physical storage infrastructure (StorageUnit), grain position ledger
(GrainLot with composite identity per RG 3593), and immutable grain movement
ledger (GrainMovement) within the existing `apps/acopio` Django application.
The feature completes the core reception workflow introduced in spec-11 (romaneo
→ silo assignment → deposit movement → lot balance update) and adds dispatch,
inter-silo transfer, cell suggestion, stock reporting, physical reconciliation,
and campaign close services. Two nullable FKs (`storage_unit`, `grain_lot`) are
added to the existing Romaneo model via migration 0003 per Data Model v1.0
Group 6. GrainMovement follows the same full-immutability pattern as
MermaCalculation; grain inventory is explicitly separate from discrete inventory
(ADR-009 Dual Inventory).

---

## Technical Context

**Language/Version**: Python 3.14.3
**Primary Dependencies**: Django 5.2.x, Django REST Framework (latest), djangorestframework-simplejwt (JWT auth), drf-spectacular (OpenAPI), pytest + pytest-django (testing)
**Storage**: PostgreSQL 18.1 — `DECIMAL(17,3)` for kg balances; `UniqueConstraint` on composite lot key; `CheckConstraint` (`total_kg >= 0`) on GrainLot; RLS on all 3 new tables
**Testing**: pytest + pytest-django via `scripts/run-tests-external.sh` (background runner). Target: 40+ tests, 90%+ coverage on new code
**Target Platform**: Linux server (Docker / GKE), same as existing backend
**Project Type**: REST API web-service — extends existing `apps/acopio` module
**Performance Goals**: StorageUnit list with derived occupancy responds within 200ms for 200 units (SC-003); stock report real-time with no cache delay (SC-002)
**Constraints**: GrainMovement fully immutable (no UPDATE/DELETE); negative lot balance blocked before commit; 3-layer tenant isolation (serializer + model + RLS); `DECIMAL(17,3)` for all kg values (Constitution I)
**Scale/Scope**: Per tenant: up to 200 storage units, multiple concurrent harvest campaigns, continuous grain movement ledger entries (deposit/dispatch/transfer/adjustment)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Ironclad Data Model** | ✅ PASS | `DECIMAL(17,3)` for all kg fields; GrainMovement is append-only ledger; `CheckConstraint(total_kg >= 0)` on GrainLot; `UniqueConstraint` enforces composite lot identity; `ON DELETE PROTECT` on all FKs except Romaneo→StorageUnit/GrainLot (SET_NULL per Data Model) |
| **II. Multi-Tenant Isolation** | ✅ PASS | All 3 new models inherit `TenantBoundModel` with `TenantBoundManager` fail-closed; RLS policies appended to `acopio_rls.sql` for `acopio_storageunit`, `acopio_grainlot`, `acopio_grainmovement`; 3-layer validation in place |
| **III. Modular Architecture** | ✅ PASS | All code added to existing `apps/acopio` module; viewsets are lightweight orchestration only; business logic in `services/storage.py`; clear dependency: acopio → core (no reverse deps) |
| **IV. Application Encryption** | ✅ N/A | No PII in StorageUnit / GrainLot / GrainMovement; operator identity is FK to AppUser (no raw string storage) |
| **V. Secure Authentication** | ✅ PASS | All endpoints require `IsAuthenticated`; serializers list explicit fields (no `__all__`); no mass assignment vectors |
| **VI. Fiscal Compliance** | ✅ PARTIAL | GrainLot `is_own_grain` routes to correct accounting codes (ADR-020); no ARCA integration in this spec (deferred to spec-13 producer accounts) |
| **VII. Offline-First** | ✅ N/A | This spec is backend-only; offline sync of movements is deferred |
| **VIII. Query Optimization** | ✅ PASS | `current_occupancy_kg` computed via single annotated `Sum()` queryset (no N+1); `select_related("branch", "current_grain_type")` on StorageUnit queries; `select_for_update()` on concurrent balance updates |
| **IX. Secure Data Operations** | ✅ PASS | All serializers use explicit field lists; no `fields = '__all__'`; patchable fields explicitly declared on `RomaneoSerializer` |
| **X. TDD** | ✅ PASS | A3 agent writes 40+ tests before or alongside A2; 90%+ coverage target on new code; tests cover immutability, tenant isolation, negative balance, transfer atomicity |
| **XI. JWT Authentication** | ✅ PASS | Endpoints inherit existing DRF permission classes; `IsAuthenticated` on all viewsets |
| **XII. Rate Limiting** | ✅ N/A | No new authentication endpoints introduced |
| **XIII. Cursor Pagination** | ⚠️ PRE-EXISTING DEVIATION | Constitution mandates cursor-based pagination. Existing `apps/acopio` uses `PageNumberPagination` (spec-10, spec-11). Spec-12 follows the established acopio pagination pattern for consistency. Switching to cursor pagination in this spec alone would create an inconsistent API surface. This deviation is inherited, not introduced by spec-12. |
| **XIV. API Documentation** | ✅ PASS | DRF serializers + viewsets + docstrings → auto-generated OpenAPI via `drf-spectacular` |

**Constitution Gate**: PASS with one pre-existing deviation (XIII). No new violations introduced by spec-12.

---

## Project Structure

### Documentation (this feature)

```text
specs/012-storage-position/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── storage-api.md   # REST API endpoint contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── acopio/
│       ├── models/
│       │   ├── storage_unit.py       # NEW -- StorageUnit model
│       │   ├── grain_lot.py          # NEW -- GrainLot model
│       │   ├── grain_movement.py     # NEW -- GrainMovement model (immutable)
│       │   ├── romaneo.py            # MODIFY -- add storage_unit + grain_lot FKs
│       │   └── __init__.py           # MODIFY -- re-export new models
│       ├── services/
│       │   └── storage.py            # NEW -- CellSuggestionService, StockReportService,
│       │                             #          ReconciliationService, CampaignCloseService
│       ├── serializers/
│       │   ├── storage.py            # NEW -- StorageUnit, GrainLot, GrainMovement serializers
│       │   ├── romaneo.py            # MODIFY -- add storage_unit patchable field
│       │   └── __init__.py           # MODIFY -- re-export new serializers
│       ├── views/
│       │   ├── storage.py            # NEW -- StorageUnitViewSet, GrainLotViewSet,
│       │   │                         #          GrainMovementViewSet (append-only)
│       │   ├── reference_data.py     # MODIFY -- add close action to CampanaConfigViewSet (US8)
│       │   └── __init__.py           # MODIFY -- re-export new viewsets
│       ├── migrations/
│       │   └── 0003_storage_position.py  # NEW -- create 3 tables + alter romaneo
│       ├── admin.py                  # MODIFY -- register StorageUnit, GrainLot, GrainMovement
│       └── urls.py                   # MODIFY -- register storage routes
├── database/
│   └── sql/
│       └── acopio_rls.sql            # MODIFY -- append RLS policies for 3 new tables
└── tests/
    └── acopio/
        ├── test_storage_models.py    # NEW -- model unit tests + constraints
        ├── test_grain_ledger.py      # NEW -- balance, immutability, transfer atomicity
        ├── test_storage_api.py       # NEW -- API integration + tenant isolation
        ├── test_storage_services.py  # NEW -- CellSuggestion, StockReport, Reconciliation
        └── conftest.py               # MODIFY -- add storage fixtures
```

**Structure Decision**: Single backend project (Option 1 adapted). All changes are
contained within the existing `apps/acopio` module. No new Django app is created.
The service layer (`services/storage.py`) houses all business invariants;
viewsets are lightweight orchestrators.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Cursor pagination not used (Const. XIII) | Pre-existing deviation in `apps/acopio` (spec-10, spec-11 use PageNumberPagination). Changing in spec-12 only creates inconsistent API surface for the same app. | Switching all acopio endpoints to cursor pagination is out of scope for spec-12 and requires a dedicated migration spec. |
