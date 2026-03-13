"""
Permission tests for Compras (Purchases) module.

Verifies HasModulePermission enforcement on Supplier, PurchaseOrder,
and GoodsReceipt ViewSets.
"""

from __future__ import annotations

import pytest
from rest_framework import status

from apps.compras.models import Supplier


pytestmark = [pytest.mark.django_db(transaction=True)]

SUPPLIERS_URL = "/api/v1/compras/suppliers/"
PURCHASE_ORDERS_URL = "/api/v1/compras/purchase-orders/"
GOODS_RECEIPTS_URL = "/api/v1/compras/goods-receipts/"


@pytest.fixture
def supplier(tenant_context):
    """Create a test supplier."""
    return Supplier.objects.create(
        tenant=tenant_context,
        name="Test Supplier",
        is_active=True,
    )


# ============================================================
# Unauthenticated Access
# ============================================================


class TestUnauthenticatedAccess:
    """Unauthenticated requests should return 401."""

    def test_suppliers_list_unauthenticated(self, api_client):
        resp = api_client.get(SUPPLIERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_suppliers_create_unauthenticated(self, api_client):
        resp = api_client.post(SUPPLIERS_URL, {"name": "New"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_purchase_orders_list_unauthenticated(self, api_client):
        resp = api_client.get(PURCHASE_ORDERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_goods_receipts_list_unauthenticated(self, api_client):
        resp = api_client.get(GOODS_RECEIPTS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Admin User (has purchases.*)
# ============================================================


class TestAdminPermissions:
    """Admin role has full purchases permissions — should succeed."""

    def test_admin_can_list_suppliers(self, authenticated_client):
        resp = authenticated_client.get(SUPPLIERS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_create_supplier(self, authenticated_client, tenant_context):
        resp = authenticated_client.post(
            SUPPLIERS_URL,
            {"name": "New Supplier"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_admin_can_delete_supplier(self, authenticated_client, supplier):
        resp = authenticated_client.delete(f"{SUPPLIERS_URL}{supplier.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_admin_can_list_purchase_orders(self, authenticated_client):
        resp = authenticated_client.get(PURCHASE_ORDERS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_list_goods_receipts(self, authenticated_client):
        resp = authenticated_client.get(GOODS_RECEIPTS_URL)
        assert resp.status_code == status.HTTP_200_OK


# ============================================================
# Sales User (NO purchases permissions)
# ============================================================


class TestSalesUserDenied:
    """Sales role lacks purchases.* permissions — should get 403."""

    def test_sales_cannot_list_suppliers(self, sales_client):
        resp = sales_client.get(SUPPLIERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_create_supplier(self, sales_client):
        resp = sales_client.post(
            SUPPLIERS_URL,
            {"name": "Blocked Supplier"},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_list_purchase_orders(self, sales_client):
        resp = sales_client.get(PURCHASE_ORDERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_list_goods_receipts(self, sales_client):
        resp = sales_client.get(GOODS_RECEIPTS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================
# Viewer User (NO purchases permissions)
# ============================================================


class TestViewerUserDenied:
    """Viewer role lacks purchases.* permissions — should get 403."""

    def test_viewer_cannot_list_suppliers(self, viewer_client):
        resp = viewer_client.get(SUPPLIERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_list_purchase_orders(self, viewer_client):
        resp = viewer_client.get(PURCHASE_ORDERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_list_goods_receipts(self, viewer_client):
        resp = viewer_client.get(GOODS_RECEIPTS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
