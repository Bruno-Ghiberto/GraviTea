# Implementation Context: Storage & Position (Spec-12)

**Branch**: `012-storage-position`
**Date**: 2026-03-19
**Spec**: `specs/012-storage-position/spec.md`
**Tasks**: `specs/012-storage-position/tasks.md` (50 tasks, 11 phases)

---

## Agent Team Orchestration Protocol

### Team Composition

| Agent | Type | Model | Mission |
|-------|------|-------|---------|
| **Orchestrator** | You (human/operator) | — | Spawn agents via tmux, dispatch waves, run checkpoints |
| **A1** | `python-expert` | Sonnet 4.6 | Models, services, migration, RLS, management command |
| **A2** | `backend-architect` | Sonnet 4.6 | Serializers, viewsets, URL registration |
| **A3** | `quality-engineer` | Sonnet 4.6 | All test files, gate checks, final validation |

### tmux Layout (MANDATORY)

```bash
# Create session with 3 panes (one per agent)
tmux new-session -s spec12 -n agents \; \
  split-window -h \; \
  split-window -v \; \
  select-layout tiled

# Pane 0 (top-left):  A1 — python-expert
# Pane 1 (top-right): A2 — backend-architect
# Pane 2 (bottom):    A3 — quality-engineer
```

### Agent Spawning Protocol

Each agent is spawned in its own tmux pane with Claude Code:

```bash
# Pane 0 — A1
claude --model sonnet "Read Docs/PROMPTS/spec-12-storage/agents/agent-a1-models-services.md and await further instructions."

# Pane 1 — A2
claude --model sonnet "Read Docs/PROMPTS/spec-12-storage/agents/agent-a2-api.md and await further instructions."

# Pane 2 — A3
claude --model sonnet "Read Docs/PROMPTS/spec-12-storage/agents/agent-a3-tests.md and await further instructions."
```

---

## Wave Execution Order

### Wave 1: Foundation (A1 solo)

**Tasks**: T001–T008
**Blocks**: ALL subsequent waves — no agent work until Wave 1 passes Gate 1.

| Task | Agent | Description |
|------|-------|-------------|
| T001 | A1 | Add storage fixtures to `conftest.py` |
| T002 | A1 | Create `StorageUnit` model |
| T003 | A1 | Create `GrainLot` model |
| T004 | A1 | Create `GrainMovement` model (immutable) |
| T005 | A1 | Add FKs to Romaneo + update CONFORME allowlist |
| T006 | A1 | Update `__init__.py` + `admin.py` |
| T007 | A1 | Generate migration `0003_storage_position.py` |
| T008 | A1 | Append RLS policies to `acopio_rls.sql` |

**Checkpoint — Gate 1**:

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

### Wave 2: MVP — US1 + US2 (A1 + A2 parallel, then A3)

**Prerequisite**: Gate 1 PASSED

**Step 2a — Parallel (A1 + A2)**:

| Task | Agent | Description |
|------|-------|-------------|
| T010 | A2 | `StorageUnitSerializer` |
| T015 | A2 | `GrainLotSerializer` + `GrainMovementSerializer` |
| T011 | A2 | `StorageUnitViewSet` (annotated queryset) |
| T017 | A2 | `GrainLotViewSet` + `GrainMovementViewSet` (append-only) |
| T012 | A2 | Register `storage-units` route + update exports |
| T018 | A2 | Register `grain-lots` + nested `movements` routes |
| T016 | A1 | `create_deposit_from_romaneo` service |

**Step 2b — Sequential (A2, requires A1's T016)**:

| Task | Agent | Description |
|------|-------|-------------|
| T019 | A2 | Update `RomaneoSerializer` (add `storage_unit` patchable) |
| T020 | A2 | Update `confirmar` action (call deposit service) |

**Step 2c — Tests (A3, after 2a+2b)**:

| Task | Agent | Description |
|------|-------|-------------|
| T009 | A3 | `StorageUnit` model tests |
| T013 | A3 | `StorageUnit` API tests |
| T014 | A3 | Deposit flow ledger tests |
| T021 | A3 | Deposit flow API tests |

**Checkpoint — Gate 2**:

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

Then run MVP tests:
```bash
bash scripts/run-tests-external.sh -n spec12-mvp tests/acopio/
cat Docs/Tests/spec12-mvp.status
```

### Wave 3: P2 Features — US3, US4, US5, US6 (A1 + A2 parallel, then A3)

**Prerequisite**: Gate 2 PASSED

**Step 3a — Services (A1)**:

| Task | Agent | Description |
|------|-------|-------------|
| T023 | A1 | `suggest_cell` service |
| T027 | A1 | `create_withdrawal` service |
| T031 | A1 | `transfer_grain` service |
| T035 | A1 | `generate_stock_report` service |

**Step 3b — Endpoints (A2, after A1 creates services)**:

| Task | Agent | Description |
|------|-------|-------------|
| T024 | A2 | `suggest` action + serializers |
| T028 | A2 | Dispatch via `GrainMovementViewSet` |
| T032 | A2 | Transfer `@action` on `GrainLotViewSet` |
| T036 | A2 | `stock-report` action + serializer |

**Step 3c — Tests (A3)**:

| Task | Agent | Description |
|------|-------|-------------|
| T022 | A3 | CellSuggestion service tests |
| T025 | A3 | Suggest endpoint API tests |
| T026 | A3 | Withdrawal ledger tests |
| T029 | A3 | Dispatch API tests |
| T030 | A3 | Transfer ledger tests |
| T033 | A3 | Transfer API tests |
| T034 | A3 | StockReport service tests |
| T037 | A3 | Stock-report API tests |

### Wave 4: P3 Features — US7, US8 (A1 + A2 parallel, then A3)

**Prerequisite**: Wave 3 tests pass

**Step 4a — Services (A1)**:

| Task | Agent | Description |
|------|-------|-------------|
| T039 | A1 | `reconcile` service |
| T041 | A1 | `check_grain_balance` management command |
| T044 | A1 | `CampaignCloseService` |

**Step 4b — Endpoints (A2)**:

| Task | Agent | Description |
|------|-------|-------------|
| T040 | A2 | Reconcile `@action` on `StorageUnitViewSet` |
| T045 | A2 | Campaign close `@action` on `CampanaConfigViewSet` |

**Step 4c — Tests (A3)**:

| Task | Agent | Description |
|------|-------|-------------|
| T038 | A3 | Reconciliation service tests |
| T042 | A3 | Reconciliation API tests |
| T043 | A3 | Campaign close service tests |
| T046 | A3 | Campaign close API tests |

### Wave 5: Polish (A3 leads)

| Task | Agent | Description |
|------|-------|-------------|
| T047 | A3 | Gate 1 re-verification |
| T048 | A3 | Gate 2 re-verification |
| T049 | A3 | Full test suite via `scripts/run-tests-external.sh` |
| T050 | A3 | Management command drift check |

---

## Files to Create / Files to Modify

### Files to CREATE (Agent Assignment)

| File | Agent | Wave |
|------|-------|------|
| `backend/apps/acopio/models/storage_unit.py` | A1 | 1 |
| `backend/apps/acopio/models/grain_lot.py` | A1 | 1 |
| `backend/apps/acopio/models/grain_movement.py` | A1 | 1 |
| `backend/apps/acopio/services/storage.py` | A1 | 2–4 |
| `backend/apps/acopio/serializers/storage.py` | A2 | 2–4 |
| `backend/apps/acopio/views/storage.py` | A2 | 2–4 |
| `backend/apps/acopio/management/commands/check_grain_balance.py` | A1 | 4 |
| `backend/apps/acopio/migrations/0003_storage_position.py` | A1 (auto) | 1 |
| `backend/tests/acopio/test_storage_models.py` | A3 | 2 |
| `backend/tests/acopio/test_grain_ledger.py` | A3 | 2–3 |
| `backend/tests/acopio/test_storage_api.py` | A3 | 2–4 |
| `backend/tests/acopio/test_storage_services.py` | A3 | 3–4 |

### Files to MODIFY (Agent Assignment)

| File | Agent | Wave | What Changes |
|------|-------|------|--------------|
| `backend/apps/acopio/models/romaneo.py` | A1 | 1 | Add `storage_unit` + `grain_lot` FKs; update CONFORME allowlist |
| `backend/apps/acopio/models/__init__.py` | A1 | 1 | Re-export 3 new models |
| `backend/apps/acopio/admin.py` | A1 | 1 | Register 3 new models |
| `backend/apps/acopio/serializers/romaneo.py` | A2 | 2 | Add `storage_unit` patchable field |
| `backend/apps/acopio/serializers/__init__.py` | A2 | 2 | Re-export new serializers |
| `backend/apps/acopio/views/romaneo.py` | A2 | 2 | Modify `confirmar` action to call deposit service |
| `backend/apps/acopio/views/reference_data.py` | A2 | 4 | Add `close` action to `CampanaConfigViewSet` |
| `backend/apps/acopio/views/__init__.py` | A2 | 2 | Re-export new viewsets |
| `backend/apps/acopio/urls.py` | A2 | 2 | Register storage-units, grain-lots, nested movements |
| `backend/database/sql/acopio_rls.sql` | A1 | 1 | Append RLS for 3 new tables |
| `backend/tests/acopio/conftest.py` | A1 | 1 | Add storage fixtures |

---

## Key Code Patterns

### Pattern 1: TenantBoundModel Inheritance

All 3 new models inherit from `TenantBoundModel` and declare both managers:

```python
import uuid
from django.db import models
from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models import Tenant

class StorageUnit(TenantBoundModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="storage_units")
    # ... fields ...

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_storageunit"
        constraints = [...]
        indexes = [...]
```

### Pattern 2: GrainMovement Full Immutability

Same pattern as `MermaCalculation` (see `backend/apps/acopio/models/merma_calculation.py:83-91`):

```python
class GrainMovement(TenantBoundModel):
    # ... fields ...

    def save(self, *args, **kwargs):
        """Enforce full immutability — only INSERT allowed."""
        if not self._state.adding:
            raise ValueError("GrainMovement is immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion — immutable ledger entry."""
        raise ValueError("GrainMovement is immutable and cannot be deleted.")
```

### Pattern 3: Romaneo CONFORME Allowlist Update (T005)

**CRITICAL**: The existing CONFORME gate is at `romaneo.py:200-213`. The current allowlist is:

```python
allowed_fields = {"tara_kg", "peso_neto_bruto_kg", "ts_tara", "status"}
```

Spec-12 must change this to:

```python
allowed_fields = {
    "tara_kg", "peso_neto_bruto_kg", "ts_tara", "status",
    "storage_unit_id", "grain_lot_id",  # spec-12: deposit service sets these at CONFORME
}
```

**Why**: The deposit service (`create_deposit_from_romaneo`) runs AFTER the romaneo
reaches CONFORME. It must set `romaneo.grain_lot` and save. Without this allowlist
update, the save will raise `ValueError("Romaneo CONFORME is immutable. Cannot change 'grain_lot_id'.")`.

Note: ForeignKey fields use `attname` which is `storage_unit_id` and `grain_lot_id`
(not `storage_unit` or `grain_lot`).

### Pattern 4: Deposit Service (Atomic Transaction)

```python
from decimal import Decimal
from django.db import transaction

def create_deposit_from_romaneo(romaneo, storage_unit, is_own_grain=False):
    """FR-012: Create deposit movement from confirmed romaneo."""
    with transaction.atomic():
        lot, created = GrainLot.objects.select_for_update().get_or_create(
            tenant=romaneo.tenant,
            branch=romaneo.branch,
            grain_type=romaneo.grain_type,
            campaign=romaneo.campaign,
            grado=romaneo.grado_asignado or 0,
            storage_unit=storage_unit,
            defaults={
                "is_own_grain": is_own_grain,
                "total_kg": Decimal("0.000"),
                "created_by": romaneo.operator_id,
            },
        )

        quantity = romaneo.peso_neto_conforme_kg
        movement = GrainMovement.objects.create(
            tenant=romaneo.tenant,
            grain_lot=lot,
            movement_type=GrainMovement.MovementType.DEPOSIT,
            quantity_kg=quantity,
            romaneo=romaneo,
            created_by=romaneo.operator_id,
        )

        lot.total_kg += quantity
        lot.save(update_fields=["total_kg", "updated_at"])

        # Update storage unit grain type if empty
        if storage_unit.current_grain_type is None:
            storage_unit.current_grain_type = romaneo.grain_type
            storage_unit.save(update_fields=["current_grain_type", "updated_at"])

        # Link romaneo back to lot (requires CONFORME allowlist update)
        romaneo.grain_lot = lot
        romaneo.save(update_fields=["grain_lot_id", "updated_at"])

    return movement, lot
```

### Pattern 5: Annotated Occupancy Queryset

```python
from django.db.models import Sum
from django.db.models.functions import Coalesce

class StorageUnitViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return (
            StorageUnit.objects
            .annotate(
                current_occupancy_kg=Coalesce(
                    Sum("grain_lots__movements__quantity_kg"),
                    Decimal("0.000"),
                )
            )
            .select_related("branch", "current_grain_type")
        )
```

### Pattern 6: Negative Balance Prevention

```python
def create_withdrawal(grain_lot, quantity_kg, operator, reference_document=None, notes=None):
    """FR-015: Record grain dispatch. Rejects if insufficient balance."""
    with transaction.atomic():
        lot = GrainLot.objects.select_for_update().get(pk=grain_lot.pk)
        if lot.total_kg < quantity_kg:
            raise ValueError(
                f"Insufficient grain stock. Lot '{lot.lot_code}' has {lot.total_kg} kg "
                f"but attempted withdrawal is {quantity_kg} kg."
            )
        movement = GrainMovement.objects.create(
            tenant=lot.tenant,
            grain_lot=lot,
            movement_type=GrainMovement.MovementType.WITHDRAWAL,
            quantity_kg=-quantity_kg,  # Stored NEGATIVE for outflow
            reference_document=reference_document,
            notes=notes,
            created_by=operator,
        )
        lot.total_kg -= quantity_kg
        lot.save(update_fields=["total_kg", "updated_at"])
    return movement
```

### Pattern 7: Deadlock-Safe Transfer

```python
def transfer_grain(source_lot, destination_lot, quantity_kg, operator, notes=None):
    """FR-016: Atomic inter-silo transfer with PK-ordered locking."""
    if source_lot.pk == destination_lot.pk:
        raise ValueError("Source and destination lots must be different.")

    with transaction.atomic():
        # Lock in ascending PK order to prevent deadlock
        pks = sorted([source_lot.pk, destination_lot.pk])
        locked = list(GrainLot.objects.select_for_update().filter(pk__in=pks).order_by("pk"))
        src = next(l for l in locked if l.pk == source_lot.pk)
        dst = next(l for l in locked if l.pk == destination_lot.pk)

        if src.total_kg < quantity_kg:
            raise ValueError(f"Insufficient source balance: {src.total_kg} kg < {quantity_kg} kg")

        out_mv = GrainMovement.objects.create(
            tenant=src.tenant, grain_lot=src,
            movement_type=GrainMovement.MovementType.TRANSFER_OUT,
            quantity_kg=-quantity_kg, notes=notes, created_by=operator,
        )
        in_mv = GrainMovement.objects.create(
            tenant=dst.tenant, grain_lot=dst,
            movement_type=GrainMovement.MovementType.TRANSFER_IN,
            quantity_kg=quantity_kg, notes=notes, created_by=operator,
        )

        src.total_kg -= quantity_kg
        src.save(update_fields=["total_kg", "updated_at"])
        dst.total_kg += quantity_kg
        dst.save(update_fields=["total_kg", "updated_at"])

    return out_mv, dst
```

### Pattern 8: Append-Only ViewSet

```python
class GrainMovementViewSet(viewsets.ModelViewSet):
    """Immutable ledger — only GET + POST allowed."""
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]  # No PATCH/PUT/DELETE
    # ...
```

### Pattern 9: RomaneoViewSet.confirmar Modification (T020)

**IMPORTANT**: The existing action is `confirmar` (NOT `confirmar_conforme`).
- Method name: `confirmar` (Python)
- URL path: `romaneos/{id}/confirmar/`
- File: `backend/apps/acopio/views/romaneo.py:164-269`

Spec-12 adds deposit service call AFTER the existing logic. Insert between
line 267 (`romaneo.save()`) and line 269 (`return Response(...)`):

```python
    # -- Spec-12: Create deposit movement if storage_unit is assigned --
    if not romaneo.storage_unit:
        return Response(
            {"type": "missing_storage_unit",
             "detail": "storage_unit must be assigned before confirming."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from apps.acopio.services.storage import create_deposit_from_romaneo
    movement, lot = create_deposit_from_romaneo(
        romaneo=romaneo,
        storage_unit=romaneo.storage_unit,
        is_own_grain=False,  # spec-12 default; own-grain deferred to spec-13
    )
```

### Pattern 10: Auto lot_code Generation

```python
class GrainLot(TenantBoundModel):
    def save(self, *args, **kwargs):
        if not self.lot_code:
            self.lot_code = self._generate_lot_code()
        super().save(*args, **kwargs)

    def _generate_lot_code(self):
        branch_code = self.branch.code if hasattr(self.branch, 'code') else str(self.branch_id)[:4]
        grain_code = self.grain_type.code
        campaign_code = self.campaign.campaign_code.replace("/", "")
        return f"{branch_code}-{grain_code}-{campaign_code}-{self.grado}"
```

---

## Testing Protocol

**ALWAYS** use the external test runner. NEVER run pytest directly inside Claude Code.

```bash
# Run specific test file
bash scripts/run-tests-external.sh -n spec12-models tests/acopio/test_storage_models.py

# Run full acopio suite
bash scripts/run-tests-external.sh -n spec12-final tests/acopio/

# Check result
cat Docs/Tests/spec12-final.status   # RUNNING → PASSED / FAILED
```

**Test targets**: 40+ tests, 90%+ coverage on new code.

**Test organization** (4 test files):
- `test_storage_models.py` — Model constraints, immutability, TenantBound
- `test_grain_ledger.py` — Balance invariants, deposit, withdrawal, transfer atomicity
- `test_storage_api.py` — CRUD, HTTP status codes, tenant isolation, immutable endpoints
- `test_storage_services.py` — CellSuggestion, StockReport, Reconciliation, CampaignClose

---

## Integration Points with Other Specs

| Integration | Spec | Detail |
|-------------|------|--------|
| Romaneo FK additions | Spec-11 | `storage_unit` + `grain_lot` FKs added to Romaneo model via migration 0003 |
| `confirmar` action hook | Spec-11 | Deposit service called after ANALIZADO→CONFORME transition |
| CONFORME allowlist | Spec-11 | `storage_unit_id` + `grain_lot_id` added to mutable-fields set |
| GrainType reference | Spec-10 | StorageUnit.current_grain_type FK, GrainLot.grain_type FK |
| CampanaConfig reference | Spec-10 | GrainLot.campaign FK, CampaignCloseService reads campaign state |
| `confirmar` serializer | Spec-11 | `ConfirmarSerializer` unchanged; storage_unit set via PATCH before confirm |

**ADR-009 Boundary**: GrainMovement (apps/acopio) is SEPARATE from StockMovement (apps/inventario).
NEVER import StockMovement for grain tracking. They share the immutability pattern but serve
different inventory dimensions (continuous kg vs discrete units).

---

## Done Criteria

- [ ] All 3 models importable: `from apps.acopio.models import StorageUnit, GrainLot, GrainMovement`
- [ ] Migration `0003_storage_position.py` applies cleanly
- [ ] RLS policies appended for all 3 new tables
- [ ] `Romaneo.storage_unit` and `Romaneo.grain_lot` FKs present and nullable
- [ ] CONFORME mutable-fields allowlist includes `storage_unit_id` and `grain_lot_id`
- [ ] All URL routes resolve: `storage-unit-list`, `grain-lot-list`
- [ ] `confirmar` action creates deposit movement when `storage_unit` is set
- [ ] GrainMovement is immutable: PATCH/PUT/DELETE return HTTP 405
- [ ] `check_grain_balance` management command reports no drift on clean data
- [ ] `Docs/Tests/spec12-final.status` reads `PASSED`
- [ ] 40+ tests collected, zero failures
- [ ] 90%+ coverage on new code in `apps/acopio/models/storage_unit.py`, `grain_lot.py`, `grain_movement.py`, `services/storage.py`
