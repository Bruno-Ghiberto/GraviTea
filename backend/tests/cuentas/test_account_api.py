"""Tests for ProducerAccount and Statement API endpoints (T017, T032)."""

import pytest
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.cuentas.models import AccountMovement, ProducerAccount


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestProducerAccountAPI:
    def test_list_returns_tenant_accounts(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.get("/api/v1/cuentas/accounts/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        ids = [r["id"] for r in response.data["results"]]
        assert account.id in ids

    def test_list_filter_by_cuit(
        self, authenticated_client, producer_account_factory
    ):
        producer_account_factory(cuit="20-12345678-9")
        producer_account_factory(cuit="20-99999999-9")
        response = authenticated_client.get(
            "/api/v1/cuentas/accounts/?producer_cuit=20-12345678-9"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["producer_cuit"] == "20-12345678-9"

    def test_detail_returns_decrypted_cuit(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory(cuit="20-12345678-9")
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["producer_cuit"] == "20-12345678-9"
        assert "producer_cuit_encrypted" not in response.data
        assert "producer_cuit_hash" not in response.data

    def test_cross_tenant_returns_404(
        self, other_tenant_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = other_tenant_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_movement_ledger_paginated(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        account_movement_factory(account=account)
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/movements/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "next" in response.data
        assert "count" not in response.data

    def test_patch_movement_405(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        movement = account_movement_factory(account=account)
        response = authenticated_client.patch(
            f"/api/v1/cuentas/accounts/{account.id}/movements/{movement.id}/",
            {"notes": "changed"},
            format="json",
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["code"] == "append_only_violation"

    def test_delete_movement_405(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        movement = account_movement_factory(account=account)
        response = authenticated_client.delete(
            f"/api/v1/cuentas/accounts/{account.id}/movements/{movement.id}/"
        )
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response.data["code"] == "append_only_violation"

    def test_unauthenticated_401(self):
        client = APIClient()
        response = client.get("/api/v1/cuentas/accounts/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_manual_movement(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.post(
            f"/api/v1/cuentas/accounts/{account.id}/movements/",
            {
                "movement_type": "SERVICE_CHARGE",
                "quantity_kg": "0.000",
                "ars_amount": "-5000.000",
                "usd_amount": "0.000",
                "reference_document": "FAC-001",
                "notes": "Storage fee",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["movement_type"] == "SERVICE_CHARGE"

    def test_create_ceg_deposit_via_api_rejected(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.post(
            f"/api/v1/cuentas/accounts/{account.id}/movements/",
            {
                "movement_type": "CEG_DEPOSIT",
                "quantity_kg": "100.000",
                "ars_amount": "0.000",
                "usd_amount": "0.000",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_adjustment_without_permission_403(
        self, sales_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = sales_client.post(
            f"/api/v1/cuentas/accounts/{account.id}/movements/",
            {
                "movement_type": "ADJUSTMENT",
                "quantity_kg": "0.000",
                "ars_amount": "1000.000",
                "usd_amount": "0.000",
                "reference_document": "ADJ-001",
                "notes": "Correction",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_movement_type_filter(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        account_movement_factory(
            account=account,
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
            quantity_kg=Decimal("100.000"),
        )
        account_movement_factory(
            account=account,
            movement_type=AccountMovement.MovementType.SERVICE_CHARGE,
            ars_amount=Decimal("-500.000"),
        )
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/movements/?movement_type=CEG_DEPOSIT"
        )
        assert response.status_code == status.HTTP_200_OK
        for mvt in response.data["results"]:
            assert mvt["movement_type"] == "CEG_DEPOSIT"


@pytest.mark.django_db
@pytest.mark.accounts
@pytest.mark.integration
class TestStatementAPI:
    def test_statement_correct_period(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        now = timezone.now()

        # Create movements in Jan
        m_jan = account_movement_factory(
            account=account,
            quantity_kg=Decimal("5000.000"),
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        AccountMovement.objects.filter(pk=m_jan.pk).update(
            movement_at=now.replace(month=1, day=15)
        )

        # Create movement in Feb
        m_feb = account_movement_factory(
            account=account,
            quantity_kg=Decimal("3000.000"),
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        AccountMovement.objects.filter(pk=m_feb.pk).update(
            movement_at=now.replace(month=2, day=10)
        )

        # Create movement in Mar
        m_mar = account_movement_factory(
            account=account,
            quantity_kg=Decimal("1000.000"),
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        AccountMovement.objects.filter(pk=m_mar.pk).update(
            movement_at=now.replace(month=3, day=5)
        )

        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/"
            f"?date_from=2026-02-01&date_to=2026-02-28"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        # Opening = Jan movements = 5000
        assert Decimal(str(data["grain_ledger"]["opening_balance_kg"])) == Decimal("5000.000")
        # Closing = opening + Feb = 5000 + 3000 = 8000
        assert Decimal(str(data["grain_ledger"]["closing_balance_kg"])) == Decimal("8000.000")

    def test_empty_period(
        self, authenticated_client, producer_account_factory, account_movement_factory
    ):
        account = producer_account_factory()
        now = timezone.now()

        # Only create movement in Jan
        m_jan = account_movement_factory(
            account=account,
            quantity_kg=Decimal("5000.000"),
            movement_type=AccountMovement.MovementType.CEG_DEPOSIT,
        )
        AccountMovement.objects.filter(pk=m_jan.pk).update(
            movement_at=now.replace(month=1, day=15)
        )

        # Request April (empty)
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/"
            f"?date_from=2026-04-01&date_to=2026-04-30"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        opening = Decimal(str(data["grain_ledger"]["opening_balance_kg"]))
        closing = Decimal(str(data["grain_ledger"]["closing_balance_kg"]))
        assert opening == closing

    def test_missing_date_from_400(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/?date_to=2026-02-28"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_date_to_400(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/?date_from=2026-02-01"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_date_from_after_date_to_400(
        self, authenticated_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = authenticated_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/"
            f"?date_from=2026-03-01&date_to=2026-02-01"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cross_tenant_statement_404(
        self, other_tenant_client, producer_account_factory
    ):
        account = producer_account_factory()
        response = other_tenant_client.get(
            f"/api/v1/cuentas/accounts/{account.id}/statement/"
            f"?date_from=2026-01-01&date_to=2026-12-31"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_posicion_consolidada_endpoint(
        self, authenticated_client, producer_account_factory
    ):
        cuit = "20-12345678-9"
        account = producer_account_factory(cuit=cuit)
        ProducerAccount.objects.filter(pk=account.pk).update(
            grain_balance_kg=Decimal("10000.000")
        )
        response = authenticated_client.get(
            f"/api/v1/cuentas/posicion-consolidada/"
            f"?producer_cuit={cuit}&campaign_id={account.campaign_id}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert "summary" in response.data
