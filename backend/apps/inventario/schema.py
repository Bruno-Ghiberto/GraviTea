"""
drf-spectacular schema definitions for inventory views.

Provides comprehensive OpenAPI schema documentation for all inventory endpoints
using @extend_schema and @extend_schema_view decorators.
"""

from decimal import Decimal

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (OpenApiExample, OpenApiParameter,
                                    OpenApiResponse, extend_schema,
                                    extend_schema_view, inline_serializer)
from rest_framework import serializers, status

from .serializers import (BranchStockSerializer, CategoryCreateSerializer,
                          CategorySerializer, PriceListSerializer,
                          ProductCostHistorySerializer,
                          ProductCreateSerializer, ProductDetailSerializer,
                          ProductPriceHistorySerializer, ProductSerializer,
                          StockMovementCreateSerializer,
                          StockMovementSerializer, SupplierCreateSerializer,
                          SupplierSerializer)

# ============================================================================
# RFC 7807 Error Response Serializers
# ============================================================================


class InventarioErrorSerializer(serializers.Serializer):
    """RFC 7807 Problem Details for HTTP APIs error response (inventario-specific)."""

    type = serializers.CharField(
        help_text="URI reference identifying the problem type", default="about:blank"
    )
    title = serializers.CharField(help_text="Short, human-readable summary")
    status = serializers.IntegerField(help_text="HTTP status code")
    detail = serializers.CharField(help_text="Human-readable explanation", required=False)
    instance = serializers.CharField(
        help_text="URI reference identifying specific occurrence", required=False
    )


class InventarioValidationErrorSerializer(serializers.Serializer):
    """Validation error response (400 Bad Request) for inventario module."""

    detail = serializers.CharField(help_text="Error description")
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Field-specific validation errors",
        required=False,
    )


# ============================================================================
# Pagination Response Serializers
# ============================================================================


class CursorPaginatedResponseSerializer(serializers.Serializer):
    """Generic cursor pagination response wrapper."""

    next = serializers.URLField(help_text="URL to next page", allow_null=True, required=False)
    previous = serializers.URLField(
        help_text="URL to previous page", allow_null=True, required=False
    )
    results = serializers.ListField(help_text="Page results")


# ============================================================================
# Custom Action Response Serializers
# ============================================================================


class BarcodeSearchRequestSerializer(serializers.Serializer):
    """Barcode search request body."""

    barcode = serializers.CharField(help_text="Product barcode to search for", required=True)


class SupplierSearchParamSerializer(serializers.Serializer):
    """Supplier search query parameter."""

    q = serializers.CharField(
        help_text="Search term (tax_id or email)", required=True, allow_blank=False
    )


class CategoryTreeNodeSerializer(serializers.Serializer):
    """Hierarchical category tree node."""

    id = serializers.UUIDField(help_text="Category ID")
    name = serializers.CharField(help_text="Category name")
    children = serializers.ListField(
        child=serializers.DictField(), help_text="Nested child categories"
    )


class PriceListDefaultResponseSerializer(serializers.Serializer):
    """Response for set-default action."""

    status = serializers.CharField(help_text="Operation status", default="default set")
    id = serializers.UUIDField(help_text="Price list ID")


# ============================================================================
# Product ViewSet Schema
# ============================================================================

product_list_schema = extend_schema(
    summary="List products",
    description="""
    List products with cursor pagination and filtering.

    **Filters:**
    - category: Filter by category ID
    - name: Search by name (case-insensitive partial match)
    - sku: Search by SKU (exact match)
    - is_active: Filter by active status
    - min_price: Minimum unit price
    - max_price: Maximum unit price
    """,
    parameters=[
        OpenApiParameter(
            name="category",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by category ID",
        ),
        OpenApiParameter(
            name="name",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search by name (case-insensitive partial match)",
        ),
        OpenApiParameter(
            name="sku",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search by SKU (exact match)",
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active status",
        ),
        OpenApiParameter(
            name="min_price",
            type=OpenApiTypes.DECIMAL,
            location=OpenApiParameter.QUERY,
            description="Minimum unit price",
        ),
        OpenApiParameter(
            name="max_price",
            type=OpenApiTypes.DECIMAL,
            location=OpenApiParameter.QUERY,
            description="Maximum unit price",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedProductList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": ProductSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=InventarioErrorSerializer, description="Authentication required"
        ),
    },
    tags=["inventory-products"],
)

product_create_schema = extend_schema(
    summary="Create product",
    description="Create a new product with encrypted barcode and tenant isolation.",
    request=ProductCreateSerializer,
    responses={
        201: ProductSerializer,
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Basic Product",
            value={
                "sku": "PROD-001",
                "name": "Sample Product",
                "description": "Product description",
                "unit_price": "150.00",
                "cost_price": "100.00",
                "tax_rate": "21.00",
                "is_active": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Product with Barcode",
            value={
                "sku": "PROD-002",
                "barcode": "1234567890123",
                "name": "Barcode Product",
                "unit_price": "200.00",
                "cost_price": "120.00",
                "tax_rate": "21.00",
                "min_stock": "10.0000",
                "max_stock": "100.0000",
            },
            request_only=True,
        ),
    ],
    tags=["inventory-products"],
)

product_retrieve_schema = extend_schema(
    summary="Get product details",
    description="Retrieve detailed product information including branch stock levels.",
    responses={
        200: ProductDetailSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-products"],
)

product_update_schema = extend_schema(
    summary="Update product",
    description="Update product details. SKU uniqueness enforced per tenant.",
    request=ProductCreateSerializer,
    responses={
        200: ProductSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-products"],
)

product_partial_update_schema = extend_schema(
    summary="Partial update product",
    description="Partially update product fields.",
    request=ProductCreateSerializer,
    responses={
        200: ProductSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-products"],
)

product_destroy_schema = extend_schema(
    summary="Soft delete product",
    description="Deactivate product by setting is_active=False. Product is not permanently deleted.",
    responses={
        204: None,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-products"],
)

product_stock_schema = extend_schema(
    summary="Get product stock by branch",
    description="Retrieve current stock levels for this product across all branches.",
    responses={
        200: BranchStockSerializer(many=True),
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-products"],
)

product_search_schema = extend_schema(
    summary="Search product by barcode",
    description="""
    Search for product using encrypted barcode with blind index.

    **Privacy:** Barcode is encrypted at rest. Search uses blind index for privacy-preserving lookup.
    """,
    request=BarcodeSearchRequestSerializer,
    responses={
        200: ProductDetailSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Barcode Search",
            value={"barcode": "1234567890123"},
            request_only=True,
        ),
    ],
    tags=["inventory-products"],
)

ProductViewSetSchema = extend_schema_view(
    list=product_list_schema,
    create=product_create_schema,
    retrieve=product_retrieve_schema,
    update=product_update_schema,
    partial_update=product_partial_update_schema,
    destroy=product_destroy_schema,
    stock=product_stock_schema,
    search=product_search_schema,
)

# ============================================================================
# StockMovement ViewSet Schema
# ============================================================================

stock_movement_list_schema = extend_schema(
    summary="List stock movements",
    description="""
    List stock movements with cursor pagination and filtering.

    **Immutability:** Stock movements are append-only and cannot be modified or deleted.

    **Filters:**
    - product: Filter by product ID
    - branch: Filter by branch ID
    - type: Filter by movement type (SALE, PURCHASE, ADJ, TRANS_IN, TRANS_OUT)
    - reference_id: Filter by external reference ID
    - created_after: Filter by creation date (>= timestamp)
    - created_before: Filter by creation date (<= timestamp)
    """,
    parameters=[
        OpenApiParameter(
            name="product",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by product ID",
        ),
        OpenApiParameter(
            name="branch",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by branch ID",
        ),
        OpenApiParameter(
            name="type",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Movement type",
            enum=["SALE", "PURCHASE", "ADJ", "TRANS_IN", "TRANS_OUT"],
        ),
        OpenApiParameter(
            name="reference_id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="External reference ID",
        ),
        OpenApiParameter(
            name="created_after",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Created after timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="created_before",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Created before timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedStockMovementList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": StockMovementSerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-stock"],
)

stock_movement_create_schema = extend_schema(
    summary="Create stock movement",
    description="""
    Create a new stock movement and update branch stock.

    **Movement Types:**
    - SALE: Stock sold (quantity_delta will be negative)
    - PURCHASE: Stock received (quantity_delta will be positive)
    - ADJ: Manual adjustment (can be positive or negative)
    - TRANS_IN: Transfer from another branch (positive)
    - TRANS_OUT: Transfer to another branch (negative)

    **Automatic Quantity Sign Adjustment:**
    The system automatically adjusts quantity_delta sign based on movement type.
    For SALE/TRANS_OUT, positive values are converted to negative.
    """,
    request=StockMovementCreateSerializer,
    responses={
        201: StockMovementSerializer,
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Purchase Movement",
            value={
                "product": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "branch": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "type": "PURCHASE",
                "quantity_delta": "100.0000",
                "cost_snapshot": "50.00",
                "notes": "Initial stock purchase",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Sale Movement",
            value={
                "product": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "branch": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                "type": "SALE",
                "quantity_delta": "5.0000",
                "reference_id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
                "notes": "Sale INV-001",
            },
            request_only=True,
        ),
    ],
    tags=["inventory-stock"],
)

stock_movement_retrieve_schema = extend_schema(
    summary="Get stock movement details",
    description="Retrieve detailed stock movement information.",
    responses={
        200: StockMovementSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-stock"],
)

StockMovementViewSetSchema = extend_schema_view(
    list=stock_movement_list_schema,
    create=stock_movement_create_schema,
    retrieve=stock_movement_retrieve_schema,
)

# ============================================================================
# Category ViewSet Schema
# ============================================================================

category_list_schema = extend_schema(
    summary="List categories",
    description="""
    List product categories with cursor pagination.

    **Query Parameters:**
    - root_only: Set to 'true' to return only root categories (no parent)
    """,
    parameters=[
        OpenApiParameter(
            name="root_only",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Return only root categories",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedCategoryList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": CategorySerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-categories"],
)

category_create_schema = extend_schema(
    summary="Create category",
    description="Create a new product category. Can be a root category or nested under a parent.",
    request=CategoryCreateSerializer,
    responses={
        201: CategorySerializer,
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Root Category",
            value={"name": "Electronics"},
            request_only=True,
        ),
        OpenApiExample(
            name="Nested Category",
            value={
                "name": "Laptops",
                "parent": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            },
            request_only=True,
        ),
    ],
    tags=["inventory-categories"],
)

category_retrieve_schema = extend_schema(
    summary="Get category details",
    description="Retrieve category details including parent and immediate children.",
    responses={
        200: CategorySerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-categories"],
)

category_update_schema = extend_schema(
    summary="Update category",
    description="Update category name or parent. Circular parent relationships are prevented.",
    request=CategoryCreateSerializer,
    responses={
        200: CategorySerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-categories"],
)

category_partial_update_schema = extend_schema(
    summary="Partial update category",
    description="Partially update category fields.",
    request=CategoryCreateSerializer,
    responses={
        200: CategorySerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-categories"],
)

category_destroy_schema = extend_schema(
    summary="Delete category",
    description="Delete category. Cannot delete if category has products or child categories.",
    responses={
        204: None,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-categories"],
)

category_tree_schema = extend_schema(
    summary="Get category tree",
    description="""
    Retrieve hierarchical category tree structure.

    Returns all root categories with their nested children recursively.
    Useful for building category navigation menus.
    """,
    responses={
        200: CategoryTreeNodeSerializer(many=True),
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Category Tree",
            value=[
                {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name": "Electronics",
                    "children": [
                        {
                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                            "name": "Laptops",
                            "children": [],
                        },
                        {
                            "id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
                            "name": "Phones",
                            "children": [],
                        },
                    ],
                },
            ],
            response_only=True,
        ),
    ],
    tags=["inventory-categories"],
)

CategoryViewSetSchema = extend_schema_view(
    list=category_list_schema,
    create=category_create_schema,
    retrieve=category_retrieve_schema,
    update=category_update_schema,
    partial_update=category_partial_update_schema,
    destroy=category_destroy_schema,
    tree=category_tree_schema,
)

# ============================================================================
# Supplier ViewSet Schema
# ============================================================================

supplier_list_schema = extend_schema(
    summary="List suppliers",
    description="""
    List suppliers with cursor pagination and filtering.

    **Privacy:** Sensitive fields (tax_id, email, contact_info, address) are encrypted at rest
    and decrypted for authorized users.

    **Filters:**
    - name: Search by name (case-insensitive partial match)
    - is_active: Filter by active status
    """,
    parameters=[
        OpenApiParameter(
            name="name",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search by name (case-insensitive partial match)",
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active status",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedSupplierList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": SupplierSerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-suppliers"],
)

supplier_create_schema = extend_schema(
    summary="Create supplier",
    description="""
    Create a new supplier with encrypted PII fields.

    **Encrypted Fields:** tax_id, email, contact_info, address
    **Blind Indexes:** Generated for tax_id and email for privacy-preserving search
    """,
    request=SupplierCreateSerializer,
    responses={
        201: SupplierSerializer,
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Basic Supplier",
            value={
                "name": "ABC Supplies Ltd.",
                "tax_id": "20-12345678-9",
                "email": "contact@abcsupplies.com",
                "contact_info": "+54 11 1234-5678",
                "address": "Av. Corrientes 1234, Buenos Aires",
                "lead_time_days": 7,
            },
            request_only=True,
        ),
    ],
    tags=["inventory-suppliers"],
)

supplier_retrieve_schema = extend_schema(
    summary="Get supplier details",
    description="Retrieve supplier details with decrypted PII fields.",
    responses={
        200: SupplierSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-suppliers"],
)

supplier_update_schema = extend_schema(
    summary="Update supplier",
    description="Update supplier details. Name uniqueness enforced per tenant.",
    request=SupplierCreateSerializer,
    responses={
        200: SupplierSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-suppliers"],
)

supplier_partial_update_schema = extend_schema(
    summary="Partial update supplier",
    description="Partially update supplier fields.",
    request=SupplierCreateSerializer,
    responses={
        200: SupplierSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-suppliers"],
)

supplier_destroy_schema = extend_schema(
    summary="Soft delete supplier",
    description="Deactivate supplier by setting is_active=False. Supplier is not permanently deleted.",
    responses={
        204: None,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-suppliers"],
)

supplier_search_schema = extend_schema(
    summary="Search suppliers by tax_id or email",
    description="""
    Search suppliers using encrypted tax_id or email with blind indexes.

    **Privacy:** Search uses blind indexes for privacy-preserving lookup without exposing plaintext.

    **Query Parameter:**
    - q: Search term (tax_id or email)
    """,
    parameters=[
        OpenApiParameter(
            name="q",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search term (tax_id or email)",
            required=True,
        ),
    ],
    responses={
        200: SupplierSerializer(many=True),
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Search by Tax ID",
            value=[
                {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name": "ABC Supplies Ltd.",
                    "tax_id": "20-12345678-9",
                    "email": "contact@abcsupplies.com",
                }
            ],
            response_only=True,
        ),
    ],
    tags=["inventory-suppliers"],
)

SupplierViewSetSchema = extend_schema_view(
    list=supplier_list_schema,
    create=supplier_create_schema,
    retrieve=supplier_retrieve_schema,
    update=supplier_update_schema,
    partial_update=supplier_partial_update_schema,
    destroy=supplier_destroy_schema,
    search=supplier_search_schema,
)

# ============================================================================
# PriceList ViewSet Schema
# ============================================================================

price_list_list_schema = extend_schema(
    summary="List price lists",
    description="List price lists with cursor pagination.",
    parameters=[
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedPriceListList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": PriceListSerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_list_create_schema = extend_schema(
    summary="Create price list",
    description="""
    Create a new price list.

    **Constraint:** Only one price list can be set as default per tenant.
    """,
    request=PriceListSerializer,
    responses={
        201: PriceListSerializer,
        400: InventarioValidationErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Retail Price List",
            value={
                "name": "Retail",
                "margin_pct": "30.00",
                "is_default": True,
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Wholesale Price List",
            value={
                "name": "Wholesale",
                "margin_pct": "15.00",
                "is_default": False,
            },
            request_only=True,
        ),
    ],
    tags=["inventory-pricing"],
)

price_list_retrieve_schema = extend_schema(
    summary="Get price list details",
    description="Retrieve price list details.",
    responses={
        200: PriceListSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_list_update_schema = extend_schema(
    summary="Update price list",
    description="Update price list. Name uniqueness enforced per tenant.",
    request=PriceListSerializer,
    responses={
        200: PriceListSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_list_partial_update_schema = extend_schema(
    summary="Partial update price list",
    description="Partially update price list fields.",
    request=PriceListSerializer,
    responses={
        200: PriceListSerializer,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_list_destroy_schema = extend_schema(
    summary="Delete price list",
    description="Delete price list. Cannot delete if price list has associated price history.",
    responses={
        204: None,
        400: InventarioValidationErrorSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_list_set_default_schema = extend_schema(
    summary="Set as default price list",
    description="""
    Set this price list as the default for the tenant.

    Automatically unsets any other default price lists for the tenant.
    """,
    request=None,
    responses={
        200: PriceListDefaultResponseSerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Set Default Response",
            value={
                "status": "default set",
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            },
            response_only=True,
        ),
    ],
    tags=["inventory-pricing"],
)

PriceListViewSetSchema = extend_schema_view(
    list=price_list_list_schema,
    create=price_list_create_schema,
    retrieve=price_list_retrieve_schema,
    update=price_list_update_schema,
    partial_update=price_list_partial_update_schema,
    destroy=price_list_destroy_schema,
    set_default=price_list_set_default_schema,
)

# ============================================================================
# ProductPriceHistory ViewSet Schema
# ============================================================================

price_history_list_schema = extend_schema(
    summary="List product price history",
    description="""
    List product price history with cursor pagination and filtering.

    **Read-Only:** Price history is automatically created when product prices change.

    **Filters:**
    - product: Filter by product ID
    - price_list: Filter by price list ID
    - valid_from_after: Filter by valid_from >= timestamp
    - valid_from_before: Filter by valid_from <= timestamp
    """,
    parameters=[
        OpenApiParameter(
            name="product",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by product ID",
        ),
        OpenApiParameter(
            name="price_list",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by price list ID",
        ),
        OpenApiParameter(
            name="valid_from_after",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Valid from after timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="valid_from_before",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Valid from before timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedPriceHistoryList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": ProductPriceHistorySerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

price_history_retrieve_schema = extend_schema(
    summary="Get price history entry details",
    description="Retrieve detailed price history entry with audit trail information.",
    responses={
        200: ProductPriceHistorySerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

ProductPriceHistoryViewSetSchema = extend_schema_view(
    list=price_history_list_schema,
    retrieve=price_history_retrieve_schema,
)

# ============================================================================
# ProductCostHistory ViewSet Schema
# ============================================================================

cost_history_list_schema = extend_schema(
    summary="List product cost history",
    description="""
    List product cost history with cursor pagination and filtering.

    **Read-Only:** Cost history is automatically created when product costs change.

    **Filters:**
    - product: Filter by product ID
    - valid_from_after: Filter by valid_from >= timestamp
    - valid_from_before: Filter by valid_from <= timestamp
    """,
    parameters=[
        OpenApiParameter(
            name="product",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by product ID",
        ),
        OpenApiParameter(
            name="valid_from_after",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Valid from after timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="valid_from_before",
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description="Valid from before timestamp (ISO 8601)",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedCostHistoryList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": ProductCostHistorySerializer(many=True),
            },
        ),
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

cost_history_retrieve_schema = extend_schema(
    summary="Get cost history entry details",
    description="Retrieve detailed cost history entry for COGS calculations and inventory valuation.",
    responses={
        200: ProductCostHistorySerializer,
        404: InventarioErrorSerializer,
        401: InventarioErrorSerializer,
    },
    tags=["inventory-pricing"],
)

ProductCostHistoryViewSetSchema = extend_schema_view(
    list=cost_history_list_schema,
    retrieve=cost_history_retrieve_schema,
)
