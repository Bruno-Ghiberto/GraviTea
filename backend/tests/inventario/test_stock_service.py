"""
Test suite for StockService (T068, T072-T077).

Tests cover:
- record_movement: Basic movements, validations, error cases
- create_correction: Stock adjustments with audit trail
- reserve_stock: Stock reservation for pending orders
- release_stock: Release reserved stock
- transfer_stock: Inter-branch transfers
- get_current_stock: Current stock levels
- get_stock_at_point_in_time: Historical stock reconstruction
- get_product_stock_summary: Multi-branch stock summary
"""

import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventario.models import StockMovement, StockSnapshot
from apps.inventario.services.stock_service import (InsufficientStockError,
                                                    StockService)


@pytest.mark.django_db
class TestRecordMovement:
    """Tests for StockService.record_movement method."""

    def test_record_purchase_creates_movement_and_snapshot(self, tenant_context, product, branch):
        """Test recording a purchase movement creates both movement and snapshot."""
        movement = StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50.0000"),
            cost_snapshot=Decimal("25.00"),
            reference_id=str(uuid.uuid4()),
            notes="Initial purchase order",
        )
        assert movement.id is not None
        assert movement.tenant_id == tenant_context.id
        assert movement.type == StockMovement.MovementType.PURCHASE
        assert movement.quantity_delta == Decimal("50.0000")
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("50.0000")

    def test_record_sale_decreases_stock(self, tenant_context, product, branch):
        """Test recording a sale movement decreases stock."""
        # First add stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
            cost_snapshot=Decimal("25.00"),
        )

        # Then record a sale
        movement = StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-30.0000"),
            cost_snapshot=Decimal("25.00"),
        )

        assert movement.type == StockMovement.MovementType.SALE
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("70.0000")

    def test_record_movement_zero_quantity_raises_error(self, tenant_context, product, branch):
        """Test that zero quantity delta raises ValueError."""
        with pytest.raises(ValueError, match="quantity_delta cannot be zero"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.ADJ,
                quantity_delta=Decimal("0"),
            )

    def test_record_movement_invalid_type_raises_error(self, tenant_context, product, branch):
        """Test that invalid movement type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid movement type"):
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=str(branch.id),
                movement_type="INVALID_TYPE",
                quantity_delta=Decimal("10.0000"),
            )

    def test_record_movement_insufficient_stock_raises_error(self, tenant_context, product, branch):
        """Test that sale with insufficient stock raises InsufficientStockError."""
        with pytest.raises(InsufficientStockError) as exc_info:
            StockService.record_movement(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=str(branch.id),
                movement_type=StockMovement.MovementType.SALE,
                quantity_delta=Decimal("-50.0000"),
            )
        assert exc_info.value.available == Decimal("0")
        assert exc_info.value.requested == Decimal("50.0000")


@pytest.mark.django_db
class TestCreateCorrection:
    """Tests for StockService.create_correction method."""

    def test_create_correction_increases_stock(self, tenant_context, product, branch):
        """Test correction that increases stock quantity."""
        movement = StockService.create_correction(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            new_quantity=Decimal("75.0000"),
            reason="Physical count adjustment",
        )

        assert movement.type == StockMovement.MovementType.ADJ
        assert movement.quantity_delta == Decimal("75.0000")
        assert "Physical count adjustment" in movement.notes

        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("75.0000")

    def test_create_correction_decreases_stock(self, tenant_context, product, branch):
        """Test correction that decreases stock quantity."""
        # First add stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )

        # Then correct to lower amount
        movement = StockService.create_correction(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            new_quantity=Decimal("80.0000"),
            reason="Damaged goods write-off",
        )

        assert movement.quantity_delta == Decimal("-20.0000")
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.quantity == Decimal("80.0000")

    def test_create_correction_requires_reason(self, tenant_context, product, branch):
        """Test that empty reason raises ValueError."""
        with pytest.raises(ValueError, match="Reason is required"):
            StockService.create_correction(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=str(branch.id),
                new_quantity=Decimal("50.0000"),
                reason="",
            )

    def test_create_correction_negative_quantity_raises_error(self, tenant_context, product, branch):
        """Test that negative new_quantity raises ValueError."""
        with pytest.raises(ValueError, match="new_quantity cannot be negative"):
            StockService.create_correction(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                branch_id=str(branch.id),
                new_quantity=Decimal("-10.0000"),
                reason="Test",
            )


@pytest.mark.django_db
class TestReserveStock:
    """Tests for StockService.reserve_stock method."""

    def test_reserve_stock_success(self, tenant_context, product, branch):
        """Test successful stock reservation."""
        # Add stock first
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )

        result = StockService.reserve_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("30.0000"),
        )

        assert result is True
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.reserved_quantity == Decimal("30.0000")
        assert snapshot.available_quantity == Decimal("70.0000")

    def test_reserve_stock_insufficient_raises_error(self, tenant_context, product, branch):
        """Test reservation with insufficient stock raises InsufficientStockError."""
        # Add some stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("20.0000"),
        )

        with pytest.raises(InsufficientStockError) as exc_info:
            StockService.reserve_stock(
                product_id=str(product.id),
                branch_id=str(branch.id),
                quantity=Decimal("50.0000"),
            )
        assert exc_info.value.available == Decimal("20.0000")
        assert exc_info.value.requested == Decimal("50.0000")

    def test_reserve_stock_no_snapshot_raises_error(self, tenant_context, product, branch):
        """Test reservation when no snapshot exists raises InsufficientStockError."""
        with pytest.raises(InsufficientStockError) as exc_info:
            StockService.reserve_stock(
                product_id=str(product.id),
                branch_id=str(branch.id),
                quantity=Decimal("10.0000"),
            )
        assert exc_info.value.available == Decimal("0.0000")

    def test_reserve_stock_zero_quantity_raises_error(self, tenant_context, product, branch):
        """Test that zero quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity to reserve must be positive"):
            StockService.reserve_stock(
                product_id=str(product.id),
                branch_id=str(branch.id),
                quantity=Decimal("0"),
            )


@pytest.mark.django_db
class TestReleaseStock:
    """Tests for StockService.release_stock method."""

    def test_release_stock_success(self, tenant_context, product, branch):
        """Test successful stock release."""
        # Add and reserve stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )
        StockService.reserve_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("50.0000"),
        )

        # Release some stock
        result = StockService.release_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("20.0000"),
        )

        assert result is True
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.reserved_quantity == Decimal("30.0000")
        assert snapshot.available_quantity == Decimal("70.0000")

    def test_release_stock_exceeds_reserved_raises_error(self, tenant_context, product, branch):
        """Test releasing more than reserved raises ValueError."""
        # Add and reserve stock
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )
        StockService.reserve_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("30.0000"),
        )

        with pytest.raises(ValueError, match="Cannot release"):
            StockService.release_stock(
                product_id=str(product.id),
                branch_id=str(branch.id),
                quantity=Decimal("50.0000"),
            )

    def test_release_stock_no_snapshot_raises_error(self, tenant_context, product, branch):
        """Test releasing from non-existent snapshot raises ValueError."""
        with pytest.raises(ValueError, match="No stock snapshot found"):
            StockService.release_stock(
                product_id=str(product.id),
                branch_id=str(branch.id),
                quantity=Decimal("10.0000"),
            )


@pytest.mark.django_db
class TestTransferStock:
    """Tests for StockService.transfer_stock method."""

    def test_transfer_stock_success(self, tenant_context, product, branch):
        """Test successful stock transfer between branches."""
        from apps.core.models.branch import Branch

        # Create second branch
        branch2 = Branch.objects.create(
            tenant=tenant_context,
            name="Branch 2",
            is_active=True,
        )

        # Add stock to source branch
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )

        # Transfer stock
        out_movement, in_movement = StockService.transfer_stock(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            from_branch_id=str(branch.id),
            to_branch_id=str(branch2.id),
            quantity=Decimal("40.0000"),
            notes="Restock branch 2",
        )

        # Verify movements
        assert out_movement.type == StockMovement.MovementType.TRANS_OUT
        assert out_movement.quantity_delta == Decimal("-40.0000")
        assert in_movement.type == StockMovement.MovementType.TRANS_IN
        assert in_movement.quantity_delta == Decimal("40.0000")
        assert out_movement.reference_id == in_movement.reference_id

        # Verify snapshots
        source_snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        dest_snapshot = StockSnapshot.objects.get(product=product, branch=branch2)
        assert source_snapshot.quantity == Decimal("60.0000")
        assert dest_snapshot.quantity == Decimal("40.0000")

    def test_transfer_stock_same_branch_raises_error(self, tenant_context, product, branch):
        """Test transfer to same branch raises ValueError."""
        with pytest.raises(ValueError, match="must be different"):
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id=str(branch.id),
                to_branch_id=str(branch.id),
                quantity=Decimal("10.0000"),
            )

    def test_transfer_stock_zero_quantity_raises_error(self, tenant_context, product, branch):
        """Test transfer with zero quantity raises ValueError."""
        from apps.core.models.branch import Branch

        branch2 = Branch.objects.create(
            tenant=tenant_context,
            name="Branch 2",
            is_active=True,
        )

        with pytest.raises(ValueError, match="must be positive"):
            StockService.transfer_stock(
                tenant_id=str(tenant_context.id),
                product_id=str(product.id),
                from_branch_id=str(branch.id),
                to_branch_id=str(branch2.id),
                quantity=Decimal("0"),
            )


@pytest.mark.django_db
class TestGetCurrentStock:
    """Tests for StockService.get_current_stock method."""

    def test_get_current_stock_with_snapshot(self, tenant_context, product, branch):
        """Test getting current stock when snapshot exists."""
        # Add stock and reserve some
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )
        StockService.reserve_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("25.0000"),
        )

        total, reserved, available = StockService.get_current_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
        )

        assert total == Decimal("100.0000")
        assert reserved == Decimal("25.0000")
        assert available == Decimal("75.0000")

    def test_get_current_stock_no_snapshot(self, tenant_context, product, branch):
        """Test getting current stock when no snapshot exists returns zeros."""
        total, reserved, available = StockService.get_current_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
        )

        assert total == Decimal("0.0000")
        assert reserved == Decimal("0.0000")
        assert available == Decimal("0.0000")


@pytest.mark.django_db
class TestGetStockAtPointInTime:
    """Tests for StockService.get_stock_at_point_in_time method."""

    def test_get_stock_at_point_in_time(self, tenant_context, product, branch):
        """Test reconstructing stock at a specific point in time."""
        # Record a series of movements
        _now = timezone.now()

        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-30.0000"),
        )

        # Get stock at current time (should include all movements)
        stock = StockService.get_stock_at_point_in_time(
            product_id=str(product.id),
            branch_id=str(branch.id),
            at_datetime=timezone.now(),
        )
        assert stock == Decimal("70.0000")

    def test_get_stock_at_point_in_time_no_movements(self, tenant_context, product, branch):
        """Test getting stock when no movements exist returns zero."""
        stock = StockService.get_stock_at_point_in_time(
            product_id=str(product.id),
            branch_id=str(branch.id),
            at_datetime=timezone.now(),
        )
        assert stock == Decimal("0.0000")


@pytest.mark.django_db
class TestGetProductStockSummary:
    """Tests for StockService.get_product_stock_summary method."""

    def test_get_product_stock_summary(self, tenant_context, product, branch):
        """Test getting stock summary across branches."""
        from apps.core.models.branch import Branch

        # Create second branch
        branch2 = Branch.objects.create(
            tenant=tenant_context,
            name="Branch 2",
            is_active=True,
        )

        # Add stock to both branches
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("100.0000"),
        )
        StockService.record_movement(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
            branch_id=str(branch2.id),
            movement_type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50.0000"),
        )

        # Reserve some stock
        StockService.reserve_stock(
            product_id=str(product.id),
            branch_id=str(branch.id),
            quantity=Decimal("20.0000"),
        )

        summary = StockService.get_product_stock_summary(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
        )

        assert summary["product_id"] == str(product.id)
        assert summary["product_sku"] == product.sku
        assert summary["total_quantity"] == Decimal("150.0000")
        assert summary["total_reserved"] == Decimal("20.0000")
        assert summary["total_available"] == Decimal("130.0000")
        assert len(summary["branches"]) == 2

    def test_get_product_stock_summary_no_stock(self, tenant_context, product, branch):
        """Test getting summary when no stock exists."""
        summary = StockService.get_product_stock_summary(
            tenant_id=str(tenant_context.id),
            product_id=str(product.id),
        )

        assert summary["total_quantity"] == Decimal("0.0000")
        assert len(summary["branches"]) == 0
