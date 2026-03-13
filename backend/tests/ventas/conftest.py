"""
Ventas test fixtures and factories.

Provides fixtures for Customer management, SaleOrder lifecycle,
and integration with facturacion (ARCA) and inventario (stock) modules.

Fixture design follows the factory-with-closure pattern established
in tests/facturacion/conftest.py.
"""

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
# Test Constants — Valid CUITs (Modulo-11 verified)
# ============================================================

# Emitter: RI (Responsable Inscripto)
EMITTER_CUIT = "30555555551"

# Customers by CondicionIVA
CUIT_RI = "20345678906"  # Responsable Inscripto
CUIT_CF = "20000000001"  # Consumidor Final
CUIT_MONO = "20111111112"  # Monotributista
CUIT_EXENTO = "20222222223"  # Exento
CUIT_RI_2 = "27333333339"  # Second RI customer (cross-tenant tests)


# ============================================================
# Customer Fixtures
# ============================================================


@pytest.fixture
def customer_factory(tenant_context):
    """
    Factory for creating Customer instances with valid CUITs.

    Usage:
        customer = customer_factory()  # Default: RI customer
        customer = customer_factory(condicion_iva=CondicionIVA.CONSUMIDOR_FINAL, cuit=CUIT_CF)
    """
    from apps.facturacion.constants import CondicionIVA, DocTipo
    from apps.ventas.models import Customer

    _counter = [0]

    def create_customer(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "cuit": CUIT_RI,
            "doc_tipo": DocTipo.CUIT,
            "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
            "razon_social": f"Test Customer {_counter[0]}",
            "domicilio": "Av. Test 1234, CABA",
            "email": f"customer{_counter[0]}@test.com",
            "telefono": "011-1234-5678",
            "is_active": True,
        }
        defaults.update(kwargs)
        return Customer.objects.create(**defaults)

    return create_customer


@pytest.fixture
def customer_ri(customer_factory):
    """Responsable Inscripto customer — triggers Factura A when emitter is RI."""
    from apps.facturacion.constants import CondicionIVA, DocTipo

    return customer_factory(
        cuit=CUIT_RI,
        doc_tipo=DocTipo.CUIT,
        condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        razon_social="ACME S.A. (RI)",
    )


@pytest.fixture
def customer_cf(customer_factory):
    """Consumidor Final customer — triggers Factura B when emitter is RI."""
    from apps.facturacion.constants import CondicionIVA, DocTipo

    return customer_factory(
        cuit=CUIT_CF,
        doc_tipo=DocTipo.CONSUMIDOR_FINAL,
        condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
        razon_social="Consumidor Final",
    )


@pytest.fixture
def customer_mono(customer_factory):
    """Monotributista customer — triggers Factura B when emitter is RI."""
    from apps.facturacion.constants import CondicionIVA, DocTipo

    return customer_factory(
        cuit=CUIT_MONO,
        doc_tipo=DocTipo.CUIT,
        condicion_iva=CondicionIVA.MONOTRIBUTISTA,
        razon_social="Mono SRL",
    )


@pytest.fixture
def customer_exento(customer_factory):
    """Exento customer — triggers Factura B when emitter is RI."""
    from apps.facturacion.constants import CondicionIVA, DocTipo

    return customer_factory(
        cuit=CUIT_EXENTO,
        doc_tipo=DocTipo.CUIT,
        condicion_iva=CondicionIVA.EXENTO,
        razon_social="Fundación Exenta",
    )


# ============================================================
# SaleOrder Fixtures
# ============================================================


@pytest.fixture
def sale_order_factory(tenant_context, branch):
    """
    Factory for creating SaleOrder instances.

    Usage:
        order = sale_order_factory(customer=customer_ri)
        order = sale_order_factory(customer=customer_ri, status="CONFIRMED")
    """
    from apps.ventas.models import SaleOrder

    def create_order(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "status": "DRAFT",
            "subtotal": Decimal("0.000"),
            "total_iva": Decimal("0.000"),
            "total_amount": Decimal("0.000"),
        }
        defaults.update(kwargs)
        return SaleOrder.objects.create(**defaults)

    return create_order


@pytest.fixture
def sale_order_item_factory(tenant_context):
    """
    Factory for creating SaleOrderItem instances.

    Items auto-calculate subtotal and iva_amount on save().

    Usage:
        item = sale_order_item_factory(sale_order=order, product=product)
    """
    from apps.ventas.models import SaleOrderItem

    def create_item(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "quantity": Decimal("1.0000"),
            "unit_price": Decimal("100.000"),
            "tax_rate": Decimal("21.00"),
        }
        defaults.update(kwargs)
        return SaleOrderItem.objects.create(**defaults)

    return create_item


@pytest.fixture
def draft_order_with_items(
    sale_order_factory, sale_order_item_factory, customer_ri, product
):
    """
    A complete DRAFT SaleOrder with 2 items, ready for confirm_sale.

    Items:
        - 5 x product @ $100 (21% IVA) → subtotal=500, iva=105
        - 3 x product @ $100 (21% IVA) → subtotal=300, iva=63
    Order totals: subtotal=800, total_iva=168, total_amount=968

    Note: Uses the `product` fixture from root conftest (SKU=TEST-001,
    unit_price=100, cost_price=50, tax_rate=21%).
    """
    order = sale_order_factory(customer=customer_ri)

    sale_order_item_factory(
        sale_order=order,
        product=product,
        quantity=Decimal("5.0000"),
        unit_price=Decimal("100.000"),
        tax_rate=Decimal("21.00"),
    )

    # Need a second product to have 2 items (unique constraint per order)
    from apps.inventario.models import Product

    product2 = Product.objects.create(
        tenant=order.tenant,
        sku="TEST-002",
        name="Test Product 2",
        description="Secondary test product",
        unit_price=Decimal("200.000"),
        cost_price=Decimal("80.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )

    sale_order_item_factory(
        sale_order=order,
        product=product2,
        quantity=Decimal("3.0000"),
        unit_price=Decimal("200.000"),
        tax_rate=Decimal("21.00"),
    )

    order.recalculate_totals()
    order.refresh_from_db()
    return order


# ============================================================
# ARCA Fixtures for ventas integration
# ============================================================


@pytest.fixture
def arca_credential(tenant_context):
    """Active ARCACredential for the test tenant (RI emitter)."""
    from apps.facturacion.constants import CondicionIVA
    from apps.facturacion.models import ARCACredential

    # Use the SAMPLE_CERT_PEM/KEY from facturacion conftest
    cert_pem = "-----BEGIN CERTIFICATE-----\nMIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls\nb2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD\nVQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7\n-----END CERTIFICATE-----"
    key_pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAu+2uZ+hBwuAtb9yZeXRMWkVo8zBzhTBm6NlaRjsCRJSkB5iZ\n-----END RSA PRIVATE KEY-----"

    return ARCACredential.objects.create(
        tenant=tenant_context,
        cuit_holder=EMITTER_CUIT,
        certificate_pem=cert_pem,
        private_key_pem=key_pem,
        is_production=False,
        is_active=True,
        emitter_condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
    )


@pytest.fixture
def punto_de_venta(tenant_context):
    """Active PuntoDeVenta for the test tenant."""
    from apps.facturacion.models import PuntoDeVenta

    return PuntoDeVenta.objects.create(
        tenant=tenant_context,
        numero=1,
        tipo="electronic",
        is_active=True,
    )


# ============================================================
# Mock Services for SaleService DI
# ============================================================


@pytest.fixture
def mock_stock_service():
    """
    Mock StockService for dependency injection into SaleService.

    Methods:
        - reserve_stock(product_id, branch_id, quantity) → True
        - record_movement(...) → MagicMock
        - commit_reservation(sale_order_id, comprobante_id) → None
    """
    service = MagicMock()
    service.reserve_stock.return_value = True
    service.record_movement.return_value = MagicMock(id=uuid.uuid4())
    service.commit_reservation.return_value = None
    return service


@pytest.fixture
def mock_invoice_service():
    """
    Mock InvoiceService for dependency injection into SaleService.

    Returns a mock whose authorize_comprobante() returns a Comprobante-like
    object with CAE and AUTORIZADO status.
    """
    from apps.facturacion.constants import ComprobanteStatus

    service = MagicMock()

    # Default: successful authorization
    result = MagicMock()
    result.status = ComprobanteStatus.AUTORIZADO
    result.cae = "71234567890123"
    result.cae_fch_vto = date(2026, 3, 15)
    result.cbte_nro = 1
    result.imp_total = Decimal("968.000")
    result.id = uuid.uuid4()
    result.arca_response = None

    service.authorize_comprobante.return_value = result
    return service


@pytest.fixture
def sale_service(mock_stock_service, mock_invoice_service):
    """SaleService with mocked dependencies for isolated testing."""
    from apps.ventas.services.sale_service import SaleService

    return SaleService(
        stock_service=mock_stock_service,
        invoice_service=mock_invoice_service,
    )
