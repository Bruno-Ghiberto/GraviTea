"""
Compras (Purchases) views for Gravitea ERP.

Provides ViewSets for Supplier, PurchaseOrder, and GoodsReceipt management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from apps.auth.permissions import HasModulePermission
from apps.core.pagination import StandardCursorPagination

from .models import (
    PURCHASE_ORDER_TRANSITIONS,
    GoodsReceipt,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
)
from .serializers import (
    GoodsReceiptCreateSerializer,
    GoodsReceiptSerializer,
    PurchaseOrderSerializer,
    SupplierCreateSerializer,
    SupplierSerializer,
)
from .services import GoodsReceiptService

logger = logging.getLogger("compras")


# ============================================================
# Supplier (migrated from inventario — T010)
# ============================================================


class SupplierFilter(filters.FilterSet):
    """Filter for Supplier queryset."""

    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    is_active = filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Supplier
        fields = ["name", "is_active"]


class SupplierViewSet(viewsets.ModelViewSet):
    """
    Supplier management viewset.

    Endpoints:
        GET    /api/v1/compras/suppliers/             - List suppliers
        POST   /api/v1/compras/suppliers/             - Create supplier
        GET    /api/v1/compras/suppliers/{id}/        - Get supplier details
        PATCH  /api/v1/compras/suppliers/{id}/        - Update supplier
        DELETE /api/v1/compras/suppliers/{id}/        - Soft delete (set is_active=False)
        GET    /api/v1/compras/suppliers/search/?q={query} - Search by tax_id or email
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "purchases"
    pagination_class = StandardCursorPagination
    filterset_class = SupplierFilter

    def get_queryset(self) -> QuerySet[Supplier]:
        """Return suppliers for current tenant."""
        return Supplier.objects.all()

    def get_serializer_class(self) -> type[Serializer]:
        if self.action in ["create", "update", "partial_update"]:
            return SupplierCreateSerializer
        return SupplierSerializer

    def perform_destroy(self, instance: Supplier) -> None:
        """Soft delete supplier by deactivating."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        logger.info(f"Supplier deactivated: {instance.name}")

    @action(detail=False, methods=["get"])
    def search(self, request: Request) -> Response:
        """
        Search suppliers by tax_id or email using blind indexes.

        Query param: ?q=search_term

        Uses blind index for privacy-preserving search.
        """
        query = request.query_params.get("q", "")
        if not query:
            return Response(
                {"detail": 'Query parameter "q" is required.'}, status=status.HTTP_400_BAD_REQUEST
            )

        # Generate blind index for search
        from apps.core.encryption.utils import compute_blind_index

        blind_idx = compute_blind_index(query)

        # Search by tax_id or email blind indexes
        suppliers = self.get_queryset().filter(
            models.Q(tax_id_hash=blind_idx) | models.Q(email_hash=blind_idx)
        )

        serializer = self.get_serializer(suppliers, many=True)
        return Response(serializer.data)


# ============================================================
# PurchaseOrder (T020)
# ============================================================


class PurchaseOrderFilter(filters.FilterSet):
    """Filter for PurchaseOrder queryset."""

    status = filters.CharFilter(field_name="status")
    supplier = filters.UUIDFilter(field_name="supplier_id")
    order_date_from = filters.DateFilter(field_name="order_date", lookup_expr="gte")
    order_date_to = filters.DateFilter(field_name="order_date", lookup_expr="lte")

    class Meta:
        model = PurchaseOrder
        fields = ["status", "supplier", "order_date_from", "order_date_to"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    PurchaseOrder management with state machine actions.

    Endpoints:
        GET    /api/v1/compras/purchase-orders/                - List POs
        POST   /api/v1/compras/purchase-orders/                - Create PO (DRAFT)
        GET    /api/v1/compras/purchase-orders/{id}/           - Get PO detail
        PATCH  /api/v1/compras/purchase-orders/{id}/           - Update PO (mutable fields by state)
        DELETE /api/v1/compras/purchase-orders/{id}/           - Delete DRAFT PO only
        POST   /api/v1/compras/purchase-orders/{id}/confirm/   - DRAFT → CONFIRMED
        POST   /api/v1/compras/purchase-orders/{id}/cancel/    - → CANCELLED
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "purchases"
    pagination_class = StandardCursorPagination
    serializer_class = PurchaseOrderSerializer
    filterset_class = PurchaseOrderFilter

    def get_queryset(self) -> QuerySet[PurchaseOrder]:
        """Return purchase orders for current tenant with items prefetched."""
        return PurchaseOrder.objects.prefetch_related("items").all()

    def perform_destroy(self, instance: PurchaseOrder) -> None:
        """Only allow deletion of DRAFT POs."""
        if instance.status != PurchaseOrderStatus.DRAFT:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"status": "Only DRAFT purchase orders can be deleted."}
            )
        instance.delete()

    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str = None) -> Response:
        """Transition PO from DRAFT to CONFIRMED."""
        po = self.get_object()
        if not po.can_transition_to(PurchaseOrderStatus.CONFIRMED):
            return Response(
                {"detail": f"Cannot confirm PO in status '{po.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        if not po.items.exists():
            return Response(
                {"detail": "Cannot confirm PO without line items."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        po.status = PurchaseOrderStatus.CONFIRMED
        po.save(update_fields=["status", "updated_at"])
        logger.info("PO confirmed: %s", po.order_number)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str = None) -> Response:
        """Transition PO to CANCELLED from DRAFT/CONFIRMED/PARTIAL_RECEIVED."""
        po = self.get_object()
        if not po.can_transition_to(PurchaseOrderStatus.CANCELLED):
            return Response(
                {"detail": f"Cannot cancel PO in status '{po.status}'."},
                status=status.HTTP_409_CONFLICT,
            )

        po.status = PurchaseOrderStatus.CANCELLED
        po.save(update_fields=["status", "updated_at"])
        logger.info("PO cancelled: %s", po.order_number)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"], url_path="receive")
    def receive(self, request: Request, pk: str = None) -> Response:
        """
        Create a goods receipt against this PO.

        POST /api/v1/compras/purchase-orders/{id}/receive/
        Body: {receipt_number, branch, lines: [{purchase_order_item_id, quantity_received}], notes?}
        """
        po = self.get_object()
        serializer = GoodsReceiptCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            gr = GoodsReceiptService.create_receipt(
                tenant_id=str(po.tenant_id),
                purchase_order_id=str(po.id),
                receipt_number=serializer.validated_data["receipt_number"],
                lines=serializer.validated_data["lines"],
                branch_id=str(serializer.validated_data["branch"]),
                received_by_id=str(request.user.id) if request.user else None,
                notes=serializer.validated_data.get("notes"),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            GoodsReceiptSerializer(gr).data,
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# GoodsReceipt (T031) — Read-only + standalone list
# ============================================================


class GoodsReceiptFilter(filters.FilterSet):
    """Filter for GoodsReceipt queryset."""

    purchase_order = filters.UUIDFilter(field_name="purchase_order_id")
    receipt_date_from = filters.DateFilter(field_name="receipt_date", lookup_expr="gte")
    receipt_date_to = filters.DateFilter(field_name="receipt_date", lookup_expr="lte")

    class Meta:
        model = GoodsReceipt
        fields = ["purchase_order", "receipt_date_from", "receipt_date_to"]


class GoodsReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Goods Receipt read-only viewset (standalone list + detail).

    Endpoints:
        GET /api/v1/compras/goods-receipts/       - List all receipts
        GET /api/v1/compras/goods-receipts/{id}/   - Get receipt detail

    Creation is handled via PurchaseOrderViewSet.receive action.
    No update or delete — GoodsReceipt is immutable.
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "purchases"
    pagination_class = StandardCursorPagination
    serializer_class = GoodsReceiptSerializer
    filterset_class = GoodsReceiptFilter

    def get_queryset(self) -> QuerySet[GoodsReceipt]:
        """Return goods receipts for current tenant with lines prefetched."""
        return GoodsReceipt.objects.prefetch_related("lines").all()
