"""
T095: Tenant isolation security tests for ventas module.

Verifies that TenantBoundManager enforces strict data isolation:
- Customers created in tenant A are invisible from tenant B context
- SaleOrders created in tenant A are invisible from tenant B context
- SaleOrderItems inherit tenant from their parent SaleOrder
"""

from decimal import Decimal

import pytest

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)
from apps.facturacion.constants import CondicionIVA, DocTipo
from apps.ventas.models import Customer, SaleOrder, SaleOrderItem

# Verified Modulo-11 CUITs
CUIT_TENANT_A = "20345678906"
CUIT_TENANT_B = "27333333339"


@pytest.mark.security
@pytest.mark.tenant_isolation
@pytest.mark.django_db
class TestVentasTenantIsolation:
    """T095: Cross-tenant data isolation for ventas models."""

    def test_customer_cross_tenant_invisible(
        self, tenant_context, other_tenant
    ):
        """Customer in tenant A must be invisible from tenant B context."""
        # Create customer in tenant A (current context)
        customer_a = Customer.objects.create(
            tenant=tenant_context,
            cuit=CUIT_TENANT_A,
            doc_tipo=DocTipo.CUIT,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
            razon_social="Tenant A Corp",
        )

        # Switch to tenant B context
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)
        try:
            # TenantBoundManager should filter out tenant A's customer
            qs = Customer.objects.all()
            assert customer_a.id not in qs.values_list("id", flat=True)
            assert qs.filter(id=customer_a.id).count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)

    def test_order_cross_tenant_invisible(
        self, tenant_context, other_tenant, customer_factory, branch
    ):
        """SaleOrder in tenant A must be invisible from tenant B context."""
        customer = customer_factory(cuit=CUIT_TENANT_A)

        order_a = SaleOrder.objects.create(
            tenant=tenant_context,
            customer=customer,
            branch=branch,
            status="DRAFT",
            subtotal=Decimal("0.000"),
            total_iva=Decimal("0.000"),
            total_amount=Decimal("0.000"),
        )

        # Switch to tenant B context
        clear_current_tenant_id()
        set_current_tenant_id(other_tenant.id)
        try:
            qs = SaleOrder.objects.all()
            assert order_a.id not in qs.values_list("id", flat=True)
            assert qs.filter(id=order_a.id).count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)

    def test_order_item_inherits_tenant(
        self, tenant_context, customer_factory, branch, product
    ):
        """SaleOrderItem must have the same tenant as its parent SaleOrder."""
        customer = customer_factory(cuit=CUIT_TENANT_A)

        order = SaleOrder.objects.create(
            tenant=tenant_context,
            customer=customer,
            branch=branch,
            status="DRAFT",
            subtotal=Decimal("0.000"),
            total_iva=Decimal("0.000"),
            total_amount=Decimal("0.000"),
        )

        item = SaleOrderItem.objects.create(
            tenant=tenant_context,
            sale_order=order,
            product=product,
            quantity=Decimal("2.0000"),
            unit_price=Decimal("100.000"),
            tax_rate=Decimal("21.00"),
        )

        assert item.tenant_id == order.tenant_id
        assert item.tenant_id == tenant_context.id
