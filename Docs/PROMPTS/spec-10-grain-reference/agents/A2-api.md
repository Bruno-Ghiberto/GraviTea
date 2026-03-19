---
agent: A2
type: backend-architect
model: Sonnet 4.6
mission: "Create DRF serializers, viewsets, URL routing, pagination, and admin for spec-10"
wave: 2
tasks: [T019, T020, T021, T022, T023, T025, T026, T027, T030, T031, T032, T034, T035, T036, T038]
---

# A2: API Layer

## Context Files (read FIRST)

Read these files before writing any code:

1. `Docs/PROMPTS/spec-10-grain-reference/10-specify.md` -- FR-010-010 through FR-010-013,
   field definitions, acceptance criteria AC-10-006/007/008
2. `Docs/PROMPTS/spec-10-grain-reference/10-plan.md` -- Patterns 4-6 (Serializer,
   Pagination, ViewSet), Pattern 10 (Admin), Pattern 11 (Router)
3. `specs/010-grain-reference/contracts/api.md` -- API contract with request/response schemas
4. `specs/010-grain-reference/tasks.md` -- tasks T019-T027, T030-T032, T034-T036, T038

## Mission

Create the complete DRF API layer:

1. Pagination class override (T019) -- CRITICAL: project default is CursorPagination,
   acopio needs PageNumberPagination
2. All 4 serializers (T020, T025, T030, T034)
3. All 4 viewsets (T021, T026, T031, T035)
4. URL routing (T022-T023, T027, T032, T036)
5. Admin registration (T038)

---

## Assigned Tasks

| Task | User Story | Description |
|------|-----------|-------------|
| T019 | US1 | Create `ReferenceDataPagination(PageNumberPagination)` in `backend/apps/acopio/pagination.py` |
| T020 | US1 | Create `GrainTypeSerializer` in `backend/apps/acopio/serializers/reference_data.py` |
| T021 | US1 | Create `GrainTypeViewSet` (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` |
| T022 | US1 | Create `backend/apps/acopio/serializers/__init__.py` and `backend/apps/acopio/views/__init__.py` |
| T023 | US1 | Replace stub `backend/apps/acopio/urls.py` with full router. Add `path("acopio/", include("apps.acopio.urls"))` to `backend/gravitea/urls.py` |
| T025 | US2 | Create `CampanaConfigSerializer` in `backend/apps/acopio/serializers/reference_data.py` |
| T026 | US2 | Create `CampanaConfigViewSet` (ModelViewSet) in `backend/apps/acopio/views/reference_data.py` |
| T027 | US2 | Register campaigns endpoint in router |
| T030 | US3 | Create `ToleranceTableSerializer` in `backend/apps/acopio/serializers/reference_data.py` |
| T031 | US3 | Create `ToleranceTableViewSet` (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` |
| T032 | US3 | Register tolerance-tables endpoint in router |
| T034 | US4 | Create `MermaTableSerializer` in `backend/apps/acopio/serializers/reference_data.py` |
| T035 | US4 | Create `MermaTableViewSet` (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` |
| T036 | US4 | Register merma-tables endpoint in router |
| T038 | Polish | Create admin registration in `backend/apps/acopio/admin.py` |

---

## Domain Knowledge

### Critical Facts

- **GrainTypeSerializer field mappings**: API field `codigo` maps to model field
  `arca_codigo`; API field `nombre` maps to model field `name`. These mappings are
  required by the REST API Design v1.0 Section 4.1.
- **Global viewsets** (GrainType, ToleranceTable, MermaTable): `ReadOnlyModelViewSet`,
  standard `Manager`, no tenant filtering. All authenticated users see the same data.
- **CampanaConfig viewset**: `ModelViewSet` (full CRUD), `TenantBoundManager` auto-filters
  by tenant_id, `perform_create` sets `tenant_id` from `request.user.tenant_id`.
- **ALL viewsets**: `pagination_class = ReferenceDataPagination` (PageNumberPagination
  override). The project default `StandardCursorPagination` orders by `created_at` --
  global models have no `created_at` field and cursor pagination would fail.
- **ALL viewsets**: `permission_classes = [IsAuthenticated]`.
- **Filter params**: `is_active` (GrainType, Campaigns), `grain_type` (Tolerance, Merma),
  `valid_from_before` (Tolerance).
- **ToleranceTable/MermaTable viewsets**: use `select_related("grain_type")` for
  performance.
- **Pagination envelope**: `{ "count", "next", "previous", "results" }` per FR-015.

### API Contract Summary

| Endpoint | Method | Scope | ViewSet Type |
|----------|--------|-------|-------------|
| `/api/v1/acopio/grain-types/` | GET (list/detail) | GLOBAL | ReadOnlyModelViewSet |
| `/api/v1/acopio/tolerance-tables/` | GET (list/detail) | GLOBAL | ReadOnlyModelViewSet |
| `/api/v1/acopio/merma-tables/` | GET (list/detail) | GLOBAL | ReadOnlyModelViewSet |
| `/api/v1/acopio/campaigns/` | GET/POST/PUT/PATCH/DELETE | TENANT | ModelViewSet |

---

## Files to Create

```
backend/apps/acopio/pagination.py
backend/apps/acopio/serializers/__init__.py
backend/apps/acopio/serializers/reference_data.py
backend/apps/acopio/views/__init__.py
backend/apps/acopio/views/reference_data.py
backend/apps/acopio/admin.py
```

## Files to Modify

- `backend/apps/acopio/urls.py` -- replace A1 stub with full router registration
- `backend/gravitea/urls.py` -- add `path("acopio/", include("apps.acopio.urls")),`
  inside the `api/v1/` include block, after the `reportes/` entry

---

## Key Patterns

### Pattern: PageNumber Pagination Override (T019)

The project default is `StandardCursorPagination` (orders by `created_at`). Global
acopio models have no `created_at` field, so cursor pagination would fail. All acopio
viewsets must use this override:

```python
# backend/apps/acopio/pagination.py
from rest_framework.pagination import PageNumberPagination


class ReferenceDataPagination(PageNumberPagination):
    """
    Page-number pagination for acopio reference data.

    Overrides project default CursorPagination because:
    1. Global models lack created_at field (cursor ordering fails)
    2. REST API Design v1.0 Section 2.6 requires count/next/previous envelope
    3. Reference data is < 100 rows -- offset performance is not a concern

    Justified deviation from Constitution Principle XIII (cursor-based).
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
```

### Pattern: Serializer with Field Mapping (T020)

Reference: REST API Design v1.0 Section 4.1 (field names `codigo`, `nombre`)

```python
from rest_framework import serializers

from apps.acopio.models import GrainType


class GrainTypeSerializer(serializers.ModelSerializer):
    """
    GrainType serializer for API responses.

    Field mapping per REST API Design v1.0 Section 4.1:
    - API field 'codigo' maps to model field 'arca_codigo'
    - API field 'nombre' maps to model field 'name'
    """

    codigo = serializers.IntegerField(source="arca_codigo", read_only=True)
    nombre = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = GrainType
        fields = [
            "id",
            "code",
            "codigo",       # -> arca_codigo
            "nombre",       # -> name
            "humedad_base_pct",
            "hf_secado_pct",
            "manipuleo_fijo_pct",
            "volatil_fijo_pct",
            "grading_system",
            "is_active",
        ]
        read_only_fields = fields
```

### Pattern: CampanaConfig Serializer (T025)

```python
from apps.acopio.models import CampanaConfig


class CampanaConfigSerializer(serializers.ModelSerializer):
    """CampanaConfig serializer -- tenant-scoped, full CRUD."""

    class Meta:
        model = CampanaConfig
        fields = [
            "id",
            "campaign_code",
            "start_date",
            "end_date",
            "is_active",
            "notes",
        ]
        read_only_fields = ["id"]
```

NOTE: `tenant` is NOT in `fields` -- it is auto-set in `perform_create` from
the JWT claims. Do not expose tenant_id in the API response.

### Pattern: ToleranceTable Serializer (T030)

```python
from apps.acopio.models import ToleranceTable


class ToleranceTableSerializer(serializers.ModelSerializer):
    """ToleranceTable serializer -- read-only, GLOBAL."""

    class Meta:
        model = ToleranceTable
        fields = [
            "id",
            "grain_type",
            "valid_from",
            "valid_to",
            "parameter",
            "tolerance_pct",
            "grado_base",
            "source_resolution",
        ]
        read_only_fields = fields
```

### Pattern: MermaTable Serializer (T034)

```python
from apps.acopio.models import MermaTable


class MermaTableSerializer(serializers.ModelSerializer):
    """MermaTable serializer -- read-only, GLOBAL."""

    class Meta:
        model = MermaTable
        fields = [
            "id",
            "grain_type",
            "valid_from",
            "valid_to",
            "materias_extranas_from_pct",
            "materias_extranas_to_pct",
            "zarandeo_deduction_pct",
        ]
        read_only_fields = fields
```

### Pattern: ViewSet -- ReadOnly for Global, ModelViewSet for Tenant-Scoped (T021, T026, T031, T035)

Reference: `backend/apps/ventas/views.py`

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.acopio.models import CampanaConfig, GrainType, MermaTable, ToleranceTable
from apps.acopio.pagination import ReferenceDataPagination
from apps.acopio.serializers import (
    CampanaConfigSerializer,
    GrainTypeSerializer,
    MermaTableSerializer,
    ToleranceTableSerializer,
)


class GrainTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for grain types. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/grain-types/
    GET /api/v1/acopio/grain-types/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GrainTypeSerializer
    pagination_class = ReferenceDataPagination
    # GLOBAL: uses standard Manager, NOT TenantBoundManager
    queryset = GrainType.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs


class CampanaConfigViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for campaign configuration. TENANT-SCOPED.

    GET/POST    /api/v1/acopio/campaigns/
    GET/PUT/PATCH/DELETE /api/v1/acopio/campaigns/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CampanaConfigSerializer
    pagination_class = ReferenceDataPagination
    # TENANT-SCOPED: TenantBoundManager auto-filters by tenant_id
    queryset = CampanaConfig.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.user.tenant_id)


class ToleranceTableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for tolerance tables. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/tolerance-tables/
    GET /api/v1/acopio/tolerance-tables/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ToleranceTableSerializer
    pagination_class = ReferenceDataPagination
    queryset = ToleranceTable.objects.select_related("grain_type").all()

    def get_queryset(self):
        qs = super().get_queryset()
        grain_type = self.request.query_params.get("grain_type")
        if grain_type is not None:
            qs = qs.filter(grain_type_id=grain_type)
        valid_from_before = self.request.query_params.get("valid_from_before")
        if valid_from_before is not None:
            qs = qs.filter(valid_from__lte=valid_from_before)
        return qs


class MermaTableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for merma tables. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/merma-tables/
    GET /api/v1/acopio/merma-tables/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MermaTableSerializer
    pagination_class = ReferenceDataPagination
    queryset = MermaTable.objects.select_related("grain_type").all()

    def get_queryset(self):
        qs = super().get_queryset()
        grain_type = self.request.query_params.get("grain_type")
        if grain_type is not None:
            qs = qs.filter(grain_type_id=grain_type)
        return qs
```

### Pattern: Admin Registration (T038)

Reference: `backend/apps/ventas/admin.py`

```python
from django.contrib import admin

from .models import CampanaConfig, GrainType, MermaTable, ToleranceTable


@admin.register(GrainType)
class GrainTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "arca_codigo", "name", "grading_system", "is_active"]
    list_filter = ["grading_system", "is_active"]
    search_fields = ["code", "name"]


@admin.register(CampanaConfig)
class CampanaConfigAdmin(admin.ModelAdmin):
    list_display = ["campaign_code", "tenant", "start_date", "end_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["campaign_code"]


@admin.register(ToleranceTable)
class ToleranceTableAdmin(admin.ModelAdmin):
    list_display = ["grain_type", "parameter", "grado_base", "tolerance_pct", "valid_from", "valid_to"]
    list_filter = ["parameter", "valid_to"]
    search_fields = ["grain_type__code", "parameter"]


@admin.register(MermaTable)
class MermaTableAdmin(admin.ModelAdmin):
    list_display = ["grain_type", "materias_extranas_from_pct", "materias_extranas_to_pct", "zarandeo_deduction_pct", "valid_from", "valid_to"]
    list_filter = ["valid_to"]
    search_fields = ["grain_type__code"]
```

### Pattern: URL Router Registration (T023, T027, T032, T036)

Reference: `backend/apps/ventas/urls.py`

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CampanaConfigViewSet,
    GrainTypeViewSet,
    MermaTableViewSet,
    ToleranceTableViewSet,
)

router = DefaultRouter()
router.register(r"grain-types", GrainTypeViewSet, basename="grain-type")
router.register(r"tolerance-tables", ToleranceTableViewSet, basename="tolerance-table")
router.register(r"merma-tables", MermaTableViewSet, basename="merma-table")
router.register(r"campaigns", CampanaConfigViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
]
```

### Pattern: URL Include in gravitea/urls.py (T023)

Add inside the `api/v1/` include block, after the reportes line:

```python
                # Reportes (reporting infrastructure)
                path("reportes/", include("apps.reportes.urls")),
                # Acopio (grain elevator reference data)
                path("acopio/", include("apps.acopio.urls")),
                # Core (customization: field definitions, module config)
                path("", include("apps.core.urls")),
```

### Pattern: serializers/__init__.py re-exports (T022)

```python
from apps.acopio.serializers.reference_data import (
    CampanaConfigSerializer,
    GrainTypeSerializer,
    MermaTableSerializer,
    ToleranceTableSerializer,
)

__all__ = [
    "GrainTypeSerializer",
    "CampanaConfigSerializer",
    "ToleranceTableSerializer",
    "MermaTableSerializer",
]
```

### Pattern: views/__init__.py re-exports (T022)

```python
from apps.acopio.views.reference_data import (
    CampanaConfigViewSet,
    GrainTypeViewSet,
    MermaTableViewSet,
    ToleranceTableViewSet,
)

__all__ = [
    "GrainTypeViewSet",
    "CampanaConfigViewSet",
    "ToleranceTableViewSet",
    "MermaTableViewSet",
]
```

---

## Constraints

- ALL viewsets MUST set `pagination_class = ReferenceDataPagination` -- do not use
  the project default `StandardCursorPagination`.
- GrainType, ToleranceTable, MermaTable viewsets MUST use `ReadOnlyModelViewSet`
  (no create/update/delete).
- CampanaConfig viewset MUST use `ModelViewSet` (full CRUD).
- CampanaConfig `perform_create` MUST set `tenant_id` from `request.user.tenant_id`.
- `tenant` field MUST NOT be in CampanaConfigSerializer `fields` list.
- All function parameters and return values must have type hints.
- All Python commands must use `.venv/bin/python`, never system python.

---

## Gate 2 (API) Checks

Run these commands after completing all tasks. Report PASS/FAIL for each.

```bash
# 1. Verify URL patterns registered
cd backend && ../.venv/bin/python -c "
from django.urls import reverse
print(reverse('grain-type-list'))
print(reverse('tolerance-table-list'))
print(reverse('merma-table-list'))
print(reverse('campaign-list'))
print('Gate 2 (URLs): PASS')
"

# 2. Verify admin registration
cd backend && ../.venv/bin/python -c "
from django.contrib import admin
from apps.acopio.models import GrainType, CampanaConfig, ToleranceTable, MermaTable
assert admin.site.is_registered(GrainType), 'GrainType not registered in admin'
assert admin.site.is_registered(CampanaConfig), 'CampanaConfig not registered in admin'
assert admin.site.is_registered(ToleranceTable), 'ToleranceTable not registered in admin'
assert admin.site.is_registered(MermaTable), 'MermaTable not registered in admin'
print('Gate 2 (Admin): PASS')
"
```

**Pass criteria**: All URL names resolve. All 4 models registered in admin.
