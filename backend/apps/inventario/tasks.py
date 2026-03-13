"""
Celery background tasks for inventory operations.

Tasks:
- recalculate_stock_levels: Recalculate stock levels from movements
- sync_stock_snapshots: Synchronize stock snapshots across branches
- cleanup_old_movements: Archive old stock movement records
"""

import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.db.models import Sum

logger = logging.getLogger("apps")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    rate_limit="30/m",
)
def recalculate_stock_levels(
    self, tenant_id: str, product_id: str = None, branch_id: str = None
) -> dict:
    """
    Recalculate stock levels from stock movements.

    This task rebuilds stock snapshots based on the immutable
    ledger of stock movements, ensuring data integrity.

    Args:
        tenant_id: UUID of the tenant
        product_id: Optional - specific product to recalculate
        branch_id: Optional - specific branch to recalculate

    Returns:
        dict: Summary of recalculation results
    """
    from apps.inventario.models import StockMovement, StockSnapshot

    logger.info(
        f"Recalculating stock levels for tenant {tenant_id}, "
        f"product={product_id}, branch={branch_id}"
    )

    # Build queryset filters
    filters = {"tenant_id": tenant_id}
    if product_id:
        filters["product_id"] = product_id
    if branch_id:
        filters["branch_id"] = branch_id

    recalculated = 0
    errors = []

    # Get unique product/branch combinations from movements
    movement_groups = (
        StockMovement.objects.filter(**filters)
        .values("product_id", "branch_id")
        .distinct()
    )

    for group in movement_groups:
        try:
            with transaction.atomic():
                # Calculate total from movements
                total = (
                    StockMovement.objects.filter(
                        tenant_id=tenant_id,
                        product_id=group["product_id"],
                        branch_id=group["branch_id"],
                    ).aggregate(total=Sum("quantity_delta"))["total"]
                    or Decimal("0")
                )

                # Update or create snapshot
                snapshot, created = StockSnapshot.objects.update_or_create(
                    product_id=group["product_id"],
                    branch_id=group["branch_id"],
                    defaults={"quantity": total},
                )

                recalculated += 1
                logger.debug(
                    f"Stock recalculated: product={group['product_id']}, "
                    f"branch={group['branch_id']}, quantity={total}"
                )

        except Exception as e:
            error_msg = f"Error recalculating {group}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    result = {
        "tenant_id": tenant_id,
        "product_id": product_id,
        "branch_id": branch_id,
        "snapshots_recalculated": recalculated,
        "errors": errors,
    }

    logger.info(f"Stock recalculation completed: {result}")
    return result


@shared_task(
    bind=True,
    max_retries=2,
    rate_limit="20/m",
)
def sync_stock_snapshots(self, tenant_id: str) -> dict:
    """
    Synchronize stock snapshots across all branches.

    Ensures all products have stock snapshots for all active branches,
    initializing missing ones to zero.

    Args:
        tenant_id: UUID of the tenant

    Returns:
        dict: Summary of synchronization results
    """
    from apps.core.models import Branch
    from apps.inventario.models import Product, StockSnapshot

    logger.info(f"Synchronizing stock snapshots for tenant {tenant_id}")

    # Get all active branches and products for this tenant
    branches = Branch.objects.filter(tenant_id=tenant_id, is_active=True)
    products = Product.objects.filter(tenant_id=tenant_id, is_active=True)

    created = 0
    for product in products:
        for branch in branches:
            _, was_created = StockSnapshot.objects.get_or_create(
                product=product,
                branch=branch,
                defaults={"quantity": Decimal("0")},
            )
            if was_created:
                created += 1

    result = {
        "tenant_id": tenant_id,
        "branches_checked": branches.count(),
        "products_checked": products.count(),
        "snapshots_created": created,
    }

    logger.info(f"Stock snapshot sync completed: {result}")
    return result


@shared_task(
    bind=True,
    max_retries=1,
    rate_limit="5/m",
)
def check_low_stock_alerts(self, tenant_id: str) -> dict:
    """
    Check for products below minimum stock level.

    Args:
        tenant_id: UUID of the tenant

    Returns:
        dict: Summary of low stock alerts
    """
    from apps.inventario.models import StockSnapshot
    from django.db.models import F

    logger.info(f"Checking low stock alerts for tenant {tenant_id}")

    # Find products where stock is below minimum
    low_stock = (
        StockSnapshot.objects.filter(
            product__tenant_id=tenant_id,
            product__is_active=True,
        )
        .select_related("product", "branch")
        .filter(quantity__lt=F("product__min_stock"))
    )

    alerts = []
    for snapshot in low_stock:
        alerts.append({
            "product_id": str(snapshot.product_id),
            "product_name": snapshot.product.name,
            "branch_id": str(snapshot.branch_id),
            "current_stock": str(snapshot.quantity),
            "min_stock": str(snapshot.product.min_stock),
        })

    result = {
        "tenant_id": tenant_id,
        "alerts_count": len(alerts),
        "alerts": alerts[:50],  # Limit to first 50 alerts
    }

    logger.info(f"Low stock check completed: {len(alerts)} alerts found")
    return result


@shared_task(
    bind=True,
    max_retries=1,
    rate_limit="2/m",
)
def generate_inventory_report(self, tenant_id: str, branch_id: str = None) -> dict:
    """
    Generate inventory valuation report.

    Args:
        tenant_id: UUID of the tenant
        branch_id: Optional - specific branch for the report

    Returns:
        dict: Inventory report summary
    """
    from apps.inventario.models import StockSnapshot
    from django.db.models import F, Sum

    logger.info(f"Generating inventory report for tenant {tenant_id}")

    filters = {"product__tenant_id": tenant_id, "product__is_active": True}
    if branch_id:
        filters["branch_id"] = branch_id

    # Calculate inventory value
    inventory_data = (
        StockSnapshot.objects.filter(**filters)
        .select_related("product")
        .aggregate(
            total_items=Sum("quantity"),
            total_cost_value=Sum(F("quantity") * F("product__cost_price")),
            total_sale_value=Sum(F("quantity") * F("product__unit_price")),
        )
    )

    result = {
        "tenant_id": tenant_id,
        "branch_id": branch_id,
        "total_items": str(inventory_data["total_items"] or 0),
        "total_cost_value": str(inventory_data["total_cost_value"] or 0),
        "total_sale_value": str(inventory_data["total_sale_value"] or 0),
    }

    logger.info(f"Inventory report completed: {result}")
    return result
