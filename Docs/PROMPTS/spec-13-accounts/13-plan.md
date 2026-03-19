---
spec: "013"
name: "Producer Accounts"
type: Implementation
branch: 013-producer-accounts
created: 2026-03-19
depends_on: [spec-10, spec-11, spec-12]
source_spec: "specs/013-producer-accounts/spec.md"
source_context: "Docs/PROMPTS/spec-13-accounts/13-specify.md"
agents: [A1, A2, A3, A4]
---

# Spec-13: Producer Accounts -- Plan Context

## Agent Team Orchestration Protocol

### tmux Layout (4 panes, required)

```
┌──────────────────────┬──────────────────────┐
│ A1: Models (py-exp)  │ A2: Services (be-ar) │
│                      │                      │
├──────────────────────┼──────────────────────┤
│ A3: API (be-ar)      │ A4: Tests (qa-eng)   │
│                      │                      │
└──────────────────────┴──────────────────────┘
```

### Agent Assignments

| Agent | Subagent Type | Scope | Deliverables |
|-------|---------------|-------|-------------|
| A1 | python-expert | Models + Migration + RLS + App Boilerplate | ProducerAccount, AccountMovement models; 0001 migration; cuentas_rls.sql; apps.py, admin.py, __init__.py |
| A2 | backend-architect | Services + Romaneo Integration | AccountService, CEGDepositService, PosicionConsolidadaService, StatementService, ManualMovementService; romaneo confirmar hook |
| A3 | backend-architect | API Layer + Blind Index | Serializers, ViewSets, URL registration, cursor pagination; encrypted CUIT search |
| A4 | quality-engineer | Full Test Suite | Model, API, service, integration, tenant isolation, immutability, blind index, balance consistency tests |

### Wave Execution Order

```
Wave 1: A1 (Models + App Boilerplate + Migration + RLS)
    │
    │ GATE G1: Models importable + no missing migrations
    ▼
Wave 2: A2 (Services + Romaneo Hook)
    │
    │ GATE G2: Services importable + romaneo integration compiles
    ▼
Wave 3: A3 (API Layer)
    │
    │ GATE G3: URL routes registered + endpoints respond
    ▼
Wave 4: A4 (Tests)
    │
    │ GATE G4: All tests pass via run-tests-external.sh
    ▼
DONE
```

**CRITICAL**: Agents MUST NOT proceed to the next wave until the gate
for the current wave passes. A1 must complete fully before A2 starts.

---

## Component Overview

### New Django App: `backend/apps/cuentas/`

A brand-new app (label: `gravitea_cuentas`) implementing the producer
current account module. Follows the same structure as `apps/acopio/`:

```
backend/apps/cuentas/
├── __init__.py
├── apps.py                      # CuentasConfig(label="gravitea_cuentas")
├── admin.py                     # ProducerAccount + AccountMovement admin
├── models/
│   ├── __init__.py              # Re-exports
│   ├── producer_account.py      # ProducerAccount (TenantBoundModel)
│   └── account_movement.py      # AccountMovement (TenantBoundModel, IMMUTABLE)
├── services/
│   ├── __init__.py
│   ├── accounts.py              # get_or_create_account, create_ceg_deposit
│   └── statements.py            # generate_statement, compute_posicion_consolidada
├── serializers/
│   ├── __init__.py
│   └── accounts.py              # ProducerAccountSerializer, AccountMovementSerializer, ManualMovementSerializer, PosicionConsolidadaSerializer
├── views/
│   ├── __init__.py
│   └── accounts.py              # ProducerAccountViewSet, AccountMovementViewSet, PosicionConsolidadaView, StatementView
├── urls.py                      # DRF router + manual routes
└── management/
    └── commands/
        └── check_account_balance.py  # Balance consistency verification
```

### Models

**ProducerAccount** (TenantBoundModel):
- Dual-ledger: `grain_balance_kg`, `ars_balance`, `usd_balance`
- Encrypted CUIT: `producer_cuit_encrypted` (EncryptedCharField) +
  `producer_cuit_hash` (BlindIndexField)
- Composite uniqueness: `(tenant, producer_cuit_hash, branch, grain_type, campaign)`
- Provenance: `created_at`, `updated_at`, `created_by`

**AccountMovement** (TenantBoundModel, IMMUTABLE):
- 9 movement types: CEG_DEPOSIT, LPG_SALE, FIJACION, RETIRO,
  SERVICE_CHARGE, CANJE_GRAIN_DEBIT, CANJE_INPUT_CREDIT,
  RETENTION_DEDUCTION, ADJUSTMENT
- Immutability enforced via save()/delete() overrides (ValueError)
- `romaneo` FK (SET_NULL) for CEG_DEPOSIT traceability
- `liquidacion` FK DEFERRED (LiquidacionPrimaria does not exist yet)
- Provenance: `created_at`, `created_by` (no updated_at — immutable)

### Services

- **AccountService.get_or_create_account()** — find or create account by
  composite key using blind index lookup + `select_for_update()`
- **CEGDepositService.create_ceg_deposit()** — create CEG_DEPOSIT movement
  + update balance atomically; called from romaneo confirmar
- **ManualMovementService.create_manual_movement()** — create SERVICE_CHARGE,
  RETIRO, RETENTION_DEDUCTION, ADJUSTMENT entries; validate signs + permissions
- **PosicionConsolidadaService.compute()** — SQL aggregation across branches
- **StatementService.generate()** — opening/closing balance + movement list

### API Endpoints (REST API Design v1.0 Section 9)

| Method | Path | ViewSet | Pagination |
|--------|------|---------|-----------|
| GET | `/api/v1/cuentas/accounts/` | ProducerAccountViewSet | Page-number |
| GET | `/api/v1/cuentas/accounts/{id}/` | ProducerAccountViewSet | — |
| GET | `/api/v1/cuentas/accounts/{id}/movements/` | AccountMovementViewSet | Cursor |
| POST | `/api/v1/cuentas/accounts/{id}/movements/` | AccountMovementViewSet (manual types only) | — |
| GET | `/api/v1/cuentas/accounts/{id}/statement/` | StatementView | — |
| GET | `/api/v1/cuentas/posicion-consolidada/` | PosicionConsolidadaView | — |

PATCH/DELETE on movements returns HTTP 405 (`append_only_violation`).
ADJUSTMENT movements require supervisor-level permission check.

---

## Files to Create

| File | Agent | Wave | Description |
|------|-------|------|-------------|
| `backend/apps/cuentas/__init__.py` | A1 | 1 | Empty init |
| `backend/apps/cuentas/apps.py` | A1 | 1 | `CuentasConfig(name="apps.cuentas", label="gravitea_cuentas")` |
| `backend/apps/cuentas/admin.py` | A1 | 1 | Admin registration for both models |
| `backend/apps/cuentas/models/__init__.py` | A1 | 1 | Re-export ProducerAccount, AccountMovement |
| `backend/apps/cuentas/models/producer_account.py` | A1 | 1 | ProducerAccount model |
| `backend/apps/cuentas/models/account_movement.py` | A1 | 1 | AccountMovement model (immutable) |
| `backend/apps/cuentas/migrations/0001_producer_accounts.py` | A1 | 1 | Generated via makemigrations |
| `backend/database/sql/cuentas_rls.sql` | A1 | 1 | RLS policies for both tables |
| `backend/apps/cuentas/services/__init__.py` | A2 | 2 | Empty init |
| `backend/apps/cuentas/services/accounts.py` | A2 | 2 | AccountService, CEGDepositService, ManualMovementService |
| `backend/apps/cuentas/services/statements.py` | A2 | 2 | PosicionConsolidadaService, StatementService |
| `backend/apps/cuentas/serializers/__init__.py` | A3 | 3 | Re-exports |
| `backend/apps/cuentas/serializers/accounts.py` | A3 | 3 | All serializers |
| `backend/apps/cuentas/views/__init__.py` | A3 | 3 | Re-exports |
| `backend/apps/cuentas/views/accounts.py` | A3 | 3 | All viewsets and views |
| `backend/apps/cuentas/urls.py` | A3 | 3 | DRF router + nested routes |
| `backend/apps/cuentas/management/__init__.py` | A2 | 2 | Empty init |
| `backend/apps/cuentas/management/commands/__init__.py` | A2 | 2 | Empty init |
| `backend/apps/cuentas/management/commands/check_account_balance.py` | A2 | 2 | Consistency check command |
| `backend/tests/cuentas/__init__.py` | A4 | 4 | Empty init |
| `backend/tests/cuentas/conftest.py` | A4 | 4 | Account-specific fixtures |
| `backend/tests/cuentas/test_account_models.py` | A4 | 4 | Model + immutability tests |
| `backend/tests/cuentas/test_account_api.py` | A4 | 4 | API endpoint tests |
| `backend/tests/cuentas/test_account_services.py` | A4 | 4 | Service layer tests |
| `backend/tests/cuentas/test_ceg_deposit_integration.py` | A4 | 4 | Romaneo confirmar → account credit integration |

## Files to Modify

| File | Agent | Wave | Change |
|------|-------|------|--------|
| `backend/gravitea/settings/base.py` | A1 | 1 | Add `"apps.cuentas"` to INSTALLED_APPS |
| `backend/gravitea/urls.py` | A3 | 3 | Add `path("cuentas/", include("apps.cuentas.urls"))` |
| `backend/apps/acopio/views/romaneo.py` | A2 | 2 | Wrap confirmar in `transaction.atomic()`; add CEG_DEPOSIT call; add `is_own_grain` conditional |
| `backend/apps/acopio/models/__init__.py` | — | — | No change needed (Romaneo already exported) |

---

## Key Code Patterns

### Pattern 1: App Configuration (follow acopio pattern)

```python
# backend/apps/cuentas/apps.py
from django.apps import AppConfig

class CuentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cuentas"
    label = "gravitea_cuentas"
    verbose_name = "Cuentas Corrientes"
```

### Pattern 2: Encrypted CUIT Fields (follow Supplier pattern)

```python
# In producer_account.py
from apps.core.encryption.fields import EncryptedCharField, BlindIndexField
from apps.core.encryption.utils import compute_blind_index

class ProducerAccount(TenantBoundModel):
    # IMPORTANT: EncryptedCharField auto-encrypts on save (get_prep_value)
    # and auto-decrypts on load (from_db_value). Do NOT call encrypt_value()
    # manually — that would DOUBLE-ENCRYPT the value.
    producer_cuit_encrypted = EncryptedCharField(max_length=500)
    producer_cuit_hash = BlindIndexField(max_length=64)

    @property
    def producer_cuit(self) -> str:
        """Decrypt CUIT on access — EncryptedCharField auto-decrypts."""
        return self.producer_cuit_encrypted

    def save(self, *args, **kwargs):
        # Auto-compute blind index on save.
        # At Python level, self.producer_cuit_encrypted holds PLAINTEXT
        # (EncryptedCharField encrypts only at DB write via get_prep_value).
        # compute_blind_index needs the plaintext to produce a correct hash.
        if self.producer_cuit_encrypted and not self.producer_cuit_hash:
            self.producer_cuit_hash = compute_blind_index(
                self.producer_cuit_encrypted
            )
        super().save(*args, **kwargs)
```

### Pattern 3: Immutable Ledger (follow GrainMovement pattern)

```python
# In account_movement.py
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

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("AccountMovement is immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AccountMovement is immutable and cannot be deleted.")
```

### Pattern 4: Atomic Deposit Service (follow create_deposit_from_romaneo)

```python
# In accounts.py
from decimal import Decimal
from django.db import transaction
from apps.core.encryption.utils import compute_blind_index

def create_ceg_deposit(romaneo, operator):
    with transaction.atomic():
        account, _ = ProducerAccount.objects.select_for_update().get_or_create(
            tenant=romaneo.tenant,
            producer_cuit_hash=compute_blind_index(romaneo.producer_cuit),
            branch=romaneo.branch,
            grain_type=romaneo.grain_type,
            campaign=romaneo.campaign,
            defaults={
                # IMPORTANT: Pass PLAINTEXT to EncryptedCharField — it
                # auto-encrypts via get_prep_value. Do NOT call encrypt_value()
                # manually or the value will be double-encrypted.
                "producer_cuit_encrypted": romaneo.producer_cuit,
                "grain_balance_kg": Decimal("0.000"),
                "ars_balance": Decimal("0.000"),
                "usd_balance": Decimal("0.000"),
                "created_by": operator,
            },
        )

        movement = AccountMovement.objects.create(
            tenant=romaneo.tenant,
            producer_account=account,
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
            quantity_kg=romaneo.peso_neto_conforme_kg,
            romaneo=romaneo,
            created_by=operator,
        )

        account.grain_balance_kg += romaneo.peso_neto_conforme_kg
        account.save(update_fields=["grain_balance_kg", "updated_at"])

    return movement
```

### Pattern 5: Romaneo Confirmar Integration (transaction.atomic wrapping)

```python
# In romaneo.py confirmar action — A2 wraps the entire flow:
@action(detail=True, methods=["post"], url_path="confirmar")
def confirmar(self, request, pk=None):
    romaneo = self.get_object()
    if romaneo.status != Romaneo.RomaneoStatus.ANALIZADO:
        return self._transition_error(romaneo, "confirmar")

    # ... merma calculation, grade assignment (existing code) ...

    with transaction.atomic():
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
        # ... other field updates ...
        romaneo.save()

        # Spec-12: grain deposit
        if not romaneo.storage_unit:
            raise ValueError("storage_unit must be set before confirming")
        is_own_grain = False  # Default; future spec adds determination logic
        create_deposit_from_romaneo(romaneo, romaneo.storage_unit, is_own_grain)

        # Spec-13: producer account credit (only for third-party grain)
        if not is_own_grain:
            from apps.cuentas.services.accounts import create_ceg_deposit
            create_ceg_deposit(romaneo, operator=request.user)

    return Response(RomaneoDetailSerializer(romaneo).data)
```

**IMPORTANT**: The existing `create_deposit_from_romaneo` has its own inner
`transaction.atomic()`. This is safe because Django supports nested savepoints.
The outer `transaction.atomic()` ensures all-or-nothing across the full flow.

### Pattern 6: RLS Policies (follow acopio_rls.sql)

```sql
-- cuentas_rls.sql
ALTER TABLE cuentas_produceraccount ENABLE ROW LEVEL SECURITY;
ALTER TABLE cuentas_produceraccount FORCE ROW LEVEL SECURITY;

CREATE POLICY produceraccount_tenant_isolation ON cuentas_produceraccount
    USING (tenant_id = get_current_tenant_id())
    WITH CHECK (tenant_id = get_current_tenant_id());

-- Same for cuentas_accountmovement
```

**NOTE**: Table name prefix is `cuentas_` (Django default: app_label + model_name
lowercase). But since our label is `gravitea_cuentas`, the table will be
`gravitea_cuentas_produceraccount`. Agent A1 should set `db_table` explicitly in
Meta to use a shorter prefix:
```python
class Meta:
    db_table = "cuentas_produceraccount"
```

### Pattern 7: ViewSet with Blind Index Search

```python
# In views/accounts.py
class ProducerAccountViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProducerAccountSerializer

    def get_queryset(self):
        qs = ProducerAccount.objects.filter(
            tenant_id=self.request.user.tenant_id
        )
        # Blind index CUIT filter
        cuit = self.request.query_params.get("producer_cuit")
        if cuit:
            from apps.core.encryption.utils import compute_blind_index
            blind_idx = compute_blind_index(cuit)
            qs = qs.filter(producer_cuit_hash=blind_idx)
        return qs
```

### Pattern 8: Cursor Pagination for Movements

```python
# Movements use CursorPagination (REST API Design §9.4)
from rest_framework.pagination import CursorPagination

class MovementCursorPagination(CursorPagination):
    ordering = "-movement_at"
    page_size = 50

class AccountMovementViewSet(viewsets.ModelViewSet):
    pagination_class = MovementCursorPagination
    http_method_names = ["get", "post", "head", "options"]  # No PATCH/PUT/DELETE

    MANUAL_TYPES = {
        "SERVICE_CHARGE", "RETIRO", "RETENTION_DEDUCTION", "ADJUSTMENT",
    }
    SUPERVISOR_ONLY_TYPES = {"ADJUSTMENT"}

    def perform_create(self, serializer):
        movement_type = serializer.validated_data["movement_type"]
        if movement_type not in self.MANUAL_TYPES:
            raise ValidationError("Only manual movement types can be created via API.")
        if movement_type in self.SUPERVISOR_ONLY_TYPES:
            if not self.request.user.has_permission("settings.admin"):
                raise PermissionDenied("ADJUSTMENT requires supervisor permission.")
        # ... create movement + update balance atomically ...
```

---

## Checkpoint Gates

### G1: After Wave 1 (A1 — Models)

```bash
# From backend/ directory
cd backend

# 1. Models importable
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.models import ProducerAccount, AccountMovement; print('OK')"

# 2. No missing migrations
.venv/bin/python manage.py makemigrations --check --dry-run

# 3. Migration applies cleanly (dry-run)
.venv/bin/python manage.py migrate --run-syncdb --check 2>&1 | tail -5
```

### G2: After Wave 2 (A2 — Services)

```bash
# 1. Services importable
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.accounts import create_ceg_deposit; print('OK')"

# 2. Statement service importable
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.statements import generate_statement; print('OK')"

# 3. Management command exists
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python manage.py check_account_balance --help 2>&1 | head -3
```

### G3: After Wave 3 (A3 — API)

```bash
# 1. URLs importable and routes registered
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.urls import urlpatterns; print(f'{len(urlpatterns)} routes')"

# 2. URL resolution check
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "
from django.urls import reverse
print(reverse('producer-account-list'))
"
```

### G4: After Wave 4 (A4 — Tests)

```bash
# Run full test suite via external runner
bash scripts/run-tests-external.sh -n spec13-final tests/cuentas/

# Poll status
cat Docs/Tests/spec13-final.status

# Read summary
cat Docs/Tests/spec13-final.summary
```

---

## Testing Protocol

### MANDATORY: Use External Test Runner

**NEVER** run pytest inside Claude Code. Always use the external runner:

```bash
# Launch tests (returns immediately):
bash scripts/run-tests-external.sh -n spec13-wave4 tests/cuentas/

# Poll status (1 line):
cat Docs/Tests/spec13-wave4.status
# → RUNNING | PASSED | FAILED | ERROR

# Read summary when done (~20 lines):
cat Docs/Tests/spec13-wave4.summary

# Debug specific failures only if needed:
grep "FAILED" Docs/Tests/spec13-wave4.log
grep -A10 "test_specific_name" Docs/Tests/spec13-wave4.log

# NEVER read the full .log file
```

### Test Fixture Requirements

The test suite requires these fixtures from `tests/conftest.py`:
- `tenant_context` — sets up tenant isolation context
- `other_tenant` — for cross-tenant isolation tests
- `branch` — default branch fixture
- `other_branch` — for multi-branch posicion consolidada tests

Plus acopio fixtures from `tests/acopio/conftest.py`:
- `grain_type_factory` — creates GrainType instances
- `campana_factory` — creates CampanaConfig instances
- `seed_grain_types` — seeds all 7 grain types

New fixtures in `tests/cuentas/conftest.py`:
- `producer_account_factory` — creates ProducerAccount instances
- `account_movement_factory` — creates AccountMovement instances
- `romaneo_conforme_factory` — creates a CONFORME romaneo with all
  prerequisites (QA, merma, storage_unit) for CEG_DEPOSIT testing

### Test File Structure

| File | Test Count (target) | Scope |
|------|-------------------|-------|
| `test_account_models.py` | ~15 | Model creation, composite uniqueness, immutability, balance fields, encrypted CUIT, blind index |
| `test_account_api.py` | ~12 | List, detail, movements ledger, posicion consolidada, statement, manual entries, 405 on mutations, blind index search |
| `test_account_services.py` | ~8 | get_or_create_account, create_ceg_deposit, manual movement, balance update, posicion consolidada computation |
| `test_ceg_deposit_integration.py` | ~8 | Romaneo confirmar → CEG_DEPOSIT, transaction atomicity, own-grain skip, concurrent creation, balance consistency |
| **Total** | **~43** | All acceptance criteria covered |

### Test Markers

```python
@pytest.mark.django_db
@pytest.mark.accounts    # New marker for spec-13
@pytest.mark.unit        # Fast, no external deps
@pytest.mark.integration # Requires database
@pytest.mark.security    # Tenant isolation, encryption
```

---

## Integration with Existing Code

### Romaneo Confirmar Modification (A2, Wave 2)

The key integration point is `backend/apps/acopio/views/romaneo.py`,
method `confirmar` (line 167). Current flow:

```
1. Validate ANALIZADO status
2. Deserialize ConfirmarSerializer
3. Lookup merma table + calculate merma deductions
4. Create MermaCalculation record
5. Grade assignment + tolerance table pin
6. romaneo.save() with CONFORME status     ← NO transaction wrapping
7. Check storage_unit (validation)
8. create_deposit_from_romaneo()           ← Own inner transaction
9. Return response
```

Spec-13 changes to:

```
1-5. Same (no changes)
6. Wrap steps 6-9 in transaction.atomic():
   6a. romaneo.save() with CONFORME status
   6b. Validate storage_unit
   6c. Determine is_own_grain (default False)
   6d. create_deposit_from_romaneo()       ← Grain deposit
   6e. IF not is_own_grain:
       create_ceg_deposit()                ← Account credit (NEW)
7. Return response
```

**IMPORTANT**: The storage_unit validation MUST move inside the
transaction.atomic() block. If it fails, romaneo should NOT be CONFORME.
Currently it returns 400 AFTER romaneo is already saved as CONFORME — this
is the atomicity bug that spec-13 fixes.

### CONFORME Allowlist Update

Romaneo.save() has a CONFORME allowlist (line 218):
```python
allowed_fields = {
    "tara_kg", "peso_neto_bruto_kg", "ts_tara", "status",
    "storage_unit_id", "grain_lot_id",
}
```

No changes needed — the confirmar action only modifies fields already
in the allowlist. The ProducerAccount creation happens in a separate model.

---

## Done Criteria

### All of the following must be true:

1. **Models**: ProducerAccount and AccountMovement models exist, importable,
   with all fields per Data Model v1.0 Section 6 (plus encryption extensions)
2. **Migration**: `0001_producer_accounts.py` applies cleanly on a fresh DB
3. **RLS**: `cuentas_rls.sql` defines tenant isolation policies for both tables
4. **App registered**: `gravitea_cuentas` in INSTALLED_APPS, URLs mounted at
   `/api/v1/cuentas/`
5. **CEG_DEPOSIT trigger**: Romaneo CONFORME creates ProducerAccount +
   AccountMovement atomically in a single transaction
6. **Immutability**: AccountMovement.save() and .delete() raise ValueError;
   API returns 405 on PATCH/DELETE
7. **Manual entries**: SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION, ADJUSTMENT
   movements can be created via API; ADJUSTMENT requires supervisor permission
8. **Posicion Consolidada**: API endpoint returns aggregated balances across
   branches; no stored entity
9. **Account Statement**: API endpoint returns opening balance + movements +
   closing balance for a date range
10. **Blind Index**: producer_cuit stored encrypted; equality search works via
    HMAC-SHA256 blind index
11. **Tenant Isolation**: Cross-tenant queries return empty results
12. **Balance Consistency**: Management command detects stored vs ledger drift
13. **Tests**: 40+ tests pass via `scripts/run-tests-external.sh`
14. **No regressions**: Existing acopio tests still pass (especially
    romaneo confirmar tests affected by transaction wrapping change)

### Regression Check

After all waves, run the full acopio test suite to verify no regressions:

```bash
bash scripts/run-tests-external.sh -n spec13-regression tests/acopio/
cat Docs/Tests/spec13-regression.status
cat Docs/Tests/spec13-regression.summary
```

If any romaneo tests fail due to the transaction.atomic() wrapping change,
A4 must investigate and fix.
