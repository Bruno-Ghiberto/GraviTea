---
spec: "011"
name: "Romaneo Core"
type: Implementation
phase: Plan
created: 2026-03-19
context_for: "/speckit.plan"
depends_on: [spec-10]
blocks: [spec-12, spec-13]
agents: [A1, A2, A3, A4, A5, A6]
---

# Spec-11: Romaneo Core -- Plan Context

> **For**: Implementation agents A1--A6 executing in tmux multi-pane layout
> **Produces**: 3 Django models in `backend/apps/acopio/`, 1 Rust module in
> `rust/gravitea-core/src/merma.rs`, DRF serializers + viewsets, Python merma
> service with FFI wrapper, and full test suite
> **Spec type**: Implementation (multi-agent, wave execution)

---

## Component Overview

Spec-11 implements the romaneo (grain reception document) lifecycle -- the central
transactional workflow of the acopio operation. This builds on spec-10's reference
data models (GrainType, ToleranceTable, MermaTable, CampanaConfig) which provide
lookup tables consumed by the merma engine and quality grading logic.

**What is being built:**

1. **3 Django models** -- `Romaneo` (31 fields, 7 groups, 6-state state machine
   with immutability gate at CONFORME), `QualityAnalysis` (one-to-one satellite
   with 9+ quality parameters), and `MermaCalculation` (one-to-one immutable
   satellite storing the sequential merma formula result with full audit trail).
2. **1 Rust module** -- `merma.rs` implementing the sequential merma calculation
   (zarandeo -> secado -> manipuleo -> volatil) with PyO3 bindings, following the
   Circular CAC 10/86 formula. Exposed as `calculate_merma()` to Python.
3. **1 Python service** -- `merma_engine.py` wrapping the Rust FFI call with a
   pure-Python fallback for development/testing convenience, plus MermaTable lookup
   logic.
4. **DRF serializers** -- Romaneo, QualityAnalysis, MermaCalculation serializers
   with nested representations and state transition request serializers.
5. **DRF viewsets** -- `RomaneoViewSet` with 6 state transition action endpoints,
   `QualityAnalysisViewSet` as nested viewset, merma preview endpoint.
6. **Full test suite** -- Model unit tests, state machine transition tests, merma
   calculation correctness tests, API integration tests, immutability enforcement
   tests, and tenant isolation verification. Minimum 40 tests, 90%+ coverage.

**All 3 models are TENANT-SCOPED** -- they inherit `TenantBoundModel`, use
`TenantBoundManager`, include `tenant_id`, and receive RLS policies. This differs
from spec-10 where GrainType, ToleranceTable, and MermaTable were global.

---

## Agent Team Orchestration Protocol

### Team Structure

| Agent | Role | Deliverables |
|-------|------|-------------|
| **A1** | Models + Migration | `models/romaneo.py`, `models/quality_analysis.py`, `models/merma_calculation.py`, `models/__init__.py` update, `admin.py` update, `0002_romaneo_core.py` migration, `database/sql/acopio_rls.sql` update |
| **A2** | Rust Merma Engine | `rust/gravitea-core/src/merma.rs` (calculate_merma function, serde structs, validation, Rust unit tests), `rust/gravitea-core/src/lib.rs` update (register export) |
| **A3** | Python Merma Service | `services/merma_engine.py` (Rust FFI wrapper, MermaTable lookup, Python fallback implementation, merma preview logic) |
| **A4** | API Layer -- Serializers | `serializers/romaneo.py` (Romaneo, QualityAnalysis, MermaCalculation serializers with nested representations, state transition request serializers) |
| **A5** | API Layer -- Views + URLs | `views/romaneo.py` (RomaneoViewSet with 6 action endpoints, QualityAnalysisViewSet nested, merma preview), `urls.py` update, `pagination.py` update |
| **A6** | Tests | `tests/acopio/test_romaneo_models.py`, `test_romaneo_api.py`, `test_quality_analysis.py`, `test_merma_calculation.py`, `test_merma_rust.py`, `conftest.py` update |

### Wave Execution Order

```
Wave 1 (parallel):  A1 (models + migration)  |  A2 (Rust merma engine)
  Prerequisite: None
  Must complete before: Wave 2

Wave 2 (parallel):  A3 (merma service)  |  A4 (serializers)
  Prerequisite: Wave 1 Gate 1 PASS (A1 models importable, A2 Rust builds)
  A3 depends on: A1 (model imports) + A2 (Rust FFI)
  A4 depends on: A1 (model imports) only

Wave 3 (sequential): A5 (views + URLs)
  Prerequisite: Wave 2 Gate 2 PASS (A3 service importable, A4 serializers importable)

Wave 4 (sequential): A6 (full test suite)
  Prerequisite: Wave 3 Gate 3 PASS (URL routing resolves)

Wave 5 (all): Integration verification
  Prerequisite: Wave 4 Gate 4 PASS (all tests green)
```

### tmux Layout (REQUIRED)

Create a 6-pane tmux session before starting execution. Each pane runs one Claude
Code agent with its dedicated instruction file.

```bash
# Create session
tmux new-session -d -s spec11 -n agents

# Split into 3x2 grid
tmux split-window -h -t spec11:agents
tmux split-window -h -t spec11:agents.0
tmux select-layout -t spec11:agents even-horizontal
tmux split-window -v -t spec11:agents.0
tmux split-window -v -t spec11:agents.1
tmux split-window -v -t spec11:agents.2

# Pane assignment:
# Pane 0 (top-left):      A1 -- Models + Migration
# Pane 1 (bottom-left):   A2 -- Rust Merma Engine
# Pane 2 (top-center):    A3 -- Python Merma Service
# Pane 3 (bottom-center): A4 -- Serializers
# Pane 4 (top-right):     A5 -- Views + URLs
# Pane 5 (bottom-right):  A6 -- Tests

# Attach
tmux attach -t spec11
```

**Pane activation by wave:**

| Wave | A1 (P0) | A2 (P1) | A3 (P2) | A4 (P3) | A5 (P4) | A6 (P5) |
|------|---------|---------|---------|---------|---------|---------|
| 1    | ACTIVE  | ACTIVE  | IDLE    | IDLE    | IDLE    | IDLE    |
| 2    | IDLE    | IDLE    | ACTIVE  | ACTIVE  | IDLE    | IDLE    |
| 3    | IDLE    | IDLE    | IDLE    | IDLE    | ACTIVE  | IDLE    |
| 4    | IDLE    | IDLE    | IDLE    | IDLE    | IDLE    | ACTIVE  |
| 5    | VERIFY  | VERIFY  | VERIFY  | VERIFY  | VERIFY  | VERIFY  |

### Agent Instruction Files

Each agent reads its dedicated instruction file before starting work. These files
are created by `/speckit.design` (Phase D) and must exist before launching the
tmux session:

- `Docs/PROMPTS/spec-11-romaneo-core/agents/A1-models.md`
- `Docs/PROMPTS/spec-11-romaneo-core/agents/A2-rust.md`
- `Docs/PROMPTS/spec-11-romaneo-core/agents/A3-merma-service.md`
- `Docs/PROMPTS/spec-11-romaneo-core/agents/A4-serializers.md`
- `Docs/PROMPTS/spec-11-romaneo-core/agents/A5-views.md`
- `Docs/PROMPTS/spec-11-romaneo-core/agents/A6-tests.md`

Each agent instruction file must reference:
- This plan file (`11-plan.md`) for wave execution and checkpoint gates
- The specification context (`11-specify.md`) for field definitions and acceptance criteria
- The spec itself (`specs/011-romaneo-core/spec.md`) for user stories and functional requirements

---

## Files to Create

### A1: Models + Migration

| File | Description |
|------|-------------|
| `backend/apps/acopio/models/romaneo.py` | Romaneo model (31 fields, 7 groups, 6-state state machine, immutability gate at CONFORME) |
| `backend/apps/acopio/models/quality_analysis.py` | QualityAnalysis model (OneToOne satellite of Romaneo, 9+ quality parameters) |
| `backend/apps/acopio/models/merma_calculation.py` | MermaCalculation model (OneToOne immutable satellite, all merma inputs/intermediates/final) |
| `backend/apps/acopio/migrations/0002_romaneo_core.py` | Auto-generated migration for 3 new models |

### A2: Rust Merma Engine

| File | Description |
|------|-------------|
| `rust/gravitea-core/src/merma.rs` | Rust merma calculation engine: `calculate_merma(input_json) -> String`, serde structs, validation, 10+ unit tests |

### A3: Python Merma Service

| File | Description |
|------|-------------|
| `backend/apps/acopio/services/__init__.py` | Empty package init |
| `backend/apps/acopio/services/merma_engine.py` | Rust FFI wrapper with Python fallback, MermaTable lookup, merma preview logic |

### A4: Serializers

| File | Description |
|------|-------------|
| `backend/apps/acopio/serializers/romaneo.py` | `RomaneoSerializer`, `RomaneoDetailSerializer` (nested QA + MC), `QualityAnalysisSerializer`, `MermaCalculationSerializer`, state transition request serializers (`PesoBrutoSerializer`, `TaraSerializer`, `ConfirmarSerializer`, `AnalizarSerializer`) |

### A5: Views + URLs

| File | Description |
|------|-------------|
| `backend/apps/acopio/views/romaneo.py` | `RomaneoViewSet` (CRUD + 6 action endpoints + merma preview), `QualityAnalysisViewSet` (nested under romaneo) |

### A6: Tests

| File | Description |
|------|-------------|
| `backend/tests/acopio/test_romaneo_models.py` | Model unit tests: creation, state machine (all valid + invalid transitions), immutability enforcement, romaneo number generation, timestamps |
| `backend/tests/acopio/test_romaneo_api.py` | API integration tests: CRUD endpoints, state transition actions, pagination, tenant isolation, error responses (409 for invalid transitions, immutable edits) |
| `backend/tests/acopio/test_quality_analysis.py` | QualityAnalysis model + API tests: creation, OneToOne constraint, parameter precision, update guards |
| `backend/tests/acopio/test_merma_calculation.py` | Merma correctness tests: sequential formula verification, multiple grain types, edge cases (Hi <= Hf, zero foreign matter), Hf vs humedad_base validation, immutability |
| `backend/tests/acopio/test_merma_rust.py` | Rust FFI tests: calculate_merma parity with Python fallback, error handling, boundary conditions |

---

## Files to Modify

| File | Agent | Change |
|------|-------|--------|
| `backend/apps/acopio/models/__init__.py` | A1 | Add re-exports for `Romaneo`, `QualityAnalysis`, `MermaCalculation` |
| `backend/apps/acopio/admin.py` | A1 | Add admin registration for `Romaneo`, `QualityAnalysis`, `MermaCalculation` |
| `rust/gravitea-core/src/lib.rs` | A2 | Add `mod merma;` declaration and `#[pymodule_export] use super::merma::calculate_merma;` |
| `backend/apps/acopio/serializers/__init__.py` | A4 | Add re-exports for new serializer classes |
| `backend/apps/acopio/views/__init__.py` | A5 | Add re-exports for `RomaneoViewSet`, `QualityAnalysisViewSet` |
| `backend/apps/acopio/urls.py` | A5 | Register `romaneos` route and nested `quality-analysis` route on the existing DRF router |
| `backend/apps/acopio/pagination.py` | A5 | Add `RomaneoPagination` class (or reuse `ReferenceDataPagination` with adjusted page_size) |
| `backend/database/sql/acopio_rls.sql` | A1 | Add RLS policies for `acopio_romaneo`, `acopio_qualityanalysis`, `acopio_mermacalculation` tables |
| `backend/tests/acopio/conftest.py` | A6 | Add romaneo fixtures: `romaneo_factory`, `quality_analysis_factory`, `merma_table_factory`, `tolerance_table_factory`, romaneo in various states |

---

## Key Code Patterns

### Pattern 1: TenantBoundModel Inheritance

All 3 new models inherit `TenantBoundModel`. Reference:
`backend/apps/core/models/mixins.py` (TenantBoundModel class).

```python
import uuid

from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class Romaneo(TenantBoundModel):
    """
    Grain reception document -- central transactional entity of the acopio operation.

    TENANT-SCOPED entity -- inherits TenantBoundModel.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="romaneos",
    )

    # ... fields ...

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_romaneo"
        ordering = ["-ts_entrada"]
```

Key points from `TenantBoundManager` (see
`backend/apps/core/managers/tenant_bound.py` lines 207-304):

- `get_queryset()` implements FAIL-CLOSED pattern: if `tenant_id` is None, raises
  `ValueError`. If `tenant_id` is not a valid UUID, returns `qs.none()`.
- Always filters by `tenant_id = get_current_tenant_id()`.
- `AllObjectsManager` provides unscoped access for system operations.

### Pattern 2: Immutability Enforcement (save() Override)

Reference: `backend/apps/inventario/models.py` lines 620-669
(`StockMovement.save()`).

The StockMovement pattern allows RESERVED -> COMMITTED/CANCELLED transitions while
blocking all other field changes. For Romaneo, adapt this pattern to:

**Romaneo immutability (CONFORME gate):**

```python
def save(self, *args: object, **kwargs: object) -> None:
    """
    Enforce 6-state linear state machine with immutability at CONFORME.

    - PENDIENTE and EN_PROCESO: all fields editable.
    - PESADO: weights editable, identity fields locked.
    - ANALIZADO: quality outcome fields editable.
    - CONFORME: IMMUTABLE. Only status transition to CERRADO allowed.
    - CERRADO: fully immutable (terminal state).
    """
    if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
        self.tenant_id = self.tenant.id

    if self.pk and Romaneo.all_objects.filter(pk=self.pk).exists():
        existing = Romaneo.all_objects.get(pk=self.pk)

        # Validate state transition (linear only)
        if existing.status != self.status:
            valid_transitions = {
                self.RomaneoStatus.PENDIENTE: self.RomaneoStatus.EN_PROCESO,
                self.RomaneoStatus.EN_PROCESO: self.RomaneoStatus.PESADO,
                self.RomaneoStatus.PESADO: self.RomaneoStatus.ANALIZADO,
                self.RomaneoStatus.ANALIZADO: self.RomaneoStatus.CONFORME,
                self.RomaneoStatus.CONFORME: self.RomaneoStatus.CERRADO,
            }
            expected_next = valid_transitions.get(existing.status)
            if expected_next is None or self.status != expected_next:
                raise ValueError(
                    f"Invalid state transition: {existing.status} -> {self.status}. "
                    f"Expected: {existing.status} -> {expected_next}."
                )

        # CERRADO: fully immutable terminal state -- no changes at all
        if existing.status == self.RomaneoStatus.CERRADO:
            for field in self._meta.get_fields():
                if hasattr(field, "attname"):
                    old_val = getattr(existing, field.attname, None)
                    new_val = getattr(self, field.attname, None)
                    if old_val != new_val:
                        raise ValueError(
                            f"Cannot modify field '{field.attname}' on romaneo "
                            f"in CERRADO status. CERRADO is the terminal state."
                        )

        # CONFORME immutability gate: only tare capture + status -> CERRADO
        if existing.status == self.RomaneoStatus.CONFORME:
            for field in self._meta.get_fields():
                if hasattr(field, "attname") and field.attname not in (
                    "status",
                    "tara_kg",
                    "peso_neto_bruto_kg",
                    "ts_tara",
                ):
                    old_val = getattr(existing, field.attname, None)
                    new_val = getattr(self, field.attname, None)
                    if old_val != new_val:
                        raise ValueError(
                            f"Cannot modify field '{field.attname}' on romaneo "
                            f"in CONFORME status. Only tare capture and "
                            f"transition to CERRADO are permitted."
                        )

    self._validate_tenant_references()
    super().save(*args, **kwargs)
```

**IMPORTANT**: At CONFORME, only `status`, `tara_kg`, `peso_neto_bruto_kg`, and
`ts_tara` are allowed to change (tare capture happens while CONFORME, before
transition to CERRADO). At CERRADO, absolutely nothing can change -- CERRADO
must be checked first (before CONFORME) so that its stricter guard takes
precedence.

**MermaCalculation full immutability:**

```python
def save(self, *args: object, **kwargs: object) -> None:
    """Enforce full immutability -- no updates allowed."""
    if self.pk and MermaCalculation.all_objects.filter(pk=self.pk).exists():
        raise ValueError(
            "MermaCalculation records are fully immutable. "
            "Cannot update or overwrite an existing record."
        )
    if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
        self.tenant_id = self.tenant.id
    self._validate_tenant_references()
    super().save(*args, **kwargs)

def delete(self, *args: object, **kwargs: object) -> None:
    """Prevent deletion of MermaCalculation records."""
    raise ValueError(
        "MermaCalculation records cannot be deleted. "
        "They are permanent audit records."
    )
```

### Pattern 3: State Machine Transition (6-State Linear)

```
PENDIENTE --> EN_PROCESO   : confirmarArriboCPE (ARCA WSCPE async)
EN_PROCESO --> PESADO      : peso_bruto captured
PESADO --> ANALIZADO       : QualityAnalysis completed
ANALIZADO --> CONFORME     : MermaCalculation completed + operator confirms
                             === IMMUTABILITY GATE ===
CONFORME --> CERRADO       : confirmarDescargaCPE + confirmacionDefinitivaCPEAutomotor (async x2)
```

Define as TextChoices on the model:

```python
class RomaneoStatus(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROCESO = "EN_PROCESO", "En Proceso"
    PESADO = "PESADO", "Pesado"
    ANALIZADO = "ANALIZADO", "Analizado"
    CONFORME = "CONFORME", "Conforme"
    CERRADO = "CERRADO", "Cerrado"

VALID_TRANSITIONS = {
    RomaneoStatus.PENDIENTE: RomaneoStatus.EN_PROCESO,
    RomaneoStatus.EN_PROCESO: RomaneoStatus.PESADO,
    RomaneoStatus.PESADO: RomaneoStatus.ANALIZADO,
    RomaneoStatus.ANALIZADO: RomaneoStatus.CONFORME,
    RomaneoStatus.CONFORME: RomaneoStatus.CERRADO,
    # CERRADO is terminal -- no outgoing transitions
}
```

### Pattern 4: OneToOneField Satellite Pattern

QualityAnalysis and MermaCalculation are one-to-one satellites of Romaneo. The
database enforces uniqueness automatically via the OneToOneField.

```python
class QualityAnalysis(TenantBoundModel):
    romaneo = models.OneToOneField(
        "Romaneo",
        on_delete=models.CASCADE,
        related_name="quality_analysis",
    )
    # ... quality parameter fields ...

class MermaCalculation(TenantBoundModel):
    romaneo = models.OneToOneField(
        "Romaneo",
        on_delete=models.CASCADE,
        related_name="merma_calculation",
    )
    # ... merma fields ...
```

Access from Romaneo: `romaneo_instance.quality_analysis`,
`romaneo_instance.merma_calculation`. Returns `DoesNotExist` if not yet created.

### Pattern 5: DRF Action Endpoints (State Transitions)

Reference pattern for action endpoints on ModelViewSet. Each state transition is
a `@action(detail=True, methods=["post"])` endpoint.

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status


class RomaneoViewSet(viewsets.ModelViewSet):
    # ... standard CRUD ...

    @action(detail=True, methods=["post"], url_path="confirmar-arribo")
    def confirmar_arribo(self, request, pk=None):
        """PENDIENTE -> EN_PROCESO. Returns 202 (async WSCPE)."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.PENDIENTE:
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": "Romaneo must be in PENDIENTE status.",
                    "current_status": romaneo.status,
                    "attempted_transition": "confirmar-arribo",
                },
                status=status.HTTP_409_CONFLICT,
            )
        romaneo.status = Romaneo.RomaneoStatus.EN_PROCESO
        romaneo.save()
        serializer = self.get_serializer(romaneo)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="peso-bruto")
    def peso_bruto(self, request, pk=None):
        """EN_PROCESO -> PESADO. Body: { "peso_bruto_kg": "28450.000" }."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.EN_PROCESO:
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": "Romaneo must be in EN_PROCESO status.",
                    "current_status": romaneo.status,
                    "attempted_transition": "peso-bruto",
                },
                status=status.HTTP_409_CONFLICT,
            )
        serializer = PesoBrutoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        romaneo.peso_bruto_kg = serializer.validated_data["peso_bruto_kg"]
        romaneo.ts_pesada_bruta = timezone.now()
        romaneo.status = Romaneo.RomaneoStatus.PESADO
        romaneo.save()
        return Response(
            RomaneoDetailSerializer(romaneo).data,
            status=status.HTTP_200_OK,
        )
```

### Pattern 6: Nested ViewSet (QualityAnalysis under Romaneo)

QualityAnalysis endpoints are nested under a specific romaneo.

```python
class QualityAnalysisViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Nested under /romaneos/{romaneo_pk}/quality-analysis/.
    POST   = create QA (guard: romaneo in EN_PROCESO or PESADO)
    GET    = retrieve QA
    PATCH  = update QA (guard: romaneo in ANALIZADO only)
    """
    serializer_class = QualityAnalysisSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        romaneo_pk = self.kwargs["romaneo_pk"]
        return QualityAnalysis.objects.filter(romaneo_id=romaneo_pk)

    def get_object(self):
        """QA is 1:1 -- retrieve the single instance."""
        romaneo_pk = self.kwargs["romaneo_pk"]
        return get_object_or_404(QualityAnalysis, romaneo_id=romaneo_pk)
```

URL registration (nested route in `urls.py`):

```python
# Option A: Manual nested path
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

### Pattern 7: Rust PyO3 Function with Serde

Reference: `rust/gravitea-core/src/compute.rs` (serde structs, `parse_decimal`,
`decimal_to_string`, `GraviteaError`).

```rust
// rust/gravitea-core/src/merma.rs

use pyo3::prelude::*;
use rust_decimal::prelude::*;
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};

use super::decimal_utils::{decimal_to_string, parse_decimal};
use super::errors::GraviteaError;

#[derive(Deserialize)]
struct MermaInput {
    peso_neto_bruto_kg: String,
    humedad_pct: String,
    hf_secado_pct: String,
    materias_extranas_pct: String,
    zarandeo_deduction_pct: String,
    manipuleo_fijo_pct: String,
    volatil_fijo_pct: String,
}

#[derive(Serialize)]
struct MermaOutput {
    zarandeo_pct: String,
    secado_pct: String,
    manipuleo_pct: String,
    volatil_pct: String,
    peso_post_zarandeo_kg: String,
    peso_post_secado_kg: String,
    peso_post_manipuleo_kg: String,
    peso_final_kg: String,
    total_merma_kg: String,
    total_factor_pct: String,
}

fn calculate_merma_internal(input_json: &str) -> Result<String, GraviteaError> {
    let input: MermaInput =
        serde_json::from_str(input_json).map_err(|e| GraviteaError::ComputeError {
            msg: format!("Invalid merma input JSON: {}", e),
        })?;

    let peso_neto_bruto = parse_decimal(&input.peso_neto_bruto_kg)?;
    let humedad = parse_decimal(&input.humedad_pct)?;
    let hf = parse_decimal(&input.hf_secado_pct)?;
    let zarandeo_pct = parse_decimal(&input.zarandeo_deduction_pct)?;
    let manipuleo_pct = parse_decimal(&input.manipuleo_fijo_pct)?;
    let volatil_pct = parse_decimal(&input.volatil_fijo_pct)?;

    // Validate inputs
    if peso_neto_bruto <= Decimal::ZERO {
        return Err(GraviteaError::InvalidInput(
            "peso_neto_bruto_kg must be positive.".to_string(),
        ));
    }
    // ... additional validation ...

    // Step 1: Zarandeo
    let peso_post_zarandeo = peso_neto_bruto * (dec!(1) - zarandeo_pct / dec!(100));

    // Step 2: Secado
    let secado_pct = if humedad > hf {
        (humedad - hf) / (dec!(100) - hf) * dec!(100)
    } else {
        Decimal::ZERO
    };
    let peso_post_secado = peso_post_zarandeo * (dec!(1) - secado_pct / dec!(100));

    // Step 3: Manipuleo (only if secado > 0)
    let effective_manipuleo = if secado_pct > Decimal::ZERO {
        manipuleo_pct
    } else {
        Decimal::ZERO
    };
    let peso_post_manipuleo = peso_post_secado * (dec!(1) - effective_manipuleo / dec!(100));

    // Step 4: Volatil (always applied)
    let peso_final = peso_post_manipuleo * (dec!(1) - volatil_pct / dec!(100));

    let total_merma = peso_neto_bruto - peso_final;
    let total_factor = peso_final / peso_neto_bruto;

    let output = MermaOutput {
        zarandeo_pct: decimal_to_string(&zarandeo_pct),
        secado_pct: decimal_to_string(&secado_pct),
        manipuleo_pct: decimal_to_string(&effective_manipuleo),
        volatil_pct: decimal_to_string(&volatil_pct),
        peso_post_zarandeo_kg: decimal_to_string(&peso_post_zarandeo),
        peso_post_secado_kg: decimal_to_string(&peso_post_secado),
        peso_post_manipuleo_kg: decimal_to_string(&peso_post_manipuleo),
        peso_final_kg: decimal_to_string(&peso_final),
        total_merma_kg: decimal_to_string(&total_merma),
        total_factor_pct: decimal_to_string(&total_factor),
    };

    serde_json::to_string(&output).map_err(|e| GraviteaError::ComputeError {
        msg: format!("JSON serialization error: {}", e),
    })
}

#[pyfunction]
pub fn calculate_merma(input_json: &str) -> PyResult<String> {
    Ok(calculate_merma_internal(input_json)?)
}
```

### Pattern 8: PyO3 Module Registration

Reference: `rust/gravitea-core/src/lib.rs` lines 21-61.

Add to `lib.rs`:

```rust
mod merma;  // Add after existing mod declarations

// Inside #[pymodule] mod gravitea_rust { ... }:
    #[pymodule_export]
    use super::merma::calculate_merma;
```

### Pattern 9: Python FFI Wrapper with Fallback

The merma service wraps the Rust call with `try/except ImportError` for a
pure-Python fallback when the Rust module is not available (CI, development
without Rust toolchain).

```python
"""
Merma calculation service -- Rust FFI wrapper with Python fallback.

Uses the Rust calculate_merma() function via PyO3 for production performance.
Falls back to a pure-Python implementation when the Rust module is unavailable.
"""

import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

logger = logging.getLogger(__name__)

try:
    from gravitea_rust import calculate_merma as _rust_calculate_merma

    _USE_RUST = True
    logger.info("Merma engine: using Rust implementation via PyO3.")
except ImportError:
    _USE_RUST = False
    logger.warning(
        "Merma engine: Rust module not available, using Python fallback. "
        "This is expected in development; ensure Rust is built for production."
    )


def _python_calculate_merma(input_data: dict[str, str]) -> dict[str, str]:
    """Pure-Python reference implementation of the sequential merma formula."""
    peso_neto_bruto = Decimal(input_data["peso_neto_bruto_kg"])
    humedad = Decimal(input_data["humedad_pct"])
    hf = Decimal(input_data["hf_secado_pct"])
    zarandeo_pct = Decimal(input_data["zarandeo_deduction_pct"])
    manipuleo_pct = Decimal(input_data["manipuleo_fijo_pct"])
    volatil_pct = Decimal(input_data["volatil_fijo_pct"])

    # Step 1: Zarandeo
    peso_post_zarandeo = peso_neto_bruto * (1 - zarandeo_pct / 100)

    # Step 2: Secado
    if humedad > hf:
        secado_pct = (humedad - hf) / (100 - hf) * 100
    else:
        secado_pct = Decimal("0")
    peso_post_secado = peso_post_zarandeo * (1 - secado_pct / 100)

    # Step 3: Manipuleo (only if secado > 0)
    effective_manipuleo = manipuleo_pct if secado_pct > 0 else Decimal("0")
    peso_post_manipuleo = peso_post_secado * (1 - effective_manipuleo / 100)

    # Step 4: Volatil (always)
    peso_final = peso_post_manipuleo * (1 - volatil_pct / 100)

    total_merma = peso_neto_bruto - peso_final
    total_factor = peso_final / peso_neto_bruto

    return {
        "zarandeo_pct": str(zarandeo_pct),
        "secado_pct": str(secado_pct),
        "manipuleo_pct": str(effective_manipuleo),
        "volatil_pct": str(volatil_pct),
        "peso_post_zarandeo_kg": str(peso_post_zarandeo),
        "peso_post_secado_kg": str(peso_post_secado),
        "peso_post_manipuleo_kg": str(peso_post_manipuleo),
        "peso_final_kg": str(peso_final),
        "total_merma_kg": str(total_merma),
        "total_factor_pct": str(total_factor),
    }


def calculate_merma_deductions(input_data: dict[str, str]) -> dict[str, str]:
    """
    Calculate sequential merma deductions.

    Uses Rust FFI when available, falls back to Python.
    Returns dict with all intermediate and final values.
    """
    if _USE_RUST:
        input_json = json.dumps(input_data)
        result_json = _rust_calculate_merma(input_json)
        return json.loads(result_json)
    return _python_calculate_merma(input_data)
```

### Pattern 10: Sequential Number Generation

Auto-generate `romaneo_number` per branch with format `ROM-YYYY-NNNNN`.

```python
from django.db.models import Max
from django.utils import timezone


def _generate_romaneo_number(branch_id: str) -> str:
    """Generate sequential romaneo number per branch."""
    year = timezone.now().year
    prefix = f"ROM-{year}-"

    # Get the max number for this branch and year
    last = (
        Romaneo.all_objects
        .filter(branch_id=branch_id, romaneo_number__startswith=prefix)
        .aggregate(max_num=Max("romaneo_number"))
    )

    last_number = last["max_num"]
    if last_number:
        # Extract sequence number and increment
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:05d}"
```

Call this in the model's `save()` on first save (when `romaneo_number` is not yet
set):

```python
def save(self, *args, **kwargs):
    if not self.romaneo_number:
        self.romaneo_number = _generate_romaneo_number(self.branch_id)
    # ... state machine validation ...
    super().save(*args, **kwargs)
```

### Pattern 11: Romaneo Pagination

Follow the existing `ReferenceDataPagination` pattern but with a smaller default
page size appropriate for transactional data.

```python
# In backend/apps/acopio/pagination.py (add to existing file)

class RomaneoPagination(PageNumberPagination):
    """
    Page-number pagination for romaneo list views.

    Smaller default page size than reference data because romaneo
    records are more numerous and frequently queried.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100
```

### Pattern 12: Test Fixtures (conftest.py Updates)

Reference: `backend/tests/acopio/conftest.py` (existing spec-10 fixtures).

Add these fixtures for spec-11:

```python
import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone


@pytest.fixture
def merma_table_factory(db):
    """Factory for creating MermaTable instances."""
    from apps.acopio.models import MermaTable

    def create_merma_table(grain_type, **kwargs):
        defaults = {
            "grain_type": grain_type,
            "materias_extranas_from_pct": Decimal("1.00"),
            "materias_extranas_to_pct": Decimal("2.00"),
            "zarandeo_deduction_pct": Decimal("1.00"),
            "valid_from": date(2020, 1, 1),
            "valid_to": None,
        }
        defaults.update(kwargs)
        return MermaTable.objects.create(**defaults)

    return create_merma_table


@pytest.fixture
def tolerance_table_factory(db):
    """Factory for creating ToleranceTable instances."""
    from apps.acopio.models import ToleranceTable

    def create_tolerance_table(grain_type, **kwargs):
        defaults = {
            "grain_type": grain_type,
            "parameter": "humedad",
            "grado_base": 1,
            "tolerance_pct": Decimal("14.00"),
            "valid_from": date(2020, 1, 1),
            "valid_to": None,
        }
        defaults.update(kwargs)
        return ToleranceTable.objects.create(**defaults)

    return create_tolerance_table


@pytest.fixture
def romaneo_factory(tenant_context, grain_type_factory, campana_factory, user_factory):
    """Factory for creating Romaneo instances in PENDIENTE status."""
    from apps.acopio.models import Romaneo
    from apps.core.models import Branch

    branch = Branch.objects.create(
        tenant=tenant_context,
        name="Planta Test",
        code="PT01",
    )
    grain_type = grain_type_factory()
    campana = campana_factory()
    default_operator = user_factory()

    def create_romaneo(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "grain_type": grain_type,
            "campaign": campana,
            "branch": branch,
            "ts_entrada": timezone.now(),
            "patente_chasis": "AB123CD",
            "driver_name": "Juan Perez",
            "driver_dni": "12345678",
            "cpe_numero": f"CPE-{uuid.uuid4().hex[:8]}",
            "producer_cuit": "20123456789",
            "origin_locality": "Pergamino, Buenos Aires",
            "operator_id": default_operator.id,
        }
        defaults.update(kwargs)
        return Romaneo.objects.create(**defaults)

    return create_romaneo


@pytest.fixture
def romaneo_en_proceso(romaneo_factory):
    """Create a romaneo and advance it to EN_PROCESO."""
    from apps.acopio.models import Romaneo

    romaneo = romaneo_factory()
    romaneo.status = Romaneo.RomaneoStatus.EN_PROCESO
    romaneo.save()
    return romaneo


@pytest.fixture
def romaneo_pesado(romaneo_en_proceso):
    """Create a romaneo and advance it to PESADO."""
    from apps.acopio.models import Romaneo

    romaneo = romaneo_en_proceso
    romaneo.peso_bruto_kg = Decimal("42450.000")
    romaneo.ts_pesada_bruta = timezone.now()
    romaneo.status = Romaneo.RomaneoStatus.PESADO
    romaneo.save()
    return romaneo
```

---

## Checkpoint Gates

### Gate 1: Models + Rust (after Wave 1)

A1 and A2 each run their portion:

**A1 checks (Models):**

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

**A2 checks (Rust):**

```bash
# 1. Verify Rust builds
cd /home/brunoghiberto/Documents/Projects/GraviTea/rust/gravitea-core && \
cargo build 2>&1 | tail -3

# 2. Verify Rust tests pass
cd /home/brunoghiberto/Documents/Projects/GraviTea/rust/gravitea-core && \
cargo test merma 2>&1 | tail -10

# 3. Verify PyO3 module loads (requires maturin develop)
cd /home/brunoghiberto/Documents/Projects/GraviTea && \
.venv/bin/python -c "from gravitea_rust import calculate_merma; print('Gate 1 (Rust FFI): PASS')"
```

**Pass criteria**: All model imports succeed. All 3 models inherit TenantBoundModel.
Migration applies cleanly. Rust builds without errors, tests pass, PyO3 function
is importable from Python.

### Gate 2: Service + Serializers (after Wave 2)

**A3 checks (Merma Service):**

```bash
# 1. Verify merma service imports
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
../.venv/bin/python -c "
from apps.acopio.services.merma_engine import calculate_merma_deductions
result = calculate_merma_deductions({
    'peso_neto_bruto_kg': '30000.000',
    'humedad_pct': '15.2',
    'hf_secado_pct': '13.5',
    'materias_extranas_pct': '1.8',
    'zarandeo_deduction_pct': '1.00',
    'manipuleo_fijo_pct': '0.10',
    'volatil_fijo_pct': '0.30',
})
print(f'peso_final_kg: {result[\"peso_final_kg\"]}')
print('Gate 2 (Merma Service): PASS')
"
```

**A4 checks (Serializers):**

```bash
# 1. Verify serializers are importable
cd /home/brunoghiberto/Documents/Projects/GraviTea/backend && \
DJANGO_SETTINGS_MODULE=gravitea.settings.development \
../.venv/bin/python -c "
import django; django.setup()
from apps.acopio.serializers.romaneo import (
    RomaneoSerializer,
    QualityAnalysisSerializer,
    MermaCalculationSerializer,
)
print(f'RomaneoSerializer fields: {list(RomaneoSerializer().fields.keys())[:5]}...')
print('Gate 2 (Serializers): PASS')
"
```

**Pass criteria**: Merma service returns valid results for a test vector.
All serializers import without errors.

### Gate 3: API Layer (after Wave 3)

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

**Pass criteria**: URL patterns resolve. Admin models are registered.

### Gate 4: Full Test Suite (after Wave 4)

```bash
# 1. Run all acopio tests
bash /home/brunoghiberto/Documents/Projects/GraviTea/scripts/run-tests-external.sh \
    -n spec11-verify tests/acopio/

# 2. Poll for completion
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.status

# 3. Read summary when status is PASSED or FAILED
cat /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.summary

# 4. If FAILED, debug specific failures
grep "FAILED" /home/brunoghiberto/Documents/Projects/GraviTea/Docs/Tests/spec11-verify.log
```

**Pass criteria**: `.status` file reads `PASSED`. Summary shows 0 failures,
0 errors. Minimum 40 tests collected. If FAILED, A6 fixes failures and re-runs.

---

## Testing Protocol

### CRITICAL: External Test Runner Only

**NEVER** run pytest directly inside Claude Code -- it consumes too many tokens
and can hang the session. **ALWAYS** use `scripts/run-tests-external.sh` for
test execution.

Reference: `scripts/run-tests-external.sh` (first 70 lines).

How the script works:
1. Launches pytest as an invisible background process via `setsid`/`nohup`.
2. The calling shell returns immediately.
3. Results are written to files in `Docs/Tests/`.
4. Check `.status` file for completion state (1 line: RUNNING/PASSED/FAILED/ERROR).
5. Read `.summary` file for test counts and coverage (~20 lines).
6. Only grep the `.log` file for specific failures if debugging is needed.

### Test Categories

| Category | File | What It Tests | Estimated Count |
|----------|------|---------------|----------------|
| Model unit tests | `test_romaneo_models.py` | Romaneo creation (31 fields), state machine (6 valid + 5 invalid transitions), immutability gate (CONFORME/CERRADO field changes blocked), romaneo number generation (per-branch sequential), timestamp recording | 12-15 |
| API integration | `test_romaneo_api.py` | 4 CRUD endpoints, 6 state transition actions, merma preview endpoint, pagination, tenant isolation (cross-tenant 404), error responses (409 for invalid transitions, immutable edits), 3 QA nested endpoints | 12-15 |
| Quality analysis | `test_quality_analysis.py` | QA creation (OneToOne constraint), all 9+ parameters at correct precision, update guard (only ANALIZADO), immutability after CONFORME | 5-7 |
| Merma correctness | `test_merma_calculation.py` | Sequential formula (trigo reference vector), soja dry case (Hi <= Hf), edge cases (all zero parameters), Hf vs humedad_base assertion (~168 kg error), immutability (no update/delete), tolerance table version pinning | 8-10 |
| Rust FFI | `test_merma_rust.py` | Rust-Python parity (10+ test vectors), error handling (invalid JSON, negative weights), boundary conditions | 5-8 |
| **Total** | | | **42-55** |

### Test Execution Commands

```bash
# Run all acopio tests (recommended)
bash scripts/run-tests-external.sh -n spec11 tests/acopio/

# Run only romaneo model tests
bash scripts/run-tests-external.sh -n spec11-models tests/acopio/test_romaneo_models.py

# Run only API tests
bash scripts/run-tests-external.sh -n spec11-api tests/acopio/test_romaneo_api.py

# Run only merma calculation tests
bash scripts/run-tests-external.sh -n spec11-merma tests/acopio/test_merma_calculation.py

# Run only Rust FFI tests
bash scripts/run-tests-external.sh -n spec11-rust tests/acopio/test_merma_rust.py

# Run with fail-fast (stop on first failure)
bash scripts/run-tests-external.sh -n spec11-fast --fail-fast tests/acopio/
```

### Test Output Location

All test output goes to `Docs/Tests/`:

| File | Contents | How to Read |
|------|----------|-------------|
| `Docs/Tests/spec11.status` | `RUNNING`, `PASSED`, `FAILED`, or `ERROR` | `cat` (1 line) |
| `Docs/Tests/spec11.summary` | Test counts, failures, coverage | `cat` (~20 lines) |
| `Docs/Tests/spec11.log` | Full pytest output | `grep "FAILED"` only |

---

## Done Criteria

### Acceptance Criteria Verification

| AC | Description | Verification Method | Agent |
|----|-------------|-------------------|-------|
| AC-011-001 | Romaneo model complete (31 fields, 7 groups) | Gate 1 check + `test_romaneo_models.py` | A1 |
| AC-011-002 | State machine enforced (6 valid, all invalid rejected) | `test_romaneo_models.py` state transition tests | A1, A6 |
| AC-011-003 | Immutability gate at CONFORME | `test_romaneo_models.py` + `test_romaneo_api.py` (HTTP 409) | A1, A5, A6 |
| AC-011-004 | QualityAnalysis 1:1 satellite (duplicate rejected) | `test_quality_analysis.py` | A1, A6 |
| AC-011-005 | MermaCalculation immutable and correct | `test_merma_calculation.py` | A1, A6 |
| AC-011-006 | Merma formula correctness (trigo, soja, edge cases) | `test_merma_calculation.py` with hand-calculated vectors | A2, A3, A6 |
| AC-011-007 | Rust-Python parity (10+ vectors, identical results) | `test_merma_rust.py` | A2, A3, A6 |
| AC-011-008 | Hf vs humedad_base correctness (~168 kg error documented) | `test_merma_calculation.py` dedicated test | A2, A3, A6 |
| AC-011-009 | Tenant isolation (cross-tenant 404) | `test_romaneo_api.py` multi-tenant tests | A5, A6 |
| AC-011-010 | All 14 API endpoints functional (correct status codes) | `test_romaneo_api.py` | A5, A6 |
| AC-011-011 | Romaneo number auto-generated (per-branch sequential) | `test_romaneo_models.py` | A1, A6 |
| AC-011-012 | State transition timestamps recorded | `test_romaneo_models.py` | A1, A6 |
| AC-011-013 | Tolerance table version pinned (no retroactive grade change) | `test_merma_calculation.py` | A3, A6 |
| AC-011-014 | Test suite passing (40+ tests, 90%+ coverage) | Gate 4 summary | A6 |

### Final Verification Command

```bash
bash /home/brunoghiberto/Documents/Projects/GraviTea/scripts/run-tests-external.sh \
    -n spec11-final tests/acopio/
```

### Minimum Counts

- Models: 3 (Romaneo, QualityAnalysis, MermaCalculation)
- Rust functions: 1 (calculate_merma)
- API endpoints: 14 (4 CRUD + 6 transitions + 1 preview + 3 QA)
- Tests: >= 40
- Test coverage: >= 90% on new code

---

## FR-to-Agent Traceability

Every functional requirement from `specs/011-romaneo-core/spec.md` maps to an
agent and wave:

| FR | Description | Agent | Wave | AC |
|----|-------------|-------|------|-----|
| FR-001 | Create romaneo (PENDIENTE, all fields) | A1, A5 | 1, 3 | AC-011-001 |
| FR-002 | Auto-generate romaneo_number per branch | A1 | 1 | AC-011-011 |
| FR-003 | 6-state linear lifecycle enforcement | A1, A5 | 1, 3 | AC-011-002 |
| FR-004 | Capture peso_bruto_kg with 3-decimal precision | A1, A5 | 1, 3 | AC-011-001 |
| FR-005 | Capture tara_kg, compute peso_neto_bruto_kg | A1, A5 | 1, 3 | AC-011-001 |
| FR-006 | QualityAnalysis 1:1 satellite (9+ parameters) | A1, A5 | 1, 3 | AC-011-004 |
| FR-007 | Sequential merma formula (CAC 10/86) | A2, A3 | 1, 2 | AC-011-006 |
| FR-008 | Use hf_secado_pct (NOT humedad_base_pct) | A2, A3 | 1, 2 | AC-011-008 |
| FR-009 | MermaCalculation immutable 1:1 record | A1 | 1 | AC-011-005 |
| FR-010 | Immutability after CONFORME | A1, A5 | 1, 3 | AC-011-003 |
| FR-011 | Non-persisting merma preview | A3, A5 | 2, 3 | AC-011-010 |
| FR-012 | Pin tolerance/merma table versions at ts_entrada | A3 | 2 | AC-011-013 |
| FR-013 | Grade assignment (GRADO/TOLERANCE systems) | A3, A5 | 2, 3 | AC-011-010 |
| FR-014 | Complete tenant isolation | A1 | 1 | AC-011-009 |
| FR-015 | High-performance merma engine (Rust + Python parity) | A2, A3 | 1, 2 | AC-011-007 |
| FR-016 | Timestamps for each state transition | A1 | 1 | AC-011-012 |
| FR-017 | Async acknowledgment for ARCA operations (202) | A5 | 3 | AC-011-010 |

---

## RAG Queries for Agents

Agents MUST run RAG queries before writing code that depends on domain-specific
values. Do NOT invent merma formulas or quality parameter values.

### A2 + A3 (Merma Engine) -- MUST run before writing calculation logic

```bash
# Query 1: Sequential merma formula and regulatory constants
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "merma zarandeo secado manipuleo volatil calculation formula sequential" -l 5

# Query 2: Secado formula using regulatory Hf
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "secado formula humidity regulatory final moisture hf" -l 5

# Query 3: Manipuleo conditional application rules
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "manipuleo applied only when secado drying occurs" -l 5
```

### A1 (Models) -- Optional, for field validation

```bash
# Romaneo document structure and fields
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo reception document structure fields groups" -l 5

# State machine transitions and immutability
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo state machine CONFORME immutable lifecycle" -l 5
```

### A5 (Views) -- Optional, for API endpoint validation

```bash
# Romaneo API endpoint design
.venv/bin/python scripts/qdrant/qdrant_search.py \
    -q "romaneo API endpoints state transition action" -l 5
```

---

## RLS Policies (A1 Deliverable)

A1 must update `backend/database/sql/acopio_rls.sql` to add RLS policies for
all 3 new tenant-scoped models. Reference pattern from the existing
`campanaconfig_tenant_isolation` policy in the same file.

```sql
-- ================================================================
-- RLS for Romaneo, QualityAnalysis, MermaCalculation
-- All 3 are TENANT-SCOPED (inherit TenantBoundModel)
-- ================================================================

-- Romaneo
ALTER TABLE acopio_romaneo ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_romaneo FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS romaneo_tenant_isolation ON acopio_romaneo;
CREATE POLICY romaneo_tenant_isolation ON acopio_romaneo
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY romaneo_tenant_isolation ON acopio_romaneo IS
'Ensures romaneos are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_romaneo TO gravitea_app;

-- QualityAnalysis
ALTER TABLE acopio_qualityanalysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_qualityanalysis FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS qualityanalysis_tenant_isolation ON acopio_qualityanalysis;
CREATE POLICY qualityanalysis_tenant_isolation ON acopio_qualityanalysis
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY qualityanalysis_tenant_isolation ON acopio_qualityanalysis IS
'Ensures quality analyses are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_qualityanalysis TO gravitea_app;

-- MermaCalculation
ALTER TABLE acopio_mermacalculation ENABLE ROW LEVEL SECURITY;
ALTER TABLE acopio_mermacalculation FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS mermacalculation_tenant_isolation ON acopio_mermacalculation;
CREATE POLICY mermacalculation_tenant_isolation ON acopio_mermacalculation
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

COMMENT ON POLICY mermacalculation_tenant_isolation ON acopio_mermacalculation IS
'Ensures merma calculations are only visible/modifiable within their tenant context.';

GRANT SELECT, INSERT, UPDATE, DELETE ON acopio_mermacalculation TO gravitea_app;
```

---

## Admin Registration (A1 Deliverable)

A1 must update `backend/apps/acopio/admin.py` to register the 3 new models.
Reference pattern from the existing admin registration in the same file.

```python
# Add to existing admin.py

@admin.register(Romaneo)
class RomaneoAdmin(admin.ModelAdmin):
    list_display = [
        "romaneo_number", "status", "grain_type", "branch",
        "patente_chasis", "ts_entrada", "peso_neto_conforme_kg",
    ]
    list_filter = ["status", "grain_type", "branch"]
    search_fields = ["romaneo_number", "cpe_numero", "patente_chasis", "driver_name"]
    readonly_fields = ["id", "romaneo_number"]


@admin.register(QualityAnalysis)
class QualityAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        "romaneo", "humedad_pct", "materias_extranas_pct",
        "analysis_timestamp",
    ]
    search_fields = ["romaneo__romaneo_number"]


@admin.register(MermaCalculation)
class MermaCalculationAdmin(admin.ModelAdmin):
    list_display = [
        "romaneo", "peso_neto_bruto_input_kg", "peso_final_kg",
        "total_merma_kg", "calculated_at",
    ]
    search_fields = ["romaneo__romaneo_number"]
    readonly_fields = [
        "id", "romaneo", "merma_table_version", "peso_neto_bruto_input_kg",
        "hi_input_pct", "hf_used_pct", "materias_extranas_input_pct",
        "zarandeo_pct", "secado_pct", "manipuleo_pct", "volatil_pct",
        "peso_post_zarandeo_kg", "peso_post_secado_kg", "peso_post_manipuleo_kg",
        "peso_final_kg", "total_merma_kg", "total_factor_pct",
        "calculated_at", "calculated_by",
    ]
```

---

## Composite Indexes (A1 Deliverable)

Per NF-011-009, add composite indexes to Romaneo Meta class for common query
patterns:

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

---

## WeighbridgeDevice and Future FK Strategy (A1 Decision)

Per the specification context (`11-specify.md`), two groups of fields reference
models not yet created:

1. **Group 4**: `weighbridge_device` FK to `WeighbridgeDevice` (future spec)
2. **Group 6**: `storage_unit` FK to `StorageUnit`, `grain_lot` FK to `GrainLot`
   (spec-12)

**Strategy**: Use nullable `CharField` placeholders for `weighbridge_device` and
omit `storage_unit`/`grain_lot` entirely. These FKs will be added by spec-12's
migration as `ALTER TABLE ADD COLUMN` operations. This avoids creating stub models
that would need to be replaced later.

Alternatively, if Django migration requires a concrete FK target, create minimal
stub models with a docstring indicating they are placeholders for future specs.

The A1 agent instruction file will specify the chosen strategy.

---

## Execution Notes

**Type**: Implementation -- multi-agent execution (A1-A6)

**Base class reference**: `backend/apps/core/models/mixins.py`
(`TenantBoundModel` -- auto-adds `tenant_id`, validates FK references).

**Immutability pattern reference**: `backend/apps/inventario/models.py` lines
620-669 (`StockMovement.save()`) -- field-by-field comparison using
`_meta.get_fields()` with an allowlist of mutable fields.

**Rust module pattern reference**: `rust/gravitea-core/src/compute.rs` -- serde
deserialization into typed structs, `parse_decimal()` and `decimal_to_string()`
from `decimal_utils`, `GraviteaError` for error propagation to Python.

**Error enum reference**: `rust/gravitea-core/src/errors.rs` -- `GraviteaError`
enum with `ComputeError { msg: String }` and `InvalidInput(String)` variants.
Both convert to Python exceptions via the `From<GraviteaError> for PyErr` impl.

**Test pattern reference**: `backend/tests/acopio/conftest.py` --
`grain_type_factory` (global model, uses `db` fixture),
`campana_factory` (tenant-scoped, uses `tenant_context` fixture).

**Writing persona**: Implementation agents should follow `django-expert` skill
for Django 5.2 patterns, `gravitea-tenant` skill for tenant isolation,
`gravitea-testing` skill for pytest conventions, and `gravitea-auth` skill for
JWT-authenticated API test patterns.

**RAG discipline**: Agents MUST run RAG queries before writing merma calculation
logic. Do NOT invent merma formulas or quality parameter values.

**Critical merma formula warning**: The secado formula uses
`Hf = GrainType.hf_secado_pct`, NOT `humedad_base_pct`. Using the wrong value
yields approximately 168 kg error per 30-tonne truck. Every test that calculates
merma must explicitly verify that `hf_secado_pct` (not `humedad_base_pct`) is used.
