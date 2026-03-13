"""
drf-spectacular schema definitions for ventas views.

Provides comprehensive OpenAPI schema documentation for all sales
endpoints using @extend_schema and @extend_schema_view decorators.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

from .serializers import (
    CustomerSerializer,
    SaleOrderDetailSerializer,
    SaleOrderItemSerializer,
    SaleOrderSerializer,
)

# ============================================================================
# RFC 7807 Error Response Serializers
# ============================================================================


class VentasErrorSerializer(serializers.Serializer):
    """RFC 7807 Problem Details for HTTP APIs error response (ventas-specific)."""

    type = serializers.CharField(
        help_text="URI reference identifying the problem type",
        default="about:blank",
    )
    title = serializers.CharField(help_text="Short, human-readable summary")
    status = serializers.IntegerField(help_text="HTTP status code")
    detail = serializers.CharField(
        help_text="Human-readable explanation", required=False
    )
    instance = serializers.CharField(
        help_text="URI reference identifying specific occurrence",
        required=False,
    )


class VentasValidationErrorSerializer(serializers.Serializer):
    """Validation error response (400 Bad Request) for ventas module."""

    detail = serializers.CharField(help_text="Error description")
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Field-specific validation errors",
        required=False,
    )


class VentasConflictErrorSerializer(serializers.Serializer):
    """Conflict error response (409) for lifecycle violations."""

    error = inline_serializer(
        name="VentasConflictDetail",
        fields={
            "code": serializers.CharField(help_text="Machine-readable error code"),
            "message": serializers.CharField(help_text="Human-readable description"),
        },
    )


# ============================================================================
# Customer ViewSet Schema
# ============================================================================

customer_list_schema = extend_schema(
    summary="List customers",
    description="""
    List customers with cursor pagination and optional filtering.

    **Filters:**
    - search: Search by razon_social or cuit (SearchFilter)
    - is_active: Filter by active status
    - condicion_iva: Filter by IVA condition code
    """,
    parameters=[
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search by razon_social or cuit",
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active status",
        ),
        OpenApiParameter(
            name="condicion_iva",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by IVA condition code (1=RI, 4=Exento, 5=CF, 6=Monotributo)",
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
            name="PaginatedCustomerList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": CustomerSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=VentasErrorSerializer,
            description="Authentication required",
        ),
    },
    tags=["ventas-customers"],
)

customer_create_schema = extend_schema(
    summary="Create customer",
    description="""
    Register a new customer with fiscal identification.

    **Constraints:**
    - CUIT must be exactly 11 digits with valid Modulo-11 check digit.
    - CUIT must be unique per tenant.
    - condicion_iva determines invoice type resolution (A/B/C).
    """,
    request=CustomerSerializer,
    responses={
        201: CustomerSerializer,
        400: VentasValidationErrorSerializer,
        401: VentasErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Responsable Inscripto",
            value={
                "cuit": "20345678901",
                "doc_tipo": 80,
                "condicion_iva": 1,
                "razon_social": "ACME S.A.",
                "domicilio": "Av. Corrientes 1234, CABA",
                "email": "contacto@acme.com.ar",
                "telefono": "011-4567-8901",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="Consumidor Final",
            value={
                "cuit": "20000000009",
                "doc_tipo": 99,
                "condicion_iva": 5,
                "razon_social": "Consumidor Final",
            },
            request_only=True,
        ),
    ],
    tags=["ventas-customers"],
)

customer_retrieve_schema = extend_schema(
    summary="Get customer details",
    description="Retrieve customer details including fiscal identification and contact info.",
    responses={
        200: CustomerSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-customers"],
)

customer_update_schema = extend_schema(
    summary="Update customer",
    description="Update customer data. CUIT uniqueness per tenant is enforced.",
    request=CustomerSerializer,
    responses={
        200: CustomerSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-customers"],
)

customer_partial_update_schema = extend_schema(
    summary="Partial update customer",
    description="Partially update customer fields.",
    request=CustomerSerializer,
    responses={
        200: CustomerSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-customers"],
)

customer_destroy_schema = extend_schema(
    summary="Deactivate customer",
    description="Soft-deactivate customer by setting is_active=False.",
    responses={
        204: None,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-customers"],
)

CustomerViewSetSchema = extend_schema_view(
    list=customer_list_schema,
    create=customer_create_schema,
    retrieve=customer_retrieve_schema,
    update=customer_update_schema,
    partial_update=customer_partial_update_schema,
    destroy=customer_destroy_schema,
)

# ============================================================================
# SaleOrder ViewSet Schema
# ============================================================================

sale_order_list_schema = extend_schema(
    summary="List sale orders",
    description="""
    List sale orders with cursor pagination and optional filtering.

    **Filters:**
    - status: Filter by order status (DRAFT, CONFIRMED, INVOICED)
    - customer: Filter by customer UUID
    - date_from: Filter by sale_date >= date
    - date_to: Filter by sale_date <= date
    """,
    parameters=[
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by order status",
            enum=["DRAFT", "CONFIRMED", "INVOICED"],
        ),
        OpenApiParameter(
            name="customer",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by customer UUID",
        ),
        OpenApiParameter(
            name="date_from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Sale date >= this date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="date_to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Sale date <= this date (YYYY-MM-DD)",
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
            name="PaginatedSaleOrderList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": SaleOrderSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=VentasErrorSerializer,
            description="Authentication required",
        ),
    },
    tags=["ventas-orders"],
)

sale_order_create_schema = extend_schema(
    summary="Create sale order",
    description="""
    Create a new sale order in DRAFT status.

    **Constraints:**
    - Customer must belong to the same tenant.
    - Branch must belong to the same tenant.
    - Order starts in DRAFT status with zero totals.
    - Add items via the nested items endpoint to populate totals.
    """,
    request=SaleOrderSerializer,
    responses={
        201: SaleOrderSerializer,
        400: VentasValidationErrorSerializer,
        401: VentasErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="New Draft Order",
            value={
                "customer": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "branch": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
            },
            request_only=True,
        ),
    ],
    tags=["ventas-orders"],
)

sale_order_retrieve_schema = extend_schema(
    summary="Get sale order details",
    description="""
    Retrieve sale order with nested items list.

    Returns the full order detail including all line items with
    product info, quantities, prices, and calculated totals.
    """,
    responses={
        200: SaleOrderDetailSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_update_schema = extend_schema(
    summary="Update sale order",
    description="""
    Update a sale order. Only DRAFT orders can be modified.

    **Lifecycle rules:**
    - DRAFT: Fully editable.
    - CONFIRMED: Returns 409 Conflict.
    - INVOICED: Returns 409 Conflict (immutable).
    """,
    request=SaleOrderSerializer,
    responses={
        200: SaleOrderSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_partial_update_schema = extend_schema(
    summary="Partial update sale order",
    description="Partially update a DRAFT sale order. Non-DRAFT orders return 409.",
    request=SaleOrderSerializer,
    responses={
        200: SaleOrderSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_destroy_schema = extend_schema(
    summary="Delete sale order",
    description="""
    Delete a sale order. Only DRAFT orders can be deleted.

    **Lifecycle rules:**
    - DRAFT: Permanently deleted with all items.
    - CONFIRMED/INVOICED: Returns 409 Conflict.
    """,
    responses={
        204: None,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_confirm_schema = extend_schema(
    summary="Confirm sale order",
    description="""
    Confirm a DRAFT sale order: reserve stock and create a Comprobante DRAFT.

    **Lifecycle transition:** DRAFT → CONFIRMED

    **Side effects:**
    - Stock is reserved via StockMovement (SALE type).
    - A Comprobante (invoice draft) is created and linked to the order.
    - confirmed_at and confirmed_by are set.

    **Possible errors:**
    - 409 insufficient_stock: Not enough stock for one or more items.
    - 409 confirm_failed: Order is not in DRAFT status or other business rule violation.
    """,
    request=None,
    responses={
        200: OpenApiResponse(description="Order confirmed with comprobante details"),
        401: VentasErrorSerializer,
        404: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_authorize_schema = extend_schema(
    summary="Authorize sale order (ARCA)",
    description="""
    Authorize a CONFIRMED sale order: submit to ARCA and commit stock.

    **Lifecycle transition:** CONFIRMED → INVOICED

    **Side effects:**
    - Comprobante is submitted to ARCA via WSFEv1 FECAESolicitar.
    - On success: CAE is assigned, order transitions to INVOICED.
    - On failure: ARCA rejection details are returned.

    **Possible errors:**
    - 409 authorize_failed: ARCA rejected the invoice (details in arca_errors).
    - 504 arca_timeout: ARCA service did not respond in time.
    """,
    request=None,
    responses={
        200: OpenApiResponse(description="Order authorized with CAE details"),
        401: VentasErrorSerializer,
        404: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
        504: VentasErrorSerializer,
    },
    tags=["ventas-orders"],
)

sale_order_invoice_schema = extend_schema(
    summary="Get linked invoice",
    description="""
    Retrieve the linked comprobante (invoice) for an INVOICED order.

    Returns comprobante details including CAE, amounts, and dates.
    Returns 404 if no invoice is linked (order not yet authorized).
    """,
    responses={
        200: OpenApiResponse(
            description="Linked comprobante details",
            response=inline_serializer(
                name="ComprobanteLink",
                fields={
                    "comprobante_id": serializers.UUIDField(),
                    "cbte_tipo": serializers.IntegerField(),
                    "cbte_nro": serializers.IntegerField(),
                    "status": serializers.CharField(),
                    "cae": serializers.CharField(allow_null=True),
                    "cae_fch_vto": serializers.CharField(allow_null=True),
                    "imp_total": serializers.CharField(),
                    "imp_neto": serializers.CharField(),
                    "imp_iva": serializers.CharField(),
                    "cbte_fch": serializers.CharField(),
                },
            ),
        ),
        401: VentasErrorSerializer,
        404: VentasErrorSerializer,
    },
    tags=["ventas-orders"],
)

SaleOrderViewSetSchema = extend_schema_view(
    list=sale_order_list_schema,
    create=sale_order_create_schema,
    retrieve=sale_order_retrieve_schema,
    update=sale_order_update_schema,
    partial_update=sale_order_partial_update_schema,
    destroy=sale_order_destroy_schema,
    confirm=sale_order_confirm_schema,
    authorize=sale_order_authorize_schema,
    invoice=sale_order_invoice_schema,
)

# ============================================================================
# SaleOrderItem ViewSet Schema
# ============================================================================

sale_order_item_list_schema = extend_schema(
    summary="List sale order items",
    description="List all line items for a specific sale order.",
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    responses={
        200: SaleOrderItemSerializer(many=True),
        401: OpenApiResponse(
            response=VentasErrorSerializer,
            description="Authentication required",
        ),
        404: OpenApiResponse(
            response=VentasErrorSerializer,
            description="Parent sale order not found",
        ),
    },
    tags=["ventas-order-items"],
)

sale_order_item_create_schema = extend_schema(
    summary="Add item to sale order",
    description="""
    Add a line item to a sale order. Only DRAFT orders accept new items.

    **Auto-calculated fields:**
    - subtotal = quantity * unit_price
    - iva_amount = subtotal * (tax_rate / 100)

    After adding, parent order totals are recalculated automatically.
    """,
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    request=SaleOrderItemSerializer,
    responses={
        201: SaleOrderItemSerializer,
        400: VentasValidationErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Add product item",
            value={
                "product": "c3d4e5f6-a7b8-9012-cdef-123456789012",
                "quantity": "5.0000",
                "unit_price": "150.000",
                "tax_rate": "21.00",
            },
            request_only=True,
        ),
    ],
    tags=["ventas-order-items"],
)

sale_order_item_retrieve_schema = extend_schema(
    summary="Get sale order item details",
    description="Retrieve a specific line item with product info and calculated amounts.",
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    responses={
        200: SaleOrderItemSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
    },
    tags=["ventas-order-items"],
)

sale_order_item_update_schema = extend_schema(
    summary="Update sale order item",
    description="""
    Update a line item. Only items on DRAFT orders can be modified.

    After updating, parent order totals are recalculated automatically.
    """,
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    request=SaleOrderItemSerializer,
    responses={
        200: SaleOrderItemSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-order-items"],
)

sale_order_item_partial_update_schema = extend_schema(
    summary="Partial update sale order item",
    description="Partially update a line item on a DRAFT order.",
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    request=SaleOrderItemSerializer,
    responses={
        200: SaleOrderItemSerializer,
        400: VentasValidationErrorSerializer,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-order-items"],
)

sale_order_item_destroy_schema = extend_schema(
    summary="Remove item from sale order",
    description="""
    Remove a line item from a sale order. Only DRAFT orders allow item removal.

    After removing, parent order totals are recalculated automatically.
    """,
    parameters=[
        OpenApiParameter(
            name="order_pk",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Parent sale order UUID",
        ),
    ],
    responses={
        204: None,
        404: VentasErrorSerializer,
        401: VentasErrorSerializer,
        409: VentasConflictErrorSerializer,
    },
    tags=["ventas-order-items"],
)

SaleOrderItemViewSetSchema = extend_schema_view(
    list=sale_order_item_list_schema,
    create=sale_order_item_create_schema,
    retrieve=sale_order_item_retrieve_schema,
    update=sale_order_item_update_schema,
    partial_update=sale_order_item_partial_update_schema,
    destroy=sale_order_item_destroy_schema,
)
