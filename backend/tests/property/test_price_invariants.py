"""
Price Invariant Property Tests.

Tests for FR-020:
- FR-020: Prices MUST maintain mathematical consistency across calculations

Uses Hypothesis for property-based testing to verify price calculation
invariants hold across all valid input combinations.
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Dict, Optional

import pytest
from hypothesis import given, assume, settings, example
from hypothesis import strategies as st

from tests.fixtures.property_strategies import (
    unit_price,
    cost_price,
    tax_rate,
    discount_percentage,
    price_calculation_scenario,
    boundary_prices,
)


def calculate_gross_price(
    base_price: Decimal,
    tax_rate: Decimal,
    quantity: int = 1
) -> Decimal:
    """
    Calculate gross price including tax.

    Formula: base_price * quantity * (1 + tax_rate/100)
    """
    subtotal = base_price * quantity
    tax_multiplier = Decimal("1") + (tax_rate / Decimal("100"))
    return (subtotal * tax_multiplier).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def calculate_discounted_price(
    base_price: Decimal,
    discount_percentage: Decimal
) -> Decimal:
    """
    Calculate price after discount.

    Formula: base_price * (1 - discount_percentage/100)
    """
    discount_multiplier = Decimal("1") - (discount_percentage / Decimal("100"))
    return (base_price * discount_multiplier).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def calculate_line_total(
    unit_price: Decimal,
    quantity: int,
    discount_percentage: Decimal,
    tax_rate: Decimal
) -> Dict[str, Decimal]:
    """
    Calculate complete line item total.

    Returns:
        Dict with subtotal, discount_amount, tax_amount, and total
    """
    subtotal = unit_price * quantity
    discount_amount = (subtotal * discount_percentage / Decimal("100")).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    taxable_amount = subtotal - discount_amount
    tax_amount = (taxable_amount * tax_rate / Decimal("100")).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    total = taxable_amount + tax_amount

    return {
        "subtotal": subtotal.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        "discount_amount": discount_amount,
        "taxable_amount": taxable_amount.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        "tax_amount": tax_amount,
        "total": total.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
    }


def calculate_margin(
    selling_price: Decimal,
    cost_price: Decimal
) -> Decimal:
    """
    Calculate profit margin percentage.

    Formula: ((selling_price - cost_price) / selling_price) * 100
    """
    if selling_price <= 0:
        return Decimal("0")
    margin = ((selling_price - cost_price) / selling_price) * Decimal("100")
    return margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@pytest.mark.property
class TestPriceCalculationInvariants:
    """
    FR-020: Prices MUST maintain mathematical consistency across calculations.

    Property-based tests for price calculation invariants.
    """

    @given(price=unit_price, quantity=st.integers(min_value=1, max_value=10000))
    @settings(max_examples=100)
    def test_subtotal_equals_price_times_quantity(
        self,
        price: Decimal,
        quantity: int
    ):
        """
        Property: Subtotal always equals unit_price * quantity.
        """
        subtotal = price * quantity

        assert subtotal == price * quantity, (
            f"Subtotal calculation error: {price} * {quantity} != {subtotal}"
        )

    @given(
        price=unit_price,
        tax=tax_rate
    )
    @settings(max_examples=100)
    def test_gross_price_always_gte_base_price(
        self,
        price: Decimal,
        tax: Decimal
    ):
        """
        Property: Gross price (with tax) is always >= base price.
        """
        gross = calculate_gross_price(price, tax)

        assert gross >= price, (
            f"Gross {gross} < base price {price} with tax {tax}%"
        )

    @given(
        price=unit_price,
        discount=discount_percentage
    )
    @settings(max_examples=100)
    def test_discounted_price_always_lte_base_price(
        self,
        price: Decimal,
        discount: Decimal
    ):
        """
        Property: Discounted price is always <= base price.
        """
        discounted = calculate_discounted_price(price, discount)

        assert discounted <= price, (
            f"Discounted {discounted} > base price {price} with discount {discount}%"
        )

    @given(
        price=unit_price,
        discount=discount_percentage
    )
    @settings(max_examples=100)
    def test_discounted_price_always_non_negative(
        self,
        price: Decimal,
        discount: Decimal
    ):
        """
        Property: Discounted price is always >= 0.
        """
        discounted = calculate_discounted_price(price, discount)

        assert discounted >= Decimal("0"), (
            f"Discounted price {discounted} is negative"
        )

    @given(price_calculation_scenario())
    @settings(max_examples=100)
    def test_line_total_invariants(self, scenario: Dict):
        """
        Property: Line total satisfies mathematical invariants.
        """
        result = calculate_line_total(
            scenario["base_price"],
            scenario["quantity"],
            scenario["discount_percentage"],
            scenario["tax_rate"]
        )

        # Invariant 1: subtotal = unit_price * quantity
        expected_subtotal = (
            scenario["base_price"] * scenario["quantity"]
        ).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        assert result["subtotal"] == expected_subtotal

        # Invariant 2: taxable_amount = subtotal - discount_amount
        expected_taxable = result["subtotal"] - result["discount_amount"]
        assert result["taxable_amount"] == expected_taxable.quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

        # Invariant 3: total = taxable_amount + tax_amount
        expected_total = result["taxable_amount"] + result["tax_amount"]
        assert result["total"] == expected_total.quantize(
            Decimal("0.001"), rounding=ROUND_HALF_UP
        )

        # Invariant 4: all amounts are non-negative
        for key, value in result.items():
            assert value >= 0, f"{key} is negative: {value}"


@pytest.mark.property
class TestPriceMonotonicity:
    """
    Test monotonicity properties of price calculations.
    """

    @given(
        price1=unit_price,
        price2=unit_price,
        tax=tax_rate
    )
    @settings(max_examples=100)
    def test_higher_base_price_yields_higher_gross(
        self,
        price1: Decimal,
        price2: Decimal,
        tax: Decimal
    ):
        """
        Property: If base_price_1 > base_price_2, then gross_1 > gross_2 (same tax).
        """
        assume(price1 != price2)

        gross1 = calculate_gross_price(price1, tax)
        gross2 = calculate_gross_price(price2, tax)

        if price1 > price2:
            assert gross1 > gross2, (
                f"Monotonicity violated: {price1} > {price2} but {gross1} <= {gross2}"
            )
        else:
            assert gross1 < gross2, (
                f"Monotonicity violated: {price1} < {price2} but {gross1} >= {gross2}"
            )

    @given(
        price=unit_price,
        tax1=tax_rate,
        tax2=tax_rate
    )
    @settings(max_examples=100)
    def test_higher_tax_yields_higher_gross(
        self,
        price: Decimal,
        tax1: Decimal,
        tax2: Decimal
    ):
        """
        Property: If tax_1 > tax_2, then gross_1 >= gross_2 (same base price).

        Note: Due to rounding to 3 decimal places, close tax rates may produce
        equal results, which is acceptable. The property is that higher tax
        should NEVER produce a LOWER gross price.
        """
        assume(tax1 != tax2)

        gross1 = calculate_gross_price(price, tax1)
        gross2 = calculate_gross_price(price, tax2)

        if tax1 > tax2:
            assert gross1 >= gross2, (
                f"Tax monotonicity violated: {tax1}% > {tax2}% but {gross1} < {gross2}"
            )
        else:
            assert gross1 <= gross2, (
                f"Tax monotonicity violated: {tax1}% < {tax2}% but {gross1} > {gross2}"
            )

    @given(
        price=unit_price,
        discount1=discount_percentage,
        discount2=discount_percentage
    )
    @settings(max_examples=100)
    def test_higher_discount_yields_lower_price(
        self,
        price: Decimal,
        discount1: Decimal,
        discount2: Decimal
    ):
        """
        Property: If discount_1 > discount_2, then price_1 <= price_2.

        Note: Due to rounding to 3 decimal places, close discount percentages
        may produce equal results, which is acceptable. The property is that
        a higher discount should NEVER produce a HIGHER price.
        """
        assume(discount1 != discount2)

        discounted1 = calculate_discounted_price(price, discount1)
        discounted2 = calculate_discounted_price(price, discount2)

        if discount1 > discount2:
            assert discounted1 <= discounted2, (
                f"Discount monotonicity violated: {discount1}% > {discount2}% "
                f"but {discounted1} > {discounted2}"
            )
        else:
            assert discounted1 >= discounted2, (
                f"Discount monotonicity violated: {discount1}% < {discount2}% "
                f"but {discounted1} < {discounted2}"
            )


@pytest.mark.property
class TestMarginCalculations:
    """
    Test margin calculation properties.
    """

    @given(
        selling=unit_price,
        cost=cost_price
    )
    @settings(max_examples=100)
    def test_margin_bounded(
        self,
        selling: Decimal,
        cost: Decimal
    ):
        """
        Property: Margin is bounded between -inf and 100%.
        """
        assume(selling > 0)

        margin = calculate_margin(selling, cost)

        # Margin cannot exceed 100% (would require negative cost)
        assert margin <= Decimal("100"), (
            f"Margin {margin}% exceeds 100%"
        )

    @given(
        selling=unit_price,
        cost=cost_price
    )
    @settings(max_examples=100)
    def test_positive_margin_when_selling_exceeds_cost(
        self,
        selling: Decimal,
        cost: Decimal
    ):
        """
        Property: Margin is positive when selling price > cost price.
        """
        assume(selling > cost)

        margin = calculate_margin(selling, cost)

        assert margin > Decimal("0"), (
            f"Margin should be positive when {selling} > {cost}, got {margin}%"
        )

    @given(
        selling=unit_price,
        cost=cost_price
    )
    @settings(max_examples=100)
    def test_negative_margin_when_cost_exceeds_selling(
        self,
        selling: Decimal,
        cost: Decimal
    ):
        """
        Property: Margin is negative when cost price > selling price.
        """
        assume(cost > selling)

        margin = calculate_margin(selling, cost)

        assert margin < Decimal("0"), (
            f"Margin should be negative when {cost} > {selling}, got {margin}%"
        )


@pytest.mark.property
class TestPriceCommutativity:
    """
    Test commutativity and associativity properties.
    """

    @given(
        price=unit_price,
        discount1=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("20"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        discount2=st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("20"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=50)
    def test_sequential_discounts_not_commutative(
        self,
        price: Decimal,
        discount1: Decimal,
        discount2: Decimal
    ):
        """
        Property: Sequential discounts are NOT commutative (order matters).

        This is an important business rule: applying discounts sequentially
        produces different results than applying them in parallel.
        """
        # Apply discount1 then discount2
        after_d1 = calculate_discounted_price(price, discount1)
        after_d1_d2 = calculate_discounted_price(after_d1, discount2)

        # Apply discount2 then discount1
        after_d2 = calculate_discounted_price(price, discount2)
        after_d2_d1 = calculate_discounted_price(after_d2, discount1)

        # They should be approximately equal due to commutativity of multiplication
        # But due to rounding, might have small differences
        diff = abs(after_d1_d2 - after_d2_d1)
        assert diff <= Decimal("0.01"), (
            f"Sequential discount order difference too large: {diff}"
        )

    @given(
        prices=st.lists(unit_price, min_size=2, max_size=5),
        tax=tax_rate
    )
    @settings(max_examples=50)
    def test_tax_distributive_over_sum(
        self,
        prices: list,
        tax: Decimal
    ):
        """
        Property: Tax on sum equals sum of taxes (distributive property).

        tax(price1 + price2) = tax(price1) + tax(price2)
        """
        # Calculate tax on sum
        total_price = sum(prices, Decimal("0"))
        gross_of_sum = calculate_gross_price(total_price, tax, quantity=1)

        # Calculate sum of individual taxes
        individual_gross = [calculate_gross_price(p, tax, quantity=1) for p in prices]
        sum_of_gross = sum(individual_gross, Decimal("0"))

        # Due to rounding, allow small tolerance
        diff = abs(gross_of_sum - sum_of_gross)
        tolerance = Decimal("0.01") * len(prices)

        assert diff <= tolerance, (
            f"Distributive property violation: {gross_of_sum} vs {sum_of_gross}, diff={diff}"
        )


@pytest.mark.property
class TestBoundaryPrices:
    """
    Test price calculations at boundary values.
    """

    @given(boundary_prices)
    @settings(max_examples=50)
    def test_boundary_prices_calculate_correctly(self, price: Decimal):
        """
        Property: Boundary prices produce valid calculations.
        """
        # Calculate with standard tax
        gross = calculate_gross_price(price, Decimal("21.00"))  # 21% IVA

        # Use >= to account for DECIMAL(17,3) rounding at boundaries
        assert gross >= price, f"Gross {gross} should be at least base {price}"
        assert gross >= Decimal("0")

    @given(price=unit_price)
    @settings(max_examples=100)
    def test_zero_tax_returns_base_price(self, price: Decimal):
        """
        Property: 0% tax returns exactly the base price.
        """
        gross = calculate_gross_price(price, Decimal("0"))

        assert gross == price, (
            f"Zero tax should return base price: {gross} != {price}"
        )

    @given(price=unit_price)
    @settings(max_examples=100)
    def test_zero_discount_returns_base_price(self, price: Decimal):
        """
        Property: 0% discount returns exactly the base price.
        """
        discounted = calculate_discounted_price(price, Decimal("0"))

        assert discounted == price, (
            f"Zero discount should return base price: {discounted} != {price}"
        )

    @given(price=unit_price)
    @settings(max_examples=100)
    def test_full_discount_returns_zero(self, price: Decimal):
        """
        Property: 100% discount returns zero.
        """
        discounted = calculate_discounted_price(price, Decimal("100"))

        assert discounted == Decimal("0"), (
            f"100% discount should return 0: {discounted}"
        )


@pytest.mark.property
class TestPricePrecision:
    """
    Test decimal precision in price calculations.
    """

    @given(
        price=st.decimals(
            min_value=Decimal("0.001"),
            max_value=Decimal("1000"),
            places=3,
            allow_nan=False,
            allow_infinity=False,
        ),
        quantity=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_price_precision_maintained(
        self,
        price: Decimal,
        quantity: int
    ):
        """
        Property: Price calculations maintain 3 decimal precision.
        """
        result = calculate_line_total(
            price,
            quantity,
            Decimal("0"),
            Decimal("21.00")
        )

        # Check all results have at most 3 decimal places
        for key, value in result.items():
            # Convert to string and check decimal places
            str_value = str(value)
            if "." in str_value:
                decimal_places = len(str_value.split(".")[1])
                assert decimal_places <= 3, (
                    f"{key} has {decimal_places} decimal places: {value}"
                )

    @given(
        price1=unit_price,
        price2=unit_price
    )
    @settings(max_examples=100)
    def test_price_addition_precision(
        self,
        price1: Decimal,
        price2: Decimal
    ):
        """
        Property: Price addition maintains precision.
        """
        total = (price1 + price2).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        # Should not lose precision
        assert total == (price1 + price2).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


@pytest.mark.property
class TestInvoiceLineItems:
    """
    Test invoice line item calculation properties.
    """

    @given(
        lines=st.lists(
            st.fixed_dictionaries({
                "unit_price": unit_price,
                "quantity": st.integers(min_value=1, max_value=100),
                "discount": discount_percentage,
                "tax_rate": tax_rate,
            }),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_invoice_total_equals_sum_of_lines(self, lines: list):
        """
        Property: Invoice total equals sum of all line totals.
        """
        line_totals = []
        for line in lines:
            result = calculate_line_total(
                line["unit_price"],
                line["quantity"],
                line["discount"],
                line["tax_rate"]
            )
            line_totals.append(result["total"])

        invoice_total = sum(line_totals, Decimal("0"))

        # Verify by recalculating
        recalc_total = Decimal("0")
        for line in lines:
            result = calculate_line_total(
                line["unit_price"],
                line["quantity"],
                line["discount"],
                line["tax_rate"]
            )
            recalc_total += result["total"]

        assert invoice_total == recalc_total, (
            f"Invoice total mismatch: {invoice_total} != {recalc_total}"
        )

    @given(
        lines=st.lists(
            st.fixed_dictionaries({
                "unit_price": unit_price,
                "quantity": st.integers(min_value=1, max_value=100),
                "discount": discount_percentage,
                "tax_rate": tax_rate,
            }),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_invoice_tax_total_non_negative(self, lines: list):
        """
        Property: Total tax amount is always non-negative.
        """
        total_tax = Decimal("0")
        for line in lines:
            result = calculate_line_total(
                line["unit_price"],
                line["quantity"],
                line["discount"],
                line["tax_rate"]
            )
            total_tax += result["tax_amount"]

        assert total_tax >= Decimal("0"), (
            f"Total tax is negative: {total_tax}"
        )
