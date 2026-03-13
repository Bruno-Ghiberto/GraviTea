"""
Inventory views for Gravitea ERP.

Provides ViewSets for Product and StockMovement management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.db import models
from django.db.models import QuerySet
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

if TYPE_CHECKING:
    from .models import Product, StockMovement

from apps.core.observability.business_metrics import record_inventory_movement
from apps.core.pagination import (PriceHistoryCursorPagination,
                                  ProductCursorPagination,
                                  StandardCursorPagination)

from .models import (BranchStock, PriceList, Product, ProductCategory,
                     ProductCostHistory, ProductPriceHistory, StockMovement)
from .schema import (CategoryViewSetSchema, PriceListViewSetSchema,
                     ProductCostHistoryViewSetSchema,
                     ProductPriceHistoryViewSetSchema, ProductViewSetSchema,
                     StockMovementViewSetSchema)
from .serializers import (BranchStockSerializer, CategoryCreateSerializer,
                          CategorySerializer, PriceListSerializer,
                          ProductCostHistorySerializer,
                          ProductCreateSerializer, ProductDetailSerializer,
                          ProductPriceHistorySerializer, ProductSerializer,
                          StockMovementCreateSerializer,
                          StockMovementSerializer)

logger = logging.getLogger("inventory")


class ProductFilter(filters.FilterSet):
    """Filter for Product queryset."""

    category = filters.UUIDFilter(field_name="category_id")
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    sku = filters.CharFilter(field_name="sku", lookup_expr="iexact")
    is_active = filters.BooleanFilter(field_name="is_active")
    min_price = filters.NumberFilter(field_name="unit_price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="unit_price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "name", "sku", "is_active", "min_price", "max_price"]


@ProductViewSetSchema
class ProductViewSet(viewsets.ModelViewSet):
    """
    Product management viewset.

    Endpoints:
        GET    /api/v1/inventory/products/           - List products
        POST   /api/v1/inventory/products/           - Create product
        GET    /api/v1/inventory/products/{id}/      - Get product details
        PATCH  /api/v1/inventory/products/{id}/      - Update product
        DELETE /api/v1/inventory/products/{id}/      - Soft delete product
        GET    /api/v1/inventory/products/{id}/stock/ - Get stock by branch
        POST   /api/v1/inventory/products/search/    - Search by barcode
    """

    permission_classes = [IsAuthenticated]
    pagination_class = ProductCursorPagination
    filterset_class = ProductFilter

    def get_queryset(self) -> QuerySet[Product]:
        """Return products for current tenant with optimized queries.

        Optimization for N+1:
        - select_related for ForeignKey fields accessed in serializer (tenant, category, supplier)
        - prefetch_related for reverse ForeignKey (stock_snapshots)
        """
        return (
            Product.objects
            .select_related("tenant", "category", "supplier")
            .prefetch_related("stock_snapshots")
            .all()
        )

    def get_serializer_class(self) -> type[Serializer]:
        if self.action == "create":
            return ProductCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ProductCreateSerializer
        elif self.action == "retrieve":
            return ProductDetailSerializer
        return ProductSerializer

    def perform_destroy(self, instance: Product) -> None:
        """Soft delete product by deactivating."""
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        logger.info(f"Product deactivated: {instance.sku}")

    @action(detail=True, methods=["get"])
    def stock(self, request: Request, pk: str | None = None) -> Response:
        """Get stock levels by branch for this product."""
        product = self.get_object()
        branch_stocks = BranchStock.objects.filter(product=product).select_related("branch")

        serializer = BranchStockSerializer(branch_stocks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def search(self, request: Request) -> Response:
        """
        Search product by barcode using blind index.

        Request body:
            {"barcode": "1234567890123"}

        Returns matching product or 404.
        """
        barcode = request.data.get("barcode")
        if not barcode:
            return Response({"detail": "Barcode is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate blind index for search
        from apps.core.encryption.utils import compute_blind_index

        blind_idx = compute_blind_index(barcode)

        try:
            product = Product.objects.get(barcode_blind_idx=blind_idx)
            serializer = ProductDetailSerializer(product)
            return Response(serializer.data)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)


class StockMovementFilter(filters.FilterSet):
    """Filter for StockMovement queryset."""

    product = filters.UUIDFilter(field_name="product_id")
    branch = filters.UUIDFilter(field_name="branch_id")
    type = filters.ChoiceFilter(field_name="type", choices=StockMovement.MovementType.choices)
    reference_id = filters.CharFilter(field_name="reference_id", lookup_expr="iexact")
    created_after = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = StockMovement
        fields = [
            "product",
            "branch",
            "type",
            "reference_id",
            "created_after",
            "created_before",
        ]


@StockMovementViewSetSchema
class StockMovementViewSet(viewsets.ModelViewSet):
    """
    Stock movement management viewset.

    Note: Stock movements are immutable. Update and delete operations
    are not allowed. Create adjustment movements instead.

    Endpoints:
        GET    /api/v1/inventory/movements/      - List movements
        POST   /api/v1/inventory/movements/      - Create movement
        GET    /api/v1/inventory/movements/{id}/ - Get movement details
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    filterset_class = StockMovementFilter
    http_method_names = ["get", "post", "head", "options"]  # No PUT, PATCH, DELETE

    def get_queryset(self) -> QuerySet[StockMovement]:
        """Return movements for current tenant."""
        return StockMovement.objects.select_related("product", "branch").all()

    def get_serializer_class(self) -> type[Serializer]:
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create stock movement and update branch stock."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        logger.info(
            f"Stock movement created: {movement.type} "
            f"{movement.product.sku} x {movement.quantity_delta} @ {movement.branch.name}"
        )

        # Record business metric for inventory movement
        tenant_id = str(request.user.tenant_id) if hasattr(request.user, "tenant_id") else "unknown"
        record_inventory_movement(
            tenant_id=tenant_id,
            branch_id=str(movement.branch_id) if movement.branch_id else "unknown",
            operation=movement.type,
            product_type=movement.product.category.name if movement.product.category else "unknown",
            quantity=abs(movement.quantity_delta),
        )

        # Return read serializer for response
        response_serializer = StockMovementSerializer(movement)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Prevent update of stock movements."""
        return Response(
            {"detail": "Stock movements are immutable and cannot be updated."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Prevent deletion of stock movements."""
        return Response(
            {"detail": "Stock movements cannot be deleted. Create a reversal movement instead."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )


@CategoryViewSetSchema
class CategoryViewSet(viewsets.ModelViewSet):
    """
    Product category management viewset.

    Endpoints:
        GET    /api/v1/inventory/categories/      - List categories
        POST   /api/v1/inventory/categories/      - Create category
        GET    /api/v1/inventory/categories/{id}/ - Get category details
        PATCH  /api/v1/inventory/categories/{id}/ - Update category
        DELETE /api/v1/inventory/categories/{id}/ - Delete category
        GET    /api/v1/inventory/categories/tree/ - Get hierarchical tree view
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

    def get_queryset(self) -> QuerySet[ProductCategory]:
        """Return categories for current tenant."""
        queryset = ProductCategory.objects.select_related("parent").all()

        # Optional filter: only root categories
        only_root = self.request.query_params.get("root_only")
        if only_root and only_root.lower() == "true":
            queryset = queryset.filter(parent__isnull=True)

        return queryset

    def get_serializer_class(self) -> type[Serializer]:
        if self.action in ["create", "update", "partial_update"]:
            return CategoryCreateSerializer
        return CategorySerializer

    @action(detail=False, methods=["get"])
    def tree(self, request: Request) -> Response:
        """
        Get hierarchical category tree.

        Returns all root categories with their nested children.
        Optimized to use a single database query regardless of tree depth.
        """
        # Fetch ALL categories in a single query (avoids N+1)
        all_categories = list(ProductCategory.objects.all().values("id", "name", "parent_id"))

        # Build lookup dictionary: parent_id -> list of children
        children_by_parent: dict[str | None, list[dict]] = {}
        category_dict: dict[str, dict] = {}

        for cat in all_categories:
            cat_id = str(cat["id"])
            parent_id = str(cat["parent_id"]) if cat["parent_id"] else None
            category_dict[cat_id] = {
                "id": cat_id,
                "name": cat["name"],
                "children": [],
            }
            if parent_id not in children_by_parent:
                children_by_parent[parent_id] = []
            children_by_parent[parent_id].append(category_dict[cat_id])

        # Link children to parents
        for cat_id, cat_data in category_dict.items():
            if cat_id in children_by_parent:
                cat_data["children"] = children_by_parent[cat_id]

        # Return root categories (those with no parent)
        tree_data = children_by_parent.get(None, [])
        return Response(tree_data)


@PriceListViewSetSchema
class PriceListViewSet(viewsets.ModelViewSet):
    """
    Price list management viewset.

    Endpoints:
        GET    /api/v1/inventory/price-lists/             - List price lists
        POST   /api/v1/inventory/price-lists/             - Create price list
        GET    /api/v1/inventory/price-lists/{id}/        - Get price list details
        PATCH  /api/v1/inventory/price-lists/{id}/        - Update price list
        DELETE /api/v1/inventory/price-lists/{id}/        - Delete price list
        POST   /api/v1/inventory/price-lists/{id}/set-default/ - Set as default
    """

    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

    def get_queryset(self) -> QuerySet[PriceList]:
        """Return price lists for current tenant."""
        return PriceList.objects.all()

    @action(detail=True, methods=["post"])
    def set_default(self, request: Request, pk: str | None = None) -> Response:
        """
        Set this price list as the default for the tenant.

        Automatically unsets other defaults.
        """
        price_list = self.get_object()

        # Clear other defaults for this tenant
        PriceList.objects.filter(tenant_id=price_list.tenant_id).update(is_default=False)

        # Set this as default
        price_list.is_default = True
        price_list.save(update_fields=["is_default"])

        logger.info(f"Price list set as default: {price_list.name}")

        return Response({"status": "default set", "id": str(price_list.id)})


class ProductPriceHistoryFilter(filters.FilterSet):
    """Filter for ProductPriceHistory queryset."""

    product = filters.UUIDFilter(field_name="product_id")
    price_list = filters.UUIDFilter(field_name="price_list_id")
    valid_from_after = filters.DateTimeFilter(field_name="valid_from", lookup_expr="gte")
    valid_from_before = filters.DateTimeFilter(field_name="valid_from", lookup_expr="lte")

    class Meta:
        model = ProductPriceHistory
        fields = ["product", "price_list", "valid_from_after", "valid_from_before"]


@ProductPriceHistoryViewSetSchema
class ProductPriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Product price history viewset (read-only).

    Price history is automatically created when product prices change.

    Endpoints:
        GET /api/v1/inventory/price-history/             - List price history
        GET /api/v1/inventory/price-history/?product={id} - Filter by product
        GET /api/v1/inventory/price-history/?price_list={id} - Filter by price list
        GET /api/v1/inventory/price-history/{id}/        - Get history entry details
    """

    serializer_class = ProductPriceHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PriceHistoryCursorPagination
    filterset_class = ProductPriceHistoryFilter

    def get_queryset(self) -> QuerySet[ProductPriceHistory]:
        """
        Return price history for current tenant.

        Filters by tenant through product relationship.
        Optimizes queries with select_related.
        """
        return (
            ProductPriceHistory.objects.filter(product__tenant_id=models.F("product__tenant_id"))
            .select_related("product", "price_list", "changed_by_user")
            .order_by("-valid_from")
        )


class ProductCostHistoryFilter(filters.FilterSet):
    """Filter for ProductCostHistory queryset."""

    product = filters.UUIDFilter(field_name="product_id")
    valid_from_after = filters.DateTimeFilter(field_name="valid_from", lookup_expr="gte")
    valid_from_before = filters.DateTimeFilter(field_name="valid_from", lookup_expr="lte")

    class Meta:
        model = ProductCostHistory
        fields = ["product", "valid_from_after", "valid_from_before"]


@ProductCostHistoryViewSetSchema
class ProductCostHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Product cost history viewset (read-only).

    Cost history is automatically created when product costs change.

    Endpoints:
        GET /api/v1/inventory/cost-history/             - List cost history
        GET /api/v1/inventory/cost-history/?product={id} - Filter by product
        GET /api/v1/inventory/cost-history/{id}/        - Get history entry details
    """

    serializer_class = ProductCostHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PriceHistoryCursorPagination
    filterset_class = ProductCostHistoryFilter

    def get_queryset(self) -> QuerySet[ProductCostHistory]:
        """
        Return cost history for current tenant.

        Filters by tenant through product relationship.
        Optimizes queries with select_related.
        """
        return (
            ProductCostHistory.objects.filter(product__tenant_id=models.F("product__tenant_id"))
            .select_related("product")
            .order_by("-valid_from")
        )
