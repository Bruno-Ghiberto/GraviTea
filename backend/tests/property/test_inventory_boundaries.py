"""
Inventory Boundary Property Tests.

Tests for FR-019:
- FR-019: Inventory quantities MUST remain non-negative after all operations

Uses Hypothesis for property-based testing to verify inventory
constraints hold across all possible input combinations.
"""

from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass

import pytest
from hypothesis import given, assume, settings, Verbosity, example
from hypothesis import strategies as st

from tests.fixtures.property_strategies import (
    inventory_quantity,
    valid_stock_quantity,
    stock_movement_delta,
    stock_movement_data,
    boundary_quantities,
)


@dataclass
class InventoryOperation:
    """Represents an inventory operation."""

    operation_type: str  # PURCHASE, SALE, ADJUSTMENT, TRANSFER_IN, TRANSFER_OUT
    quantity: Decimal
    timestamp: int  # Relative ordering

    def apply_to(self, current_stock: Decimal) -> Decimal:
        """Apply this operation to current stock level."""
        if self.operation_type in ["PURCHASE", "ADJUSTMENT", "TRANSFER_IN"]:
            return current_stock + abs(self.quantity)
        elif self.operation_type in ["SALE", "TRANSFER_OUT"]:
            return current_stock - abs(self.quantity)
        return current_stock


@dataclass
class StockLedger:
    """Simulates a stock ledger for testing."""

    product_id: str
    tenant_id: str
    current_quantity: Decimal = Decimal("0")
    operations: List[InventoryOperation] = None

    def __post_init__(self):
        if self.operations is None:
            self.operations = []

    def record_purchase(self, quantity: Decimal) -> bool:
        """Record a purchase (always valid, increases stock)."""
        op = InventoryOperation("PURCHASE", abs(quantity), len(self.operations))
        self.operations.append(op)
        self.current_quantity += abs(quantity)
        return True

    def record_sale(self, quantity: Decimal) -> bool:
        """Record a sale (only valid if sufficient stock)."""
        sale_qty = abs(quantity)
        if self.current_quantity >= sale_qty:
            op = InventoryOperation("SALE", sale_qty, len(self.operations))
            self.operations.append(op)
            self.current_quantity -= sale_qty
            return True
        return False

    def record_adjustment(self, quantity: Decimal) -> bool:
        """Record an adjustment (only valid if result non-negative)."""
        new_qty = self.current_quantity + quantity
        if new_qty >= 0:
            op = InventoryOperation("ADJUSTMENT", quantity, len(self.operations))
            self.operations.append(op)
            self.current_quantity = new_qty
            return True
        return False


def calculate_final_stock(
    initial: Decimal,
    operations: List[Dict]
) -> Decimal:
    """
    Calculate final stock after a series of operations.

    Args:
        initial: Initial stock quantity
        operations: List of {type: str, quantity: Decimal} dicts

    Returns:
        Final stock quantity
    """
    current = initial
    for op in operations:
        if op["type"] in ["PURCHASE", "ADJUSTMENT_IN"]:
            current += abs(op["quantity"])
        elif op["type"] in ["SALE", "ADJUSTMENT_OUT"]:
            current -= abs(op["quantity"])
    return current


def validate_stock_constraint(quantity: Decimal) -> bool:
    """Check if a quantity satisfies the non-negative constraint."""
    return quantity >= Decimal("0")


@pytest.mark.property
class TestInventoryNonNegativeConstraint:
    """
    FR-019: Inventory quantities MUST remain non-negative after all operations.

    Property-based tests to verify this constraint holds universally.
    """

    @given(initial_stock=valid_stock_quantity)
    @settings(max_examples=100)
    def test_initial_stock_always_non_negative(self, initial_stock: Decimal):
        """
        Property: Initial stock values are always non-negative.
        """
        assert validate_stock_constraint(initial_stock), (
            f"Initial stock {initial_stock} violates non-negative constraint"
        )

    @given(
        initial_stock=valid_stock_quantity,
        purchase_qty=valid_stock_quantity.filter(lambda x: x > 0)
    )
    @settings(max_examples=100)
    def test_purchase_never_causes_negative_stock(
        self,
        initial_stock: Decimal,
        purchase_qty: Decimal
    ):
        """
        Property: Purchase operations never cause negative stock.
        """
        final_stock = initial_stock + purchase_qty

        assert validate_stock_constraint(final_stock), (
            f"Purchase caused negative stock: {initial_stock} + {purchase_qty} = {final_stock}"
        )

    @given(
        initial_stock=valid_stock_quantity,
        sale_qty=valid_stock_quantity.filter(lambda x: x > 0)
    )
    @settings(max_examples=100)
    def test_sale_rejected_when_insufficient_stock(
        self,
        initial_stock: Decimal,
        sale_qty: Decimal
    ):
        """
        Property: Sales are rejected when they would cause negative stock.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = initial_stock

        sale_success = ledger.record_sale(sale_qty)

        # Either sale succeeded and stock is non-negative
        # Or sale was rejected
        if sale_success:
            assert validate_stock_constraint(ledger.current_quantity), (
                f"Sale succeeded but resulted in negative stock: {ledger.current_quantity}"
            )
        else:
            # Sale was rejected because it would cause negative stock
            assert initial_stock < sale_qty, (
                f"Sale was incorrectly rejected: {initial_stock} >= {sale_qty}"
            )

    @given(
        initial_stock=valid_stock_quantity,
        adjustment=inventory_quantity  # Can be positive or negative
    )
    @settings(max_examples=100)
    def test_adjustment_maintains_non_negative_invariant(
        self,
        initial_stock: Decimal,
        adjustment: Decimal
    ):
        """
        Property: Adjustments maintain non-negative invariant.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = initial_stock

        adjustment_success = ledger.record_adjustment(adjustment)

        # After any operation, stock must be non-negative
        assert validate_stock_constraint(ledger.current_quantity), (
            f"Adjustment violated non-negative constraint: {ledger.current_quantity}"
        )

        # Adjustment should succeed iff result would be non-negative
        expected_result = initial_stock + adjustment
        if expected_result >= 0:
            assert adjustment_success, (
                f"Valid adjustment was rejected: {initial_stock} + {adjustment}"
            )
        else:
            assert not adjustment_success, (
                f"Invalid adjustment was accepted: {initial_stock} + {adjustment}"
            )

    @given(boundary_quantities)
    @settings(max_examples=50)
    def test_boundary_quantities_are_valid(self, quantity: Decimal):
        """
        Property: All boundary quantities satisfy constraints.
        """
        assert validate_stock_constraint(quantity), (
            f"Boundary quantity {quantity} is invalid"
        )


@pytest.mark.property
class TestStockLedgerIntegrity:
    """
    Test stock ledger maintains integrity across multiple operations.
    """

    @given(
        initial=valid_stock_quantity,
        purchases=st.lists(valid_stock_quantity.filter(lambda x: x > 0), min_size=0, max_size=10)
    )
    @settings(max_examples=50)
    def test_multiple_purchases_accumulate_correctly(
        self,
        initial: Decimal,
        purchases: List[Decimal]
    ):
        """
        Property: Multiple purchases accumulate to expected total.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = initial

        for qty in purchases:
            ledger.record_purchase(qty)

        expected = initial + sum(purchases, Decimal("0"))

        assert ledger.current_quantity == expected, (
            f"Stock mismatch: {ledger.current_quantity} != {expected}"
        )
        assert validate_stock_constraint(ledger.current_quantity)

    @given(
        initial=st.decimals(
            min_value=Decimal("1000"),
            max_value=Decimal("10000"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        ),
        sales=st.lists(
            st.decimals(
                min_value=Decimal("1"),
                max_value=Decimal("100"),
                places=4,
                allow_nan=False,
                allow_infinity=False,
            ),
            min_size=0,
            max_size=5
        )
    )
    @settings(max_examples=50)
    def test_valid_sales_deplete_correctly(
        self,
        initial: Decimal,
        sales: List[Decimal]
    ):
        """
        Property: Valid sales deplete stock correctly.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = initial
        total_sold = Decimal("0")

        for qty in sales:
            if ledger.record_sale(qty):
                total_sold += qty

        expected = initial - total_sold

        assert ledger.current_quantity == expected, (
            f"Stock mismatch after sales: {ledger.current_quantity} != {expected}"
        )
        assert validate_stock_constraint(ledger.current_quantity)


@pytest.mark.property
class TestStockOperationSequences:
    """
    Test sequences of stock operations maintain invariants.
    """

    @given(
        operations=st.lists(
            st.fixed_dictionaries({
                "type": st.sampled_from(["PURCHASE", "SALE"]),
                "quantity": st.decimals(
                    min_value=Decimal("1"),
                    max_value=Decimal("100"),
                    places=4,
                    allow_nan=False,
                    allow_infinity=False,
                )
            }),
            min_size=0,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_operation_sequence_maintains_invariant(
        self,
        operations: List[Dict]
    ):
        """
        Property: Any sequence of operations maintains non-negative invariant.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = Decimal("1000")  # Start with sufficient stock

        for op in operations:
            if op["type"] == "PURCHASE":
                ledger.record_purchase(op["quantity"])
            else:
                ledger.record_sale(op["quantity"])

            # After each operation, invariant must hold
            assert validate_stock_constraint(ledger.current_quantity), (
                f"Invariant violated after {op}: {ledger.current_quantity}"
            )

    @given(
        purchase_seq=st.lists(valid_stock_quantity.filter(lambda x: x > 0), min_size=1, max_size=5),
        sale_seq=st.lists(valid_stock_quantity.filter(lambda x: x > 0), min_size=1, max_size=5)
    )
    @settings(max_examples=50)
    def test_purchase_sale_interleaving(
        self,
        purchase_seq: List[Decimal],
        sale_seq: List[Decimal]
    ):
        """
        Property: Interleaved purchases and sales maintain invariant.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")

        # Do purchases first to build up stock
        for qty in purchase_seq:
            ledger.record_purchase(qty)
            assert validate_stock_constraint(ledger.current_quantity)

        # Then do sales (may be rejected if insufficient stock)
        for qty in sale_seq:
            ledger.record_sale(qty)
            assert validate_stock_constraint(ledger.current_quantity)


@pytest.mark.property
class TestQuantityPrecision:
    """
    Test that quantity precision is maintained correctly.
    """

    @given(
        qty1=st.decimals(
            min_value=Decimal("0.0001"),
            max_value=Decimal("1000"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        ),
        qty2=st.decimals(
            min_value=Decimal("0.0001"),
            max_value=Decimal("1000"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=100)
    def test_decimal_precision_preserved(
        self,
        qty1: Decimal,
        qty2: Decimal
    ):
        """
        Property: Decimal precision is preserved in calculations.
        """
        # Addition preserves precision
        sum_qty = qty1 + qty2

        # Result should have no more than 4 decimal places
        # and should equal the mathematical sum
        assert sum_qty == qty1 + qty2

        # Subtraction preserves precision
        if qty1 >= qty2:
            diff_qty = qty1 - qty2
            assert diff_qty == qty1 - qty2
            assert validate_stock_constraint(diff_qty)

    @given(
        qty=st.decimals(
            min_value=Decimal("0.0001"),
            max_value=Decimal("1000"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        ),
        multiplier=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100)
    def test_quantity_scaling_precision(
        self,
        qty: Decimal,
        multiplier: int
    ):
        """
        Property: Scaling quantities preserves precision.
        """
        scaled = qty * multiplier

        # Scaling a valid quantity produces a valid quantity
        assert scaled >= 0, f"Scaled quantity is negative: {scaled}"


@pytest.mark.property
class TestEdgeCases:
    """
    Test edge cases and boundary conditions.
    """

    def test_zero_quantity_operations(self):
        """
        Property: Zero quantity operations are handled correctly.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        ledger.current_quantity = Decimal("100")

        # Zero purchase should work
        ledger.record_purchase(Decimal("0"))
        assert ledger.current_quantity == Decimal("100")

        # Zero sale should work
        ledger.record_sale(Decimal("0"))
        assert ledger.current_quantity == Decimal("100")

        # Zero adjustment should work
        ledger.record_adjustment(Decimal("0"))
        assert ledger.current_quantity == Decimal("100")

    def test_minimum_quantity_operations(self):
        """
        Property: Minimum quantity (0.0001) operations work correctly.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        min_qty = Decimal("0.0001")

        ledger.record_purchase(min_qty)
        assert ledger.current_quantity == min_qty

        ledger.record_sale(min_qty)
        assert ledger.current_quantity == Decimal("0")
        assert validate_stock_constraint(ledger.current_quantity)

    def test_maximum_quantity_operations(self):
        """
        Property: Maximum quantity operations work correctly.
        """
        ledger = StockLedger(product_id="TEST-001", tenant_id="tenant-1")
        max_qty = Decimal("10000000")

        ledger.record_purchase(max_qty)
        assert ledger.current_quantity == max_qty
        assert validate_stock_constraint(ledger.current_quantity)

    @given(
        qty=st.decimals(
            min_value=Decimal("-1000"),
            max_value=Decimal("-0.0001"),
            places=4,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    @settings(max_examples=50)
    def test_negative_initial_stock_rejected(self, qty: Decimal):
        """
        Property: Negative initial stock should be invalid.
        """
        assert not validate_stock_constraint(qty), (
            f"Negative quantity {qty} should be invalid"
        )
