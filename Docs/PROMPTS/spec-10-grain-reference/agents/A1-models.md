---
agent: A1
type: python-expert
model: Sonnet 4.6
mission: "Create all 4 Django models, migration, app config, RLS policy, and test conftest for spec-10"
wave: 1
tasks: [T001, T002, T003, T004, T005, T006, T007, T008, T009, T010, T011, T012]
---

# A1: Models & Migrations

## Context Files (read FIRST)

Read these files before writing any code:

1. `Docs/PROMPTS/spec-10-grain-reference/10-specify.md` -- field definitions, constraints,
   acceptance criteria AC-10-001/003/012
2. `Docs/PROMPTS/spec-10-grain-reference/10-plan.md` -- Pattern 1 (AppConfig), Pattern 2
   (Global), Pattern 3 (TenantBound), Pattern 9 (RLS), Pattern 12 (Test Fixtures)
3. `specs/010-grain-reference/tasks.md` -- tasks T001-T012

## Mission

Create the `backend/apps/acopio/` Django application foundation:

1. App scaffolding (T001-T004)
2. All 4 models with correct inheritance (T005-T009)
3. Generate migration (T010)
4. RLS policy for CampanaConfig (T011)
5. Test conftest with factories (T012)

---

## Assigned Tasks

| Task | Description |
|------|-------------|
| T001 | Create `backend/apps/acopio/__init__.py` (empty package init) |
| T002 | Create `backend/apps/acopio/apps.py` with `AcopioConfig` |
| T003 | Create stub `backend/apps/acopio/urls.py` with empty `urlpatterns = []` |
| T004 | Add `"apps.acopio"` to INSTALLED_APPS in `backend/gravitea/settings/base.py` after `"apps.reportes"` |
| T005 | Create `backend/apps/acopio/models/__init__.py` with re-exports |
| T006 | Create GrainType model (GLOBAL) in `backend/apps/acopio/models/grain_type.py` |
| T007 | Create CampanaConfig model (TENANT-SCOPED) in `backend/apps/acopio/models/campana_config.py` |
| T008 | Create ToleranceTable model (GLOBAL) in `backend/apps/acopio/models/tolerance_table.py` |
| T009 | Create MermaTable model (GLOBAL) in `backend/apps/acopio/models/merma_table.py` |
| T010 | Run `cd backend && ../.venv/bin/python manage.py makemigrations gravitea_acopio` |
| T011 | Create RLS policy in `backend/database/sql/acopio_rls.sql` |
| T012 | Create `backend/tests/acopio/__init__.py` and `backend/tests/acopio/conftest.py` |

---

## Domain Knowledge

### RAG Queries (optional -- for field validation)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain type model fields data model specification" -l 3
.venv/bin/python scripts/qdrant/qdrant_search.py -q "campaign year management agricultural" -l 3
```

### Critical Facts (inlined -- do NOT read research PDFs)

- **GrainType, ToleranceTable, MermaTable**: GLOBAL entities. Inherit `models.Model`,
  use `models.Manager()`, NO tenant FK, NO RLS policy.
- **CampanaConfig**: TENANT-SCOPED entity. Inherit `TenantBoundModel`, explicit
  `TenantBoundManager` + `AllObjectsManager`, FK to Tenant.
- All models use UUID PK: `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
- Decimal precision: `(5,2)` for percentages per ADR-007.
- `GrainType.code` max_length=5 (not 3) to accommodate `CEB_F`, `CEB_C`.
- `GrainType.arca_codigo`: `PositiveSmallIntegerField`, unique -- ARCA ncespecie code.
- CampanaConfig validators: `campaign_code` regex `^\d{4}/\d{2}$`, consecutive years,
  `end_date > start_date`.
- CampanaConfig `wslpg_code` property: `"2024/25"` -> `"2425"`.
- Composite indexes on ToleranceTable: `(grain_type_id, valid_to)`,
  `(grain_type_id, parameter, grado_base, valid_to)`.
- Composite indexes on MermaTable: `(grain_type_id, valid_to)`,
  `(grain_type_id, materias_extranas_from_pct, valid_to)`.
- App label: `gravitea_acopio` (use `gravitea_` prefix).
- INSTALLED_APPS: add `"apps.acopio"` after `"apps.reportes"`.

---

## Files to Create

```
backend/apps/acopio/__init__.py
backend/apps/acopio/apps.py
backend/apps/acopio/models/__init__.py
backend/apps/acopio/models/grain_type.py
backend/apps/acopio/models/campana_config.py
backend/apps/acopio/models/tolerance_table.py
backend/apps/acopio/models/merma_table.py
backend/apps/acopio/urls.py
backend/apps/acopio/migrations/0001_initial.py  (auto-generated)
backend/database/sql/acopio_rls.sql
backend/tests/acopio/__init__.py
backend/tests/acopio/conftest.py
```

## Files to Modify

- `backend/gravitea/settings/base.py` -- add `"apps.acopio",` to INSTALLED_APPS after
  `"apps.reportes",`

---

## Key Patterns

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
Django's internal app registry. This matches the pattern used by existing local
apps (`gravitea_ventas`, `gravitea_auth`, `gravitea_compras`, `gravitea_facturacion`,
`gravitea_reportes`).

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

CRITICAL: `hf_secado_pct` is NOT the same as `humedad_base_pct`. Using the wrong
value yields approximately 168 kg error per 30-tonne truck.

### Pattern 3: Tenant-Scoped Entity (CampanaConfig)

Reference: `backend/apps/core/models/mixins.py` (TenantBoundModel)

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

Key points from TenantBoundModel:
- Auto-adds `tenant_id = UUIDField(db_index=True)` (inherited field).
- Sets `objects = TenantBoundManager()` and `all_objects = AllObjectsManager()`.
- `save()` auto-sets `tenant_id` from context if not set and validates FK tenant refs.
- The explicit `tenant = ForeignKey(Tenant, ...)` field is in ADDITION to the inherited
  `tenant_id` -- CampanaConfig needs the FK for Django admin and ORM joins.

### Pattern: ToleranceTable (GLOBAL)

```python
import uuid

from django.db import models


class ToleranceTable(models.Model):
    """
    Quality parameter tolerance thresholds per grain type and grade level.

    GLOBAL entity -- shared across all tenants (ADR-010).
    Supports temporal versioning via valid_from/valid_to.
    valid_to = NULL means currently active version.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grain_type = models.ForeignKey(
        "acopio.GrainType",
        on_delete=models.PROTECT,
        related_name="tolerance_entries",
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    parameter = models.CharField(max_length=50)
    tolerance_pct = models.DecimalField(max_digits=5, decimal_places=2)
    grado_base = models.IntegerField()
    source_resolution = models.CharField(max_length=100, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        db_table = "acopio_tolerancetable"
        indexes = [
            models.Index(
                fields=["grain_type_id", "valid_to"],
                name="idx_tolerance_grain_valid",
            ),
            models.Index(
                fields=["grain_type_id", "parameter", "grado_base", "valid_to"],
                name="idx_tolerance_grain_param_grade",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.grain_type} - {self.parameter} (Grado {self.grado_base})"
```

### Pattern: MermaTable (GLOBAL)

```python
import uuid

from django.db import models


class MermaTable(models.Model):
    """
    Zarandeo (screening) deduction bands per grain type.

    GLOBAL entity -- shared across all tenants (ADR-010, ADR-014).
    Progressive deduction ranges based on foreign matter content.
    Supports temporal versioning via valid_from/valid_to.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grain_type = models.ForeignKey(
        "acopio.GrainType",
        on_delete=models.PROTECT,
        related_name="merma_bands",
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    materias_extranas_from_pct = models.DecimalField(max_digits=5, decimal_places=2)
    materias_extranas_to_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    zarandeo_deduction_pct = models.DecimalField(max_digits=5, decimal_places=2)

    objects = models.Manager()

    class Meta:
        db_table = "acopio_mermatable"
        indexes = [
            models.Index(
                fields=["grain_type_id", "valid_to"],
                name="idx_merma_grain_valid",
            ),
            models.Index(
                fields=["grain_type_id", "materias_extranas_from_pct", "valid_to"],
                name="idx_merma_grain_me_valid",
            ),
        ]

    def __str__(self) -> str:
        to_str = f"{self.materias_extranas_to_pct}" if self.materias_extranas_to_pct else "+"
        return f"{self.grain_type} ME {self.materias_extranas_from_pct}-{to_str}%"
```

### Pattern: RLS Policy (CampanaConfig Only)

Reference: `backend/database/sql/ventas_rls.sql`

```sql
-- ============================================================
-- Row Level Security (RLS) Policies for Acopio Module
-- PostgreSQL 18.1 Required
-- ============================================================
-- Purpose: Defense-in-depth tenant isolation for CampanaConfig.
-- Global tables (GrainType, ToleranceTable, MermaTable) do NOT
-- receive RLS policies per ADR-010/NF-010-010.
-- ============================================================

-- ============================================================
-- CampanaConfig Table RLS
-- ============================================================

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

### Pattern: Test Fixtures (conftest.py for acopio)

Reference: `backend/tests/conftest.py` (root fixtures available: `tenant_context`,
`other_tenant`, `other_tenant_client`, `authenticated_client`, `admin_user`, etc.)

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

### Pattern: models/__init__.py re-exports

```python
from apps.acopio.models.grain_type import GrainType
from apps.acopio.models.campana_config import CampanaConfig
from apps.acopio.models.tolerance_table import ToleranceTable
from apps.acopio.models.merma_table import MermaTable

__all__ = [
    "GrainType",
    "CampanaConfig",
    "ToleranceTable",
    "MermaTable",
]
```

### Pattern: INSTALLED_APPS modification

Add `"apps.acopio",` after the existing `"apps.reportes",` line in
`backend/gravitea/settings/base.py`:

```python
    # Local apps
    "apps.core",
    "apps.core.observability",
    "apps.auth",
    "apps.inventario",
    "apps.sync",
    "apps.facturacion",
    "apps.ventas",
    "apps.compras",
    "apps.reportes",
    "apps.acopio",        # <-- ADD THIS LINE
]
```

---

## Constraints

- NEVER inherit `TenantBoundModel` for global tables (GrainType, ToleranceTable, MermaTable).
- ALWAYS use explicit `db_table` names (`acopio_graintype`, `acopio_campanaconfig`, etc.).
- CampanaConfig MUST have explicit manager declarations (`objects` + `all_objects`)
  per codebase convention.
- All function parameters and return values must have type hints.
- All Python commands must use `.venv/bin/python`, never system python.

---

## Gate 1 Checks

Run these commands after completing all tasks. Report PASS/FAIL for each.

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
