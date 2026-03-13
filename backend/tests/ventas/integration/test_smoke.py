"""
T108: Final integration smoke test.

End-to-end validation of the entire ventas feature:
    create customer → create order → add items → confirm →
    authorize (mocked ARCA) → verify QR code → verify stock committed →
    verify audit trail.

Tests use API endpoints (via DRF APIClient) for customer/order/item CRUD,
then call SaleService directly for confirm/authorize (with mocked ARCA).
This validates the full stack: serializers → views → service → models.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.facturacion.constants import (
    CbteTipo,
    ComprobanteStatus,
    CondicionIVA,
    DocTipo,
)
from apps.facturacion.qr import generate_fiscal_qr_data
from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.ventas.models import SaleOrder, SaleOrderItem, SaleOrderStatus
from apps.ventas.services.sale_service import SaleService


# ============================================================
# Constants
# ============================================================

EMITTER_CUIT = "30555555551"
CUSTOMER_CUIT_RI = "20345678906"


# ============================================================
# T108: Full lifecycle smoke test
# ============================================================


@pytest.mark.django_db
class TestFullLifecycleSmokeTest:
    """
    T108: End-to-end smoke test covering the complete sale lifecycle
    through all layers of the application stack.

    Flow:
        1. Create customer via API
        2. Create sale order via API
        3. Add items via API
        4. Confirm sale (service layer with mocked stock)
        5. Authorize sale (service layer with mocked ARCA)
        6. Verify QR code generated
        7. Verify stock committed
        8. Verify audit trail (timestamps, status, comprobante link)
    """

    @pytest.fixture
    def _arca_setup(self, tenant_context):
        """Create ARCACredential and PuntoDeVenta for the test tenant."""
        from apps.facturacion.models import ARCACredential, PuntoDeVenta

        credential = ARCACredential.objects.create(
            tenant=tenant_context,
            cuit_holder=EMITTER_CUIT,
            certificate_pem=(
                "-----BEGIN CERTIFICATE-----\n"
                "MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls\n"
                "b2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD\n"
                "VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7\n"
                "-----END CERTIFICATE-----"
            ),
            private_key_pem=(
                "-----BEGIN RSA PRIVATE KEY-----\n"
                "MIIEpAIBAAKCAQEAu+2uZ+hBwuAtb9yZeXRMWkVo8zBzhTBm6NlaRjsCRJSkB5iZ\n"
                "-----END RSA PRIVATE KEY-----"
            ),
            is_production=False,
            is_active=True,
            emitter_condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )

        punto_de_venta = PuntoDeVenta.objects.create(
            tenant=tenant_context,
            numero=1,
            tipo="electronic",
            is_active=True,
        )

        return credential, punto_de_venta

    @pytest.fixture
    def _mock_services(self):
        """Create mocked stock and invoice services for DI."""
        mock_stock = MagicMock()
        mock_stock.reserve_stock.return_value = True
        mock_stock.record_movement.return_value = MagicMock(id=uuid.uuid4())
        mock_stock.commit_reservation.return_value = None

        mock_invoice = MagicMock()
        result = MagicMock()
        result.status = ComprobanteStatus.AUTORIZADO
        result.cae = "71234567890123"
        result.cae_fch_vto = date(2026, 3, 15)
        result.cbte_nro = 1
        result.imp_total = Decimal("242.000")
        result.id = uuid.uuid4()
        result.arca_response = None
        mock_invoice.authorize_comprobante.return_value = result

        return mock_stock, mock_invoice

    @pytest.mark.integration
    def test_full_lifecycle_api_to_invoiced(
        self,
        authenticated_client,
        admin_user,
        tenant_context,
        branch,
        product,
        _arca_setup,
        _mock_services,
    ):
        """
        T108: Complete smoke test — API CRUD → confirm → authorize → verify.

        Steps:
            1. POST /customers/ — Create RI customer
            2. POST /orders/ — Create DRAFT sale order
            3. POST /orders/{id}/items/ — Add product item
            4. SaleService.confirm_sale() — Reserve stock + create Comprobante
            5. SaleService.authorize_sale() — Mock ARCA CAE
            6. Verify QR code data is generated
            7. Verify stock service commit was called
            8. Verify audit trail: timestamps, status, comprobante link
        """
        client = authenticated_client
        mock_stock, mock_invoice = _mock_services

        # ── Step 1: Create customer via API ──────────────────────
        customer_resp = client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": CUSTOMER_CUIT_RI,
                "doc_tipo": DocTipo.CUIT,
                "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
                "razon_social": "Smoke Test S.A.",
                "domicilio": "Av. Corrientes 1234, CABA",
                "email": "smoke@test.com",
                "telefono": "011-5555-0001",
            },
            format="json",
        )
        assert customer_resp.status_code == 201, (
            f"Customer create failed: {customer_resp.data}"
        )
        customer_id = customer_resp.data["id"]
        assert customer_resp.data["cuit"] == CUSTOMER_CUIT_RI
        assert customer_resp.data["condicion_iva"] == CondicionIVA.RESPONSABLE_INSCRIPTO

        # ── Step 2: Create sale order via API ────────────────────
        order_resp = client.post(
            "/api/v1/ventas/orders/",
            {
                "customer": customer_id,
                "branch": str(branch.id),
            },
            format="json",
        )
        assert order_resp.status_code == 201, (
            f"Order create failed: {order_resp.data}"
        )
        order_id = order_resp.data["id"]
        assert order_resp.data["status"] == SaleOrderStatus.DRAFT

        # ── Step 3: Add item via API ─────────────────────────────
        item_resp = client.post(
            f"/api/v1/ventas/orders/{order_id}/items/",
            {
                "product": str(product.id),
                "quantity": "2.0000",
                "unit_price": "100.000",
                "tax_rate": "21.00",
            },
            format="json",
        )
        assert item_resp.status_code == 201, (
            f"Item create failed: {item_resp.data}"
        )
        assert item_resp.data["product_sku"] == "TEST-001"
        assert Decimal(item_resp.data["subtotal"]) == Decimal("200.000")
        assert Decimal(item_resp.data["iva_amount"]) == Decimal("42.000")

        # Verify order totals recalculated
        order_detail_resp = client.get(f"/api/v1/ventas/orders/{order_id}/")
        assert order_detail_resp.status_code == 200
        assert Decimal(order_detail_resp.data["subtotal"]) == Decimal("200.000")
        assert Decimal(order_detail_resp.data["total_iva"]) == Decimal("42.000")
        assert Decimal(order_detail_resp.data["total_amount"]) == Decimal("242.000")

        # ── Step 4: Confirm sale via service layer ───────────────
        order = SaleOrder.all_objects.get(pk=order_id)
        sale_service = SaleService(
            stock_service=mock_stock,
            invoice_service=mock_invoice,
        )

        # Set tenant context for direct service call (no HTTP middleware)
        set_current_tenant_id(tenant_context.id)
        confirm_result = sale_service.confirm_sale(order=order, user=admin_user)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.CONFIRMED
        assert order.confirmed_at is not None
        assert order.confirmed_by == admin_user
        assert confirm_result["order_status"] == SaleOrderStatus.CONFIRMED

        # Verify stock was reserved (1 item → 1 reserve_stock call)
        assert mock_stock.reserve_stock.call_count == 1
        reserve_kwargs = mock_stock.reserve_stock.call_args.kwargs
        assert reserve_kwargs["product_id"] == str(product.id)
        assert reserve_kwargs["branch_id"] == str(branch.id)
        assert reserve_kwargs["quantity"] == Decimal("2.0000")

        # Verify Comprobante DRAFT was created
        assert hasattr(order, "comprobante_direct")
        comp = order.comprobante_direct
        assert comp.status == ComprobanteStatus.DRAFT
        assert comp.cbte_tipo == CbteTipo.FACTURA_A  # RI→RI = Type A
        assert comp.imp_total == Decimal("242.000")
        assert comp.imp_neto == Decimal("200.000")
        assert comp.imp_iva == Decimal("42.000")
        assert comp.doc_nro == CUSTOMER_CUIT_RI
        assert comp.emitter_cuit == EMITTER_CUIT
        assert comp.sale_order_id == order.id
        assert comp.customer_id == uuid.UUID(customer_id)

        # Verify AlicIva rows (Type A: 1 row for 21% IVA)
        alic_rows = list(comp.aliciva_set.all())
        assert len(alic_rows) == 1
        assert alic_rows[0].base_imp == Decimal("200.000")
        assert alic_rows[0].importe == Decimal("42.000")

        # ── Step 5: Authorize sale via service layer ─────────────
        # Update the mock to return the correct comprobante ID
        mock_invoice.authorize_comprobante.return_value.id = comp.id

        auth_result = sale_service.authorize_sale(order=order)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED
        assert order.invoiced_at is not None
        assert auth_result["cae"] == "71234567890123"
        assert auth_result["comprobante_status"] == ComprobanteStatus.AUTORIZADO

        # ── Step 6: Verify stock committed ───────────────────────
        mock_stock.commit_reservation.assert_called_once()
        commit_kwargs = mock_stock.commit_reservation.call_args.kwargs
        assert commit_kwargs["sale_order_id"] == str(order.id)
        assert commit_kwargs["comprobante_id"] == str(comp.id)

        # ── Step 7: Verify QR code can be generated ──────────────
        # To verify QR, we need the comprobante to have status AUTORIZADO
        # and a CAE set. Since we used mocks, update the comprobante directly.
        from apps.facturacion.models import Comprobante

        Comprobante.all_objects.filter(pk=comp.pk).update(
            status=ComprobanteStatus.AUTORIZADO,
            cae="71234567890123",
            cae_fch_vto=date(2026, 3, 15),
            cbte_nro=1,
        )
        comp.refresh_from_db()

        qr_url = generate_fiscal_qr_data(comp)
        assert qr_url.startswith("https://www.afip.gob.ar/fe/qr/")
        assert "p=" in qr_url  # base64url payload parameter

        # ── Step 8: Verify audit trail ───────────────────────────

        # Order audit
        assert order.confirmed_at is not None
        assert order.invoiced_at is not None
        assert order.confirmed_at < order.invoiced_at
        assert order.confirmed_by == admin_user

        # Comprobante audit
        assert comp.cae == "71234567890123"
        assert comp.cae_fch_vto == date(2026, 3, 15)
        assert comp.cbte_nro == 1
        assert comp.status == ComprobanteStatus.AUTORIZADO

        # Immutability: INVOICED order cannot be modified
        order.subtotal = Decimal("999.000")
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()

        # API confirms order is INVOICED
        final_resp = client.get(f"/api/v1/ventas/orders/{order_id}/")
        assert final_resp.status_code == 200
        assert final_resp.data["status"] == SaleOrderStatus.INVOICED

        # Invoice endpoint returns comprobante details
        invoice_resp = client.get(f"/api/v1/ventas/orders/{order_id}/invoice/")
        assert invoice_resp.status_code == 200
        assert invoice_resp.data["cae"] == "71234567890123"
        assert invoice_resp.data["cbte_tipo"] == CbteTipo.FACTURA_A
        assert invoice_resp.data["status"] == ComprobanteStatus.AUTORIZADO

    @pytest.mark.integration
    def test_smoke_type_b_consumidor_final(
        self,
        authenticated_client,
        admin_user,
        tenant_context,
        branch,
        product,
        _arca_setup,
        _mock_services,
    ):
        """
        Smoke test variant: Consumidor Final customer → Factura B.

        Validates that the CbteTipo resolver correctly determines Type B
        when emitter is RI and receiver is CF.
        """
        client = authenticated_client
        mock_stock, mock_invoice = _mock_services

        # Create CF customer
        cf_resp = client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": "20000000001",
                "doc_tipo": DocTipo.DNI,
                "condicion_iva": CondicionIVA.CONSUMIDOR_FINAL,
                "razon_social": "Consumidor Final Test",
                "domicilio": "Calle Test 999",
            },
            format="json",
        )
        assert cf_resp.status_code == 201

        # Create order + item
        order_resp = client.post(
            "/api/v1/ventas/orders/",
            {"customer": cf_resp.data["id"], "branch": str(branch.id)},
            format="json",
        )
        assert order_resp.status_code == 201

        client.post(
            f"/api/v1/ventas/orders/{order_resp.data['id']}/items/",
            {
                "product": str(product.id),
                "quantity": "1.0000",
                "unit_price": "100.000",
                "tax_rate": "21.00",
            },
            format="json",
        )

        # Confirm — set tenant context for direct service call
        set_current_tenant_id(tenant_context.id)
        order = SaleOrder.all_objects.get(pk=order_resp.data["id"])
        sale_service = SaleService(
            stock_service=mock_stock,
            invoice_service=mock_invoice,
        )
        sale_service.confirm_sale(order=order, user=admin_user)
        order.refresh_from_db()

        # Verify Type B
        comp = order.comprobante_direct
        assert comp.cbte_tipo == CbteTipo.FACTURA_B

    @pytest.mark.integration
    def test_smoke_api_confirm_endpoint(
        self,
        authenticated_client,
        admin_user,
        tenant_context,
        branch,
        product,
        _arca_setup,
    ):
        """
        Smoke test: confirm via API endpoint POST /orders/{id}/confirm/.

        Uses real SaleService (default DI) with real stock service that
        will need stock setup. This test validates the API layer properly
        delegates to SaleService and returns structured results.
        """
        from apps.inventario.models import StockSnapshot

        client = authenticated_client

        # Create stock so reservation works
        StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=Decimal("100.0000"),
            reserved_quantity=Decimal("0.0000"),
        )

        # Create customer
        cust_resp = client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": CUSTOMER_CUIT_RI,
                "doc_tipo": DocTipo.CUIT,
                "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
                "razon_social": "API Confirm Test S.A.",
            },
            format="json",
        )
        assert cust_resp.status_code == 201

        # Create order + item
        order_resp = client.post(
            "/api/v1/ventas/orders/",
            {"customer": cust_resp.data["id"], "branch": str(branch.id)},
            format="json",
        )
        assert order_resp.status_code == 201
        order_id = order_resp.data["id"]

        client.post(
            f"/api/v1/ventas/orders/{order_id}/items/",
            {
                "product": str(product.id),
                "quantity": "3.0000",
                "unit_price": "100.000",
                "tax_rate": "21.00",
            },
            format="json",
        )

        # Confirm via API endpoint
        confirm_resp = client.post(
            f"/api/v1/ventas/orders/{order_id}/confirm/"
        )
        assert confirm_resp.status_code == 200, (
            f"API confirm failed: {confirm_resp.data}"
        )
        assert confirm_resp.data["order_status"] == SaleOrderStatus.CONFIRMED
        assert "comprobante" in confirm_resp.data

        # Verify order is now CONFIRMED
        order = SaleOrder.all_objects.get(pk=order_id)
        assert order.status == SaleOrderStatus.CONFIRMED

        # Verify stock snapshot was updated (reserved_quantity increased)
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.reserved_quantity == Decimal("3.0000")

    @pytest.mark.integration
    def test_smoke_insufficient_stock_via_api(
        self,
        authenticated_client,
        admin_user,
        tenant_context,
        branch,
        product,
        _arca_setup,
    ):
        """
        Smoke test: confirm via API with insufficient stock → 409 error.

        Validates the API error response structure for stock failures.
        """
        from apps.inventario.models import StockSnapshot

        client = authenticated_client

        # Create stock with only 1 unit
        StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=Decimal("1.0000"),
            reserved_quantity=Decimal("0.0000"),
        )

        # Create customer + order + item requesting 10 units
        cust_resp = client.post(
            "/api/v1/ventas/customers/",
            {
                "cuit": CUSTOMER_CUIT_RI,
                "doc_tipo": DocTipo.CUIT,
                "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
                "razon_social": "Stock Fail Test S.A.",
            },
            format="json",
        )
        order_resp = client.post(
            "/api/v1/ventas/orders/",
            {"customer": cust_resp.data["id"], "branch": str(branch.id)},
            format="json",
        )
        client.post(
            f"/api/v1/ventas/orders/{order_resp.data['id']}/items/",
            {
                "product": str(product.id),
                "quantity": "10.0000",
                "unit_price": "100.000",
                "tax_rate": "21.00",
            },
            format="json",
        )

        # Confirm → should fail with 409 insufficient_stock
        confirm_resp = client.post(
            f"/api/v1/ventas/orders/{order_resp.data['id']}/confirm/"
        )
        assert confirm_resp.status_code == 409
        assert confirm_resp.data["error"]["code"] == "insufficient_stock"
        assert "product_sku" in confirm_resp.data["error"]["details"]
        assert confirm_resp.data["error"]["details"]["product_sku"] == "TEST-001"
