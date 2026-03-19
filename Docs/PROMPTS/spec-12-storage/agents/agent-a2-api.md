# Agent A2: Serializers, ViewSets & URL Registration

**Agent Type**: `backend-architect`
**Model**: Sonnet 4.6
**Mission**: Create all DRF serializers, viewsets, URL routes, and modify existing romaneo serializer/viewset for the storage module API layer.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-12-storage/12-implement.md` — Orchestration protocol, wave order, code patterns
2. `specs/012-storage-position/contracts/storage-api.md` — Full REST API contracts (endpoints, request/response shapes, status codes)
3. `specs/012-storage-position/quickstart.md` — Service call signatures, queryset patterns
4. `specs/012-storage-position/tasks.md` — Full task list with descriptions

---

## Assigned Tasks

### Wave 2: MVP API (T010–T012, T015, T017–T020)

| Task | Description |
|------|-------------|
| T010 | Create `StorageUnitSerializer` in `backend/apps/acopio/serializers/storage.py` |
| T015 | Add `GrainLotSerializer` + `GrainMovementSerializer` to same file |
| T011 | Create `StorageUnitViewSet` (annotated occupancy queryset) in `backend/apps/acopio/views/storage.py` |
| T017 | Add `GrainLotViewSet` + `GrainMovementViewSet` (append-only) to same file |
| T012 | Register `storage-units` route in `backend/apps/acopio/urls.py`; update exports |
| T018 | Register `grain-lots` + nested `movements` routes |
| T019 | Update `backend/apps/acopio/serializers/romaneo.py`: add `storage_unit` patchable |
| T020 | Update `confirmar` action in `backend/apps/acopio/views/romaneo.py`: call deposit service |

### Wave 3: P2 Endpoints (T024, T028, T032, T036)

| Task | Description |
|------|-------------|
| T024 | Add `suggest` action + `CellSuggestionRequestSerializer` + response serializer |
| T028 | Wire dispatch via `GrainMovementViewSet.perform_create` for WITHDRAWAL type |
| T032 | Add `transfer` `@action` on `GrainLotViewSet` + `TransferRequestSerializer` |
| T036 | Add `stock-report` `@action` on `StorageUnitViewSet` + `StockReportSerializer` |

### Wave 4: P3 Endpoints (T040, T045)

| Task | Description |
|------|-------------|
| T040 | Add `reconcile` `@action` on `StorageUnitViewSet` + `ReconciliationRequestSerializer` |
| T045 | Add `close` `@action` on `CampanaConfigViewSet` in `backend/apps/acopio/views/reference_data.py` |

---

## Files to Create

| File | Description |
|------|-------------|
| `backend/apps/acopio/serializers/storage.py` | All storage serializers (grows incrementally) |
| `backend/apps/acopio/views/storage.py` | StorageUnitViewSet, GrainLotViewSet, GrainMovementViewSet |

## Files to Modify

| File | What Changes |
|------|--------------|
| `backend/apps/acopio/serializers/romaneo.py` | Add `storage_unit` UUID patchable + `grain_lot` read-only |
| `backend/apps/acopio/serializers/__init__.py` | Re-export new serializers |
| `backend/apps/acopio/views/romaneo.py` | Modify `confirmar` action (insert deposit service call after line 267) |
| `backend/apps/acopio/views/reference_data.py` | Add `close` action to `CampanaConfigViewSet` |
| `backend/apps/acopio/views/__init__.py` | Re-export new viewsets |
| `backend/apps/acopio/urls.py` | Register storage-units, grain-lots, nested movements, transfer |

---

## Domain Knowledge

### RAG Queries (run if you need additional context)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "REST API design grain storage endpoints" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "DRF viewset action immutable append-only" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "cell suggestion scoring grain type campaign" -l 5
```

### Critical Domain Facts (Inlined)

1. **GrainMovement is IMMUTABLE at API layer**: `http_method_names = ["get", "post", "head", "options"]`. PATCH/PUT/DELETE return HTTP 405 automatically.
2. **GrainLot is READ-ONLY via API**: No create/update/delete endpoints. Lots are created internally by the deposit service.
3. **`current_occupancy_kg` is annotated**: `StorageUnitViewSet.get_queryset()` must annotate with `Coalesce(Sum("grain_lots__movements__quantity_kg"), Decimal("0.000"))`.
4. **`capacity_utilisation_pct` is a SerializerMethodField**: `(current_occupancy_kg / (capacity_tonnes * 1000)) * 100`.
5. **The action is called `confirmar`** (not `confirmar_conforme`). Python method: `confirmar`. URL path: `confirmar`. File: `views/romaneo.py:164`.
6. **Storage unit PATCH `is_active=False`**: Must return HTTP 409 if any GrainLot has `total_kg > 0` for that unit.
7. **Storage unit DELETE**: Always returns HTTP 405 (use PATCH `is_active=false` for soft-deactivation).
8. **Nested movements URL**: `grain-lots/<uuid:grain_lot_pk>/movements/` — manual path, not router-nested.
9. **Transfer endpoint**: `@action(detail=False, methods=["post"], url_path="transfer")` on `GrainLotViewSet`.
10. **All serializers use explicit `fields` lists** — never `fields = '__all__'` (Constitution IX).
11. **`is_own_grain=False`** hardcoded in T020's deposit call — own-grain deferred to spec-13.
12. **Campaign close permission**: `IsSupervisorOrAdmin` — verify it exists in `apps/auth/permissions.py`. If not, create a simple one checking `request.user.is_staff or request.user.is_superuser`.

---

## Key Patterns & Constraints

### Serializer Pattern

```python
from rest_framework import serializers
from decimal import Decimal

class StorageUnitSerializer(serializers.ModelSerializer):
    unit_type_display = serializers.CharField(source="get_unit_type_display", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    current_grain_type_code = serializers.CharField(
        source="current_grain_type.code", read_only=True, default=None
    )
    current_occupancy_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True  # From annotation
    )
    capacity_utilisation_pct = serializers.SerializerMethodField()

    class Meta:
        model = StorageUnit
        fields = [
            "id", "name", "unit_type", "unit_type_display",
            "branch", "branch_name", "capacity_tonnes",
            "current_grain_type", "current_grain_type_code",
            "is_active", "environment_sensor_id",
            "current_occupancy_kg", "capacity_utilisation_pct",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "current_occupancy_kg"]

    def get_capacity_utilisation_pct(self, obj):
        occupancy = getattr(obj, "current_occupancy_kg", None) or Decimal("0")
        capacity_kg = obj.capacity_tonnes * 1000
        if capacity_kg == 0:
            return Decimal("0")
        return round((occupancy / capacity_kg) * 100, 1)
```

### ViewSet Pattern (Tenant-Scoped)

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class StorageUnitViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StorageUnitSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]  # No PUT/DELETE

    def get_queryset(self):
        qs = StorageUnit.objects.annotate(
            current_occupancy_kg=Coalesce(
                Sum("grain_lots__movements__quantity_kg"), Decimal("0.000"),
            )
        ).select_related("branch", "current_grain_type")

        branch = self.request.query_params.get("branch")
        if branch:
            qs = qs.filter(branch_id=branch)
        is_active = self.request.query_params.get("is_active", "true")
        qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.user.tenant_id,
            created_by=self.request.user,
        )

    def partial_update(self, request, *args, **kwargs):
        """Guard: cannot deactivate unit with non-zero active stock."""
        instance = self.get_object()
        if (
            request.data.get("is_active") is False
            and instance.grain_lots.filter(total_kg__gt=0).exists()
        ):
            return Response(
                {"type": "active_stock_exists",
                 "detail": "Cannot deactivate storage unit with non-zero grain stock."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Hard delete is always rejected."""
        return Response(
            {"detail": "Use PATCH is_active=false for soft-deactivation."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
```

### Append-Only ViewSet (GrainMovement)

```python
class GrainMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = GrainMovementSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        grain_lot_pk = self.kwargs.get("grain_lot_pk")
        return (
            GrainMovement.objects
            .filter(grain_lot_id=grain_lot_pk)
            .select_related("romaneo", "created_by")
            .order_by("-movement_at")
        )

    def perform_create(self, serializer):
        grain_lot_pk = self.kwargs.get("grain_lot_pk")
        grain_lot = GrainLot.objects.get(pk=grain_lot_pk)
        # Delegate to service layer based on movement_type
        movement_type = serializer.validated_data["movement_type"]
        if movement_type == GrainMovement.MovementType.WITHDRAWAL:
            from apps.acopio.services.storage import create_withdrawal
            try:
                movement = create_withdrawal(
                    grain_lot=grain_lot,
                    quantity_kg=serializer.validated_data["quantity_kg"],
                    operator=self.request.user,
                    reference_document=serializer.validated_data.get("reference_document"),
                    notes=serializer.validated_data.get("notes"),
                )
            except ValueError as e:
                raise serializers.ValidationError({"detail": str(e)})
        # ... ADJUSTMENT type delegates to reconcile service
```

### URL Registration Pattern

```python
# In backend/apps/acopio/urls.py — add to existing router + patterns

router.register(r"storage-units", StorageUnitViewSet, basename="storage-unit")
router.register(r"grain-lots", GrainLotViewSet, basename="grain-lot")

# Nested movements (manual path for 1:N nested resource)
movement_patterns = [
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/",
        GrainMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="grain-lot-movements-list",
    ),
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/<uuid:pk>/",
        GrainMovementViewSet.as_view({"get": "retrieve"}),
        name="grain-lot-movements-detail",
    ),
]

urlpatterns = qa_patterns + movement_patterns + [
    path("", include(router.urls)),
]
```

### Modifying the confirmar Action (T020)

The existing action is at `views/romaneo.py:164-269`. Insert spec-12 logic
AFTER the `romaneo.save()` call (line 267) but BEFORE the `return Response(...)` (line 269):

```python
        # ... existing code up to line 267 ...
        romaneo.save()

        # -- Spec-12: Deposit from romaneo --
        if not romaneo.storage_unit:
            return Response(
                {"type": "missing_storage_unit",
                 "detail": "storage_unit must be set on romaneo before confirming. "
                           "Use PATCH /romaneos/{id}/ to assign a storage unit first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.acopio.services.storage import create_deposit_from_romaneo
        movement, lot = create_deposit_from_romaneo(
            romaneo=romaneo,
            storage_unit=romaneo.storage_unit,
            is_own_grain=False,  # spec-12 default; own-grain deferred to spec-13
        )

        return Response(RomaneoDetailSerializer(romaneo).data)
```

### Romaneo Serializer Update (T019)

Add `storage_unit` as a patchable UUID field and `grain_lot` as read-only:

```python
# In RomaneoSerializer.Meta.fields, add:
"storage_unit",
"grain_lot",

# In RomaneoSerializer.Meta.read_only_fields, add:
"grain_lot",

# In RomaneoDetailSerializer, add:
storage_unit_name = serializers.CharField(source="storage_unit.name", read_only=True, default=None)
grain_lot_code = serializers.CharField(source="grain_lot.lot_code", read_only=True, default=None)
```

---

## NEVER

- NEVER use `fields = '__all__'` on any serializer (Constitution IX)
- NEVER add PATCH/PUT/DELETE to GrainMovementViewSet
- NEVER add create/update/delete to GrainLotViewSet (lots are internal-only)
- NEVER compute occupancy anywhere except the annotated queryset
- NEVER read full research PDFs — use RAG queries above if needed
- NEVER run tests directly — testing is A3's responsibility
