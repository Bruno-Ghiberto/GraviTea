"""
T084: SaleOrder model unit tests.

Tests SaleOrder.save() lifecycle enforcement: valid/invalid status
transitions, INVOICED immutability, CONFIRMED field lock, and
recalculate_totals() accuracy.
"""

from decimal import Decimal

import pytest

from apps.ventas.models import SaleOrder, SaleOrderStatus


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderTransitions:
    """Status transition validation in SaleOrder.save()."""

    # --- Valid transitions ---

    def test_draft_to_confirmed(self, sale_order_factory, customer_ri):
        """DRAFT → CONFIRMED is a valid transition."""
        order = sale_order_factory(customer=customer_ri)
        assert order.status == SaleOrderStatus.DRAFT

        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.DRAFT
        )
        order.refresh_from_db()
        order.status = SaleOrderStatus.CONFIRMED
        order.save()

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.CONFIRMED

    def test_confirmed_to_invoiced(self, sale_order_factory, customer_ri):
        """CONFIRMED → INVOICED is a valid transition."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )
        order.refresh_from_db()

        order.status = SaleOrderStatus.INVOICED
        order.save()

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED

    def test_confirmed_to_draft(self, sale_order_factory, customer_ri):
        """CONFIRMED → DRAFT is a valid transition (manual cancellation)."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )
        order.refresh_from_db()

        order.status = SaleOrderStatus.DRAFT
        order.save()

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.DRAFT

    # --- Invalid transitions ---

    def test_draft_to_invoiced_invalid(self, sale_order_factory, customer_ri):
        """DRAFT → INVOICED (skipping CONFIRMED) raises ValueError."""
        order = sale_order_factory(customer=customer_ri)
        assert order.status == SaleOrderStatus.DRAFT

        order.status = SaleOrderStatus.INVOICED
        with pytest.raises(ValueError, match="Invalid status transition"):
            order.save()

    def test_invoiced_to_draft_invalid(self, sale_order_factory, customer_ri):
        """INVOICED → DRAFT raises ValueError (terminal state)."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.INVOICED
        )
        order.refresh_from_db()

        order.status = SaleOrderStatus.DRAFT
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()

    def test_invoiced_to_confirmed_invalid(
        self, sale_order_factory, customer_ri
    ):
        """INVOICED → CONFIRMED raises ValueError (terminal state)."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.INVOICED
        )
        order.refresh_from_db()

        order.status = SaleOrderStatus.CONFIRMED
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderImmutability:
    """INVOICED orders reject all modifications."""

    def test_invoiced_order_rejects_any_save(
        self, sale_order_factory, customer_ri
    ):
        """Any save() on an INVOICED order raises ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.INVOICED
        )
        order.refresh_from_db()

        # Try saving without changing anything — should still raise
        # because INVOICED is terminal
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderConfirmedFieldLock:
    """CONFIRMED orders only allow status-related field changes."""

    def test_changing_customer_on_confirmed_raises(
        self, sale_order_factory, customer_ri, customer_factory
    ):
        """Changing customer_id on CONFIRMED order raises ValueError."""
        from tests.ventas.conftest import CUIT_CF
        from apps.facturacion.constants import CondicionIVA, DocTipo

        other_customer = customer_factory(
            cuit=CUIT_CF,
            doc_tipo=DocTipo.DNI,
            condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
            razon_social="Other Customer",
        )

        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )
        order.refresh_from_db()

        order.customer = other_customer
        with pytest.raises(ValueError, match="Cannot modify field"):
            order.save()

    def test_status_change_on_confirmed_allowed(
        self, sale_order_factory, customer_ri
    ):
        """Changing status on CONFIRMED order is allowed (it's mutable)."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )
        order.refresh_from_db()

        order.status = SaleOrderStatus.INVOICED
        order.save()  # Should not raise

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderRecalculateTotals:
    """recalculate_totals() sums items correctly."""

    def test_recalculate_totals_with_items(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
        product_factory,
    ):
        """recalculate_totals() sums subtotal, total_iva, total_amount."""
        order = sale_order_factory(customer=customer_ri)

        # Item 1: qty=2, price=100, tax=21% → subtotal=200, iva=42
        sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("2.0000"),
            unit_price=Decimal("100.000"),
            tax_rate=Decimal("21.00"),
        )

        # Item 2: qty=3, price=50, tax=21% → subtotal=150, iva=31.5
        product2 = product_factory(sku="CALC-002", unit_price=Decimal("50.000"))
        sale_order_item_factory(
            sale_order=order,
            product=product2,
            quantity=Decimal("3.0000"),
            unit_price=Decimal("50.000"),
            tax_rate=Decimal("21.00"),
        )

        order.recalculate_totals()
        order.refresh_from_db()

        assert order.subtotal == Decimal("350.000")
        assert order.total_iva == Decimal("73.500")
        assert order.total_amount == Decimal("423.500")

    def test_recalculate_totals_no_items(
        self, sale_order_factory, customer_ri
    ):
        """recalculate_totals() with no items sets totals to zero."""
        order = sale_order_factory(customer=customer_ri)
        order.recalculate_totals()
        order.refresh_from_db()

        assert order.subtotal == Decimal("0.000")
        assert order.total_iva == Decimal("0.000")
        assert order.total_amount == Decimal("0.000")
