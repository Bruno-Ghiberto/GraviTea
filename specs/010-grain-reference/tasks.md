# Tasks: Grain Reference Data

**Input**: Design documents from `/specs/010-grain-reference/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/api.md, research.md, quickstart.md

**Tests**: Included — spec requires 90% coverage and 20+ tests (AC-10-010, NF-010-005).

**Organization**: Tasks grouped by user story. US5 (seed data) placed first because US1, US3, US4 depend on reference data being loaded.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US5)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (App Scaffolding)

**Purpose**: Create the `backend/apps/acopio/` Django application structure and register it.

- [x] T001 Create `backend/apps/acopio/__init__.py` (empty package init)
- [x] T002 Create `backend/apps/acopio/apps.py` with `AcopioConfig` (name="apps.acopio", label="gravitea_acopio", verbose_name="Acopio")
- [x] T003 Create stub `backend/apps/acopio/urls.py` with empty `urlpatterns = []`
- [x] T004 Add `"apps.acopio"` to INSTALLED_APPS in `backend/gravitea/settings/base.py` after `"apps.reportes"`

**Checkpoint**: `cd backend && ../.venv/bin/python manage.py check` passes with acopio app registered.

---

## Phase 2: Foundational (Models & Migration)

**Purpose**: Create all 4 models and the database migration. MUST complete before any user story.

- [x] T005 Create `backend/apps/acopio/models/__init__.py` with re-exports for GrainType, CampanaConfig, ToleranceTable, MermaTable
- [x] T006 [P] Create GrainType model (GLOBAL, inherits models.Model) in `backend/apps/acopio/models/grain_type.py` with fields: id (UUID PK), code (CharField max_length=5 unique), arca_codigo (PositiveSmallIntegerField unique), name (CharField 100), humedad_base_pct (Decimal 5,2), hf_secado_pct (Decimal 5,2), manipuleo_fijo_pct (Decimal 5,2), volatil_fijo_pct (Decimal 5,2), grading_system (CharField choices GRADO/TOLERANCE), is_active (BooleanField default True). Explicit `objects = models.Manager()`. Meta: db_table="acopio_graintype", ordering=["code"], UniqueConstraints on code and arca_codigo.
- [x] T007 [P] Create CampanaConfig model (TENANT-SCOPED, inherits TenantBoundModel) in `backend/apps/acopio/models/campana_config.py` with fields: id (UUID PK), tenant (FK Tenant PROTECT), campaign_code (CharField 7), start_date (DateField), end_date (DateField), is_active (BooleanField default False), notes (TextField null). Explicit `objects = TenantBoundManager()` and `all_objects = AllObjectsManager()`. Meta: db_table="acopio_campanaconfig", ordering=["-start_date"], UniqueConstraint on (tenant, campaign_code) and partial UniqueConstraint on (tenant, is_active) where is_active=True. Include clean() validator for campaign_code regex, consecutive years, and end_date > start_date. Include wslpg_code property.
- [x] T008 [P] Create ToleranceTable model (GLOBAL) in `backend/apps/acopio/models/tolerance_table.py` with fields: id (UUID PK), grain_type (FK GrainType PROTECT), valid_from (DateField), valid_to (DateField null), parameter (CharField 50), tolerance_pct (Decimal 5,2), grado_base (IntegerField), source_resolution (CharField 100 null). Meta: db_table="acopio_tolerancetable", composite indexes on (grain_type_id, valid_to) and (grain_type_id, parameter, grado_base, valid_to).
- [x] T009 [P] Create MermaTable model (GLOBAL) in `backend/apps/acopio/models/merma_table.py` with fields: id (UUID PK), grain_type (FK GrainType PROTECT), valid_from (DateField), valid_to (DateField null), materias_extranas_from_pct (Decimal 5,2), materias_extranas_to_pct (Decimal 5,2 null), zarandeo_deduction_pct (Decimal 5,2). Meta: db_table="acopio_mermatable", composite indexes on (grain_type_id, valid_to) and (grain_type_id, materias_extranas_from_pct, valid_to).
- [x] T010 Run `cd backend && ../.venv/bin/python manage.py makemigrations gravitea_acopio` to generate `backend/apps/acopio/migrations/0001_initial.py`
- [x] T011 Create RLS policy for CampanaConfig in `backend/database/sql/acopio_rls.sql` — enable RLS, create tenant isolation policy using get_current_tenant_id(), grant permissions to gravitea_app role. Do NOT create RLS for GrainType, ToleranceTable, or MermaTable (global tables per ADR-010).
- [x] T012 Create `backend/tests/acopio/__init__.py` (empty) and `backend/tests/acopio/conftest.py` with grain_type_factory, campana_factory, and seed_grain_types fixtures

**Checkpoint (Gate 1)**: All 4 models importable, migration created, CampanaConfig inherits TenantBoundModel, GrainType does NOT inherit TenantBoundModel.

---

## Phase 3: User Story 5 - Initialize Reference Data (Priority: P1) MVP

**Goal**: Load all official grain reference data from authoritative sources in a single idempotent operation with preview mode.

**Independent Test**: Run seed operation on empty system, verify counts, run again and confirm no duplicates.

**IMPORTANT**: Run RAG queries BEFORE writing fixtures to get authoritative regulatory values. Do NOT invent values.

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain types codes ARCA humidity base" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "tolerance tables bonification rebaja" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "merma calculation formula sequential" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "grain quality parameters humidity moisture" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "ARCA grain commodity codes grain type nomenclature" -l 5
```

### Implementation for User Story 5

- [x] T013 [P] [US5] Create grain type fixture in `backend/apps/acopio/fixtures/grain_types.json` with 7 primary grains (TRI/15, MAI/19, SOJ/23, GIR/2, SOR/22, CEB_F/11, CEB_C/17) including all regulatory parameters (humedad_base_pct, hf_secado_pct, manipuleo_fijo_pct, volatil_fijo_pct, grading_system). CRITICAL: Soja hf_secado_pct=12.50 NOT 13.50.
- [x] T014 [P] [US5] Create tolerance table fixture in `backend/apps/acopio/fixtures/tolerance_tables.json` with tolerance entries for 5 primary grains (trigo, maiz, soja, girasol, sorgo) covering humedad, materias_extranas, peso_hectolitrico parameters per grade level. All valid_from=2020-01-01, valid_to=null.
- [x] T015 [P] [US5] Create merma table fixture in `backend/apps/acopio/fixtures/merma_tables.json` with zarandeo deduction bands for 5 primary grains (progressive ranges: 0-1%=0%, 1-2%=1%, 2-3%=2%, 3%+=3%). All valid_from=2020-01-01, valid_to=null.
- [x] T016 [US5] Create `backend/apps/acopio/management/__init__.py` and `backend/apps/acopio/management/commands/__init__.py` (empty inits)
- [x] T017 [US5] Create management command in `backend/apps/acopio/management/commands/seed_grain_reference.py` that loads grain_types, tolerance_tables, and merma_tables idempotently using update_or_create. Support --dry-run flag. Log each created/updated/skipped record. Key on: code (GrainType), (grain_type+parameter+grado_base+valid_from) (ToleranceTable), (grain_type+materias_extranas_from_pct+valid_from) (MermaTable).

### Tests for User Story 5

- [x] T018 [P] [US5] Write fixture and seed command tests in `backend/tests/acopio/test_fixtures.py`: test_seed_creates_grain_types (count >= 7), test_seed_idempotency (run twice, same count), test_seed_dry_run (no writes), test_soja_hf_correctness (hf=12.50 not 13.50), test_tolerance_entries_exist (>0 per grain), test_merma_bands_no_gaps

**Checkpoint (Gate 2 - Seed)**: `manage.py seed_grain_reference` loads data, Soja Hf=12.50, dry-run works.

---

## Phase 4: User Story 1 - Browse Official Grain Types (Priority: P1)

**Goal**: Authenticated users can browse the complete grain type catalog with ARCA codes and regulatory parameters.

**Independent Test**: GET /api/v1/acopio/grain-types/ returns 7+ grain types with correct data after seed.

### Implementation for User Story 1

- [x] T019 [US1] Create `ReferenceDataPagination(PageNumberPagination)` class in `backend/apps/acopio/pagination.py` with page_size=100, max_page_size=500. REQUIRED because the project default is `StandardCursorPagination` which orders by `created_at` — global models (GrainType, ToleranceTable, MermaTable) have no `created_at` field and cursor pagination would fail. All 4 acopio viewsets must set `pagination_class = ReferenceDataPagination`. CampanaConfig viewsets also use this to match the API contract (count/next/previous envelope per FR-015).
- [x] T020 [P] [US1] Create GrainTypeSerializer in `backend/apps/acopio/serializers/reference_data.py` with field mappings: codigo->arca_codigo, nombre->name. Expose: id, code, codigo, nombre, humedad_base_pct, hf_secado_pct, manipuleo_fijo_pct, volatil_fijo_pct, grading_system, is_active. All read-only.
- [x] T021 [US1] Create GrainTypeViewSet (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` with IsAuthenticated permission, standard Manager queryset (GLOBAL, no tenant filtering), is_active query parameter filter, pagination_class=ReferenceDataPagination. Add select_related() if needed.
- [x] T022 [US1] Create `backend/apps/acopio/serializers/__init__.py` and `backend/apps/acopio/views/__init__.py` with re-exports
- [x] T023 [US1] Update `backend/apps/acopio/urls.py` with DefaultRouter registering grain-types endpoint. Add `path("acopio/", include("apps.acopio.urls"))` to `backend/gravitea/urls.py` inside api/v1/ block.

### Tests for User Story 1

- [x] T024 [P] [US1] Write API tests in `backend/tests/acopio/test_api.py`: test_grain_types_list (returns paginated envelope with count/next/previous), test_grain_types_detail (single grain), test_grain_types_filter_active, test_grain_types_requires_auth (401 without token), test_grain_types_same_for_all_tenants (GLOBAL)

**Checkpoint**: GET /api/v1/acopio/grain-types/ returns 7 grains with correct ARCA codes in paginated envelope.

---

## Phase 5: User Story 2 - Manage Campaign Years (Priority: P1)

**Goal**: Administrators can create, activate, and deactivate campaign years per organization with complete tenant isolation.

**Independent Test**: Create campaign for tenant A, verify tenant B cannot see it. Activate one, try activating another — fails.

### Implementation for User Story 2

- [x] T025 [US2] Create CampanaConfigSerializer in `backend/apps/acopio/serializers/reference_data.py` with all model fields. Tenant-scoped.
- [x] T026 [US2] Create CampanaConfigViewSet (ModelViewSet) in `backend/apps/acopio/views/reference_data.py` with IsAuthenticated permission, TenantBoundManager queryset, is_active query parameter filter, pagination_class=ReferenceDataPagination, perform_create setting tenant_id from request.user.
- [x] T027 [US2] Register campaigns endpoint in `backend/apps/acopio/urls.py` router.

### Tests for User Story 2

- [x] T028 [P] [US2] Write model tests in `backend/tests/acopio/test_models.py`: test_campana_creation, test_campana_code_format_validation (regex), test_campana_consecutive_years_validation, test_campana_date_range_validation (end > start), test_campana_one_active_per_tenant (IntegrityError on second active), test_wslpg_code_conversion ("2025/26" -> "2526"), test_campana_tenant_isolation
- [x] T029 [P] [US2] Write API tests in `backend/tests/acopio/test_api.py`: test_campaigns_list_tenant_scoped, test_campaigns_create, test_campaigns_cross_tenant_isolation (other_tenant_client returns empty), test_campaigns_requires_auth

**Checkpoint**: Full CRUD on campaigns with tenant isolation verified.

---

## Phase 6: User Story 3 - Look Up Tolerance Thresholds (Priority: P2)

**Goal**: Users can look up quality tolerance thresholds per grain type with temporal versioning support.

**Independent Test**: GET /api/v1/acopio/tolerance-tables/?grain_type={uuid} returns entries for the given grain.

### Implementation for User Story 3

- [x] T030 [US3] Create ToleranceTableSerializer in `backend/apps/acopio/serializers/reference_data.py`
- [x] T031 [US3] Create ToleranceTableViewSet (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` with IsAuthenticated, standard Manager (GLOBAL), grain_type and valid_from_before query parameter filters, pagination_class=ReferenceDataPagination. Use select_related("grain_type").
- [x] T032 [US3] Register tolerance-tables endpoint in `backend/apps/acopio/urls.py` router.

### Tests for User Story 3

- [x] T033 [P] [US3] Write API tests in `backend/tests/acopio/test_api.py`: test_tolerance_tables_list, test_tolerance_tables_filter_by_grain_type, test_tolerance_tables_same_for_all_tenants (GLOBAL)

**Checkpoint**: GET /api/v1/acopio/tolerance-tables/ returns filtered tolerance data.

---

## Phase 7: User Story 4 - Look Up Merma Deduction Bands (Priority: P2)

**Goal**: Users can look up zarandeo deduction bands per grain type with progressive ranges.

**Independent Test**: GET /api/v1/acopio/merma-tables/?grain_type={uuid} returns progressive bands without gaps.

### Implementation for User Story 4

- [x] T034 [US4] Create MermaTableSerializer in `backend/apps/acopio/serializers/reference_data.py`
- [x] T035 [US4] Create MermaTableViewSet (ReadOnlyModelViewSet) in `backend/apps/acopio/views/reference_data.py` with IsAuthenticated, standard Manager (GLOBAL), grain_type query parameter filter, pagination_class=ReferenceDataPagination. Use select_related("grain_type").
- [x] T036 [US4] Register merma-tables endpoint in `backend/apps/acopio/urls.py` router.

### Tests for User Story 4

- [x] T037 [P] [US4] Write API tests in `backend/tests/acopio/test_api.py`: test_merma_tables_list, test_merma_tables_filter_by_grain_type, test_merma_tables_same_for_all_tenants (GLOBAL)

**Checkpoint**: GET /api/v1/acopio/merma-tables/ returns filtered merma bands.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Admin interfaces, model-level tests, full integration verification.

- [x] T038 [P] Create admin registration in `backend/apps/acopio/admin.py` for all 4 models with list_display, list_filter, search_fields per FR-017
- [x] T039 [P] Write GrainType model unit tests in `backend/tests/acopio/test_models.py`: test_grain_type_creation, test_grain_type_unique_code, test_grain_type_unique_arca_codigo (IntegrityError), test_hf_not_equal_humedad_base (for all grains where they differ), test_grain_type_str_repr
- [x] T040 Write ToleranceTable and MermaTable model tests in `backend/tests/acopio/test_models.py`: test_tolerance_versioning (valid_to null = active), test_merma_bands_ordering
- [x] T041 Run full test suite via external runner: `bash scripts/run-tests-external.sh -n spec10-final --no-cov tests/acopio/` then `bash scripts/run-tests-external.sh -n spec10-coverage tests/acopio/` — verify PASSED status, 20+ tests, 0 failures, coverage >= 90% (check TOTAL line in summary)
- [x] T042 Run Gate 4 acceptance verification: confirm all 12 acceptance criteria (AC-10-001 through AC-10-012) pass per plan checkpoint gates

**Checkpoint (Final)**: All tests pass, all 12 ACs verified, coverage >= 90%.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US5 - Seed Data (Phase 3)**: Depends on Phase 2 — BLOCKS US1, US3, US4 (they need loaded data for testing)
- **US1 - Grain Types API (Phase 4)**: Depends on Phase 2 + Phase 3 seed data
- **US2 - Campaigns API (Phase 5)**: Depends on Phase 2 only (campaigns are tenant-created, no seed data needed)
- **US3 - Tolerances API (Phase 6)**: Depends on Phase 2 + Phase 3 seed data
- **US4 - Merma API (Phase 7)**: Depends on Phase 2 + Phase 3 seed data
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

- **US5 (Seed Data)**: First to implement — prerequisite for US1/US3/US4 testing
- **US2 (Campaigns)**: Independent of other stories (no seed data needed)
- **US1 (Grain Types)**: Depends on US5 for test data
- **US3 (Tolerances)**: Depends on US5 for test data
- **US4 (Merma)**: Depends on US5 for test data

### Within Each User Story

- Serializers before ViewSets (ViewSets reference serializers)
- ViewSets before URL registration (URLs reference ViewSets)
- Implementation before tests (tests need working endpoints)

### Parallel Opportunities

**Phase 2**: T006, T007, T008, T009 can all run in parallel (separate model files)
**Phase 3**: T013, T014, T015 can all run in parallel (separate fixture files)
**After Phase 3**: US1 (Phase 4), US2 (Phase 5) can run in parallel
**After Phase 3**: US3 (Phase 6), US4 (Phase 7) can run in parallel
**Phase 8**: T037, T038 can run in parallel (separate files)

---

## Parallel Example: Foundational Phase

```bash
# Launch all 4 models in parallel (different files):
T006: "Create GrainType model in backend/apps/acopio/models/grain_type.py"
T007: "Create CampanaConfig model in backend/apps/acopio/models/campana_config.py"
T008: "Create ToleranceTable model in backend/apps/acopio/models/tolerance_table.py"
T009: "Create MermaTable model in backend/apps/acopio/models/merma_table.py"
```

## Parallel Example: Seed Data Phase

```bash
# Launch all 3 fixtures in parallel (different files):
T013: "Create grain_types.json in backend/apps/acopio/fixtures/"
T014: "Create tolerance_tables.json in backend/apps/acopio/fixtures/"
T015: "Create merma_tables.json in backend/apps/acopio/fixtures/"
```

## Parallel Example: API Phases

```bash
# After Phase 3, US1 and US2 can run in parallel:
Phase 4 (US1): "Grain Types API — serializer, viewset, URL, tests"
Phase 5 (US2): "Campaigns API — serializer, viewset, URL, tests"

# Similarly, US3 and US4 can run in parallel:
Phase 6 (US3): "Tolerance Tables API"
Phase 7 (US4): "Merma Tables API"
```

---

## Implementation Strategy

### MVP First (US5 + US1)

1. Complete Phase 1: Setup (app scaffolding)
2. Complete Phase 2: Foundational (all 4 models + migration)
3. Complete Phase 3: US5 (seed data — bootstrap the system)
4. Complete Phase 4: US1 (grain types API — primary operator workflow)
5. **STOP and VALIDATE**: Grain types browsable via API with correct ARCA codes

### Incremental Delivery

1. Setup + Foundational + US5 + US1 -> Grain types browsable (MVP!)
2. Add US2 -> Campaign management functional per tenant
3. Add US3 -> Tolerance lookups functional
4. Add US4 -> Merma band lookups functional
5. Polish -> Admin interfaces, full test suite, acceptance gates

### Agent Team Strategy (from 10-plan.md)

With tmux 4-pane layout:
- **A1 (Wave 1)**: Phase 1 + Phase 2 (setup + models + migration)
- **A2 (Wave 2)**: Phase 4 + Phase 5 + Phase 6 + Phase 7 (all API layers)
- **A3 (Wave 2)**: Phase 3 (seed data + management command)
- **A4 (Wave 3)**: All test tasks from all phases + Phase 8 verification

---

## Testing Protocol

**CRITICAL**: NEVER run pytest inside Claude Code. ALWAYS use the external runner:

```bash
# Run all acopio tests
bash scripts/run-tests-external.sh -n spec10 tests/acopio/

# Check results
cat Docs/Tests/spec10.status     # PASSED | FAILED | RUNNING
cat Docs/Tests/spec10.summary    # ~20 lines
grep "FAILED" Docs/Tests/spec10.log  # Only if FAILED
```

---

## Notes

- [P] tasks = different files, no dependencies
- [US*] label maps task to specific user story for traceability
- All fixture data MUST come from RAG queries — do NOT invent regulatory values
- Soja Hf=12.50 (NOT 13.50) — verified by dedicated test
- Global models use models.Manager(), NOT TenantBoundManager
- CampanaConfig uses TenantBoundManager + AllObjectsManager (explicit declarations)
- Page-number pagination used (justified deviation from constitution's cursor-based default)
