"""
T089: SaleOrderItem API integration tests.

Tests the nested SaleOrderItemViewSet endpoints:
    POST   /api/v1/ventas/orders/{order_pk}/items/       — add item
    GET    /api/v1/ventas/orders/{order_pk}/items/        — list items
    GET    /api/v1/ventas/orders/{order_pk}/items/{id}/   — retrieve item
    PATCH  /api/v1/ventas/orders/{order_pk}/items/{id}/   — update item
    DELETE /api/v1/ventas/orders/{order_pk}/items/{id}/   — remove item
"""

from decimal import Decimal

import pytest
from rest_framework import status as http_status

from apps.ventas.models import SaleOrder


def _items_url(order_pk):
    return f"/api/v1/ventas/orders/{order_pk}/items/"


def _item_detail_url(order_pk, item_pk):
    return f"/api/v1/ventas/orders/{order_pk}/items/{item_pk}/"


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderItemAPI:
    """T089: SaleOrderItem nested CRUD endpoints."""

    def test_add_item_to_draft_order(
        self, authenticated_client, sale_order_factory, customer_ri, product
    ):
        """POST item to DRAFT order → 201, order totals recalculated."""
        order = sale_order_factory(customer=customer_ri)

        resp = authenticated_client.post(
            _items_url(order.pk),
            {
                "product": str(product.pk),
                "quantity": "3.0000",
                "unit_price": "100.000",
                "tax_rate": "21.00",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_201_CREATED
        assert str(resp.data["product"]) == str(product.pk)

        # Order totals should be recalculated
        order.refresh_from_db()
        assert order.subtotal == Decimal("300.000")
        assert order.total_iva == Decimal("63.000")
        assert order.total_amount == Decimal("363.000")

    def test_add_item_to_confirmed_order_blocked(
        self, authenticated_client, sale_order_factory, customer_ri, product
    ):
        """POST item to CONFIRMED order → 409."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")

        resp = authenticated_client.post(
            _items_url(order.pk),
            {
                "product": str(product.pk),
                "quantity": "1.0000",
                "unit_price": "50.000",
                "tax_rate": "21.00",
            },
            format="json",
        )
        assert resp.status_code == http_status.HTTP_409_CONFLICT
        assert resp.data["error"]["code"] == "order_not_draft"

    def test_update_item_on_draft_order(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """PATCH item on DRAFT order → 200, order totals recalculated."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(sale_order=order, product=product)

        resp = authenticated_client.patch(
            _item_detail_url(order.pk, item.pk),
            {"quantity": "10.0000"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_200_OK

        # Order totals recalculated
        order.refresh_from_db()
        assert order.subtotal == Decimal("1000.000")

    def test_update_item_on_confirmed_order_blocked(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """PATCH item on CONFIRMED order → 409."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(sale_order=order, product=product)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")

        resp = authenticated_client.patch(
            _item_detail_url(order.pk, item.pk),
            {"quantity": "99.0000"},
            format="json",
        )
        assert resp.status_code == http_status.HTTP_409_CONFLICT
        assert resp.data["error"]["code"] == "order_not_draft"

    def test_delete_item_from_draft_order(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """DELETE item from DRAFT order → 204, totals recalculated to zero."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(sale_order=order, product=product)
        order.recalculate_totals()

        resp = authenticated_client.delete(
            _item_detail_url(order.pk, item.pk),
        )
        assert resp.status_code == http_status.HTTP_204_NO_CONTENT

        order.refresh_from_db()
        assert order.subtotal == Decimal("0.000")
        assert order.total_amount == Decimal("0.000")

    def test_delete_item_from_confirmed_order_blocked(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """DELETE item from CONFIRMED order → 409."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(sale_order=order, product=product)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")

        resp = authenticated_client.delete(
            _item_detail_url(order.pk, item.pk),
        )
        assert resp.status_code == http_status.HTTP_409_CONFLICT
        assert resp.data["error"]["code"] == "order_not_draft"

    def test_duplicate_product_rejected(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """POST duplicate product to same order → error (UniqueConstraint)."""
        order = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(sale_order=order, product=product)

        resp = authenticated_client.post(
            _items_url(order.pk),
            {
                "product": str(product.pk),
                "quantity": "1.0000",
                "unit_price": "200.000",
                "tax_rate": "21.00",
            },
            format="json",
        )
        # Expect 400 (IntegrityError caught by DRF) or 409
        assert resp.status_code in (
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_409_CONFLICT,
        )

    def test_list_items_for_order(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """GET list items → returns items for that order."""
        order = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(sale_order=order, product=product)

        resp = authenticated_client.get(_items_url(order.pk))
        assert resp.status_code == http_status.HTTP_200_OK
        # Response could be paginated (list in "results") or a plain list
        items = resp.data.get("results", resp.data)
        assert len(items) == 1
        assert str(items[0]["product"]) == str(product.pk)

    def test_retrieve_single_item(
        self, authenticated_client, sale_order_factory, customer_ri,
        sale_order_item_factory, product
    ):
        """GET retrieve single item → 200 with item data."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(sale_order=order, product=product)

        resp = authenticated_client.get(
            _item_detail_url(order.pk, item.pk),
        )
        assert resp.status_code == http_status.HTTP_200_OK
        assert resp.data["id"] == str(item.pk)
        assert resp.data["quantity"] == "1.0000"
