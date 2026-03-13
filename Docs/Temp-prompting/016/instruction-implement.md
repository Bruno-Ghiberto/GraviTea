# Speckit Implement Context: Backend Modules Solidification

> **Phase**: IMPLEMENT (Django models, serializers, views, services, tests, migrations, RLS policies).
> **Version**: 1.0 (2026-02-24) — Machine-readable orchestration prompt for backend module implementation.
> **Feature**: `016-backend-modules-solidification`

---

## IMMEDIATE EXECUTION DIRECTIVE

**Upon reading this document, LEAD must act — not plan.**

**Execute this sequence NOW, without pausing for human approval between phases:**

1. **Create the team** (`TeamCreate` with name `016-backend-modules-solidification`)
2. **Execute Phase 1 yourself** (T001-T004) — create app skeletons, register in settings/urls
3. **Verify Phase 1 GATE** — project starts without errors (`python manage.py check`)
4. **Spawn COMPRAS-ENGINEER and REPORTES-ENGINEER in parallel** — each gets ALL their tasks upfront in the spawn prompt (no handshake). Both start working immediately after Phase 1.
5. **When COMPRAS-ENGINEER completes** (Phases 2-5, T005-T039) → verify GATE regressions passed
6. **When REPORTES-ENGINEER completes** (Phase 6, T040-T052) → verify GATE regression passed
7. **Execute Phase 7 yourself** (T053-T059) — permission enforcement on both modules
8. **Execute Phase 8 yourself** (T060-T064) — seed data for both modules
9. **Execute Phase 9 yourself** (T065-T071) — admin, final regression, coverage, RLS verification
10. **Report final results** to human → wait for commit approval

**Key principle**: Maximize agent autonomy. Each engineer gets its full workload upfront and works through phases sequentially on its own. LEAD monitors and intervenes only on CRITICAL errors.

**No worktree isolation** — all agents share the main filesystem. This works because COMPRAS-ENGINEER and REPORTES-ENGINEER write to completely non-overlapping files (different apps, different test dirs).

---

## Authoritative Documents

Read these documents for reference (do NOT block execution to study them — execute Phase 1 immediately, spawn agents, read as needed):

| Priority | Document | Path | Purpose |
|----------|----------|------|---------|
| 1 | Tasks (AUTHORITATIVE) | `specs/016-backend-modules-solidification/tasks.md` | 71 tasks, 9 phases, execution order — THIS IS THE TASK AUTHORITY |
| 2 | Plan | `specs/016-backend-modules-solidification/plan.md` | Architecture, constitution check, phase gates |
| 3 | Spec | `specs/016-backend-modules-solidification/spec.md` | 7 user stories, 34 FRs, 14 SCs |
| 4 | Data Model | `specs/016-backend-modules-solidification/data-model.md` | 3 ERDs, 7 entity definitions, state machine, field specs |
| 5 | Compras API | `specs/016-backend-modules-solidification/contracts/compras-api.yaml` | OpenAPI 3.0.3 — suppliers, POs, goods receipts |
| 6 | Reportes API | `specs/016-backend-modules-solidification/contracts/reportes-api.yaml` | OpenAPI 3.0.3 — definitions, saved reports, export jobs |
| 7 | Research | `specs/016-backend-modules-solidification/research.md` | 7 decisions (R-001 through R-007) |
| 8 | Quickstart | `specs/016-backend-modules-solidification/quickstart.md` | 8-phase execution guide with gates |

**`tasks.md` supersedes `plan.md`** for task IDs, counts, and execution order. When in doubt, follow `tasks.md`.

---

## Agent Team Architecture (2 Agents + LEAD)

### Agent Roster

| Agent | Model | subagent_type | Role Summary |
|-------|-------|---------------|-------------|
| **LEAD** | Opus 4.6 | orchestrator (main) | Shot caller. Executes Phase 1 setup, Phase 7 permissions, Phase 8 seed, Phase 9 polish. Manages phase gates. |
| **COMPRAS-ENGINEER** | Opus 4.6 | general-purpose | Builds entire compras module: Supplier migration (Phase 2), PO lifecycle (Phase 3), GoodsReceipt+stock (Phase 4), custom fields (Phase 5). 35 tasks. |
| **REPORTES-ENGINEER** | Sonnet 4.6 | general-purpose | Builds entire reportes module: models, serializers, views, services, URLs, tests (Phase 6). 13 tasks. |

### Why This Split

- **COMPRAS-ENGINEER gets Opus** because Phase 2 (SeparateDatabaseAndState migration) is the riskiest operation in the feature — requires deep Django migration internals understanding
- **REPORTES-ENGINEER gets Sonnet** because Phase 6 is straightforward CRUD (3 models, 3 serializers, 3 viewsets, 1 service) following existing patterns
- **LEAD handles cross-cutting phases** (permissions, seed, admin) that touch BOTH modules — avoids file ownership conflicts

### Spawning Schedule

| Phase | Active Agents | Notes |
|-------|---------------|-------|
| 1 (Setup) | LEAD only | Create app skeletons, register in settings — trivial |
| 2 (Supplier Migration) | COMPRAS-ENGINEER | RISKIEST phase — full regression after |
| 3 (PO Lifecycle) | COMPRAS-ENGINEER | Depends on Phase 2 |
| 4 (Goods Receipt) | COMPRAS-ENGINEER | Depends on Phase 3 |
| 5 (Custom Fields) | COMPRAS-ENGINEER | Depends on Phase 3 |
| 6 (Reportes) | REPORTES-ENGINEER | Parallel with Phases 2-5 |
| 7 (Permissions) | LEAD only | Needs both modules' ViewSets to exist |
| 8 (Seed Data) | LEAD only | Needs both modules' models to exist |
| 9 (Polish) | LEAD only | Final validation, admin, regression |

**Max concurrent agents**: 3 (LEAD + COMPRAS-ENGINEER + REPORTES-ENGINEER during Phases 2-6).

---

## Agent Spawn Prompts (LEAD: copy these EXACTLY)

Each agent has a dedicated instruction file in `Docs/Temp-prompting/016/`. The spawn prompt is a boot loader — the agent's first action reads its instruction file for the complete mission brief.

**CRITICAL**: Do NOT improvise spawn prompts. Do NOT embed long instructions in the prompt. The instruction files are the single source of truth per agent.

#### COMPRAS-ENGINEER

```
name: "COMPRAS-ENGINEER"
model: "opus"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```

Spawn prompt:

```
You are COMPRAS-ENGINEER on team 016-backend-modules-solidification.

STEP 1: Read your mission brief at Docs/Temp-prompting/016/agent-COMPRAS-ENGINEER.md
STEP 2: Read the tasks at specs/016-backend-modules-solidification/tasks.md
STEP 3: Read the data model at specs/016-backend-modules-solidification/data-model.md
STEP 4: Read the API contract at specs/016-backend-modules-solidification/contracts/compras-api.yaml
STEP 5: Execute ALL tasks T005-T039 from tasks.md (Phases 2-5)

Phase execution order (MUST be sequential between phases):
  Phase 2 (T005-T014): Supplier Migration — SeparateDatabaseAndState, FK update, test updates
  Phase 3 (T015-T024): PO Lifecycle — models, serializers, views, state machine, tests
  Phase 4 (T025-T035): Goods Receipt — models, service, views, stock integration, tests
  Phase 5 (T036-T039): Custom Fields — extend EntityType, apply mixin, tests

GATE after each phase: Run regression tests via:
  bash scripts/run-tests-external.sh "016-compras-phaseN" "backend/venv-wsl/bin/python -m pytest tests/ --tb=short -q"
Then read Docs/Tests/016-compras-phaseN.summary for results. If new failures, fix before next phase.

Phase 2 GATE is CRITICAL (riskiest migration). If any pre-existing test fails due to supplier move, fix it.

When all 4 phases complete, report: total tests written, any issues, any deviations from spec.
```

#### REPORTES-ENGINEER

```
name: "REPORTES-ENGINEER"
model: "sonnet"
subagent_type: "general-purpose"
mode: "bypassPermissions"
```

Spawn prompt:

```
You are REPORTES-ENGINEER on team 016-backend-modules-solidification.

STEP 1: Read your mission brief at Docs/Temp-prompting/016/agent-REPORTES-ENGINEER.md
STEP 2: Read the tasks at specs/016-backend-modules-solidification/tasks.md (Phase 6 only: T040-T052)
STEP 3: Read the data model at specs/016-backend-modules-solidification/data-model.md (REPORTES section)
STEP 4: Read the API contract at specs/016-backend-modules-solidification/contracts/reportes-api.yaml
STEP 5: Execute ALL tasks T040-T052 from tasks.md (Phase 6)

Build order (sequential within Phase 6):
  T040-T042: Models (ReportDefinition, SavedReport, ExportJob)
  T043: Migration
  T044: RLS policies
  T045: Serializers
  T046: ViewSets
  T047: ReportService (read-only QuerySets)
  T048: URL registration
  T049-T051: Tests (can run parallel — 3 different test files)
  T052: GATE regression

GATE: Run regression via:
  bash scripts/run-tests-external.sh "016-reportes" "backend/venv-wsl/bin/python -m pytest tests/reportes/ --tb=short -q"
Then read Docs/Tests/016-reportes.summary for results.

When complete, report: test count, any issues, any deviations from contract.
```

### Spawn Protocol Notes

- **No [READY] handshake** — tasks included in spawn prompt, agents start working immediately
- **No one-at-a-time assignment** — each engineer receives full multi-phase workload upfront
- **No worktree isolation** — agents share filesystem (non-overlapping writes)
- **bypassPermissions mode** — agents read/write freely without approval prompts
- If an agent acts outside its documented boundaries, send: `"BOUNDARY VIOLATION: Re-read your instruction file — you are not authorized to {action}"`

---

## Communication Protocol

### Message Flow

```
LEAD (human-facing)
    |
    +---> COMPRAS-ENGINEER (Phases 2-5: compras module)
    |        +- progress / GATE results / blockers ---> LEAD
    |
    +---> REPORTES-ENGINEER (Phase 6: reportes module)
             +- progress / GATE results / blockers ---> LEAD
```

### Communication Rules

1. **LEAD is the ONLY agent that communicates with the human**
2. **No agent-to-agent direct messaging** — all communication flows through LEAD
3. **COMPRAS-ENGINEER and REPORTES-ENGINEER never communicate directly** — they work on separate modules with zero file overlap
4. Agents report phase completion, GATE results, blockers, and issues to LEAD only

---

## File Ownership Rules (STRICT)

| Agent | May Write |
|-------|-----------|
| **LEAD** | Phase 1: `backend/apps/compras/__init__.py`, `apps.py`, empty `models.py`, `views.py`, `serializers.py`, `services.py`, `urls.py`, `admin.py`; `backend/apps/reportes/` (same skeleton files); `backend/gravitea/settings/base.py` (INSTALLED_APPS); `backend/gravitea/urls.py` (include). Phase 7: `backend/apps/auth/models.py` (VALID_ACTIONS), `backend/apps/compras/views.py` (permission classes), `backend/apps/reportes/views.py` (permission classes), `backend/apps/core/management/commands/seed_data.py` (role defs), `tests/compras/test_permissions.py`, `tests/reportes/test_permissions.py`. Phase 8: `backend/apps/compras/management/commands/seed_compras.py`, `backend/apps/reportes/management/commands/seed_reportes.py`, `backend/apps/core/management/commands/seed_all.py`, `tests/compras/test_seed_compras.py`, `tests/reportes/test_seed_reportes.py`. Phase 9: `backend/apps/compras/admin.py`, `backend/apps/reportes/admin.py`. |
| **COMPRAS-ENGINEER** | `backend/apps/compras/models.py`, `backend/apps/compras/serializers.py`, `backend/apps/compras/views.py`, `backend/apps/compras/services.py`, `backend/apps/compras/urls.py`, `backend/apps/compras/migrations/*`, `backend/apps/inventario/models.py` (Product.supplier FK), `backend/apps/inventario/migrations/*` (supplier state removal), `backend/apps/core/models/customization.py` (EntityType), `backend/database/sql/*` (compras RLS), `tests/compras/__init__.py`, `tests/compras/test_supplier_migration.py`, `tests/compras/test_purchase_order_crud.py`, `tests/compras/test_purchase_order_state_machine.py`, `tests/compras/test_goods_receipt.py`, `tests/compras/test_stock_integration.py`, `tests/compras/test_custom_fields.py`. Also: updating existing test imports in `tests/performance/`, `tests/inventario/`, `tests/integration/` for supplier migration. |
| **REPORTES-ENGINEER** | `backend/apps/reportes/models.py`, `backend/apps/reportes/serializers.py`, `backend/apps/reportes/views.py`, `backend/apps/reportes/services.py`, `backend/apps/reportes/urls.py`, `backend/apps/reportes/migrations/*`, `backend/database/sql/*` (reportes RLS only), `tests/reportes/__init__.py`, `tests/reportes/test_report_definition_crud.py`, `tests/reportes/test_saved_report.py`, `tests/reportes/test_export_job.py`. |

### Overlap Resolution

- **`backend/apps/compras/views.py`**: COMPRAS-ENGINEER writes it in Phases 2-4. LEAD adds permission classes in Phase 7 (after COMPRAS-ENGINEER is done).
- **`backend/apps/reportes/views.py`**: REPORTES-ENGINEER writes it in Phase 6. LEAD adds permission classes in Phase 7 (after REPORTES-ENGINEER is done).
- **`backend/apps/compras/admin.py`**: LEAD creates empty skeleton in Phase 1. LEAD fills it in Phase 9 (COMPRAS-ENGINEER never touches it).
- **`backend/apps/reportes/admin.py`**: Same pattern as compras admin.
- **`backend/database/sql/`**: COMPRAS-ENGINEER writes compras-specific RLS files. REPORTES-ENGINEER writes reportes-specific RLS files. Different files, no conflict.

**Violation of file ownership is a CRITICAL error.** LEAD must enforce this.

---

## Phase Execution Guide

### Phase 1: Setup (Tasks T001-T004) — LEAD

**Purpose**: Create both Django app skeletons and register them.

**LEAD actions**:
1. T001: Create `backend/apps/compras/` skeleton (empty Python files: `__init__.py`, `apps.py`, `models.py`, `views.py`, `serializers.py`, `services.py`, `urls.py`, `admin.py`)
2. T002: Create `backend/apps/reportes/` skeleton (same structure)
3. T003: Add `"apps.compras"` and `"apps.reportes"` to `INSTALLED_APPS` in `backend/gravitea/settings/base.py`
4. T004: Include `compras.urls` under `/api/v1/compras/` and `reportes.urls` under `/api/v1/reportes/` in `backend/gravitea/urls.py`

**GATE**: `python manage.py check` passes. Both apps recognized.

**Then immediately spawn both engineers.** Do NOT wait for human approval.

---

### Phases 2-5: COMPRAS Module (Tasks T005-T039) — COMPRAS-ENGINEER

**LEAD actions**: Spawn COMPRAS-ENGINEER with exact prompt above. Wait for completion.

**Phase 2 (T005-T014)**: Supplier Migration — **HIGHEST RISK**
- SeparateDatabaseAndState migration pattern
- `db_table = "inventario_supplier"` to avoid table rename
- Update Product FK, update all test imports
- Full regression GATE — 0 new failures from migration

**Phase 3 (T015-T024)**: PO Lifecycle
- PurchaseOrder + PurchaseOrderItem models with state machine
- Nested writable serializer (follow SaleOrder pattern from ventas)
- ViewSet with confirm/cancel actions
- GATE regression

**Phase 4 (T025-T035)**: Goods Receipt + Stock
- GoodsReceipt + GoodsReceiptLine models (immutable)
- GoodsReceiptService (validates, creates StockMovement(type=PURCHASE), updates PO state)
- Over-receipt rejection, partial/full receipt handling
- GATE regression

**Phase 5 (T036-T039)**: Custom Fields on PO
- Add PURCHASE_ORDER to EntityType choices
- Apply CustomFieldsMixin to PO serializer
- GATE regression

---

### Phase 6: REPORTES Module (Tasks T040-T052) — REPORTES-ENGINEER

**LEAD actions**: Spawn REPORTES-ENGINEER with exact prompt above (same time as COMPRAS-ENGINEER). Wait for completion.

- 3 models (ReportDefinition, SavedReport, ExportJob)
- Serializers, ViewSets (standard CRUD), ReportService (read-only QuerySets)
- URL registration, RLS policies, migration
- 15+ tests across 3 test files
- GATE regression

---

### Phase 7: Permissions (Tasks T053-T059) — LEAD

**Depends on**: COMPRAS-ENGINEER AND REPORTES-ENGINEER both complete.

**LEAD actions**:
1. T053: Add `"export"` to `VALID_ACTIONS` in `backend/apps/auth/models.py`
2. T054: Add permission enforcement to compras ViewSets (purchases.read/write/admin)
3. T055: Add permission enforcement to reportes ViewSets (reports.read/write, reports.export)
4. T056: Update seed role definitions in `seed_data.py` for purchases + reports permissions
5. T057: Write `tests/compras/test_permissions.py`
6. T058: Write `tests/reportes/test_permissions.py`
7. T059: GATE regression

---

### Phase 8: Seed Data (Tasks T060-T064) — LEAD

**Depends on**: Phase 7 complete.

**LEAD actions**:
1. T060: Create `seed_compras` management command (sample POs in various states, items, goods receipts)
2. T061: Create `seed_reportes` management command (sample ReportDefinitions)
3. T062: Update `seed_all` to chain `seed_compras` and `seed_reportes`
4. T063: Write seed command tests (idempotency, expected counts)
5. T064: GATE regression

---

### Phase 9: Polish & Final Validation (Tasks T065-T071) — LEAD

**Depends on**: All phases complete.

**LEAD actions**:
1. T065: Create `PurchaseOrderAdmin` (inline items) + `GoodsReceiptAdmin` (inline lines) in compras `admin.py`
2. T066: Create `ReportDefinitionAdmin`, `SavedReportAdmin`, `ExportJobAdmin` in reportes `admin.py`
3. T067: Full regression suite — 0 new failures
4. T068: Verify compras test count >= 60 and reportes test count >= 15
5. T069: Verify overall test coverage >= 78%
6. T070: Review all cross-module FK references
7. T071: Verify RLS policies active on all 7 new entity tables

**Human Gate**: Present final validation report to human. Wait for commit approval.

---

## Test Execution Protocol

**ALL test runs MUST use the external runner to save tokens.**

### Running Tests

```bash
# Full regression (after risky phases)
bash scripts/run-tests-external.sh "016-{name}" "backend/venv-wsl/bin/python -m pytest tests/ --tb=short -q"

# Module-scoped (after non-risky phases)
bash scripts/run-tests-external.sh "016-compras" "backend/venv-wsl/bin/python -m pytest tests/compras/ --tb=short -q"
bash scripts/run-tests-external.sh "016-reportes" "backend/venv-wsl/bin/python -m pytest tests/reportes/ --tb=short -q"

# Single test file (during development)
bash scripts/run-tests-external.sh "016-{name}" "backend/venv-wsl/bin/python -m pytest tests/compras/test_purchase_order_crud.py --tb=short -q"
```

### Reading Results

1. Read ONLY the `.summary` file: `Docs/Tests/016-{name}.summary`
2. If failures exist: `Grep "FAIL\|Error" Docs/Tests/016-{name}.log`
3. **NEVER read the full `.log` file** — grep for specific failures only

### GATE Regression Requirements

| Phase | Scope | Expectation |
|-------|-------|-------------|
| Phase 2 (Supplier Migration) | FULL suite (`tests/`) | 0 new failures. Pre-existing Docker failures OK. |
| Phase 3 (PO Lifecycle) | FULL suite (`tests/`) | 0 new failures. |
| Phase 4 (Goods Receipt) | Module (`tests/compras/`) | All compras tests pass. |
| Phase 5 (Custom Fields) | Module (`tests/compras/`) | All compras tests pass. |
| Phase 6 (Reportes) | Module (`tests/reportes/`) | 15+ tests, all pass. |
| Phase 7 (Permissions) | FULL suite (`tests/`) | 0 new failures. |
| Phase 8 (Seed Data) | FULL suite (`tests/`) | 0 new failures. |
| Phase 9 (Final) | FULL suite (`tests/`) + coverage | 0 new failures, >= 78% coverage. |

---

## Error & Blocker Protocol

When ANY agent encounters a problem:

```
1. Agent detects issue (migration fails, test breaks, model conflict)
        |
        v
2. Agent reports to LEAD with:
   - Problem summary (1-2 sentences)
   - File(s) involved
   - Severity: CRITICAL / HIGH / MEDIUM / LOW
        |
        v
3. LEAD evaluates:
   - CRITICAL: Pause ALL work. Present to human.
   - HIGH: Agent must fix before proceeding to next phase.
   - MEDIUM: Note for Phase 9. Continue current phase.
   - LOW: Note for Phase 9. Continue.
```

### Severity Classification

| Severity | Criteria | Action |
|----------|----------|--------|
| **CRITICAL** | Migration destroys data, breaks existing models, FK integrity lost | Halt ALL work. Fix immediately. |
| **HIGH** | GATE regression fails with new failures, model constraint violation | Fix before next phase. |
| **MEDIUM** | Test assertion needs adjustment, minor serializer field issue | Note for Phase 9 fix. |
| **LOW** | Admin cosmetics, seed data quantity adjustment | Note for Phase 9. |

---

## Human-in-the-Loop Protocol

| Event | LEAD Action | Blocks? |
|-------|------------|---------|
| Phase 1 complete | Print status | **NO** — spawn engineers immediately |
| COMPRAS-ENGINEER complete | Print GATE results, test count | **NO** — wait for REPORTES too |
| REPORTES-ENGINEER complete | Print GATE results, test count | **NO** — start Phase 7 |
| Phase 7 complete | Print permission test results | **NO** — continue to Phase 8 |
| Phase 8 complete | Print seed test results | **NO** — continue to Phase 9 |
| Phase 9 complete | Print final validation report | **YES** — wait for human commit approval |
| CRITICAL error | Print full error context | **YES** — wait for human decision |

---

## Skills to Invoke

Each agent should invoke these skills when working on relevant files:

| Agent | Skills |
|-------|--------|
| LEAD | `gravitea-auth` (Phase 7 permissions), `gravitea-testing` (all test writing), `django-expert` (models/views) |
| COMPRAS-ENGINEER | `gravitea-tenant` (TenantBoundModel), `gravitea-inventory` (StockMovement), `gravitea-testing`, `django-expert` |
| REPORTES-ENGINEER | `gravitea-tenant` (TenantBoundModel), `gravitea-testing`, `django-expert` |

---

## Existing Pattern References

Agents should study these existing implementations for pattern consistency:

| Pattern | Reference File | Used For |
|---------|---------------|----------|
| TenantBoundModel | `backend/apps/core/models/base.py` | All 7 new entities |
| Nested writable serializer | `backend/apps/ventas/serializers.py` (SaleOrderSerializer) | PurchaseOrderSerializer, GoodsReceiptSerializer |
| StockMovement creation | `backend/apps/inventario/services.py` (StockService) | GoodsReceiptService calls StockService |
| CustomFieldsMixin | `backend/apps/core/serializers.py` or `backend/apps/ventas/serializers.py` | PurchaseOrderSerializer |
| TextChoices enum | `backend/apps/inventario/models.py` (MovementType) | PurchaseOrderStatus, ReportType, OutputFormat |
| RLS policy | `backend/database/sql/` (existing policies) | 7 new compras + reportes tables |
| Cursor pagination | Any existing ViewSet | All new ViewSets |
| Seed command | `backend/apps/core/management/commands/seed_data.py` | seed_compras, seed_reportes |

---

## Execution Sequence for LEAD (DO THIS NOW)

1. **Create team** -> `TeamCreate(team_name: "016-backend-modules-solidification")`
2. **Create tracking tasks** -> One TaskCreate per major phase
3. **Execute Phase 1** (T001-T004) yourself — create skeletons, register apps, verify `manage.py check`
4. **Spawn COMPRAS-ENGINEER and REPORTES-ENGINEER in parallel** using exact spawn prompts above. Both run as foreground Task agents (you need results before Phase 7).
5. **When both engineers return** -> Print combined GATE results to human (non-blocking)
6. **Execute Phase 7** (T053-T059) — permissions on both modules
7. **Execute Phase 8** (T060-T064) — seed data for both modules
8. **Execute Phase 9** (T065-T071) — admin, final regression, coverage check
9. **Print final validation report** -> **WAIT for human approval** before committing

**DO NOT** re-read all authoritative documents before spawning. The agents have their own instruction files. Just execute Phase 1, spawn, and go.

---

## Known Gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| SeparateDatabaseAndState migration fails | Wrong operations list or missing dependency | Follow R-001 exactly. `state_operations` = CreateModel, `database_operations` = empty. |
| Product.supplier FK still points to inventario | State-only FK migration missing | T008 must create a state-only migration updating the FK target app label |
| Test imports break after supplier move | Tests import `apps.inventario.models.Supplier` | T012 must update ALL test imports to `apps.compras.models.Supplier` |
| GoodsReceiptService fails on StockMovement | Wrong StockService API or missing type | Use existing `MovementType.PURCHASE` (R-007). Study StockService interface first. |
| Custom fields validation fails | EntityType choice not in DB | T036 migration must add `purchase_order` to EntityType TextChoices |
| RLS policies not applied | SQL files not executed in bootstrap | Add new SQL files to `backend/database/sql/` following existing naming pattern |
| `manage.py check` fails after app registration | Circular import or wrong app_label | Ensure `apps.py` has correct `default_auto_field` and `name`/`label` |
| Existing test uses shared `APIClient` fixture | conftest shared client causes credential overwrites | Use separate `APIClient()` per tenant (lesson from 014) |
| Permission test: user still has access | ViewSet missing `permission_classes` | Phase 7 adds HasModulePermission to each ViewSet |
| CRLF line endings | Files on `/mnt/c/` (Windows filesystem) | Run `sed -i 's/\r$//' <file>` after writing to `/mnt/c/` paths |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 71 |
| LEAD tasks | 23 (Phases 1, 7, 8, 9) |
| COMPRAS-ENGINEER tasks | 35 (Phases 2-5) |
| REPORTES-ENGINEER tasks | 13 (Phase 6) |
| New entities | 7 (5 compras + 2... err 3 reportes) |
| New test files | 11 |
| Target: compras tests | >= 60 |
| Target: reportes tests | >= 15 |
| Target: coverage | >= 78% |
| Blocking human gates | 1 (final commit) + CRITICAL errors |
