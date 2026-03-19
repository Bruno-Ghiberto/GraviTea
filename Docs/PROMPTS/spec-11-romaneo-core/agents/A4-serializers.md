---
agent: A4
role: "Serializers"
agent_type: "python-expert"
model: "sonnet"
spec: "011"
wave: 2
depends_on: [A1]
---

# Agent A4: Serializers

## Mission

Create all DRF serializers for the romaneo module in a single file
`backend/apps/acopio/serializers/romaneo.py`. This includes list/create and detail
serializers for Romaneo (with nested QualityAnalysis and MermaCalculation),
read-only nested serializers for satellite models, and request serializers for each
state transition action endpoint (peso-bruto, tara, analizar, confirmar).

## Context Files (read FIRST)

- `Docs/PROMPTS/spec-11-romaneo-core/11-implement.md` -- orchestrator context
- `Docs/PROMPTS/spec-11-romaneo-core/11-specify.md` -- FR-011-001 (Romaneo fields), FR-011-003 (QualityAnalysis), FR-011-004 (MermaCalculation), FR-011-006 (API endpoints)
- `Docs/PROMPTS/spec-11-romaneo-core/11-plan.md` -- code patterns (Pattern 5 for action endpoint response serializers)
- `specs/011-romaneo-core/spec.md` -- user stories, functional requirements
- `specs/011-romaneo-core/tasks.md` -- task assignments T015-T016, T020, T023, T026, T030

**Reference files (read for existing patterns):**

- `backend/apps/acopio/serializers/reference_data.py` -- existing DRF serializer patterns for the acopio app

## Assigned Tasks

| Task | Description |
|------|-------------|
| T015 | Create `RomaneoSerializer` (list/create) and `RomaneoDetailSerializer` (retrieve with nested QA + MC) |
| T016 | Create `QualityAnalysisSerializer` and `MermaCalculationSerializer` (read-only nested) |
| T020 | Update `backend/apps/acopio/serializers/__init__.py` to re-export all new serializer classes |
| T023 | Create `PesoBrutoSerializer` (peso_bruto_kg required, positive validation) and `TaraSerializer` (tara_kg required, positive validation) |
| T026 | Create `AnalizarSerializer` (inline 9+ quality parameter fields) |
| T030 | Create `ConfirmarSerializer` (grado_asignado required for cereals, optional for oleaginosas) |

## Files to Create

```
backend/apps/acopio/serializers/romaneo.py
```

## Files to Modify

- `backend/apps/acopio/serializers/__init__.py` -- add re-exports for all new serializer classes

---

## Domain Knowledge

### Critical Domain Facts

#### Serializer Classes to Create

All serializers go in ONE file: `backend/apps/acopio/serializers/romaneo.py`.

**1. QualityAnalysisSerializer** -- read-only nested representation.

Fields: `id`, `humedad_pct`, `materias_extranas_pct`, `granos_danados_pct`,
`granos_quebrados_pct`, `peso_hectolitrico_kg`, `proteina_pct`,
`granos_verdes_pct`, `granos_ardidos_pct`, `cuerpos_extranos_pct`,
`analysis_timestamp`, `sample_reference`.

**2. MermaCalculationSerializer** -- read-only nested representation.

Fields: `id`, `merma_table_version`, `peso_neto_bruto_input_kg`, `hi_input_pct`,
`hf_used_pct`, `materias_extranas_input_pct`, `zarandeo_pct`, `secado_pct`,
`manipuleo_pct`, `volatil_pct`, `peso_post_zarandeo_kg`, `peso_post_secado_kg`,
`peso_post_manipuleo_kg`, `peso_final_kg`, `total_merma_kg`, `total_factor_pct`,
`calculated_at`, `calculated_by`.

**3. RomaneoSerializer** -- list/create serializer.

Fields for create: `grain_type`, `campaign`, `branch`, `ts_entrada`,
`patente_chasis`, `patente_acoplado`, `driver_name`, `driver_dni`, `cpe_numero`,
`producer_cuit`, `origin_locality`.

Fields for read: all identification fields + `romaneo_number`, `status`,
`peso_bruto_kg`, `tara_kg`, `peso_neto_bruto_kg`, `peso_neto_conforme_kg`,
`grado_asignado`, `bonificacion_rebaja_pct`.

Read-only fields: `id`, `romaneo_number`, `status`.

**4. RomaneoDetailSerializer** -- retrieve serializer with nested QA + MC.

Extends RomaneoSerializer with:
- `quality_analysis = QualityAnalysisSerializer(read_only=True)`
- `merma_calculation = MermaCalculationSerializer(read_only=True)`
- All timestamp fields
- All operator/device fields

**5. PesoBrutoSerializer** -- request body for peso-bruto action.

Fields: `peso_bruto_kg` (required, DecimalField, min_value > 0).

**6. TaraSerializer** -- request body for tara action.

Fields: `tara_kg` (required, DecimalField, min_value > 0).

**7. AnalizarSerializer** -- request body for analizar action.

Fields: all 9+ quality parameters matching QualityAnalysis model fields.
Common fields required, grain-specific fields optional (nullable).

**8. ConfirmarSerializer** -- request body for confirmar action.

Fields: `grado_asignado` (IntegerField, required for cereals, optional for
oleaginosas). Validation: value must be 0, 1, 2, or 3.

---

## Key Patterns

### Explicit Field Lists (NO `fields = '__all__'`)

Per Constitution IX, all serializers MUST define explicit `fields` lists. Never
use `fields = '__all__'`.

```python
class Meta:
    model = Romaneo
    fields = [
        "id",
        "romaneo_number",
        "status",
        "grain_type",
        "campaign",
        # ... explicit list ...
    ]
    read_only_fields = ["id", "romaneo_number", "status"]
```

### Nested Read-Only Serializers

```python
class RomaneoDetailSerializer(RomaneoSerializer):
    quality_analysis = QualityAnalysisSerializer(read_only=True)
    merma_calculation = MermaCalculationSerializer(read_only=True)

    class Meta(RomaneoSerializer.Meta):
        fields = RomaneoSerializer.Meta.fields + [
            "quality_analysis",
            "merma_calculation",
            # ... additional detail fields ...
        ]
```

### Request Serializers for State Transitions

These are NOT ModelSerializers -- they are plain `Serializer` classes that validate
the request body for action endpoints.

```python
class PesoBrutoSerializer(serializers.Serializer):
    peso_bruto_kg = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
```

### Decimal Precision Convention

- Weight fields: `DecimalField(max_digits=17, decimal_places=3)`
- Percentage fields: `DecimalField(max_digits=5, decimal_places=2)`
- Factor field: `DecimalField(max_digits=7, decimal_places=4)`

---

## Constraints

- ALL serializers go in ONE file: `serializers/romaneo.py`.
- NEVER use `fields = '__all__'` -- always explicit field lists.
- Read-only fields must be explicitly listed in `read_only_fields`.
- Nested serializers (QA, MC) are read-only in the Romaneo detail serializer.
- Request serializers (PesoBruto, Tara, Analizar, Confirmar) are plain `Serializer` classes, NOT `ModelSerializer`.
- Decimal precision must match the model field definitions exactly.
- All function parameters and return values must have type hints.
- Use `.venv/bin/python` for all Python commands, never system python.

### Re-exports in `__init__.py`

Update `backend/apps/acopio/serializers/__init__.py` to re-export all serializer
classes:

```python
from apps.acopio.serializers.romaneo import (
    AnalizarSerializer,
    ConfirmarSerializer,
    MermaCalculationSerializer,
    PesoBrutoSerializer,
    QualityAnalysisSerializer,
    RomaneoDetailSerializer,
    RomaneoSerializer,
    TaraSerializer,
)

__all__ = [
    "AnalizarSerializer",
    "ConfirmarSerializer",
    "MermaCalculationSerializer",
    "PesoBrutoSerializer",
    "QualityAnalysisSerializer",
    "RomaneoDetailSerializer",
    "RomaneoSerializer",
    "TaraSerializer",
]
```

---

## Checkpoint

**Gate 2 (Serializers)** -- run after completing all tasks:

```bash
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.serializers.romaneo import (
    RomaneoSerializer,
    RomaneoDetailSerializer,
    QualityAnalysisSerializer,
    MermaCalculationSerializer,
    PesoBrutoSerializer,
    TaraSerializer,
    AnalizarSerializer,
    ConfirmarSerializer,
)
print(f'RomaneoSerializer fields: {list(RomaneoSerializer().fields.keys())[:5]}...')
print(f'PesoBrutoSerializer fields: {list(PesoBrutoSerializer().fields.keys())}')
print(f'AnalizarSerializer fields: {list(AnalizarSerializer().fields.keys())[:5]}...')
print('Gate 2 (Serializers): PASS')
"
```

**Pass criteria**: All 8 serializer classes import without errors. Field lists are
non-empty and correct.
