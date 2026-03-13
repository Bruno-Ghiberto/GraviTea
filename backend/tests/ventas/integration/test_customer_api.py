"""
T087: Customer CRUD API integration tests.

Tests CustomerViewSet endpoints: list, search, filter, create,
retrieve, update, and delete (soft deactivation).

Uses authenticated_client fixture (admin JWT with tenant claims)
and customer_factory from ventas conftest.
"""

from decimal import Decimal

import pytest

from apps.facturacion.constants import CondicionIVA, DocTipo

# Verified Modulo-11 CUITs from ventas conftest
CUIT_RI = "20345678906"
CUIT_CF = "20000000001"
CUIT_MONO = "20111111112"
CUIT_EXENTO = "20222222223"

# Additional valid CUITs for test isolation
CUIT_NEW = "27333333339"  # Type-27, check digit 9

BASE_URL = "/api/v1/ventas/customers/"


def _customer_url(pk):
    """Build detail URL for a customer."""
    return f"{BASE_URL}{pk}/"


@pytest.mark.integration
@pytest.mark.django_db
class TestCustomerCrudApi:
    """T087: CustomerViewSet API endpoints."""

    # --- List ---

    def test_list_customers(self, authenticated_client, customer_factory):
        """GET /customers/ returns paginated list with results key."""
        customer_factory(cuit=CUIT_RI, razon_social="Alpha S.A.")
        customer_factory(cuit=CUIT_CF, razon_social="Beta SRL")

        response = authenticated_client.get(BASE_URL)
        assert response.status_code == 200
        # CursorPagination returns "results" key
        assert "results" in response.data
        assert len(response.data["results"]) == 2

    # --- Search ---

    def test_search_customers(self, authenticated_client, customer_factory):
        """GET ?search=... filters by razon_social and cuit."""
        customer_factory(cuit=CUIT_RI, razon_social="Acme Corporation")
        customer_factory(cuit=CUIT_CF, razon_social="Beta Industries")

        # Search by razon_social
        response = authenticated_client.get(BASE_URL, {"search": "Acme"})
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["razon_social"] == "Acme Corporation"

        # Search by CUIT
        response = authenticated_client.get(BASE_URL, {"search": CUIT_CF})
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["cuit"] == CUIT_CF

    # --- Filter by is_active ---

    def test_filter_by_is_active(self, authenticated_client, customer_factory):
        """GET ?is_active=true/false filters active/inactive customers."""
        active = customer_factory(cuit=CUIT_RI, is_active=True)
        inactive = customer_factory(cuit=CUIT_CF, is_active=False)

        response = authenticated_client.get(BASE_URL, {"is_active": "true"})
        assert response.status_code == 200
        results = response.data["results"]
        cuits = [c["cuit"] for c in results]
        assert CUIT_RI in cuits
        assert CUIT_CF not in cuits

        response = authenticated_client.get(BASE_URL, {"is_active": "false"})
        assert response.status_code == 200
        results = response.data["results"]
        cuits = [c["cuit"] for c in results]
        assert CUIT_CF in cuits
        assert CUIT_RI not in cuits

    # --- Filter by condicion_iva ---

    def test_filter_by_condicion_iva(self, authenticated_client, customer_factory):
        """GET ?condicion_iva=1 filters by CondicionIVA code."""
        customer_factory(
            cuit=CUIT_RI,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        customer_factory(
            cuit=CUIT_CF,
            condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
        )

        response = authenticated_client.get(
            BASE_URL,
            {"condicion_iva": str(CondicionIVA.RESPONSABLE_INSCRIPTO)},
        )
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["condicion_iva"] == CondicionIVA.RESPONSABLE_INSCRIPTO

    # --- Create ---

    def test_create_customer_valid(self, authenticated_client, tenant_context):
        """POST with valid data → 201 with all fields."""
        data = {
            "cuit": CUIT_NEW,
            "doc_tipo": DocTipo.CUIT,
            "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
            "razon_social": "New Customer S.A.",
            "domicilio": "Av. Corrientes 1234",
            "email": "new@customer.com",
            "telefono": "011-5555-0001",
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        assert response.status_code == 201
        assert response.data["cuit"] == CUIT_NEW
        assert response.data["razon_social"] == "New Customer S.A."
        assert response.data["is_active"] is True
        assert "condicion_iva_display" in response.data

    def test_create_customer_invalid_cuit(self, authenticated_client):
        """POST with bad CUIT check digit → 400."""
        data = {
            "cuit": "20345678901",  # Invalid check digit (should be 6)
            "doc_tipo": DocTipo.CUIT,
            "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
            "razon_social": "Bad CUIT Corp",
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        assert response.status_code == 400

    def test_create_customer_duplicate_cuit(
        self, authenticated_client, customer_factory
    ):
        """POST same CUIT in same tenant → 400 (uniqueness violation)."""
        customer_factory(cuit=CUIT_RI)

        data = {
            "cuit": CUIT_RI,
            "doc_tipo": DocTipo.CUIT,
            "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
            "razon_social": "Duplicate Corp",
        }
        response = authenticated_client.post(BASE_URL, data, format="json")
        # Expect 400 (serializer uniqueness check) or 409 (conflict)
        assert response.status_code in (400, 409)

    # --- Retrieve ---

    def test_retrieve_customer(self, authenticated_client, customer_factory):
        """GET /customers/{id}/ → 200 with condicion_iva_display."""
        customer = customer_factory(
            cuit=CUIT_RI,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
            razon_social="Retrieve Test S.A.",
        )

        response = authenticated_client.get(_customer_url(customer.id))
        assert response.status_code == 200
        assert response.data["cuit"] == CUIT_RI
        assert response.data["razon_social"] == "Retrieve Test S.A."
        assert "condicion_iva_display" in response.data

    # --- Update ---

    def test_update_customer(self, authenticated_client, customer_factory):
        """PATCH /customers/{id}/ → 200 with updated fields."""
        customer = customer_factory(
            cuit=CUIT_RI,
            razon_social="Original Name",
        )

        response = authenticated_client.patch(
            _customer_url(customer.id),
            {"razon_social": "Updated Name"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["razon_social"] == "Updated Name"

    # --- Delete (soft deactivation) ---

    def test_delete_customer_no_orders(self, authenticated_client, customer_factory):
        """DELETE customer with no linked orders → 204 (soft deactivate)."""
        customer = customer_factory(cuit=CUIT_RI)

        response = authenticated_client.delete(_customer_url(customer.id))
        assert response.status_code == 204

        # Verify soft deactivation
        customer.refresh_from_db()
        assert customer.is_active is False

    def test_delete_customer_with_orders(
        self,
        authenticated_client,
        customer_factory,
        sale_order_factory,
    ):
        """DELETE customer with linked SaleOrder → 409 customer_has_orders.

        TDD: This test defines the desired protection behavior.
        The CustomerViewSet.perform_destroy should check for linked
        orders and return 409 instead of soft-deactivating.
        """
        customer = customer_factory(cuit=CUIT_RI)
        sale_order_factory(customer=customer)

        response = authenticated_client.delete(_customer_url(customer.id))
        assert response.status_code == 409
        assert response.data["error"]["code"] == "customer_has_orders"
