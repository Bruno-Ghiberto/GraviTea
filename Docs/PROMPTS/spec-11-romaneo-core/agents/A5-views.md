---
agent: A5
role: "Views + URLs"
agent_type: "backend-architect"
model: "sonnet"
spec: "011"
wave: 3
depends_on: [A1, A3, A4]
---

# Agent A5: Views + URLs

## Mission

Create the DRF viewsets for the romaneo module: `RomaneoViewSet` with CRUD
operations, 6 state transition action endpoints, and a merma preview endpoint;
`QualityAnalysisViewSet` as a nested viewset under romaneo. Register all URL routes,
add pagination, and update the module re-exports. This agent delivers the full API
layer that consumes serializers (A4) and the merma service (A3).

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- FR-011-006 (Romaneo API), FR-011-007 (QA API), endpoint table with HTTP methods and status codes
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 5, Pattern 6, Pattern 11)
- `specs/011-romaneo-core/spec.md` -- user stories, acceptance criteria
- `specs/011-romaneo-core/tasks.md` -- task assignments T017-T019, T021-T022, T024-T025, T027-T029, T031-T035

**Reference files (read for existing patterns):**

- `backend/apps/acopio/views/reference_data.py` -- existing DRF viewset patterns for the acopio app
- `backend/apps/acopio/urls.py` -- existing router registration pattern
- `backend/apps/acopio/pagination.py` -- existing pagination class

## Assigned Tasks

| Task | Description |
|------|-------------|
| T017 | Create RomaneoViewSet with CRUD (list, create, retrieve, partial_update) and PATCH guard returning 409 for CONFORME/CERRADO |
| T018 | Add `confirmar_arribo` action endpoint (POST, PENDIENTE->EN_PROCESO, returns 202) |
| T019 | Create RomaneoPagination class (PageNumberPagination, page_size=25, max=100) |
| T021 | Update `backend/apps/acopio/views/__init__.py` to re-export RomaneoViewSet, QualityAnalysisViewSet |
| T022 | Register `romaneos` route on the DRF router in `backend/apps/acopio/urls.py` |
| T024 | Add `peso_bruto` action endpoint (POST, EN_PROCESO->PESADO) |
| T025 | Add `tara` action endpoint (POST, CONFORME only, computes peso_neto_bruto_kg) |
| T027 | Add `analizar` action endpoint (POST, PESADO->ANALIZADO, creates QualityAnalysis) |
| T028 | Create QualityAnalysisViewSet nested under romaneo with state guards |
| T029 | Add nested QA URL route (`romaneos/<uuid:romaneo_pk>/quality-analysis/`) |
| T032 | Add `confirmar` action endpoint (POST, ANALIZADO->CONFORME, triggers merma calculation) |
| T033 | Add grade assignment logic into the confirmar action |
| T034 | Add `merma_preview` action endpoint (GET, non-persisting) |
| T035 | Add `cerrar` action endpoint (POST, CONFORME->CERRADO, returns 202) |

## Files to Create

```
backend/apps/acopio/views/romaneo.py
```

## Files to Modify

- `backend/apps/acopio/views/__init__.py` -- add re-exports for RomaneoViewSet, QualityAnalysisViewSet
- `backend/apps/acopio/urls.py` -- register romaneo router route + nested QA path
- `backend/apps/acopio/pagination.py` -- add RomaneoPagination class

---

## Domain Knowledge

### RAG Queries (optional -- for API endpoint validation)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo API endpoints state transition action" -l 5
```

### Critical Domain Facts

#### API Endpoint Table

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `POST` | `/api/v1/acopio/romaneos/` | Create romaneo (PENDIENTE) | 201 |
| `GET` | `/api/v1/acopio/romaneos/` | List romaneos (paginated) | 200 |
| `GET` | `/api/v1/acopio/romaneos/{id}/` | Retrieve with nested QA + MC | 200 |
| `PATCH` | `/api/v1/acopio/romaneos/{id}/` | Update (PENDIENTE/EN_PROCESO only) | 200 / 409 |
| `POST` | `.../romaneos/{id}/confirmar-arribo/` | PENDIENTE -> EN_PROCESO | 202 |
| `POST` | `.../romaneos/{id}/peso-bruto/` | EN_PROCESO -> PESADO | 200 |
| `POST` | `.../romaneos/{id}/analizar/` | PESADO -> ANALIZADO | 200 |
| `POST` | `.../romaneos/{id}/confirmar/` | ANALIZADO -> CONFORME | 200 |
| `POST` | `.../romaneos/{id}/tara/` | Capture tare while CONFORME | 200 |
| `POST` | `.../romaneos/{id}/cerrar/` | CONFORME -> CERRADO | 202 |
| `GET` | `.../romaneos/{id}/merma-preview/` | Non-persisting merma projection | 200 |
| `POST` | `.../romaneos/{id}/quality-analysis/` | Create QA satellite | 201 |
| `GET` | `.../romaneos/{id}/quality-analysis/` | Retrieve QA | 200 |
| `PATCH` | `.../romaneos/{id}/quality-analysis/` | Update QA (ANALIZADO only) | 200 / 409 |

#### State Transition Rules

Each state transition action MUST validate the current status and return 409 if
the romaneo is not in the expected state:

```python
{
    "type": "invalid_state_transition",
    "detail": "Romaneo must be in {EXPECTED} status.",
    "current_status": romaneo.status,
    "attempted_transition": "action-name",
}
```

For PATCH on CONFORME/CERRADO romaneos:

```python
{
    "type": "romaneo_immutable",
    "detail": "Cannot modify romaneo in {status} status.",
    "current_status": romaneo.status,
}
```

#### HTTP Status Code Rules

- 202 Accepted: `confirmar-arribo` (async WSCPE) and `cerrar` (async WSCPE x 2)
- 200 OK: all other successful state transitions
- 201 Created: POST create romaneo, POST create QA
- 409 Conflict: invalid state transition, immutability violation
- 404 Not Found: cross-tenant access (TenantBoundManager returns empty queryset)

#### Confirmar Action (IMMUTABILITY GATE)

The `confirmar` action is the most complex -- it must:

1. Validate romaneo is in ANALIZADO status (409 if not).
2. Validate quality analysis exists (409 if not).
3. Validate request body with ConfirmarSerializer (`grado_asignado`).
4. Call `lookup_zarandeo_deduction()` from merma service to get MermaTable band.
5. Call `build_merma_input()` to construct input dict.
6. Call `calculate_merma_deductions()` to run the Rust/Python calculation.
7. Create MermaCalculation record with all inputs, intermediates, and final values.
8. Set `grado_asignado`, `bonificacion_rebaja_pct`, `tolerance_table_version`,
   `peso_neto_conforme_kg` on the Romaneo instance.
9. Transition status to CONFORME.
10. Save romaneo.
11. Return RomaneoDetailSerializer response with 200.

#### Tara Action

The `tara` action captures the tare weight while the romaneo is in CONFORME status.
It does NOT transition the state -- the romaneo stays in CONFORME. The tare weight
must be less than the gross weight.

```python
romaneo.tara_kg = validated_data["tara_kg"]
romaneo.peso_neto_bruto_kg = romaneo.peso_bruto_kg - romaneo.tara_kg
romaneo.ts_tara = timezone.now()
romaneo.save()
```

#### Cerrar Action

Requires `tara_kg` to be present (non-null). If tara_kg is null, return 409.
Transitions CONFORME -> CERRADO. Returns 202 (async WSCPE enqueued).

---

## Key Patterns

### Pattern 5: DRF Action Endpoints (State Transitions)

See 11-plan.md Pattern 5 for the full examples of `confirmar_arribo` and
`peso_bruto` action implementations. Each action follows this structure:

```python
@action(detail=True, methods=["post"], url_path="action-name")
def action_name(self, request, pk=None):
    romaneo = self.get_object()
    if romaneo.status != Romaneo.RomaneoStatus.EXPECTED_STATUS:
        return Response(
            {
                "type": "invalid_state_transition",
                "detail": "Romaneo must be in EXPECTED status.",
                "current_status": romaneo.status,
                "attempted_transition": "action-name",
            },
            status=status.HTTP_409_CONFLICT,
        )
    # ... perform action ...
    romaneo.save()
    serializer = RomaneoDetailSerializer(romaneo)
    return Response(serializer.data, status=status.HTTP_200_OK)
```

### Pattern 6: Nested ViewSet (QualityAnalysis)

See 11-plan.md Pattern 6 for the `QualityAnalysisViewSet` implementation:

- `CreateModelMixin + RetrieveModelMixin + UpdateModelMixin + GenericViewSet`
- Nested under `romaneos/<uuid:romaneo_pk>/quality-analysis/`
- Create guard: romaneo must be EN_PROCESO or PESADO
- Update guard: romaneo must be ANALIZADO
- Return 409 for CONFORME/CERRADO modifications

URL registration pattern:

```python
urlpatterns = [
    path("", include(router.urls)),
    path(
        "romaneos/<uuid:romaneo_pk>/quality-analysis/",
        QualityAnalysisViewSet.as_view({
            "post": "create",
            "get": "retrieve",
            "patch": "partial_update",
        }),
        name="romaneo-quality-analysis",
    ),
]
```

### Pattern 11: Romaneo Pagination

See 11-plan.md Pattern 11. Add to existing `pagination.py`:

```python
class RomaneoPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
```

### PATCH Guard for Immutable Romaneos

Override `partial_update` on RomaneoViewSet to guard CONFORME/CERRADO:

```python
def partial_update(self, request, *args, **kwargs):
    romaneo = self.get_object()
    if romaneo.status in (
        Romaneo.RomaneoStatus.CONFORME,
        Romaneo.RomaneoStatus.CERRADO,
    ):
        return Response(
            {
                "type": "romaneo_immutable",
                "detail": f"Cannot modify romaneo in {romaneo.status} status.",
                "current_status": romaneo.status,
            },
            status=status.HTTP_409_CONFLICT,
        )
    return super().partial_update(request, *args, **kwargs)
```

---

## Constraints

- ALL view classes go in ONE file: `views/romaneo.py`.
- RomaneoViewSet must use `RomaneoPagination` for list view.
- RomaneoViewSet must use `RomaneoSerializer` for list/create and `RomaneoDetailSerializer` for retrieve.
- All endpoints require `IsAuthenticated` permission.
- State transition actions must be `@action(detail=True, methods=["post"])`.
- Merma preview must be `@action(detail=True, methods=["get"])`.
- The `confirmar` action must import and call functions from `apps.acopio.services.merma_engine`.
- QualityAnalysisViewSet must enforce state guards (create: EN_PROCESO/PESADO; update: ANALIZADO only).
- All function parameters and return values must have type hints.
- Use `.venv/bin/python` for all Python commands, never system python.

### Views re-exports in `__init__.py`

```python
from apps.acopio.views.romaneo import QualityAnalysisViewSet, RomaneoViewSet

__all__ = [
    "QualityAnalysisViewSet",
    "RomaneoViewSet",
]
```

---

## Checkpoint

**Gate 3 (API)** -- run after completing all tasks:

```bash
# 1. Verify URL routing
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from django.urls import reverse
print(reverse('romaneo-list'))
print(reverse('romaneo-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'}))
print('Gate 3 (URLs): PASS')
"

# 2. Verify admin registration for 3 new models
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from django.contrib import admin
from apps.acopio.models import Romaneo, QualityAnalysis, MermaCalculation
for model in [Romaneo, QualityAnalysis, MermaCalculation]:
    assert admin.site.is_registered(model), f'{model.__name__} not registered in admin'
print('Gate 3 (Admin): PASS')
"
```

**Pass criteria**: URL patterns resolve for romaneo list and detail. Admin models
are registered.
