---
spec: "010"
name: "Grain Reference Data"
type: Implementation
phase: Implement
created: 2026-03-19
depends_on: [spec-03, spec-09]
blocks: [spec-11, spec-12]
---

# Spec-10: Grain Reference Data -- Implementation Context

> **For**: Orchestrator managing 4-agent tmux session
> **Produces**: `backend/apps/acopio/` Django application with models, fixtures,
> management command, DRF API, and test suite
> **Spec type**: Implementation (multi-agent, wave execution)

---

## Orchestrator Protocol

The orchestrator manages a 4-agent team executing in a tmux multi-pane layout.
Responsibilities:

1. **Session setup** -- Create the tmux session with 4 panes before any agent starts.
2. **Agent spawning** -- Send each agent its instruction file path; agent reads the
   file and awaits the "BEGIN WAVE N" signal.
3. **Wave execution** -- Signal agents to begin their assigned wave. Only one wave
   runs at a time (except Wave 2, where A2 and A3 run in parallel).
4. **Checkpoint gates** -- After each wave, run the gate verification commands. If
   any gate fails, halt execution and direct the responsible agent to fix the issue
   before proceeding.
5. **Failure handling** -- If an agent reports FAIL on a gate check, the orchestrator
   reads the error output, identifies the root cause, and instructs the agent to fix
   and re-run the gate. Do not advance to the next wave until all gates pass.
6. **Final verification** -- After Wave 4, confirm all 12 acceptance criteria are
   satisfied and report the spec as complete.

---

## Agent Team

| Agent | Type | Model | Instruction File | Mission |
|-------|------|-------|-----------------|---------|
| A1 | python-expert | Sonnet 4.6 | `agents/A1-models.md` | Models, migration, RLS, app scaffolding, test conftest |
| A2 | backend-architect | Sonnet 4.6 | `agents/A2-api.md` | Serializers, viewsets, URLs, pagination, admin |
| A3 | python-expert | Sonnet 4.6 | `agents/A3-seed-data.md` | Fixtures, management command, fixture tests |
| A4 | quality-engineer | Sonnet 4.6 | `agents/A4-tests.md` | Full test suite, acceptance criteria verification |

---

## tmux Session Setup (MANDATORY)

Create the 4-pane tmux session before launching any agent.

```bash
# Create session
tmux new-session -d -s spec10 -n agents

# Split into 2x2 grid
tmux split-window -h -t spec10:agents
tmux split-window -v -t spec10:agents.0
tmux split-window -v -t spec10:agents.1

# Pane layout:
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

---

## Spawning Protocol

For each agent:

1. Send the agent its instruction file path:
   `Docs/PROMPTS/spec-10-grain-reference/agents/A{N}-{name}.md`
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
BEGIN WAVE {N} -- Spec-10 Grain Reference Data
Your instruction file: Docs/PROMPTS/spec-10-grain-reference/agents/A{N}-{name}.md
Read the file, execute all assigned tasks, then run gate checks and report results.
```

---

## Wave Execution

### Wave 1: Foundation (A1 only)

**Prerequisite**: None -- this is the first wave.
**Must complete before**: Wave 2 can begin.
**Agent**: A1 (Models & Migrations)

**Tasks**: T001, T002, T003, T004, T005, T006, T007, T008, T009, T010, T011, T012

**Deliverables in order**:

1. `backend/apps/acopio/__init__.py` (empty)
2. `backend/apps/acopio/apps.py` (AcopioConfig)
3. `backend/apps/acopio/models/__init__.py` (re-exports all 4 models)
4. `backend/apps/acopio/models/grain_type.py` (GrainType -- GLOBAL)
5. `backend/apps/acopio/models/campana_config.py` (CampanaConfig -- TenantBound)
6. `backend/apps/acopio/models/tolerance_table.py` (ToleranceTable -- GLOBAL)
7. `backend/apps/acopio/models/merma_table.py` (MermaTable -- GLOBAL)
8. `backend/apps/acopio/urls.py` (stub: empty `urlpatterns = []`)
9. Modify `backend/gravitea/settings/base.py` -- add `"apps.acopio"` to INSTALLED_APPS
10. Run `makemigrations gravitea_acopio` to generate `0001_initial.py`
11. `backend/database/sql/acopio_rls.sql` (RLS policy for CampanaConfig only)
12. `backend/tests/acopio/__init__.py` + `backend/tests/acopio/conftest.py` (factories)

**Completion signal**: A1 runs Gate 1 checks and reports PASS/FAIL.

**Checkpoint Gate 1 commands**:

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

---

### Wave 2: API + Seed Data (A2 + A3 -- Parallel)

**Prerequisite**: Wave 1 Gate 1 PASS.
**A2 and A3 run simultaneously** -- they have no mutual dependencies.

#### A2: API Layer

**Tasks**: T019, T020, T021, T022, T023, T025, T026, T027, T030, T031, T032, T034, T035, T036, T038

**Deliverables**:

1. `backend/apps/acopio/pagination.py` (ReferenceDataPagination)
2. `backend/apps/acopio/serializers/__init__.py` (re-exports)
3. `backend/apps/acopio/serializers/reference_data.py` (all 4 serializers)
4. `backend/apps/acopio/views/__init__.py` (re-exports)
5. `backend/apps/acopio/views/reference_data.py` (all 4 viewsets)
6. Replace `backend/apps/acopio/urls.py` stub with full router registration
7. `backend/apps/acopio/admin.py` (all 4 model admin classes)
8. Modify `backend/gravitea/urls.py` -- add acopio URL include

#### A3: Seed Data

**Tasks**: T013, T014, T015, T016, T017, T018

**Deliverables**:

1. `backend/apps/acopio/fixtures/grain_types.json`
2. `backend/apps/acopio/fixtures/tolerance_tables.json`
3. `backend/apps/acopio/fixtures/merma_tables.json`
4. `backend/apps/acopio/management/__init__.py` (empty)
5. `backend/apps/acopio/management/commands/__init__.py` (empty)
6. `backend/apps/acopio/management/commands/seed_grain_reference.py`

**A3 MUST run RAG queries before writing fixture data** -- see A3 instruction file.

**Completion signal**: Both A2 and A3 run Gate 2 checks and report PASS/FAIL.

**Checkpoint Gate 2 commands (A2 -- API)**:

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

**Checkpoint Gate 2 commands (A3 -- Seed Data)**:

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

**Pass criteria**: All A2 and A3 checks pass.

---

### Wave 3: Testing (A4 only)

**Prerequisite**: Wave 2 Gate 2 PASS (both A2 and A3 confirmed).
**Agent**: A4 (Tests)

**Tasks**: T024, T028, T029, T033, T037, T039, T040, T041, T042

**Deliverables**:

1. `backend/tests/acopio/test_models.py` (model unit tests -- T028, T039, T040)
2. `backend/tests/acopio/test_api.py` (API integration tests -- T024, T029, T033, T037)
3. `backend/tests/acopio/test_fixtures.py` (fixture and seed command tests -- from A3 T018)
4. Run full test suite via external runner (T041)
5. Verify all 12 acceptance criteria (T042)

NOTE: `backend/tests/acopio/__init__.py` and `backend/tests/acopio/conftest.py` were
already created by A1 in Wave 1 (T012). A4 should verify they exist and extend the
conftest if additional fixtures are needed for test scenarios.

**Completion signal**: A4 runs Gate 3 checks and reports PASS/FAIL.

**Checkpoint Gate 3 commands**:

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

---

### Wave 4: Final Verification (All Agents)

**Prerequisite**: Wave 3 Gate 3 PASS.

All agents verify the 12 acceptance criteria by reviewing Gate 3 test results and
running any additional spot checks. Each agent is responsible for the ACs relevant
to their deliverables:

| Agent | Acceptance Criteria |
|-------|-------------------|
| A1    | AC-10-001 (GrainType model), AC-10-003 (CampanaConfig), AC-10-012 (ARCA code uniqueness) |
| A2    | AC-10-006 (API endpoints), AC-10-007 (global no tenant filter), AC-10-008 (campaign isolation) |
| A3    | AC-10-002 (fixture loaded), AC-10-004 (tolerance versioning), AC-10-005 (merma bands), AC-10-009 (idempotency), AC-10-011 (Hf correctness) |
| A4    | AC-10-010 (test suite passing -- all tests green) |

**Gate 4 -- Final Acceptance**:

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

**CRITICAL**: NEVER run pytest directly inside Claude Code. ALWAYS use the external
runner script. Running pytest directly consumes too many tokens and can hang the
session.

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec10 tests/acopio/

# Check results
cat Docs/Tests/spec10.status     # PASSED | FAILED | RUNNING
cat Docs/Tests/spec10.summary    # ~20 lines
grep "FAILED" Docs/Tests/spec10.log  # Only if FAILED

# Run only model tests
bash scripts/run-tests-external.sh -n spec10-models -k "test_model" tests/acopio/

# Run only API tests
bash scripts/run-tests-external.sh -n spec10-api -k "test_api" tests/acopio/

# Run only fixture/seed tests
bash scripts/run-tests-external.sh -n spec10-fixtures -k "test_fixture" tests/acopio/

# Run with coverage
bash scripts/run-tests-external.sh -n spec10-coverage tests/acopio/
```

All Python commands MUST use `.venv/bin/python`, never system python.

---

## Files Summary

### Files to Create (28 new files)

#### A1: Models & Migrations (10 files)

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

#### A1: Test Infrastructure (2 files)

| File | Description |
|------|-------------|
| `backend/tests/acopio/__init__.py` | Empty package init |
| `backend/tests/acopio/conftest.py` | Acopio-specific fixtures (grain_type_factory, campana_factory, seed_grain_types) |

#### A2: API Layer (7 files)

| File | Description |
|------|-------------|
| `backend/apps/acopio/pagination.py` | `ReferenceDataPagination(PageNumberPagination)` |
| `backend/apps/acopio/serializers/__init__.py` | Re-export all serializer classes |
| `backend/apps/acopio/serializers/reference_data.py` | All 4 serializers |
| `backend/apps/acopio/views/__init__.py` | Re-export all viewset classes |
| `backend/apps/acopio/views/reference_data.py` | All 4 viewsets |
| `backend/apps/acopio/urls.py` | Full `DefaultRouter` registration (replaces A1 stub) |
| `backend/apps/acopio/admin.py` | Admin registration for all 4 models |

#### A3: Seed Data (6 files)

| File | Description |
|------|-------------|
| `backend/apps/acopio/fixtures/grain_types.json` | 7 primary grain types with ARCA codes and regulatory values |
| `backend/apps/acopio/fixtures/tolerance_tables.json` | Tolerance thresholds for 5 primary grains |
| `backend/apps/acopio/fixtures/merma_tables.json` | Zarandeo deduction bands for 5 primary grains |
| `backend/apps/acopio/management/__init__.py` | Empty package init |
| `backend/apps/acopio/management/commands/__init__.py` | Empty package init |
| `backend/apps/acopio/management/commands/seed_grain_reference.py` | Idempotent seed command with `--dry-run` |

#### A4: Tests (3 files)

| File | Description |
|------|-------------|
| `backend/tests/acopio/test_models.py` | Model unit tests: fields, constraints, validation, Hf correctness |
| `backend/tests/acopio/test_api.py` | API integration tests: endpoints, filtering, pagination, tenant isolation |
| `backend/tests/acopio/test_fixtures.py` | Fixture tests: seed command, idempotency, data correctness |

### Files to Modify (2 existing files)

| File | Agent | Change |
|------|-------|--------|
| `backend/gravitea/settings/base.py` | A1 | Add `"apps.acopio",` to INSTALLED_APPS after `"apps.reportes",` |
| `backend/gravitea/urls.py` | A2 | Add `path("acopio/", include("apps.acopio.urls")),` inside the `api/v1/` include block |

---

## FR-to-Agent Traceability

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

## Integration Points

- **Depends on**: spec-03 (Data Model blueprint -- entity definitions for GrainType,
  CampanaConfig, ToleranceTable, MermaTable), spec-09 (ARCA Knowledge Update --
  enriched grain species codes).
- **Blocks**: spec-11 (Romaneo Core -- needs GrainType for FK, ToleranceTable for
  quality grading, MermaTable for loss calculations), spec-12 (Storage & Position --
  needs GrainType for StorageUnit.current_grain_type and GrainLot.grain_type FKs).

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
