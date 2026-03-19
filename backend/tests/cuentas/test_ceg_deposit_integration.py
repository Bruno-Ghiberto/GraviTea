"""Tests for CEG_DEPOSIT integration flow (T013)."""

import pytest
from decimal import Decimal
from unittest.mock import patch

from apps.cuentas.models import ProducerAccount, AccountMovement
from apps.cuentas.services.accounts import create_ceg_deposit
from apps.core.encryption.utils import compute_blind_index


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestCEGDepositFlow:
    def test_create_ceg_deposit_creates_account_and_movement(
        self, romaneo_conforme_factory, admin_user
    ):
        romaneo = romaneo_conforme_factory()
        # Set CONFORME status and peso_neto_conforme_kg for service-level test
        from apps.acopio.models import Romaneo

        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)

        assert ProducerAccount.objects.count() == 1
        account = ProducerAccount.objects.first()
        movements = AccountMovement.objects.filter(
            producer_account=account,
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        assert movements.count() == 1
        assert movements.first().quantity_kg == romaneo.peso_neto_conforme_kg
        assert account.grain_balance_kg == romaneo.peso_neto_conforme_kg

    def test_second_deposit_reuses_account(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        r1 = romaneo_conforme_factory()
        r1.status = Romaneo.RomaneoStatus.CONFORME
        r1.save()

        r2 = romaneo_conforme_factory()
        r2.status = Romaneo.RomaneoStatus.CONFORME
        r2.save()

        create_ceg_deposit(r1, operator=admin_user)
        create_ceg_deposit(r2, operator=admin_user)

        assert ProducerAccount.objects.count() == 1
        account = ProducerAccount.objects.first()
        expected = r1.peso_neto_conforme_kg + r2.peso_neto_conforme_kg
        assert account.grain_balance_kg == expected

    def test_balance_matches_peso_neto_exactly(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)
        account = ProducerAccount.objects.first()
        assert account.grain_balance_kg == Decimal("28500.000")

    def test_movement_references_romaneo(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)
        movement = AccountMovement.objects.first()
        assert movement.romaneo == romaneo

    def test_account_composite_key_correct(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)
        account = ProducerAccount.objects.first()
        assert account.branch == romaneo.branch
        assert account.grain_type == romaneo.grain_type
        assert account.campaign == romaneo.campaign

    def test_blind_index_matches_cuit(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)
        account = ProducerAccount.objects.first()
        expected_hash = compute_blind_index(romaneo.producer_cuit)
        assert account.producer_cuit_hash == expected_hash

    def test_transaction_atomicity_on_failure(
        self, romaneo_conforme_factory, admin_user
    ):
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        with patch.object(
            AccountMovement.objects, "create", side_effect=RuntimeError("boom")
        ):
            with pytest.raises(RuntimeError):
                create_ceg_deposit(romaneo, operator=admin_user)

        # No account should have been created (or it was rolled back)
        assert ProducerAccount.objects.count() == 0

    def test_concurrent_creation_handled(
        self, romaneo_conforme_factory, admin_user
    ):
        """Verify get_or_create returns existing account on second call."""
        from apps.acopio.models import Romaneo

        romaneo = romaneo_conforme_factory()
        romaneo.status = Romaneo.RomaneoStatus.CONFORME
        romaneo.save()

        create_ceg_deposit(romaneo, operator=admin_user)
        # Second call for same romaneo dimensions should reuse account
        create_ceg_deposit(romaneo, operator=admin_user)
        assert ProducerAccount.objects.count() == 1
        account = ProducerAccount.objects.first()
        # Balance should be doubled
        assert account.grain_balance_kg == romaneo.peso_neto_conforme_kg * 2
