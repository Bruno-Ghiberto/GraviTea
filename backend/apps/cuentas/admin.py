"""Admin registration for cuentas models."""

from django.contrib import admin

from .models import AccountMovement, ProducerAccount


@admin.register(ProducerAccount)
class ProducerAccountAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "branch",
        "grain_type",
        "campaign",
        "grain_balance_kg",
        "ars_balance",
        "usd_balance",
        "is_active",
    ]
    list_filter = ["is_active", "grain_type", "campaign"]
    search_fields = ["producer_cuit_hash"]


@admin.register(AccountMovement)
class AccountMovementAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "producer_account",
        "movement_type",
        "quantity_kg",
        "movement_at",
        "created_by",
    ]
    list_filter = ["movement_type"]
    readonly_fields = [
        f.name
        for f in AccountMovement._meta.get_fields()
        if hasattr(f, "name")
    ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
