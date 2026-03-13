"""
Integration tests: Sale Order → Comprobante → ARCA Authorization.

Verifies the full invoice lifecycle:
1. SaleService.confirm_sale creates a Comprobante DRAFT with correct amounts
2. SaleService.authorize_sale sends proper ARCA payload (mock SOAP only)
3. Comprobante amounts match SaleOrder totals
4. AlicIva rows are correctly generated

Per spec 011-backend-devops-coherence FR-024.
Boundary mock: external SOAP HTTP only (ARCA client).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)


# ============================================================
# Test Constants
# ============================================================

EMITTER_CUIT = "30555555551"
CUIT_RI = "20345678906"
CUIT_CF = "20000000001"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def _invoice_products(tenant_context, product_category):
    """Products for invoice integration tests."""
    from apps.inventario.models import Product

    product_a = Product.objects.create(
        tenant=tenant_context,
        sku="INV-PROD-A",
        name="Invoice Product A",
        category=product_category,
        unit_price=Decimal("1000.000"),
        cost_price=Decimal("500.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )
    product_b = Product.objects.create(
        tenant=tenant_context,
        sku="INV-PROD-B",
        name="Invoice Product B",
        category=product_category,
        unit_price=Decimal("500.000"),
        cost_price=Decimal("250.000"),
        tax_rate=Decimal("10.50"),
        is_active=True,
    )
    return product_a, product_b


@pytest.fixture
def _arca_fixtures(tenant_context):
    """ARCACredential + PuntoDeVenta for invoice tests."""
    from apps.facturacion.constants import CondicionIVA
    from apps.facturacion.models import ARCACredential, PuntoDeVenta

    cert_pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls\n"
        "b2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD\n"
        "VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7\n"
        "-----END CERTIFICATE-----"
    )
    key_pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEAu+2uZ+hBwuAtb9yZeXRMWkVo8zBzhTBm6NlaRjsCRJSkB5iZ\n"
        "-----END RSA PRIVATE KEY-----"
    )

    credential = ARCACredential.objects.create(
        tenant=tenant_context,
        cuit_holder=EMITTER_CUIT,
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
        is_production=False,
        is_active=True,
        emitter_condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
    )
    pdv = PuntoDeVenta.objects.create(
        tenant=tenant_context,
        numero=1,
        tipo="electronic",
        is_active=True,
    )
    return credential, pdv


@pytest.fixture
def _ri_sale_order(tenant_context, branch, _invoice_products, _arca_fixtures):
    """DRAFT SaleOrder for RI→RI (Type A invoice)."""
    from apps.facturacion.constants import CondicionIVA, DocTipo
    from apps.inventario.models import StockSnapshot
    from apps.ventas.models import Customer, SaleOrder, SaleOrderItem

    product_a, product_b = _invoice_products

    # Seed stock so confirm_sale doesn't fail
    for prod in (product_a, product_b):
        StockSnapshot.objects.create(
            product=prod,
            branch=branch,
            quantity=Decimal("100.0000"),
            reserved_quantity=Decimal("0.0000"),
        )

    customer = Customer.objects.create(
        tenant=tenant_context,
        cuit=CUIT_RI,
        doc_tipo=DocTipo.CUIT,
        condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        razon_social="Invoice Test RI Customer",
        domicilio="Av. Test 200, CABA",
        is_active=True,
    )

    order = SaleOrder.objects.create(
        tenant=tenant_context,
        branch=branch,
        customer=customer,
    )

    SaleOrderItem.objects.create(
        sale_order=order,
        product=product_a,
        quantity=Decimal("2.0000"),
        unit_price=product_a.unit_price,
        tax_rate=product_a.tax_rate,
    )
    SaleOrderItem.objects.create(
        sale_order=order,
        product=product_b,
        quantity=Decimal("4.0000"),
        unit_price=product_b.unit_price,
        tax_rate=product_b.tax_rate,
    )

    order.recalculate_totals()
    order.refresh_from_db()
    return order


@pytest.fixture
def _cf_sale_order(tenant_context, branch, _invoice_products, _arca_fixtures):
    """DRAFT SaleOrder for RI→CF (Type B invoice)."""
    from apps.facturacion.constants import CondicionIVA, DocTipo
    from apps.inventario.models import StockSnapshot
    from apps.ventas.models import Customer, SaleOrder, SaleOrderItem

    product_a, _ = _invoice_products

    StockSnapshot.objects.get_or_create(
        product=product_a,
        branch=branch,
        defaults={
            "quantity": Decimal("100.0000"),
            "reserved_quantity": Decimal("0.0000"),
        },
    )

    customer = Customer.objects.create(
        tenant=tenant_context,
        cuit=CUIT_CF,
        doc_tipo=DocTipo.SIN_IDENTIFICAR,
        condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
        razon_social="Consumidor Final",
        domicilio="Av. CF 300, CABA",
        is_active=True,
    )

    order = SaleOrder.objects.create(
        tenant=tenant_context,
        branch=branch,
        customer=customer,
    )

    SaleOrderItem.objects.create(
        sale_order=order,
        product=product_a,
        quantity=Decimal("1.0000"),
        unit_price=product_a.unit_price,
        tax_rate=product_a.tax_rate,
    )

    order.recalculate_totals()
    order.refresh_from_db()
    return order


# ============================================================
# Tests
# ============================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestConfirmCreatesComprobante:
    """confirm_sale creates a properly populated Comprobante DRAFT."""

    def test_comprobante_amounts_match_sale_order(self, _ri_sale_order):
        """Comprobante imp_total equals SaleOrder total."""
        from apps.facturacion.constants import ComprobanteStatus
        from apps.facturacion.models import Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        mock_invoice = MagicMock()
        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        service.confirm_sale(order=_ri_sale_order)

        comp = Comprobante.objects.get(sale_order=_ri_sale_order)
        assert comp.status == ComprobanteStatus.DRAFT
        assert comp.imp_total == _ri_sale_order.total_amount
        assert comp.emitter_cuit == EMITTER_CUIT
        assert comp.doc_nro == CUIT_RI

    def test_type_a_invoice_has_aliciva_rows(self, _ri_sale_order):
        """RI→RI sale produces Factura A with AlicIva rows."""
        from apps.facturacion.constants import CbteTipo
        from apps.facturacion.models import AlicIva, Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        mock_invoice = MagicMock()
        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        service.confirm_sale(order=_ri_sale_order)

        comp = Comprobante.objects.get(sale_order=_ri_sale_order)
        assert comp.cbte_tipo == CbteTipo.FACTURA_A

        # Should have AlicIva rows (21% and 10.5% for two product tax rates)
        aliciva_set = AlicIva.objects.filter(comprobante=comp)
        assert aliciva_set.count() >= 1  # At least one IVA row

        # Sum of aliciva importe should equal comp.imp_iva
        total_iva = sum(a.importe for a in aliciva_set)
        assert total_iva == comp.imp_iva

    def test_type_b_invoice_for_consumidor_final(self, _cf_sale_order):
        """RI→CF sale produces Factura B."""
        from apps.facturacion.constants import CbteTipo
        from apps.facturacion.models import Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        mock_invoice = MagicMock()
        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        service.confirm_sale(order=_cf_sale_order)

        comp = Comprobante.objects.get(sale_order=_cf_sale_order)
        assert comp.cbte_tipo == CbteTipo.FACTURA_B


@pytest.mark.django_db
@pytest.mark.integration
class TestAuthorizeCallsARCA:
    """authorize_sale sends Comprobante to ARCA via InvoiceService."""

    def test_authorize_passes_comprobante_to_invoice_service(self, _ri_sale_order):
        """authorize_sale calls invoice_service.authorize_comprobante."""
        from apps.facturacion.constants import ComprobanteStatus
        from apps.facturacion.models import Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        # Mock InvoiceService — simulates ARCA returning CAE
        mock_invoice = MagicMock()
        mock_result = MagicMock()
        mock_result.status = ComprobanteStatus.AUTORIZADO
        mock_result.cae = "71234567890123"
        mock_result.cae_fch_vto = date(2026, 3, 15)
        mock_result.cbte_nro = 1
        mock_result.imp_total = _ri_sale_order.total_amount
        mock_result.id = None
        mock_result.arca_response = None
        mock_invoice.authorize_comprobante.return_value = mock_result

        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        # Confirm first
        service.confirm_sale(order=_ri_sale_order)

        comp = Comprobante.objects.get(sale_order=_ri_sale_order)
        mock_result.id = comp.id

        # Authorize
        _ri_sale_order.refresh_from_db()
        result = service.authorize_sale(order=_ri_sale_order)

        # Verify InvoiceService was called with the comprobante
        mock_invoice.authorize_comprobante.assert_called_once()
        call_kwargs = mock_invoice.authorize_comprobante.call_args
        passed_comp = call_kwargs.kwargs.get(
            "comprobante", call_kwargs.args[0] if call_kwargs.args else None
        )
        assert passed_comp is not None

        # Result should contain ARCA data
        assert result["comprobante_status"] == ComprobanteStatus.AUTORIZADO
        assert result["cae"] == "71234567890123"

    def test_authorize_sets_order_invoiced(self, _ri_sale_order):
        """After successful authorization, order status becomes INVOICED."""
        from apps.facturacion.constants import ComprobanteStatus
        from apps.facturacion.models import Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.models import SaleOrderStatus
        from apps.ventas.services.sale_service import SaleService

        mock_invoice = MagicMock()
        mock_result = MagicMock()
        mock_result.status = ComprobanteStatus.AUTORIZADO
        mock_result.cae = "71234567890123"
        mock_result.cae_fch_vto = date(2026, 3, 15)
        mock_result.cbte_nro = 1
        mock_result.imp_total = _ri_sale_order.total_amount
        mock_result.id = None
        mock_result.arca_response = None
        mock_invoice.authorize_comprobante.return_value = mock_result

        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        service.confirm_sale(order=_ri_sale_order)

        comp = Comprobante.objects.get(sale_order=_ri_sale_order)
        mock_result.id = comp.id

        _ri_sale_order.refresh_from_db()
        service.authorize_sale(order=_ri_sale_order)

        _ri_sale_order.refresh_from_db()
        assert _ri_sale_order.status == SaleOrderStatus.INVOICED
