"""
Reportes services for Gravitea ERP.

Provides read-only QuerySet methods for aggregating data across modules.
These methods are the data access layer for future report generators —
no report generation logic is implemented here.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("reportes")


class ReportService:
    """
    Read-only data access layer for the reporting module.

    Methods return QuerySets or aggregated data scoped by tenant_id.
    Future report generators will consume these methods to produce output.

    Note: compras module import is guarded with try/except because
    COMPRAS-ENGINEER's module may not be complete during parallel execution.
    LEAD will verify full integration in Phase 9.
    """

    @staticmethod
    def get_sales_summary(tenant_id: Any) -> Any:
        """
        Return aggregated sales data scoped by tenant.

        Queries SaleOrder data from the ventas module.
        Returns a QuerySet annotated with order counts, totals, and status breakdown.
        """
        from django.db.models import Count, Sum

        from apps.ventas.models import SaleOrder

        return (
            SaleOrder.all_objects.filter(tenant_id=tenant_id)
            .select_related("customer")
            .values("status")
            .annotate(
                order_count=Count("id"),
                total_amount_sum=Sum("total_amount"),
            )
            .order_by("status")
        )

    @staticmethod
    def get_stock_levels(tenant_id: Any) -> Any:
        """
        Return current stock level summaries scoped by tenant.

        Queries Product and StockSnapshot data from the inventario module.
        Returns a QuerySet of products with their current stock quantity per branch.
        """
        from apps.inventario.models import StockSnapshot

        return (
            StockSnapshot.objects.select_related("product", "branch")
            .filter(product__tenant_id=tenant_id)
            .values(
                "product__sku",
                "product__name",
                "branch__name",
                "quantity",
            )
            .order_by("product__sku", "branch__name")
        )

    @staticmethod
    def get_purchase_history(tenant_id: Any) -> Any:
        """
        Return purchase order history scoped by tenant.

        Queries PurchaseOrder data from the compras module.
        Returns a QuerySet of purchase orders with supplier and status info.

        Note: The compras module may not exist yet (parallel execution).
        If the import fails, returns an empty list with a log warning.
        """
        try:
            from django.db.models import Count, Sum

            from apps.compras.models import PurchaseOrder

            return (
                PurchaseOrder.all_objects.filter(tenant_id=tenant_id)
                .select_related("supplier")
                .values("status")
                .annotate(
                    order_count=Count("id"),
                    total_amount_sum=Sum("total_amount"),
                )
                .order_by("status")
            )
        except ImportError:
            # compras module not yet available (parallel execution scenario)
            # LEAD will verify integration in Phase 9
            logger.warning(
                "ReportService.get_purchase_history: compras module not available. "
                "This is expected during parallel module development. "
                "LEAD will verify integration in Phase 9."
            )
            return []
