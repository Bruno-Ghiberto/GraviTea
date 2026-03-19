"""Tests for ManualMovementService and PosicionConsolidadaService (T023, T027)."""

import pytest
from decimal import Decimal

from django.core.exceptions import ValidationError

from apps.cuentas.models import AccountMovement, ProducerAccount
from apps.cuentas.services.accounts import ManualMovementService
from apps.cuentas.services.statements import PosicionConsolidadaService
from apps.core.encryption.utils import compute_blind_index


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestManualMovementService:
    def test_service_charge_decrements_ars(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        ManualMovementService.create_manual_movement(
            account=account,
            movement_type=AccountMovement.MovementType.SERVICE_CHARGE,
            quantity_kg=Decimal("0.000"),
            ars_amount=Decimal("-5000.000"),
            usd_amount=Decimal("0.000"),
            reference_document="FAC-001",
            notes="Storage fee",
            operator=admin_user,
        )
        account.refresh_from_db()
        assert account.ars_balance == Decimal("-5000.000")

    def test_retiro_decrements_ars(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        ManualMovementService.create_manual_movement(
            account=account,
            movement_type=AccountMovement.MovementType.RETIRO,
            quantity_kg=Decimal("0.000"),
            ars_amount=Decimal("-3000.000"),
            usd_amount=Decimal("0.000"),
            reference_document="RET-001",
            notes="Cash withdrawal",
            operator=admin_user,
        )
        account.refresh_from_db()
        assert account.ars_balance == Decimal("-3000.000")

    def test_service_charge_positive_ars_raises(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        with pytest.raises(ValidationError) as exc_info:
            ManualMovementService.create_manual_movement(
                account=account,
                movement_type=AccountMovement.MovementType.SERVICE_CHARGE,
                quantity_kg=Decimal("0.000"),
                ars_amount=Decimal("100.000"),
                usd_amount=Decimal("0.000"),
                reference_document="FAC-002",
                notes="",
                operator=admin_user,
            )
        assert exc_info.value.code == "sign_violation"

    def test_adjustment_allowed(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        movement = ManualMovementService.create_manual_movement(
            account=account,
            movement_type=AccountMovement.MovementType.ADJUSTMENT,
            quantity_kg=Decimal("0.000"),
            ars_amount=Decimal("1000.000"),
            usd_amount=Decimal("0.000"),
            reference_document="ADJ-001",
            notes="Correction",
            operator=admin_user,
        )
        assert movement.pk is not None
        assert movement.movement_type == AccountMovement.MovementType.ADJUSTMENT

    def test_ceg_deposit_not_manual_type(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        with pytest.raises(ValidationError) as exc_info:
            ManualMovementService.create_manual_movement(
                account=account,
                movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
                quantity_kg=Decimal("100.000"),
                ars_amount=Decimal("0.000"),
                usd_amount=Decimal("0.000"),
                reference_document="",
                notes="",
                operator=admin_user,
            )
        assert exc_info.value.code == "invalid_movement_type"

    def test_retention_deduction_decrements(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        ManualMovementService.create_manual_movement(
            account=account,
            movement_type=AccountMovement.MovementType.RETENTION_DEDUCTION,
            quantity_kg=Decimal("0.000"),
            ars_amount=Decimal("-2000.000"),
            usd_amount=Decimal("0.000"),
            reference_document="RET-D-001",
            notes="Tax retention",
            operator=admin_user,
        )
        account.refresh_from_db()
        assert account.ars_balance == Decimal("-2000.000")

    def test_grain_balance_negative_pre_check(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        # Account starts with grain_balance_kg=0, trying to debit 100 should fail
        with pytest.raises(ValidationError) as exc_info:
            ManualMovementService.create_manual_movement(
                account=account,
                movement_type=AccountMovement.MovementType.ADJUSTMENT,
                quantity_kg=Decimal("-100.000"),
                ars_amount=Decimal("0.000"),
                usd_amount=Decimal("0.000"),
                reference_document="ADJ-002",
                notes="",
                operator=admin_user,
            )
        assert exc_info.value.code == "grain_balance_negative"

    def test_movement_created_atomically(self, producer_account_factory, admin_user):
        account = producer_account_factory()
        ManualMovementService.create_manual_movement(
            account=account,
            movement_type=AccountMovement.MovementType.SERVICE_CHARGE,
            quantity_kg=Decimal("0.000"),
            ars_amount=Decimal("-1000.000"),
            usd_amount=Decimal("0.000"),
            reference_document="FAC-003",
            notes="",
            operator=admin_user,
        )
        assert AccountMovement.objects.filter(producer_account=account).count() == 1
        account.refresh_from_db()
        assert account.ars_balance == Decimal("-1000.000")


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestPosicionConsolidadaService:
    def test_multi_branch_totals_correctly(
        self, producer_account_factory, tenant_context, branch, other_branch
    ):
        cuit = "20-12345678-9"
        a1 = producer_account_factory(cuit=cuit)
        # Create second account at different branch
        a2 = producer_account_factory(
            cuit=cuit,
            branch=other_branch,
            producer_cuit_hash=compute_blind_index(cuit),
        )
        # Set balances
        ProducerAccount.objects.filter(pk=a1.pk).update(grain_balance_kg=Decimal("10000.000"))
        ProducerAccount.objects.filter(pk=a2.pk).update(grain_balance_kg=Decimal("5000.000"))

        result = PosicionConsolidadaService.compute(
            tenant=tenant_context,
            producer_cuit=cuit,
            campaign=a1.campaign,
        )
        assert len(result) == 1  # one grain type
        assert result[0]["total_grain_kg"] == Decimal("15000.000")
        assert len(result[0]["branch_breakdown"]) == 2

    def test_zero_balance_returns_empty(self, tenant_context):
        from apps.acopio.models import CampanaConfig
        from datetime import date

        campaign = CampanaConfig.objects.create(
            tenant=tenant_context,
            campaign_code="EMPTY/TEST",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            is_active=False,
        )
        result = PosicionConsolidadaService.compute(
            tenant=tenant_context,
            producer_cuit="20-99999999-9",
            campaign=campaign,
        )
        assert result == []

    def test_cross_tenant_not_included(
        self, producer_account_factory, tenant_context, other_tenant
    ):
        cuit = "20-12345678-9"
        account = producer_account_factory(cuit=cuit)
        ProducerAccount.objects.filter(pk=account.pk).update(
            grain_balance_kg=Decimal("5000.000")
        )

        # Compute for the same cuit but in a different tenant context
        from apps.core.managers.tenant_bound import set_current_tenant_id, clear_current_tenant_id

        set_current_tenant_id(other_tenant.id)
        try:
            result = PosicionConsolidadaService.compute(
                tenant=other_tenant,
                producer_cuit=cuit,
                campaign=account.campaign,
            )
        finally:
            set_current_tenant_id(tenant_context.id)

        assert result == []

    def test_branch_breakdown_present(
        self, producer_account_factory, tenant_context, branch, other_branch
    ):
        cuit = "20-12345678-9"
        a1 = producer_account_factory(cuit=cuit)
        a2 = producer_account_factory(
            cuit=cuit,
            branch=other_branch,
            producer_cuit_hash=compute_blind_index(cuit),
        )
        ProducerAccount.objects.filter(pk=a1.pk).update(grain_balance_kg=Decimal("8000.000"))
        ProducerAccount.objects.filter(pk=a2.pk).update(grain_balance_kg=Decimal("2000.000"))

        result = PosicionConsolidadaService.compute(
            tenant=tenant_context,
            producer_cuit=cuit,
            campaign=a1.campaign,
        )
        breakdown = result[0]["branch_breakdown"]
        branch_ids = {b["branch_id"] for b in breakdown}
        assert branch.id in branch_ids
        assert other_branch.id in branch_ids
