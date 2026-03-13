# Tasks: Tenant Customization Framework

**Input**: Design documents from `/specs/014-tenant-customization/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included — spec success criteria require validation of all 6 field types (SC-004), zero regressions (SC-008), tenant isolation (SC-005), and idempotency (SC-007).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

**Phase Cross-Reference** (tasks phases ↔ plan.md phases):

| Tasks Phase | Plan Phase(s) | Content |
|-------------|---------------|---------|
| 1 (Setup) | — | Package directories |
| 2 (Foundational) | 2 (Models) | Models + migrations |
| 3 (US1) | 3 (Mixin) + 4 (Serializers) | CustomFieldsMixin + Product integration |
| 4 (US2) | 5 (API) | Field definitions endpoint |
| 5 (US3) | 6 (Command) | apply_template command |
| 6 (US5) | 4 (Serializers) | Other entity serializer integration |
| 7 (US4) | 7 (Frontend) | DynamicFields component |
| 8 (US6) | 5 (API) | Module config endpoint |
| 9 (US7) | 5 (API) | Admin interface |
| 10 (Polish) | 8 (Tests) + 9 (Security) | Regression + security review |

> **Note**: Always reference task IDs (T011, T022) not phase numbers when communicating between agents.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create Python package directories needed by later phases

- [X] T001 Create `backend/apps/core/serializers/` Python package — add `__init__.py` (empty, package only)
- [X] T002 [P] Create `backend/apps/core/views/` Python package — add `__init__.py` (empty, package only)
- [X] T003 [P] Create `backend/tests/core/` directory with `__init__.py` if not exists
- [X] T004 [P] Create `backend/tests/integration/` directory with `__init__.py` if not exists

---

## Phase 2: Foundational — Models & Migrations

**Purpose**: Create all 3 new models, add custom_data to 4 entities, generate and apply migrations

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create TenantFieldDefinition, TenantModuleConfig, BusinessTemplate models in `backend/apps/core/models/customization.py` — all fields, validators (RegexValidator on field_key `^[a-z][a-z0-9_]{0,49}$`), choices (entity_type: product/customer/supplier/sale_order; field_type: text/integer/decimal/boolean/date/select; module: inventario/ventas/facturacion/sync), UniqueConstraints (unique_field_per_tenant_entity, unique_module_per_tenant), clean() for select/choices validation, ordering ["section","position","field_key"] on TenantFieldDefinition. BusinessTemplate inherits models.Model (NOT TenantBoundModel). See data-model.md for complete field specifications
- [X] T006 Export TenantFieldDefinition, TenantModuleConfig, BusinessTemplate from `backend/apps/core/models/__init__.py`
- [X] T007 [P] Modify `backend/apps/inventario/models.py` — rename Product.attributes → custom_data (field name + docstring), add Supplier.custom_data = JSONField(default=dict, blank=True), add GIN indexes with jsonb_path_ops (idx_product_custom_data replacing any existing attributes index, idx_supplier_custom_data)
- [X] T008 [P] Modify `backend/apps/ventas/models.py` — add Customer.custom_data and SaleOrder.custom_data = JSONField(default=dict, blank=True), add GIN indexes with jsonb_path_ops (idx_customer_custom_data, idx_saleorder_custom_data)
- [X] T009 Update `backend/apps/inventario/serializers.py` — rename `attributes` → `custom_data` in all field lists (ProductSerializer Meta.fields, ProductCreateSerializer Meta.fields) to match renamed model field
- [X] T010 Generate migrations (core `0003_customization_models`, inventario `0006_product_custom_data`, ventas `0003_custom_data_fields`), run `manage.py migrate`, run `manage.py check`, verify existing tests pass with zero regressions

**Checkpoint**: All 3 migrations applied, `manage.py check` clean, existing tests pass. Foundation ready — user story implementation can begin.

---

## Phase 3: User Story 1 — Product with Validated Custom Fields (Priority: P1) 🎯 MVP

**Goal**: Users create/update Products with tenant-scoped custom field validation including merge semantics, default injection, and caching.

**Independent Test**: Create TenantFieldDefinitions for a tenant (entity_type=product), create Product with custom_data, verify: valid values accepted, invalid types rejected, missing required fields rejected, merge preserves existing keys on PATCH, null removes keys, defaults inject on create only.

**FRs**: FR-001, FR-002, FR-003, FR-004, FR-015, FR-017, FR-023, FR-024, FR-025, FR-026, FR-027

### Implementation

- [X] T011 [US1] Create CustomFieldsMixin in `backend/apps/core/serializers/customization.py` — fetch active TenantFieldDefinitions by tenant_id + entity_type (cache with 60s TTL, key `field_defs:{tenant_id}:{entity_type}`), validate each custom_data key/value against field_type (text→str, integer→int, decimal→Decimal/float, boolean→bool, date→YYYY-MM-DD string, select→in choices list), skip inactive definitions (active=False), apply merge semantics on update (merge incoming with existing custom_data, pop keys with null value), inject default_value on create for absent field keys only, return errors as `{"custom_data": {"field_key": ["error message"]}}`. Mixin must call super().validate() and super().create()/super().update() to preserve existing serializer behavior
- [X] T012 [US1] Create `backend/apps/core/signals.py` — post_save and post_delete signals on TenantFieldDefinition to invalidate cache key `field_defs:{instance.tenant_id}:{instance.entity_type}` via cache.delete()
- [X] T013 [US1] Wire signals in `backend/apps/core/apps.py` ready() method — import apps.core.signals module
- [X] T014 [US1] Add CustomFieldsMixin to ProductCreateSerializer in `backend/apps/inventario/serializers.py` — set entity_type = "product", ensure custom_data passes through mixin validation on create and update

### Tests

- [X] T015 [US1] Write model constraint tests in `backend/tests/core/test_customization_models.py` — unique constraint violation (same tenant+entity_type+field_key), field_key regex rejection (uppercase, spaces, starts with digit), choices required for select type, invalid entity_type/field_type/module values rejected, default_value type mismatch, active defaults to True, ordering verification
- [X] T016 [P] [US1] Write mixin validation tests in `backend/tests/core/test_custom_fields_mixin.py` — valid/invalid for all 6 field types, merge semantics (incoming merges with existing, null removes key, unstated keys preserved), default injection (create-only and absent-only, not on update), inactive field skipping (active=False excluded), error format structure matches `{"custom_data": {"key": ["msg"]}}`, cache hit/miss verification, undefined keys silently ignored

**Checkpoint**: US1 complete — Product custom_data validated, merge works, defaults inject, cache invalidates. All US1 tests pass.

---

## Phase 4: User Story 2 — Field Definitions Retrieval (Priority: P1)

**Goal**: Frontend can query tenant-scoped field definitions filtered by entity type for dynamic form rendering.

**Independent Test**: Create field definitions for multiple tenants and entity types, query GET /api/v1/field-definitions/, verify: correct fields returned, entity_type filter works, inactive excluded, ordered by section/position/field_key, tenant isolation enforced, 401 without auth.

**FRs**: FR-007

### Implementation

- [X] T017 [US2] Add FieldDefinitionSerializer to `backend/apps/core/serializers/customization.py` — read-only ModelSerializer, fields: id, field_key, label, entity_type, field_type, section, position, required, default_value, choices per contracts/field-definitions.yaml
- [X] T018 [US2] Create FieldDefinitionViewSet in `backend/apps/core/views/customization.py` — list-only (no create/update/delete), queryset = TenantFieldDefinition.objects.filter(active=True) scoped by request.user.tenant, support entity_type query parameter filter, ordering by section/position/field_key, permission_classes = [IsAuthenticated]
- [X] T019 [US2] Create `backend/apps/core/urls.py` — import DefaultRouter from rest_framework.routers, register FieldDefinitionViewSet at prefix "field-definitions", export urlpatterns = router.urls
- [X] T020 [US2] Update `backend/gravitea/urls.py` — add `path("", include("apps.core.urls"))` in the api/v1/ urlpatterns block alongside existing app includes

### Tests

- [X] T021 [US2] Write endpoint tests in `backend/tests/core/test_field_definitions_api.py` — list returns all active fields for tenant, entity_type query param filters correctly, inactive definitions excluded, response ordered by section/position/field_key, tenant A cannot see tenant B's definitions, 401 returned without authentication, response fields match contract schema

**Checkpoint**: US2 complete — GET /api/v1/field-definitions/ returns correct data with filtering and tenant isolation. All US2 tests pass.

---

## Phase 5: User Story 3 — Template-Based Tenant Onboarding (Priority: P1)

**Goal**: Administrators apply a business template to bootstrap field definitions and module configs for a tenant in one idempotent command.

**Independent Test**: Run `manage.py apply_template ferreteria --tenant-id <UUID>`, verify 3 module configs + 7 field definitions created. Run again, verify idempotent (no duplicates, no errors).

**FRs**: FR-009, FR-010, FR-011

### Implementation

- [X] T022 [US3] Create `backend/apps/core/management/commands/apply_template.py` — BaseCommand accepting slug (positional arg) + --tenant-id (required UUID arg). Look up BusinessTemplate by slug or use embedded template data. For "ferreteria": create 3 TenantModuleConfig rows (inventario/ventas/facturacion, all enabled=True) and 7 TenantFieldDefinition rows (peso_kg, largo_cm, ancho_cm, alto_cm as decimal in dimensiones; material as select with 7 choices, marca as text, codigo_proveedor as text in caracteristicas) — all idempotent via get_or_create. Print "Created" or "Already exists" per record. Template data per data-model.md ferreteria section

### Tests

- [X] T023 [US3] Write command tests in `backend/tests/core/test_apply_template.py` — first run creates 3 modules + 7 fields (verify counts), second run is idempotent (verify "already exists" for all), invalid slug returns error with exit code 1, verify field definition attributes match template data (field_key, label, entity_type, field_type, section, position, choices for material)

**Checkpoint**: US3 complete — `manage.py apply_template ferreteria --tenant-id <UUID>` creates expected records, idempotent. All US3 tests pass.

---

## Phase 6: User Story 5 — Custom Data on Other Business Entities (Priority: P2)

**Goal**: Customer, Supplier, and SaleOrder support validated custom_data using the same CustomFieldsMixin proven on Product.

**Independent Test**: Create field definitions for entity_type=customer/supplier/sale_order, create records with custom_data, verify entity-specific validation runs correctly (not Product definitions).

**FRs**: FR-003 (applied to all 4), FR-006, FR-024 (proven reusable)

**Depends on**: US1 (CustomFieldsMixin must be proven on Product first)

### Implementation

- [X] T024 [P] [US5] Add CustomFieldsMixin to SupplierSerializer (or write variant) in `backend/apps/inventario/serializers.py` — set entity_type = "supplier", add "custom_data" to Meta.fields
- [X] T025 [P] [US5] Add CustomFieldsMixin to CustomerSerializer and SaleOrderSerializer (or write variants) in `backend/apps/ventas/serializers.py` — set entity_type = "customer" and "sale_order" respectively, add "custom_data" to Meta.fields for each

### Tests

- [X] T026 [US5] Write cross-entity validation tests in `backend/tests/integration/test_custom_fields_e2e.py` — create field definitions per entity type, create Customer/Supplier/SaleOrder with valid custom_data, verify invalid values rejected, verify entity-specific definitions don't cross-contaminate (product defs don't apply to customer), test merge semantics on all entities

**Checkpoint**: US5 complete — all 4 entity types support validated custom_data via same reusable mixin (SC-009). All US5 tests pass.

---

## Phase 7: User Story 4 — Frontend Renders Dynamic Product Fields (Priority: P2)

**Goal**: Product create/edit form dynamically renders custom fields based on tenant's field definitions with type-mapped inputs, client-side validation, and backend error display.

**Independent Test**: Apply ferreteria template, open Product form at http://localhost:3000, verify: "Custom Fields" section with 2 subsections (Dimensiones: 4 number inputs; Caracteristicas: 1 dropdown + 2 text inputs), fill values and submit, verify saved and visible on edit. No section shown when no definitions exist.

**FRs**: FR-018, FR-019, FR-020, FR-021, FR-022

**Depends on**: US2 (field definitions endpoint must exist)

### Implementation

- [X] T027 [US4] Create `frontend-prototype/src/components/inventario/dynamic-fields.tsx` — fetch field definitions from `/api/v1/field-definitions/?entity_type=product` using TanStack Query (useQuery), group fields by section, render section headers (capitalize section name), map field_type to shadcn/ui inputs: text→Input, integer/decimal→Input[type=number step appropriate], boolean→Switch or Checkbox, date→Input[type=date], select→Select with choices as options. Accept props: initialValues (Record<string,any> for edit pre-population), errors (Record<string,string[]> for backend error display), onChange (callback with updated custom_data object). Implement required field client-side validation (mark required, prevent empty submit). Render nothing (return null) when field definitions array is empty (FR-022)
- [X] T028 [US4] Update `frontend-prototype/src/components/inventario/products-tab.tsx` — import DynamicFields component, render below standard fields in CrudForm create/edit form, pass existing custom_data as initialValues for edit mode, collect DynamicFields values and include as custom_data in form submission payload, wire backend error.custom_data to DynamicFields errors prop for per-field error display

**Checkpoint**: US4 complete — Product form renders ferreteria custom fields in 2 sections, validation works client+server, errors display next to inputs, no section when no definitions (FR-022).

---

## Phase 8: User Story 6 — Module Activation (Priority: P3)

**Goal**: Frontend can query which ERP modules are enabled for the current tenant via read-only API.

**Independent Test**: Create module configs for a tenant (inventario enabled, sync disabled), query GET /api/v1/module-config/, verify correct enabled/disabled status per module.

**FRs**: FR-008 (FR-012 and FR-013 model creation covered in Phase 2/T005)

### Implementation

- [X] T029 [US6] Add ModuleConfigSerializer to `backend/apps/core/serializers/customization.py` — read-only ModelSerializer, fields: id, module, enabled, settings per contracts/module-config.yaml
- [X] T030 [US6] Add ModuleConfigViewSet to `backend/apps/core/views/customization.py` — list-only, queryset scoped by request.user.tenant, permission_classes = [IsAuthenticated]
- [X] T031 [US6] Register ModuleConfigViewSet at prefix "module-config" in `backend/apps/core/urls.py` DefaultRouter

### Tests

- [X] T032 [US6] Write endpoint tests in `backend/tests/core/test_module_config_api.py` — list returns correct modules and enabled status, tenant isolation (tenant A can't see tenant B's configs), 401 without auth, unique constraint prevents duplicate module per tenant

**Checkpoint**: US6 complete — GET /api/v1/module-config/ returns correct data with tenant isolation. All US6 tests pass.

---

## Phase 9: User Story 7 — Admin Interface for Field Management (Priority: P3)

**Goal**: Team members manage field definitions, module configs, and business templates via Django admin with proper list views, filters, and search.

**Independent Test**: Navigate http://localhost:8000/admin/, verify all 3 models listed under Core, create/edit/deactivate field definitions, verify list views show correct columns with working filters and search.

**FRs**: FR-014

### Implementation

- [X] T033 [US7] Create `backend/apps/core/admin.py` — register TenantFieldDefinition with ModelAdmin (list_display: field_key, label, entity_type, field_type, section, active; list_filter: entity_type, field_type, section, active; search_fields: field_key, label), TenantModuleConfig with ModelAdmin (list_display: tenant, module, enabled; list_filter: module, enabled), BusinessTemplate with ModelAdmin (list_display: slug, name; search_fields: slug, name)

### Tests

- [X] T034 [US7] Verify admin interface renders correctly — navigate to each model's changelist and add views in browser, verify list_display columns shown, filters functional, search works for field_key and label

**Checkpoint**: US7 complete — Django admin provides full list/add/change/delete for all 3 customization models with filters and search.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Security review, integration testing, regression verification, documentation validation

- [X] T035 [P] Security review — verify TenantFieldDefinition and TenantModuleConfig use TenantBoundManager (tenant isolation), verify both API endpoints return only current tenant's data, verify BusinessTemplate has no tenant FK (system-wide by design), review CustomFieldsMixin for injection risks via field_key or custom_data values
- [X] T036 Write tenant isolation regression test in `backend/tests/core/test_field_definitions_api.py` — create field definitions for two separate tenants, authenticate as each, verify each tenant sees only their own definitions via API, verify module-config endpoint similarly isolated
- [X] T037 Run full regression suite — all new tests + all existing tests pass, zero regressions (SC-008)
- [X] T038 [P] Verify Swagger/ReDoc includes new endpoints (field-definitions, module-config) with correct request/response schemas matching contracts/
- [X] T039 Run quickstart.md verification steps 1-9 end-to-end — migrations, template, field definitions API, module config API, custom data validation, merge semantics, frontend DynamicFields, admin interface, all test files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP delivery
- **US2 (Phase 4)**: Depends on Foundational — can run in parallel with US1
- **US3 (Phase 5)**: Depends on Foundational — can run in parallel with US1/US2
- **US5 (Phase 6)**: Depends on US1 (CustomFieldsMixin must exist)
- **US4 (Phase 7)**: Depends on US2 (field definitions endpoint must exist)
- **US6 (Phase 8)**: Depends on Foundational — can run in parallel with US1-US5
- **US7 (Phase 9)**: Depends on Foundational — can run in parallel with US1-US6
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

```text
Foundational (Phase 2) ─┬─► US1 (Phase 3) ──► US5 (Phase 6)
                        ├─► US2 (Phase 4) ──► US4 (Phase 7)
                        ├─► US3 (Phase 5)
                        ├─► US6 (Phase 8)
                        └─► US7 (Phase 9)
                                              ──► Polish (Phase 10)
```

### Within Each User Story

- Implementation tasks before test tasks
- Models before serializers before views before URLs
- Core framework (mixin, signals) before integration (wire into app serializers)
- Backend before frontend

### Parallel Opportunities

**After Foundational completes, these can run in parallel:**
- US1 + US2 + US3 + US6 + US7 (all depend only on Foundational)
- US4 starts after US2 completes
- US5 starts after US1 completes

**Within phases, [P] tasks can run in parallel:**
- Phase 1: T002, T003, T004 (all parallel with each other)
- Phase 2: T007, T008 (parallel — different model files)
- Phase 3: T015, T016 (parallel — different test files)
- Phase 6: T024, T025 (parallel — different serializer files)
- Phase 10: T035, T038 (parallel — independent reviews)

---

## Parallel Example: After Foundational

```text
# With 3 agents (plan.md team architecture):
BACKEND-CODER: US1 (T011-T014) → US5 (T024-T025) → US6 (T029-T031) → US7 (T033)
QA:            US1 tests (T015-T016) → US2 tests (T021) → US3 tests (T023) → US5 tests (T026) → US6 tests (T032) → US7 (T034)
FRONTEND-CODER: [idle until US2 done] → US4 (T027-T028)

# Backend-only (1 agent):
T011-T016 → T017-T021 → T022-T023 → T024-T026 → T027-T028 → T029-T032 → T033-T034 → T035-T039
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 — Product with Validated Custom Fields
4. **STOP and VALIDATE**: Create field definitions, validate Product custom_data
5. Deploy/demo: Tenants can define and validate custom product fields

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Product custom fields validated → **MVP!**
3. US2 → Field definitions API available → enables frontend (US4)
4. US3 → Template onboarding → rapid tenant setup
5. US5 → All 4 entities support custom fields → framework proven reusable (SC-009)
6. US4 → Frontend renders dynamic fields on Product form → user-facing proof
7. US6 + US7 → Module config + admin interface → management tools
8. Polish → Security review + regression suite → feature complete

### Parallel Team Strategy

With the 6-agent team from plan.md:

1. ORCHESTRATOR manages phase gates and checkpoints
2. BACKEND-CODER: Foundational → US1 → US2 → US3 → US5 → US6 → US7
3. QA: Tests for US1 → Tests for US2 → Tests for US3 → Tests for US5 → Tests for US6 → Integration + security
4. FRONTEND-CODER: Idle until US2 endpoint available → US4
5. DJANGO-EXPERT (on-demand): Advisory during Foundational + US1 (first mixin, first admin)
6. SECURITY (on-demand): Phase 10 tenant isolation review

---

## Notes

- [P] tasks = different files, no dependencies on other [P] tasks in same phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable after its checkpoint
- Commit after each task or logical group
- All file paths are relative to repository root
- **data-model.md** is authoritative for model field definitions, constraints, and validators
- **contracts/** (field-definitions.yaml, module-config.yaml) are authoritative for API response schemas
- **quickstart.md** provides end-to-end verification steps (Phase 10 T039)
- Undefined keys in custom_data are silently ignored (not validated, not rejected)
- CustomFieldsMixin is the project's FIRST serializer mixin — quality matters for pattern setting
