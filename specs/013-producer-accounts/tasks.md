# Tasks: Producer Accounts (Spec-13)

**Input**: Design documents from `/specs/013-producer-accounts/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: Included — spec.md SC-008 explicitly requires 40+ automated tests.

**Agent Wave Mapping**:
| Wave | Agent | Tasks |
|------|-------|-------|
| Wave 1 | A1 (python-expert) | T001–T011 |
| Wave 2 | A2 (backend-architect) | T014–T016, T024, T028, T033, T037, T040–T041 |
| Wave 3 | A3 (backend-architect) | T018–T022, T025–T026, T029–T031, T034–T035, T038–T039, T042 |
| Wave 4 | A4 (quality-engineer) | T012–T013, T017, T023, T027, T032, T036 (run after Wave 3; fix any failures) |

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel with other [P] tasks in the same phase
- **[Story]**: User story this task belongs to (US1–US6)

---

## Phase 1: Setup (App Boilerplate)

**Purpose**: Create the `apps.cuentas` package structure so A1 can immediately write models.

**⚠️ CRITICAL**: Must complete before any model work begins.

- [X] T001 Create backend/apps/cuentas/__init__.py (empty)
- [X] T002 Create backend/apps/cuentas/apps.py with `CuentasConfig(name="apps.cuentas", label="gravitea_cuentas", verbose_name="Cuentas Corrientes")`
- [X] T003 [P] Create empty init files: backend/apps/cuentas/models/__init__.py, services/__init__.py, serializers/__init__.py, views/__init__.py, migrations/__init__.py, management/__init__.py, management/commands/__init__.py
- [X] T004 [P] Register app and test marker: (1) append `"apps.cuentas"` to INSTALLED_APPS after `"apps.acopio"` in backend/gravitea/settings/base.py; (2) add `accounts` to the markers list in backend/pytest.ini (or `[tool:pytest]` markers section in backend/setup.cfg) — required so `@pytest.mark.accounts` does not trigger `PytestUnknownMarkWarning` or fail under `--strict-markers`

**Checkpoint**: `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "import apps.cuentas; print('OK')"` succeeds

---

## Phase 2: Foundational (Models + Migration + RLS)

**Purpose**: ProducerAccount and AccountMovement models — shared foundation for ALL user stories.

**⚠️ CRITICAL**: No user story work can begin until GATE G1 passes (models importable, no missing migrations).

- [X] T005 [P] Create ProducerAccount model in backend/apps/cuentas/models/producer_account.py — TenantBoundModel with fields: producer_cuit_encrypted (EncryptedCharField), producer_cuit_hash (BlindIndexField), branch FK, grain_type FK, campaign FK, grain_balance_kg DECIMAL(17,3), ars_balance DECIMAL(17,3), usd_balance DECIMAL(17,3), is_active, created_by FK, created_at, updated_at; Meta: db_table="cuentas_produceraccount", UniqueConstraint on (tenant, producer_cuit_hash, branch, grain_type, campaign), CheckConstraint grain_balance_kg >= 0, two Index entries; save() auto-computes producer_cuit_hash from plaintext using compute_blind_index(); also add `validators=[RegexValidator(r'^\d{2}-\d{8}-\d$', message="CUIT must be in format XX-XXXXXXXX-X")]` on `producer_cuit_encrypted` field to enforce Argentine CUIT format at model level (11 digits in XX-XXXXXXXX-X pattern)
- [X] T006 [P] Create AccountMovement model in backend/apps/cuentas/models/account_movement.py — TenantBoundModel with MovementType TextChoices (9 types: CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO, SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT, RETENTION_DEDUCTION, ADJUSTMENT), fields: producer_account FK(PROTECT), movement_type, quantity_kg DECIMAL(17,3), ars_amount DECIMAL(17,3), usd_amount DECIMAL(17,3), romaneo FK(Romaneo, SET_NULL, null=True), reference_document CharField(200, blank), notes TextField(blank), movement_at (auto_now_add), created_by FK; Meta: db_table="cuentas_accountmovement", Index on (producer_account, -movement_at); immutability: save() raises ValueError if not _state.adding; delete() raises ValueError
- [X] T007 Update backend/apps/cuentas/models/__init__.py to re-export ProducerAccount and AccountMovement
- [X] T008 Create backend/apps/cuentas/admin.py — register ProducerAccount (list_display: id, producer_cuit_hash, branch, grain_type, campaign, grain_balance_kg, is_active) and AccountMovement (list_display: id, producer_account, movement_type, quantity_kg, movement_at, created_by)
- [X] T009 Generate migration: run `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python manage.py makemigrations cuentas --name producer_accounts` in backend/ to produce backend/apps/cuentas/migrations/0001_producer_accounts.py; verify migration applies with `manage.py migrate --run-syncdb --check`
- [X] T010 [P] Create backend/database/sql/cuentas_rls.sql — RLS policies for cuentas_produceraccount and cuentas_accountmovement tables following acopio_rls.sql pattern: ENABLE ROW LEVEL SECURITY, FORCE ROW LEVEL SECURITY, CREATE POLICY using get_current_tenant_id() for both USING and WITH CHECK clauses
- [X] T011 [P] Create backend/tests/cuentas/__init__.py (empty) and backend/tests/cuentas/conftest.py with fixtures: producer_account_factory (creates ProducerAccount with compute_blind_index for hash, default CUIT "20-12345678-9"), account_movement_factory (creates AccountMovement of any type), romaneo_conforme_factory (creates a fully-valid CONFORME Romaneo with all prerequisites: QA record, merma calculation, storage_unit set — represents a third-party grain romaneo; note: `is_own_grain` is a local variable in the confirmar view, NOT a Romaneo model field, so do not attempt to set it on the model) — reuse acopio fixtures from tests/acopio/conftest.py

**GATE G1**: Run `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.models import ProducerAccount, AccountMovement; print('OK')"` and `manage.py makemigrations --check --dry-run` — both must pass before proceeding

---

## Phase 3: User Story 1 — Automatic Account Creation on Grain Reception (Priority: P1) 🎯 MVP

**Goal**: When a romaneo is confirmed (CONFORME) for third-party grain, automatically create (or find) a ProducerAccount and insert a CEG_DEPOSIT AccountMovement for the confirmed kg, all within a single transaction.atomic().

**Independent Test**: Confirm a romaneo via API POST /acopio/romaneos/{id}/confirmar/ and verify: (1) ProducerAccount exists with correct composite key, (2) AccountMovement of type CEG_DEPOSIT exists with quantity_kg = peso_neto_conforme_kg, (3) account.grain_balance_kg equals the movement quantity.

### Tests (US1)

- [X] T012 [P] [US1] Write backend/tests/cuentas/test_account_models.py with ~15 tests covering: ProducerAccount creation with all required fields, composite uniqueness constraint (duplicate raises IntegrityError), blind index auto-computed on save, grain_balance_kg non-negative check constraint, AccountMovement creation succeeds when _state.adding=True, AccountMovement.save() raises ValueError on update attempt, AccountMovement.delete() raises ValueError, EncryptedCharField stores ciphertext (not plaintext) in DB, producer_cuit property decrypts correctly, movement types enum has all 9 values, balance fields default to 0.000, created_at/updated_at/created_by provenance populated, CUIT format validation rejects invalid format (e.g. "12345" raises ValidationError), valid CUIT format "20-12345678-9" accepted; mark with @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.unit
- [X] T013 [P] [US1] Write backend/tests/cuentas/test_ceg_deposit_integration.py with ~8 tests: romaneo CONFORME creates ProducerAccount + CEG_DEPOSIT (happy path), existing account reused on second romaneo (grain_balance_kg accumulates), own_grain=True skips account creation entirely, transaction rolls back when storage_unit missing (romaneo stays non-CONFORME), transaction rolls back when grain deposit fails (no ProducerAccount created), concurrent creation race condition handled by select_for_update (no duplicate accounts), balance matches peso_neto_conforme_kg exactly; mark with @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.integration

### Implementation (US1)

- [X] T014 Create backend/apps/cuentas/services/accounts.py — implement AccountService.get_or_create_account(tenant, producer_cuit: str, branch, grain_type, campaign, operator) using select_for_update() + get_or_create on producer_cuit_hash blind index; implement CEGDepositService.create_ceg_deposit(romaneo, operator) wrapping in transaction.atomic(): get_or_create account, create AccountMovement(CEG_DEPOSIT, quantity_kg=romaneo.peso_neto_conforme_kg), update account.grain_balance_kg atomically via update_fields=["grain_balance_kg", "updated_at"]
- [X] T015 [P] Create backend/apps/cuentas/services/__init__.py exporting create_ceg_deposit and AccountService
- [X] T016 Modify backend/apps/acopio/views/romaneo.py confirmar action: wrap steps 6-9 in transaction.atomic() (romaneo.save + storage_unit validation moved inside + create_deposit_from_romaneo + conditional create_ceg_deposit); add `is_own_grain = False` default; add `if not is_own_grain: from apps.cuentas.services.accounts import create_ceg_deposit; create_ceg_deposit(romaneo, operator=request.user)`; storage_unit validation MUST be inside the atomic block

**GATE G2**: Run `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.services.accounts import create_ceg_deposit; print('OK')"` — must succeed before Wave 3

**Checkpoint**: US1 complete — run `bash scripts/run-tests-external.sh -n spec13-us1 tests/cuentas/test_ceg_deposit_integration.py tests/cuentas/test_account_models.py` and verify PASSED

---

## Phase 4: User Story 2 — View Account Balances and Movement History (Priority: P1)

**Goal**: Authenticated users can list/retrieve ProducerAccounts (with CUIT blind index filter) and browse the append-only AccountMovement ledger. PATCH/DELETE on movements returns HTTP 405.

**Independent Test**: GET /api/v1/cuentas/accounts/?producer_cuit=20-12345678-9 returns the correct accounts. GET /api/v1/cuentas/accounts/{id}/movements/ returns cursor-paginated ledger. PATCH/DELETE on a movement → 405 append_only_violation.

### Tests (US2)

- [X] T017 [P] [US2] Write backend/tests/cuentas/test_account_api.py with ~12 tests: GET /accounts/ returns only tenant accounts (isolation), GET /accounts/?producer_cuit= filters via blind index, GET /accounts/{id}/ returns account with decrypted CUIT, GET /accounts/{wrong_tenant_id}/ returns 404, GET /accounts/{id}/movements/ returns cursor-paginated ledger newest-first, movement_type filter works, PATCH /movements/{id}/ returns 405 with code="append_only_violation", DELETE /movements/{id}/ returns 405, unauthenticated request → 401, movement list includes romaneo reference for CEG_DEPOSIT entries; mark @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.integration

### Implementation (US2)

- [X] T018 [P] [US2] Create backend/apps/cuentas/serializers/accounts.py — ProducerAccountSerializer (read-only, fields: id, producer_cuit [decrypted], branch, branch_name, grain_type, grain_type_code, grain_type_name, campaign, campaign_label, grain_balance_kg, ars_balance, usd_balance, is_active, created_at, updated_at; exclude producer_cuit_encrypted and producer_cuit_hash); AccountMovementSerializer (read-only, fields: id, movement_type, movement_type_display, quantity_kg, ars_amount, usd_amount, romaneo, romaneo_numero, reference_document, notes, movement_at, created_by_name)
- [X] T019 [P] [US2] Create two CursorPagination subclasses in backend/apps/cuentas/views/accounts.py: `AccountCursorPagination(ordering="-created_at", page_size=25)` and `MovementCursorPagination(ordering="-movement_at", page_size=50)`; create ProducerAccountViewSet (ReadOnlyModelViewSet, IsAuthenticated, pagination_class=AccountCursorPagination, get_queryset returns `ProducerAccount.objects.filter(tenant_id=...).select_related("branch", "grain_type", "campaign", "created_by")` + optional CUIT blind index filter via `compute_blind_index`); create AccountMovementViewSet (ModelViewSet, IsAuthenticated, pagination_class=MovementCursorPagination, http_method_names=["get","post","head","options"], get_queryset returns `AccountMovement.objects.filter(producer_account_id=pk, tenant_id=...).select_related("producer_account", "romaneo", "created_by")`, update/partial_update/destroy methods returning Response(status=405, data={"code":"append_only_violation"}))
- [X] T020 [P] [US2] Update backend/apps/cuentas/serializers/__init__.py and backend/apps/cuentas/views/__init__.py to export all serializers and viewsets
- [X] T021 [US2] Create backend/apps/cuentas/urls.py — DRF DefaultRouter registers ProducerAccountViewSet at "accounts" (provides list + detail routes); add explicit `path()` entries for nested movement routes (DRF DefaultRouter does NOT auto-nest): `path("accounts/<uuid:pk>/movements/", AccountMovementViewSet.as_view({"get": "list", "post": "create"}), name="account-movement-list")` and `path("accounts/<uuid:pk>/movements/<uuid:movement_pk>/", AccountMovementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="account-movement-detail")`; export `urlpatterns = router.urls + [...]`
- [X] T022 [US2] Add cuentas URL include to backend/gravitea/urls.py: `path("api/v1/cuentas/", include("apps.cuentas.urls"))`

**GATE G3**: Run `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(f'{len(urlpatterns)} routes')"` — must return ≥2 routes

**Checkpoint**: US2 complete — run `bash scripts/run-tests-external.sh -n spec13-us2 tests/cuentas/test_account_api.py` and verify PASSED

---

## Phase 5: User Story 3 — Record Manual Debit Entries (Priority: P2)

**Goal**: Operators create SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION movements; supervisors create ADJUSTMENT. Each updates the account balance atomically. ADJUSTMENT without supervisor permission → 403.

**Independent Test**: POST /api/v1/cuentas/accounts/{id}/movements/ with movement_type=SERVICE_CHARGE, ars_amount="-5000.000", reference_document="FAC-001" → 201, account ars_balance decreases by 5000.

### Tests (US3)

- [X] T023 [P] [US3] Write backend/tests/cuentas/test_account_services.py with ~8 tests: create SERVICE_CHARGE decrements ars_balance, create RETIRO decrements ars_balance (negative balance allowed), SERVICE_CHARGE with positive ars_amount raises ValidationError (sign violation), ADJUSTMENT with supervisor permission succeeds, ADJUSTMENT without supervisor permission raises PermissionDenied, CEG_DEPOSIT via API returns 400 (not a manual type), RETENTION_DEDUCTION decrements ars_balance, account from different tenant returns 404; mark @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.unit

### Implementation (US3)

- [X] T024 [US3] Add ManualMovementService to backend/apps/cuentas/services/accounts.py — create_manual_movement(account, movement_type, quantity_kg, ars_amount, usd_amount, reference_document, notes, operator): (1) validate movement_type in MANUAL_TYPES set; (2) validate sign convention (SERVICE_CHARGE/RETIRO/RETENTION_DEDUCTION: ars_amount ≤ 0); (3) **pre-validate grain balance**: if quantity_kg < 0 and account.grain_balance_kg + quantity_kg < 0 raise `ValidationError({"quantity_kg": "Grain balance cannot go negative."}, code="grain_balance_negative")` — this produces a clean 400 before the DB CheckConstraint fires; (4) in transaction.atomic() create AccountMovement + update account balance fields via update_fields=["grain_balance_kg", "ars_balance", "usd_balance", "updated_at"]; add MANUAL_TYPES and SUPERVISOR_ONLY_TYPES constants
- [X] T025 [US3] Add ManualMovementSerializer to backend/apps/cuentas/serializers/accounts.py — write-only serializer with fields: movement_type (validate in MANUAL_TYPES), quantity_kg, ars_amount, usd_amount, reference_document (required), notes; sign validation in validate()
- [X] T026 [US3] Extend AccountMovementViewSet.perform_create() in backend/apps/cuentas/views/accounts.py — validate movement_type in MANUAL_TYPES (else raise ValidationError code="invalid_movement_type"), check SUPERVISOR_ONLY_TYPES against request.user.has_permission("settings.admin") (else raise PermissionDenied), call ManualMovementService.create_manual_movement(); select serializer class based on request method (read vs write)

**Checkpoint**: US3 complete — run `bash scripts/run-tests-external.sh -n spec13-us3 tests/cuentas/test_account_services.py` and verify PASSED

---

## Phase 6: User Story 4 — Consolidated Position Across Plants (Priority: P2)

**Goal**: GET /api/v1/cuentas/posicion-consolidada/?producer_cuit=&campaign_id= returns aggregated grain/monetary balances across all branches, grouped by grain type with per-branch breakdown.

**Independent Test**: Create ProducerAccount records for the same CUIT across 2 branches with known balances. Query posicion-consolidada → verify totals equal sum of individual accounts, branch_breakdown contains both branches.

### Tests (US4)

- [X] T027 [P] [US4] Add posicion consolidada tests to backend/tests/cuentas/test_account_services.py: single producer multi-branch multi-grain totals correctly, zero-balance campaigns return empty summary (not error), missing producer_cuit returns 400, cross-tenant CUITs not included in result; mark @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.integration

### Implementation (US4)

- [X] T028 [US4] Create backend/apps/cuentas/services/statements.py — PosicionConsolidadaService.compute(tenant, producer_cuit: str, campaign) using SQL aggregation via Django ORM: ProducerAccount.objects.filter(tenant, producer_cuit_hash, campaign, is_active=True).values(grain_type_id, grain_type__code, grain_type__name).annotate(total_grain_kg=Sum, total_ars=Sum, total_usd=Sum) + separate branch_breakdown query; return structured dict (never stored)
- [X] T029 [P] [US4] Create PosicionConsolidadaSerializer in backend/apps/cuentas/serializers/accounts.py — read-only, nested structure: producer_cuit, campaign_id, campaign_label, summary list (grain_type_id, codes, total_grain_kg, total_ars, total_usd, branch_breakdown list)
- [X] T030 [US4] Add PosicionConsolidadaView (APIView, IsAuthenticated) to backend/apps/cuentas/views/accounts.py — GET validates producer_cuit and campaign_id query params (400 if missing), calls PosicionConsolidadaService.compute(), returns PosicionConsolidadaSerializer response
- [X] T031 [US4] Register PosicionConsolidadaView route in backend/apps/cuentas/urls.py: `path("posicion-consolidada/", PosicionConsolidadaView.as_view(), name="posicion-consolidada")`

**Checkpoint**: US4 complete — run `bash scripts/run-tests-external.sh -n spec13-us4 tests/cuentas/test_account_services.py` and verify PASSED

---

## Phase 7: User Story 5 — Account Statement Generation (Priority: P3)

**Goal**: GET /api/v1/cuentas/accounts/{id}/statement/?date_from=&date_to= returns structured statement with opening/closing balances and movement list for the period, separated into grain and monetary sub-ledgers.

**Independent Test**: Create account with 10 movements (Jan–Mar 2026). Request statement for Feb 2026 only → opening balance = sum of Jan movements, movements list = Feb only, closing balance = opening + Feb sum.

### Tests (US5)

- [X] T032 [P] [US5] Add statement tests to backend/tests/cuentas/test_account_api.py: correct period isolation (only Feb movements in Feb statement), opening balance = pre-period sum, closing = opening + period sum, empty period returns equal opening/closing with empty movements list, missing date_from returns 400, missing date_to returns 400, date_from > date_to returns 400; mark @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.integration

### Implementation (US5)

- [X] T033 [US5] Add StatementService to backend/apps/cuentas/services/statements.py — generate(account, date_from, date_to): compute opening_balance via AccountMovement.objects.filter(movement_at__lt=date_from).aggregate(Sum(quantity_kg), Sum(ars_amount), Sum(usd_amount)); get period movements via filter(movement_at__date__range=(date_from, date_to)).order_by("movement_at"); compute closing = opening + period sums; return dict with grain_ledger and monetary_ledger sub-objects
- [X] T034 [US5] Add StatementView (APIView, IsAuthenticated) to backend/apps/cuentas/views/accounts.py — GET validates date_from + date_to query params and date_from ≤ date_to (400 on violation), fetches account (404 if cross-tenant), calls StatementService.generate(), returns structured response per contracts/accounts-api.md
- [X] T035 [US5] Register StatementView as nested route in backend/apps/cuentas/urls.py: `path("accounts/<uuid:pk>/statement/", StatementView.as_view(), name="account-statement")`

**Checkpoint**: US5 complete — run `bash scripts/run-tests-external.sh -n spec13-us5 tests/cuentas/test_account_api.py` and verify PASSED

---

## Phase 8: User Story 6 — Balance Consistency Verification (Priority: P3)

**Goal**: Management command that compares stored ProducerAccount balance fields against the sum of all AccountMovement records. Reports discrepancies to stdout with account ID and expected vs actual values.

**Independent Test**: Run `manage.py check_account_balance` on correct accounts → "OK: 0 discrepancies". Manually set account.grain_balance_kg to wrong value → command reports that account ID with delta.

### Tests (US6)

- [X] T036 [P] [US6] Add balance consistency tests to backend/tests/cuentas/test_account_models.py: check_account_balance command returns 0 discrepancies for correct accounts, command detects grain_balance_kg drift (manually corrupted), command detects ars_balance drift, command returns exit code 1 when discrepancies found, command accepts --tenant flag to scope check; mark @pytest.mark.django_db @pytest.mark.accounts @pytest.mark.unit

### Implementation (US6)

- [X] T037 [US6] Create backend/apps/cuentas/management/commands/check_account_balance.py — BaseCommand subclass with handle(): accept --tenant optional arg; query ProducerAccount.objects (scoped by tenant if provided); for each account compute expected_grain = AccountMovement.objects.filter(producer_account=acc).aggregate(Sum("quantity_kg")), expected_ars = Sum("ars_amount"), expected_usd = Sum("usd_amount"); compare with stored values; output discrepancies; exit with sys.exit(1) if any found; exit 0 if clean

**Checkpoint**: US6 complete — run `bash scripts/run-tests-external.sh -n spec13-us6 tests/cuentas/test_account_models.py` and verify PASSED

---

## Phase 9: Polish & Full Test Run

**Purpose**: Run full test suite, verify no regressions in acopio, apply RLS.

- [X] T038 Run complete spec-13 test suite via `bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/` — poll `cat Docs/Tests/spec13-final.status` until PASSED; read summary via `cat Docs/Tests/spec13-final.summary`; investigate any failures via `grep "FAILED" Docs/Tests/spec13-final.log`
- [X] T039 Run acopio regression check via `bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/` — verify romaneo confirmar tests still pass after transaction.atomic() wrapping change; poll and read summary; fix any regressions before marking done
- [X] T040 [P] Apply RLS policies to database: execute `backend/database/sql/cuentas_rls.sql` via `psql $DATABASE_URL -f backend/database/sql/cuentas_rls.sql` or equivalent; verify policies exist via `\d cuentas_produceraccount` in psql
- [X] T041 [P] Update backend/apps/cuentas/services/__init__.py and backend/apps/cuentas/services/statements.py __init__.py imports to export all public service functions (create_ceg_deposit, StatementService, PosicionConsolidadaService, ManualMovementService)
- [X] T042 [P] Verify management command help: `DJANGO_SETTINGS_MODULE=gravitea.settings.test .venv/bin/python manage.py check_account_balance --help` must print usage without error
- [X] T043 [P] Add `@extend_schema` annotations (drf-spectacular, Constitution §XIV) to all ViewSets and Views in backend/apps/cuentas/views/accounts.py: ProducerAccountViewSet (list + retrieve), AccountMovementViewSet (list + retrieve + create), PosicionConsolidadaView (get), StatementView (get) — include summary, description, query parameter schemas, and response serializer references

**GATE G4**: `cat Docs/Tests/spec13-final.status` = PASSED AND `cat Docs/Tests/spec13-regression.status` = PASSED

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundation)**: Depends on Phase 1 — **BLOCKS all user story phases**
- **Phase 3 (US1)**: Depends on Phase 2 (G1 gate) — MVP blocker
- **Phase 4 (US2)**: Depends on Phase 2 (G1 gate) — can start in parallel with US1 after G1
- **Phase 5 (US3)**: Depends on Phase 2; services extend US1 work (T014)
- **Phase 6 (US4)**: Depends on Phase 2 only — independent of US1–US3
- **Phase 7 (US5)**: Depends on Phase 2 only — independent of US1–US4
- **Phase 8 (US6)**: Depends on Phase 2 only — independent of all other stories
- **Phase 9 (Polish)**: Depends on all desired user story phases complete

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2 complete. No dependencies on other stories. Core MVP.
- **US2 (P1)**: Requires Phase 2 complete. No hard dependencies on US1 (reads data, doesn't create it). Can start in parallel.
- **US3 (P2)**: Extends AccountMovementViewSet from US2 (T019). Should complete US2 first.
- **US4 (P2)**: Requires Phase 2 complete. No dependency on US1–US3. Fully independent.
- **US5 (P3)**: Requires Phase 2 complete. No dependency on US1–US4. Fully independent.
- **US6 (P3)**: Requires Phase 2 complete. No dependency on any other story.

### Within Each Wave (Agent Assignments)

```
A1 (Wave 1): T001 → T002 → T003 → T004 → T005+T006 [P] → T007 → T008 → T009+T010+T011 [P]
              │
              └─ GATE G1 ─────────────────────────────────────────────────────┐
                                                                               │
A2 (Wave 2): T012+T013 [P]                                                     ▼
             T014 → T015 → T016                                         A2+A3 can start
             T028 → T029 → T030 → T031 (US4)
             T033 → T034 → T035 (US5)
             T037 (US6)
             T040+T041 [P]

A3 (Wave 3): T017+T018 [P]
             T019+T020 [P] → T021 → T022
             T023 [P]
             T025 → T026 (US3)
             T027 [P] (US4)
             T032 [P] (US5)
             T036 [P] (US6)
             T038 → T039 (sequential: final test run)

A4 (Wave 4): T012+T013 [P] (US1 tests)
             T017 [P] (US2 tests)
             T023+T027 [P] (US3+US4 tests)
             T032+T036 [P] (US5+US6 tests)
             (fixes any failures found during T038/T039 regression run)
```

### Parallel Opportunities

- T005 + T006: Produce independent models simultaneously (different files)
- T009 + T010 + T011: RLS SQL + conftest can be written simultaneously
- T012 + T013: Model tests + integration test conftest can be written simultaneously
- T017 + T018: Serializers + ViewSets have no file overlap initially
- T027 + T032: Different test files for US4 and US5
- T028 + T033: PosicionConsolidadaService + StatementService are in same file but different classes — sequence them
- T040 + T041 + T042 + T043: Independent polish tasks

---

## Parallel Execution Examples

### Wave 1 — Phase 2 Parallelism

```bash
# A1 can work on both models simultaneously:
Task A: "Create ProducerAccount model in backend/apps/cuentas/models/producer_account.py"
Task B: "Create AccountMovement model in backend/apps/cuentas/models/account_movement.py"
# Plus in parallel:
Task C: "Create RLS policies in backend/database/sql/cuentas_rls.sql"
Task D: "Create backend/tests/cuentas/conftest.py with factory fixtures"
```

### Wave 2 — Services Parallelism

```bash
# After G1, A2 can start services while A4 writes tests simultaneously:
Task A: "Create AccountService + CEGDepositService in services/accounts.py"
Task B: "Write test_account_models.py (15 model tests)"
Task C: "Write test_ceg_deposit_integration.py (8 integration tests)"
```

### Wave 3 — API Parallelism

```bash
# Serializers and ViewSets can start simultaneously:
Task A: "Create ProducerAccountSerializer + AccountMovementSerializer"
Task B: "Create ProducerAccountViewSet + AccountMovementViewSet"
# Then sequential:
Task C: "Create urls.py (depends on ViewSets)"
Task D: "Register URL in gravitea/urls.py"
```

---

## Implementation Strategy

### MVP First (US1 Only — ~12 tasks)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundation (T005–T011)
3. Complete Phase 3: US1 — CEG_DEPOSIT trigger (T012–T016)
4. **STOP and VALIDATE**: Confirm a romaneo via API, check account created, check movement exists, check balance updated
5. Run `bash scripts/run-tests-external.sh -n spec13-mvp tests/cuentas/test_ceg_deposit_integration.py`

**MVP is complete when**: Romaneo CONFORME creates ProducerAccount + CEG_DEPOSIT atomically. No API endpoints needed for MVP.

### Incremental Delivery

1. **T001–T011** → Foundation ready (models, migration, RLS)
2. **T012–T016** → US1: Grain deposits work ← **MVP**
3. **T017–T022** → US2: Balance API + movement ledger
4. **T023–T026** → US3: Manual entries
5. **T027–T031** → US4: Consolidated position
6. **T032–T035** → US5: Account statements
7. **T036–T037** → US6: Consistency check
8. **T038–T042** → Full test run + regression check

### 4-Agent Wave Strategy

```
Wave 1 (A1): T001–T011  ← 11 tasks — models, migration, RLS, test infra
Wave 2 (A2): T012–T016, T028, T031, T033–T035, T037, T041  ← services + integration hooks
Wave 3 (A3): T017–T027, T029–T030, T032, T036, T038–T040, T042  ← API layer + all tests
Wave 4 (A4): Fix any test failures from T038 and T039
```

---

## Task Summary

| Phase | Tasks | US | Count |
|-------|-------|----|-------|
| Phase 1: Setup | T001–T004 | — | 4 |
| Phase 2: Foundation | T005–T011 | — | 7 |
| Phase 3: US1 CEG_DEPOSIT | T012–T016 | US1 | 5 |
| Phase 4: US2 Balances API | T017–T022 | US2 | 6 |
| Phase 5: US3 Manual Entries | T023–T026 | US3 | 4 |
| Phase 6: US4 Consolidated Position | T027–T031 | US4 | 5 |
| Phase 7: US5 Account Statement | T032–T035 | US5 | 4 |
| Phase 8: US6 Balance Consistency | T036–T037 | US6 | 2 |
| Phase 9: Polish | T038–T043 | — | 6 |
| **TOTAL** | | | **43** |

**Parallel opportunities identified**: 16 tasks marked [P]
**Test tasks**: T012, T013, T017, T023, T027, T032, T036 (7 test-writing tasks → target 43+ tests) — all authored by A4 in Wave 4 after A3 completes
**Suggested MVP scope**: Phases 1–3 (T001–T016, 16 tasks) — delivers CEG_DEPOSIT auto-credit

---

## Notes

- [P] tasks = different files, no blocking dependencies within the same phase
- All test files use `@pytest.mark.django_db @pytest.mark.accounts` markers
- NEVER run pytest directly inside Claude Code — use `bash scripts/run-tests-external.sh`
- NEVER call `encrypt_value()` manually on a field that uses EncryptedCharField — double-encryption bug
- ALWAYS use `select_for_update()` in get_or_create_account() to prevent race conditions
- The T016 romaneo.py modification MUST move storage_unit validation INSIDE transaction.atomic()
- Commit after each phase checkpoint with descriptive message per project conventions
