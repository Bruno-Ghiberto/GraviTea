"""
T085: SaleOrderItem model unit tests.

Tests SaleOrderItem.save() auto-calculation of subtotal/iva_amount,
parent status lock enforcement, and unique constraint per order.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.ventas.models import SaleOrder, SaleOrderItem, SaleOrderStatus


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderItemAutoCalculation:
    """Auto-calculate subtotal and iva_amount on save()."""

    def test_auto_calculate_subtotal_and_iva(
        self, sale_order_factory, sale_order_item_factory, customer_ri, product
    ):
        """quantity * unit_price → subtotal; subtotal * tax_rate/100 → iva."""
        order = sale_order_factory(customer=customer_ri)

        item = sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("5.0000"),
            unit_price=Decimal("100.000"),
            tax_rate=Decimal("21.00"),
        )

        assert item.subtotal == Decimal("500.0000")
        assert item.iva_amount == Decimal("105.000000")

    def test_auto_calculate_zero_tax(
        self, sale_order_factory, sale_order_item_factory, customer_ri, product
    ):
        """tax_rate=0 → iva_amount=0."""
        order = sale_order_factory(customer=customer_ri)

        item = sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("3.0000"),
            unit_price=Decimal("200.000"),
            tax_rate=Decimal("0.00"),
        )

        assert item.subtotal == Decimal("600.0000")
        assert item.iva_amount == Decimal("0.000000")

    def test_auto_calculate_fractional_quantity(
        self, sale_order_factory, sale_order_item_factory, customer_ri, product
    ):
        """Fractional quantities calculate correctly."""
        order = sale_order_factory(customer=customer_ri)

        item = sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("2.5000"),
            unit_price=Decimal("100.000"),
            tax_rate=Decimal("10.50"),
        )

        assert item.subtotal == Decimal("250.0000")
        # 250 * 10.50 / 100 = 26.25
        assert item.iva_amount == Decimal("26.250000")


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderItemParentStatusLock:
    """Items cannot be created or modified on non-DRAFT orders."""

    def test_create_item_on_confirmed_order_raises(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
    ):
        """Creating item on CONFIRMED order raises ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )

        with pytest.raises(ValueError, match="non-DRAFT"):
            sale_order_item_factory(
                sale_order=order,
                product=product,
                quantity=Decimal("1.0000"),
                unit_price=Decimal("100.000"),
            )

    def test_edit_item_on_confirmed_order_raises(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
    ):
        """Editing item on CONFIRMED order raises ValueError."""
        order = sale_order_factory(customer=customer_ri)
        item = sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("1.0000"),
            unit_price=Decimal("100.000"),
        )

        # Transition order to CONFIRMED (bypass save validation)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )

        item.quantity = Decimal("10.0000")
        with pytest.raises(ValueError, match="non-DRAFT"):
            item.save()

    def test_create_item_on_invoiced_order_raises(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
    ):
        """Creating item on INVOICED order raises ValueError."""
        order = sale_order_factory(customer=customer_ri)
        SaleOrder.all_objects.filter(pk=order.pk).update(
            status=SaleOrderStatus.INVOICED
        )

        with pytest.raises(ValueError, match="non-DRAFT"):
            sale_order_item_factory(
                sale_order=order,
                product=product,
                quantity=Decimal("1.0000"),
                unit_price=Decimal("100.000"),
            )


@pytest.mark.unit
@pytest.mark.django_db
class TestSaleOrderItemUniqueConstraint:
    """UniqueConstraint: one product per order."""

    def test_duplicate_product_same_order_raises(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
    ):
        """Adding same product twice to one order raises IntegrityError."""
        order = sale_order_factory(customer=customer_ri)

        sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("1.0000"),
            unit_price=Decimal("100.000"),
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                sale_order_item_factory(
                    sale_order=order,
                    product=product,
                    quantity=Decimal("2.0000"),
                    unit_price=Decimal("100.000"),
                )

    def test_different_products_same_order_ok(
        self,
        sale_order_factory,
        sale_order_item_factory,
        customer_ri,
        product,
        product_factory,
    ):
        """Different products on same order is allowed."""
        order = sale_order_factory(customer=customer_ri)

        item1 = sale_order_item_factory(
            sale_order=order,
            product=product,
            quantity=Decimal("1.0000"),
            unit_price=Decimal("100.000"),
        )

        product2 = product_factory(sku="ITEM-002", unit_price=Decimal("50.000"))
        item2 = sale_order_item_factory(
            sale_order=order,
            product=product2,
            quantity=Decimal("3.0000"),
            unit_price=Decimal("50.000"),
        )

        assert SaleOrderItem.objects.filter(sale_order=order).count() == 2
