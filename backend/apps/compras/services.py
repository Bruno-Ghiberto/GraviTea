"""
Compras business services.

GoodsReceiptService: Validate receipt, create GoodsReceipt + lines,
create StockMovement per line via StockService, update PO item
received_quantity, auto-transition PO state.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from django.db import transaction

from apps.compras.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
)
from apps.inventario.services.stock_service import StockService

logger = logging.getLogger("compras")


class GoodsReceiptService:
    """Create goods receipts against confirmed/partial POs."""

    @staticmethod
    @transaction.atomic
    def create_receipt(
        tenant_id: str,
        purchase_order_id: str,
        receipt_number: str,
        lines: list[dict],
        branch_id: str,
        received_by_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> GoodsReceipt:
        """
        Create a goods receipt with lines, stock movements, and PO state update.

        Args:
            tenant_id: UUID string of the tenant
            purchase_order_id: UUID string of the PO
            receipt_number: Unique receipt number
            lines: List of dicts with keys: purchase_order_item_id, quantity_received
            branch_id: UUID string of the receiving branch
            received_by_id: Optional UUID string of user
            notes: Optional receipt notes

        Returns:
            Created GoodsReceipt instance

        Raises:
            ValueError: If PO is not in receivable state, or over-receipt detected
        """
        po = PurchaseOrder.all_objects.select_for_update().get(
            id=purchase_order_id, tenant_id=tenant_id
        )

        # Validate PO is in receivable state
        if po.status not in (
            PurchaseOrderStatus.CONFIRMED,
            PurchaseOrderStatus.PARTIAL_RECEIVED,
        ):
            raise ValueError(
                f"Cannot receive against PO in status '{po.status}'. "
                "Must be CONFIRMED or PARTIAL_RECEIVED."
            )

        if not lines:
            raise ValueError("At least one receipt line is required.")

        # Create the goods receipt — use po.tenant_id (UUID) to match IDOR checks
        gr = GoodsReceipt.objects.create(
            tenant_id=po.tenant_id,
            purchase_order=po,
            receipt_number=receipt_number,
            received_by_id=received_by_id,
            notes=notes,
        )

        # Process each line
        for line_data in lines:
            poi_id = line_data["purchase_order_item_id"]
            qty = Decimal(str(line_data["quantity_received"]))

            poi = PurchaseOrderItem.objects.select_for_update().get(
                id=poi_id, purchase_order=po
            )

            # Validate no over-receipt
            remaining = poi.quantity - poi.received_quantity
            if qty > remaining:
                raise ValueError(
                    f"Over-receipt on item {poi_id}: "
                    f"requested {qty}, remaining {remaining} "
                    f"(ordered {poi.quantity}, already received {poi.received_quantity})"
                )

            # Create receipt line
            GoodsReceiptLine.objects.create(
                goods_receipt=gr,
                purchase_order_item=poi,
                product_id=poi.product_id,
                quantity_received=qty,
            )

            # Create stock movement via StockService
            StockService.record_movement(
                tenant_id=tenant_id,
                product_id=str(poi.product_id),
                branch_id=branch_id,
                movement_type="PURCHASE",
                quantity_delta=qty,
                cost_snapshot=poi.unit_price,
                reference_id=str(gr.id),
                notes=f"GR-{receipt_number} for PO-{po.order_number}",
            )

            # Update POItem received_quantity
            poi.received_quantity += qty
            poi.save(update_fields=["received_quantity"])

        # Auto-transition PO state
        _update_po_status(po)

        logger.info(
            "Goods receipt created: %s for PO %s (%d lines)",
            receipt_number,
            po.order_number,
            len(lines),
        )

        return gr


def _update_po_status(po: PurchaseOrder) -> None:
    """
    Auto-transition PO status based on cumulative received quantities.

    - All items fully received → RECEIVED
    - Any item partially received → PARTIAL_RECEIVED
    """
    items = po.items.all()
    all_received = all(item.received_quantity >= item.quantity for item in items)
    any_received = any(item.received_quantity > 0 for item in items)

    if all_received:
        po.status = PurchaseOrderStatus.RECEIVED
    elif any_received:
        po.status = PurchaseOrderStatus.PARTIAL_RECEIVED

    po.save(update_fields=["status", "updated_at"])
