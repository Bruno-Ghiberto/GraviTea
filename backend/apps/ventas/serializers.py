"""
Ventas serializers for Gravitea ERP.

Provides serializers for sales entities: Customer, SaleOrder,
SaleOrderItem with lifecycle management and invoice integration.
"""

from __future__ import annotations

import re
from decimal import Decimal

from django.db import IntegrityError
from rest_framework import serializers

from apps.core.serializers.customization import CustomFieldsMixin

from .models import Customer, SaleOrder, SaleOrderItem, SaleOrderStatus


# ============================================================
# CUIT Validation
# ============================================================

_CUIT_PATTERN = re.compile(r"^\d{11}$")
_CUIT_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _validate_cuit_serializer(value: str) -> str:
    """Validate CUIT format (11 digits) and check digit."""
    if not _CUIT_PATTERN.match(value):
        raise serializers.ValidationError(
            "CUIT must be exactly 11 digits with no hyphens."
        )
    digits = [int(d) for d in value]
    total = sum(d * w for d, w in zip(digits[:10], _CUIT_WEIGHTS))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        check = 9
    if digits[10] != check:
        raise serializers.ValidationError("Invalid CUIT check digit.")
    return value


# ============================================================
# Customer
# ============================================================


class CustomerSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """
    Customer serializer for CRUD operations.

    Validates CUIT with Modulo-11. Provides condicion_iva_display
    as read-only computed field.
    """

    entity_type = "customer"

    condicion_iva_display = serializers.CharField(
        source="get_condicion_iva_display",
        read_only=True,
    )

    class Meta:
        model = Customer
        fields = [
            "id",
            "cuit",
            "doc_tipo",
            "condicion_iva",
            "condicion_iva_display",
            "razon_social",
            "domicilio",
            "email",
            "telefono",
            "custom_data",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_cuit(self, value: str) -> str:
        """Validate CUIT format and check digit."""
        return _validate_cuit_serializer(value)

    def validate(self, attrs: dict) -> dict:
        """Check for duplicate CUIT within same tenant + custom_data via mixin."""
        request = self.context.get("request")
        cuit = attrs.get("cuit")
        if request and cuit and hasattr(request, "user"):
            tenant = request.user.tenant
            qs = Customer.objects.filter(tenant=tenant, cuit=cuit)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"cuit": "A customer with this CUIT already exists."}
                )
        return super().validate(attrs)

    def create(self, validated_data: dict) -> Customer:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        try:
            return super().create(validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"cuit": "A customer with this CUIT already exists."}
            )


# ============================================================
# SaleOrderItem
# ============================================================


class SaleOrderItemSerializer(serializers.ModelSerializer):
    """
    SaleOrderItem serializer with auto-calculated fields.

    Create accepts product_id (UUID), quantity, unit_price.
    subtotal and iva_amount are read-only (auto-calculated by model).
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_sku = serializers.CharField(
        source="product.sku",
        read_only=True,
    )

    class Meta:
        model = SaleOrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "quantity",
            "unit_price",
            "subtotal",
            "tax_rate",
            "iva_amount",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "subtotal",
            "iva_amount",
            "created_at",
        ]


# ============================================================
# SaleOrder
# ============================================================


class SaleOrderSerializer(CustomFieldsMixin, serializers.ModelSerializer):
    """
    SaleOrder serializer for list/create/update.

    Create accepts customer_id (UUID), branch_id (UUID).
    Status, totals, confirmed_by are read-only.
    Includes comprobante_id from reverse OneToOne accessor.
    """

    entity_type = "sale_order"

    customer_name = serializers.CharField(
        source="customer.razon_social",
        read_only=True,
    )
    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    comprobante_id = serializers.SerializerMethodField()

    class Meta:
        model = SaleOrder
        fields = [
            "id",
            "customer",
            "customer_name",
            "branch",
            "branch_name",
            "status",
            "status_display",
            "subtotal",
            "total_iva",
            "total_amount",
            "sale_date",
            "confirmed_at",
            "invoiced_at",
            "confirmed_by",
            "comprobante_id",
            "custom_data",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "subtotal",
            "total_iva",
            "total_amount",
            "sale_date",
            "confirmed_at",
            "invoiced_at",
            "confirmed_by",
            "created_at",
            "updated_at",
        ]

    def get_comprobante_id(self, obj: SaleOrder) -> str | None:
        """Return linked comprobante ID via reverse OneToOne, or null."""
        if hasattr(obj, "comprobante_direct"):
            return str(obj.comprobante_direct.id)
        return None

    def create(self, validated_data: dict) -> SaleOrder:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


# ============================================================
# SaleOrderDetail (extended with nested items)
# ============================================================


class SaleOrderDetailSerializer(SaleOrderSerializer):
    """
    Extended SaleOrder serializer with nested items list.

    Used for retrieve action to show full order details.
    """

    items = SaleOrderItemSerializer(many=True, read_only=True)

    class Meta(SaleOrderSerializer.Meta):
        fields = SaleOrderSerializer.Meta.fields + [
            "items",
        ]
