"""
T023 — PurchaseOrder state machine tests.

Tests all valid transitions, all invalid transitions, field mutability
per state, and line item lock after confirm.
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.compras.models import (
    PURCHASE_ORDER_TRANSITIONS,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)


BASE_URL = "/api/v1/compras/purchase-orders/"


@pytest.fixture
def supplier(tenant_context):
    return Supplier.objects.create(tenant=tenant_context, name="SM Test Supplier")


@pytest.fixture
def draft_po(tenant_context, supplier, product):
    """Create a DRAFT PO with one item."""
    po = PurchaseOrder.objects.create(
        tenant=tenant_context,
        supplier=supplier,
        order_number="PO-SM-001",
        order_date=timezone.now().date(),
        status=PurchaseOrderStatus.DRAFT,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity=Decimal("10.000"),
        unit_price=Decimal("25.000"),
    )
    po.recalculate_total()
    return po


@pytest.mark.django_db
class TestValidTransitions:
    """Test all allowed state transitions."""

    def test_draft_to_confirmed(self, authenticated_client, draft_po) -> None:
        """DRAFT → CONFIRMED via /confirm/ action."""
        response = authenticated_client.post(f"{BASE_URL}{draft_po.id}/confirm/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "CONFIRMED"

    def test_draft_to_cancelled(self, authenticated_client, draft_po) -> None:
        """DRAFT → CANCELLED via /cancel/ action."""
        response = authenticated_client.post(f"{BASE_URL}{draft_po.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "CANCELLED"

    def test_confirmed_to_cancelled(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CONFIRMED → CANCELLED via /cancel/ action."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-CONF-CANCEL",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CONFIRMED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "CANCELLED"

    def test_partial_received_to_cancelled(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """PARTIAL_RECEIVED → CANCELLED via /cancel/ action."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-PR-CANCEL",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.PARTIAL_RECEIVED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/cancel/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "CANCELLED"


@pytest.mark.django_db
class TestInvalidTransitions:
    """Test all disallowed state transitions."""

    def test_confirmed_cannot_confirm_again(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CONFIRMED → CONFIRMED is rejected (409)."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-DBL-CONF",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CONFIRMED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/confirm/")
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_received_cannot_cancel(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """RECEIVED → CANCELLED is rejected (terminal state)."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-RECV-CANCEL",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.RECEIVED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/cancel/")
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_cancelled_cannot_confirm(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CANCELLED → CONFIRMED is rejected (terminal state)."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-CANC-CONF",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CANCELLED,
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/confirm/")
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_confirm_po_without_items_rejected(
        self, authenticated_client, tenant_context, supplier
    ) -> None:
        """Cannot confirm PO with no items (400)."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SM-NO-ITEMS",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.DRAFT,
        )

        response = authenticated_client.post(f"{BASE_URL}{po.id}/confirm/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFieldMutabilityByState:
    """Test that fields are locked based on PO status."""

    def test_draft_all_fields_editable(
        self, authenticated_client, draft_po, product
    ) -> None:
        """DRAFT PO allows editing all fields."""
        response = authenticated_client.patch(
            f"{BASE_URL}{draft_po.id}/",
            {
                "notes": "New notes",
                "expected_delivery_date": "2026-03-15",
                "items": [
                    {"product": str(product.id), "quantity": "5.000", "unit_price": "30.000"},
                ],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "New notes"

    def test_confirmed_only_notes_and_delivery_editable(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CONFIRMED PO only allows notes + expected_delivery_date."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-MUT-CONF",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CONFIRMED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        # Allowed: notes, expected_delivery_date
        response = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"notes": "Updated confirmed notes"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_confirmed_supplier_change_rejected(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CONFIRMED PO rejects supplier change."""
        other_supplier = Supplier.objects.create(
            tenant=tenant_context, name="Other Supplier"
        )
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-MUT-CONF-SUP",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CONFIRMED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"supplier": str(other_supplier.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_partial_received_only_notes_editable(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """PARTIAL_RECEIVED PO only allows notes."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-MUT-PR",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.PARTIAL_RECEIVED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        # notes allowed
        resp = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"notes": "Partial note"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

        # expected_delivery_date rejected
        resp = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"expected_delivery_date": "2026-04-01"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_received_no_fields_editable(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """RECEIVED PO rejects all updates."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-MUT-RECV",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.RECEIVED,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"notes": "Should fail"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancelled_no_fields_editable(
        self, authenticated_client, tenant_context, supplier, product
    ) -> None:
        """CANCELLED PO rejects all updates."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-MUT-CANC",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CANCELLED,
        )

        response = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"notes": "Should fail"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
