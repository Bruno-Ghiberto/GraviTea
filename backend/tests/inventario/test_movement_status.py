"""
T086: StockMovement status transition and immutability unit tests.

Tests the save() enforcement logic at inventario/models.py:726-775:
- RESERVED → COMMITTED/CANCELLED transitions are allowed
- COMMITTED and CANCELLED movements are fully immutable
- Only status and comprobante_id fields may change on RESERVED movements
- delete() always raises ValueError (immutable ledger)
"""

import uuid
from decimal import Decimal

import pytest

from apps.inventario.models import StockMovement


@pytest.mark.unit
@pytest.mark.django_db
class TestStockMovementStatusTransitions:
    """T086: StockMovement status lifecycle enforcement."""

    def _create_reserved_movement(self, tenant_context, branch, product):
        """Helper: create a COMMITTED movement then force status to RESERVED via queryset update."""
        mv = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-5.0000"),
            cost_snapshot=product.cost_price,
            reference_id=uuid.uuid4(),
            notes="Reserved for sale",
        )
        # Force status to RESERVED bypassing save() validation
        StockMovement.all_objects.filter(pk=mv.pk).update(
            status=StockMovement.StockMovementStatus.RESERVED,
        )
        mv.refresh_from_db()
        assert mv.status == StockMovement.StockMovementStatus.RESERVED
        return mv

    def test_reserved_to_committed(self, tenant_context, branch, product):
        """RESERVED → COMMITTED is a valid transition."""
        mv = self._create_reserved_movement(tenant_context, branch, product)

        mv.status = StockMovement.StockMovementStatus.COMMITTED
        mv.save()

        mv.refresh_from_db()
        assert mv.status == StockMovement.StockMovementStatus.COMMITTED

    def test_reserved_to_cancelled(self, tenant_context, branch, product):
        """RESERVED → CANCELLED is a valid transition."""
        mv = self._create_reserved_movement(tenant_context, branch, product)

        mv.status = StockMovement.StockMovementStatus.CANCELLED
        mv.save()

        mv.refresh_from_db()
        assert mv.status == StockMovement.StockMovementStatus.CANCELLED

    def test_committed_is_immutable(self, tenant_context, branch, product):
        """COMMITTED movements cannot be modified at all."""
        mv = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.SALE,
            quantity_delta=Decimal("-3.0000"),
            cost_snapshot=product.cost_price,
            reference_id=uuid.uuid4(),
        )
        assert mv.status == StockMovement.StockMovementStatus.COMMITTED

        mv.status = StockMovement.StockMovementStatus.CANCELLED
        with pytest.raises(ValueError, match="immutable"):
            mv.save()

    def test_cancelled_is_immutable(self, tenant_context, branch, product):
        """CANCELLED movements cannot be modified at all."""
        mv = self._create_reserved_movement(tenant_context, branch, product)

        # Transition to CANCELLED
        mv.status = StockMovement.StockMovementStatus.CANCELLED
        mv.save()
        mv.refresh_from_db()

        # Try to change back to RESERVED
        mv.status = StockMovement.StockMovementStatus.RESERVED
        with pytest.raises(ValueError, match="immutable"):
            mv.save()

    def test_reserved_field_change_blocked(self, tenant_context, branch, product):
        """Changing non-allowed fields on RESERVED movement raises ValueError."""
        mv = self._create_reserved_movement(tenant_context, branch, product)

        # Try to change quantity_delta (not in allowed set)
        mv.quantity_delta = Decimal("-99.0000")
        mv.status = StockMovement.StockMovementStatus.COMMITTED
        with pytest.raises(ValueError, match="Cannot modify field"):
            mv.save()

    def test_new_movement_defaults_to_committed(self, tenant_context, branch, product):
        """New movements default to COMMITTED status."""
        mv = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("10.0000"),
            cost_snapshot=product.cost_price,
            reference_id=uuid.uuid4(),
        )
        assert mv.status == StockMovement.StockMovementStatus.COMMITTED

    def test_delete_always_raises(self, tenant_context, branch, product):
        """delete() on any movement raises ValueError (immutable ledger)."""
        mv = StockMovement.objects.create(
            tenant=tenant_context,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.PURCHASE,
            quantity_delta=Decimal("10.0000"),
            cost_snapshot=product.cost_price,
            reference_id=uuid.uuid4(),
        )
        with pytest.raises(ValueError, match="cannot be deleted"):
            mv.delete()
