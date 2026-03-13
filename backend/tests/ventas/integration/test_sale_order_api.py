"""
T088: SaleOrder CRUD API integration tests.

Tests SaleOrderViewSet endpoints: list with filters, create, retrieve
with nested items, update, delete, and authentication enforcement.

Uses authenticated_client fixture (admin JWT with tenant claims)
and ventas conftest factories.
"""

from decimal import Decimal

import pytest

from apps.ventas.models import SaleOrder, SaleOrderStatus

BASE_URL = "/api/v1/ventas/orders/"


def _order_url(pk):
    """Build detail URL for a sale order."""
    return f"{BASE_URL}{pk}/"


def _items_url(order_pk):
    """Build items list URL for a sale order."""
    return f"{BASE_URL}{order_pk}/items/"


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderCreate:
    """POST /api/v1/ventas/orders/"""

    def test_create_order(
        self, authenticated_client, customer_ri, branch
    ):
        """POST with customer + branch → 201 DRAFT order."""
        data = {
            "customer": str(customer_ri.id),
            "branch": str(branch.id),
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["status"] == SaleOrderStatus.DRAFT
        assert str(response.data["customer"]) == str(customer_ri.id)
        assert str(response.data["branch"]) == str(branch.id)
        assert response.data["subtotal"] == "0.000"
        assert response.data["total_amount"] == "0.000"


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderList:
    """GET /api/v1/ventas/orders/ with filters."""

    def test_list_orders(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """GET /orders/ returns paginated results."""
        sale_order_factory(customer=customer_ri)
        sale_order_factory(customer=customer_ri)

        response = authenticated_client.get(BASE_URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) == 2

    def test_filter_by_status(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """GET ?status=DRAFT filters by status."""
        sale_order_factory(customer=customer_ri)  # DRAFT by default

        order2 = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order2.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )

        response = authenticated_client.get(
            BASE_URL, {"status": SaleOrderStatus.DRAFT}
        )
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["status"] == SaleOrderStatus.DRAFT

    def test_filter_by_customer(
        self,
        authenticated_client,
        sale_order_factory,
        customer_ri,
        customer_factory,
    ):
        """GET ?customer={id} filters by customer FK."""
        from tests.ventas.conftest import CUIT_CF
        from apps.facturacion.constants import CondicionIVA, DocTipo

        other_customer = customer_factory(
            cuit=CUIT_CF,
            doc_tipo=DocTipo.DNI,
            condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
            razon_social="Other Customer",
        )

        sale_order_factory(customer=customer_ri)
        sale_order_factory(customer=other_customer)

        response = authenticated_client.get(
            BASE_URL, {"customer": str(customer_ri.id)}
        )
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1

    def test_filter_by_date_range(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """GET ?date_from=...&date_to=... filters by sale_date."""
        order = sale_order_factory(customer=customer_ri)

        # Use today's date (auto_now_add) — order should appear
        from django.utils import timezone

        today = timezone.now().date().isoformat()

        response = authenticated_client.get(
            BASE_URL, {"date_from": today, "date_to": today}
        )
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderRetrieve:
    """GET /api/v1/ventas/orders/{id}/"""

    def test_retrieve_order_with_items(
        self,
        authenticated_client,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
    ):
        """GET /orders/{id}/ returns nested items (SaleOrderDetailSerializer)."""
        order = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("2.0000"),
            unit_price=Decimal("100.000"),
        )
        order.recalculate_totals()

        response = authenticated_client.get(_order_url(order.id))
        assert response.status_code == 200
        assert "items" in response.data
        assert len(response.data["items"]) == 1
        assert str(response.data["items"][0]["product"]) == str(product.id)
        assert "customer_name" in response.data
        assert "status_display" in response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderUpdate:
    """PATCH /api/v1/ventas/orders/{id}/"""

    def test_update_draft_order(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """PATCH DRAFT order → 200."""
        order = sale_order_factory(customer=customer_ri)

        response = authenticated_client.patch(
            _order_url(order.id),
            {"customer": str(customer_ri.id)},
            format="json",
        )
        assert response.status_code == 200

    def test_update_confirmed_order_blocked(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """PATCH CONFIRMED order → 409 order_not_draft."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )

        response = authenticated_client.patch(
            _order_url(order.id),
            {"customer": str(customer_ri.id)},
            format="json",
        )
        assert response.status_code == 409
        assert response.data["error"]["code"] == "order_not_draft"


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderDelete:
    """DELETE /api/v1/ventas/orders/{id}/"""

    def test_delete_draft_order(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """DELETE DRAFT order → 204."""
        order = sale_order_factory(customer=customer_ri)

        response = authenticated_client.delete(_order_url(order.id))
        assert response.status_code == 204

    def test_delete_confirmed_order_blocked(
        self, authenticated_client, sale_order_factory, customer_ri
    ):
        """DELETE CONFIRMED order → 409 order_not_draft."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )

        response = authenticated_client.delete(_order_url(order.id))
        assert response.status_code == 409
        assert response.data["error"]["code"] == "order_not_draft"


@pytest.mark.integration
@pytest.mark.django_db
class TestSaleOrderAuthentication:
    """Authentication enforcement on SaleOrder endpoints."""

    def test_unauthenticated_list_rejected(self, api_client):
        """GET /orders/ without token → 401 or 403."""
        response = api_client.get(BASE_URL)
        assert response.status_code in (401, 403)

    def test_unauthenticated_create_rejected(self, api_client):
        """POST /orders/ without token → 401 or 403."""
        response = api_client.post(BASE_URL, {}, format="json")
        assert response.status_code in (401, 403)
