"""Ventas admin configuration for Gravitea ERP."""

from django.contrib import admin

from .models import Customer, SaleOrder, SaleOrderItem


class SaleOrderItemInline(admin.TabularInline):
    """Inline display for sale order items."""

    model = SaleOrderItem
    extra = 0
    readonly_fields = ["subtotal", "iva_amount", "created_at"]
    fields = [
        "product",
        "quantity",
        "unit_price",
        "subtotal",
        "tax_rate",
        "iva_amount",
    ]


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Customer admin with search and filters."""

    list_display = ["cuit", "razon_social", "condicion_iva", "is_active"]
    list_filter = ["is_active", "condicion_iva"]
    search_fields = ["cuit", "razon_social"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    """SaleOrder admin with inline items."""

    list_display = ["id", "customer", "status", "total_amount", "sale_date"]
    list_filter = ["status"]
    search_fields = ["customer__razon_social", "customer__cuit"]
    readonly_fields = [
        "subtotal",
        "total_iva",
        "total_amount",
        "confirmed_at",
        "invoiced_at",
        "confirmed_by",
        "created_at",
        "updated_at",
    ]
    inlines = [SaleOrderItemInline]
