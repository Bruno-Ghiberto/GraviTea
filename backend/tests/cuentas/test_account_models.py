"""Tests for ProducerAccount and AccountMovement models (T012, T036)."""

import pytest
from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError

from apps.cuentas.models import ProducerAccount, AccountMovement
from apps.core.encryption.utils import compute_blind_index


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestProducerAccountModel:
    def test_create_producer_account(self, producer_account_factory):
        account = producer_account_factory()
        assert account.pk is not None
        assert account.grain_balance_kg == Decimal("0.000")

    def test_blind_index_auto_computed_on_save(self, producer_account_factory):
        cuit = "20-12345678-9"
        account = producer_account_factory(cuit=cuit)
        expected_hash = compute_blind_index(cuit)
        assert account.producer_cuit_hash == expected_hash

    def test_cuit_encrypted_not_stored_as_plaintext(self, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        fresh = ProducerAccount.objects.get(pk=account.pk)
        assert fresh.producer_cuit == "20-12345678-9"

    def test_cuit_format_validation_rejects_invalid(self, producer_account_factory):
        account = producer_account_factory()
        account.producer_cuit_encrypted = "12345"
        with pytest.raises(ValidationError):
            account.full_clean()

    def test_cuit_format_validation_accepts_valid(self, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        account.full_clean()  # should not raise

    def test_grain_balance_kg_non_negative_check_constraint(self, producer_account_factory):
        account = producer_account_factory()
        with pytest.raises(IntegrityError):
            ProducerAccount.objects.filter(pk=account.pk).update(
                grain_balance_kg=Decimal("-1.000")
            )

    def test_composite_uniqueness_constraint(self, producer_account_factory):
        producer_account_factory(cuit="20-12345678-9")
        with pytest.raises(IntegrityError):
            producer_account_factory(cuit="20-12345678-9")

    def test_balance_fields_default_to_zero(self, producer_account_factory):
        account = producer_account_factory()
        assert account.grain_balance_kg == Decimal("0.000")
        assert account.ars_balance == Decimal("0.000")
        assert account.usd_balance == Decimal("0.000")

    def test_created_at_populated(self, producer_account_factory):
        account = producer_account_factory()
        assert account.created_at is not None

    def test_updated_at_populated(self, producer_account_factory):
        account = producer_account_factory()
        assert account.updated_at is not None

    def test_producer_cuit_property(self, producer_account_factory):
        account = producer_account_factory(cuit="20-12345678-9")
        assert account.producer_cuit == "20-12345678-9"


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestAccountMovementImmutability:
    def test_create_movement_succeeds(self, account_movement_factory):
        movement = account_movement_factory()
        assert movement.pk is not None

    def test_save_raises_on_update(self, account_movement_factory):
        movement = account_movement_factory()
        movement.notes = "changed"
        with pytest.raises(ValueError, match="immutable"):
            movement.save()

    def test_delete_raises(self, account_movement_factory):
        movement = account_movement_factory()
        with pytest.raises(ValueError, match="immutable"):
            movement.delete()

    def test_movement_type_choices_count(self):
        assert len(AccountMovement.MovementType.choices) == 9

    def test_no_updated_at_field(self):
        field_names = [f.name for f in AccountMovement._meta.get_fields()]
        assert "updated_at" not in field_names

    def test_all_movement_types_present(self):
        expected = {
            "CEG_DEPOSIT", "LPG_SALE", "FIJACION", "RETIRO",
            "SERVICE_CHARGE", "CANJE_GRAIN_DEBIT", "CANJE_INPUT_CREDIT",
            "RETENTION_DEDUCTION", "ADJUSTMENT",
        }
        actual = {choice[0] for choice in AccountMovement.MovementType.choices}
        assert actual == expected

    def test_quantity_kg_defaults_to_zero(self, account_movement_factory):
        movement = account_movement_factory()
        assert movement.quantity_kg == Decimal("0.000")

    def test_movement_at_auto_set(self, account_movement_factory):
        movement = account_movement_factory()
        assert movement.movement_at is not None

    def test_romaneo_fk_nullable(self, account_movement_factory):
        movement = account_movement_factory(romaneo=None)
        assert movement.pk is not None
        assert movement.romaneo is None


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.unit
class TestCheckAccountBalanceCommand:
    def test_no_discrepancies(self, producer_account_factory, account_movement_factory):
        account = producer_account_factory()
        account_movement_factory(
            account=account,
            quantity_kg=Decimal("100.000"),
            ars_amount=Decimal("50.000"),
        )
        # Update balance to match
        ProducerAccount.objects.filter(pk=account.pk).update(
            grain_balance_kg=Decimal("100.000"),
            ars_balance=Decimal("50.000"),
        )
        out = StringIO()
        call_command("check_account_balance", stdout=out)
        assert "OK: 0 discrepancies" in out.getvalue()

    def test_detects_grain_balance_drift(self, producer_account_factory, account_movement_factory):
        account = producer_account_factory()
        account_movement_factory(
            account=account,
            quantity_kg=Decimal("100.000"),
        )
        # Corrupt grain_balance_kg to wrong value
        ProducerAccount.objects.filter(pk=account.pk).update(
            grain_balance_kg=Decimal("999.000"),
        )
        out = StringIO()
        with pytest.raises(SystemExit):
            call_command("check_account_balance", stdout=out)
        assert "ERROR" in out.getvalue()

    def test_detects_ars_balance_drift(self, producer_account_factory, account_movement_factory):
        account = producer_account_factory()
        account_movement_factory(
            account=account,
            ars_amount=Decimal("-5000.000"),
        )
        # Corrupt ars_balance to wrong value
        ProducerAccount.objects.filter(pk=account.pk).update(
            ars_balance=Decimal("999.000"),
        )
        out = StringIO()
        with pytest.raises(SystemExit):
            call_command("check_account_balance", stdout=out)
        assert "ERROR" in out.getvalue()

    def test_exit_code_1_on_discrepancy(self, producer_account_factory, account_movement_factory):
        account = producer_account_factory()
        account_movement_factory(account=account, quantity_kg=Decimal("100.000"))
        # Leave grain_balance_kg at 0 (discrepancy)
        with pytest.raises(SystemExit, match="1"):
            call_command("check_account_balance")

    def test_tenant_flag(self, producer_account_factory, account_movement_factory, tenant_context):
        account = producer_account_factory()
        account_movement_factory(
            account=account,
            quantity_kg=Decimal("100.000"),
        )
        ProducerAccount.objects.filter(pk=account.pk).update(
            grain_balance_kg=Decimal("100.000"),
        )
        out = StringIO()
        call_command("check_account_balance", tenant=str(tenant_context.id), stdout=out)
        assert "OK: 0 discrepancies" in out.getvalue()
