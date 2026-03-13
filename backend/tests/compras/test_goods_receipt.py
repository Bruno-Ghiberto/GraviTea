"""
Tests for GoodsReceipt CRUD and immutability (T033).

Covers: create receipt, immutability (reject PUT/PATCH/DELETE),
over-receipt rejection, partial receipt, full receipt,
receipt against non-confirmed PO rejected, tenant isolation.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

from apps.compras.models import (
    GoodsReceipt,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)

pytestmark = [pytest.mark.django_db(transaction=True)]

PO_URL = "/api/v1/compras/purchase-orders/"
GR_URL = "/api/v1/compras/goods-receipts/"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def supplier(tenant_context):
    return Supplier.objects.create(
        tenant=tenant_context,
        name="GR Test Supplier",
    )


@pytest.fixture
def confirmed_po(tenant_context, supplier, product):
    """Create a confirmed PO with 2 items."""
    po = PurchaseOrder.objects.create(
        tenant=tenant_context,
        supplier=supplier,
        order_number="PO-GR-001",
        order_date="2026-02-24",
        status=PurchaseOrderStatus.CONFIRMED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity=Decimal("10.000"),
        unit_price=Decimal("50.000"),
    )
    return po


@pytest.fixture
def confirmed_po_multi(tenant_context, supplier, product, product_category):
    """Confirmed PO with 2 items (different products)."""
    from apps.inventario.models import Product

    product2 = Product.objects.create(
        tenant=tenant_context,
        sku="TEST-GR-002",
        name="GR Product 2",
        category=product_category,
        unit_price=Decimal("25.000"),
        cost_price=Decimal("15.000"),
    )
    po = PurchaseOrder.objects.create(
        tenant=tenant_context,
        supplier=supplier,
        order_number="PO-GR-002",
        order_date="2026-02-24",
        status=PurchaseOrderStatus.CONFIRMED,
    )
    item1 = PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity=Decimal("10.000"),
        unit_price=Decimal("50.000"),
    )
    item2 = PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product2,
        quantity=Decimal("5.000"),
        unit_price=Decimal("25.000"),
    )
    return po, item1, item2


@pytest.fixture
def receive_url(confirmed_po):
    return f"{PO_URL}{confirmed_po.id}/receive/"


# ============================================================
# TestGoodsReceiptCreate
# ============================================================


class TestGoodsReceiptCreate:
    """Test goods receipt creation via PO receive action."""

    def test_create_receipt_success(self, authenticated_client, confirmed_po, branch, receive_url):
        """Create a valid goods receipt."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-001",
            "branch": str(branch.id),
            "lines": [
                {
                    "purchase_order_item_id": str(poi.id),
                    "quantity_received": "5.000",
                }
            ],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["receipt_number"] == "GR-001"
        assert str(resp.data["purchase_order"]) == str(confirmed_po.id)
        assert len(resp.data["lines"]) == 1

    def test_create_receipt_with_notes(self, authenticated_client, confirmed_po, branch, receive_url):
        """Create receipt with optional notes field."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-002",
            "branch": str(branch.id),
            "lines": [
                {
                    "purchase_order_item_id": str(poi.id),
                    "quantity_received": "3.000",
                }
            ],
            "notes": "Partial delivery — rest next week.",
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["notes"] == "Partial delivery — rest next week."

    def test_create_receipt_empty_lines_rejected(self, authenticated_client, confirmed_po, branch, receive_url):
        """Reject receipt with no lines."""
        data = {
            "receipt_number": "GR-003",
            "branch": str(branch.id),
            "lines": [],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# TestGoodsReceiptImmutability
# ============================================================


class TestGoodsReceiptImmutability:
    """Goods receipts are immutable — no update or delete."""

    def test_update_receipt_rejected(self, authenticated_client, confirmed_po, branch, receive_url):
        """PUT/PATCH on goods receipt should fail (405 or 404)."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-IMM",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        gr_id = resp.data["id"]

        # ReadOnlyModelViewSet does not expose PUT/PATCH/DELETE
        resp_patch = authenticated_client.patch(
            f"{GR_URL}{gr_id}/", {"notes": "changed"}, format="json"
        )
        assert resp_patch.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_receipt_rejected(self, authenticated_client, confirmed_po, branch, receive_url):
        """DELETE on goods receipt should fail."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-DEL",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        gr_id = resp.data["id"]

        resp_del = authenticated_client.delete(f"{GR_URL}{gr_id}/")
        assert resp_del.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ============================================================
# TestOverReceiptRejection
# ============================================================


class TestOverReceiptRejection:
    """Over-receipt must be rejected."""

    def test_over_receipt_rejected(self, authenticated_client, confirmed_po, branch, receive_url):
        """Cannot receive more than ordered quantity."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-OVER",
            "branch": str(branch.id),
            "lines": [
                {
                    "purchase_order_item_id": str(poi.id),
                    "quantity_received": "999.000",
                }
            ],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "Over-receipt" in resp.data["detail"]

    def test_cumulative_over_receipt_rejected(self, authenticated_client, confirmed_po, branch, receive_url):
        """Second receipt that exceeds remaining quantity is rejected."""
        poi = confirmed_po.items.first()
        # First receipt: 8 of 10
        data1 = {
            "receipt_number": "GR-CUM1",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "8.000"}],
        }
        resp1 = authenticated_client.post(receive_url, data1, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED

        # Second receipt: 3 of remaining 2 → rejected
        data2 = {
            "receipt_number": "GR-CUM2",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "3.000"}],
        }
        resp2 = authenticated_client.post(receive_url, data2, format="json")
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Over-receipt" in resp2.data["detail"]


# ============================================================
# TestPartialAndFullReceipt
# ============================================================


class TestPartialAndFullReceipt:
    """Test partial and full receipt scenarios with PO state transitions."""

    def test_partial_receipt_transitions_po(self, authenticated_client, confirmed_po, branch, receive_url):
        """Partial receipt sets PO to PARTIAL_RECEIVED."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-PART",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

        confirmed_po.refresh_from_db()
        assert confirmed_po.status == PurchaseOrderStatus.PARTIAL_RECEIVED

    def test_full_receipt_transitions_po(self, authenticated_client, confirmed_po, branch, receive_url):
        """Full receipt sets PO to RECEIVED."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-FULL",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "10.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

        confirmed_po.refresh_from_db()
        assert confirmed_po.status == PurchaseOrderStatus.RECEIVED

    def test_partial_then_full_receipt(self, authenticated_client, confirmed_po, branch, receive_url):
        """Two partial receipts completing the PO transitions to RECEIVED."""
        poi = confirmed_po.items.first()
        # First partial
        data1 = {
            "receipt_number": "GR-P1",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "6.000"}],
        }
        resp1 = authenticated_client.post(receive_url, data1, format="json")
        assert resp1.status_code == status.HTTP_201_CREATED
        confirmed_po.refresh_from_db()
        assert confirmed_po.status == PurchaseOrderStatus.PARTIAL_RECEIVED

        # Second partial completing the order
        data2 = {
            "receipt_number": "GR-P2",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "4.000"}],
        }
        resp2 = authenticated_client.post(receive_url, data2, format="json")
        assert resp2.status_code == status.HTTP_201_CREATED
        confirmed_po.refresh_from_db()
        assert confirmed_po.status == PurchaseOrderStatus.RECEIVED


# ============================================================
# TestReceiptAgainstNonConfirmedPO
# ============================================================


class TestReceiptAgainstNonConfirmedPO:
    """Receipt against non-receivable PO states must be rejected."""

    def test_receipt_against_draft_po(self, authenticated_client, tenant_context, supplier, product, branch):
        """Cannot receive against DRAFT PO."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-DRAFT-RCV",
            order_date="2026-02-24",
            status=PurchaseOrderStatus.DRAFT,
        )
        poi = PurchaseOrderItem.objects.create(
            purchase_order=po, product=product,
            quantity=Decimal("10.000"), unit_price=Decimal("50.000"),
        )
        url = f"{PO_URL}{po.id}/receive/"
        data = {
            "receipt_number": "GR-DRAFT",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "CONFIRMED or PARTIAL_RECEIVED" in resp.data["detail"]

    def test_receipt_against_cancelled_po(self, authenticated_client, tenant_context, supplier, product, branch):
        """Cannot receive against CANCELLED PO."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-CANCEL-RCV",
            order_date="2026-02-24",
            status=PurchaseOrderStatus.CANCELLED,
        )
        poi = PurchaseOrderItem.objects.create(
            purchase_order=po, product=product,
            quantity=Decimal("10.000"), unit_price=Decimal("50.000"),
        )
        url = f"{PO_URL}{po.id}/receive/"
        data = {
            "receipt_number": "GR-CANCEL",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_receipt_against_received_po(self, authenticated_client, tenant_context, supplier, product, branch):
        """Cannot receive against RECEIVED PO."""
        po = PurchaseOrder.objects.create(
            tenant=tenant_context,
            supplier=supplier,
            order_number="PO-RECV-RCV",
            order_date="2026-02-24",
            status=PurchaseOrderStatus.RECEIVED,
        )
        poi = PurchaseOrderItem.objects.create(
            purchase_order=po, product=product,
            quantity=Decimal("10.000"), unit_price=Decimal("50.000"),
        )
        url = f"{PO_URL}{po.id}/receive/"
        data = {
            "receipt_number": "GR-RECV",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ============================================================
# TestGoodsReceiptTenantIsolation
# ============================================================


class TestGoodsReceiptTenantIsolation:
    """Goods receipts must be tenant-isolated."""

    def test_other_tenant_cannot_see_receipts(
        self, authenticated_client, other_tenant_client, confirmed_po, branch, receive_url
    ):
        """Other tenant cannot see receipts created by first tenant."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-ISO",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        gr_id = resp.data["id"]

        # Other tenant cannot see it
        resp_other = other_tenant_client.get(f"{GR_URL}{gr_id}/")
        assert resp_other.status_code == status.HTTP_404_NOT_FOUND

    def test_other_tenant_list_empty(
        self, authenticated_client, other_tenant_client, confirmed_po, branch, receive_url
    ):
        """Other tenant sees empty list."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-LIST",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "5.000"}],
        }
        authenticated_client.post(receive_url, data, format="json")

        resp = other_tenant_client.get(GR_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["results"] == []


# ============================================================
# TestGoodsReceiptStandaloneList
# ============================================================


class TestGoodsReceiptStandaloneList:
    """Test standalone goods receipt list endpoint."""

    def test_list_all_receipts(self, authenticated_client, confirmed_po, branch, receive_url):
        """List all goods receipts."""
        poi = confirmed_po.items.first()
        # Create 2 receipts
        for i in range(2):
            data = {
                "receipt_number": f"GR-LST-{i}",
                "branch": str(branch.id),
                "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "2.000"}],
            }
            authenticated_client.post(receive_url, data, format="json")

        resp = authenticated_client.get(GR_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 2

    def test_filter_by_purchase_order(self, authenticated_client, confirmed_po, branch, receive_url):
        """Filter receipts by purchase_order UUID."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-FLT",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "3.000"}],
        }
        authenticated_client.post(receive_url, data, format="json")

        resp = authenticated_client.get(GR_URL, {"purchase_order": str(confirmed_po.id)})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) == 1

    def test_get_receipt_detail(self, authenticated_client, confirmed_po, branch, receive_url):
        """Get a single goods receipt by ID."""
        poi = confirmed_po.items.first()
        data = {
            "receipt_number": "GR-DET",
            "branch": str(branch.id),
            "lines": [{"purchase_order_item_id": str(poi.id), "quantity_received": "4.000"}],
        }
        resp = authenticated_client.post(receive_url, data, format="json")
        gr_id = resp.data["id"]

        resp_detail = authenticated_client.get(f"{GR_URL}{gr_id}/")
        assert resp_detail.status_code == status.HTTP_200_OK
        assert resp_detail.data["receipt_number"] == "GR-DET"
        assert len(resp_detail.data["lines"]) == 1
