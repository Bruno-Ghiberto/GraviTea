# Quickstart: Producer Accounts (Spec-13)

**Generated**: 2026-03-19

A rapid-reference guide for developers implementing or integrating with the
Producer Accounts module. Read this before writing any code.

---

## Mental Model (5 minutes)

```
ROMANEO (confirmed reception, third-party grain)
     │
     │ confirmar → CONFORME + transaction.atomic()
     ▼
PRODUCER ACCOUNT (get or create by composite key)
(tenant × producer_cuit × branch × grain_type × campaign)
     │
     │ append immutable entry
     ▼
ACCOUNT MOVEMENT (immutable ledger: what happened and when)
```

**Key invariant**: `ProducerAccount.grain_balance_kg == SUM(AccountMovement.quantity_kg for that account)`
at all times. Never update `grain_balance_kg` without creating a corresponding
`AccountMovement`. Never create an `AccountMovement` without updating the balance.
Both happen in the same `transaction.atomic()` block.

**Own grain exception**: If `romaneo.is_own_grain = True`, no account or movement
is created. Own grain is the acopiador's balance-sheet asset with no producer-facing account.

---

## App Setup

1. INSTALLED_APPS: `"apps.cuentas"` (label: `gravitea_cuentas`)
2. Root URL: `path("api/v1/cuentas/", include("apps.cuentas.urls"))`
3. RLS: Apply `backend/database/sql/cuentas_rls.sql` after migration

```bash
cd backend
.venv/bin/python manage.py migrate
# Then apply RLS via your DB admin tooling
```

---

## The 3 Pitfalls to Avoid

### Pitfall 1: Double-Encryption Bug

```python
# WRONG — EncryptedCharField already encrypts via get_prep_value
account.producer_cuit_encrypted = encrypt_value(plaintext_cuit)  # ← DOUBLE-ENCRYPTED

# CORRECT — assign plaintext; field encrypts at DB write
account.producer_cuit_encrypted = plaintext_cuit
```

### Pitfall 2: Balance Without Movement (or Movement Without Balance)

```python
# WRONG — balance update without corresponding movement
account.grain_balance_kg += kg
account.save()  # ← No audit trail, inconsistency possible

# CORRECT — both in one atomic block
with transaction.atomic():
    AccountMovement.objects.create(...)
    account.grain_balance_kg += kg
    account.save(update_fields=["grain_balance_kg", "updated_at"])
```

### Pitfall 3: Searching CUIT Without Blind Index

```python
# WRONG — cannot search on ciphertext
ProducerAccount.objects.filter(producer_cuit_encrypted=cuit)  # ← always empty

# CORRECT — compute blind index hash first
from apps.core.encryption.utils import compute_blind_index
ProducerAccount.objects.filter(
    tenant=tenant,
    producer_cuit_hash=compute_blind_index(cuit)
)
```

---

## Key Service Functions

```python
# Get or create account (race-safe)
from apps.cuentas.services.accounts import AccountService
account, created = AccountService.get_or_create_account(
    tenant, producer_cuit, branch, grain_type, campaign, operator
)

# Create CEG_DEPOSIT from romaneo (called by A2 in confirmar)
from apps.cuentas.services.accounts import create_ceg_deposit
movement = create_ceg_deposit(romaneo, operator=request.user)

# Create manual movement (SERVICE_CHARGE, RETIRO, RETENTION_DEDUCTION, ADJUSTMENT)
from apps.cuentas.services.accounts import ManualMovementService
movement = ManualMovementService.create_manual_movement(
    account=account,
    movement_type="SERVICE_CHARGE",
    ars_amount=Decimal("-5000.000"),
    reference_document="FAC-2026-00123",
    operator=request.user,
)

# Account statement
from apps.cuentas.services.statements import StatementService
stmt = StatementService.generate(account, date_from, date_to)
# Returns: {opening_balance_kg, opening_ars, opening_usd,
#           movements: [...], closing_balance_kg, closing_ars, closing_usd}

# Posicion consolidada (cross-branch aggregation)
from apps.cuentas.services.statements import PosicionConsolidadaService
posicion = PosicionConsolidadaService.compute(
    tenant, producer_cuit, campaign
)
```

---

## Romaneo confirmar Integration Point

File: `backend/apps/acopio/views/romaneo.py`, method `confirmar` (~line 167).

A2 wraps steps 6-9 in `transaction.atomic()` and adds the CEG_DEPOSIT call:

```python
with transaction.atomic():
    romaneo.status = Romaneo.RomaneoStatus.CONFORME
    romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
    romaneo.save()

    if not romaneo.storage_unit:   # ← validation moves INSIDE atomic
        raise ValidationError(...)

    is_own_grain = False  # MVP default
    create_deposit_from_romaneo(romaneo, romaneo.storage_unit, is_own_grain)

    if not is_own_grain:
        from apps.cuentas.services.accounts import create_ceg_deposit
        create_ceg_deposit(romaneo, operator=request.user)
```

---

## API Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/cuentas/accounts/` | List accounts (filter: `producer_cuit`, `grain_type`, `campaign`, `branch`) |
| `GET` | `/api/v1/cuentas/accounts/{id}/` | Account detail |
| `GET` | `/api/v1/cuentas/accounts/{id}/movements/` | Movement ledger (cursor paginated) |
| `POST` | `/api/v1/cuentas/accounts/{id}/movements/` | Create manual movement |
| `GET` | `/api/v1/cuentas/accounts/{id}/statement/` | Account statement (params: `date_from`, `date_to`) |
| `GET` | `/api/v1/cuentas/posicion-consolidada/` | Consolidated position (params: `producer_cuit`, `campaign_id`) |
| `PATCH/DELETE` | `/api/v1/cuentas/accounts/{id}/movements/{id}/` | → 405 (append-only) |

---

## Test Fixtures

```python
# tests/cuentas/conftest.py provides:
@pytest.fixture
def producer_account_factory(tenant, branch, grain_type, campaign):
    def make(cuit="20-12345678-9", **kwargs):
        return ProducerAccount.objects.create(
            tenant=tenant, branch=branch,
            grain_type=grain_type, campaign=campaign,
            producer_cuit_encrypted=cuit,
            producer_cuit_hash=compute_blind_index(cuit),
            grain_balance_kg=Decimal("0.000"),
            ars_balance=Decimal("0.000"),
            usd_balance=Decimal("0.000"),
            created_by=...,
            **kwargs,
        )
    return make

@pytest.fixture
def romaneo_conforme_factory(...)  # creates full CONFORME romaneo with QA + merma + storage_unit
```

---

## Management Command

```bash
# Check balance consistency (stored vs ledger)
cd backend
.venv/bin/python manage.py check_account_balance
# Output: "OK: 0 discrepancies" or "ERROR: Account {id} grain_balance_kg stored=X expected=Y"

# Run for specific tenant
.venv/bin/python manage.py check_account_balance --tenant <tenant_id>
```
