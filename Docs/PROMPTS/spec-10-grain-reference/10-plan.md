---
spec: "010"
name: "Grain Reference Data"
type: Implementation
phase: Plan
created: 2026-03-18
depends_on: [spec-03, spec-09]
blocks: [spec-11, spec-12]
---

# Spec-10: Grain Reference Data -- Plan Context

> **For**: Implementation agents A1--A4 executing in tmux multi-pane layout
> **Produces**: `backend/apps/acopio/` Django application with models, fixtures,
> management command, DRF API, and test suite
> **Spec type**: Implementation (multi-agent, wave execution)

---

## Component Overview

Spec-10 creates the `backend/apps/acopio/` Django application from scratch. This is
the foundational reference data layer for the entire grain elevator (acopio) module.

**What is being built:**

1. **4 Django models** -- `GrainType`, `ToleranceTable`, and `MermaTable` (global
   reference data shared across all tenants) and `CampanaConfig` (tenant-scoped
   campaign year configuration).
2. **3 seed fixture files** -- Official ARCA grain species codes and regulatory
   reference values from the Camara Arbitral de Cereales.
3. **1 management command** -- `seed_grain_reference` for idempotent fixture loading
   with `--dry-run` preview mode.
4. **4 DRF API endpoints** -- Read-only for global tables, full CRUD for campaigns,
   all behind JWT authentication with pagination.
5. **Full test suite** -- Model unit tests, API integration tests, fixture idempotency
   tests, and cross-tenant isolation verification.

**Global vs Tenant-Scoped split:**

- `GrainType`, `ToleranceTable`, `MermaTable` are **GLOBAL** entities (ADR-010).
  They inherit `django.db.models.Model`, use `models.Manager()`, have no `tenant_id`
  field, and receive no RLS policy. All authenticated users see the same data.
- `CampanaConfig` is **TENANT-SCOPED**. It inherits `TenantBoundModel`, gets
  `TenantBoundManager` auto-applied, includes `tenant_id`, and receives an RLS
  policy. Each organization sees only its own campaigns.

---

## Agent Team Orchestration Protocol

### tmux Layout (REQUIRED)

Create a 4-pane tmux session before starting execution. Each pane runs one Claude
Code agent with its dedicated instruction file.

```bash
# Create session
tmux new-session -d -s spec10 -n agents

# Split into 2x2 grid
tmux split-window -h -t spec10:agents
tmux split-window -v -t spec10:agents.0
tmux split-window -v -t spec10:agents.1

# Label panes (optional, for orientation)
# Pane 0 (top-left):     A1 -- Models & Migrations
# Pane 1 (bottom-left):  A3 -- Seed Data
# Pane 2 (top-right):    A2 -- API Layer
# Pane 3 (bottom-right): A4 -- Tests

# Attach
tmux attach -t spec10
```

**Pane activation by wave:**

| Wave | Pane 0 (A1) | Pane 1 (A3) | Pane 2 (A2) | Pane 3 (A4) |
|------|-------------|-------------|-------------|-------------|
| 1    | ACTIVE      | IDLE        | IDLE        | IDLE        |
| 2    | IDLE        | ACTIVE      | ACTIVE      | IDLE        |
| 3    | IDLE        | IDLE        | IDLE        | ACTIVE      |
| 4    | VERIFY      | VERIFY      | VERIFY      | VERIFY      |

### Agent Instruction Files

Each agent reads its dedicated instruction file before starting work. These files
must exist before launching the tmux session:

- `Docs/PROMPTS/spec-10-grain-reference/agents/A1-models.md`
- `Docs/PROMPTS/spec-10-grain-reference/agents/A2-api.md`
- `Docs/PROMPTS/spec-10-grain-reference/agents/A3-seed-data.md`
- `Docs/PROMPTS/spec-10-grain-reference/agents/A4-tests.md`

Each agent instruction file must reference:
- This plan file (`10-plan.md`) for wave execution and checkpoint gates
- The specification context (`10-specify.md`) for field definitions and acceptance criteria
- The spec itself (`specs/010-grain-reference/spec.md`) for functional requirements

---

## Wave Execution Order

### Wave 1: Foundation (A1 -- Sequential)

**Agent**: A1 (Models & Migrations)
**Prerequisite**: None -- this is the first wave.
**Must complete before**: Wave 2 can begin.

**A1 deliverables in order:**

1. Create `backend/apps/acopio/__init__.py` (empty)
2. Create `backend/apps/acopio/apps.py` (`AcopioConfig`)
3. Create `backend/apps/acopio/models/__init__.py` (re-exports all 4 models)
4. Create `backend/apps/acopio/models/grain_type.py` (GrainType -- GLOBAL)
5. Create `backend/apps/acopio/models/campana_config.py` (CampanaConfig -- TenantBound)
6. Create `backend/apps/acopio/models/tolerance_table.py` (ToleranceTable -- GLOBAL)
7. Create `backend/apps/acopio/models/merma_table.py` (MermaTable -- GLOBAL)
8. Create stub `backend/apps/acopio/urls.py` (empty `urlpatterns = []` so the app
   loads without errors when registered)
9. Modify `backend/gravitea/settings/base.py` -- add `"apps.acopio"` to INSTALLED_APPS
   after the last local app entry (`"apps.reportes"`)
10. Run `makemigrations gravitea_acopio` to generate `0001_initial.py`
    NOTE: The migration must include composite indexes for performance per NF-010-009:
    - ToleranceTable: `(grain_type_id, valid_to)` and
      `(grain_type_id, parameter, grado_base, valid_to)`
    - MermaTable: `(grain_type_id, valid_to)` and
      `(grain_type_id, materias_extranas_from_pct, valid_to)`
    Add these as `indexes = [...]` in the model Meta classes so they are included in
    the auto-generated migration. See `10-specify.md` Migration Strategy section.
11. Create `backend/database/sql/acopio_rls.sql` (RLS policy for CampanaConfig only)

**Completion signal**: A1 runs Gate 1 checks and reports PASS/FAIL.

---

### Wave 2: API + Seed Data (A2 + A3 -- Parallel)

**Prerequisite**: Wave 1 Gate 1 PASS.
**A2 and A3 can run simultaneously** -- they have no mutual dependencies.

#### A2: API Layer

1. Create `backend/apps/acopio/serializers/__init__.py`
2. Create `backend/apps/acopio/serializers/reference_data.py` (all 4 serializers)
3. Create `backend/apps/acopio/views/__init__.py`
4. Create `backend/apps/acopio/views/reference_data.py` (all 4 viewsets)
5. Replace stub `backend/apps/acopio/urls.py` with full router registration
6. Create `backend/apps/acopio/admin.py` (all 4 model admin classes)
7. Modify `backend/gravitea/urls.py` -- add `path("acopio/", include("apps.acopio.urls"))`
   inside the `api/v1/` block

#### A3: Seed Data

1. Create `backend/apps/acopio/fixtures/grain_types.json`
2. Create `backend/apps/acopio/fixtures/tolerance_tables.json`
3. Create `backend/apps/acopio/fixtures/merma_tables.json`
4. Create `backend/apps/acopio/management/__init__.py` (empty)
5. Create `backend/apps/acopio/management/commands/__init__.py` (empty)
6. Create `backend/apps/acopio/management/commands/seed_grain_reference.py`

**A3 RAG requirement**: A3 MUST run RAG queries before writing fixture data to
retrieve authoritative regulatory values. See "RAG Queries for Agents" section.

**Completion signal**: Both A2 and A3 run Gate 2 checks and report PASS/FAIL.

---

### Wave 3: Testing (A4 -- Sequential)

**Prerequisite**: Wave 2 Gate 2 PASS (both A2 and A3 confirmed).

**A4 deliverables:**

1. Create `backend/tests/acopio/__init__.py` (empty)
2. Create `backend/tests/acopio/conftest.py` (acopio-specific fixtures)
3. Create `backend/tests/acopio/test_models.py` (model unit tests)
4. Create `backend/tests/acopio/test_api.py` (API integration tests)
5. Create `backend/tests/acopio/test_fixtures.py` (fixture and management command tests)
6. Run test suite via external runner (see Testing Protocol)

**Completion signal**: A4 runs Gate 3 checks and reports PASS/FAIL.

---

### Wave 4: Integration Verification (All Agents)

**Prerequisite**: Wave 3 Gate 3 PASS.

All agents verify the 12 acceptance criteria (AC-10-001 through AC-10-012) by
reviewing Gate 3 test results and running any additional spot checks. Each agent
is responsible for the ACs relevant to their deliverables:

| Agent | Acceptance Criteria |
|-------|-------------------|
| A1    | AC-10-001 (GrainType model), AC-10-003 (CampanaConfig), AC-10-012 (ARCA code uniqueness) |
| A2    | AC-10-006 (API endpoints), AC-10-007 (global no tenant filter), AC-10-008 (campaign isolation) |
| A3    | AC-10-002 (fixture loaded), AC-10-004 (tolerance versioning), AC-10-005 (merma bands), AC-10-009 (idempotency), AC-10-011 (Hf correctness) |
| A4    | AC-10-010 (test suite passing -- all tests green) |

---

## Files to Create

### A1: Models & Migrations

| File | Description |
|------|-------------|
| `backend/apps/acopio/__init__.py` | Empty package init |
| `backend/apps/acopio/apps.py` | `AcopioConfig` with `name="apps.acopio"`, `label="gravitea_acopio"` |
| `backend/apps/acopio/models/__init__.py` | Re-export: `GrainType`, `CampanaConfig`, `ToleranceTable`, `MermaTable` |
| `backend/apps/acopio/models/grain_type.py` | GrainType model (GLOBAL, `models.Model`) |
| `backend/apps/acopio/models/campana_config.py` | CampanaConfig model (TenantBound) |
| `backend/apps/acopio/models/tolerance_table.py` | ToleranceTable model (GLOBAL, `models.Model`) |
| `backend/apps/acopio/models/merma_table.py` | MermaTable model (GLOBAL, `models.Model`) |
| `backend/apps/acopio/urls.py` | Stub with `urlpatterns = []` (replaced by A2 in Wave 2) |
| `backend/apps/acopio/migrations/0001_initial.py` | Auto-generated by `makemigrations` |
| `backend/database/sql/acopio_rls.sql` | RLS policy for `acopio_campanaconfig` table only |

### A2: API Layer

| File | Description |
|------|-------------|
| `backend/apps/acopio/pagination.py` | `ReferenceDataPagination(PageNumberPagination)` — overrides project default `StandardCursorPagination` because global models lack `created_at` field |
| `backend/apps/acopio/serializers/__init__.py` | Re-export all serializer classes |
| `backend/apps/acopio/serializers/reference_data.py` | `GrainTypeSerializer`, `CampanaConfigSerializer`, `ToleranceTableSerializer`, `MermaTableSerializer` |
| `backend/apps/acopio/views/__init__.py` | Re-export all viewset classes |
| `backend/apps/acopio/views/reference_data.py` | `GrainTypeViewSet`, `CampanaConfigViewSet`, `ToleranceTableViewSet`, `MermaTableViewSet` — all use `pagination_class = ReferenceDataPagination` |
| `backend/apps/acopio/urls.py` | Full `DefaultRouter` registration (replaces A1 stub) |
| `backend/apps/acopio/admin.py` | Admin registration for all 4 models |

### A3: Seed Data

| File | Description |
|------|-------------|
| `backend/apps/acopio/fixtures/grain_types.json` | 7 primary grain types with ARCA codes and regulatory values |
| `backend/apps/acopio/fixtures/tolerance_tables.json` | Tolerance thresholds for 5 primary grains |
| `backend/apps/acopio/fixtures/merma_tables.json` | Zarandeo deduction bands for 5 primary grains |
| `backend/apps/acopio/management/__init__.py` | Empty package init |
| `backend/apps/acopio/management/commands/__init__.py` | Empty package init |
| `backend/apps/acopio/management/commands/seed_grain_reference.py` | Idempotent seed command with `--dry-run` |

### A4: Tests

| File | Description |
|------|-------------|
| `backend/tests/acopio/__init__.py` | Empty package init |
| `backend/tests/acopio/conftest.py` | Acopio-specific fixtures (grain_type factory, campana factory, etc.) |
| `backend/tests/acopio/test_models.py` | Model unit tests: fields, constraints, validation, Hf correctness |
| `backend/tests/acopio/test_api.py` | API integration tests: endpoints, filtering, pagination, tenant isolation |
| `backend/tests/acopio/test_fixtures.py` | Fixture tests: seed command, idempotency, data correctness |

---

## Files to Modify

| File | Agent | Change |
|------|-------|--------|
| `backend/gravitea/settings/base.py` | A1 | Add `"apps.acopio",` to INSTALLED_APPS after `"apps.reportes",` |
| `backend/gravitea/urls.py` | A2 | Add `path("acopio/", include("apps.acopio.urls")),` inside the `api/v1/` include block |

---

## Key Code Patterns

### Pattern 1: AppConfig Registration

Reference: `backend/apps/ventas/apps.py`

```python
"""Acopio app configuration."""

from django.apps import AppConfig


class AcopioConfig(AppConfig):
    """Configuration for Acopio (Grain Elevator) app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.acopio"
    label = "gravitea_acopio"
    verbose_name = "Acopio"
```

The `label` must use the `gravitea_` prefix to avoid namespace conflicts with
Django's internal app registry. This matches the pattern used by most existing
local apps (`gravitea_ventas`, `gravitea_auth`, `gravitea_compras`,
`gravitea_facturacion`, `gravitea_reportes`). Note: some older apps
(`apps.inventario`, `apps.sync`, `apps.core`) use default labels without the
prefix, but all new apps should adopt `gravitea_` for consistency.

### Pattern 2: Global Reference Entity (GrainType, ToleranceTable, MermaTable)

These models do NOT inherit `TenantBoundModel`. They use standard `models.Model`
with `models.Manager()` as the default manager. Per ADR-010, global reference
data is shared across all tenants.

```python
import uuid

from django.db import models


class GrainType(models.Model):
    """
    Officially recognized grain species with ARCA code and regulatory parameters.

    GLOBAL entity -- shared across all tenants (ADR-010).
    Uses standard Manager, no tenant_id, no RLS policy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=5, unique=True)  # Internal: TRI, MAI, SOJ, CEB_F
    arca_codigo = models.PositiveSmallIntegerField(unique=True)  # ARCA ncespecie
    name = models.CharField(max_length=100)  # Spanish name
    humedad_base_pct = models.DecimalField(max_digits=5, decimal_places=2)
    hf_secado_pct = models.DecimalField(max_digits=5, decimal_places=2)  # != humedad_base_pct
    manipuleo_fijo_pct = models.DecimalField(max_digits=5, decimal_places=2)
    volatil_fijo_pct = models.DecimalField(max_digits=5, decimal_places=2)
    grading_system = models.CharField(
        max_length=10,
        choices=[("GRADO", "Grado"), ("TOLERANCE", "Tolerance")],
        default="GRADO",
    )
    is_active = models.BooleanField(default=True)

    objects = models.Manager()  # Explicit: standard manager, no tenant filtering

    class Meta:
        db_table = "acopio_graintype"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["code"], name="uq_graintype_code"),
            models.UniqueConstraint(fields=["arca_codigo"], name="uq_graintype_arca_codigo"),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"
```

**Critical**: `hf_secado_pct` is NOT the same as `humedad_base_pct`. Using the wrong
value yields approximately 168 kg error per 30-tonne truck. A dedicated test must
assert inequality for all grains where these values differ.

### Pattern 3: Tenant-Scoped Entity (CampanaConfig)

Reference: `backend/apps/core/models/mixins.py` lines 28--137

```python
import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class CampanaConfig(TenantBoundModel):
    """
    Agricultural campaign year configuration per organization.

    TENANT-SCOPED entity -- inherits TenantBoundModel.
    Gets TenantBoundManager auto-applied and tenant_id auto-added.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="campaign_configs",
    )
    campaign_code = models.CharField(max_length=7)  # "YYYY/YY" e.g. "2025/26"
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)

    # Explicit manager declarations (matches codebase convention in ventas models)
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_campanaconfig"
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "campaign_code"],
                name="uq_campana_tenant_code",
            ),
            models.UniqueConstraint(
                fields=["tenant", "is_active"],
                condition=models.Q(is_active=True),
                name="uq_campana_one_active_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"Campana {self.campaign_code} ({'active' if self.is_active else 'inactive'})"

    @property
    def wslpg_code(self) -> str:
        """Convert 'YYYY/YY' to 'XXYY' format for WSLPG submission."""
        parts = self.campaign_code.split("/")
        return f"{parts[0][2:]}{parts[1]}"

    def clean(self) -> None:
        """Validate campaign_code format and date range consistency."""
        super().clean()
        if not re.match(r"^\d{4}/\d{2}$", self.campaign_code):
            raise ValidationError({"campaign_code": "Campaign code must be YYYY/YY format."})
        start_year = int(self.campaign_code[:4])
        end_suffix = int(self.campaign_code[5:])
        if end_suffix != (start_year + 1) % 100:
            raise ValidationError({"campaign_code": "Campaign code years must be consecutive."})
        if self.end_date <= self.start_date:
            raise ValidationError({"end_date": "end_date must be after start_date."})
```

**Key points from TenantBoundModel:**
- Auto-adds `tenant_id = UUIDField(db_index=True)` (inherited field)
- Sets `objects = TenantBoundManager()` and `all_objects = AllObjectsManager()`
- `save()` auto-sets `tenant_id` from context if not set and validates FK tenant refs
- The explicit `tenant = ForeignKey(Tenant, ...)` field is in ADDITION to the inherited
  `tenant_id` -- CampanaConfig needs the FK for Django admin and ORM joins

### Pattern 4: Serializer with Field Mapping

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

### Pattern 5: PageNumber Pagination Override

The project default is `StandardCursorPagination` (orders by `created_at`). Global acopio
models (GrainType, ToleranceTable, MermaTable) have no `created_at` field, so cursor
pagination would **fail**. All acopio viewsets must use this override:

```python
# backend/apps/acopio/pagination.py
from rest_framework.pagination import PageNumberPagination


class ReferenceDataPagination(PageNumberPagination):
    """
    Page-number pagination for acopio reference data.

    Overrides project default CursorPagination because:
    1. Global models lack created_at field (cursor ordering fails)
    2. REST API Design v1.0 Section 2.6 requires count/next/previous envelope
    3. Reference data is < 100 rows — offset performance is not a concern

    Justified deviation from Constitution Principle XIII (cursor-based).
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
```

All viewsets set `pagination_class = ReferenceDataPagination`.

### Pattern 6: ViewSet -- ReadOnly for Global, ModelViewSet for Tenant-Scoped

Reference: `backend/apps/ventas/views.py`

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class GrainTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for grain types. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/grain-types/
    GET /api/v1/acopio/grain-types/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GrainTypeSerializer
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
```

### Pattern 7: Django Fixture Format

Fixtures use standard Django JSON format with `model`, `pk`, and `fields` keys.
GrainType fixtures use UUID primary keys.

```json
[
  {
    "model": "gravitea_acopio.graintype",
    "pk": "a1b2c3d4-...",
    "fields": {
      "code": "TRI",
      "arca_codigo": 15,
      "name": "Trigo pan",
      "humedad_base_pct": "14.00",
      "hf_secado_pct": "13.50",
      "manipuleo_fijo_pct": "0.10",
      "volatil_fijo_pct": "0.30",
      "grading_system": "GRADO",
      "is_active": true
    }
  }
]
```

NOTE: The `model` key uses the app label (`gravitea_acopio`) not the app name
(`apps.acopio`). However, the management command should use `update_or_create`
with Python dicts rather than `loaddata` -- this gives better control over
idempotency and logging.

### Pattern 8: Management Command with update_or_create

```python
from django.core.management.base import BaseCommand

from apps.acopio.models import GrainType


class Command(BaseCommand):
    help = "Load grain reference data (grain types, tolerances, merma bands) idempotently."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        # ... load grain_types, tolerance_tables, merma_tables
        # Use update_or_create keyed on natural key fields
        for grain_data in GRAIN_TYPES:
            obj, created = GrainType.objects.update_or_create(
                code=grain_data["code"],
                defaults={...},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action}: {obj}")
```

### Pattern 9: RLS Policy (CampanaConfig Only)

Reference: `backend/database/sql/ventas_rls.sql`

```sql
-- RLS for CampanaConfig only. Global tables (GrainType, ToleranceTable,
-- MermaTable) do NOT receive RLS policies per ADR-010/NF-010-010.

ALTER TABLE acopio_campanaconfig ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_campanaconfig FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS campanaconfig_tenant_isolation ON acopio_campanaconfig;
CREATE POLICY campanaconfig_tenant_isolation ON acopio_campanaconfig
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY campanaconfig_tenant_isolation ON acopio_campanaconfig IS
'Ensures campaign configs are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_campanaconfig TO gravitea_app;
```

### Pattern 10: Admin Registration

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

### Pattern 11: URL Router Registration

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

### Pattern 12: Test Fixtures (conftest.py for acopio)

Reference: `backend/tests/ventas/conftest.py` and `backend/tests/conftest.py`

```python
import pytest
from datetime import date

from apps.core.managers.tenant_bound import set_current_tenant_id, clear_current_tenant_id


@pytest.fixture
def grain_type_factory(db):
    """Factory for creating GrainType instances."""
    from apps.acopio.models import GrainType

    def create_grain_type(**kwargs):
        defaults = {
            "code": "TRI",
            "arca_codigo": 15,
            "name": "Trigo pan",
            "humedad_base_pct": "14.00",
            "hf_secado_pct": "13.50",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
            "grading_system": "GRADO",
            "is_active": True,
        }
        defaults.update(kwargs)
        return GrainType.objects.create(**defaults)

    return create_grain_type


@pytest.fixture
def seed_grain_types(db):
    """Load all 7 primary grain types via the management command."""
    from django.core.management import call_command
    call_command("seed_grain_reference")


@pytest.fixture
def campana_factory(tenant_context):
    """Factory for creating CampanaConfig instances."""
    from apps.acopio.models import CampanaConfig

    def create_campana(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "campaign_code": "2025/26",
            "start_date": date(2025, 12, 1),
            "end_date": date(2026, 11, 30),
            "is_active": False,
        }
        defaults.update(kwargs)
        return CampanaConfig.objects.create(**defaults)

    return create_campana
```

NOTE: `grain_type_factory` uses `db` fixture (not `tenant_context`) because
GrainType is a GLOBAL model with no tenant dependency. `campana_factory` uses
`tenant_context` because CampanaConfig is tenant-scoped.

---

## Checkpoint Gates

### Gate 1: After Wave 1 (Models)

A1 runs these checks before signaling Wave 1 complete:

```bash
# 1. Verify app is registered and migration was created
cd backend && ../.venv/bin/python manage.py showmigrations gravitea_acopio

# 2. Verify all 4 models are importable
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import GrainType, CampanaConfig, ToleranceTable, MermaTable
print(f'GrainType fields: {[f.name for f in GrainType._meta.get_fields()]}')
print(f'CampanaConfig fields: {[f.name for f in CampanaConfig._meta.get_fields()]}')
print(f'ToleranceTable fields: {[f.name for f in ToleranceTable._meta.get_fields()]}')
print(f'MermaTable fields: {[f.name for f in MermaTable._meta.get_fields()]}')
print('Gate 1: PASS')
"

# 3. Verify CampanaConfig inherits TenantBoundModel
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import CampanaConfig
from apps.core.models.mixins import TenantBoundModel
assert issubclass(CampanaConfig, TenantBoundModel), 'CampanaConfig must inherit TenantBoundModel'
print('TenantBoundModel inheritance: PASS')
"

# 4. Verify GrainType does NOT inherit TenantBoundModel
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import GrainType
from apps.core.models.mixins import TenantBoundModel
assert not issubclass(GrainType, TenantBoundModel), 'GrainType must NOT inherit TenantBoundModel'
print('GrainType global pattern: PASS')
"
```

**Pass criteria**: All 4 checks print PASS. No import errors, no migration errors.

### Gate 2: After Wave 2 (API + Seed Data)

A2 and A3 each run their portion:

**A2 checks (API):**

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

**A3 checks (Seed Data):**

```bash
# 1. Verify dry-run mode works
cd backend && ../.venv/bin/python manage.py seed_grain_reference --dry-run

# 2. Verify actual seed (requires database)
cd backend && ../.venv/bin/python manage.py seed_grain_reference
cd backend && ../.venv/bin/python -c "
from apps.acopio.models import GrainType, ToleranceTable, MermaTable
gt_count = GrainType.objects.count()
tt_count = ToleranceTable.objects.count()
mt_count = MermaTable.objects.count()
assert gt_count >= 7, f'Expected >= 7 grain types, got {gt_count}'
assert tt_count > 0, f'Expected > 0 tolerance entries, got {tt_count}'
assert mt_count > 0, f'Expected > 0 merma entries, got {mt_count}'
# Critical: Soja Hf must be 12.50, not 13.50
from decimal import Decimal
soja = GrainType.objects.get(code='SOJ')
assert soja.hf_secado_pct == Decimal('12.50'), f'Soja Hf must be 12.50, got {soja.hf_secado_pct}'
print(f'Gate 2 (Seed): PASS -- {gt_count} grains, {tt_count} tolerances, {mt_count} merma bands')
"
```

**Pass criteria**: All A2 and A3 checks pass. URLs resolve, admin registered,
seed command loads data with correct values.

### Gate 3: After Wave 3 (Tests)

A4 runs the test suite using the EXTERNAL runner. NEVER run pytest directly
inside Claude Code.

```bash
# 1. Run full acopio test suite
bash scripts/run-tests-external.sh -n spec10-verify tests/acopio/

# 2. Poll for completion (repeat until not RUNNING)
cat Docs/Tests/spec10-verify.status

# 3. Read summary when status is PASSED or FAILED
cat Docs/Tests/spec10-verify.summary

# 4. If FAILED, debug specific failures
grep "FAILED" Docs/Tests/spec10-verify.log
grep -A 10 "FAILED tests/acopio/test_" Docs/Tests/spec10-verify.log
```

**Pass criteria**: `.status` file reads `PASSED`. Summary shows 0 failures, 0 errors.
Minimum 20 tests collected. If FAILED, A4 fixes failures and re-runs.

### Gate 4: Final Acceptance

Verify all 12 acceptance criteria from `specs/010-grain-reference/spec.md`:

| AC | Description | Verification Method |
|----|-------------|-------------------|
| AC-10-001 | GrainType model complete | Gate 1 check + test_models.py |
| AC-10-002 | GrainType fixture loaded (>= 7 grains, correct values) | Gate 2 seed check + test_fixtures.py |
| AC-10-003 | CampanaConfig tenant isolation + one-active constraint | test_models.py |
| AC-10-004 | ToleranceTable temporal versioning | test_fixtures.py |
| AC-10-005 | MermaTable zarandeo bands (multiple rows per grain) | test_fixtures.py |
| AC-10-006 | All 4 API endpoints functional | test_api.py |
| AC-10-007 | Global tables same data for different tenants | test_api.py (multi-tenant test) |
| AC-10-008 | CampanaConfig different data per tenant | test_api.py (multi-tenant test) |
| AC-10-009 | Fixture idempotency (no duplicates on re-run) | test_fixtures.py |
| AC-10-010 | Test suite passing (>= 20 tests) | Gate 3 summary |
| AC-10-011 | Hf != humedad_base for applicable grains | test_models.py |
| AC-10-012 | ARCA code uniqueness enforced | test_models.py |

**Pass criteria**: All 12 ACs verified as PASS.

---

## Testing Protocol

### CRITICAL: Test Execution Rules

1. **NEVER** run pytest directly inside Claude Code -- it consumes too many tokens
   and can hang the session.
2. **ALWAYS** use `scripts/run-tests-external.sh` for test execution. It runs pytest
   in a background process and writes results to files.
3. Read `.status` file to check completion, `.summary` for results.
4. Only grep specific failures from `.log` file if needed.

### Test Categories

| Category | File | What It Tests | Marks |
|----------|------|---------------|-------|
| Model unit tests | `test_models.py` | GrainType CRUD, constraints (unique code, unique arca_codigo), CampanaConfig validation (code format, date range, year consistency), CampanaConfig active constraint, WSLPG code conversion, Hf vs humedad_base correctness | `@pytest.mark.django_db` |
| API integration tests | `test_api.py` | All 4 endpoints (list/detail), filtering (`?is_active=true`, `?grain_type={uuid}`), pagination envelope, JWT auth required (401 without token), global tables return same data for different tenants, CampanaConfig returns different data per tenant | `@pytest.mark.django_db` |
| Fixture tests | `test_fixtures.py` | `seed_grain_reference` creates correct record counts, idempotency (run twice, same count), dry-run mode (no writes), data correctness (Soja Hf=12.50), merma bands have no gaps, tolerance entries exist for 5 primary grains | `@pytest.mark.django_db` |
| Tenant isolation | `test_api.py` | CampanaConfig cross-tenant isolation (use `other_tenant_client` fixture from root conftest), global tables visible to all tenants | `@pytest.mark.django_db`, `@pytest.mark.tenant_isolation` |

### Minimum Test Count

AC-10-010 requires at least 20 tests. Target breakdown:

| File | Estimated Tests |
|------|----------------|
| `test_models.py` | 8--10 (fields, constraints, validation, wslpg_code, Hf check) |
| `test_api.py` | 8--10 (4 endpoints x list/detail, filtering, auth, tenant isolation) |
| `test_fixtures.py` | 4--6 (seed, idempotency, dry-run, data correctness) |
| **Total** | **20--26** |

### Test Execution Commands

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec10 tests/acopio/

# Run only model tests
bash scripts/run-tests-external.sh -n spec10-models -k "test_model" tests/acopio/

# Run only API tests
bash scripts/run-tests-external.sh -n spec10-api -k "test_api" tests/acopio/

# Run only fixture/seed tests
bash scripts/run-tests-external.sh -n spec10-fixtures -k "test_fixture" tests/acopio/

# Run with fail-fast (stop on first failure)
bash scripts/run-tests-external.sh -n spec10-fast --fail-fast tests/acopio/
```

### Test Output Location

All test output goes to `Docs/Tests/`:

| File | Contents | How to Read |
|------|----------|-------------|
| `Docs/Tests/spec10.status` | `RUNNING`, `PASSED`, `FAILED`, or `ERROR` | `cat` (1 line) |
| `Docs/Tests/spec10.summary` | Test counts, failures, coverage | `cat` (~20 lines) |
| `Docs/Tests/spec10.log` | Full pytest output | `grep "FAILED"` only |

---

## RAG Queries for Agents

Agents MUST run RAG queries to retrieve authoritative regulatory data before writing
code that depends on domain-specific values. Do NOT invent tolerance/merma values.

### A3 (Seed Data) -- MUST run before writing fixtures

```bash
# Query 1: ARCA grain species codes and moisture constants
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "grain types codes ARCA humidity base" -l 5

# Query 2: Tolerance tables and bonification/rebaja values
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "tolerance tables bonification rebaja" -l 5

# Query 3: Merma calculation parameters and zarandeo deduction bands
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "merma calculation formula sequential" -l 5

# Query 4: Quality parameters per grain type (for tolerance fixture)
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "grain quality parameters humidity moisture" -l 5

# Query 5: ARCA official commodity nomenclature
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "ARCA grain commodity codes grain type nomenclature" -l 5
```

### A1 (Models) -- Optional, for field validation

```bash
# Verify field names and types from Data Model specification
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "grain type model fields data model specification" -l 3

# Verify campaign year configuration structure
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "campaign year management agricultural" -l 3
```

### A4 (Tests) -- Optional, for test data verification

```bash
# Verify expected grain type values for assertions
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "grain types quality parameters reference" -l 3
```

---

## FR-to-Agent Traceability

Every functional requirement from `specs/010-grain-reference/spec.md` maps to an
agent and wave:

| FR | Description | Agent | Wave | AC |
|----|-------------|-------|------|-----|
| FR-001 | GrainType model with all fields | A1 | 1 | AC-10-001 |
| FR-002 | Unique code + arca_codigo constraints | A1 | 1 | AC-10-012 |
| FR-003 | 7 grain fixture with regulatory values | A3 | 2 | AC-10-002 |
| FR-004 | CampanaConfig per organization | A1 | 1 | AC-10-003 |
| FR-005 | One active campaign per tenant | A1 | 1 | AC-10-003 |
| FR-006 | Campaign code validation (format, consecutive years) | A1 | 1 | AC-10-003 |
| FR-007 | WSLPG code conversion property | A1 | 1 | AC-10-003 |
| FR-008 | ToleranceTable with temporal versioning | A1 | 1 | AC-10-004 |
| FR-009 | MermaTable zarandeo bands | A1 | 1 | AC-10-005 |
| FR-010 | Idempotent seed operation | A3 | 2 | AC-10-009 |
| FR-011 | Preview/dry-run mode | A3 | 2 | AC-10-009 |
| FR-012 | Read-only endpoints (3 global tables) | A2 | 2 | AC-10-006, AC-10-007 |
| FR-013 | CRUD campaign endpoint (tenant-scoped) | A2 | 2 | AC-10-006, AC-10-008 |
| FR-014 | Filtering support | A2 | 2 | AC-10-006 |
| FR-015 | Paginated envelope format | A2 | 2 | AC-10-006 |
| FR-016 | Global vs tenant-scoped data access | A1 + A2 | 1 + 2 | AC-10-007, AC-10-008 |
| FR-017 | Admin interfaces | A2 | 2 | (implicit) |

---

## Done Criteria

Spec-10 is complete when ALL of the following are true:

1. All 4 models exist with correct fields, constraints, and inheritance patterns.
   Migration `0001_initial.py` applies without errors.
2. All 3 fixture files contain correct regulatory values sourced from RAG queries.
   Minimum: 7 grain types, tolerance entries for 5 primary grains, merma bands
   for 5 primary grains.
3. `seed_grain_reference` command loads data idempotently. Running twice produces
   zero duplicates. `--dry-run` reports without writing.
4. All 4 API endpoints return correct responses with JWT authentication, pagination
   envelope, and filtering support.
5. CampanaConfig tenant isolation is verified -- each tenant sees only its own
   campaigns. Cross-tenant access returns empty results.
6. Global tables (GrainType, ToleranceTable, MermaTable) return the same data
   regardless of which tenant is querying.
7. Test suite passes with 20+ tests and 90%+ coverage for `apps/acopio/`.
8. Acceptance criteria AC-10-001 through AC-10-012 all verified as PASS.
9. RLS policy for `acopio_campanaconfig` exists in `database/sql/acopio_rls.sql`.
10. Soja `hf_secado_pct` is `12.50` (not `13.50`), verified by dedicated test.
