# Quickstart: Storage & Position (Spec-12)

**Generated**: 2026-03-19

A rapid-reference guide for developers implementing or integrating with the
Storage & Position module. Read this before writing any code.

---

## Mental Model (5 minutes)

```
ROMANEO (confirmed reception)
     │
     │ operator assigns silo
     ▼
STORAGE UNIT (physical silo/celda/bin)
     │
     │ get_or_create lot by composite key
     ▼
GRAIN LOT (logical position record per grain/campaign/grade/silo)
     │
     │ append immutable entry
     ▼
GRAIN MOVEMENT (immutable ledger: what came in/went out and when)
```

**Key invariant**: `GrainLot.total_kg == Sum(GrainMovement.quantity_kg for that lot)`
at all times. Never update `total_kg` without creating a corresponding `GrainMovement`.
Never create a `GrainMovement` without updating `total_kg`.

---

## Four Things to Know Before Coding

1. **GrainMovement is immutable.** `save()` raises `ValueError` on existing records.
   `delete()` raises `ValueError` always. API returns HTTP 405 for PATCH/DELETE/PUT.
   There is no exception to this rule.

2. **GrainLot uses get_or_create.** Two deposits of the same `(branch, grain_type,
   campaign, grado, storage_unit)` go into the same lot. Never create a new lot
   manually — always use `GrainLot.objects.get_or_create(...)` with the full
   composite key.

3. **current_occupancy_kg is NOT stored.** It is annotated on demand:
   `StorageUnit.objects.annotate(current_occupancy_kg=Coalesce(Sum(...), 0))`.
   Never add it as a model field.

4. **GrainMovement ≠ StockMovement.** They are in different apps and serve
   different purposes. Do not import StockMovement from `apps/inventario` for
   grain tracking. (ADR-009: Dual Inventory)

---

## Quick Reference: Service Calls

```python
from apps.acopio.services.storage import (
    create_deposit_from_romaneo,
    create_withdrawal,
    transfer_grain,
    suggest_cell,
    generate_stock_report,
    reconcile,
)

# 1. Deposit grain from a confirmed romaneo
movement, lot = create_deposit_from_romaneo(
    romaneo=romaneo,           # must be in CONFORME status
    storage_unit=storage_unit, # operator-selected silo
    is_own_grain=False,        # True = purchased grain; False = third-party custody
)

# 2. Record a dispatch (withdrawal)
movement = create_withdrawal(
    grain_lot=lot,
    quantity_kg=Decimal("15000.000"),
    operator=request.user,
    reference_document="CPE-2026-0123",
)

# 3. Transfer between silos (atomic)
out_movement, dest_lot = transfer_grain(
    source_lot=silo1_lot,
    destination_lot=silo2_lot,
    quantity_kg=Decimal("20000.000"),
    operator=request.user,
)

# 4. Get cell suggestions for incoming grain
suggestions = suggest_cell(
    tenant_id=tenant_id,
    branch_id=branch_id,
    grain_type_id=grain_type_id,
    campaign_id=campaign_id,
    grado=2,
    incoming_kg=Decimal("28500.000"),
)
# Returns: list[CellSuggestion] sorted by score descending

# 5. Generate stock report
report = generate_stock_report(
    tenant_id=tenant_id,
    branch_id=branch_id,      # optional filter
    grain_type_id=None,       # optional filter
    campaign_id=None,         # optional filter
)
```

---

## Quick Reference: Key Models

```python
# All 3 new models are in apps/acopio/models/
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement

# StorageUnit types
StorageUnit.UnitType.SILO_VERTICAL    # vertical concrete silo
StorageUnit.UnitType.CELDA_HORIZONTAL # horizontal storage cell
StorageUnit.UnitType.SECADERO_BIN     # wet holding bin

# GrainMovement types (ADJUSTMENT is the 5th type, added for SRS-AL06)
GrainMovement.MovementType.DEPOSIT       # + inflow from romaneo
GrainMovement.MovementType.WITHDRAWAL    # − outflow for dispatch
GrainMovement.MovementType.TRANSFER_IN   # + from inter-silo transfer
GrainMovement.MovementType.TRANSFER_OUT  # − from inter-silo transfer
GrainMovement.MovementType.ADJUSTMENT    # ± reconciliation correction
```

---

## Quick Reference: Queryset Patterns

```python
# StorageUnit list with occupancy (SINGLE QUERY - no N+1)
from django.db.models import Sum
from django.db.models.functions import Coalesce

units = StorageUnit.objects.annotate(
    current_occupancy_kg=Coalesce(
        Sum("grain_lots__movements__quantity_kg"),
        Decimal("0.000"),
    )
).select_related("branch", "current_grain_type")

# GrainLot running balance (always computed from movements; stored on lot)
lot = GrainLot.objects.get(pk=lot_id)
assert lot.total_kg == lot.movements.aggregate(total=Sum("quantity_kg"))["total"]

# All movements for a lot (newest first)
movements = GrainMovement.objects.filter(
    grain_lot=lot
).select_related("romaneo", "created_by").order_by("-movement_at")

# Cross-lot stock report for a branch+campaign
from django.db.models import Sum
stock = GrainLot.objects.filter(
    tenant_id=tenant_id,
    campaign_id=campaign_id,
    branch_id=branch_id,
).values("grain_type__code", "storage_unit__name").annotate(
    total_kg=Sum("total_kg")
)
```

---

## Quick Reference: Transaction Patterns

```python
from django.db import transaction

# All movement creation MUST be within a transaction
with transaction.atomic():
    lot, created = GrainLot.objects.select_for_update().get_or_create(
        tenant=romaneo.tenant,
        branch=romaneo.branch,
        grain_type=romaneo.grain_type,
        campaign=romaneo.campaign,
        grado=grado,
        storage_unit=storage_unit,
        defaults={"is_own_grain": is_own_grain, "total_kg": Decimal("0.000"), ...},
    )
    movement = GrainMovement.objects.create(...)  # raises ValueError if pk exists
    lot.total_kg += quantity_kg
    lot.save(update_fields=["total_kg", "updated_at"])
```

---

## Quick Reference: Test Setup

```python
# Use conftest.py fixtures
def test_deposit_creates_lot(
    romaneo_conforme,    # new fixture added by A3
    storage_unit_factory,
    grain_lot_factory,
    db,
):
    storage_unit = storage_unit_factory(branch=romaneo_conforme.branch)
    movement, lot = create_deposit_from_romaneo(
        romaneo=romaneo_conforme,
        storage_unit=storage_unit,
        is_own_grain=False,
    )
    assert lot.total_kg == romaneo_conforme.peso_neto_conforme_kg
    assert GrainMovement.objects.filter(grain_lot=lot).count() == 1
```

---

## Quick Reference: Checkpoint Commands

```bash
# Gate 1: Models importable + migration clean
cd backend && DJANGO_SETTINGS_MODULE=gravitea.settings.test \
    ../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement
print('Models OK')
"

# Gate 2: URL routing + serializers
cd backend && DJANGO_SETTINGS_MODULE=gravitea.settings.test \
    ../.venv/bin/python -c "
import django; django.setup()
from django.urls import reverse
print(reverse('storage-unit-list'))
print('URLs OK')
"

# Gate 3: Run full test suite (NEVER run pytest directly)
bash scripts/run-tests-external.sh -n spec12-storage tests/acopio/
cat Docs/Tests/spec12-storage.status   # RUNNING → PASSED / FAILED
```

---

## Common Mistakes to Avoid

| Mistake | Correct Approach |
|---------|-----------------|
| `GrainMovement.objects.filter(...).update(...)` | Never. Raises ValueError. Create a counter-entry movement instead. |
| `grain_lot.total_kg = 0; grain_lot.save()` without movement | Never. Always create GrainMovement + update balance in same transaction. |
| Import StockMovement for grain | Import GrainMovement from apps.acopio.models. |
| `StorageUnit.current_occupancy_kg` as a model field | It's a derived annotated value. Access via `.annotate(...)` in queryset. |
| Two deposits same combination → two lots | Use `get_or_create` with full composite key. Second deposit reuses the lot. |
| `delete()` on GrainMovement | Raises ValueError. Use adjustment movement for corrections. |
