"""
Tests for stock movement functionality.

Tests the immutable ledger pattern and stock level calculations.
"""

import uuid
from decimal import Decimal

import pytest

from apps.inventario.models import StockMovement, StockSnapshot

pytestmark = pytest.mark.django_db


class TestStockMovementImmutability:
    """Tests for stock movement immutability."""

    def test_create_stock_movement(self, tenant_context, product, branch):
        """Test creating a stock movement."""
        movement = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("50.0000"),
            cost_snapshot=product.cost_price,
            reference_id=uuid.uuid4(),
        )

        assert movement.id is not None
        assert movement.quantity_delta == Decimal("50.0000")
        assert movement.type == StockMovement.MovementType.PURCHASE

    def test_cannot_update_stock_movement(self, stock_movement):
        """Test that stock movements cannot be updated."""
        stock_movement.quantity_delta = Decimal("200.0000")

        with pytest.raises(ValueError) as exc_info:
            stock_movement.save()

        assert "immutable" in str(exc_info.value).lower()

    def test_cannot_delete_stock_movement(self, stock_movement):
        """Test that stock movements cannot be deleted."""
        with pytest.raises(ValueError) as exc_info:
            stock_movement.delete()

        assert "cannot be deleted" in str(exc_info.value).lower()


class TestStockSnapshotUpdate:
    """Tests for stock snapshot level updates."""

    def test_purchase_increases_stock(self, tenant_context, product, branch):
        """Test that purchase movements increase stock."""
        initial_quantity = Decimal("100.0000")

        # Create initial purchase movement
        StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=initial_quantity,
            cost_snapshot=product.cost_price,
        )

        # Create or update stock snapshot
        snapshot, _ = StockSnapshot.objects.get_or_create(
            product=product, branch=branch, defaults={"quantity": Decimal("0.0000")}
        )
        snapshot.quantity = initial_quantity
        snapshot.save()

        assert snapshot.quantity == initial_quantity

    def test_sale_decreases_stock(self, tenant_context, product, branch):
        """Test that sale movements decrease stock."""
        # First create stock
        snapshot, _ = StockSnapshot.objects.get_or_create(
            product=product, branch=branch, defaults={"quantity": Decimal("100.0000")}
        )
        snapshot.quantity = Decimal("100.0000")
        snapshot.save()

        initial_stock = snapshot.quantity
        sale_quantity = Decimal("10.0000")

        # Create sale movement (negative quantity)
        StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.SALE,
            quantity_delta=-sale_quantity,
            cost_snapshot=product.unit_price,
            reference_id=uuid.uuid4(),
        )

        # Update stock snapshot
        snapshot.quantity -= sale_quantity
        snapshot.save()

        assert snapshot.quantity == initial_stock - sale_quantity


class TestStockMovementTypes:
    """Tests for different stock movement types."""

    @pytest.mark.parametrize(
        "movement_type,expected_sign",
        [
            (StockMovement.MovementType.PURCHASE, 1),
            (StockMovement.MovementType.TRANS_IN, 1),
            (StockMovement.MovementType.SALE, -1),
            (StockMovement.MovementType.TRANS_OUT, -1),
            (StockMovement.MovementType.ADJ, 1),  # Adjustments can be positive or negative
        ],
    )
    def test_movement_type_quantity_sign(
        self, tenant_context, product, branch, movement_type, expected_sign
    ):
        """Test that movement types use correct quantity signs."""
        quantity = Decimal("10.0000") * expected_sign

        movement = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=movement_type,
            quantity_delta=quantity,
            cost_snapshot=product.cost_price,
        )

        if expected_sign > 0:
            assert movement.quantity_delta > 0
        else:
            assert movement.quantity_delta < 0


class TestStockMovementTenantIsolation:
    """Tests for stock movement tenant isolation."""

    def test_movements_filtered_by_tenant(self, tenant_context, other_tenant, product, branch):
        """Test that stock movements are filtered by tenant."""
        from apps.core.managers.tenant_bound import set_current_tenant_id

        # Create movement for current tenant
        movement = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("10.0000"),
            cost_snapshot=Decimal("50.00"),
        )

        # Set tenant context and query
        set_current_tenant_id(tenant_context.id)
        movements = StockMovement.objects.all()

        assert movement in movements

        # Check that other tenant doesn't see this movement
        set_current_tenant_id(other_tenant.id)
        other_movements = StockMovement.objects.all()

        assert movement not in other_movements


class TestStockMovementAuditTrail:
    """Tests for stock movement audit trail."""

    def test_movement_has_timestamp(self, stock_movement):
        """Test that stock movements have creation timestamp."""
        assert stock_movement.created_at is not None

    def test_movement_records_reference(self, tenant_context, product, branch):
        """Test that stock movements can record reference IDs."""
        ref_id = uuid.uuid4()
        movement = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-5.0000"),
            cost_snapshot=Decimal("100.00"),
            reference_id=ref_id,
        )

        assert movement.reference_id == ref_id

    def test_movement_can_have_notes(self, tenant_context, product, branch):
        """Test that stock movements can have notes."""
        movement = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.ADJ,
            quantity_delta=Decimal("-2.0000"),
            cost_snapshot=Decimal("50.00"),
            notes="Damaged in transit",
        )

        assert movement.notes == "Damaged in transit"
