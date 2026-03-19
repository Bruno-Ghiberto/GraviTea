---
spec: "011"
name: "Romaneo Core"
type: Implementation
phase: Implement
created: 2026-03-19
context_for: "/speckit.implement"
depends_on: [spec-10]
blocks: [spec-12, spec-13]
agents: [A1, A2, A3, A4, A5, A6]
---

# Spec-11: Romaneo Core -- Implementation Context

> **For**: Orchestrator managing 6-agent tmux session
> **Produces**: 3 Django models in `backend/apps/acopio/`, 1 Rust module in
> `rust/gravitea-core/src/merma.rs`, DRF serializers + viewsets, Python merma
> service with FFI wrapper, and full test suite
> **Spec type**: Implementation (multi-agent, wave execution)

---

## Orchestrator Protocol

The orchestrator manages a 6-agent team executing in a tmux multi-pane layout.
Responsibilities:

1. **Session setup** -- Create the tmux session with 6 panes before any agent starts.
2. **Agent spawning** -- Send each agent its instruction file path; agent reads the
   file and awaits the "BEGIN WAVE N" signal.
3. **Wave execution** -- Signal agents to begin their assigned wave. Waves 1 and 2
   have parallel execution within the wave. Waves 3 and 4 are sequential.
4. **Checkpoint gates** -- After each wave, run the gate verification commands. If
   any gate fails, halt execution and direct the responsible agent to fix the issue
   before proceeding.
5. **Failure handling** -- If an agent reports FAIL on a gate check, the orchestrator
   reads the error output, identifies the root cause, and instructs the agent to fix
   and re-run the gate. Do not advance to the next wave until all gates pass.
6. **Final verification** -- After Wave 4, confirm all 14 acceptance criteria are
   satisfied and report the spec as complete.

---

## Agent Team

| Agent | Role | Agent Type | Model | Instruction File |
|-------|------|------------|-------|-----------------|
| A1 | Models + Migration | python-expert | Sonnet 4.6 | `agents/A1-models.md` |
| A2 | Rust Merma Engine | general-purpose | Sonnet 4.6 | `agents/A2-rust.md` |
| A3 | Python Merma Service | python-expert | Sonnet 4.6 | `agents/A3-merma-service.md` |
| A4 | Serializers | python-expert | Sonnet 4.6 | `agents/A4-serializers.md` |
| A5 | Views + URLs | backend-architect | Sonnet 4.6 | `agents/A5-views.md` |
| A6 | Tests | quality-engineer | Sonnet 4.6 | `agents/A6-tests.md` |

---

## Wave Execution Order

### Wave 1: Foundation (A1 + A2 -- Parallel)

**Prerequisite**: None -- this is the first wave.
**Must complete before**: Wave 2 can begin.
**Agents**: A1 (Models + Migration) and A2 (Rust Merma Engine) run simultaneously.

**A1 deliverables** (Tasks T003-T009):

1. `backend/apps/acopio/models/romaneo.py` (Romaneo -- 31 fields, 6-state machine)
2. `backend/apps/acopio/models/quality_analysis.py` (QualityAnalysis -- 1:1 satellite)
3. `backend/apps/acopio/models/merma_calculation.py` (MermaCalculation -- immutable)
4. `backend/apps/acopio/models/__init__.py` update (re-export 3 new models)
5. `backend/apps/acopio/admin.py` update (register 3 new models)
6. `backend/apps/acopio/migrations/0002_romaneo_core.py` (auto-generated)
7. `backend/database/sql/acopio_rls.sql` update (RLS for 3 new tables)
8. `backend/apps/acopio/services/__init__.py` (empty package init -- T001)

**A2 deliverables** (Tasks T010-T013):

1. `rust/gravitea-core/src/merma.rs` (calculate_merma function, serde structs, tests)
2. `rust/gravitea-core/src/lib.rs` update (register merma module export)
3. Rust build + PyO3 module verification

**Completion signal**: A1 runs Gate 1 (Models) checks, A2 runs Gate 1 (Rust) checks.

---

### Wave 2: Service + Serializers (A3 + A4 -- Parallel)

**Prerequisite**: Wave 1 Gate 1 PASS (A1 models importable, A2 Rust builds).
**Agents**: A3 (Merma Service) and A4 (Serializers) run simultaneously.

**A3 deliverables** (Tasks T014, T031):

1. `backend/apps/acopio/services/merma_engine.py` (Rust FFI wrapper, Python fallback,
   MermaTable lookup, merma preview logic)

**A4 deliverables** (Tasks T015-T016, T020, T023, T026, T030):

1. `backend/apps/acopio/serializers/romaneo.py` (all romaneo serializers)
2. `backend/apps/acopio/serializers/__init__.py` update (re-export serializers)

**Completion signal**: A3 runs Gate 2 (Service) checks, A4 runs Gate 2 (Serializers) checks.

---

### Wave 3: API Layer (A5 -- Sequential)

**Prerequisite**: Wave 2 Gate 2 PASS (A3 service importable, A4 serializers importable).
**Agent**: A5 (Views + URLs)

**A5 deliverables** (Tasks T017-T019, T021-T022, T024-T025, T027-T029, T031-T035):

1. `backend/apps/acopio/views/romaneo.py` (RomaneoViewSet + QualityAnalysisViewSet)
2. `backend/apps/acopio/views/__init__.py` update (re-export new viewsets)
3. `backend/apps/acopio/urls.py` update (register romaneo routes + nested QA route)
4. `backend/apps/acopio/pagination.py` update (add RomaneoPagination)

**Completion signal**: A5 runs Gate 3 (API) checks.

---

### Wave 4: Tests (A6 -- Sequential)

**Prerequisite**: Wave 3 Gate 3 PASS (URL routing resolves).
**Agent**: A6 (Tests)

**A6 deliverables** (Tasks T036-T042):

1. `backend/tests/acopio/conftest.py` update (romaneo fixtures)
2. `backend/tests/acopio/test_romaneo_models.py` (model + state machine tests)
3. `backend/tests/acopio/test_quality_analysis.py` (QA tests)
4. `backend/tests/acopio/test_merma_calculation.py` (merma correctness tests)
5. `backend/tests/acopio/test_merma_rust.py` (Rust FFI parity tests)
6. `backend/tests/acopio/test_romaneo_api.py` (API integration tests)

**Completion signal**: A6 runs Gate 4 (Tests) checks.

---

### Wave 5: Final Verification (All Agents)

**Prerequisite**: Wave 4 Gate 4 PASS (all tests green).

All agents verify acceptance criteria and run polish tasks T043-T047.

| Agent | Verification Responsibility |
|-------|---------------------------|
| A1 | AC-011-001 (model), AC-011-002 (state machine), AC-011-003 (immutability), AC-011-011 (number gen) |
| A2 | AC-011-007 (Rust parity), AC-011-006 (formula correctness from Rust side) |
| A3 | AC-011-006 (formula correctness from service), AC-011-008 (Hf correctness), AC-011-013 (table pinning) |
| A4 | (implicit -- serializers verified by A6 tests) |
| A5 | AC-011-009 (tenant isolation), AC-011-010 (API endpoints), AC-011-012 (timestamps) |
| A6 | AC-011-014 (test suite: 40+ tests, 90%+ coverage) |

---

## Checkpoint Gates

### Gate 1: Models + Rust (after Wave 1)

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

---

### Gate 2: Service + Serializers (after Wave 2)

**A3 checks (Merma Service):**

```bash
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
print('Gate 2 (Serializers): PASS')
"
```

**Pass criteria**: Merma service returns valid results for a test vector.
All serializers import without errors.

---

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

---

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

**CRITICAL**: NEVER run pytest directly inside Claude Code. ALWAYS use the external
runner script. Running pytest directly consumes too many tokens and can hang the
session.

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec11 tests/acopio/

# Check results
cat Docs/Tests/spec11.status     # PASSED | FAILED | RUNNING
cat Docs/Tests/spec11.summary    # ~20 lines
grep "FAILED" Docs/Tests/spec11.log  # Only if FAILED

# Run only model tests
bash scripts/run-tests-external.sh -n spec11-models tests/acopio/test_romaneo_models.py

# Run only API tests
bash scripts/run-tests-external.sh -n spec11-api tests/acopio/test_romaneo_api.py

# Run only merma calculation tests
bash scripts/run-tests-external.sh -n spec11-merma tests/acopio/test_merma_calculation.py

# Run only Rust FFI tests
bash scripts/run-tests-external.sh -n spec11-rust tests/acopio/test_merma_rust.py

# Run with fail-fast
bash scripts/run-tests-external.sh -n spec11-fast --fail-fast tests/acopio/
```

All Python commands MUST use `.venv/bin/python`, never system python.

---

## tmux Session Setup (MANDATORY)

Create the 6-pane tmux session before launching any agent.

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

---

## Agent Spawning Protocol

For each agent:

1. Send the agent its instruction file path:
   `Docs/PROMPTS/spec-11-romaneo-core/agents/A{N}-{name}.md`
2. The agent reads the instruction file, which contains:
   - Context files to read first
   - Assigned tasks with IDs
   - Code patterns to follow
   - Gate check commands to run on completion
3. The agent awaits the orchestrator's "BEGIN WAVE N" signal.
4. On signal, the agent executes all tasks assigned to that wave.
5. On completion, the agent runs its gate checks and reports PASS/FAIL with output.

**Signal format** (orchestrator sends to agent pane):

```
BEGIN WAVE {N} -- Spec-11 Romaneo Core
Your instruction file: Docs/PROMPTS/spec-11-romaneo-core/agents/A{N}-{name}.md
Read the file, execute all assigned tasks, then run gate checks and report results.
```

---

## Done Criteria

Spec-11 is complete when ALL of the following are true:

1. All 3 models exist with correct fields, constraints, and inheritance patterns.
   Migration `0002_romaneo_core.py` applies without errors.
2. Romaneo state machine enforces all 6 valid transitions and rejects all invalid
   transitions. Immutability gate at CONFORME prevents field changes.
3. QualityAnalysis 1:1 satellite enforces uniqueness. MermaCalculation is fully
   immutable (no update, no delete).
4. Rust `calculate_merma()` builds, passes 10+ unit tests, and is importable from
   Python via PyO3.
5. Python merma service wraps Rust FFI with fallback, includes MermaTable lookup
   logic, and returns correct results for test vectors.
6. All serializers import cleanly with correct field lists and validation.
7. All 14 API endpoints return correct responses with correct HTTP status codes.
8. Tenant isolation verified -- cross-tenant access returns 404.
9. Test suite passes with 40+ tests and 90%+ coverage for new code.
10. Acceptance criteria AC-011-001 through AC-011-014 all verified as PASS.
11. RLS policies for all 3 new tables exist in `database/sql/acopio_rls.sql`.
12. Composite indexes on Romaneo table exist for query performance.

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

## Files Summary

### Files to Create (14 new files)

| File | Agent | Description |
|------|-------|-------------|
| `backend/apps/acopio/services/__init__.py` | A1 | Empty package init |
| `backend/apps/acopio/models/romaneo.py` | A1 | Romaneo model (31 fields, state machine, immutability) |
| `backend/apps/acopio/models/quality_analysis.py` | A1 | QualityAnalysis (1:1 satellite, 9+ parameters) |
| `backend/apps/acopio/models/merma_calculation.py` | A1 | MermaCalculation (1:1 immutable, full audit trail) |
| `backend/apps/acopio/migrations/0002_romaneo_core.py` | A1 | Auto-generated migration |
| `rust/gravitea-core/src/merma.rs` | A2 | Rust merma engine with PyO3 bindings |
| `backend/apps/acopio/services/merma_engine.py` | A3 | Rust FFI wrapper + Python fallback |
| `backend/apps/acopio/serializers/romaneo.py` | A4 | All romaneo serializers |
| `backend/apps/acopio/views/romaneo.py` | A5 | RomaneoViewSet + QualityAnalysisViewSet |
| `backend/tests/acopio/test_romaneo_models.py` | A6 | Model + state machine tests |
| `backend/tests/acopio/test_quality_analysis.py` | A6 | QA tests |
| `backend/tests/acopio/test_merma_calculation.py` | A6 | Merma correctness tests |
| `backend/tests/acopio/test_merma_rust.py` | A6 | Rust FFI parity tests |
| `backend/tests/acopio/test_romaneo_api.py` | A6 | API integration tests |

### Files to Modify (9 existing files)

| File | Agent | Change |
|------|-------|--------|
| `backend/apps/acopio/models/__init__.py` | A1 | Add re-exports for Romaneo, QualityAnalysis, MermaCalculation |
| `backend/apps/acopio/admin.py` | A1 | Add admin registration for 3 new models |
| `backend/database/sql/acopio_rls.sql` | A1 | Add RLS policies for 3 new tables |
| `rust/gravitea-core/src/lib.rs` | A2 | Add `mod merma;` and `#[pymodule_export]` |
| `backend/apps/acopio/serializers/__init__.py` | A4 | Add re-exports for new serializers |
| `backend/apps/acopio/views/__init__.py` | A5 | Add re-exports for new viewsets |
| `backend/apps/acopio/urls.py` | A5 | Register romaneo routes + nested QA route |
| `backend/apps/acopio/pagination.py` | A5 | Add RomaneoPagination class |
| `backend/tests/acopio/conftest.py` | A6 | Add romaneo fixtures |

---

## FR-to-Agent Traceability

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
