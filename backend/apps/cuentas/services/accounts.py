from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.encryption.utils import compute_blind_index
from apps.cuentas.models import AccountMovement, ProducerAccount


class AccountService:
    @staticmethod
    def get_or_create_account(
        tenant, producer_cuit: str, branch, grain_type, campaign, operator
    ):
        """Race-safe get_or_create using select_for_update + blind index."""
        cuit_hash = compute_blind_index(producer_cuit)
        with transaction.atomic():
            account, created = (
                ProducerAccount.objects.select_for_update().get_or_create(
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
                    },
                )
            )
        return account, created


class CEGDepositService:
    @staticmethod
    def create_ceg_deposit(romaneo, operator):
        """Called from within romaneo confirmar's outer transaction.atomic()."""
        producer_cuit = romaneo.producer_cuit
        cuit_hash = compute_blind_index(producer_cuit)

        with transaction.atomic():
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
                },
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


MANUAL_TYPES = frozenset(
    {
        AccountMovement.MovementType.SERVICE_CHARGE,
        AccountMovement.MovementType.RETIRO,
        AccountMovement.MovementType.RETENTION_DEDUCTION,
        AccountMovement.MovementType.ADJUSTMENT,
    }
)
SUPERVISOR_ONLY_TYPES = frozenset({AccountMovement.MovementType.ADJUSTMENT})


class ManualMovementService:
    @staticmethod
    def create_manual_movement(
        account,
        movement_type,
        quantity_kg,
        ars_amount,
        usd_amount,
        reference_document,
        notes,
        operator,
    ):
        # 1. Type whitelist
        if movement_type not in MANUAL_TYPES:
            raise ValidationError(
                f"{movement_type} is not a manually-creatable type.",
                code="invalid_movement_type",
            )

        # 2. Sign convention
        if (
            movement_type
            in (
                AccountMovement.MovementType.SERVICE_CHARGE,
                AccountMovement.MovementType.RETENTION_DEDUCTION,
            )
            and ars_amount > 0
        ):
            raise ValidationError(
                "Must be zero or negative for this movement type.",
                code="sign_violation",
            )
        if movement_type == AccountMovement.MovementType.RETIRO:
            if ars_amount > 0 or usd_amount > 0:
                raise ValidationError(
                    "Retiro must have non-positive amounts.",
                    code="sign_violation",
                )

        # 3. Pre-check grain balance (produces clean 400 vs IntegrityError)
        if quantity_kg < 0 and (account.grain_balance_kg + quantity_kg) < 0:
            raise ValidationError(
                "Grain balance cannot go negative.",
                code="grain_balance_negative",
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
            account.save(
                update_fields=[
                    "grain_balance_kg",
                    "ars_balance",
                    "usd_balance",
                    "updated_at",
                ]
            )

        return movement
