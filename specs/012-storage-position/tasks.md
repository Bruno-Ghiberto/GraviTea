# Tasks: Storage & Position

**Input**: Design documents from `/specs/012-storage-position/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included — mandated by Constitution Principle X (TDD), spec.md acceptance scenarios, and plan.md minimum counts (40+ tests, 90%+ coverage).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Tests are written per user story per TDD discipline — write tests first, verify they fail, then implement.

**Agents**: 3-agent tmux layout per `Docs/PROMPTS/spec-12-storage/12-plan.md`:
- **A1** (python-expert): Models, services, migration, RLS — Foundational + service tasks
- **A2** (backend-architect): Serializers, viewsets, URL registration — API tasks
- **A3** (quality-engineer): All test files — test tasks

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on each other)
- **[Story]**: Which user story this task belongs to (US1–US8)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add test fixtures that every user story's test phase depends on. Must exist before any test task in Phases 3–10.

- [x] T001 Add storage fixtures to `backend/tests/acopio/conftest.py`: `storage_unit_factory`, `grain_lot_factory`, `grain_movement_factory`, `romaneo_conforme` (romaneo in CONFORME status with `peso_neto_conforme_kg` set)

**Checkpoint**: conftest.py fixtures importable; existing spec-10/11 tests still pass.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The 3 new models + Romaneo FK additions + migration + RLS are prerequisites for **ALL** 8 user stories. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 [P] Create `StorageUnit` model (TenantBound, 3 unit types, UniqueConstraint on tenant+branch+name, Index on tenant+branch+is_active, derived `current_occupancy_kg` excluded from DB) in `backend/apps/acopio/models/storage_unit.py`
- [x] T003 [P] Create `GrainLot` model (TenantBound, composite UniqueConstraint on 6-field natural key, CheckConstraint total_kg >= 0, auto lot_code generation in save(), 2 indexes) in `backend/apps/acopio/models/grain_lot.py`
- [x] T004 [P] Create `GrainMovement` model (TenantBound, FULLY IMMUTABLE — save() raises ValueError for existing pk, delete() raises ValueError always, 5 movement types including ADJUSTMENT, no `updated_at`, 2 indexes) in `backend/apps/acopio/models/grain_movement.py`
- [x] T005 Add `storage_unit` (FK→StorageUnit, SET_NULL, null=True) and `grain_lot` (FK→GrainLot, SET_NULL, null=True) fields to Romaneo Group 6 in `backend/apps/acopio/models/romaneo.py`; also update CONFORME mutable-fields allowlist to include `grain_lot` and `storage_unit`
- [x] T006 [P] Update `backend/apps/acopio/models/__init__.py` to re-export `StorageUnit`, `GrainLot`, `GrainMovement`; update `backend/apps/acopio/admin.py` to register all 3 new models with appropriate `list_display`, `readonly_fields` (GrainMovement has `has_change_permission=False`, `has_delete_permission=False`)
- [x] T007 Generate migration `backend/apps/acopio/migrations/0003_storage_position.py` by running `python manage.py makemigrations`; verify it creates 3 tables then adds 2 columns to `acopio_romaneo`; run `migrate --check` to confirm clean state
- [x] T008 Append RLS policies for `acopio_storageunit`, `acopio_grainlot`, `acopio_grainmovement` to `backend/database/sql/acopio_rls.sql`; grant only `SELECT, INSERT` on `acopio_grainmovement` (no UPDATE/DELETE — immutable table)

**Checkpoint (Gate 1)**: Run Gate 1 commands from `Docs/PROMPTS/spec-12-storage/12-plan.md` — all 3 models importable, TenantBound, Romaneo FKs present, migration clean, services importable.

---

## Phase 3: User Story 1 — Plant Manager Registers Storage Infrastructure (Priority: P1) 🎯 MVP

**Goal**: Tenant admin can create, list, update, and soft-deactivate physical storage units (silos, celdas, bins). The list response includes derived `current_occupancy_kg` per unit (computed from GrainMovement ledger, not stored). Storage unit names are unique within tenant+branch. A unit with non-zero active stock cannot be deleted.

**Independent Test**: Create a `StorageUnit` via `POST /api/v1/acopio/storage-units/`, list it via `GET` and verify `current_occupancy_kg` is 0.000, attempt to create a duplicate name and verify HTTP 400, then PATCH `is_active=false` and verify the unit disappears from default list.

### Tests for User Story 1

- [x] T009 [P] [US1] Write `StorageUnit` model tests in `backend/tests/acopio/test_storage_models.py`: create with all fields; UniqueConstraint raises IntegrityError on duplicate name+branch+tenant; TenantBoundManager fail-closed; `current_occupancy_kg` annotation returns 0 for empty unit and correct sum after movements; deactivation guard (unit with total_kg > 0 cannot be deactivated) tested via service call

### Implementation for User Story 1

- [x] T010 [P] [US1] Create `StorageUnitSerializer` (fields: id, name, unit_type, unit_type_display, branch, branch_name, capacity_tonnes, current_grain_type, current_grain_type_code, is_active, environment_sensor_id, current_occupancy_kg read-only via annotation, capacity_utilisation_pct SerializerMethodField, created_at) in `backend/apps/acopio/serializers/storage.py`
- [x] T011 [US1] Create `StorageUnitViewSet` (ModelViewSet, annotated queryset with `Coalesce(Sum("grain_lots__movements__quantity_kg"), 0)`, `select_related("branch", "current_grain_type")`, filter by branch + is_active, pagination) in `backend/apps/acopio/views/storage.py`
- [x] T012 [US1] Register `storage-units` route in `backend/apps/acopio/urls.py`; update `backend/apps/acopio/serializers/__init__.py` and `backend/apps/acopio/views/__init__.py` with new exports
- [x] T013 [US1] Write `StorageUnit` API tests in `backend/tests/acopio/test_storage_api.py`: CRUD (4 endpoints + expected status codes); `current_occupancy_kg` in list response is 0 for new unit; duplicate name returns HTTP 400; soft-deactivate via PATCH; cross-tenant request returns HTTP 404 (tenant isolation); DELETE returns HTTP 405

**Checkpoint**: `StorageUnit` API fully functional. `GET /api/v1/acopio/storage-units/` returns list with occupancy. Gate 2 URL check resolves `storage-unit-list`.

---

## Phase 4: User Story 2 — Operator Assigns Grain to Silo After Reception (Priority: P1)

**Goal**: After a romaneo reaches CONFORME, the operator assigns a storage unit and the system automatically creates/reuses a `GrainLot` and records an immutable `DEPOSIT` movement. The romaneo record is updated with `storage_unit` and `grain_lot` FK references. A second CONFORME romaneo with the same grain/campaign/grade/silo combination reuses the existing lot and increments `total_kg`.

**Independent Test**: Confirm a romaneo to CONFORME with `storage_unit` assigned → verify `GrainLot` is created with `total_kg == peso_neto_conforme_kg` → confirm a second romaneo (same combination) → verify `total_kg` equals the sum of both; verify `GrainMovement` count is 2 and both are immutable (ValueError on update/delete); verify Romaneo.grain_lot FK is set.

### Tests for User Story 2

- [x] T014 [P] [US2] Write deposit flow tests in `backend/tests/acopio/test_grain_ledger.py`: `create_deposit_from_romaneo` creates GrainLot on first call; second call with same composite key reuses lot; `total_kg` equals sum of deposited weights; `GrainMovement` created with correct `movement_type=DEPOSIT`, `romaneo` FK, `quantity_kg`; Romaneo `grain_lot` FK updated; `GrainMovement.save()` raises ValueError for existing pk; `GrainMovement.delete()` raises ValueError

### Implementation for User Story 2

- [x] T015 [P] [US2] Add `GrainLotSerializer` (fields: id, lot_code, grain_type, grain_type_code, campaign, campaign_code, grado, storage_unit, storage_unit_name, total_kg, is_own_grain, created_at) and `GrainMovementSerializer` (all fields, movement_type_display, romaneo_number, created_by_name — all read-only except on create: movement_type, quantity_kg, reference_document, notes) to `backend/apps/acopio/serializers/storage.py`
- [x] T016 [US2] Create `backend/apps/acopio/services/storage.py` with `create_deposit_from_romaneo(romaneo, storage_unit, is_own_grain) -> tuple[GrainMovement, GrainLot]`: uses `select_for_update().get_or_create()` on composite key inside `transaction.atomic()`; updates `lot.total_kg`; sets `StorageUnit.current_grain_type` if NULL; sets `romaneo.grain_lot`; and `_generate_lot_code()` helper
- [x] T017 [US2] Add `GrainLotViewSet` (list + retrieve only — no create/update/delete) and `GrainMovementViewSet` (`http_method_names = ["get", "post", "head", "options"]`, create + list + retrieve only) to `backend/apps/acopio/views/storage.py`
- [x] T018 [US2] Register `grain-lots` router route and nested `grain-lots/<uuid:grain_lot_pk>/movements/` URL patterns in `backend/apps/acopio/urls.py`
- [x] T019 [US2] Update `backend/apps/acopio/serializers/romaneo.py`: add `storage_unit` UUID field as patchable; add `grain_lot` UUID field as read-only; update `RomaneoDetailSerializer` to include both FK references
- [x] T020 [US2] Update `RomaneoViewSet.confirmar_conforme` action in `backend/apps/acopio/views/romaneo.py`: validate `storage_unit` is set on romaneo (return HTTP 400 if not); after status save, call `create_deposit_from_romaneo(romaneo, storage_unit, is_own_grain=False)` — **Note**: `is_own_grain=False` (third-party custody) is the correct default for spec-12 acopio reception; own-grain flag configuration is deferred to spec-13 per FR-008
- [x] T021 [US2] Extend `backend/tests/acopio/test_storage_api.py` with: GrainLot list endpoint; GrainMovement list + create endpoints; HTTP 405 for PATCH/DELETE/PUT on movements; GrainLot creation via deposit (no direct POST); `confirmar-conforme` action creates deposit movement when `storage_unit` is set; HTTP 400 when `storage_unit` missing

**Checkpoint**: Full deposit flow end-to-end. CONFORME romaneo with storage_unit assigned → deposit recorded → lot balance correct. Immutability enforced at model + API levels.

---

## Phase 5: User Story 3 — System Suggests Optimal Silo for Incoming Grain (Priority: P2)

**Goal**: Operator can request a ranked list of compatible storage units for incoming grain. The system scores units by grain type match (+40), grade match (+20), campaign match (+10), excludes incompatible types and units with insufficient capacity. Operator can override; override reason is captured.

**Independent Test**: Call `POST /api/v1/acopio/storage-units/suggest/` with grain_type, campaign, grado, incoming_kg → verify response is a ranked list with compatible silos only → verify silos with incompatible grain type are absent → verify silos with insufficient capacity are absent.

### Tests for User Story 3

- [x] T022 [P] [US3] Write `CellSuggestionService` tests in `backend/tests/acopio/test_storage_services.py`: type match scores 40; grade match adds 20; campaign match adds 10; incompatible grain type excluded; insufficient capacity excluded; empty unit gets score 40; results sorted descending by score

### Implementation for User Story 3

- [x] T023 [US3] Add `suggest_cell(tenant_id, branch_id, grain_type_id, campaign_id, grado, incoming_kg) -> list[CellSuggestion]` and `CellSuggestion` dataclass to `backend/apps/acopio/services/storage.py`; scoring: 40 for type match (or empty), +20 for grade match, +10 for campaign match; exclude incompatible + insufficient capacity
- [x] T024 [US3] Add `@action(detail=False, methods=["post"], url_path="suggest")` to `StorageUnitViewSet` in `backend/apps/acopio/views/storage.py`; add `CellSuggestionRequestSerializer` and `CellSuggestionResponseSerializer` to `backend/apps/acopio/serializers/storage.py`
- [x] T025 [US3] Write suggest endpoint tests in `backend/tests/acopio/test_storage_api.py`: valid request returns ranked list; incompatible unit absent; insufficient capacity unit absent; empty units appear with score 40

**Checkpoint**: `POST /suggest/` returns correctly ranked compatible silos.

---

## Phase 6: User Story 4 — Operator Records Grain Dispatch (Priority: P2)

**Goal**: Dispatch operator records grain leaving a storage unit. A WITHDRAWAL movement is created with negative `quantity_kg`. The lot balance decreases accordingly. Dispatch is rejected if it would produce a negative lot balance. Movement is immutable after creation.

**Independent Test**: Create a GrainLot with 100,000 kg → dispatch 35,000 kg → verify `total_kg` is 65,000 → attempt to dispatch 70,000 kg → verify HTTP 409 with clear error message → verify neither movement was created on the failed attempt.

### Tests for User Story 4

- [x] T026 [P] [US4] Extend `backend/tests/acopio/test_grain_ledger.py` with withdrawal tests: successful withdrawal reduces `total_kg`; insufficient balance raises `ValueError` (and HTTP 409 at API); balance check is atomic with movement creation; `quantity_kg` stored as negative for WITHDRAWAL

### Implementation for User Story 4

- [x] T027 [US4] Add `create_withdrawal(grain_lot, quantity_kg, operator, reference_document, notes) -> GrainMovement` to `backend/apps/acopio/services/storage.py`; uses `select_for_update()` on lot; raises `ValueError` if `lot.total_kg < quantity_kg`; stores `quantity_kg` as negative; updates `lot.total_kg` in same transaction
- [x] T028 [US4] Wire dispatch via `GrainMovementViewSet.create()` — the viewset's `perform_create` delegates to service layer based on `movement_type`; add dispatch validation (if WITHDRAWAL, call `create_withdrawal` service); add `DispatchSerializer` to `backend/apps/acopio/serializers/storage.py` with `reference_document`, `notes` optional fields
- [x] T029 [US4] Write dispatch API tests in `backend/tests/acopio/test_storage_api.py`: POST movement with WITHDRAWAL type → 201; insufficient balance → 409; immutable after creation (405 on PATCH/DELETE)

**Checkpoint**: Dispatch flow working. Insufficient balance correctly rejected.

---

## Phase 7: User Story 5 — Manager Transfers Grain Between Silos (Priority: P2)

**Goal**: Plant manager transfers grain from one storage unit to another within the same branch. The operation creates paired TRANSFER_OUT + TRANSFER_IN movements atomically. If either side fails, both are rolled back. Deadlock is prevented by consistent PK-ordered locking.

**Independent Test**: Set up Silo A (50,000 kg) and Silo B (empty) → transfer 20,000 kg → verify Silo A `total_kg` is 30,000 and Silo B `total_kg` is 20,000 → verify 2 GrainMovement records created with matching timestamps → attempt transfer with insufficient source balance → verify neither movement is created (atomicity).

### Tests for User Story 5

- [x] T030 [P] [US5] Extend `backend/tests/acopio/test_grain_ledger.py` with transfer tests: transfer reduces source and increases destination by same amount; TRANSFER_OUT (negative) + TRANSFER_IN (positive) both created; transfer with insufficient source balance creates zero movements (atomicity); source == destination raises ValueError; deadlock-safe ordering (both PKs locked in ascending order)

### Implementation for User Story 5

- [x] T031 [US5] Add `transfer_grain(source_lot, destination_lot, quantity_kg, operator, notes) -> tuple[GrainMovement, GrainLot]` to `backend/apps/acopio/services/storage.py`; locks both lots in sorted PK order; creates TRANSFER_OUT then TRANSFER_IN in `transaction.atomic()`; updates both balances
- [x] T032 [US5] Add `POST /grain-lots/transfer/` endpoint as `@action(detail=False, methods=["post"], url_path="transfer")` on `GrainLotViewSet` in `backend/apps/acopio/views/storage.py`; add `TransferRequestSerializer` (source_lot_id, destination_lot_id, quantity_kg, notes) to `backend/apps/acopio/serializers/storage.py`; register the router — `DefaultRouter` auto-generates `/grain-lots/transfer/` from the action — in `backend/apps/acopio/urls.py`
- [x] T033 [US5] Write transfer API tests in `backend/tests/acopio/test_storage_api.py`: valid transfer → 200, both movements present; insufficient source → 409; source == destination → 400

**Checkpoint**: Atomic transfer working. Both movements created or both rolled back.

---

## Phase 8: User Story 6 — Manager Views Real-Time Stock Report (Priority: P2)

**Goal**: Plant manager requests a real-time stock report showing current stock per storage unit (with occupancy %), per grain type, per campaign, and total warehouse capacity utilisation. Report is computed from the GrainMovement ledger (no cache). Filterable by branch, grain type, campaign.

**Independent Test**: Record several deposits across 3 silos and 2 campaigns → call `GET /api/v1/acopio/storage-units/stock-report/?campaign={id}` → verify aggregated totals match the sum of deposit quantities → verify `utilisation_pct` is correct → record one more deposit and immediately re-fetch → verify the new quantity appears (real-time, no cache delay).

### Tests for User Story 6

- [x] T034 [P] [US6] Write `StockReportService` tests in `backend/tests/acopio/test_storage_services.py`: aggregation per storage unit is correct; aggregation per grain_type is correct; aggregation per campaign is correct; `utilisation_pct` calculation; filtering by branch + grain_type + campaign works; zero-capacity unit returns 0 utilisation_pct

### Implementation for User Story 6

- [x] T035 [US6] Add `generate_stock_report(tenant_id, branch_id, grain_type_id, campaign_id) -> dict` to `backend/apps/acopio/services/storage.py`; aggregates `GrainLot.total_kg` grouped by storage unit / grain type / campaign; computes utilisation_pct from capacity_tonnes × 1000
- [x] T036 [US6] Add `@action(detail=False, methods=["get"], url_path="stock-report")` to `StorageUnitViewSet` in `backend/apps/acopio/views/storage.py`; add `StockReportSerializer` to `backend/apps/acopio/serializers/storage.py`
- [x] T037 [US6] Write stock-report API tests in `backend/tests/acopio/test_storage_api.py`: correct totals; filter params respected; real-time (deposit + immediate re-fetch reflects change); tenant isolation (cross-tenant data absent)

**Checkpoint**: `GET /stock-report/` returns correct real-time aggregated stock.

---

## Phase 9: User Story 7 — Manager Performs Physical Inventory Reconciliation (Priority: P3)

**Goal**: Plant manager enters physical weight measurements per storage unit. The system computes variance against ledger balance, generates a reconciliation report, and creates ADJUSTMENT GrainMovement entries for each silo with a non-zero variance. Adjustment movements carry mandatory `notes`. A management command checks balance consistency across the entire tenant database and reports drift without auto-correcting.

**Independent Test**: Set GrainLot to 100,000 kg via deposit → submit reconciliation with measured_kg=98,500 → verify report shows −1,500 kg variance → verify ADJUSTMENT movement created with quantity_kg = −1,500 → verify lot `total_kg` is now 98,500 → attempt reconciliation with blank notes → verify HTTP 400.

### Tests for User Story 7

- [x] T038 [P] [US7] Write `ReconciliationService` tests in `backend/tests/acopio/test_storage_services.py`: deficit produces negative ADJUSTMENT and reduces total_kg; surplus produces positive ADJUSTMENT and increases total_kg; zero variance produces no movement; mandatory notes validation raises ValueError when blank; ADJUSTMENT movement has correct operator + notes

### Implementation for User Story 7

- [x] T039 [US7] Add `reconcile(tenant_id, measurements: list[dict], operator_id, notes) -> dict` to `backend/apps/acopio/services/storage.py`; computes ledger balance per storage unit from GrainLot aggregation; creates ADJUSTMENT movement for non-zero variances; `notes` is required (raises ValueError if blank)
- [x] T040 [US7] Add `POST /storage-units/reconcile/` endpoint as `@action` on `StorageUnitViewSet` in `backend/apps/acopio/views/storage.py`; add `ReconciliationRequestSerializer` (branch_id, notes, measurements list) to `backend/apps/acopio/serializers/storage.py`; register route in `backend/apps/acopio/urls.py`
- [x] T041 [US7] Create management command `backend/apps/acopio/management/commands/check_grain_balance.py` that iterates all GrainLots for a tenant, compares `total_kg` against `Sum(movements.quantity_kg)`, and reports any drift (does NOT auto-correct per NF-001)
- [x] T042 [US7] Write reconciliation API tests in `backend/tests/acopio/test_storage_api.py`: valid reconciliation → 200 with variance report; blank notes → 400; ADJUSTMENT movements immutable (405 on PATCH); cross-tenant data absent from variance report

**Checkpoint**: Reconciliation workflow functional. Adjustment movements correctly created and immutable.

---

## Phase 10: User Story 8 — Supervisor Closes a Campaign Year (Priority: P3)

**Goal**: Supervisor closes a completed campaign year. The system validates all romaneos in the campaign are in a final state (CONFORME or CERRADO), creates carry-forward GrainMovement entries (`TRANSFER_IN` to new campaign lots) for all non-zero grain lots, and marks the campaign as closed. Operation is atomic. Non-supervisors get HTTP 403. A campaign with incomplete romaneos is rejected with the list of offending romaneos.

**Independent Test**: Create campaign with all romaneos in CONFORME + 2 non-zero lots → close campaign → verify carry-forward movements created for both lots → verify source campaign's lots show 0 balance → verify new campaign lots have the carry amounts. Test rollback: add one romaneo in EN_PROCESO → close attempt rejected, no movements created.

### Tests for User Story 8

- [x] T043 [P] [US8] Write `CampaignCloseService` tests in `backend/tests/acopio/test_storage_services.py`: validation rejects if any romaneo not in final state (returns list of offenders); carry-forward creates TRANSFER_OUT (source) + TRANSFER_IN (target campaign lot) for each non-zero lot; zero-balance lots are skipped; operation is atomic (simulated error mid-close rolls back all movements); non-supervisor call raises `PermissionError`

### Implementation for User Story 8

- [x] T044 [US8] Add `CampaignCloseService` class + `close_campaign(tenant_id, campaign_id, target_campaign_id, supervisor_id) -> dict` to `backend/apps/acopio/services/storage.py`; validate all romaneos in CONFORME or CERRADO; for each non-zero lot: create TRANSFER_OUT (source) + get_or_create target lot + create TRANSFER_IN (target); mark `CampanaConfig.is_active=False` at end; entire operation in `transaction.atomic()`
- [x] T045 [US8] Add `POST /campaigns/{id}/close/` action to `CampanaConfigViewSet` in `backend/apps/acopio/views/reference_data.py` (or new `views/storage.py` action); check `IsSupervisorOrAdmin` permission; call `CampaignCloseService`; register route in `backend/apps/acopio/urls.py`
- [x] T046 [US8] Write campaign close API tests in `backend/tests/acopio/test_storage_api.py`: supervisor can close campaign with all-final romaneos (200); non-supervisor gets 403; incomplete romaneo returns 409 with offender list; carry-forward movements present in target campaign lots after close; rollback verified (incomplete romaneo = zero movements created)

**Checkpoint**: Campaign close workflow functional. Atomic rollback confirmed. Supervisor gate enforced.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, cross-story integration checks, and delivery of the complete test suite.

- [x] T047 [P] Run Gate 1 verification commands from `Docs/PROMPTS/spec-12-storage/12-plan.md` (models importable, TenantBound, Romaneo FKs, migration clean, services importable) and fix any failures
- [x] T048 [P] Run Gate 2 verification commands (serializers importable, URL routing resolves, Romaneo serializer has storage_unit, admin registered) and fix any failures
- [x] T049 Run full acopio test suite via `bash scripts/run-tests-external.sh -n spec12-final tests/acopio/`; read `Docs/Tests/spec12-final.status`; fix any failures; verify 40+ tests collected and 90%+ coverage on new code
- [x] T050 [P] Verify the `check_grain_balance` management command produces no drift report on a freshly populated test dataset (run manually from backend shell)

**Done**: `Docs/Tests/spec12-final.status` reads `PASSED`. 40+ tests. Zero failures. All acceptance criteria in `Docs/PROMPTS/spec-12-storage/12-plan.md` AC-012-001 through AC-012-015 verified.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — **BLOCKS** all user story phases
- **US1 Phase (Phase 3)**: Depends on Phase 2 — StorageUnit model must exist
- **US2 Phase (Phase 4)**: Depends on Phase 2 (GrainLot + GrainMovement models) + Phase 3 (serializers/__init__ must include StorageUnit)
- **US3–US6 Phases (5–8)**: Depend on Phase 4 (services/storage.py must exist; deposit service is the base)
- **US7 Phase (Phase 9)**: Depends on Phase 4 (GrainMovement ADJUSTMENT type must be in place)
- **US8 Phase (Phase 10)**: Depends on Phase 4 (GrainLot balance service; CampaignConfig FK)
- **Polish (Phase 11)**: Depends on all desired phases being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no story dependencies
- **US2 (P1)**: Can start after Phase 2 — depends on StorageUnit model (Phase 2) and StorageUnit URL existence (Phase 3 T012) for the Romaneo PATCH to set `storage_unit`
- **US3 (P2)**: Can start after Phase 4 (needs StorageUnit queryset pattern from US2)
- **US4 (P2)**: Can start after Phase 4 (needs `services/storage.py` base)
- **US5 (P2)**: Can start after Phase 4 (needs `services/storage.py` base + GrainLot selects)
- **US6 (P2)**: Can start after Phase 4 (reads GrainLot.total_kg aggregated)
- **US7 (P3)**: Can start after Phase 4 (needs ADJUSTMENT movement type + GrainLot service)
- **US8 (P3)**: Can start after Phase 4 (needs GrainLot/GrainMovement + CampaignConfig FK)

### Within Each User Story

1. Tests written FIRST (per TDD — verify they fail before implementation)
2. Models/service functions before API layer
3. Serializers before viewsets
4. Viewsets before URL registration
5. Story complete before moving to next priority

### Parallel Opportunities

- **T002, T003, T004** (Foundational): Different files — can run in parallel
- **T006** runs concurrently with T002–T004 if __init__.py and admin.py are created before models are finalized (or immediately after)
- **T009, T010** (US1 tests + serializer): Different files — can start in parallel
- **T014, T015** (US2 tests + serializer): Different files — can start in parallel
- **US3, US4, US5, US6** (Phases 5–8): All depend only on Phase 4 — can be worked in parallel by different developers
- **US7, US8** (Phases 9–10): Both depend only on Phase 4 — can run in parallel with each other

---

## Parallel Example: User Story 2 (Deposit from Romaneo)

```bash
# Launch in parallel (different files, both need Phase 2 to be complete):
Task T014: "Write deposit flow tests in backend/tests/acopio/test_grain_ledger.py"
Task T015: "Create GrainLotSerializer + GrainMovementSerializer in backend/apps/acopio/serializers/storage.py"

# Then sequentially:
Task T016: "Create services/storage.py with create_deposit_from_romaneo"
Task T017: "Create GrainLotViewSet + GrainMovementViewSet in views/storage.py"
Task T018: "Register grain-lots routes in urls.py"
Task T019: "Update serializers/romaneo.py"
Task T020: "Update RomaneoViewSet.confirmar_conforme in views/romaneo.py"
Task T021: "Extend test_storage_api.py with deposit flow API tests"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only — P1)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T008)
3. Complete Phase 3: US1 — StorageUnit Catalogue (T009–T013)
4. Complete Phase 4: US2 — Deposit from Romaneo (T014–T021)
5. **STOP and VALIDATE**: Run `bash scripts/run-tests-external.sh -n spec12-mvp tests/acopio/`
6. Gate 1 + Gate 2 checks pass → MVP delivered

**MVP delivers**: Physical silo catalogue, grain reception → silo assignment → deposit ledger. This is the operational core of the storage module.

### Incremental Delivery

1. MVP (US1 + US2) → Core grain reception complete
2. Add US3 (Cell Suggestion) → Operators get AI-assisted silo selection
3. Add US4 (Dispatch) + US5 (Transfer) → Stock outflows operational
4. Add US6 (Stock Report) → Management visibility into current holdings
5. Add US7 (Reconciliation) → Regulatory compliance (physical count)
6. Add US8 (Campaign Close) → Full agricultural year lifecycle

---

## Notes

- **[P]** tasks = different files, no blocking inter-dependencies
- **[Story]** label maps each task to its user story for traceability
- **TDD discipline**: Test tasks (T009, T014, T022, T026, T030, T034, T038, T043) must be written and verified to fail **before** implementing the corresponding service/view
- **Test runner**: ALWAYS use `bash scripts/run-tests-external.sh -n <name> tests/acopio/` — NEVER run pytest directly inside Claude Code
- **GrainMovement is immutable**: NEVER call `.update()` or `.delete()` on a GrainMovement queryset — it will raise ValueError
- **services/storage.py grows incrementally**: Created in T016 (US2), extended in T023 (US3), T027 (US4), T031 (US5), T035 (US6), T039 (US7), T044 (US8) — all in the same file
- **Romaneo immutability gate**: T005 must update the CONFORME mutable-fields allowlist or T020 (deposit service) will fail at runtime when setting `romaneo.grain_lot`
