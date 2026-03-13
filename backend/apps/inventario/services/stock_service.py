"""
Stock management service layer for Gravitea ERP.

Provides business logic for stock operations using the immutable ledger pattern.
All stock changes go through this service to ensure:
- Proper movement recording
- Snapshot updates
- Tenant isolation
- Audit trail
"""

import json as _json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.models.branch import Branch
from apps.core.validators import validate_uuid
from apps.inventario.models import Product, StockMovement, StockSnapshot

logger = logging.getLogger(__name__)

try:
    from gravitea_rust import aggregate_stock_levels as _rust_aggregate_stock  # type: ignore[import]

    _USE_RUST_COMPUTE = True
except (ImportError, OSError):
    _USE_RUST_COMPUTE = False
    logging.getLogger(__name__).warning(
        "gravitea_rust compute not available — using Python fallback"
    )


class InsufficientStockError(Exception):
    """Raised when stock is insufficient for the operation."""

    def __init__(
        self,
        product_id: str,
        branch_id: str,
        available: Decimal,
        requested: Decimal,
        *,
        product_sku: str | None = None,
        product_name: str | None = None,
        branch_name: str | None = None,
    ):
        self.product_id = product_id
        self.branch_id = branch_id
        self.available = available
        self.requested = requested
        self.product_sku = product_sku
        self.product_name = product_name
        self.branch_name = branch_name
        label = product_sku or product_id
        super().__init__(
            f"Insufficient stock for product {label} at branch {branch_name or branch_id}: "
            f"available={available}, requested={requested}"
        )


class ProductNotFoundError(Exception):
    """Raised when a product does not exist."""

    def __init__(self, product_id: str, tenant_id: str):
        self.product_id = product_id
        self.tenant_id = tenant_id
        super().__init__(
            f"Product not found: {product_id} for tenant {tenant_id}"
        )


class BranchNotFoundError(Exception):
    """Raised when a branch does not exist."""

    def __init__(self, branch_id: str, tenant_id: str):
        self.branch_id = branch_id
        self.tenant_id = tenant_id
        super().__init__(
            f"Branch not found: {branch_id} for tenant {tenant_id}"
        )


class StockService:
    """
    Stock management service with immutable ledger pattern.

    All stock changes go through this service to ensure:
    - Proper movement recording
    - Snapshot updates
    - Tenant isolation
    - Audit trail
    """

    @staticmethod
    @transaction.atomic
    def record_movement(
        tenant_id: str,
        product_id: str,
        branch_id: str,
        movement_type: str,  # SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT
        quantity_delta: Decimal,
        cost_snapshot: Optional[Decimal] = None,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> StockMovement:
        """
        Record a stock movement and update the snapshot.

        Args:
            tenant_id: Tenant UUID
            product_id: Product UUID
            branch_id: Branch UUID
            movement_type: Type of movement
            quantity_delta: Quantity change (positive=in, negative=out)
            cost_snapshot: Optional cost at time of movement
            reference_id: Optional reference to sale/purchase
            notes: Optional notes

        Returns:
            The created StockMovement

        Raises:
            ValueError: If quantity_delta is zero or invalid movement type
            InsufficientStockError: If sale/out would result in negative stock
        """
        # Validate quantity_delta
        if quantity_delta == 0:
            raise ValueError("quantity_delta cannot be zero")

        # Validate movement type
        valid_types = [choice[0] for choice in StockMovement.MovementType.choices]
        if movement_type not in valid_types:
            raise ValueError(
                f"Invalid movement type: {movement_type}. Must be one of {valid_types}"
            )

        # Validate and convert UUIDs
        try:
            tenant_uuid = validate_uuid(tenant_id, "tenant_id")
            product_uuid = validate_uuid(product_id, "product_id")
            branch_uuid = validate_uuid(branch_id, "branch_id")
            reference_uuid = validate_uuid(reference_id, "reference_id", allow_none=True)
        except Exception as e:
            logger.error(f"UUID validation failed in record_movement: {str(e)}")
            raise ValueError(f"Invalid UUID parameter: {str(e)}")

        # Get product and branch with proper error handling
        try:
            product = Product.objects.get(id=product_uuid, tenant_id=tenant_uuid)
        except Product.DoesNotExist:
            logger.warning(
                f"Product not found: {product_id} for tenant {tenant_id}",
                extra={"product_id": str(product_id), "tenant_id": str(tenant_id)},
            )
            raise ProductNotFoundError(str(product_id), str(tenant_id))

        try:
            branch = Branch.objects.get(id=branch_uuid, tenant_id=tenant_uuid)
        except Branch.DoesNotExist:
            logger.warning(
                f"Branch not found: {branch_id} for tenant {tenant_id}",
                extra={"branch_id": str(branch_id), "tenant_id": str(tenant_id)},
            )
            raise BranchNotFoundError(str(branch_id), str(tenant_id))

        # Get or create stock snapshot with row-level lock
        snapshot, created = StockSnapshot.objects.select_for_update().get_or_create(
            product=product,
            branch=branch,
            defaults={
                "quantity": Decimal("0.0000"),
                "reserved_quantity": Decimal("0.0000"),
            },
        )

        # Check if operation would result in negative stock for outbound movements
        new_quantity = snapshot.quantity + quantity_delta
        if quantity_delta < 0 and new_quantity < 0:
            raise InsufficientStockError(
                product_id=str(product_id),
                branch_id=str(branch_id),
                available=snapshot.quantity,
                requested=abs(quantity_delta),
            )

        # Create the movement (immutable ledger entry)
        movement = StockMovement.objects.create(
            tenant_id=tenant_uuid,
            product=product,
            branch=branch,
            type=movement_type,
            quantity_delta=quantity_delta,
            cost_snapshot=cost_snapshot,
            reference_id=reference_uuid,
            notes=notes,
        )

        # Update the snapshot
        snapshot.quantity = new_quantity
        snapshot.save(update_fields=["quantity", "last_updated"])

        logger.info(
            f"Stock movement recorded: type={movement_type}, "
            f"product={product.sku}, branch={branch.name}, "
            f"delta={quantity_delta}, new_quantity={new_quantity}"
        )

        return movement

    @staticmethod
    @transaction.atomic
    def create_correction(
        tenant_id: str,
        product_id: str,
        branch_id: str,
        new_quantity: Decimal,
        reason: str,
    ) -> StockMovement:
        """
        Create an adjustment to correct stock to a specific level.

        Args:
            tenant_id: Tenant UUID
            product_id: Product UUID
            branch_id: Branch UUID
            new_quantity: Target stock quantity
            reason: Reason for correction (required for audit)

        Returns:
            The adjustment StockMovement

        Raises:
            ValueError: If reason is empty
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is required for stock corrections (audit trail)")

        if new_quantity < 0:
            raise ValueError("new_quantity cannot be negative")

        # Validate and convert UUIDs
        try:
            tenant_uuid = validate_uuid(tenant_id, "tenant_id")
            product_uuid = validate_uuid(product_id, "product_id")
            branch_uuid = validate_uuid(branch_id, "branch_id")
        except Exception as e:
            logger.error(f"UUID validation failed in create_correction: {str(e)}")
            raise ValueError(f"Invalid UUID parameter: {str(e)}")

        # Get product and branch with proper error handling
        try:
            product = Product.objects.get(id=product_uuid, tenant_id=tenant_uuid)
        except Product.DoesNotExist:
            logger.warning(
                f"Product not found: {product_id} for tenant {tenant_id}",
                extra={"product_id": str(product_id), "tenant_id": str(tenant_id)},
            )
            raise ProductNotFoundError(str(product_id), str(tenant_id))

        try:
            branch = Branch.objects.get(id=branch_uuid, tenant_id=tenant_uuid)
        except Branch.DoesNotExist:
            logger.warning(
                f"Branch not found: {branch_id} for tenant {tenant_id}",
                extra={"branch_id": str(branch_id), "tenant_id": str(tenant_id)},
            )
            raise BranchNotFoundError(str(branch_id), str(tenant_id))

        # Get current stock with lock
        snapshot, created = StockSnapshot.objects.select_for_update().get_or_create(
            product=product,
            branch=branch,
            defaults={
                "quantity": Decimal("0.0000"),
                "reserved_quantity": Decimal("0.0000"),
            },
        )

        current_quantity = snapshot.quantity
        quantity_delta = new_quantity - current_quantity

        # If no change needed, return without creating movement
        if quantity_delta == 0:
            logger.info(
                f"Stock correction skipped - no change needed: "
                f"product={product.sku}, branch={branch.name}, quantity={current_quantity}"
            )
            # Still create a movement for audit trail
            pass

        # Create adjustment movement with reason in notes
        notes = f"Stock correction: {reason}\nOld quantity: {current_quantity}, New quantity: {new_quantity}"

        movement = StockMovement.objects.create(
            tenant_id=tenant_uuid,
            product=product,
            branch=branch,
            type=StockMovement.MovementType.ADJ,
            quantity_delta=quantity_delta,
            cost_snapshot=product.cost_price,
            notes=notes,
        )

        # Update snapshot
        snapshot.quantity = new_quantity
        snapshot.save(update_fields=["quantity", "last_updated"])

        logger.info(
            f"Stock correction recorded: product={product.sku}, branch={branch.name}, "
            f"old={current_quantity}, new={new_quantity}, delta={quantity_delta}, reason={reason}"
        )

        return movement

    @staticmethod
    def get_stock_at_point_in_time(
        product_id: str,
        branch_id: str,
        at_datetime: datetime,
    ) -> Decimal:
        """
        Reconstruct stock level at a specific point in time.

        Uses the immutable ledger to calculate stock by summing
        all movements up to the specified timestamp.

        Args:
            product_id: Product UUID
            branch_id: Branch UUID
            at_datetime: Point in time to calculate stock

        Returns:
            Stock quantity at that point in time
        """
        # Convert string IDs to UUIDs
        product_uuid = uuid.UUID(product_id) if isinstance(product_id, str) else product_id
        branch_uuid = uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id

        # Ensure timezone-aware datetime
        if timezone.is_naive(at_datetime):
            at_datetime = timezone.make_aware(at_datetime)

        # Sum all movements up to the specified time
        result = StockMovement.objects.filter(
            product_id=product_uuid,
            branch_id=branch_uuid,
            created_at__lte=at_datetime,
        ).aggregate(total=Sum("quantity_delta"))

        total = result["total"] or Decimal("0.0000")

        logger.debug(
            f"Stock at point in time: product={product_id}, branch={branch_id}, "
            f"at={at_datetime}, quantity={total}"
        )

        return total

    @staticmethod
    @transaction.atomic
    def reserve_stock(
        product_id: str,
        branch_id: str,
        quantity: Decimal,
        *,
        tenant_id: str | None = None,
        sale_order_id: str | None = None,
        notes: str | None = None,
    ) -> "StockMovement | bool":
        """
        Reserve stock for a pending order.

        When tenant_id and sale_order_id are provided (T046), also creates
        a StockMovement with status=RESERVED and the sale_order FK.

        Args:
            product_id: Product UUID
            branch_id: Branch UUID
            quantity: Quantity to reserve
            tenant_id: Tenant UUID (enables movement creation)
            sale_order_id: SaleOrder UUID (sets FK on movement)
            notes: Optional notes for the movement

        Returns:
            StockMovement if tenant_id provided, True otherwise

        Raises:
            InsufficientStockError: If not enough available stock
            ValueError: If quantity is not positive
        """
        if quantity <= 0:
            raise ValueError("Quantity to reserve must be positive")

        # Convert string IDs to UUIDs
        product_uuid = uuid.UUID(product_id) if isinstance(product_id, str) else product_id
        branch_uuid = uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id

        # Get snapshot with lock
        try:
            snapshot = StockSnapshot.objects.select_for_update().get(
                product_id=product_uuid,
                branch_id=branch_uuid,
            )
        except StockSnapshot.DoesNotExist:
            raise InsufficientStockError(
                product_id=str(product_id),
                branch_id=str(branch_id),
                available=Decimal("0.0000"),
                requested=quantity,
            )

        # Check available stock (quantity - reserved)
        available = snapshot.quantity - snapshot.reserved_quantity
        if available < quantity:
            raise InsufficientStockError(
                product_id=str(product_id),
                branch_id=str(branch_id),
                available=available,
                requested=quantity,
            )

        # Update reserved quantity
        snapshot.reserved_quantity += quantity
        snapshot.save(update_fields=["reserved_quantity", "last_updated"])

        logger.info(
            f"Stock reserved: product={product_id}, branch={branch_id}, "
            f"quantity={quantity}, new_reserved={snapshot.reserved_quantity}"
        )

        # T046: Create RESERVED movement when sale context is provided
        if tenant_id and sale_order_id:
            tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
            so_uuid = uuid.UUID(sale_order_id) if isinstance(sale_order_id, str) else sale_order_id

            movement = StockMovement.objects.create(
                tenant_id=tenant_uuid,
                product_id=product_uuid,
                branch_id=branch_uuid,
                type=StockMovement.MovementType.SALE,
                status=StockMovement.StockMovementStatus.RESERVED,
                quantity_delta=-quantity,
                sale_order_id=so_uuid,
                notes=notes or f"Stock reservation for sale order",
            )
            return movement

        return True

    @staticmethod
    @transaction.atomic
    def commit_reservation(
        sale_order_id: str,
        comprobante_id: str,
    ) -> list:
        """
        Commit reserved stock after successful ARCA authorization (T047).

        Finds all RESERVED movements for the sale order, transitions them
        to COMMITTED, sets the comprobante FK, and updates snapshots.

        Args:
            sale_order_id: SaleOrder UUID
            comprobante_id: Authorized Comprobante UUID

        Returns:
            List of committed StockMovement instances

        Raises:
            ValueError: If no RESERVED movements found
        """
        so_uuid = uuid.UUID(sale_order_id) if isinstance(sale_order_id, str) else sale_order_id
        comp_uuid = uuid.UUID(comprobante_id) if isinstance(comprobante_id, str) else comprobante_id

        # Find all RESERVED movements for this sale order
        movements = list(
            StockMovement.objects.select_for_update().filter(
                sale_order_id=so_uuid,
                status=StockMovement.StockMovementStatus.RESERVED,
            )
        )

        if not movements:
            raise ValueError(
                f"No RESERVED movements found for sale order {sale_order_id}"
            )

        for movement in movements:
            # Transition RESERVED → COMMITTED (allowed by model save())
            movement.status = StockMovement.StockMovementStatus.COMMITTED
            movement.comprobante_id = comp_uuid
            movement.save()

            # Update snapshot: deduct from quantity and reserved_quantity
            snapshot = StockSnapshot.objects.select_for_update().get(
                product_id=movement.product_id,
                branch_id=movement.branch_id,
            )
            qty = abs(movement.quantity_delta)
            snapshot.quantity -= qty
            snapshot.reserved_quantity -= qty
            snapshot.save(update_fields=["quantity", "reserved_quantity", "last_updated"])

        logger.info(
            "Stock committed: sale_order=%s comprobante=%s movements=%d",
            str(so_uuid)[:8],
            str(comp_uuid)[:8],
            len(movements),
        )

        return movements

    @staticmethod
    @transaction.atomic
    def cancel_reservation(
        sale_order_id: str,
    ) -> list:
        """
        Cancel reserved stock after ARCA rejection (T055).

        Finds all RESERVED movements for the sale order, transitions them
        to CANCELLED, and releases the reserved quantity on snapshots.

        Args:
            sale_order_id: SaleOrder UUID

        Returns:
            List of cancelled StockMovement instances

        Raises:
            ValueError: If no RESERVED movements found
        """
        so_uuid = uuid.UUID(sale_order_id) if isinstance(sale_order_id, str) else sale_order_id

        # Find all RESERVED movements for this sale order
        movements = list(
            StockMovement.objects.select_for_update().filter(
                sale_order_id=so_uuid,
                status=StockMovement.StockMovementStatus.RESERVED,
            )
        )

        if not movements:
            raise ValueError(
                f"No RESERVED movements found for sale order {sale_order_id}"
            )

        for movement in movements:
            # Transition RESERVED → CANCELLED (allowed by model save())
            movement.status = StockMovement.StockMovementStatus.CANCELLED
            movement.save()

            # Release reserved quantity on snapshot
            snapshot = StockSnapshot.objects.select_for_update().get(
                product_id=movement.product_id,
                branch_id=movement.branch_id,
            )
            qty = abs(movement.quantity_delta)
            snapshot.reserved_quantity -= qty
            snapshot.save(update_fields=["reserved_quantity", "last_updated"])

        logger.info(
            "Stock reservation cancelled: sale_order=%s movements=%d",
            str(so_uuid)[:8],
            len(movements),
        )

        return movements

    @staticmethod
    @transaction.atomic
    def release_stock(
        product_id: str,
        branch_id: str,
        quantity: Decimal,
    ) -> bool:
        """
        Release previously reserved stock.

        Args:
            product_id: Product UUID
            branch_id: Branch UUID
            quantity: Quantity to release

        Returns:
            True if release successful

        Raises:
            ValueError: If quantity is not positive or exceeds reserved quantity
        """
        if quantity <= 0:
            raise ValueError("Quantity to release must be positive")

        # Convert string IDs to UUIDs
        product_uuid = uuid.UUID(product_id) if isinstance(product_id, str) else product_id
        branch_uuid = uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id

        # Get snapshot with lock
        try:
            snapshot = StockSnapshot.objects.select_for_update().get(
                product_id=product_uuid,
                branch_id=branch_uuid,
            )
        except StockSnapshot.DoesNotExist:
            raise ValueError(
                f"No stock snapshot found for product {product_id} at branch {branch_id}"
            )

        # Check if we have enough reserved stock
        if snapshot.reserved_quantity < quantity:
            raise ValueError(
                f"Cannot release {quantity} - only {snapshot.reserved_quantity} is reserved"
            )

        # Update reserved quantity
        snapshot.reserved_quantity -= quantity
        snapshot.save(update_fields=["reserved_quantity", "last_updated"])

        logger.info(
            f"Stock released: product={product_id}, branch={branch_id}, "
            f"quantity={quantity}, new_reserved={snapshot.reserved_quantity}"
        )

        return True

    @staticmethod
    @transaction.atomic
    def transfer_stock(
        tenant_id: str,
        product_id: str,
        from_branch_id: str,
        to_branch_id: str,
        quantity: Decimal,
        notes: Optional[str] = None,
    ) -> Tuple[StockMovement, StockMovement]:
        """
        Transfer stock between branches.

        Creates two movements: TRANS_OUT from source, TRANS_IN to destination.
        Uses same reference_id to link the movements.

        Args:
            tenant_id: Tenant UUID
            product_id: Product UUID
            from_branch_id: Source branch UUID
            to_branch_id: Destination branch UUID
            quantity: Quantity to transfer (must be positive)
            notes: Optional transfer notes

        Returns:
            Tuple of (trans_out_movement, trans_in_movement)

        Raises:
            InsufficientStockError: If source doesn't have enough stock
            ValueError: If quantity is not positive or branches are the same
        """
        if quantity <= 0:
            raise ValueError("Transfer quantity must be positive")

        # Validate and convert UUIDs
        try:
            tenant_uuid = validate_uuid(tenant_id, "tenant_id")
            product_uuid = validate_uuid(product_id, "product_id")
            from_branch_uuid = validate_uuid(from_branch_id, "from_branch_id")
            to_branch_uuid = validate_uuid(to_branch_id, "to_branch_id")
        except Exception as e:
            logger.error(f"UUID validation failed in transfer_stock: {str(e)}")
            raise ValueError(f"Invalid UUID parameter: {str(e)}")

        if from_branch_uuid == to_branch_uuid:
            raise ValueError("Source and destination branches must be different")

        # Get product and branches with proper error handling
        try:
            product = Product.objects.get(id=product_uuid, tenant_id=tenant_uuid)
        except Product.DoesNotExist:
            logger.warning(
                f"Product not found: {product_id} for tenant {tenant_id}",
                extra={"product_id": str(product_id), "tenant_id": str(tenant_id)},
            )
            raise ProductNotFoundError(str(product_id), str(tenant_id))

        try:
            from_branch = Branch.objects.get(id=from_branch_uuid, tenant_id=tenant_uuid)
        except Branch.DoesNotExist:
            logger.warning(
                f"Source branch not found: {from_branch_id} for tenant {tenant_id}",
                extra={"branch_id": str(from_branch_id), "tenant_id": str(tenant_id)},
            )
            raise BranchNotFoundError(str(from_branch_id), str(tenant_id))

        try:
            to_branch = Branch.objects.get(id=to_branch_uuid, tenant_id=tenant_uuid)
        except Branch.DoesNotExist:
            logger.warning(
                f"Destination branch not found: {to_branch_id} for tenant {tenant_id}",
                extra={"branch_id": str(to_branch_id), "tenant_id": str(tenant_id)},
            )
            raise BranchNotFoundError(str(to_branch_id), str(tenant_id))

        # Generate a common reference_id for linking movements
        transfer_ref_id = uuid.uuid4()

        # Prepare transfer notes
        transfer_notes = notes or f"Stock transfer: {from_branch.name} → {to_branch.name}"

        # Create TRANS_OUT movement (will validate stock availability)
        out_movement = StockService.record_movement(
            tenant_id=str(tenant_uuid),
            product_id=str(product_uuid),
            branch_id=str(from_branch_uuid),
            movement_type=StockMovement.MovementType.TRANS_OUT,
            quantity_delta=-quantity,  # Negative for outbound
            cost_snapshot=product.cost_price,
            reference_id=str(transfer_ref_id),
            notes=f"{transfer_notes} (OUT)",
        )

        # Create TRANS_IN movement
        in_movement = StockService.record_movement(
            tenant_id=str(tenant_uuid),
            product_id=str(product_uuid),
            branch_id=str(to_branch_uuid),
            movement_type=StockMovement.MovementType.TRANS_IN,
            quantity_delta=quantity,  # Positive for inbound
            cost_snapshot=product.cost_price,
            reference_id=str(transfer_ref_id),
            notes=f"{transfer_notes} (IN)",
        )

        logger.info(
            f"Stock transfer completed: product={product.sku}, "
            f"from={from_branch.name}, to={to_branch.name}, quantity={quantity}, "
            f"reference_id={transfer_ref_id}"
        )

        return (out_movement, in_movement)

    @staticmethod
    def get_current_stock(
        product_id: str,
        branch_id: str,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Get current stock levels for a product at a branch.

        Args:
            product_id: Product UUID
            branch_id: Branch UUID

        Returns:
            Tuple of (total_quantity, reserved_quantity, available_quantity)
        """
        # Convert string IDs to UUIDs
        product_uuid = uuid.UUID(product_id) if isinstance(product_id, str) else product_id
        branch_uuid = uuid.UUID(branch_id) if isinstance(branch_id, str) else branch_id

        try:
            snapshot = StockSnapshot.objects.get(
                product_id=product_uuid,
                branch_id=branch_uuid,
            )
            return (snapshot.quantity, snapshot.reserved_quantity, snapshot.available_quantity)
        except StockSnapshot.DoesNotExist:
            return (Decimal("0.0000"), Decimal("0.0000"), Decimal("0.0000"))

    @staticmethod
    def get_product_stock_summary(
        tenant_id: str,
        product_id: str,
    ) -> dict:
        """
        Get stock summary for a product across all branches.

        Args:
            tenant_id: Tenant UUID
            product_id: Product UUID

        Returns:
            Dictionary with stock information per branch
        """
        # Validate and convert UUIDs
        try:
            product_uuid = validate_uuid(product_id, "product_id")
        except Exception as e:
            logger.error(f"UUID validation failed in get_product_stock_summary: {str(e)}")
            raise ValueError(f"Invalid UUID parameter: {str(e)}")

        # Get product with proper error handling
        try:
            product = Product.objects.get(id=product_uuid)
        except Product.DoesNotExist:
            logger.warning(
                f"Product not found: {product_id}",
                extra={"product_id": str(product_id)},
            )
            raise ProductNotFoundError(str(product_id), "unknown")

        # Get all snapshots for this product
        snapshots = (
            StockSnapshot.objects.filter(
                product_id=product_uuid,
                branch__tenant_id=tenant_id,
            )
            .select_related("branch")
            .order_by("branch__name")
        )

        summary = {
            "product_id": str(product_id),
            "product_sku": product.sku,
            "product_name": product.name,
            "total_quantity": Decimal("0.0000"),
            "total_reserved": Decimal("0.0000"),
            "total_available": Decimal("0.0000"),
            "branches": [],
        }

        for snapshot in snapshots:
            branch_data = {
                "branch_id": str(snapshot.branch_id),
                "branch_name": snapshot.branch.name,
                "quantity": snapshot.quantity,
                "reserved": snapshot.reserved_quantity,
                "available": snapshot.available_quantity,
                "last_updated": snapshot.last_updated,
            }
            summary["branches"].append(branch_data)
            summary["total_quantity"] += snapshot.quantity
            summary["total_reserved"] += snapshot.reserved_quantity
            summary["total_available"] += snapshot.available_quantity

        return summary


def aggregate_stock_levels_batch(movements_qs) -> dict:
    """
    Aggregate stock levels from a queryset of movement objects.

    Each movement object must expose: product_id, branch_id, quantity,
    movement_type (one of IN/OUT/ADJUSTMENT/TRANSFER_IN/TRANSFER_OUT/
    RESERVED/RELEASED).

    Returns a nested dict keyed by product_id → branch_id → {total, reserved,
    available}  where amounts are string-serialised Decimals for round-trip
    safety.

    Delegates to the Rust implementation when gravitea_rust is available;
    falls back to an equivalent pure-Python path otherwise.
    """
    if _USE_RUST_COMPUTE:
        movements_json = _json.dumps(
            [
                {
                    "product_id": str(m.product_id),
                    "branch_id": str(m.branch_id),
                    "quantity": str(m.quantity),
                    "movement_type": m.movement_type,
                }
                for m in movements_qs
            ]
        )
        return _json.loads(_rust_aggregate_stock(movements_json))

    # Python fallback — mirrors the Rust aggregation logic
    _IN_TYPES = {"IN", "ADJUSTMENT", "TRANSFER_IN"}
    _OUT_TYPES = {"OUT", "TRANSFER_OUT"}
    _RESERVE_TYPES = {"RESERVED"}
    _RELEASE_TYPES = {"RELEASED"}

    # {product_id: {branch_id: {"total": Decimal, "reserved": Decimal}}}
    accumulator: dict[str, dict[str, dict[str, Decimal]]] = {}

    for m in movements_qs:
        pid = str(m.product_id)
        bid = str(m.branch_id)
        qty = Decimal(str(m.quantity))
        mtype = m.movement_type

        bucket = accumulator.setdefault(pid, {}).setdefault(
            bid, {"total": Decimal("0"), "reserved": Decimal("0")}
        )
        if mtype in _IN_TYPES:
            bucket["total"] += qty
        elif mtype in _OUT_TYPES:
            bucket["total"] -= qty
        elif mtype in _RESERVE_TYPES:
            bucket["reserved"] += qty
        elif mtype in _RELEASE_TYPES:
            bucket["reserved"] -= qty

    result: dict[str, dict[str, dict[str, str]]] = {}
    for pid, branches in accumulator.items():
        result[pid] = {}
        for bid, vals in branches.items():
            total = vals["total"]
            reserved = vals["reserved"]
            result[pid][bid] = {
                "total": str(total),
                "reserved": str(reserved),
                "available": str(total - reserved),
            }

    return result
