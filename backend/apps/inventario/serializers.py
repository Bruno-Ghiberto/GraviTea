"""
Inventory serializers for Gravitea ERP.

Provides serializers for Product and StockMovement management.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.core.serializers.customization import CustomFieldsMixin

from .models import (BranchStock, PriceList, Product, ProductCategory,
                     ProductCostHistory, ProductPriceHistory, StockMovement,
                     StockSnapshot)

# Supplier serializers migrated to apps.compras.serializers (T009).
# Re-export for backward compatibility.
from apps.compras.serializers import (  # noqa: F401
    SupplierCreateSerializer,
    SupplierSerializer,
)


class ProductSerializer(serializers.ModelSerializer):
    """
    Product serializer for read operations.

    Returns product details with computed fields and related object names.
    """

    price_with_tax = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "barcode",
            "name",
            "description",
            "category",
            "category_name",
            "supplier",
            "supplier_name",
            "unit_price",
            "cost_price",
            "tax_rate",
            "price_with_tax",
            "min_stock",
            "max_stock",
            "custom_data",
            "ml_tags",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_price_with_tax(self, obj):
        """Calculate price including tax."""
        tax_multiplier = 1 + (obj.tax_rate / Decimal("100"))
        return str((obj.unit_price * tax_multiplier).quantize(Decimal("0.001")))


class ProductCreateSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """
    Product serializer for create/update operations.

    Validates SKU uniqueness within tenant and handles barcode encryption.
    """

    entity_type = "product"

    barcode = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Product barcode (will be encrypted)",
    )

    class Meta:
        model = Product
        fields = [
            "sku",
            "barcode",
            "name",
            "description",
            "category",
            "supplier",
            "unit_price",
            "cost_price",
            "tax_rate",
            "min_stock",
            "max_stock",
            "custom_data",
            "ml_tags",
            "is_active",
        ]

    def validate_sku(self, value):
        """Validate SKU uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            queryset = Product.objects.filter(tenant=tenant, sku=value)

            # Exclude current instance for updates
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError("A product with this SKU already exists.")
        return value

    def validate_category(self, value):
        """Validate category belongs to same tenant."""
        if value is None:
            return value
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Category not found in your organization.")
        return value

    def validate_supplier(self, value):
        """Validate supplier belongs to same tenant."""
        if value is None:
            return value
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Supplier not found in your organization.")
        return value

    def validate(self, data):
        """Cross-field validation for stock levels + custom_data via mixin."""
        min_stock = data.get("min_stock")
        max_stock = data.get("max_stock")

        if min_stock is not None and max_stock is not None:
            if min_stock > max_stock:
                raise serializers.ValidationError(
                    {"min_stock": "Minimum stock cannot exceed maximum stock."}
                )

        return super().validate(data)

    def create(self, validated_data):
        """Create product with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        # Barcode encryption is handled by model field
        return super().create(validated_data)


class BranchStockSerializer(serializers.ModelSerializer):
    """
    Branch stock serializer for read operations.

    Returns current stock level per branch including product,
    reserved quantity, and computed available quantity.
    """

    branch_name = serializers.CharField(source="branch.name", read_only=True)
    available_quantity = serializers.DecimalField(
        max_digits=16, decimal_places=4, read_only=True
    )

    class Meta:
        model = StockSnapshot
        fields = [
            "id",
            "branch",
            "branch_name",
            "product",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "last_updated",
        ]
        read_only_fields = ["id", "last_updated", "available_quantity"]


class ProductDetailSerializer(ProductSerializer):
    """
    Product serializer with stock information.

    Extends ProductSerializer with branch stock levels.
    """

    branch_stocks = BranchStockSerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + ["branch_stocks"]


class StockMovementSerializer(serializers.ModelSerializer):
    """
    Stock movement serializer for read operations.

    Returns movement details with product and branch info.
    """

    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    total_value = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "branch",
            "branch_name",
            "type",
            "quantity_delta",
            "cost_snapshot",
            "total_value",
            "reference_id",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_total_value(self, obj):
        """Calculate total value of movement."""
        if obj.cost_snapshot is None:
            return None
        return str((obj.quantity_delta * obj.cost_snapshot).quantize(Decimal("0.001")))


class StockMovementCreateSerializer(serializers.ModelSerializer):
    """
    Stock movement serializer for create operations.

    Validates product and branch belong to same tenant.
    """

    class Meta:
        model = StockMovement
        fields = [
            "product",
            "branch",
            "type",
            "quantity_delta",
            "cost_snapshot",
            "reference_id",
            "notes",
        ]

    def validate_product(self, value):
        """Validate product belongs to same tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Product not found in your organization.")
        return value

    def validate_branch(self, value):
        """Validate branch belongs to same tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Branch not found in your organization.")
        return value

    def validate_quantity_delta(self, value):
        """Validate quantity based on movement type."""
        # Quantity validation will depend on movement_type
        # For SALE, TRANS_OUT: should be negative or will be negated
        # For PURCHASE, TRANS_IN, ADJ: should be positive
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        movement_type = attrs.get("type")
        quantity_delta = attrs.get("quantity_delta")

        # Ensure quantity sign matches movement type
        outbound_types = [
            StockMovement.MovementType.SALE,
            StockMovement.MovementType.TRANS_OUT,
        ]

        if movement_type in outbound_types and quantity_delta > 0:
            attrs["quantity_delta"] = -abs(quantity_delta)
        elif movement_type not in outbound_types and quantity_delta < 0:
            attrs["quantity_delta"] = abs(quantity_delta)

        return attrs

    def create(self, validated_data):
        """Create stock movement with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant

        movement = super().create(validated_data)

        # Update BranchStock (materialized view)
        self._update_branch_stock(movement)

        return movement

    def _update_branch_stock(self, movement):
        """Update or create BranchStock record."""
        branch_stock, created = BranchStock.objects.get_or_create(
            product=movement.product,
            branch=movement.branch,
            defaults={"quantity": Decimal("0.0000")},
        )

        branch_stock.quantity += movement.quantity_delta
        branch_stock.save()  # last_updated is auto_now


class CategorySerializer(serializers.ModelSerializer):
    """
    Product category serializer for read operations.

    Returns category details with parent hierarchy and immediate children.
    """

    parent_name = serializers.CharField(source="parent.name", read_only=True, allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "name",
            "parent",
            "parent_name",
            "children",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_children(self, obj):
        """
        Return immediate child categories.

        Limited to one level for performance. Use nested requests
        for deeper traversal.
        """
        children = obj.children.all()
        if not children:
            return []
        return [{"id": str(child.id), "name": child.name} for child in children]


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Product category serializer for create/update operations.

    Validates category name uniqueness and parent references.
    """

    class Meta:
        model = ProductCategory
        fields = ["name", "parent"]

    def validate_name(self, value):
        """Validate category name uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            queryset = ProductCategory.objects.filter(tenant=tenant, name=value)

            # Exclude current instance for updates
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError("A category with this name already exists.")
        return value

    def validate_parent(self, value):
        """Validate parent belongs to same tenant."""
        if value is None:
            return value

        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if value.tenant_id != tenant.id:
                raise serializers.ValidationError("Parent category not found in your organization.")
        return value

    def validate(self, attrs):
        """Prevent circular parent relationships."""
        parent = attrs.get("parent")
        if parent and self.instance:
            # Check if setting parent would create a cycle
            current = parent
            while current is not None:
                if current.id == self.instance.id:
                    raise serializers.ValidationError(
                        {"parent": "Circular parent relationship detected."}
                    )
                current = current.parent
        return attrs

    def create(self, validated_data):
        """Create category with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


class PriceListSerializer(serializers.ModelSerializer):
    """
    Price list serializer for read and write operations.

    Validates single default price list per tenant.
    """

    class Meta:
        model = PriceList
        fields = [
            "id",
            "name",
            "margin_pct",
            "is_default",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        """Validate price list name uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            queryset = PriceList.objects.filter(tenant=tenant, name=value)

            # Exclude current instance for updates
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError("A price list with this name already exists.")
        return value

    def validate(self, data):
        """
        Validate single default price list per tenant.

        Note: The model's save() method also enforces this constraint,
        but we validate early for better error messages.
        """
        is_default = data.get("is_default", False)
        if is_default:
            request = self.context.get("request")
            if request and hasattr(request, "user"):
                tenant = request.user.tenant
                existing_default = PriceList.objects.filter(tenant=tenant, is_default=True)

                # Exclude current instance for updates
                if self.instance:
                    existing_default = existing_default.exclude(pk=self.instance.pk)

                if existing_default.exists():
                    raise serializers.ValidationError(
                        {
                            "is_default": (
                                f"A default price list already exists: "
                                f"{existing_default.first().name}. "
                                f"Only one default price list is allowed per organization."
                            )
                        }
                    )
        return data

    def create(self, validated_data):
        """Create price list with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


class ProductPriceHistorySerializer(serializers.ModelSerializer):
    """
    Product price history serializer for read operations.

    Returns price history entries with product and price list details.
    Tracks price changes over time with audit trail.
    """

    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    price_list_name = serializers.CharField(source="price_list.name", read_only=True)
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProductPriceHistory
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "price_list",
            "price_list_name",
            "price",
            "valid_from",
            "valid_to",
            "change_reason",
            "changed_by_user",
            "changed_by_name",
        ]
        read_only_fields = ["id"]

    def get_changed_by_name(self, obj):
        """Return user's full name or username if available."""
        if not obj.changed_by_user:
            return None
        if hasattr(obj.changed_by_user, "full_name") and obj.changed_by_user.full_name:
            return obj.changed_by_user.full_name
        return obj.changed_by_user.username


class ProductCostHistorySerializer(serializers.ModelSerializer):
    """
    Product cost history serializer for read operations.

    Returns cost history entries with product details.
    Tracks cost changes for COGS calculations and inventory valuation.
    """

    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ProductCostHistory
        fields = [
            "id",
            "product",
            "product_sku",
            "product_name",
            "cost",
            "valid_from",
            "valid_to",
            "source_doc",
        ]
        read_only_fields = ["id"]
