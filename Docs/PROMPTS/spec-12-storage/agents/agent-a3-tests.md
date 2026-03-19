# Agent A3: Tests & Validation

**Agent Type**: `quality-engineer`
**Model**: Sonnet 4.6
**Mission**: Write all test files covering model constraints, service layer logic, API integration, and tenant isolation. Run gate checks and final test suite validation.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-12-storage/12-implement.md` — Orchestration protocol, wave order, done criteria
2. `specs/012-storage-position/spec.md` — User stories, acceptance scenarios, success criteria
3. `specs/012-storage-position/contracts/storage-api.md` — API contracts (expected status codes, response shapes)
4. `specs/012-storage-position/quickstart.md` — Test setup patterns, queryset patterns
5. `specs/012-storage-position/tasks.md` — Full task list with test descriptions

---

## Assigned Tasks

### Wave 2: MVP Tests (T009, T013, T014, T021)

| Task | Description |
|------|-------------|
| T009 | `StorageUnit` model tests in `backend/tests/acopio/test_storage_models.py` |
| T013 | `StorageUnit` API tests in `backend/tests/acopio/test_storage_api.py` |
| T014 | Deposit flow tests in `backend/tests/acopio/test_grain_ledger.py` |
| T021 | Deposit flow API tests — extend `test_storage_api.py` |

### Wave 3: P2 Tests (T022, T025, T026, T029, T030, T033, T034, T037)

| Task | Description |
|------|-------------|
| T022 | CellSuggestion service tests in `backend/tests/acopio/test_storage_services.py` |
| T025 | Suggest endpoint API tests |
| T026 | Withdrawal ledger tests — extend `test_grain_ledger.py` |
| T029 | Dispatch API tests — extend `test_storage_api.py` |
| T030 | Transfer ledger tests — extend `test_grain_ledger.py` |
| T033 | Transfer API tests — extend `test_storage_api.py` |
| T034 | StockReport service tests — extend `test_storage_services.py` |
| T037 | Stock-report API tests — extend `test_storage_api.py` |

### Wave 4: P3 Tests (T038, T042, T043, T046)

| Task | Description |
|------|-------------|
| T038 | Reconciliation service tests — extend `test_storage_services.py` |
| T042 | Reconciliation API tests — extend `test_storage_api.py` |
| T043 | Campaign close service tests — extend `test_storage_services.py` |
| T046 | Campaign close API tests — extend `test_storage_api.py` |

### Wave 5: Polish (T047–T050)

| Task | Description |
|------|-------------|
| T047 | Re-run Gate 1 verification commands |
| T048 | Re-run Gate 2 verification commands |
| T049 | Run full test suite via `scripts/run-tests-external.sh`; verify 40+ tests, 0 failures |
| T050 | Verify `check_grain_balance` management command reports no drift |

---

## Files to Create

| File | Description |
|------|-------------|
| `backend/tests/acopio/test_storage_models.py` | Model unit tests (constraints, immutability, TenantBound) |
| `backend/tests/acopio/test_grain_ledger.py` | Balance invariants, deposit, withdrawal, transfer atomicity |
| `backend/tests/acopio/test_storage_api.py` | CRUD, HTTP codes, tenant isolation, immutable endpoints |
| `backend/tests/acopio/test_storage_services.py` | CellSuggestion, StockReport, Reconciliation, CampaignClose |

---

## Domain Knowledge

### RAG Queries (run if you need additional context)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "pytest fixtures tenant isolation acopio" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "immutable ledger test ValueError delete" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain movement deposit withdrawal balance" -l 5
```

### Critical Domain Facts (Inlined)

1. **GrainMovement is IMMUTABLE**: `save()` on existing pk → `ValueError`. `delete()` → `ValueError`. API PATCH/PUT/DELETE → HTTP 405.
2. **GrainLot.total_kg == Sum(GrainMovement.quantity_kg)** for that lot AT ALL TIMES.
3. **Withdrawal stores negative quantity_kg**: Input is positive (amount to withdraw), stored as `-quantity_kg`.
4. **Transfer creates 2 movements atomically**: TRANSFER_OUT (negative) + TRANSFER_IN (positive).
5. **Insufficient balance** → `ValueError` from service → HTTP 409 from API.
6. **Cross-tenant requests** → HTTP 404 (TenantBoundManager returns empty queryset).
7. **Duplicate storage unit name** in same branch/tenant → HTTP 400 (IntegrityError caught by DRF).
8. **ADJUSTMENT movement requires notes** → `ValueError` if notes is blank.
9. **Campaign close requires supervisor permission** → HTTP 403 for non-supervisor.
10. **Cell suggestion scoring**: grain type match = 40pts, grade match = +20pts, campaign match = +10pts.
11. **`romaneo_conforme` fixture**: A romaneo in CONFORME status with `peso_neto_conforme_kg` set, `storage_unit` assigned, ready for deposit testing.

---

## Key Patterns & Constraints

### Test File Structure

```python
import pytest
from decimal import Decimal
from django.db import IntegrityError

pytestmark = [pytest.mark.django_db]


class TestStorageUnitModel:
    """T009: StorageUnit model constraints and behavior."""

    def test_create_storage_unit(self, storage_unit_factory):
        unit = storage_unit_factory()
        assert unit.pk is not None
        assert unit.is_active is True

    def test_unique_name_per_branch_tenant(self, storage_unit_factory):
        storage_unit_factory(name="Silo 1")
        with pytest.raises(IntegrityError):
            storage_unit_factory(name="Silo 1")

    def test_tenant_bound_manager_fail_closed(self, storage_unit_factory):
        """TenantBoundManager returns empty if no tenant context."""
        unit = storage_unit_factory()
        # Without tenant context, should not be visible
        from apps.acopio.models import StorageUnit
        assert StorageUnit.all_objects.filter(pk=unit.pk).exists()
```

### Immutability Test Pattern

```python
class TestGrainMovementImmutability:
    """T014: GrainMovement save/delete raise ValueError."""

    def test_save_existing_raises(self, grain_movement_factory):
        movement = grain_movement_factory()
        movement.notes = "changed"
        with pytest.raises(ValueError, match="immutable"):
            movement.save()

    def test_delete_raises(self, grain_movement_factory):
        movement = grain_movement_factory()
        with pytest.raises(ValueError, match="immutable"):
            movement.delete()
```

### Deposit Flow Test Pattern

```python
class TestDepositFromRomaneo:
    """T014: create_deposit_from_romaneo service tests."""

    def test_first_deposit_creates_lot(self, romaneo_conforme, storage_unit_factory):
        unit = storage_unit_factory(branch=romaneo_conforme.branch)
        from apps.acopio.services.storage import create_deposit_from_romaneo
        movement, lot = create_deposit_from_romaneo(
            romaneo=romaneo_conforme,
            storage_unit=unit,
            is_own_grain=False,
        )
        assert lot.total_kg == romaneo_conforme.peso_neto_conforme_kg
        assert movement.movement_type == "DEPOSIT"
        assert movement.romaneo == romaneo_conforme
        assert romaneo_conforme.grain_lot == lot
        # US2-AS3: current_grain_type auto-set on empty unit
        unit.refresh_from_db()
        assert unit.current_grain_type == romaneo_conforme.grain_type

    def test_second_deposit_reuses_lot(self, romaneo_conforme, storage_unit_factory, romaneo_factory):
        unit = storage_unit_factory(branch=romaneo_conforme.branch)
        from apps.acopio.services.storage import create_deposit_from_romaneo
        _, lot1 = create_deposit_from_romaneo(romaneo_conforme, unit, False)
        # Second romaneo with same grain/campaign/grade/silo
        rom2 = romaneo_factory(
            grain_type=romaneo_conforme.grain_type,
            campaign=romaneo_conforme.campaign,
        )
        # Progress rom2 to CONFORME (abbreviated — use existing transition helpers)
        _, lot2 = create_deposit_from_romaneo(rom2, unit, False)
        assert lot1.pk == lot2.pk  # Same lot reused
```

### API Test Pattern

```python
class TestStorageUnitAPI:
    """T013: StorageUnit CRUD API tests."""

    def test_list_storage_units(self, api_client, storage_unit_factory):
        storage_unit_factory()
        response = api_client.get("/api/v1/acopio/storage-units/")
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert "current_occupancy_kg" in response.data["results"][0]

    def test_delete_returns_405(self, api_client, storage_unit_factory):
        unit = storage_unit_factory()
        response = api_client.delete(f"/api/v1/acopio/storage-units/{unit.pk}/")
        assert response.status_code == 405

    def test_cross_tenant_returns_404(self, api_client_other_tenant, storage_unit_factory):
        unit = storage_unit_factory()
        response = api_client_other_tenant.get(
            f"/api/v1/acopio/storage-units/{unit.pk}/"
        )
        assert response.status_code == 404
```

### Test Runner Protocol

**ALWAYS** use the external test runner:

```bash
# Run specific test file
bash scripts/run-tests-external.sh -n spec12-models tests/acopio/test_storage_models.py

# Run specific test class
bash scripts/run-tests-external.sh -n spec12-deposit tests/acopio/test_grain_ledger.py::TestDepositFromRomaneo

# Run full acopio suite (Wave 5)
bash scripts/run-tests-external.sh -n spec12-final tests/acopio/

# Check status
cat Docs/Tests/spec12-final.status
```

### Gate Verification Commands

**Gate 1** (Wave 1 checkpoint):
```bash
cd backend && DJANGO_SETTINGS_MODULE=gravitea.settings.test \
    ../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement
print('Models OK')
from apps.acopio.models import Romaneo
r = Romaneo._meta.get_field('storage_unit')
print(f'Romaneo.storage_unit FK: {r.related_model.__name__}')
r2 = Romaneo._meta.get_field('grain_lot')
print(f'Romaneo.grain_lot FK: {r2.related_model.__name__}')
print('Gate 1 PASSED')
"
```

**Gate 2** (Wave 2 checkpoint):
```bash
cd backend && DJANGO_SETTINGS_MODULE=gravitea.settings.test \
    ../.venv/bin/python -c "
import django; django.setup()
from django.urls import reverse
print(reverse('storage-unit-list'))
print(reverse('grain-lot-list'))
print('Gate 2 PASSED')
"
```

---

## Fixture Dependencies

Your tests depend on fixtures from `conftest.py` (created by A1 in Wave 1):

| Fixture | Returns | Created By |
|---------|---------|------------|
| `storage_unit_factory` | Callable → `StorageUnit` instance | A1 (T001) |
| `grain_lot_factory` | Callable → `GrainLot` instance | A1 (T001) |
| `grain_movement_factory` | Callable → `GrainMovement` instance | A1 (T001) |
| `romaneo_conforme` | `Romaneo` in CONFORME status with `peso_neto_conforme_kg` | A1 (T001) |
| `tenant_context` | `Tenant` instance (existing from spec-10) | Existing |
| `branch` | `Branch` instance (existing) | Existing |
| `admin_user` | `AppUser` instance (existing) | Existing |
| `api_client` | Authenticated DRF `APIClient` (existing) | Existing |

---

## Test Coverage Targets

| Area | Minimum Tests | Key Assertions |
|------|---------------|----------------|
| Model constraints | 8+ | UniqueConstraint, CheckConstraint, immutability, TenantBound |
| Deposit flow | 5+ | Create lot, reuse lot, balance correct, romaneo FK updated, current_grain_type set |
| Withdrawal | 3+ | Balance decreases, insufficient balance rejected, negative quantity stored |
| Transfer | 4+ | Both movements created, atomicity, insufficient source rejected, same-lot rejected |
| API CRUD | 8+ | All HTTP methods tested, 405 for DELETE, 409 for deactivation guard, 404 for cross-tenant |
| Cell suggestion | 4+ | Scoring correct, incompatible excluded, insufficient capacity excluded |
| Stock report | 3+ | Aggregations correct, filters work, real-time (no cache) |
| Reconciliation | 4+ | Variance calculation, ADJUSTMENT created, notes required, immutable after |
| Campaign close | 4+ | Carry-forward created, incomplete romaneo rejected, supervisor required, atomic rollback |
| **Total** | **40+** | |

---

## NEVER

- NEVER run `pytest` directly inside Claude Code — always use `bash scripts/run-tests-external.sh`
- NEVER import StockMovement from `apps/inventario` — use GrainMovement from `apps/acopio`
- NEVER test `current_occupancy_kg` as a stored field — it's an annotated queryset value
- NEVER read full research PDFs — use RAG queries above if needed
- NEVER skip tenant isolation tests — every API test class needs at least one cross-tenant 404 assertion
