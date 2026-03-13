"""Compras admin configuration."""

from django.contrib import admin

from .models import GoodsReceipt, GoodsReceiptLine, PurchaseOrder, PurchaseOrderItem, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "lead_time_days", "tenant", "created_at")
    list_filter = ("is_active", "tenant")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ("id", "received_quantity")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "status", "order_date", "tenant")
    list_filter = ("status", "tenant")
    search_fields = ("order_number",)
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [PurchaseOrderItemInline]


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    readonly_fields = ("id",)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "purchase_order", "receipt_date", "tenant")
    list_filter = ("tenant",)
    search_fields = ("receipt_number",)
    readonly_fields = ("id", "receipt_date")
    inlines = [GoodsReceiptLineInline]
