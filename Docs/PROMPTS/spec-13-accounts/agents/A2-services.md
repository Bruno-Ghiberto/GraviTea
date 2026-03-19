# Agent A2: Services, Romaneo Hook, Statements & Management Command

**Agent Type**: `backend-architect`
**Model**: Sonnet 4.6
**Mission**: Implement all service layer functions (AccountService, CEGDepositService,
ManualMovementService, StatementService, PosicionConsolidadaService), the critical romaneo
confirmar integration hook, and the balance consistency management command.
Wave 2 — begins after GATE G1 passes.

---

## Context Files — Read FIRST

1. `Docs/PROMPTS/spec-13-accounts/13-implement.md` — Orchestration protocol, confirmar bug details, all patterns
2. `specs/013-producer-accounts/data-model.md` — Entity fields, movement types, state transitions
3. `specs/013-producer-accounts/quickstart.md` — Service function signatures, invariants, pitfalls
4. `specs/013-producer-accounts/contracts/accounts-api.md` — Statement and posicion-consolidada response shapes
5. `specs/013-producer-accounts/tasks.md` — Task descriptions (T014–T016, T024, T028, T033, T037, T040–T041)

---

## Assigned Tasks (Wave 2)

| Task | Description |
|------|-------------|
| T014 | Create `backend/apps/cuentas/services/accounts.py` — AccountService, CEGDepositService, ManualMovementService |
| T015 | Create/update `backend/apps/cuentas/services/__init__.py` — export create_ceg_deposit, AccountService |
| T016 | **CRITICAL** Modify `backend/apps/acopio/views/romaneo.py` confirmar action — wrap in transaction.atomic() + add CEG_DEPOSIT hook |
| T024 | Add ManualMovementService to `backend/apps/cuentas/services/accounts.py` with grain balance pre-check |
| T028 | Create `backend/apps/cuentas/services/statements.py` — PosicionConsolidadaService |
| T033 | Add StatementService to `backend/apps/cuentas/services/statements.py` |
| T037 | Create `backend/apps/cuentas/management/commands/check_account_balance.py` |
| T040 | Apply RLS policies: `psql $DATABASE_URL -f backend/database/sql/cuentas_rls.sql` |
| T041 | Update `backend/apps/cuentas/services/__init__.py` — export all public service functions |

---

## Files to Create

| File | Description |
|------|-------------|
| `backend/apps/cuentas/services/accounts.py` | AccountService, CEGDepositService, ManualMovementService |
| `backend/apps/cuentas/services/statements.py` | StatementService, PosicionConsolidadaService |
| `backend/apps/cuentas/management/commands/check_account_balance.py` | Balance consistency command |

## Files to Modify

| File | What Changes |
|------|--------------|
| `backend/apps/acopio/views/romaneo.py` | Wrap confirmar action in `transaction.atomic()`, add CEG_DEPOSIT hook |
| `backend/apps/cuentas/services/__init__.py` | Export all public service functions |

---

## Domain Knowledge

### RAG Queries (run for additional context)

```bash
cd backend
.venv/bin/python scripts/qdrant/qdrant_search.py -q "Django transaction atomic nested savepoint" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "select_for_update get_or_create race condition" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "romaneo confirmar CONFORME status flow" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "running balance ledger atomic update" -l 5
.venv/bin/python scripts/qdrant/qdrant_search.py -q "Django management command BaseCommand handle" -l 5
```

### Critical Domain Facts (Inlined)

1. **Romaneo confirmar atomicity bug** (T016 is the fix):
   Current code in `backend/apps/acopio/views/romaneo.py` at ~line 246:
   - `romaneo.save()` with status=CONFORME is called BEFORE `storage_unit` validation
   - If `storage_unit` is None, returns 400 but romaneo is ALREADY PERSISTED as CONFORME
   - Spec-13 requires ALL of these inside ONE `transaction.atomic()`:
     1. romaneo.save()
     2. storage_unit validation (raise ValidationError if None)
     3. create_deposit_from_romaneo()
     4. create_ceg_deposit() (if not is_own_grain)

2. **`create_deposit_from_romaneo`** at `backend/apps/acopio/services/storage.py` lines 14-68:
   Has its own inner `transaction.atomic()` with `select_for_update()`. Safe to nest — Django
   uses SAVEPOINT for nested atomics. Do NOT remove the inner atomic.

3. **`is_own_grain` is NOT a Romaneo model field**: It's a local variable in confirmar.
   Default value for MVP: `is_own_grain = False`. When True, skip both create_deposit_from_romaneo
   and create_ceg_deposit entirely.

4. **select_for_update in get_or_create**: Required to prevent duplicate ProducerAccount creation
   under concurrent romaneo confirms for the same producer+branch+grain_type+campaign combination.

5. **Balance update pattern**: ALWAYS use `update_fields=["grain_balance_kg", "updated_at"]` (or
   whichever balance fields changed) — prevents overwriting concurrent changes to other fields.
   `account.grain_balance_kg += kg` in Python followed by `account.save(update_fields=...)`.

6. **StatementService opening balance**: Use `AccountMovement.objects.filter(movement_at__lt=date_from)`
   to compute opening balance (sum of all movements before the period start). Period movements are
   `filter(movement_at__date__range=(date_from, date_to))`.

7. **PosicionConsolidadaService**: Uses Django ORM aggregation (never raw SQL loops). Group by
   grain_type with `values("grain_type_id", "grain_type__code", "grain_type__name")` +
   `annotate(total_grain_kg=Sum("grain_balance_kg"), total_ars=Sum("ars_balance"), total_usd=Sum("usd_balance"))`.
   Branch breakdown is a separate query ordered by branch.

8. **MANUAL_TYPES whitelist**:
   ```python
   MANUAL_TYPES = {
       AccountMovement.MovementType.SERVICE_CHARGE,
       AccountMovement.MovementType.RETIRO,
       AccountMovement.MovementType.RETENTION_DEDUCTION,
       AccountMovement.MovementType.ADJUSTMENT,
   }
   SUPERVISOR_ONLY_TYPES = {AccountMovement.MovementType.ADJUSTMENT}
   ```

9. **Grain balance pre-check** (T024 critical detail):
   BEFORE the atomic block, check:
   ```python
   if quantity_kg < 0 and (account.grain_balance_kg + quantity_kg) < 0:
       raise ValidationError(
           {"quantity_kg": "Grain balance cannot go negative."},
           code="grain_balance_negative"
       )
   ```
   This produces a clean 400 validation error instead of an IntegrityError from the DB CheckConstraint.

10. **Management command exit codes**: `sys.exit(1)` when discrepancies found, `sys.exit(0)` (implicit)
    when clean. Accept `--tenant` optional UUID arg to scope check to a single tenant.

---

## Key Patterns & Constraints

### T016: Romaneo confirmar Refactor (MOST CRITICAL TASK)

**Before editing**: Run gitnexus impact analysis:
```bash
# In a terminal (not this agent):
npx gitnexus analyze  # ensure index is fresh
```

**Current file**: `backend/apps/acopio/views/romaneo.py`

Find the `confirmar` action method. The current structure (BUGGY) is approximately:

```python
# Existing lines ~240-290 (BUGGY — no outer transaction.atomic):
romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
romaneo.status = Romaneo.RomaneoStatus.CONFORME
romaneo.save()                        # ← saved before storage_unit check

if not romaneo.storage_unit:          # ← check after save — BUG
    return Response({...}, status=400)

from apps.acopio.services.storage import create_deposit_from_romaneo
create_deposit_from_romaneo(romaneo=romaneo, storage_unit=romaneo.storage_unit, is_own_grain=False)
return Response(RomaneoDetailSerializer(romaneo).data)
```

**Required transformation**:

```python
# CORRECTED — spec-13 fix:
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

with transaction.atomic():
    romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
    romaneo.status = Romaneo.RomaneoStatus.CONFORME
    romaneo.save()

    if not romaneo.storage_unit:
        raise DRFValidationError({"storage_unit": "Must be set before confirming."})

    is_own_grain = False  # MVP default; NOT a Romaneo model field
    from apps.acopio.services.storage import create_deposit_from_romaneo
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

**Constraint**: Do NOT change any other logic in the confirmar action (QA validation, merma calculation,
status machine checks). Only wrap the final save/deposit block in atomic() and add the CEG_DEPOSIT call.

### T014: CEGDepositService Pattern

```python
# backend/apps/cuentas/services/accounts.py
from decimal import Decimal
from django.db import transaction
from apps.cuentas.models import ProducerAccount, AccountMovement
from apps.core.encryption.utils import compute_blind_index


class AccountService:
    @staticmethod
    def get_or_create_account(tenant, producer_cuit: str, branch, grain_type, campaign, operator):
        """Race-safe get_or_create using select_for_update + blind index."""
        cuit_hash = compute_blind_index(producer_cuit)
        with transaction.atomic():
            account, created = ProducerAccount.objects.select_for_update().get_or_create(
                tenant=tenant,
                producer_cuit_hash=cuit_hash,
                branch=branch,
                grain_type=grain_type,
                campaign=campaign,
                defaults={
                    "producer_cuit_encrypted": producer_cuit,
                    "grain_balance_kg": Decimal("0.000"),
                    "ars_balance": Decimal("0.000"),
                    "usd_balance": Decimal("0.000"),
                    "is_active": True,
                    "created_by": operator,
                }
            )
        return account, created


class CEGDepositService:
    @staticmethod
    def create_ceg_deposit(romaneo, operator):
        """Called from within romaneo confirmar's outer transaction.atomic()."""
        producer_cuit = romaneo.producer_cuit  # plaintext via EncryptedCharField
        cuit_hash = compute_blind_index(producer_cuit)

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

### T024: ManualMovementService Pattern

```python
MANUAL_TYPES = frozenset({
    AccountMovement.MovementType.SERVICE_CHARGE,
    AccountMovement.MovementType.RETIRO,
    AccountMovement.MovementType.RETENTION_DEDUCTION,
    AccountMovement.MovementType.ADJUSTMENT,
})
SUPERVISOR_ONLY_TYPES = frozenset({AccountMovement.MovementType.ADJUSTMENT})


class ManualMovementService:
    @staticmethod
    def create_manual_movement(
        account, movement_type, quantity_kg, ars_amount, usd_amount,
        reference_document, notes, operator
    ):
        from decimal import Decimal

        # 1. Type whitelist
        if movement_type not in MANUAL_TYPES:
            raise ValidationError(
                {"movement_type": f"{movement_type} is not a manually-creatable type."},
                code="invalid_movement_type"
            )

        # 2. Sign convention
        if movement_type in (
            AccountMovement.MovementType.SERVICE_CHARGE,
            AccountMovement.MovementType.RETENTION_DEDUCTION,
        ) and ars_amount > 0:
            raise ValidationError(
                {"ars_amount": "Must be zero or negative for this movement type."},
                code="sign_violation"
            )
        if movement_type == AccountMovement.MovementType.RETIRO:
            if ars_amount > 0 or usd_amount > 0:
                raise ValidationError(
                    {"ars_amount": "Retiro must have non-positive amounts."},
                    code="sign_violation"
                )

        # 3. Pre-check grain balance (produces clean 400 vs IntegrityError)
        if quantity_kg < 0 and (account.grain_balance_kg + quantity_kg) < 0:
            raise ValidationError(
                {"quantity_kg": "Grain balance cannot go negative."},
                code="grain_balance_negative"
            )

        # 4. Atomic: create movement + update balance
        with transaction.atomic():
            movement = AccountMovement.objects.create(
                tenant=account.tenant,
                producer_account=account,
                movement_type=movement_type,
                quantity_kg=quantity_kg,
                ars_amount=ars_amount,
                usd_amount=usd_amount,
                reference_document=reference_document or "",
                notes=notes or "",
                created_by=operator,
            )
            account.grain_balance_kg += quantity_kg
            account.ars_balance += ars_amount
            account.usd_balance += usd_amount
            account.save(update_fields=["grain_balance_kg", "ars_balance", "usd_balance", "updated_at"])

        return movement
```

### T028/T033: Statement and Posicion Services Skeleton

```python
# backend/apps/cuentas/services/statements.py
from django.db.models import Sum
from apps.cuentas.models import ProducerAccount, AccountMovement
from apps.core.encryption.utils import compute_blind_index


class PosicionConsolidadaService:
    @staticmethod
    def compute(tenant, producer_cuit: str, campaign):
        cuit_hash = compute_blind_index(producer_cuit)
        accounts = ProducerAccount.objects.filter(
            tenant=tenant,
            producer_cuit_hash=cuit_hash,
            campaign=campaign,
            is_active=True,
        ).select_related("grain_type", "branch")

        # Group by grain_type
        summary = accounts.values(
            "grain_type_id", "grain_type__code", "grain_type__name"
        ).annotate(
            total_grain_kg=Sum("grain_balance_kg"),
            total_ars=Sum("ars_balance"),
            total_usd=Sum("usd_balance"),
        )
        # Branch breakdown per grain_type
        result = []
        for row in summary:
            branches = accounts.filter(grain_type_id=row["grain_type_id"]).values(
                "branch_id", "branch__name", "grain_balance_kg", "ars_balance", "usd_balance"
            )
            result.append({**row, "branch_breakdown": list(branches)})
        return result


class StatementService:
    @staticmethod
    def generate(account, date_from, date_to):
        from decimal import Decimal

        # Opening balance = sum of all movements before date_from
        pre = AccountMovement.objects.filter(
            producer_account=account,
            movement_at__lt=date_from,
        ).aggregate(
            grain=Sum("quantity_kg"),
            ars=Sum("ars_amount"),
            usd=Sum("usd_amount"),
        )
        opening_grain = pre["grain"] or Decimal("0.000")
        opening_ars = pre["ars"] or Decimal("0.000")
        opening_usd = pre["usd"] or Decimal("0.000")

        # Period movements
        period_mvts = list(
            AccountMovement.objects.filter(
                producer_account=account,
                movement_at__date__range=(date_from, date_to),
            ).order_by("movement_at").select_related("romaneo", "created_by")
        )

        # Compute closing
        grain_delta = sum((m.quantity_kg for m in period_mvts), Decimal("0.000"))
        ars_delta = sum((m.ars_amount for m in period_mvts), Decimal("0.000"))
        usd_delta = sum((m.usd_amount for m in period_mvts), Decimal("0.000"))

        return {
            "opening_balance_kg": opening_grain,
            "opening_ars": opening_ars,
            "opening_usd": opening_usd,
            "movements": period_mvts,
            "closing_balance_kg": opening_grain + grain_delta,
            "closing_ars": opening_ars + ars_delta,
            "closing_usd": opening_usd + usd_delta,
        }
```

### T037: Management Command Pattern

```python
# backend/apps/cuentas/management/commands/check_account_balance.py
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.cuentas.models import ProducerAccount, AccountMovement


class Command(BaseCommand):
    help = "Check ProducerAccount stored balances against AccountMovement ledger sums."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", type=str, help="UUID of tenant to check (optional).")

    def handle(self, *args, **options):
        qs = ProducerAccount.all_objects.all()  # use AllObjectsManager for admin scan
        if options["tenant"]:
            qs = qs.filter(tenant_id=options["tenant"])

        discrepancies = 0
        for account in qs.iterator():
            agg = AccountMovement.objects.filter(producer_account=account).aggregate(
                exp_grain=Sum("quantity_kg"),
                exp_ars=Sum("ars_amount"),
                exp_usd=Sum("usd_amount"),
            )
            exp_grain = agg["exp_grain"] or Decimal("0.000")
            exp_ars = agg["exp_ars"] or Decimal("0.000")
            exp_usd = agg["exp_usd"] or Decimal("0.000")

            if account.grain_balance_kg != exp_grain:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} grain_balance_kg "
                        f"stored={account.grain_balance_kg} expected={exp_grain}"
                    )
                )
                discrepancies += 1
            if account.ars_balance != exp_ars:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} ars_balance "
                        f"stored={account.ars_balance} expected={exp_ars}"
                    )
                )
                discrepancies += 1
            if account.usd_balance != exp_usd:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} usd_balance "
                        f"stored={account.usd_balance} expected={exp_usd}"
                    )
                )
                discrepancies += 1

        if discrepancies == 0:
            self.stdout.write(self.style.SUCCESS("OK: 0 discrepancies"))
        else:
            sys.exit(1)
```

---

## GATE G2 Verification

After all tasks complete:

```bash
cd backend
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.accounts import create_ceg_deposit; print('OK')"

DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.cuentas.services.statements import StatementService; print('OK')"

# Compile check on modified romaneo.py:
DJANGO_SETTINGS_MODULE=gravitea.settings.test \
  .venv/bin/python -c "from apps.acopio.views.romaneo import RomaneoViewSet; print('OK')"
```

Report GATE G2 PASSED to orchestrator.

---

## NEVER

- NEVER remove or bypass the inner `transaction.atomic()` inside `create_deposit_from_romaneo` (storage.py)
- NEVER modify any logic in confirmar other than wrapping the final save/deposit block
- NEVER use `all_objects` manager in service layer (only in management command with explicit admin intent)
- NEVER update balances without a corresponding AccountMovement in the same atomic block
- NEVER create an AccountMovement without updating the corresponding account balance in the same atomic block
- NEVER read full research PDFs — use RAG queries above
- NEVER run pytest directly — tests are A4's responsibility via `scripts/run-tests-external.sh`
