"""
Compras (Purchases) serializers for Gravitea ERP.

Provides serializers for Supplier CRUD and PurchaseOrder lifecycle
with nested PurchaseOrderItem, GoodsReceipt, and GoodsReceiptLine.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.core.serializers.customization import CustomFieldsMixin

from .models import (
    MUTABLE_FIELDS_BY_STATUS,
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)


# ============================================================
# Supplier (migrated from inventario — T009)
# ============================================================


class SupplierSerializer(serializers.ModelSerializer):
    """
    Supplier serializer for read operations.

    Returns supplier details with decrypted PII fields.
    """

    tax_id = serializers.CharField(source="tax_id_encrypted", read_only=True)
    email = serializers.CharField(source="email_encrypted", read_only=True)
    contact_info = serializers.CharField(source="contact_info_encrypted", read_only=True)
    address = serializers.CharField(source="address_encrypted", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "tax_id",
            "email",
            "contact_info",
            "address",
            "lead_time_days",
            "current_balance",
            "custom_data",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "current_balance", "created_at"]


class SupplierCreateSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """
    Supplier serializer for create/update operations.

    Handles encryption of PII fields.
    """

    entity_type = "supplier"

    tax_id = serializers.CharField(
        source="tax_id_encrypted", required=False, allow_blank=True, allow_null=True
    )
    email = serializers.EmailField(
        source="email_encrypted", required=False, allow_blank=True, allow_null=True
    )
    contact_info = serializers.CharField(
        source="contact_info_encrypted", required=False, allow_blank=True, allow_null=True
    )
    address = serializers.CharField(
        source="address_encrypted", required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = Supplier
        fields = [
            "name",
            "tax_id",
            "email",
            "contact_info",
            "address",
            "lead_time_days",
            "custom_data",
            "is_active",
        ]

    def validate_name(self, value):
        """Validate supplier name uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            queryset = Supplier.objects.filter(tenant=tenant, name=value)

            # Exclude current instance for updates
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError("A supplier with this name already exists.")
        return value

    def create(self, validated_data):
        """Create supplier with tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


# ============================================================
# PurchaseOrder + PurchaseOrderItem (T019)
# ============================================================


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    """Line item serializer — nested inside PurchaseOrderSerializer."""

    line_total = serializers.DecimalField(max_digits=17, decimal_places=3, read_only=True)
    received_quantity = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "product",
            "quantity",
            "unit_price",
            "line_total",
            "received_quantity",
        ]
        read_only_fields = ["id", "line_total", "received_quantity"]


class PurchaseOrderSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """
    PurchaseOrder serializer with nested writable items and custom fields.

    On create: items are created inline, custom_data validated.
    On update: items are replaced (delete existing + create new) for DRAFT POs.
    """

    entity_type = "purchase_order"

    items = PurchaseOrderItemSerializer(many=True)
    status = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "supplier",
            "order_number",
            "status",
            "order_date",
            "expected_delivery_date",
            "notes",
            "custom_data",
            "total_amount",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "total_amount", "created_at", "updated_at"]

    def validate_order_number(self, value: str) -> str:
        """Ensure order_number is unique within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            qs = PurchaseOrder.objects.filter(tenant=tenant, order_number=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "A purchase order with this number already exists."
                )
        return value

    def validate(self, attrs: dict) -> dict:
        """Enforce field mutability by status on update, then custom fields."""
        if self.instance:
            current_status = self.instance.status
            allowed = MUTABLE_FIELDS_BY_STATUS.get(current_status, set())
            for field_name in attrs:
                if field_name not in allowed:
                    raise serializers.ValidationError(
                        {field_name: f"Cannot modify '{field_name}' when status is {current_status}."}
                    )
        return super().validate(attrs)

    def validate_items(self, items: list[dict]) -> list[dict]:
        """Ensure at least one item on create."""
        if not self.instance and not items:
            raise serializers.ValidationError("At least one item is required.")
        return items

    def create(self, validated_data: dict) -> PurchaseOrder:
        """Create PO with nested items and compute totals.

        Delegates to super().create() so CustomFieldsMixin injects defaults.
        """
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant

        po = super().create(validated_data)

        total = Decimal("0.000")
        for item_data in items_data:
            item = PurchaseOrderItem.objects.create(purchase_order=po, **item_data)
            total += item.line_total

        po.total_amount = total
        po.save(update_fields=["total_amount"])
        return po

    def update(self, instance: PurchaseOrder, validated_data: dict) -> PurchaseOrder:
        """Update PO; replace items if provided (DRAFT only).

        Delegates to super().update() so CustomFieldsMixin handles merge.
        """
        items_data = validated_data.pop("items", None)

        instance = super().update(instance, validated_data)

        if items_data is not None and instance.status == PurchaseOrderStatus.DRAFT:
            instance.items.all().delete()
            total = Decimal("0.000")
            for item_data in items_data:
                item = PurchaseOrderItem.objects.create(
                    purchase_order=instance, **item_data
                )
                total += item.line_total
            instance.total_amount = total
            instance.save(update_fields=["total_amount", "updated_at"])

        return instance


# ============================================================
# GoodsReceipt + GoodsReceiptLine (T030)
# ============================================================


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    """GoodsReceiptLine serializer — nested inside GoodsReceiptSerializer."""

    class Meta:
        model = GoodsReceiptLine
        fields = [
            "id",
            "purchase_order_item",
            "product",
            "quantity_received",
        ]
        read_only_fields = ["id", "product"]


class GoodsReceiptLineCreateSerializer(serializers.Serializer):
    """Input serializer for creating GR lines (used in GoodsReceiptCreateSerializer)."""

    purchase_order_item_id = serializers.UUIDField()
    quantity_received = serializers.DecimalField(max_digits=17, decimal_places=3, min_value=0.001)


class GoodsReceiptSerializer(serializers.ModelSerializer):
    """GoodsReceipt read serializer with nested lines."""

    lines = GoodsReceiptLineSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "purchase_order",
            "receipt_number",
            "receipt_date",
            "received_by",
            "notes",
            "lines",
            "created_at",
        ]
        read_only_fields = fields


class GoodsReceiptCreateSerializer(serializers.Serializer):
    """
    Create-only serializer for goods receipts.

    Delegates to GoodsReceiptService for creation with validation.
    """

    receipt_number = serializers.CharField(max_length=32)
    branch = serializers.UUIDField(help_text="Receiving branch UUID")
    lines = GoodsReceiptLineCreateSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_lines(self, lines: list[dict]) -> list[dict]:
        """Ensure at least one line."""
        if not lines:
            raise serializers.ValidationError("At least one receipt line is required.")
        return lines
