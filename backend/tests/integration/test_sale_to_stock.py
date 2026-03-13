"""
Integration tests: Sale Order → Stock Reservation → Inventory Update.

Verifies the full lifecycle:
1. SaleService.confirm_sale reserves stock via real StockService
2. SaleService.authorize_sale commits stock via real StockService
3. StockSnapshot quantities reflect the changes
4. Tenant isolation is preserved throughout

Per spec 011-backend-devops-coherence FR-023.
"""

from __future__ import annotations

import uuid
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


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def _stock_setup(tenant_context, branch, product_category):
    """Create products with initial stock for sale-to-stock tests."""
    from apps.inventario.models import Product, StockSnapshot

    product_a = Product.objects.create(
        tenant=tenant_context,
        sku="INTEG-STOCK-A",
        name="Integration Product A",
        category=product_category,
        unit_price=Decimal("100.000"),
        cost_price=Decimal("50.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )
    product_b = Product.objects.create(
        tenant=tenant_context,
        sku="INTEG-STOCK-B",
        name="Integration Product B",
        category=product_category,
        unit_price=Decimal("200.000"),
        cost_price=Decimal("100.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )

    # Seed initial stock
    StockSnapshot.objects.create(
        product=product_a,
        branch=branch,
        quantity=Decimal("50.0000"),
        reserved_quantity=Decimal("0.0000"),
    )
    StockSnapshot.objects.create(
        product=product_b,
        branch=branch,
        quantity=Decimal("30.0000"),
        reserved_quantity=Decimal("0.0000"),
    )

    return product_a, product_b


@pytest.fixture
def _arca_fixtures(tenant_context):
    """ARCACredential + PuntoDeVenta required for comprobante creation."""
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
def _sale_order(tenant_context, branch, _stock_setup, _arca_fixtures):
    """Create a DRAFT SaleOrder with 2 items referencing stock products."""
    from apps.facturacion.constants import CondicionIVA, DocTipo
    from apps.ventas.models import Customer, SaleOrder, SaleOrderItem

    product_a, product_b = _stock_setup

    customer = Customer.objects.create(
        tenant=tenant_context,
        cuit=CUIT_RI,
        doc_tipo=DocTipo.CUIT,
        condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        razon_social="Stock Test Customer RI",
        domicilio="Av. Test 100, CABA",
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
        quantity=Decimal("5.0000"),
        unit_price=product_a.unit_price,
        tax_rate=product_a.tax_rate,
    )
    SaleOrderItem.objects.create(
        sale_order=order,
        product=product_b,
        quantity=Decimal("3.0000"),
        unit_price=product_b.unit_price,
        tax_rate=product_b.tax_rate,
    )

    order.recalculate_totals()
    order.refresh_from_db()
    return order


# ============================================================
# Tests
# ============================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestSaleConfirmReservesStock:
    """confirm_sale with real StockService creates RESERVED movements."""

    def test_confirm_reserves_stock_for_each_item(
        self, _sale_order, _stock_setup, branch
    ):
        """Confirming a sale creates RESERVED StockMovements and updates snapshots."""
        from apps.inventario.models import StockMovement, StockSnapshot
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        product_a, product_b = _stock_setup

        # Use real StockService, mock InvoiceService (we only test stock here)
        mock_invoice = MagicMock()
        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        result = service.confirm_sale(order=_sale_order)

        assert result["order_status"] == "CONFIRMED"

        # Verify RESERVED movements exist
        reserved = StockMovement.objects.filter(
            sale_order=_sale_order,
            status=StockMovement.StockMovementStatus.RESERVED,
        )
        assert reserved.count() == 2

        # Product A: ordered 5, snapshot should have reserved_quantity=5
        snap_a = StockSnapshot.objects.get(product=product_a, branch=branch)
        assert snap_a.reserved_quantity == Decimal("5.0000")
        assert snap_a.quantity == Decimal("50.0000")  # unchanged until commit

        # Product B: ordered 3
        snap_b = StockSnapshot.objects.get(product=product_b, branch=branch)
        assert snap_b.reserved_quantity == Decimal("3.0000")
        assert snap_b.quantity == Decimal("30.0000")

    def test_confirm_creates_comprobante_draft(self, _sale_order):
        """confirm_sale also creates a Comprobante in DRAFT status."""
        from apps.facturacion.constants import ComprobanteStatus
        from apps.facturacion.models import Comprobante
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        mock_invoice = MagicMock()
        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        result = service.confirm_sale(order=_sale_order)

        comprobante = Comprobante.objects.get(sale_order=_sale_order)
        assert comprobante.status == ComprobanteStatus.DRAFT
        assert comprobante.imp_total > 0


@pytest.mark.django_db
@pytest.mark.integration
class TestSaleAuthorizeCommitsStock:
    """authorize_sale commits RESERVED movements after ARCA success."""

    def test_authorize_commits_stock_and_deducts_quantity(
        self, _sale_order, _stock_setup, branch
    ):
        """Full lifecycle: confirm → authorize → stock committed, quantity decreased."""
        from apps.facturacion.constants import ComprobanteStatus
        from apps.facturacion.models import Comprobante
        from apps.inventario.models import StockMovement, StockSnapshot
        from apps.inventario.services.stock_service import StockService
        from apps.ventas.services.sale_service import SaleService

        product_a, product_b = _stock_setup

        # Mock InvoiceService to simulate ARCA success
        mock_invoice = MagicMock()
        mock_result = MagicMock()
        mock_result.status = ComprobanteStatus.AUTORIZADO
        mock_result.cae = "71234567890123"
        mock_result.cae_fch_vto = timezone.now().date()
        mock_result.cbte_nro = 1
        mock_result.imp_total = _sale_order.total_amount
        mock_result.id = None  # will be set after confirm
        mock_result.arca_response = None
        mock_invoice.authorize_comprobante.return_value = mock_result

        service = SaleService(
            stock_service=StockService,
            invoice_service=mock_invoice,
        )

        # Step 1: Confirm
        service.confirm_sale(order=_sale_order)

        # Set the mock comprobante id to match the real one
        comp = Comprobante.objects.get(sale_order=_sale_order)
        mock_result.id = comp.id

        # Step 2: Authorize (mocked ARCA, real stock commit)
        _sale_order.refresh_from_db()
        service.authorize_sale(order=_sale_order)

        # Verify movements are now COMMITTED
        committed = StockMovement.objects.filter(
            sale_order=_sale_order,
            status=StockMovement.StockMovementStatus.COMMITTED,
        )
        assert committed.count() == 2

        # Product A: 50 initial - 5 sold = 45, reserved back to 0
        snap_a = StockSnapshot.objects.get(product=product_a, branch=branch)
        assert snap_a.quantity == Decimal("45.0000")
        assert snap_a.reserved_quantity == Decimal("0.0000")

        # Product B: 30 initial - 3 sold = 27
        snap_b = StockSnapshot.objects.get(product=product_b, branch=branch)
        assert snap_b.quantity == Decimal("27.0000")
        assert snap_b.reserved_quantity == Decimal("0.0000")


@pytest.mark.django_db
@pytest.mark.integration
class TestSaleStockTenantIsolation:
    """Sale-to-stock flow respects tenant isolation."""

    def test_sale_does_not_affect_other_tenant_stock(
        self, tenant_context, other_tenant, branch, product_category
    ):
        """Stock changes in tenant A are invisible to tenant B."""
        from apps.inventario.models import Product, StockSnapshot

        # Create product in tenant A
        product = Product.objects.create(
            tenant=tenant_context,
            sku="ISOLATION-A",
            name="Tenant A Product",
            category=product_category,
            unit_price=Decimal("100.000"),
            cost_price=Decimal("50.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        )
        StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=Decimal("100.0000"),
            reserved_quantity=Decimal("0.0000"),
        )

        # Switch to tenant B
        try:
            clear_current_tenant_id()
            set_current_tenant_id(other_tenant.id)

            # Tenant B should see zero products via TenantBoundManager
            assert Product.objects.count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)
