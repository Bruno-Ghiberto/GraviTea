---
spec: "012"
name: "Storage & Position"
type: Implementation
phase: Plan
created: 2026-03-19
context_for: "/speckit.plan"
depends_on: [spec-10, spec-11]
blocks: [spec-13]
agents: [A1, A2, A3]
---

# Spec-12: Storage & Position -- Plan Context

> **For**: Implementation agents A1--A3 executing in tmux multi-pane layout
> **Produces**: 3 Django models in `backend/apps/acopio/`, storage service layer
> (`CellSuggestionService`, `StockReportService`, `ReconciliationService`,
> `CampaignCloseService`), DRF serializers + viewsets, Romaneo FK additions,
> database migration 0003, and full test suite
> **Spec type**: Implementation (multi-agent, wave execution)

---

## Component Overview

Spec-12 implements the physical storage infrastructure and grain position ledger
for the acopio operation. It builds directly on spec-10 reference data (GrainType,
CampanaConfig) and spec-11 transactional data (Romaneo, QualityAnalysis) to
complete the core grain reception workflow: grain arrives via romaneo → gets
assigned to a silo → deposit movement recorded → grain lot balance updated.

**What is being built:**

1. **3 Django models** -- `StorageUnit` (physical silo/celda/bin with capacity
   and IoT anchor), `GrainLot` (logical grain position per composite key with
   running balance), and `GrainMovement` (immutable append-only ledger entry,
   5 movement types: DEPOSIT, WITHDRAWAL, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT).
2. **Service layer** (`services/storage.py`) -- `CellSuggestionService` (ranked
   silo recommendation for incoming grain), `StockReportService` (real-time stock
   report from ledger aggregation), `ReconciliationService` (physical vs ledger
   variance + adjustment movements), `CampaignCloseService` (carry-forward workflow
   per SRS-AL07).
3. **DRF serializers** -- StorageUnit (with derived `current_occupancy_kg`),
   GrainLot (with lot_code auto-generation), GrainMovement (append-only),
   plus cell-suggestion and stock-report response serializers.
4. **DRF viewsets** -- `StorageUnitViewSet` (CRUD + soft-deactivate +
   suggest action), `GrainLotViewSet` (read + list), `GrainMovementViewSet`
   (create + read + list only; no PATCH/DELETE/PUT).
5. **Romaneo FK additions** -- `storage_unit` (SET_NULL, nullable) and
   `grain_lot` (SET_NULL, nullable) added to the existing Romaneo model via
   migration 0003. These are mandated by Data Model v1.0 Group 6 and REST API
   Design §5 (patchable fields) but were intentionally deferred from spec-11.
6. **Full test suite** -- Model unit tests, immutability enforcement, running
   balance tests, cell suggestion scoring, API integration tests, tenant isolation,
   and reconciliation workflow. Minimum 35 tests, 90%+ coverage on new code.

**All 3 new models are TENANT-SCOPED** -- they inherit `TenantBoundModel`, use
`TenantBoundManager` with fail-closed filtering, and receive RLS policies. This
is the same pattern as Romaneo, QualityAnalysis, and MermaCalculation in spec-11.

**GrainMovement is FULLY IMMUTABLE** -- same pattern as `MermaCalculation` in
spec-11 and `StockMovement` in inventario. `save()` raises `ValueError` for
existing records; `delete()` raises `ValueError` always.

**GrainMovement is NOT StockMovement** -- per ADR-009 (Dual Inventory), grain
uses its own continuous-kg ledger (`GrainMovement`), completely separate from
the discrete-units ledger (`StockMovement`) in `apps/inventario`.

---

## Agent Team Orchestration Protocol

### Team Structure

| Agent | Role | Deliverables |
|-------|------|-------------|
| **A1** | Models + Services | `models/storage_unit.py`, `models/grain_lot.py`, `models/grain_movement.py`, `models/__init__.py` update, `admin.py` update, `services/storage.py` (4 services), `0003_storage_position.py` migration, `database/sql/acopio_rls.sql` update |
| **A2** | API Layer | `serializers/storage.py`, `serializers/__init__.py` update, `views/storage.py` (3 viewsets + actions), `views/__init__.py` update, `urls.py` update, `serializers/romaneo.py` update (add `storage_unit` patchable) |
| **A3** | Tests | `tests/acopio/test_storage_models.py`, `tests/acopio/test_storage_api.py`, `tests/acopio/test_grain_ledger.py`, `tests/acopio/test_storage_services.py`, `tests/acopio/conftest.py` update |

### Wave Execution Order

```
Wave 1 (sequential): A1 -- Models + Services
  Prerequisite: None
  Must complete before: Wave 2
  Deliverable: All 3 models importable, migration applies, services importable

Wave 2 (sequential): A2 -- API Layer
  Prerequisite: Wave 1 Gate 1 PASS (models importable, migration clean)
  Deliverable: Serializers + viewsets importable, URL routing resolves

Wave 3 (sequential): A3 -- Full Test Suite
  Prerequisite: Wave 2 Gate 2 PASS (URL routing resolves, serializers importable)
  Deliverable: All tests pass (35+ tests, 90%+ coverage)
```

**Note**: Unlike spec-11 (6 parallel agents), spec-12 uses 3 sequential agents.
This is appropriate because A2 has hard dependencies on A1 model definitions and
A3 needs both A1 and A2 complete for full coverage. The sequential constraint
avoids interface mismatches between agents.

### tmux Layout (REQUIRED)

Create a 3-pane tmux session before starting execution. Each pane runs one Claude
Code agent with its dedicated instruction file.

```bash
# Create session
tmux new-session -d -s spec12 -n agents

# Split into 3 vertical panes
tmux split-window -v -t spec12:agents
tmux split-window -v -t spec12:agents.1

# Pane assignment:
# Pane 0 (top):    A1 -- Models + Services
# Pane 1 (middle): A2 -- API Layer
# Pane 2 (bottom): A3 -- Tests

# Attach
tmux attach -t spec12
```

**Pane activation by wave:**

| Wave | A1 (P0) | A2 (P1) | A3 (P2) |
|------|---------|---------|---------|
| 1    | ACTIVE  | IDLE    | IDLE    |
| 2    | IDLE    | ACTIVE  | IDLE    |
| 3    | IDLE    | IDLE    | ACTIVE  |

### Agent Instruction Files

Each agent reads its dedicated instruction file before starting work. These files
are created by `/speckit.design` (Phase D) and must exist before launching the
tmux session:

- `Docs/PROMPTS/spec-12-storage/agents/A1-models.md`
- `Docs/PROMPTS/spec-12-storage/agents/A2-api.md`
- `Docs/PROMPTS/spec-12-storage/agents/A3-tests.md`

Each agent instruction file must reference:
- This plan file (`12-plan.md`) for wave execution and checkpoint gates
- The specification context (`12-specify.md`) for field definitions and acceptance criteria
- The spec itself (`specs/012-storage-position/spec.md`) for user stories and functional requirements

---

## Files to Create

### A1: Models + Services

| File | Description |
|------|-------------|
| `backend/apps/acopio/models/storage_unit.py` | StorageUnit model (TenantBound, 12 fields, 3 unit types, uniqueness constraint, index on tenant+branch+is_active) |
| `backend/apps/acopio/models/grain_lot.py` | GrainLot model (TenantBound, composite natural key, running total_kg balance, is_own_grain flag, auto lot_code) |
| `backend/apps/acopio/models/grain_movement.py` | GrainMovement model (TenantBound, FULLY IMMUTABLE, 5 movement types, notes field, no updated_at) |
| `backend/apps/acopio/services/storage.py` | CellSuggestionService, StockReportService, ReconciliationService, CampaignCloseService -- all business logic lives here |
| `backend/apps/acopio/migrations/0003_storage_position.py` | Auto-generated migration: create 3 tables + ALTER acopio_romaneo ADD storage_unit_id + grain_lot_id |

### A2: API Layer

| File | Description |
|------|-------------|
| `backend/apps/acopio/serializers/storage.py` | `StorageUnitSerializer` (with computed `current_occupancy_kg`), `GrainLotSerializer`, `GrainMovementSerializer`, `CellSuggestionRequestSerializer`, `CellSuggestionResponseSerializer`, `StockReportSerializer` |
| `backend/apps/acopio/views/storage.py` | `StorageUnitViewSet` (CRUD + `suggest` action + `stock-report` action), `GrainLotViewSet` (list/retrieve only), `GrainMovementViewSet` (create/list/retrieve only -- no PATCH/DELETE/PUT) |

### A3: Tests

| File | Description |
|------|-------------|
| `backend/tests/acopio/test_storage_models.py` | StorageUnit creation/uniqueness constraint; GrainLot composite key + lot_code auto-generation; GrainMovement immutability (ValueError on save/delete for existing); TenantBoundModel inheritance for all 3 |
| `backend/tests/acopio/test_grain_ledger.py` | Deposit from romaneo (get_or_create lot + balance update); withdrawal positive/negative balance scenarios; transfer atomicity (TRANSFER_IN/TRANSFER_OUT paired); negative balance prevention; running balance consistency |
| `backend/tests/acopio/test_storage_api.py` | StorageUnit CRUD endpoints; occupancy annotation returned in list; tenant isolation (cross-tenant 404); cell suggestion endpoint; movements append-only (HTTP 405 for PATCH/DELETE); stock-report endpoint; reconciliation endpoint |
| `backend/tests/acopio/test_storage_services.py` | CellSuggestionService ranking (type match > grade match > capacity); StockReportService aggregation correctness; ReconciliationService variance detection + adjustment creation; CampaignCloseService validation + carry-forward |

---

## Files to Modify

| File | Agent | Change |
|------|-------|--------|
| `backend/apps/acopio/models/__init__.py` | A1 | Add re-exports for `StorageUnit`, `GrainLot`, `GrainMovement` |
| `backend/apps/acopio/admin.py` | A1 | Add admin registration for `StorageUnit`, `GrainLot`, `GrainMovement` |
| `backend/database/sql/acopio_rls.sql` | A1 | Append RLS policies for `acopio_storageunit`, `acopio_grainlot`, `acopio_grainmovement` tables |
| `backend/apps/acopio/models/romaneo.py` | A1 | Add `storage_unit` (FK StorageUnit, SET_NULL, null=True) and `grain_lot` (FK GrainLot, SET_NULL, null=True) fields -- Data Model v1.0 Group 6 |
| `backend/apps/acopio/serializers/__init__.py` | A2 | Add re-exports for new storage serializer classes |
| `backend/apps/acopio/serializers/romaneo.py` | A2 | Add `storage_unit` to patchable fields per REST API Design §5; add `grain_lot` as read-only in response |
| `backend/apps/acopio/views/__init__.py` | A2 | Add re-exports for `StorageUnitViewSet`, `GrainLotViewSet`, `GrainMovementViewSet` |
| `backend/apps/acopio/urls.py` | A2 | Register `storage-units`, `grain-lots` routes on router; add nested movement routes |
| `backend/tests/acopio/conftest.py` | A3 | Add storage fixtures: `storage_unit_factory`, `grain_lot_factory`, `grain_movement_factory`, `romaneo_conforme` state fixture |

---

## Key Code Patterns

### Pattern 1: TenantBoundModel Inheritance

All 3 new models inherit `TenantBoundModel`. Reference:
`backend/apps/core/models/mixins.py` (`TenantBoundModel` class) and
`backend/apps/core/managers/tenant_bound.py` (`TenantBoundManager`).

```python
import uuid

from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class StorageUnit(TenantBoundModel):
    """
    Physical grain storage location (silo, celda, or drying bin).

    TENANT-SCOPED entity -- inherits TenantBoundModel.
    """

    class UnitType(models.TextChoices):
        SILO_VERTICAL = "SILO_VERTICAL", "Silo Vertical"
        CELDA_HORIZONTAL = "CELDA_HORIZONTAL", "Celda Horizontal"
        SECADERO_BIN = "SECADERO_BIN", "Secadero / Bin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="storage_units",
    )
    # ... fields ...

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_storageunit"
        ordering = ["branch", "name"]
```

Key points from `TenantBoundManager`:
- `get_queryset()` implements FAIL-CLOSED: if `tenant_id` is None, raises `ValueError`.
- Always filters by `tenant_id = get_current_tenant_id()`.
- `AllObjectsManager` provides unscoped access for system operations and immutability checks.

### Pattern 2: GrainMovement Full Immutability

Reference: `backend/apps/inventario/models.py` lines 620-669 (`StockMovement.save()`)
and `backend/apps/acopio/models/merma_calculation.py` (`MermaCalculation.save()`).
GrainMovement uses the same full-immutability pattern as MermaCalculation.

```python
def save(self, *args: object, **kwargs: object) -> None:
    """Enforce full immutability -- no updates allowed. Append-only."""
    if self.pk and GrainMovement.all_objects.filter(pk=self.pk).exists():
        raise ValueError(
            "GrainMovement records are fully immutable. "
            "Cannot update or overwrite an existing record. "
            "Corrections are made by creating new counter-entry movements."
        )
    if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
        self.tenant_id = self.tenant.id
    self._validate_tenant_references()
    super().save(*args, **kwargs)


def delete(self, *args: object, **kwargs: object) -> None:
    """Prevent deletion of GrainMovement records."""
    raise ValueError(
        "GrainMovement records cannot be deleted. "
        "They are permanent audit records. "
        "Corrections are made by creating new counter-entry movements."
    )
```

**Important**: `GrainMovement` omits `updated_at` (ADR-034 normally mandates it).
The exception is justified because the model is fully immutable -- no updates
are possible, so `updated_at` would always equal `created_at`. Same precedent
as `MermaCalculation`.

### Pattern 3: GrainLot get_or_create and Deposit from Romaneo

The core FR-005 flow: when a Romaneo reaches CONFORME, create or reuse the
GrainLot and record the DEPOSIT movement. Uses `select_for_update` to prevent
race conditions on the running balance.

```python
# In services/storage.py

import uuid
from decimal import Decimal

from django.db import transaction

from apps.acopio.models import GrainLot, GrainMovement, Romaneo, StorageUnit


def create_deposit_from_romaneo(
    romaneo: Romaneo,
    storage_unit: StorageUnit,
    is_own_grain: bool,
) -> tuple[GrainMovement, GrainLot]:
    """
    Create or reuse a GrainLot and record a DEPOSIT movement.

    Called after the romaneo reaches CONFORME status. The operator assigns
    the storage_unit before or at CONFORME; this function resolves the lot.

    Args:
        romaneo: Romaneo in CONFORME status with peso_neto_conforme_kg set.
        storage_unit: Target StorageUnit selected by operator (or suggested).
        is_own_grain: True if acopiador purchased the grain (balance-sheet asset).

    Returns:
        Tuple of (movement, grain_lot).
    """
    with transaction.atomic():
        grado = romaneo.quality_analysis.grado

        grain_lot, created = GrainLot.objects.select_for_update().get_or_create(
            tenant=romaneo.tenant,
            branch=romaneo.branch,
            grain_type=romaneo.grain_type,
            campaign=romaneo.campaign,
            grado=grado,
            storage_unit=storage_unit,
            defaults={
                "is_own_grain": is_own_grain,
                "total_kg": Decimal("0.000"),
                "created_by": romaneo.operator,
            },
        )

        quantity_kg = romaneo.peso_neto_conforme_kg

        movement = GrainMovement.objects.create(
            tenant=romaneo.tenant,
            grain_lot=grain_lot,
            movement_type=GrainMovement.MovementType.DEPOSIT,
            romaneo=romaneo,
            quantity_kg=quantity_kg,
            created_by=romaneo.operator,
            device_id=romaneo.device_id,
        )

        # Update running balance
        grain_lot.total_kg += quantity_kg
        grain_lot.save(update_fields=["total_kg", "updated_at"])

        # Set StorageUnit.current_grain_type if previously empty
        if storage_unit.current_grain_type is None:
            storage_unit.current_grain_type = romaneo.grain_type
            storage_unit.save(update_fields=["current_grain_type", "updated_at"])

        # Update Romaneo Group 6 FKs for direct navigability
        romaneo.grain_lot = grain_lot
        romaneo.save(update_fields=["grain_lot", "updated_at"])

        return movement, grain_lot
```

**Note on `get_or_create` race condition**: `select_for_update()` on the queryset
does not prevent a race on INSERT (two transactions both seeing no existing lot).
Use `select_for_update(skip_locked=False)` combined with a `UNIQUE` constraint on
the composite key so that only one INSERT wins; the losing transaction retries
via `IntegrityError` -> retry loop. The database constraint is the final safety net.

### Pattern 4: Derived Field via Annotated Queryset

`current_occupancy_kg` is NOT stored on StorageUnit. It is computed on-demand
from the GrainMovement ledger using a single annotated queryset (no N+1 queries).
The annotation relies on the related_name chain:
`StorageUnit.grain_lots` → `GrainLot.movements`.

```python
# In views/storage.py -- StorageUnitViewSet

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce


class StorageUnitViewSet(viewsets.ModelViewSet):

    def get_queryset(self):
        """
        Annotate each StorageUnit with current_occupancy_kg derived from
        the GrainMovement ledger. Single-query approach -- no N+1.
        """
        return (
            StorageUnit.objects.annotate(
                current_occupancy_kg=Coalesce(
                    Sum("grain_lots__movements__quantity_kg"),
                    Decimal("0.000"),
                )
            )
            .select_related("branch", "current_grain_type")
            .order_by("branch", "name")
        )
```

In the serializer, expose `current_occupancy_kg` as a `SerializerMethodField` or
directly as a field sourced from the annotation:

```python
class StorageUnitSerializer(serializers.ModelSerializer):
    current_occupancy_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True, default=Decimal("0.000")
    )
    capacity_utilisation_pct = serializers.SerializerMethodField()

    def get_capacity_utilisation_pct(self, obj) -> float:
        if not obj.capacity_tonnes or obj.capacity_tonnes == 0:
            return 0.0
        occupancy = getattr(obj, "current_occupancy_kg", Decimal("0.000")) or Decimal("0.000")
        capacity_kg = obj.capacity_tonnes * 1000
        return round(float(occupancy / capacity_kg * 100), 2)
```

### Pattern 5: Negative Balance Prevention

All outflow movements (WITHDRAWAL, TRANSFER_OUT) must be rejected if the lot
balance would drop below zero. Use `select_for_update()` on the lot before
creating the movement to prevent race conditions.

```python
# In services/storage.py

def create_withdrawal(
    grain_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    reference_document: str | None = None,
    notes: str | None = None,
) -> GrainMovement:
    """
    Record a grain dispatch (WITHDRAWAL). Rejects if insufficient balance.

    Args:
        quantity_kg: Positive amount being dispatched (stored as negative).
    """
    with transaction.atomic():
        # Lock the lot row to prevent concurrent withdrawals
        lot = GrainLot.objects.select_for_update().get(pk=grain_lot.pk)

        if lot.total_kg < quantity_kg:
            raise ValueError(
                f"Insufficient grain stock. Lot '{lot.lot_code}' has {lot.total_kg} kg "
                f"but attempted withdrawal is {quantity_kg} kg. "
                f"Shortfall: {quantity_kg - lot.total_kg} kg."
            )

        movement = GrainMovement.objects.create(
            tenant=lot.tenant,
            grain_lot=lot,
            movement_type=GrainMovement.MovementType.WITHDRAWAL,
            quantity_kg=-quantity_kg,  # outflow stored as negative
            reference_document=reference_document,
            notes=notes,
            created_by=operator,
        )

        lot.total_kg -= quantity_kg
        lot.save(update_fields=["total_kg", "updated_at"])

        return movement
```

### Pattern 6: Atomic Transfer Between Storage Units

Transfer creates two GrainMovement entries in a single transaction. Locks both
lot rows before writing to prevent partial state.

```python
# In services/storage.py

def transfer_grain(
    source_lot: GrainLot,
    destination_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    notes: str | None = None,
) -> tuple[GrainMovement, GrainLot]:
    """
    Transfer grain between two storage units atomically.
    Creates paired TRANSFER_OUT (source) + TRANSFER_IN (destination).

    Both operations succeed or both are rolled back.
    """
    if source_lot.pk == destination_lot.pk:
        raise ValueError("Source and destination lots cannot be the same.")

    with transaction.atomic():
        # Lock both rows in consistent order (by PK) to prevent deadlock
        lot_pks = sorted([str(source_lot.pk), str(destination_lot.pk)])
        lots = {
            str(lot.pk): lot
            for lot in GrainLot.objects.select_for_update().filter(pk__in=lot_pks)
        }
        source = lots[str(source_lot.pk)]
        destination = lots[str(destination_lot.pk)]

        if source.total_kg < quantity_kg:
            raise ValueError(
                f"Insufficient stock for transfer. Source lot '{source.lot_code}' "
                f"has {source.total_kg} kg; requested {quantity_kg} kg."
            )

        out_movement = GrainMovement.objects.create(
            tenant=source.tenant,
            grain_lot=source,
            movement_type=GrainMovement.MovementType.TRANSFER_OUT,
            quantity_kg=-quantity_kg,
            notes=notes,
            created_by=operator,
        )

        GrainMovement.objects.create(
            tenant=destination.tenant,
            grain_lot=destination,
            movement_type=GrainMovement.MovementType.TRANSFER_IN,
            quantity_kg=quantity_kg,
            notes=notes,
            created_by=operator,
        )

        source.total_kg -= quantity_kg
        source.save(update_fields=["total_kg", "updated_at"])

        destination.total_kg += quantity_kg
        destination.save(update_fields=["total_kg", "updated_at"])

        return out_movement, destination


```

### Pattern 7: Lot Code Auto-Generation

`lot_code` is generated on first save when the field is not set. Format:
`BRANCH-GRAIN-CAMPAIGN-GRADE`. Branch code and grain type code are from the
related objects' `.code` fields; campaign uses the campaign_code; grade is the
integer grado.

```python
def _generate_lot_code(branch, grain_type, campaign, grado: int) -> str:
    """Generate human-readable lot code: BRANCH-GRAIN-CAMPAIGN-GRADE."""
    branch_part = branch.code[:4].upper().replace("/", "")
    grain_part = grain_type.code[:3].upper()
    campaign_part = campaign.campaign_code.replace("/", "")[:5]
    grade_part = str(grado)
    return f"{branch_part}-{grain_part}-{campaign_part}-{grade_part}"


class GrainLot(TenantBoundModel):
    # ...

    def save(self, *args: object, **kwargs: object) -> None:
        if not self.lot_code:
            self.lot_code = _generate_lot_code(
                self.branch, self.grain_type, self.campaign, self.grado
            )
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        self._validate_tenant_references()
        super().save(*args, **kwargs)
```

### Pattern 8: GrainMovementViewSet -- Append-Only REST

GrainMovement endpoints must reject PATCH, PUT, and DELETE with HTTP 405.
Restrict HTTP methods at the viewset level.

```python
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response


class GrainMovementViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Append-only grain movement ledger.

    Allowed: GET (list), GET (retrieve), POST (create)
    Rejected: PATCH, PUT, DELETE (HTTP 405 -- immutable ledger)
    """

    # Restrict allowed HTTP methods -- no PATCH, PUT, DELETE
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = GrainMovementSerializer
    pagination_class = GrainMovementPagination

    def get_queryset(self):
        grain_lot_pk = self.kwargs.get("grain_lot_pk")
        qs = GrainMovement.objects.filter(grain_lot_id=grain_lot_pk)
        return qs.select_related("grain_lot", "romaneo", "created_by").order_by(
            "-movement_at"
        )
```

URL registration for nested movement routes:

```python
# In urls.py -- append to existing qa_patterns

movement_patterns = [
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/",
        GrainMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="grainlot-movements-list",
    ),
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/<uuid:pk>/",
        GrainMovementViewSet.as_view({"get": "retrieve"}),
        name="grainlot-movements-detail",
    ),
]
```

### Pattern 9: CellSuggestionService Scoring

The suggestion algorithm scores each StorageUnit and returns a ranked list.
Priority: grain type compatibility > grade match > campaign match > capacity.

```python
# In services/storage.py

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CellSuggestion:
    storage_unit_id: str
    name: str
    score: int
    reasons: list[str]
    available_capacity_kg: Decimal
    current_occupancy_kg: Decimal


def suggest_cell(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID,
    grain_type_id: uuid.UUID,
    campaign_id: uuid.UUID,
    grado: int,
    incoming_kg: Decimal,
) -> list[CellSuggestion]:
    """
    Return a ranked list of compatible storage units for incoming grain.

    Scoring (additive):
    +40: grain type match (current_grain_type == incoming OR unit is empty)
    +20: grade match (existing lot with same grado in this unit)
    +10: campaign match (existing lot in same campaign)
    -- Excluded: grain type incompatible (current_grain_type != incoming AND not NULL)
    -- Excluded: insufficient capacity (available_capacity_kg < incoming_kg)
    """
    from django.db.models import Sum
    from django.db.models.functions import Coalesce

    units = (
        StorageUnit.objects
        .filter(tenant_id=tenant_id, branch_id=branch_id, is_active=True)
        .annotate(
            current_occupancy_kg=Coalesce(
                Sum("grain_lots__movements__quantity_kg"), Decimal("0.000")
            )
        )
        .select_related("current_grain_type")
    )

    suggestions = []
    for unit in units:
        # Exclude incompatible grain types
        if (
            unit.current_grain_type_id is not None
            and str(unit.current_grain_type_id) != str(grain_type_id)
        ):
            continue

        capacity_kg = unit.capacity_tonnes * 1000
        available = capacity_kg - (unit.current_occupancy_kg or Decimal("0.000"))

        # Exclude insufficient capacity
        if available < incoming_kg:
            continue

        score = 0
        reasons = []

        if unit.current_grain_type_id is None:
            score += 40
            reasons.append("empty unit -- compatible")
        else:
            score += 40
            reasons.append("grain type match")

        # Check for grade/campaign match in existing lots
        existing_lots = GrainLot.objects.filter(
            tenant_id=tenant_id,
            storage_unit=unit,
        )
        if existing_lots.filter(grado=grado).exists():
            score += 20
            reasons.append("grade match")
        if existing_lots.filter(campaign_id=campaign_id).exists():
            score += 10
            reasons.append("campaign match")

        suggestions.append(
            CellSuggestion(
                storage_unit_id=str(unit.pk),
                name=unit.name,
                score=score,
                reasons=reasons,
                available_capacity_kg=available,
                current_occupancy_kg=unit.current_occupancy_kg or Decimal("0.000"),
            )
        )

    return sorted(suggestions, key=lambda s: s.score, reverse=True)
```

### Pattern 10: Romaneo FK Addition (migration 0003)

Spec-12 adds two nullable FKs to the existing `Romaneo` model in `romaneo.py`.
These fields are set to `null=True, blank=True` with `on_delete=models.SET_NULL`
so that deleting a StorageUnit or GrainLot does not cascade to existing romaneos.

**Add to `romaneo.py` in Group 6 (Storage Assignment):**

```python
# In backend/apps/acopio/models/romaneo.py -- add to Group 6 fields

# Group 6 -- Storage Assignment (Data Model v1.0, added by spec-12)
storage_unit = models.ForeignKey(
    "StorageUnit",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="romaneos",
    help_text="Storage unit assigned at discharge. Set by operator before CONFORME.",
)
grain_lot = models.ForeignKey(
    "GrainLot",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="romaneos",
    help_text="Grain lot resolved at CONFORME when deposit movement is created.",
)
```

**Forward reference**: Both FKs use string references (`"StorageUnit"`, `"GrainLot"`)
to avoid circular imports since the models are in the same `apps/acopio/models/`
package. Django resolves these within the same app.

**Migration 0003** must:
1. Create `acopio_storageunit` table
2. Create `acopio_grainlot` table (depends on 1)
3. Create `acopio_grainmovement` table (depends on 2)
4. `ALTER TABLE acopio_romaneo ADD COLUMN storage_unit_id` (nullable FK → step 1)
5. `ALTER TABLE acopio_romaneo ADD COLUMN grain_lot_id` (nullable FK → step 2)

Django `makemigrations` generates this automatically if all models are correct.
The agent should run `makemigrations --check` after writing models to verify
no manual migration edits are needed.

---

## Checkpoint Gates

### Gate 1: Models + Services (after Wave 1)

**Run from repo root (`/home/brunoghiberto/Documents/Projects/GraviTea/backend`):**

```bash
# 1. Verify all 3 new models importable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement
print(f'StorageUnit fields: {len(StorageUnit._meta.get_fields())}')
print(f'GrainLot fields: {len(GrainLot._meta.get_fields())}')
print(f'GrainMovement fields: {len(GrainMovement._meta.get_fields())}')
print('Gate 1 (Models): PASS')
"

# 2. Verify TenantBoundModel inheritance for all 3 new models
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement
from apps.core.models.mixins import TenantBoundModel
for model in [StorageUnit, GrainLot, GrainMovement]:
    assert issubclass(model, TenantBoundModel), f'{model.__name__} must inherit TenantBoundModel'
print('Gate 1 (TenantBound): PASS')
"

# 3. Verify Romaneo has new FKs
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import Romaneo
field_names = [f.name for f in Romaneo._meta.get_fields()]
assert 'storage_unit' in field_names, 'Romaneo missing storage_unit FK'
assert 'grain_lot' in field_names, 'Romaneo missing grain_lot FK'
print('Gate 1 (Romaneo FKs): PASS')
"

# 4. Verify migration applies cleanly
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
../.venv/bin/python manage.py migrate --check 2>&1 | tail -5

# 5. Verify services importable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.services.storage import (
    CellSuggestionService, StockReportService,
    ReconciliationService, CampaignCloseService,
)
print('Gate 1 (Services): PASS')
"
```

**Pass criteria**: All 3 models importable. All 3 inherit TenantBoundModel.
Romaneo has `storage_unit` and `grain_lot` fields. Migration applies cleanly.
Services importable.

### Gate 2: API Layer (after Wave 2)

```bash
# 1. Verify serializers importable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.serializers.storage import (
    StorageUnitSerializer,
    GrainLotSerializer,
    GrainMovementSerializer,
)
print(f'StorageUnitSerializer fields: {list(StorageUnitSerializer().fields.keys())[:6]}...')
print('Gate 2 (Serializers): PASS')
"

# 2. Verify URL routing resolves (storage routes registered)
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from django.urls import reverse
print(reverse('storage-unit-list'))
print(reverse('grain-lot-list'))
print('Gate 2 (URLs): PASS')
"

# 3. Verify romaneo serializer has storage_unit as patchable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.serializers.romaneo import RomaneoSerializer
s = RomaneoSerializer()
assert 'storage_unit' in s.fields, 'RomaneoSerializer missing storage_unit field'
print('Gate 2 (Romaneo Serializer): PASS')
"

# 4. Verify admin registration for 3 new models
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
../.venv/bin/python -c "
import django; django.setup()
from django.contrib import admin
from apps.acopio.models import StorageUnit, GrainLot, GrainMovement
for model in [StorageUnit, GrainLot, GrainMovement]:
    assert admin.site.is_registered(model), f'{model.__name__} not registered in admin'
print('Gate 2 (Admin): PASS')
"
```

**Pass criteria**: All serializers importable with expected fields. URL routes
resolve for `storage-unit-list` and `grain-lot-list`. `RomaneoSerializer`
includes `storage_unit`. Admin registered for all 3 models.

### Gate 3: Full Test Suite (after Wave 3)

```bash
# 1. Run all acopio tests
bash /home/brunoghiberto/Documents/Projects/GraviTea/scripts/run-tests-external.sh \
    -n spec12-storage tests/acopio/

# 2. Poll for completion (status file is written by the script)
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec12-storage.status

# 3. Read summary when status is PASSED or FAILED
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec12-storage.summary

# 4. If FAILED, debug specific failures
grep "FAILED" /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec12-storage.log
```

**Pass criteria**: `.status` file reads `PASSED`. Summary shows 0 failures,
0 errors. Minimum 35 tests collected. If FAILED, A3 fixes failures and re-runs.

---

## Testing Protocol

### CRITICAL: External Test Runner Only

**NEVER** run pytest directly inside Claude Code -- it consumes excessive tokens
and can hang the session. **ALWAYS** use `scripts/run-tests-external.sh`.

Reference: `scripts/run-tests-external.sh` (first 70 lines for usage).

How the script works:
1. Launches pytest as a background process via `setsid`/`nohup`.
2. The calling shell returns immediately.
3. Results are written to files in `Docs/Tests/`.
4. Check `.status` file for completion state (`RUNNING`/`PASSED`/`FAILED`/`ERROR`).
5. Read `.summary` file for test counts and coverage (~20 lines).
6. Only grep the `.log` file for specific failures if debugging.

### Test Categories

| Category | File | What It Tests | Estimated Count |
|----------|------|---------------|----------------|
| Model unit tests | `test_storage_models.py` | StorageUnit creation + uniqueness constraint; GrainLot composite key enforcement; GrainMovement immutability (ValueError on update/delete); TenantBound inheritance; lot_code auto-generation; derived occupancy annotated correctly | 12-15 |
| Grain ledger | `test_grain_ledger.py` | Deposit from romaneo (get_or_create lot, balance += weight); lot reuse (two deposits same combination); withdrawal positive/negative balance scenarios; negative balance rejection error message; transfer atomicity (source -kg, destination +kg); TRANSFER_IN/TRANSFER_OUT paired in single transaction | 10-12 |
| API integration | `test_storage_api.py` | StorageUnit CRUD (4 endpoints + soft-deactivate); occupancy in list response; HTTP 405 on GrainMovement PATCH/DELETE/PUT; suggest endpoint (ranked response); stock-report endpoint; tenant isolation (cross-tenant 404 for all 3 models); reconciliation endpoint | 10-12 |
| Service tests | `test_storage_services.py` | CellSuggestionService: type match scores 40, grade match +20, campaign +10; incompatible type excluded; insufficient capacity excluded; StockReportService: aggregation per unit, per grain type, per campaign; utilisation_pct calculation; ReconciliationService: variance detection, adjustment movement creation, mandatory notes | 8-10 |
| **Total** | | | **40-49** |

### Test Execution Commands

```bash
# Run all acopio tests (recommended -- catches regressions from spec-10 and spec-11)
bash scripts/run-tests-external.sh -n spec12-storage tests/acopio/

# Run only new storage tests
bash scripts/run-tests-external.sh -n spec12-new tests/acopio/test_storage_models.py \
    tests/acopio/test_grain_ledger.py tests/acopio/test_storage_api.py \
    tests/acopio/test_storage_services.py

# Run with fail-fast (stop on first failure during development)
bash scripts/run-tests-external.sh -n spec12-fast --fail-fast tests/acopio/

# Run only ledger tests (for debugging balance issues)
bash scripts/run-tests-external.sh -n spec12-ledger tests/acopio/test_grain_ledger.py
```

### Test Output Location

| File | Contents | How to Read |
|------|----------|-------------|
| `Docs/Tests/spec12-storage.status` | `RUNNING`, `PASSED`, `FAILED`, or `ERROR` | `cat` (1 line) |
| `Docs/Tests/spec12-storage.summary` | Test counts, failures, coverage | `cat` (~20 lines) |
| `Docs/Tests/spec12-storage.log` | Full pytest output | `grep "FAILED"` only |

---

## Done Criteria

### Acceptance Criteria Verification

| AC | Description | Verification Method | Agent |
|----|-------------|-------------------|-------|
| AC-012-001 | StorageUnit model (12 fields, 3 types, unique name per branch) | Gate 1 + `test_storage_models.py` | A1 |
| AC-012-002 | GrainLot composite key enforced (duplicate raises IntegrityError) | `test_storage_models.py` | A1, A3 |
| AC-012-003 | GrainMovement fully immutable (ValueError on save/delete) | `test_grain_ledger.py` immutability tests | A1, A3 |
| AC-012-004 | Deposit from romaneo: lot created or reused, balance incremented | `test_grain_ledger.py` deposit tests | A1, A3 |
| AC-012-005 | Lot reuse: two deposits same combination → same lot, sum balance | `test_grain_ledger.py` lot reuse test | A1, A3 |
| AC-012-006 | Negative balance prevention: withdrawal > balance → ValueError | `test_grain_ledger.py` negative balance test | A1, A3 |
| AC-012-007 | Transfer atomic: both TRANSFER_IN + TRANSFER_OUT or neither | `test_grain_ledger.py` transfer tests | A1, A3 |
| AC-012-008 | current_occupancy_kg derived correctly via annotated queryset | `test_storage_api.py` list response test | A2, A3 |
| AC-012-009 | GrainMovement API returns HTTP 405 for PATCH/DELETE/PUT | `test_storage_api.py` 405 tests | A2, A3 |
| AC-012-010 | Cell suggestion ranked (type match > grade match > capacity) | `test_storage_services.py` scoring tests | A1, A3 |
| AC-012-011 | Stock report aggregation correct (per unit, type, campaign) | `test_storage_services.py` stock report tests | A1, A3 |
| AC-012-012 | Reconciliation creates ADJUSTMENT movements with mandatory notes | `test_storage_services.py` reconciliation tests | A1, A3 |
| AC-012-013 | Romaneo FK additions (storage_unit, grain_lot) in place | Gate 1 Romaneo FK check + `test_storage_models.py` | A1 |
| AC-012-014 | Tenant isolation: cross-tenant queries return empty (fail-closed) | `test_storage_api.py` tenant isolation tests | A2, A3 |
| AC-012-015 | Test suite passing (40+ tests, 90%+ coverage on new code) | Gate 3 summary | A3 |

### Final Verification Command

```bash
bash /home/brunoghiberto/Documents/Projects/GraviTea/scripts/run-tests-external.sh \
    -n spec12-final tests/acopio/
```

### Minimum Counts

- Models: 3 (StorageUnit, GrainLot, GrainMovement)
- Service functions: 4+ (suggest_cell, generate_stock_report, reconcile, close_campaign)
- API endpoints: 10+ (StorageUnit CRUD + suggest + stock-report, GrainLot list/retrieve, GrainMovement list/create/retrieve)
- Tests: >= 40
- Test coverage: >= 90% on new code

---

## FR-to-Agent Traceability

Every functional requirement from `specs/012-storage-position/spec.md` maps to
an agent and wave:

| FR | Description | Agent | Wave | AC |
|----|-------------|-------|------|-----|
| FR-001 | StorageUnit CRUD per branch | A1, A2 | 1, 2 | AC-012-001 |
| FR-002 | GrainLot position tracking (composite key, running balance) | A1 | 1 | AC-012-002 |
| FR-003 | GrainMovement immutable ledger (5 types, no UPDATE/DELETE) | A1, A2 | 1, 2 | AC-012-003, AC-012-009 |
| FR-004 | Cell suggestion (ranked list) | A1, A2 | 1, 2 | AC-012-010 |
| FR-005 | Deposit from romaneo (get_or_create lot + DEPOSIT movement) | A1 | 1 | AC-012-004, AC-012-005 |
| FR-006 | Dispatch (WITHDRAWAL movement, negative balance prevention) | A1, A2 | 1, 2 | AC-012-006 |
| FR-007 | Stock report (real-time, per unit / grain type / campaign) | A1, A2 | 1, 2 | AC-012-011 |
| FR-008 | Physical inventory reconciliation (ADJUSTMENT movements) | A1, A2 | 1, 2 | AC-012-012 |
| FR-009 | Campaign year close (carry-forward, supervisor-only, atomic) | A1 | 1 | AC-012-015 |
| FR-010 | Atomic inter-unit transfer (TRANSFER_IN + TRANSFER_OUT) | A1, A2 | 1, 2 | AC-012-007 |
| NF-001 | Balance consistency (GrainLot.total_kg == sum of movements) | A1, A3 | 1, 3 | AC-012-004 |
| NF-002 | Occupancy query < 200ms for 200 units (annotated queryset) | A2 | 2 | AC-012-008 |
| NF-003 | GrainMovement immutability at model + API levels | A1, A2 | 1, 2 | AC-012-003, AC-012-009 |
| NF-004 | Tenant isolation (TenantBoundManager fail-closed) | A1 | 1 | AC-012-014 |
| NF-005 | Provenance fields (ADR-034: created_at, created_by, device_id) | A1 | 1 | AC-012-001 |

---

## RLS Policies (A1 Deliverable)

A1 must append to `backend/database/sql/acopio_rls.sql` to add RLS policies for
all 3 new tenant-scoped models. Reference pattern: `mermacalculation_tenant_isolation`
at the bottom of the existing file.

```sql
-- ================================================================
-- RLS for StorageUnit, GrainLot, GrainMovement
-- All 3 are TENANT-SCOPED (inherit TenantBoundModel)
-- ================================================================

-- StorageUnit
ALTER TABLE acopio_storageunit ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_storageunit FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS storageunit_tenant_isolation ON acopio_storageunit;
CREATE POLICY storageunit_tenant_isolation ON acopio_storageunit
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY storageunit_tenant_isolation ON acopio_storageunit IS
'Ensures storage units are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_storageunit TO gravitea_app;

-- GrainLot
ALTER TABLE acopio_grainlot ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_grainlot FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS grainlot_tenant_isolation ON acopio_grainlot;
CREATE POLICY grainlot_tenant_isolation ON acopio_grainlot
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY grainlot_tenant_isolation ON acopio_grainlot IS
'Ensures grain lots are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_grainlot TO gravitea_app;

-- GrainMovement
ALTER TABLE acopio_grainmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_grainmovement FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS grainmovement_tenant_isolation ON acopio_grainmovement;
CREATE POLICY grainmovement_tenant_isolation ON acopio_grainmovement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY grainmovement_tenant_isolation ON acopio_grainmovement IS
'Ensures grain movements are only visible/modifiable within their tenant context.';

-- Note: GrainMovement is immutable -- DELETE should be blocked by application
-- layer. The INSERT-only constraint is enforced by the model save() override.
GRANT SELECT, INSERT ON acopio_grainmovement TO gravitea_app;
-- Intentionally no UPDATE, DELETE grants -- enforces immutability at DB level.
```

---

## Admin Registration (A1 Deliverable)

A1 must update `backend/apps/acopio/admin.py` to register the 3 new models.
Pattern reference: existing `RomaneoAdmin` and `MermaCalculationAdmin` in the same file.

```python
# Add to existing imports in admin.py
from .models import (
    # ... existing imports ...
    StorageUnit,
    GrainLot,
    GrainMovement,
)


@admin.register(StorageUnit)
class StorageUnitAdmin(admin.ModelAdmin):
    list_display = [
        "name", "unit_type", "branch", "capacity_tonnes", "is_active",
        "current_grain_type",
    ]
    list_filter = ["unit_type", "is_active", "branch"]
    search_fields = ["name", "environment_sensor_id"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(GrainLot)
class GrainLotAdmin(admin.ModelAdmin):
    list_display = [
        "lot_code", "grain_type", "campaign", "grado", "storage_unit",
        "total_kg", "is_own_grain",
    ]
    list_filter = ["grain_type", "campaign", "is_own_grain", "storage_unit"]
    search_fields = ["lot_code"]
    readonly_fields = ["id", "lot_code", "created_at", "updated_at"]


@admin.register(GrainMovement)
class GrainMovementAdmin(admin.ModelAdmin):
    list_display = [
        "grain_lot", "movement_type", "quantity_kg", "movement_at",
        "romaneo", "created_by",
    ]
    list_filter = ["movement_type"]
    search_fields = ["grain_lot__lot_code", "romaneo__romaneo_number", "reference_document"]
    readonly_fields = [
        "id", "grain_lot", "movement_type", "quantity_kg", "movement_at",
        "romaneo", "reference_document", "created_by", "device_id", "notes",
    ]

    def has_change_permission(self, request, obj=None) -> bool:
        """GrainMovement is immutable -- no changes through admin."""
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """GrainMovement is immutable -- no deletion through admin."""
        return False
```

---

## Composite Indexes (A1 Deliverable)

Per NF-002 (query performance) and NF-004 (tenant isolation), add composite
indexes to all 3 new models' `Meta` classes for common query patterns.

### StorageUnit

```python
class Meta:
    db_table = "acopio_storageunit"
    ordering = ["branch", "name"]
    constraints = [
        models.UniqueConstraint(
            fields=["tenant", "branch", "name"],
            name="uq_storageunit_tenant_branch_name",
        ),
    ]
    indexes = [
        models.Index(
            fields=["tenant_id", "branch_id", "is_active"],
            name="idx_storageunit_tenant_branch_active",
        ),
    ]
```

### GrainLot

```python
class Meta:
    db_table = "acopio_grainlot"
    ordering = ["-updated_at"]
    constraints = [
        models.UniqueConstraint(
            fields=[
                "tenant", "branch", "grain_type", "campaign",
                "grado", "storage_unit",
            ],
            name="uq_grainlot_composite_identity",
        ),
        models.CheckConstraint(
            check=models.Q(total_kg__gte=0),
            name="chk_grainlot_nonnegative_balance",
        ),
    ]
    indexes = [
        models.Index(
            fields=["tenant_id", "storage_unit_id"],
            name="idx_grainlot_tenant_storage",
        ),
        models.Index(
            fields=["tenant_id", "campaign_id", "grain_type_id"],
            name="idx_grainlot_tenant_campaign_grain",
        ),
    ]
```

### GrainMovement

```python
class Meta:
    db_table = "acopio_grainmovement"
    ordering = ["-movement_at"]
    indexes = [
        models.Index(
            fields=["tenant_id", "grain_lot_id", "movement_at"],
            name="idx_grainmovement_tenant_lot_ts",
        ),
        models.Index(
            fields=["tenant_id", "movement_type", "movement_at"],
            name="idx_grainmovement_tenant_type_ts",
        ),
    ]
```

---

## RAG Queries for Agents

Agents MUST run RAG queries before writing code that depends on domain-specific
values (grain lot identity, campaign segregation rules, accounting codes).

```bash
# Query 1: Storage operations and grain position tracking
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "grain storage silo position stock movement tracking" -l 5

# Query 2: Campaign year segregation per ARCA RG 3593
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "campaign year segregation grain storage by type grade" -l 5

# Query 3: Own grain vs third-party custody accounting codes
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "own grain third party custody accounting classification RG 3593" -l 5

# Query 4: Cell/silo assignment criteria (jefe de planta decision)
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "silo assignment criteria grain type quality humidity campaign capacity" -l 5

# Query 5: Physical vs ledger reconciliation workflow
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "physical inventory reconciliation aforo cubicaje variance adjustment" -l 5
```

---

## Execution Notes

**Type**: Implementation -- multi-agent sequential execution (A1 → A2 → A3)

**Base class reference**: `backend/apps/core/models/mixins.py`
(`TenantBoundModel` -- auto-adds `tenant_id`, validates FK references,
implements `_validate_tenant_references()`).

**Immutability pattern reference**: `backend/apps/acopio/models/merma_calculation.py`
(`MermaCalculation.save()` and `MermaCalculation.delete()`) -- full immutability
(no updates, no deletes). This is the exact pattern to replicate for `GrainMovement`.

**Running balance reference**: `backend/apps/inventario/models.py` lines 678-750
(`StockSnapshot`) -- demonstrates the running-balance approach. However, spec-12
does NOT use snapshots: balance is stored directly on `GrainLot.total_kg` and
recomputed if drift is detected by a management command.

**Annotated queryset reference**: `backend/apps/inventario/models.py` -- search
for `annotate(` patterns showing how derived aggregates are computed. The
`current_occupancy_kg` pattern is a `Sum()` annotation over a nested related
queryset via `grain_lots__movements__quantity_kg`.

**Atomic transaction reference**: `backend/apps/acopio/services/merma_engine.py`
-- not transactional itself, but the pattern of wrapping multi-model operations
in `with transaction.atomic():` is established in spec-11 state transitions.

**Test pattern reference**: `backend/tests/acopio/conftest.py` -- existing
`grain_type_factory` and `campana_factory` fixtures. A3 adds `storage_unit_factory`,
`grain_lot_factory`, and `romaneo_conforme` (a romaneo in CONFORME state with
`peso_neto_conforme_kg` set) to the same conftest.

**Writing persona**: Implementation agents should follow `django-expert` skill
for Django 5.2 patterns, `gravitea-tenant` skill for tenant isolation,
`gravitea-testing` skill for pytest conventions, and `gravitea-inventory` skill
for the immutable ledger pattern (same principle, different model).

**Blueprint deviation alert**: GrainMovement has 5 movement types, not 4. The
5th type `ADJUSTMENT` is required by SRS-AL06 but missing from the Data Model
v1.0 GrainMovement definition. This is a justified extension. Document the
deviation in a code comment on the `MovementType` choices class.

**Romaneo immutability interaction**: The spec-11 Romaneo model has an immutability
gate at CONFORME. Spec-12 needs to call `romaneo.save(update_fields=['grain_lot',
'updated_at'])` after deposit to update the `grain_lot` FK. Verify that the
CONFORME gate's allowed-fields list includes `grain_lot` -- if not, A1 must
update the Romaneo `save()` method's mutable fields allowlist.
