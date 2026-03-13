"""
T096: Status transition security tests for ventas models.

Tests that direct model.save() properly validates transitions
when bypassing the service layer — ensures the model itself
is the last line of defense against invalid state changes.
"""

from decimal import Decimal

import pytest

from apps.ventas.models import SaleOrder, SaleOrderItem


@pytest.mark.security
@pytest.mark.django_db
class TestSaleOrderStatusTransitionSecurity:
    """T096: Direct model save() transition validation."""

    def test_draft_to_invoiced_blocked(
        self, sale_order_factory, customer_ri
    ):
        """Direct DRAFT → INVOICED via save() must raise ValueError."""
        order = sale_order_factory(customer=customer_ri)
        assert order.status == "DRAFT"

        order.status = "INVOICED"
        with pytest.raises(ValueError, match="Invalid status transition"):
            order.save()

    def test_invoiced_to_draft_blocked(
        self, sale_order_factory, customer_ri
    ):
        """Direct INVOICED → DRAFT via save() must raise ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="INVOICED")
        order.refresh_from_db()

        order.status = "DRAFT"
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()

    def test_invoiced_to_confirmed_blocked(
        self, sale_order_factory, customer_ri
    ):
        """Direct INVOICED → CONFIRMED via save() must raise ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="INVOICED")
        order.refresh_from_db()

        order.status = "CONFIRMED"
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()

    def test_confirmed_order_customer_change_blocked(
        self, sale_order_factory, customer_ri, customer_factory
    ):
        """Modifying customer_id on CONFIRMED order via save() must raise ValueError."""
        from tests.ventas.conftest import CUIT_MONO

        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")
        order.refresh_from_db()

        other_customer = customer_factory(
            cuit=CUIT_MONO,
            razon_social="Other Customer",
        )
        order.customer = other_customer
        with pytest.raises(ValueError, match="Cannot modify field"):
            order.save()

    def test_confirmed_order_subtotal_change_blocked(
        self, sale_order_factory, customer_ri
    ):
        """Modifying subtotal on CONFIRMED order via save() must raise ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")
        order.refresh_from_db()

        order.subtotal = Decimal("99999.000")
        with pytest.raises(ValueError, match="Cannot modify field"):
            order.save()

    def test_item_create_on_confirmed_order_blocked(
        self, sale_order_factory, customer_ri, product, tenant_context
    ):
        """SaleOrderItem.save() on CONFIRMED parent order must raise ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")

        with pytest.raises(ValueError, match="non-DRAFT"):
            SaleOrderItem.objects.create(
                tenant=tenant_context,
                sale_order=order,
                product=product,
                quantity=Decimal("1.0000"),
                unit_price=Decimal("100.000"),
                tax_rate=Decimal("21.00"),
            )
