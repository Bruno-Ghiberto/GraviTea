---
agent: A1
role: "Models + Migration"
agent_type: "python-expert"
model: "sonnet"
spec: "011"
wave: 1
depends_on: []
---

# Agent A1: Models + Migration

## Mission

Create all 3 Django models for spec-11 (Romaneo, QualityAnalysis, MermaCalculation),
generate the database migration, register the models in Django admin, add RLS
policies for tenant isolation, and create the services package init. All 3 models
are tenant-scoped and inherit TenantBoundModel.

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context, wave structure
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- field definitions (FR-011-001 through FR-011-004), acceptance criteria (AC-011-001 through AC-011-005)
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 1, 2, 3, 4, 10)
- `specs/011-romaneo-core/spec.md` -- user stories US1-US8, functional requirements FR-001 through FR-017
- `specs/011-romaneo-core/tasks.md` -- task assignments T001-T009

## Assigned Tasks

| Task | Description |
|------|-------------|
| T001 | Create `backend/apps/acopio/services/__init__.py` empty package init |
| T002 | Verify `backend/apps/acopio/` app is registered in INSTALLED_APPS and URL routing at `/api/v1/acopio/` (from spec-10) |
| T003 | Create Romaneo model with 31 fields, 6-state TextChoices, `save()` override with state machine validation and CONFORME/CERRADO immutability gate, `_generate_romaneo_number()` helper |
| T004 | Create QualityAnalysis model with OneToOneField to Romaneo, 9+ quality parameters |
| T005 | Create MermaCalculation model with OneToOneField to Romaneo, full immutability enforcement |
| T006 | Update `backend/apps/acopio/models/__init__.py` to re-export Romaneo, QualityAnalysis, MermaCalculation |
| T007 | Run `makemigrations gravitea_acopio` to generate `0002_romaneo_core.py` and verify migration applies |
| T008 | Update `backend/apps/acopio/admin.py` with RomaneoAdmin, QualityAnalysisAdmin, MermaCalculationAdmin |
| T009 | Update `backend/database/sql/acopio_rls.sql` with RLS policies for 3 new tables |

## Files to Create

```
backend/apps/acopio/services/__init__.py
backend/apps/acopio/models/romaneo.py
backend/apps/acopio/models/quality_analysis.py
backend/apps/acopio/models/merma_calculation.py
backend/apps/acopio/migrations/0002_romaneo_core.py   (auto-generated)
```

## Files to Modify

- `backend/apps/acopio/models/__init__.py` -- add re-exports for 3 new models
- `backend/apps/acopio/admin.py` -- add admin registration for 3 new models
- `backend/database/sql/acopio_rls.sql` -- add RLS policies for 3 new tables

---

## Domain Knowledge

### RAG Queries (run before writing code)

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo reception document structure fields groups" -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo state machine CONFORME immutable lifecycle" -l 5
```

### Critical Domain Facts

#### Romaneo Fields (31 total, 7 groups)

**Group 1 -- Identification (7 fields):**

| Field | Type | Precision | Null | Default |
|-------|------|-----------|------|---------|
| `id` | UUIDField PK | -- | No | uuid4 |
| `tenant` | FK(Tenant) PROTECT | -- | No | -- |
| `romaneo_number` | CharField(20) | -- | No | auto-generated |
| `status` | CharField choices | -- | No | PENDIENTE |
| `grain_type` | FK(GrainType) PROTECT | -- | No | -- |
| `campaign` | FK(CampanaConfig) PROTECT | -- | No | -- |
| `branch` | FK(Branch) PROTECT | -- | No | -- |

**Group 2 -- Timestamps (6 fields, ADR-035):**

| Field | Type | Null |
|-------|------|------|
| `ts_entrada` | DateTimeField | No |
| `ts_pesada_bruta` | DateTimeField | Yes |
| `ts_calado` | DateTimeField | Yes |
| `ts_analisis` | DateTimeField | Yes |
| `ts_descarga` | DateTimeField | Yes |
| `ts_tara` | DateTimeField | Yes |

**Group 3 -- Vehicle (4 fields):**

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `patente_chasis` | CharField(15) | -- | No |
| `patente_acoplado` | CharField(15) | -- | Yes |
| `driver_name` | CharField(200) | -- | No |
| `driver_dni` | CharField(20) | -- | No |

**Group 4 -- Weight (4 fields):**

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `peso_bruto_kg` | DecimalField | (17,3) | Yes |
| `tara_kg` | DecimalField | (17,3) | Yes |
| `peso_neto_bruto_kg` | DecimalField | (17,3) | Yes |
| `weighbridge_device` | CharField(100) | -- | Yes |

NOTE: `weighbridge_device` is a CharField placeholder. The FK to WeighbridgeDevice
model will be added in a future spec. Use `CharField(max_length=100, null=True,
blank=True)` for now.

**Group 5 -- CPE / Origin (4 fields):**

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `cpe_numero` | CharField(20) | -- | No |
| `ctg_codigo` | CharField(20) | -- | Yes |
| `producer_cuit` | CharField(13) | -- | No |
| `origin_locality` | CharField(200) | -- | No |

**Group 6 -- Storage Assignment (omitted):**

StorageUnit and GrainLot FKs are NOT created in spec-11. They will be added by
spec-12's migration. Omit these fields entirely.

**Group 7 -- Operators & Quality Outcome (7 fields):**

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `operator_id` | FK(AppUser) PROTECT | -- | No |
| `laboratorista_id` | FK(AppUser) SET_NULL | -- | Yes |
| `device_id` | CharField(100) | -- | Yes |
| `grado_asignado` | IntegerField | -- | Yes |
| `bonificacion_rebaja_pct` | DecimalField | (5,2) | Yes |
| `tolerance_table_version` | FK(ToleranceTable) PROTECT | -- | Yes |
| `peso_neto_conforme_kg` | DecimalField | (17,3) | Yes |

Total: 31 fields (after excluding Group 6 and using CharField for weighbridge_device).

#### State Machine (6 states, linear progression)

```
PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO -> CONFORME -> CERRADO
```

- CERRADO is terminal -- no outgoing transitions.
- At CONFORME: only `status`, `tara_kg`, `peso_neto_bruto_kg`, and `ts_tara` may change.
- At CERRADO: absolutely nothing may change.
- Check CERRADO first (stricter guard) before CONFORME in `save()`.

#### QualityAnalysis Fields

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `id` | UUIDField PK | -- | No |
| `romaneo` | OneToOneField(Romaneo) CASCADE | -- | No |
| `humedad_pct` | DecimalField | (5,2) | No |
| `materias_extranas_pct` | DecimalField | (5,2) | No |
| `granos_danados_pct` | DecimalField | (5,2) | No |
| `granos_quebrados_pct` | DecimalField | (5,2) | No |
| `peso_hectolitrico_kg` | DecimalField | (5,2) | Yes |
| `proteina_pct` | DecimalField | (5,2) | Yes |
| `granos_verdes_pct` | DecimalField | (5,2) | Yes |
| `granos_ardidos_pct` | DecimalField | (5,2) | No |
| `cuerpos_extranos_pct` | DecimalField | (5,2) | No |
| `analysis_timestamp` | DateTimeField | -- | No |
| `sample_reference` | CharField(50) | -- | Yes |

#### MermaCalculation Fields (fully immutable)

| Field | Type | Precision | Null |
|-------|------|-----------|------|
| `id` | UUIDField PK | -- | No |
| `romaneo` | OneToOneField(Romaneo) CASCADE | -- | No |
| `merma_table_version` | FK(MermaTable) PROTECT | -- | No |
| `peso_neto_bruto_input_kg` | DecimalField | (17,3) | No |
| `hi_input_pct` | DecimalField | (5,2) | No |
| `hf_used_pct` | DecimalField | (5,2) | No |
| `materias_extranas_input_pct` | DecimalField | (5,2) | No |
| `zarandeo_pct` | DecimalField | (5,2) | No |
| `secado_pct` | DecimalField | (5,2) | No |
| `manipuleo_pct` | DecimalField | (5,2) | No |
| `volatil_pct` | DecimalField | (5,2) | No |
| `peso_post_zarandeo_kg` | DecimalField | (17,3) | No |
| `peso_post_secado_kg` | DecimalField | (17,3) | No |
| `peso_post_manipuleo_kg` | DecimalField | (17,3) | No |
| `peso_final_kg` | DecimalField | (17,3) | No |
| `total_merma_kg` | DecimalField | (17,3) | No |
| `total_factor_pct` | DecimalField | (7,4) | No |
| `calculated_at` | DateTimeField | -- | No (auto_now_add) |
| `calculated_by` | FK(AppUser) PROTECT | -- | No |

---

## Key Patterns

### Pattern 1: TenantBoundModel Inheritance

Reference: `backend/apps/core/models/mixins.py`. All 3 models inherit
TenantBoundModel, declare explicit `tenant` FK, and set both `objects =
TenantBoundManager()` and `all_objects = AllObjectsManager()`.

See 11-plan.md Pattern 1 for the full code example.

### Pattern 2: Immutability Enforcement (save() Override)

Reference: `backend/apps/inventario/models.py` lines 620-669
(`StockMovement.save()`). Romaneo uses field-by-field comparison with an
allowlist of mutable fields at CONFORME.

See 11-plan.md Pattern 2 for the complete `save()` implementation. Key points:

- Check CERRADO first (fully immutable), then CONFORME (allowlist).
- CONFORME allowlist: `status`, `tara_kg`, `peso_neto_bruto_kg`, `ts_tara`.
- MermaCalculation: reject ALL updates (no allowlist), reject ALL deletes.

### Pattern 3: State Machine TextChoices

See 11-plan.md Pattern 3. Define `RomaneoStatus` as inner TextChoices class and
`VALID_TRANSITIONS` dict on the model.

### Pattern 4: OneToOneField Satellite

See 11-plan.md Pattern 4. QualityAnalysis and MermaCalculation use
`OneToOneField("Romaneo", on_delete=CASCADE, related_name=...)`.

### Pattern 10: Sequential Number Generation

See 11-plan.md Pattern 10. `_generate_romaneo_number(branch_id)` uses
`Romaneo.all_objects` with `Max("romaneo_number")` to find the next sequence
number per branch and year. Format: `ROM-YYYY-NNNNN`.

---

## Constraints

- All 3 models MUST inherit `TenantBoundModel` (tenant-scoped, not global).
- All models MUST use UUID PK: `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)`.
- Decimal precision: `(5,2)` for percentages, `(17,3)` for weights, `(7,4)` for factor.
- ALWAYS use explicit `db_table` names: `acopio_romaneo`, `acopio_qualityanalysis`, `acopio_mermacalculation`.
- Romaneo `save()` must handle romaneo_number generation on first save.
- Romaneo `save()` must validate state transitions and enforce immutability.
- MermaCalculation `save()` must reject updates. `delete()` must reject deletion.
- All function parameters and return values must have type hints.
- Use `.venv/bin/python` for all Python commands, never system python.
- Group 6 fields (StorageUnit, GrainLot FKs) are NOT created -- omit entirely.
- `weighbridge_device` is CharField (placeholder), not FK.

### Composite Indexes (Romaneo Meta class)

```python
class Meta:
    db_table = "acopio_romaneo"
    ordering = ["-ts_entrada"]
    indexes = [
        models.Index(
            fields=["tenant_id", "status", "ts_entrada"],
            name="idx_romaneo_tenant_status_ts",
        ),
        models.Index(
            fields=["tenant_id", "branch_id", "ts_entrada"],
            name="idx_romaneo_tenant_branch_ts",
        ),
        models.Index(
            fields=["tenant_id", "campaign_id", "grain_type_id"],
            name="idx_romaneo_tenant_camp_grain",
        ),
    ]
    constraints = [
        models.UniqueConstraint(
            fields=["tenant", "cpe_numero"],
            name="uq_romaneo_tenant_cpe",
        ),
        models.UniqueConstraint(
            fields=["tenant", "romaneo_number"],
            name="uq_romaneo_tenant_number",
        ),
    ]
```

### Admin Registration

See 11-plan.md Admin Registration section for the exact `@admin.register` classes
for all 3 models. Include `list_display`, `list_filter`, `search_fields`, and
`readonly_fields`.

### RLS Policies

See 11-plan.md RLS Policies section for the exact SQL. Add ENABLE + FORCE + policy
+ GRANT for each of the 3 tables: `acopio_romaneo`, `acopio_qualityanalysis`,
`acopio_mermacalculation`.

---

## Checkpoint

**Gate 1 (Models)** -- run after completing all tasks:

```bash
# 1. Verify all 3 new models are importable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import Romaneo, QualityAnalysis, MermaCalculation
print(f'Romaneo fields: {len([f for f in Romaneo._meta.get_fields()])}')
print(f'QualityAnalysis fields: {len([f for f in QualityAnalysis._meta.get_fields()])}')
print(f'MermaCalculation fields: {len([f for f in MermaCalculation._meta.get_fields()])}')
print('Gate 1 (Models): PASS')
"

# 2. Verify TenantBoundModel inheritance for all 3 models
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.models import Romaneo, QualityAnalysis, MermaCalculation
from apps.core.models.mixins import TenantBoundModel
for model in [Romaneo, QualityAnalysis, MermaCalculation]:
    assert issubclass(model, TenantBoundModel), f'{model.__name__} must inherit TenantBoundModel'
print('Gate 1 (TenantBound): PASS')
"

# 3. Verify migration applies
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
../.venv/bin/python manage.py migrate --check
```

**Pass criteria**: All 3 checks print PASS. No import errors, no migration errors.
