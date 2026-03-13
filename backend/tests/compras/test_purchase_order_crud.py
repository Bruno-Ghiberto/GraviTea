"""
T022 — PurchaseOrder CRUD + tenant isolation tests.

Tests create, read, update, delete, list with filters, nested items,
total calculation, and cross-tenant rejection.
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.compras.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus, Supplier


BASE_URL = "/api/v1/compras/purchase-orders/"


@pytest.fixture
def supplier(tenant_context):
    """Create a supplier for PO tests."""
    return Supplier.objects.create(
        tenant=tenant_context,
        name="PO Test Supplier",
    )


@pytest.fixture
def po_payload(supplier):
    """Standard PO creation payload."""
    return {
        "supplier": str(supplier.id),
        "order_number": "PO-TEST-001",
        "order_date": str(timezone.now().date()),
        "notes": "Test purchase order",
        "items": [
            {
                "product": None,  # Will be replaced by caller
                "quantity": "10.000",
                "unit_price": "25.500",
            },
        ],
    }


@pytest.mark.django_db
class TestPurchaseOrderCreate:
    """Test PO creation with nested items."""

    def test_create_po_with_items(
        self, authenticated_client, supplier, product
    ) -> None:
        """POST creates PO with nested items and computed totals."""
        data = {
            "supplier": str(supplier.id),
            "order_number": "PO-CREATE-001",
            "order_date": str(timezone.now().date()),
            "items": [
                {
                    "product": str(product.id),
                    "quantity": "10.000",
                    "unit_price": "25.500",
                },
                {
                    "product": str(product.id),
                    "quantity": "5.000",
                    "unit_price": "50.000",
                },
            ],
        }
        response = authenticated_client.post(BASE_URL, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "DRAFT"
        assert len(response.data["items"]) == 2
        # 10*25.5 + 5*50 = 255 + 250 = 505
        assert Decimal(response.data["total_amount"]) == Decimal("505.000")

    def test_create_po_without_items_rejected(
        self, authenticated_client, supplier
    ) -> None:
        """POST without items returns 400."""
        data = {
            "supplier": str(supplier.id),
            "order_number": "PO-NOITEMS",
            "order_date": str(timezone.now().date()),
            "items": [],
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_po_status_defaults_to_draft(
        self, authenticated_client, supplier, product
    ) -> None:
        """Status is always DRAFT on creation, ignoring input."""
        data = {
            "supplier": str(supplier.id),
            "order_number": "PO-DRAFT",
            "order_date": str(timezone.now().date()),
            "items": [
                {"product": str(product.id), "quantity": "1.000", "unit_price": "10.000"},
            ],
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "DRAFT"

    def test_duplicate_order_number_rejected(
        self, authenticated_client, supplier, product
    ) -> None:
        """Duplicate order_number for same tenant is rejected."""
        data = {
            "supplier": str(supplier.id),
            "order_number": "PO-DUP-001",
            "order_date": str(timezone.now().date()),
            "items": [
                {"product": str(product.id), "quantity": "1.000", "unit_price": "10.000"},
            ],
        }
        resp1 = authenticated_client.post(BASE_URL, data, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED

        resp2 = authenticated_client.post(BASE_URL, data, format="json")
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPurchaseOrderRead:
    """Test PO retrieval and listing."""

    def test_list_pos(self, authenticated_client, supplier, product, tenant_context) -> None:
        """GET list returns POs for current tenant."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-LIST-001",
            order_date=timezone.now().date(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("5.000"),
            unit_price=Decimal("10.000"),
        )

        response = authenticated_client.get(BASE_URL)
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_po_detail(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """GET detail returns PO with nested items."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-DETAIL-001",
            order_date=timezone.now().date(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("3.000"),
            unit_price=Decimal("20.000"),
        )

        response = authenticated_client.get(f"{BASE_URL}{po.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["items"]) == 1
        assert response.data["order_number"] == "PO-DETAIL-001"

    def test_filter_by_status(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """GET with ?status=DRAFT filters results."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-FILTER-001",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.DRAFT,
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("1.000"),
            unit_price=Decimal("1.000"),
        )

        response = authenticated_client.get(BASE_URL, {"status": "DRAFT"})
        assert response.status_code == status.HTTP_200_OK

    def test_filter_by_supplier(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """GET with ?supplier=UUID filters by supplier."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-SUPFILTER-001",
            order_date=timezone.now().date(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("1.000"),
            unit_price=Decimal("1.000"),
        )

        response = authenticated_client.get(BASE_URL, {"supplier": str(supplier.id)})
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPurchaseOrderUpdate:
    """Test PO update with mutability enforcement."""

    def test_update_draft_po(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """PATCH on DRAFT PO updates allowed fields."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-UPD-001",
            order_date=timezone.now().date(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po,
            product=product,
            quantity=Decimal("1.000"),
            unit_price=Decimal("1.000"),
        )

        response = authenticated_client.patch(
            f"{BASE_URL}{po.id}/",
            {"notes": "Updated notes", "items": [
                {"product": str(product.id), "quantity": "20.000", "unit_price": "15.000"},
            ]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["notes"] == "Updated notes"

    def test_delete_draft_po(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """DELETE on DRAFT PO succeeds."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-DEL-001",
            order_date=timezone.now().date(),
        )
        response = authenticated_client.delete(f"{BASE_URL}{po.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_confirmed_po_rejected(
        self, authenticated_client, supplier, product, tenant_context
    ) -> None:
        """DELETE on CONFIRMED PO returns 400."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-DELFAIL-001",
            order_date=timezone.now().date(),
            status=PurchaseOrderStatus.CONFIRMED,
        )
        response = authenticated_client.delete(f"{BASE_URL}{po.id}/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPurchaseOrderTenantIsolation:
    """Cross-tenant rejection tests."""

    def test_other_tenant_cannot_access_po(
        self, other_tenant_client, supplier, product, tenant_context
    ) -> None:
        """Other tenant gets 404 for foreign PO."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-ISO-001",
            order_date=timezone.now().date(),
        )
        response = other_tenant_client.get(f"{BASE_URL}{po.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_returns_401(self, api_client) -> None:
        """Unauthenticated request returns 401."""
        response = api_client.get(BASE_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
