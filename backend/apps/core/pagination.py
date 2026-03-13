"""
Pagination classes for Gravitea ERP API.

Implements cursor-based pagination for consistent performance
on large datasets per SC-015.
"""

from rest_framework.pagination import CursorPagination


class StandardCursorPagination(CursorPagination):
    """
    Cursor-based pagination for consistent performance on large datasets.

    Orders by created_at descending by default.
    Provides stable pagination that doesn't degrade with large offsets.

    Configuration:
        - Default page size: 100 items
        - Maximum page size: 500 items
        - Default ordering: -created_at (newest first)
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
    ordering = "-created_at"
    cursor_query_param = "cursor"


class ProductCursorPagination(StandardCursorPagination):
    """
    Product-specific pagination with SKU ordering option.

    Supports ordering by:
    - created_at (default): Newest products first
    - sku: Alphabetical by SKU
    - name: Alphabetical by name

    Usage:
        GET /api/v1/products/?order_by=sku&page_size=50
    """

    def get_ordering(self, request, queryset, view):
        order_by = request.query_params.get("order_by")
        if order_by == "sku":
            return ["sku"]
        elif order_by == "name":
            return ["name"]
        elif order_by == "-name":
            return ["-name"]
        return super().get_ordering(request, queryset, view)


class StockMovementPagination(StandardCursorPagination):
    """
    Pagination for stock movement ledger.

    Always ordered by created_at descending (newest first)
    as the ledger is append-only.
    """

    ordering = "-created_at"


class PriceHistoryCursorPagination(CursorPagination):
    """
    Pagination for price history records.

    Orders by valid_from descending since PriceHistory uses
    valid_from timestamp instead of created_at.
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
    ordering = "-valid_from"
    cursor_query_param = "cursor"
