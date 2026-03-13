"""
Ventas views for Gravitea ERP.

Provides ViewSets for Customer, SaleOrder, and SaleOrderItem
with lifecycle management and invoice integration.
"""

from __future__ import annotations

import logging

from django.conf import settings as django_settings
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from apps.core.pagination import StandardCursorPagination
from apps.inventario.services.stock_service import InsufficientStockError

from .models import Customer, SaleOrder, SaleOrderItem, SaleOrderStatus
from .schema import (
    CustomerViewSetSchema,
    SaleOrderItemViewSetSchema,
    SaleOrderViewSetSchema,
)
from .serializers import (
    CustomerSerializer,
    SaleOrderDetailSerializer,
    SaleOrderItemSerializer,
    SaleOrderSerializer,
)
from .services.sale_service import (
    SaleAuthorizeError,
    SaleConfirmError,
    SaleService,
    SaleTimeoutError,
)

logger = logging.getLogger("ventas")


# ============================================================
# Customer
# ============================================================


@CustomerViewSetSchema
class CustomerViewSet(viewsets.ModelViewSet):
    """
    Customer CRUD viewset.

    Endpoints:
        GET    /api/v1/ventas/customers/        - List customers
        POST   /api/v1/ventas/customers/        - Create customer
        GET    /api/v1/ventas/customers/{id}/    - Get customer detail
        PATCH  /api/v1/ventas/customers/{id}/    - Update customer
        DELETE /api/v1/ventas/customers/{id}/    - Soft deactivate
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["razon_social", "cuit"]

    def get_queryset(self) -> QuerySet[Customer]:
        """Return customers for current tenant with optional filters."""
        qs = Customer.objects.all()

        params = self.request.query_params

        is_active = params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        condicion_iva = params.get("condicion_iva")
        if condicion_iva is not None:
            try:
                qs = qs.filter(condicion_iva=int(condicion_iva))
            except (ValueError, TypeError):
                pass

        return qs

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Soft deactivate customer. Block if linked to any sale orders."""
        instance = self.get_object()

        if instance.sale_orders.exists():
            return Response(
                {
                    "error": {
                        "code": "customer_has_orders",
                        "message": (
                            "Cannot deactivate customer with existing sale orders."
                        ),
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        logger.info("Customer deactivated: %s", instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ============================================================
# SaleOrder
# ============================================================


@SaleOrderViewSetSchema
class SaleOrderViewSet(viewsets.ModelViewSet):
    """
    SaleOrder management viewset.

    Endpoints:
        GET    /api/v1/ventas/orders/              - List orders
        POST   /api/v1/ventas/orders/              - Create order (DRAFT)
        GET    /api/v1/ventas/orders/{id}/          - Get order detail
        PATCH  /api/v1/ventas/orders/{id}/          - Update order (DRAFT only)
        DELETE /api/v1/ventas/orders/{id}/          - Delete order (DRAFT only)
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

    def get_queryset(self) -> QuerySet[SaleOrder]:
        """Return sale orders for current tenant with optional filters."""
        qs = SaleOrder.objects.select_related("customer", "branch").all()

        params = self.request.query_params

        status_param = params.get("status")
        if status_param is not None:
            qs = qs.filter(status=status_param)

        customer = params.get("customer")
        if customer is not None:
            qs = qs.filter(customer_id=customer)

        date_from = params.get("date_from")
        if date_from is not None:
            qs = qs.filter(sale_date__gte=date_from)

        date_to = params.get("date_to")
        if date_to is not None:
            qs = qs.filter(sale_date__lte=date_to)

        return qs

    def get_serializer_class(self) -> type[Serializer]:
        """Use detail serializer for retrieve action."""
        if self.action == "retrieve":
            return SaleOrderDetailSerializer
        return SaleOrderSerializer

    def perform_create(self, serializer: Serializer) -> None:
        """Catch IDOR violations from tenant reference validation."""
        try:
            serializer.save()
        except ValueError as exc:
            if "IDOR violation" in str(exc):
                logger.warning("IDOR violation in SaleOrder create: %s", exc)
                raise PermissionDenied(
                    detail="Cross-tenant reference detected."
                )
            raise

    def perform_update(self, serializer: Serializer) -> None:
        """Catch IDOR violations from tenant reference validation."""
        try:
            serializer.save()
        except ValueError as exc:
            if "IDOR violation" in str(exc):
                logger.warning("IDOR violation in SaleOrder update: %s", exc)
                raise PermissionDenied(
                    detail="Cross-tenant reference detected."
                )
            raise

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Block updates for non-DRAFT orders."""
        instance = self.get_object()
        if instance.status != SaleOrderStatus.DRAFT:
            return Response(
                {
                    "error": {
                        "code": "order_not_draft",
                        "message": "Only DRAFT orders can be modified.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Block deletion for non-DRAFT orders."""
        instance = self.get_object()
        if instance.status != SaleOrderStatus.DRAFT:
            return Response(
                {
                    "error": {
                        "code": "order_not_draft",
                        "message": "Only DRAFT orders can be deleted.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    # T048: Confirm action
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request: Request, pk=None) -> Response:
        """
        Confirm a DRAFT sale order: reserve stock and create Comprobante DRAFT.

        POST /api/v1/ventas/orders/{id}/confirm/
        """
        order = self.get_object()
        sale_service = SaleService()

        try:
            result = sale_service.confirm_sale(
                order=order,
                user=request.user,
            )
        except InsufficientStockError as exc:
            # T064: Structured stock error with product/branch details
            return Response(
                {
                    "error": {
                        "code": "insufficient_stock",
                        "message": str(exc),
                        "details": {
                            "product_id": exc.product_id,
                            "product_sku": exc.product_sku,
                            "product_name": exc.product_name,
                            "available": str(exc.available),
                            "requested": str(exc.requested),
                            "branch": exc.branch_name,
                        },
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        except SaleConfirmError as exc:
            return Response(
                {
                    "error": {
                        "code": "confirm_failed",
                        "message": str(exc),
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        except IntegrityError as exc:
            logger.error("Stock constraint violation on confirm: %s", exc)
            return Response(
                {
                    "error": {
                        "code": "stock_constraint_violation",
                        "message": "Stock constraint violated during confirmation.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(result, status=status.HTTP_200_OK)

    # T049: Authorize action
    @action(detail=True, methods=["post"], url_path="authorize")
    def authorize(self, request: Request, pk=None) -> Response:
        """
        Authorize a CONFIRMED sale: submit to ARCA and commit stock.

        POST /api/v1/ventas/orders/{id}/authorize/
        """
        order = self.get_object()
        is_production = getattr(django_settings, "ARCA_IS_PRODUCTION", False)
        sale_service = SaleService()

        try:
            result = sale_service.authorize_sale(
                order=order,
                is_production=is_production,
            )
        except SaleTimeoutError as exc:
            # T072: ARCA timeout — 504 Gateway Timeout
            error_body: dict = {
                "code": "arca_timeout",
                "message": str(exc),
            }
            if exc.arca_errors:
                error_body["arca_errors"] = exc.arca_errors
            return Response(
                {"error": error_body},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except SaleAuthorizeError as exc:
            error_body: dict = {
                "code": "authorize_failed",
                "message": str(exc),
            }
            # T058: Surface ARCA rejection details when available
            if exc.arca_errors:
                error_body["arca_errors"] = exc.arca_errors
            return Response(
                {"error": error_body},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(result, status=status.HTTP_200_OK)

    # T050: Invoice retrieval action
    @action(detail=True, methods=["get"], url_path="invoice")
    def invoice(self, request: Request, pk=None) -> Response:
        """
        Get the linked comprobante (invoice) for an order.

        GET /api/v1/ventas/orders/{id}/invoice/
        """
        order = self.get_object()

        if not hasattr(order, "comprobante_direct"):
            return Response(
                {
                    "error": {
                        "code": "no_invoice",
                        "message": "This order has no linked invoice.",
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        comp = order.comprobante_direct
        return Response(
            {
                "comprobante_id": str(comp.id),
                "cbte_tipo": comp.cbte_tipo,
                "cbte_nro": comp.cbte_nro,
                "status": comp.status,
                "cae": comp.cae,
                "cae_fch_vto": str(comp.cae_fch_vto) if comp.cae_fch_vto else None,
                "imp_total": str(comp.imp_total),
                "imp_neto": str(comp.imp_neto),
                "imp_iva": str(comp.imp_iva),
                "cbte_fch": str(comp.cbte_fch),
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# SaleOrderItem (nested under SaleOrder)
# ============================================================


@SaleOrderItemViewSetSchema
class SaleOrderItemViewSet(viewsets.ModelViewSet):
    """
    SaleOrderItem management viewset, nested under SaleOrder.

    Endpoints:
        GET    /api/v1/ventas/orders/{order_pk}/items/        - List items
        POST   /api/v1/ventas/orders/{order_pk}/items/        - Add item
        GET    /api/v1/ventas/orders/{order_pk}/items/{id}/    - Get item
        PATCH  /api/v1/ventas/orders/{order_pk}/items/{id}/    - Update item
        DELETE /api/v1/ventas/orders/{order_pk}/items/{id}/    - Remove item
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SaleOrderItemSerializer

    def get_queryset(self) -> QuerySet[SaleOrderItem]:
        """Return items for the parent sale order."""
        order_pk = self.kwargs["order_pk"]
        return SaleOrderItem.objects.select_related("product").filter(
            sale_order_id=order_pk,
        )

    def _get_parent_order(self) -> SaleOrder:
        """Retrieve and validate parent sale order."""
        order_pk = self.kwargs["order_pk"]
        try:
            return SaleOrder.objects.get(pk=order_pk)
        except SaleOrder.DoesNotExist:
            raise NotFound(detail="Sale order not found.")

    def perform_create(self, serializer: Serializer) -> None:
        """Catch IDOR violations from tenant reference validation."""
        try:
            serializer.save()
        except ValueError as exc:
            if "IDOR violation" in str(exc):
                logger.warning("IDOR violation in SaleOrderItem create: %s", exc)
                raise PermissionDenied(
                    detail="Cross-tenant reference detected."
                )
            raise

    def perform_update(self, serializer: Serializer) -> None:
        """Catch IDOR violations from tenant reference validation."""
        try:
            serializer.save()
        except ValueError as exc:
            if "IDOR violation" in str(exc):
                logger.warning("IDOR violation in SaleOrderItem update: %s", exc)
                raise PermissionDenied(
                    detail="Cross-tenant reference detected."
                )
            raise

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Add item to order. Block if order is not DRAFT."""
        order = self._get_parent_order()
        if order.status != SaleOrderStatus.DRAFT:
            return Response(
                {
                    "error": {
                        "code": "order_not_draft",
                        "message": "Cannot add items to a non-DRAFT order.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save(
                    sale_order=order,
                    tenant=request.user.tenant,
                )
        except IntegrityError:
            return Response(
                {
                    "error": {
                        "code": "duplicate_product",
                        "message": "This product already exists in the order.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Recalculate order totals
        order.recalculate_totals()

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        """Update item. Block if order is not DRAFT."""
        order = self._get_parent_order()
        if order.status != SaleOrderStatus.DRAFT:
            return Response(
                {
                    "error": {
                        "code": "order_not_draft",
                        "message": "Cannot modify items on a non-DRAFT order.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        response = super().update(request, *args, **kwargs)
        order.recalculate_totals()
        return response

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """Remove item. Block if order is not DRAFT."""
        order = self._get_parent_order()
        if order.status != SaleOrderStatus.DRAFT:
            return Response(
                {
                    "error": {
                        "code": "order_not_draft",
                        "message": "Cannot remove items from a non-DRAFT order.",
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        response = super().destroy(request, *args, **kwargs)
        order.recalculate_totals()
        return response
