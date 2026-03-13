"""
Tests for GoodsReceipt -> StockMovement integration (T034).

Covers: StockMovement created with type=PURCHASE, correct quantity,
product reference, PO traceability, stock level updated,
POItem.received_quantity accumulated.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

from apps.compras.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from apps.inventario.models import StockMovement, StockSnapshot

pytestmark = [pytest.mark.django_db(transaction=True)]

PO_URL = "/api/v1/compras/purchase-orders/"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def supplier(tenant_context):
    return Supplier.objects.create(
        tenant=tenant_context,
        name="Stock Integration Supplier",
    )


@pytest.fixture
def confirmed_po(tenant_context, supplier, product):
    """Confirmed PO with one item (qty=20)."""
    po = PurchaseOrder.objects.create(
        tenant=tenant_context,
        supplier=supplier,
        order_number="PO-STK-001",
        order_date="2026-02-24",
        status=PurchaseOrderStatus.CONFIRMED,
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        product=product,
        quantity=Decimal("20.000"),
        unit_price=Decimal("100.000"),
    )
    return po


@pytest.fixture
def receive_url(confirmed_po):
    return f"{PO_URL}{confirmed_po.id}/receive/"


def _receive(client, receive_url, branch, poi, qty, receipt_number):
    """Helper to create a goods receipt."""
    data = {
        "receipt_number": receipt_number,
        "branch": str(branch.id),
        "lines": [
            {
                "purchase_order_item_id": str(poi.id),
                "quantity_received": str(qty),
            }
        ],
    }
    return client.post(receive_url, data, format="json")


# ============================================================
# TestStockMovementCreation
# ============================================================


class TestStockMovementCreation:
    """Verify StockMovement records are created on goods receipt."""

    def test_stock_movement_created(self, authenticated_client, confirmed_po, branch, receive_url):
        """A PURCHASE StockMovement is created for each receipt line."""
        poi = confirmed_po.items.first()
        # Use all_objects because middleware clears tenant context after API call
        initial_count = StockMovement.all_objects.count()

        resp = _receive(authenticated_client, receive_url, branch, poi, "10.000", "GR-SM-001")
        assert resp.status_code == status.HTTP_201_CREATED

        assert StockMovement.all_objects.count() == initial_count + 1

    def test_stock_movement_type_purchase(self, authenticated_client, confirmed_po, branch, receive_url):
        """StockMovement type must be PURCHASE."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "10.000", "GR-SM-002")

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert sm.type == "PURCHASE"

    def test_stock_movement_correct_quantity(self, authenticated_client, confirmed_po, branch, receive_url):
        """StockMovement quantity matches receipt line quantity."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "7.500", "GR-SM-003")

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert sm.quantity_delta == Decimal("7.500")

    def test_stock_movement_product_reference(self, authenticated_client, confirmed_po, branch, product, receive_url):
        """StockMovement references the correct product."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "5.000", "GR-SM-004")

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert sm.product_id == product.id

    def test_stock_movement_branch_reference(self, authenticated_client, confirmed_po, branch, receive_url):
        """StockMovement references the receiving branch."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "5.000", "GR-SM-005")

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert sm.branch_id == branch.id

    def test_stock_movement_cost_snapshot(self, authenticated_client, confirmed_po, branch, receive_url):
        """StockMovement cost_snapshot matches PO item unit_price."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "5.000", "GR-SM-006")

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert sm.cost_snapshot == Decimal("100.000")

    def test_stock_movement_reference_id(self, authenticated_client, confirmed_po, branch, receive_url):
        """StockMovement reference_id points to the GoodsReceipt."""
        poi = confirmed_po.items.first()
        resp = _receive(authenticated_client, receive_url, branch, poi, "5.000", "GR-SM-007")
        gr_id = resp.data["id"]

        sm = StockMovement.all_objects.order_by("-created_at").first()
        assert str(sm.reference_id) == str(gr_id)


# ============================================================
# TestStockLevelUpdate
# ============================================================


class TestStockLevelUpdate:
    """Verify stock levels are updated after goods receipt."""

    def test_stock_snapshot_updated(self, authenticated_client, confirmed_po, branch, product, receive_url):
        """StockSnapshot is created/updated after receipt."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "10.000", "GR-SL-001")

        snapshot = StockSnapshot.objects.filter(
            product=product, branch=branch
        ).first()
        assert snapshot is not None
        assert snapshot.quantity >= Decimal("10.000")

    def test_cumulative_stock_updates(self, authenticated_client, confirmed_po, branch, product, receive_url):
        """Multiple receipts accumulate stock."""
        poi = confirmed_po.items.first()

        _receive(authenticated_client, receive_url, branch, poi, "8.000", "GR-SL-002")
        snapshot1 = StockSnapshot.objects.get(product=product, branch=branch)
        qty_after_first = snapshot1.quantity

        _receive(authenticated_client, receive_url, branch, poi, "5.000", "GR-SL-003")
        snapshot1.refresh_from_db()
        assert snapshot1.quantity == qty_after_first + Decimal("5.000")


# ============================================================
# TestPOItemReceivedQuantityAccumulation
# ============================================================


class TestPOItemReceivedQuantityAccumulation:
    """Verify POItem.received_quantity is accumulated from receipts."""

    def test_single_receipt_updates_received_qty(self, authenticated_client, confirmed_po, branch, receive_url):
        """After one receipt, POItem.received_quantity reflects it."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "7.000", "GR-RQ-001")

        poi.refresh_from_db()
        assert poi.received_quantity == Decimal("7.000")

    def test_multiple_receipts_accumulate(self, authenticated_client, confirmed_po, branch, receive_url):
        """Multiple receipts accumulate received_quantity."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "6.000", "GR-RQ-002")
        _receive(authenticated_client, receive_url, branch, poi, "4.000", "GR-RQ-003")

        poi.refresh_from_db()
        assert poi.received_quantity == Decimal("10.000")

    def test_full_receipt_matches_ordered(self, authenticated_client, confirmed_po, branch, receive_url):
        """Full receipt sets received_quantity == quantity."""
        poi = confirmed_po.items.first()
        _receive(authenticated_client, receive_url, branch, poi, "20.000", "GR-RQ-004")

        poi.refresh_from_db()
        assert poi.received_quantity == poi.quantity
