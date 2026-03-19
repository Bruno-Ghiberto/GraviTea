# Agent A3: Serializers, ViewSets, URL Routing & Final Test Run

**Agent Type**: `backend-architect`
**Model**: Sonnet 4.6
**Mission**: Implement the full API layer — serializers, ProducerAccountViewSet,
AccountMovementViewSet (with 405 immutability enforcement), PosicionConsolidadaView,
StatementView, cursor pagination, URL routing, OpenAPI annotations, and run the final
test suite to close the implementation loop.
Wave 3 — begins after GATE G2 passes.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-13-accounts/13-implement.md` — Orchestration protocol, URL patterns, pagination code
2. `specs/013-producer-accounts/contracts/accounts-api.md` — All endpoint contracts, request/response shapes
3. `specs/013-producer-accounts/data-model.md` — Field types, serializer field names
4. `specs/013-producer-accounts/tasks.md` — Task descriptions (T018–T022, T025–T026, T029–T031, T034–T035, T038–T039, T042–T043)

---

## Assigned Tasks (Wave 3)

| Task | Description |
|------|-------------|
| T018 | Create `backend/apps/cuentas/serializers/accounts.py` — ProducerAccountSerializer + AccountMovementSerializer (read-only) |
| T019 | Create cursor pagination classes + ProducerAccountViewSet + AccountMovementViewSet in `backend/apps/cuentas/views/accounts.py` |
| T020 | Update `backend/apps/cuentas/serializers/__init__.py` and `views/__init__.py` |
| T021 | Create `backend/apps/cuentas/urls.py` with router + explicit nested movement routes |
| T022 | Add cuentas URL include to `backend/gravitea/urls.py` |
| T025 | Add ManualMovementSerializer (write-only) to `backend/apps/cuentas/serializers/accounts.py` |
| T026 | Extend AccountMovementViewSet.perform_create() — manual movement validation + service call |
| T029 | Add PosicionConsolidadaSerializer to `backend/apps/cuentas/serializers/accounts.py` |
| T030 | Add PosicionConsolidadaView (APIView) to `backend/apps/cuentas/views/accounts.py` |
| T031 | Register PosicionConsolidadaView in `backend/apps/cuentas/urls.py` |
| T034 | Add StatementView (APIView) to `backend/apps/cuentas/views/accounts.py` |
| T035 | Register StatementView nested route in `backend/apps/cuentas/urls.py` |
| T038 | Run full spec-13 test suite: `bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/` |
| T039 | Run acopio regression check: `bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/` |
| T042 | Verify management command help works |
| T043 | Add `@extend_schema` annotations (drf-spectacular) to all ViewSets and Views |

---

## Files to Create

| File | Description |
|------|-------------|
| `backend/apps/cuentas/serializers/accounts.py` | All serializers (read + write) |
| `backend/apps/cuentas/views/accounts.py` | All ViewSets and APIViews |
| `backend/apps/cuentas/urls.py` | URL routing |

## Files to Modify

| File | What Changes |
|------|--------------|
| `backend/apps/cuentas/serializers/__init__.py` | Export all serializer classes |
| `backend/apps/cuentas/views/__init__.py` | Export all viewset classes |
| `backend/gravitea/urls.py` | Add cuentas URL include |

---

## Domain Knowledge

### RAG Queries (run for additional context)

```bash
cd backend
.venv/bin/python scripts/qdrant/qdrant_search.py -q "DRF CursorPagination ModelViewSet ReadOnly" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "DRF serializer nested read-only source field" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "drf-spectacular extend_schema query parameter" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "DRF DefaultRouter nested resource URL path" -l 5
```

### Critical Domain Facts (Inlined)

1. **CursorPagination is MANDATORY** (Constitution §XIII):
   - ProducerAccountViewSet: `ordering="-created_at"`, `page_size=25`
   - AccountMovementViewSet: `ordering="-movement_at"`, `page_size=50`
   - Response has `next`, `previous`, `results` — NO `count` field
   - NEVER use PageNumberPagination on these endpoints

2. **DRF DefaultRouter does NOT auto-nest**: Movement routes require explicit `path()` entries.
   Router only generates `/accounts/` and `/accounts/{id}/`. Nested `/accounts/{id}/movements/`
   and `/accounts/{id}/movements/{movement_pk}/` must be added manually.

3. **CUIT blind index search**: In ProducerAccountViewSet.get_queryset(), compute hash before filter:
   ```python
   from apps.core.encryption.utils import compute_blind_index
   if cuit := self.request.query_params.get("producer_cuit"):
       qs = qs.filter(producer_cuit_hash=compute_blind_index(cuit))
   ```

4. **producer_cuit in serializer**: Serialize `producer_cuit_encrypted` as field named `producer_cuit`
   (transparent EncryptedCharField decryption). NEVER include `producer_cuit_encrypted` or
   `producer_cuit_hash` in any serializer output.

5. **PATCH/DELETE → 405**: AccountMovementViewSet must return exactly:
   ```json
   {"detail": "Method not allowed.", "code": "append_only_violation"}
   ```
   with HTTP 405 status.

6. **AccountMovementViewSet http_method_names**: Set `http_method_names = ["get", "post", "head", "options"]`
   BUT also override `update`, `partial_update`, `destroy` to return 405 (for explicit nested URL routes
   that map patch/delete to those methods).

7. **Supervisor permission for ADJUSTMENT**: Check `request.user.has_permission("settings.admin")`.
   If not, raise `PermissionDenied`. See other ViewSets in `apps/acopio/` for the permission check pattern.

8. **select_related in ViewSets**: Required for query optimization (Constitution §VIII):
   - ProducerAccountViewSet: `.select_related("branch", "grain_type", "campaign", "created_by")`
   - AccountMovementViewSet: `.select_related("producer_account", "romaneo", "created_by")`

9. **StatementView date validation**: Both `date_from` and `date_to` are required; `date_from > date_to`
   returns 400. Parse as ISO8601 date strings → Python `date` objects. Use `datetime.date.fromisoformat()`.

10. **PosicionConsolidadaView params**: `producer_cuit` and `campaign_id` are required query params.
    Missing either → 400 with `{"detail": "...", "code": "missing_param"}`.

11. **`@extend_schema` import**: from `drf_spectacular.utils import extend_schema, OpenApiParameter`.
    Annotate list/retrieve/create/custom actions. Include `summary`, `description`, response schema,
    and query parameter definitions for filtered endpoints.

---

## Key Patterns & Constraints

### T018/T019: Serializers + ViewSets Skeleton

```python
# backend/apps/cuentas/serializers/accounts.py
from rest_framework import serializers
from apps.cuentas.models import ProducerAccount, AccountMovement


class ProducerAccountSerializer(serializers.ModelSerializer):
    producer_cuit = serializers.CharField(source="producer_cuit_encrypted", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    grain_type_code = serializers.CharField(source="grain_type.code", read_only=True)
    grain_type_name = serializers.CharField(source="grain_type.name", read_only=True)
    campaign_label = serializers.CharField(source="campaign.label", read_only=True)

    class Meta:
        model = ProducerAccount
        fields = [
            "id", "producer_cuit",
            "branch", "branch_name",
            "grain_type", "grain_type_code", "grain_type_name",
            "campaign", "campaign_label",
            "grain_balance_kg", "ars_balance", "usd_balance",
            "is_active", "created_at", "updated_at",
        ]
        # NEVER include producer_cuit_encrypted or producer_cuit_hash


class AccountMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    romaneo_numero = serializers.CharField(source="romaneo.numero", read_only=True, default=None)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = AccountMovement
        fields = [
            "id", "movement_type", "movement_type_display",
            "quantity_kg", "ars_amount", "usd_amount",
            "romaneo", "romaneo_numero",
            "reference_document", "notes",
            "movement_at", "created_by_name",
        ]
        read_only_fields = fields  # All fields read-only in this serializer
```

### T019: ViewSets with CursorPagination (MANDATORY)

```python
# backend/apps/cuentas/views/accounts.py
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets


class AccountCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 25


class MovementCursorPagination(CursorPagination):
    ordering = "-movement_at"
    page_size = 50


class ProducerAccountViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = AccountCursorPagination
    serializer_class = ProducerAccountSerializer

    def get_queryset(self):
        tenant = self.request.user.tenant
        qs = ProducerAccount.objects.filter(
            tenant=tenant
        ).select_related("branch", "grain_type", "campaign", "created_by")

        # CUIT blind index filter
        if cuit := self.request.query_params.get("producer_cuit"):
            from apps.core.encryption.utils import compute_blind_index
            qs = qs.filter(producer_cuit_hash=compute_blind_index(cuit))

        # Optional filters
        for param in ("grain_type", "campaign", "branch"):
            if val := self.request.query_params.get(param):
                qs = qs.filter(**{f"{param}_id": val})

        if is_active := self.request.query_params.get("is_active"):
            qs = qs.filter(is_active=is_active.lower() != "false")

        return qs


class AccountMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = MovementCursorPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ManualMovementSerializer
        return AccountMovementSerializer

    def get_queryset(self):
        tenant = self.request.user.tenant
        account_pk = self.kwargs.get("pk")
        qs = AccountMovement.objects.filter(
            producer_account_id=account_pk,
            tenant=tenant,
        ).select_related("producer_account", "romaneo", "created_by")

        if mt := self.request.query_params.get("movement_type"):
            qs = qs.filter(movement_type=mt)
        if df := self.request.query_params.get("date_from"):
            qs = qs.filter(movement_at__gte=df)
        if dt := self.request.query_params.get("date_to"):
            qs = qs.filter(movement_at__lt=dt)

        return qs

    def perform_create(self, serializer):
        from apps.cuentas.services.accounts import ManualMovementService, MANUAL_TYPES, SUPERVISOR_ONLY_TYPES
        from rest_framework.exceptions import PermissionDenied, ValidationError

        movement_type = serializer.validated_data["movement_type"]
        if movement_type not in MANUAL_TYPES:
            raise ValidationError(
                {"movement_type": f"{movement_type} cannot be created manually."},
                code="invalid_movement_type"
            )
        if movement_type in SUPERVISOR_ONLY_TYPES:
            if not self.request.user.has_permission("settings.admin"):
                raise PermissionDenied(code="permission_denied")

        account_pk = self.kwargs.get("pk")
        account = ProducerAccount.objects.get(pk=account_pk, tenant=self.request.user.tenant)
        ManualMovementService.create_manual_movement(
            account=account,
            operator=self.request.user,
            **serializer.validated_data,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed.", "code": "append_only_violation"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed.", "code": "append_only_violation"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
```

### T021: URL Routing (Explicit Nested Routes)

```python
# backend/apps/cuentas/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter
from apps.cuentas.views.accounts import (
    ProducerAccountViewSet,
    AccountMovementViewSet,
    PosicionConsolidadaView,
    StatementView,
)

router = DefaultRouter()
router.register("accounts", ProducerAccountViewSet, basename="produceraccount")

urlpatterns = router.urls + [
    # DRF router does NOT auto-nest — explicit nested routes required
    path(
        "accounts/<uuid:pk>/movements/",
        AccountMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="account-movement-list",
    ),
    path(
        "accounts/<uuid:pk>/movements/<uuid:movement_pk>/",
        AccountMovementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="account-movement-detail",
    ),
    path(
        "accounts/<uuid:pk>/statement/",
        StatementView.as_view(),
        name="account-statement",
    ),
    path(
        "posicion-consolidada/",
        PosicionConsolidadaView.as_view(),
        name="posicion-consolidada",
    ),
]
```

### T030/T034: APIViews

```python
# PosicionConsolidadaView:
class PosicionConsolidadaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        producer_cuit = request.query_params.get("producer_cuit")
        campaign_id = request.query_params.get("campaign_id")
        if not producer_cuit or not campaign_id:
            return Response(
                {"detail": "producer_cuit and campaign_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign = get_object_or_404(CampanaConfig, pk=campaign_id, tenant=request.user.tenant)
        result = PosicionConsolidadaService.compute(request.user.tenant, producer_cuit, campaign)
        serializer = PosicionConsolidadaSerializer(result)
        return Response(serializer.data)


# StatementView:
class StatementView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        import datetime
        account = get_object_or_404(ProducerAccount, pk=pk, tenant=request.user.tenant)
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")
        if not date_from_str or not date_to_str:
            return Response(
                {"detail": "date_from and date_to are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            date_from = datetime.date.fromisoformat(date_from_str)
            date_to = datetime.date.fromisoformat(date_to_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use ISO8601 (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if date_from > date_to:
            return Response(
                {"detail": "date_from must not be after date_to."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stmt = StatementService.generate(account, date_from, date_to)
        return Response(stmt)
```

### T043: @extend_schema Annotations

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

@extend_schema(
    summary="List producer accounts",
    description="Returns cursor-paginated list of producer accounts for the tenant.",
    parameters=[
        OpenApiParameter("producer_cuit", OpenApiTypes.STR, description="Filter by CUIT (blind index equality)"),
        OpenApiParameter("grain_type", OpenApiTypes.UUID, description="Filter by grain type ID"),
        OpenApiParameter("campaign", OpenApiTypes.UUID, description="Filter by campaign ID"),
        OpenApiParameter("branch", OpenApiTypes.UUID, description="Filter by branch ID"),
        OpenApiParameter("cursor", OpenApiTypes.STR, description="Opaque cursor for pagination"),
    ],
)
def list(self, request, *args, **kwargs): ...
```

---

## T038/T039: Final Test Runs

After all API tasks complete, trigger final test runs:

```bash
# Full spec-13 test suite
bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/

# Poll until done
while [ "$(cat Docs/Tests/spec13-final.status 2>/dev/null)" != "PASSED" ] && \
      [ "$(cat Docs/Tests/spec13-final.status 2>/dev/null)" != "FAILED" ]; do
  sleep 5
done

cat Docs/Tests/spec13-final.status
cat Docs/Tests/spec13-final.summary
grep "FAILED\|ERROR" Docs/Tests/spec13-final.log | head -30

# Acopio regression check
bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
while [ "$(cat Docs/Tests/spec13-regression.status 2>/dev/null)" != "PASSED" ] && \
      [ "$(cat Docs/Tests/spec13-regression.status 2>/dev/null)" != "FAILED" ]; do
  sleep 5
done
cat Docs/Tests/spec13-regression.status
```

If failures found, coordinate with A4 to fix them. A3 owns the API layer code fixes;
A4 owns the test code fixes.

---

## GATE G3 Verification

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(f'{len(urlpatterns)} routes')"
# Must print ≥ 4 routes (router accounts list/detail + 4 explicit paths)
```

Report GATE G3 PASSED to orchestrator.

---

## NEVER

- NEVER expose `producer_cuit_encrypted` or `producer_cuit_hash` in any serializer output
- NEVER use PageNumberPagination — always CursorPagination with the correct ordering/page_size
- NEVER create movement routes via DRF router nesting — always explicit `path()` entries
- NEVER allow PATCH/DELETE on movements to return 2xx — always 405 with `append_only_violation`
- NEVER filter accounts by plaintext CUIT — always compute `compute_blind_index()` first
- NEVER read full research PDFs — use RAG queries above
- NEVER run pytest directly — use `bash scripts/run-tests-external.sh` only
