"""Pagination classes for acopio reference data."""

from rest_framework.pagination import PageNumberPagination


class ReferenceDataPagination(PageNumberPagination):
    """
    Page-number pagination for acopio reference data.

    Overrides project default CursorPagination because:
    1. Global models lack created_at field (cursor ordering fails)
    2. REST API Design v1.0 Section 2.6 requires count/next/previous envelope
    3. Reference data is < 100 rows -- offset performance is not a concern

    Justified deviation from Constitution Principle XIII (cursor-based).
    """

    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500
