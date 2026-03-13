from django.contrib import admin

from apps.core.models import BusinessTemplate, TenantFieldDefinition, TenantModuleConfig


@admin.register(TenantFieldDefinition)
class TenantFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("field_key", "label", "entity_type", "field_type", "section", "active")
    list_filter = ("entity_type", "field_type", "section", "active")
    search_fields = ("field_key", "label")


@admin.register(TenantModuleConfig)
class TenantModuleConfigAdmin(admin.ModelAdmin):
    list_display = ("tenant", "module", "enabled")
    list_filter = ("module", "enabled")


@admin.register(BusinessTemplate)
class BusinessTemplateAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    search_fields = ("slug", "name")
