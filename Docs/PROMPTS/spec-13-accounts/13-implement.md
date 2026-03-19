# Implementation Context: Producer Accounts (Spec-13)

**Branch**: `013-producer-accounts` | **Date**: 2026-03-19
**Spec**: `specs/013-producer-accounts/spec.md`
**Plan**: `specs/013-producer-accounts/plan.md`
**Tasks**: `specs/013-producer-accounts/tasks.md`

---

## Mission

Implement the producer current account (`cuenta corriente de productores`) module as new Django app
`apps.cuentas` (label: `gravitea_cuentas`). The module provides dual-ledger tracking (grain kg + ARS + USD),
an immutable `AccountMovement` ledger, automatic CEG_DEPOSIT triggering from romaneo confirmation,
manual entry API, consolidated position aggregation, account statements, encrypted CUIT search,
and RLS-enforced tenant isolation.

---

## Agent Team Orchestration Protocol

### MANDATORY: tmux Multi-Pane Spawning

Before spawning agents, create 4-pane tmux layout:

```bash
tmux new-session -d -s spec13 -n impl
tmux split-window -h -t spec13:impl
tmux split-window -v -t spec13:impl.0
tmux split-window -v -t spec13:impl.1
# Pane 0: A1 Models   | Pane 1: A2 Services
# Pane 2: A3 API      | Pane 3: A4 Tests
```

Spawn each agent by giving its instruction file as first task:

```text
A1: "Read Docs/PROMPTS/spec-13-accounts/agents/A1-models.md and complete your assigned tasks."
A2: "Read Docs/PROMPTS/spec-13-accounts/agents/A2-services.md and await GATE G1 clearance."
A3: "Read Docs/PROMPTS/spec-13-accounts/agents/A3-api.md and await GATE G2 clearance."
A4: "Read Docs/PROMPTS/spec-13-accounts/agents/A4-tests.md and await GATE G3 clearance."
```

---

## Wave Execution Order

```
Wave 1: A1 — App boilerplate + Models + Migration + RLS + conftest fixtures
         │  Tasks: T001–T011
         │
         └─ GATE G1: models importable; no missing migrations
            cd backend
            DJANGO_SETTINGS_MODULE=gravitea.settings.test \
              .venv/bin/python -c "from apps.cuentas.models import ProducerAccount, AccountMovement; print('OK')"
            .venv/bin/python manage.py makemigrations --check --dry-run
            Both must print OK / exit 0 before Wave 2 starts.
         │
         ▼
Wave 2: A2 — Services + Romaneo integration hook + Statements + Management command
         │  Tasks: T014–T016, T024, T028, T033, T037, T040–T041
         │
         └─ GATE G2: services importable; romaneo integration compiles
            DJANGO_SETTINGS_MODULE=gravitea.settings.test \
              .venv/bin/python -c "from apps.cuentas.services.accounts import create_ceg_deposit; print('OK')"
            DJANGO_SETTINGS_MODULE=gravitea.settings.test \
              .venv/bin/python -c "from apps.cuentas.services.statements import StatementService; print('OK')"
         │
         ▼
Wave 3: A3 — Serializers + ViewSets + URL routing + Final test run + OpenAPI
         │  Tasks: T018–T022, T025–T026, T029–T031, T034–T035, T038–T039, T042–T043
         │
         └─ GATE G3: URL routes registered; endpoints respond
            DJANGO_SETTINGS_MODULE=gravitea.settings.test \
              .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(f'{len(urlpatterns)} routes')"
         │
         ▼
Wave 4: A4 — Full test suite write + fix failures
         │  Tasks: T012–T013, T017, T023, T027, T032, T036
         │  (runs concurrently with Wave 3 where possible; fixes any failures after T038/T039)
         │
         └─ GATE G4: All tests PASSED + acopio regression clean
            bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/
            cat Docs/Tests/spec13-final.status    → PASSED
            bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
            cat Docs/Tests/spec13-regression.status  → PASSED
```

---

## Agent Task Assignments

| Agent | Type | Wave | Tasks | Scope |
|-------|------|------|-------|-------|
| A1 | python-expert | 1 | T001–T011 | App boilerplate, ProducerAccount, AccountMovement, migration, RLS, conftest |
| A2 | backend-architect | 2 | T014–T016, T024, T028, T033, T037, T040–T041 | Services, romaneo hook, statements, management cmd |
| A3 | backend-architect | 3 | T018–T022, T025–T026, T029–T031, T034–T035, T038–T039, T042–T043 | Serializers, ViewSets, URLs, final runs, OpenAPI |
| A4 | quality-engineer | 4 | T012–T013, T017, T023, T027, T032, T036 | Full test suite (43+ tests) |

---

## Files to Create / Modify

### New Files

| File | Agent | Description |
|------|-------|-------------|
| `backend/apps/cuentas/__init__.py` | A1 | Empty package init |
| `backend/apps/cuentas/apps.py` | A1 | CuentasConfig |
| `backend/apps/cuentas/models/__init__.py` | A1 | Re-exports |
| `backend/apps/cuentas/models/producer_account.py` | A1 | ProducerAccount model |
| `backend/apps/cuentas/models/account_movement.py` | A1 | AccountMovement (IMMUTABLE) |
| `backend/apps/cuentas/admin.py` | A1 | Admin registrations |
| `backend/apps/cuentas/migrations/0001_producer_accounts.py` | A1 | Initial migration |
| `backend/apps/cuentas/services/__init__.py` | A1/A2 | Service exports |
| `backend/apps/cuentas/services/accounts.py` | A2 | AccountService, CEGDepositService, ManualMovementService |
| `backend/apps/cuentas/services/statements.py` | A2 | StatementService, PosicionConsolidadaService |
| `backend/apps/cuentas/management/__init__.py` | A1 | Empty init |
| `backend/apps/cuentas/management/commands/__init__.py` | A1 | Empty init |
| `backend/apps/cuentas/management/commands/check_account_balance.py` | A2 | Balance consistency command |
| `backend/database/sql/cuentas_rls.sql` | A1 | RLS policies |
| `backend/apps/cuentas/serializers/__init__.py` | A3 | Serializer exports |
| `backend/apps/cuentas/serializers/accounts.py` | A3 | All serializers |
| `backend/apps/cuentas/views/__init__.py` | A3 | ViewSet exports |
| `backend/apps/cuentas/views/accounts.py` | A3 | ProducerAccountViewSet, AccountMovementViewSet, APIViews |
| `backend/apps/cuentas/urls.py` | A3 | URL routing |
| `backend/tests/cuentas/__init__.py` | A1 | Empty test package |
| `backend/tests/cuentas/conftest.py` | A1 | Test fixtures |
| `backend/tests/cuentas/test_account_models.py` | A4 | ~15 model tests |
| `backend/tests/cuentas/test_account_api.py` | A4 | ~12 API tests |
| `backend/tests/cuentas/test_account_services.py` | A4 | ~8 service tests |
| `backend/tests/cuentas/test_ceg_deposit_integration.py` | A4 | ~8 integration tests |

### Modified Files

| File | Agent | What Changes |
|------|-------|--------------|
| `backend/gravitea/settings/base.py` | A1 | Add `"apps.cuentas"` to INSTALLED_APPS |
| `backend/pytest.ini` (or `setup.cfg`) | A1 | Add `accounts` to markers list |
| `backend/apps/acopio/views/romaneo.py` | A2 | Wrap confirmar in transaction.atomic(); add CEG_DEPOSIT hook |
| `backend/gravitea/urls.py` | A3 | Add cuentas URL include |

---

## Critical Code Patterns

### 1. ProducerAccount Model Skeleton

```python
# backend/apps/cuentas/models/producer_account.py
from django.core.validators import RegexValidator
from apps.core.models import TenantBoundModel
from apps.core.encryption.fields import EncryptedCharField, BlindIndexField
from apps.core.encryption.utils import compute_blind_index

class ProducerAccount(TenantBoundModel):
    producer_cuit_encrypted = EncryptedCharField(
        max_length=500,
        validators=[RegexValidator(r'^\d{2}-\d{8}-\d$', message="CUIT must be in format XX-XXXXXXXX-X")]
    )
    producer_cuit_hash = BlindIndexField(max_length=64)
    branch = models.ForeignKey("core.Branch", on_delete=models.PROTECT, related_name="producer_accounts")
    grain_type = models.ForeignKey("acopio.GrainType", on_delete=models.PROTECT, related_name="producer_accounts")
    campaign = models.ForeignKey("acopio.CampanaConfig", on_delete=models.PROTECT, related_name="producer_accounts")
    grain_balance_kg = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0.000"))
    ars_balance = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0.000"))
    usd_balance = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0.000"))
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey("core.AppUser", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.producer_cuit_hash and self.producer_cuit_encrypted:
            self.producer_cuit_hash = compute_blind_index(self.producer_cuit_encrypted)
        super().save(*args, **kwargs)

    class Meta:
        db_table = "cuentas_produceraccount"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "producer_cuit_hash", "branch", "grain_type", "campaign"],
                name="unique_producer_account_per_dimension",
            ),
            models.CheckConstraint(
                check=models.Q(grain_balance_kg__gte=0),
                name="grain_balance_kg_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "producer_cuit_hash"]),
            models.Index(fields=["tenant", "branch", "campaign"]),
        ]
```

### 2. AccountMovement Immutability Pattern

```python
# backend/apps/cuentas/models/account_movement.py
class AccountMovement(TenantBoundModel):
    class MovementType(models.TextChoices):
        CEG_DEPOSIT = "CEG_DEPOSIT", "Grain Deposit (CEG)"
        LPG_SALE = "LPG_SALE", "Grain Sale (LPG)"
        FIJACION = "FIJACION", "Price Fixation"
        RETIRO = "RETIRO", "Cash Withdrawal"
        SERVICE_CHARGE = "SERVICE_CHARGE", "Service Charge"
        CANJE_GRAIN_DEBIT = "CANJE_GRAIN_DEBIT", "Canje Grain Debit"
        CANJE_INPUT_CREDIT = "CANJE_INPUT_CREDIT", "Canje Input Credit"
        RETENTION_DEDUCTION = "RETENTION_DEDUCTION", "Tax Retention"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment (Supervisor)"

    # ... fields ...
    movement_at = models.DateTimeField(auto_now_add=True)
    # NOTE: NO updated_at — immutable model

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AccountMovement is immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AccountMovement is immutable and cannot be deleted.")

    class Meta:
        db_table = "cuentas_accountmovement"
        indexes = [
            models.Index(fields=["producer_account", "-movement_at"]),
            models.Index(fields=["tenant", "movement_type"]),
        ]
        ordering = ["-movement_at"]
```

### 3. CEG_DEPOSIT Service Pattern

```python
# backend/apps/cuentas/services/accounts.py
from django.db import transaction
from apps.core.encryption.utils import compute_blind_index

class CEGDepositService:
    @staticmethod
    def create_ceg_deposit(romaneo, operator):
        """Called from romaneo confirmar within outer transaction.atomic()."""
        producer_cuit = romaneo.producer_cuit  # plaintext from encrypted field
        cuit_hash = compute_blind_index(producer_cuit)

        # select_for_update prevents race conditions on get_or_create
        account, _ = ProducerAccount.objects.select_for_update().get_or_create(
            tenant=romaneo.tenant,
            producer_cuit_hash=cuit_hash,
            branch=romaneo.branch,
            grain_type=romaneo.grain_type,
            campaign=romaneo.campaign,
            defaults={
                "producer_cuit_encrypted": producer_cuit,
                "grain_balance_kg": Decimal("0.000"),
                "ars_balance": Decimal("0.000"),
                "usd_balance": Decimal("0.000"),
                "is_active": True,
                "created_by": operator,
            }
        )

        kg = romaneo.peso_neto_conforme_kg
        AccountMovement.objects.create(
            tenant=romaneo.tenant,
            producer_account=account,
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
            quantity_kg=kg,
            romaneo=romaneo,
            created_by=operator,
        )
        account.grain_balance_kg += kg
        account.save(update_fields=["grain_balance_kg", "updated_at"])
        return account


def create_ceg_deposit(romaneo, operator):
    """Module-level shortcut for romaneo integration."""
    return CEGDepositService.create_ceg_deposit(romaneo, operator)
```

### 4. Romaneo confirmar Integration (CRITICAL — A2 Modifies This)

**File**: `backend/apps/acopio/views/romaneo.py` — `confirmar` action (~line 166)

**CURRENT BUG** (pre-spec-13): romaneo saved as CONFORME BEFORE storage_unit validation.
If storage_unit check fails (line ~258), romaneo is already persisted as CONFORME — inconsistent state.

**REQUIRED CHANGE**:
```python
# BEFORE (buggy):
romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
romaneo.status = Romaneo.RomaneoStatus.CONFORME
romaneo.save()                    # ← CONFORME saved unconditionally
if not romaneo.storage_unit:      # ← check AFTER save — bug!
    return Response({...}, status=400)
create_deposit_from_romaneo(...)
return Response(...)

# AFTER (spec-13 fix):
with transaction.atomic():
    romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
    romaneo.status = Romaneo.RomaneoStatus.CONFORME
    romaneo.save()

    if not romaneo.storage_unit:      # ← validation INSIDE atomic — rolls back if fails
        raise ValidationError({"storage_unit": "Must be set before confirming."})

    is_own_grain = False  # MVP default; NOT a Romaneo model field
    create_deposit_from_romaneo(
        romaneo=romaneo,
        storage_unit=romaneo.storage_unit,
        is_own_grain=is_own_grain,
    )

    if not is_own_grain:
        from apps.cuentas.services.accounts import create_ceg_deposit
        create_ceg_deposit(romaneo, operator=request.user)

return Response(RomaneoDetailSerializer(romaneo).data)
```

**Key constraint**: `create_deposit_from_romaneo` (storage.py lines 14-68) has its own inner
`transaction.atomic()` with `select_for_update()`. This is safe to nest — Django uses savepoints
for nested atomics. Do NOT remove the inner atomic from create_deposit_from_romaneo.

### 5. CursorPagination (Constitution §XIII — MANDATORY)

```python
# backend/apps/cuentas/views/accounts.py
from rest_framework.pagination import CursorPagination

class AccountCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 25

class MovementCursorPagination(CursorPagination):
    ordering = "-movement_at"
    page_size = 50

# ProducerAccountViewSet uses AccountCursorPagination
# AccountMovementViewSet uses MovementCursorPagination
# NEVER use PageNumberPagination for these endpoints
```

### 6. Blind Index CUIT Search Pattern

```python
# In ProducerAccountViewSet.get_queryset():
from apps.core.encryption.utils import compute_blind_index

producer_cuit = self.request.query_params.get("producer_cuit")
if producer_cuit:
    qs = qs.filter(producer_cuit_hash=compute_blind_index(producer_cuit))
```

### 7. Manual Movement Sign Conventions

```python
MANUAL_TYPES = {
    AccountMovement.MovementType.SERVICE_CHARGE,
    AccountMovement.MovementType.RETIRO,
    AccountMovement.MovementType.RETENTION_DEDUCTION,
    AccountMovement.MovementType.ADJUSTMENT,
}
SUPERVISOR_ONLY_TYPES = {AccountMovement.MovementType.ADJUSTMENT}

# Sign validation (in ManualMovementService or serializer):
if movement_type in (SERVICE_CHARGE, RETENTION_DEDUCTION) and ars_amount > 0:
    raise ValidationError({"ars_amount": "..."}, code="sign_violation")
if movement_type == RETIRO and ars_amount > 0 and usd_amount > 0:
    raise ValidationError(...)

# Pre-check grain balance BEFORE the atomic block:
if quantity_kg < 0 and (account.grain_balance_kg + quantity_kg) < 0:
    raise ValidationError(
        {"quantity_kg": "Grain balance cannot go negative."},
        code="grain_balance_negative"
    )
```

### 8. URL Routing (A3 — Explicit Nested Routes Required)

```python
# backend/apps/cuentas/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("accounts", ProducerAccountViewSet, basename="produceraccount")

urlpatterns = router.urls + [
    # DRF router does NOT auto-nest — explicit nested routes required
    path(
        "accounts/<uuid:pk>/movements/",
        AccountMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="account-movement-list",
    ),
    path(
        "accounts/<uuid:pk>/movements/<uuid:movement_pk>/",
        AccountMovementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="account-movement-detail",
    ),
    path("accounts/<uuid:pk>/statement/", StatementView.as_view(), name="account-statement"),
    path("posicion-consolidada/", PosicionConsolidadaView.as_view(), name="posicion-consolidada"),
]
```

### 9. PATCH/DELETE → 405 Pattern

```python
# In AccountMovementViewSet:
def update(self, request, *args, **kwargs):
    return Response(
        {"detail": "Method not allowed.", "code": "append_only_violation"},
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )

def partial_update(self, request, *args, **kwargs):
    return self.update(request, *args, **kwargs)

def destroy(self, request, *args, **kwargs):
    return Response(
        {"detail": "Method not allowed.", "code": "append_only_violation"},
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )
```

### 10. RLS Policy Pattern

```sql
-- backend/database/sql/cuentas_rls.sql
ALTER TABLE cuentas_produceraccount ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_produceraccount FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS produceraccount_tenant_isolation ON cuentas_produceraccount;
CREATE POLICY produceraccount_tenant_isolation ON cuentas_produceraccount
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

ALTER TABLE cuentas_accountmovement ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_accountmovement FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS accountmovement_tenant_isolation ON cuentas_accountmovement;
CREATE POLICY accountmovement_tenant_isolation ON cuentas_accountmovement
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());
-- NOTE: AccountMovement is immutable — no UPDATE/DELETE grant to gravitea_app
GRANT SELECT, INSERT ON cuentas_accountmovement TO gravitea_app;
```

---

## Testing Protocol

**MANDATORY**: NEVER run pytest directly inside Claude Code.
ALL test runs MUST go through `scripts/run-tests-external.sh`.

```bash
# Per-story checkpoints (run after each wave):
bash scripts/run-tests-external.sh -n spec13-us1 tests/cuentas/test_ceg_deposit_integration.py tests/cuentas/test_account_models.py
bash scripts/run-tests-external.sh -n spec13-us2 tests/cuentas/test_account_api.py
bash scripts/run-tests-external.sh -n spec13-us3 tests/cuentas/test_account_services.py
bash scripts/run-tests-external.sh -n spec13-us4 tests/cuentas/test_account_services.py
bash scripts/run-tests-external.sh -n spec13-us5 tests/cuentas/test_account_api.py
bash scripts/run-tests-external.sh -n spec13-us6 tests/cuentas/test_account_models.py

# Final gate (Wave 4 GATE G4):
bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/
cat Docs/Tests/spec13-final.status    # → PASSED

# Regression (romaneo confirmar must still pass):
bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
cat Docs/Tests/spec13-regression.status  # → PASSED
```

Poll results:
```bash
# Non-blocking poll loop:
while [ "$(cat Docs/Tests/spec13-final.status 2>/dev/null)" != "PASSED" ]; do sleep 5; done
cat Docs/Tests/spec13-final.summary
grep "FAILED" Docs/Tests/spec13-final.log | head -20
```

---

## Integration Points with Other Specs

| Spec | Integration | Notes |
|------|-------------|-------|
| Spec-10 (Grain Reference) | GrainType FK in ProducerAccount | Read-only FK; no modification to spec-10 models |
| Spec-11 (Romaneo Core) | Romaneo FK in AccountMovement (SET_NULL) | confirmar action modified by A2 |
| Spec-12 (Storage & Position) | create_deposit_from_romaneo called inside same atomic | Inner atomic is safe to nest (Django savepoints) |
| Spec-14+ (LPG/Canje) | LPG_SALE, FIJACION, CANJE_* movement types reserved | Deferred — these types are enum-defined but not yet triggered |

---

## Security Invariants

1. **NEVER expose `producer_cuit_encrypted` or `producer_cuit_hash` in API responses** — only the decrypted `producer_cuit` property
2. **NEVER assign `encrypt_value(plaintext)` to EncryptedCharField** — double-encryption bug. Assign plaintext; field encrypts at `get_prep_value()`
3. **NEVER search on `producer_cuit_encrypted`** — always use `producer_cuit_hash` with `compute_blind_index()`
4. **All account queries scoped by tenant** — TenantBoundManager enforces this; never bypass with `all_objects`
5. **ADJUSTMENT movement type requires supervisor permission** — `request.user.has_permission("settings.admin")`

---

## Done Criteria

All 14 criteria from spec.md must be met:

1. ProducerAccount + AccountMovement models importable, all fields per data-model.md
2. `0001_producer_accounts.py` applies cleanly on a fresh DB
3. `cuentas_rls.sql` defines tenant isolation policies for both tables
4. `gravitea_cuentas` in INSTALLED_APPS; URLs mounted at `/api/v1/cuentas/`
5. Romaneo CONFORME → ProducerAccount + AccountMovement atomically in one transaction
6. AccountMovement.save() and .delete() raise ValueError; API returns 405 on PATCH/DELETE
7. SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION, ADJUSTMENT via API; ADJUSTMENT requires supervisor
8. Posicion Consolidada endpoint returns aggregated balances; never stored
9. Account Statement returns opening balance + movements + closing balance
10. producer_cuit encrypted; equality search via HMAC-SHA256 blind index
11. Cross-tenant queries return empty; tenant can never access another's accounts
12. Management command detects stored vs ledger drift
13. 40+ tests pass via `scripts/run-tests-external.sh`
14. No regressions in `tests/acopio/` (especially romaneo confirmar tests)
