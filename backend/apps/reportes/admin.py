"""Reportes admin configuration."""

from django.contrib import admin

from .models import ExportJob, ReportDefinition, SavedReport


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "output_format", "is_active", "tenant", "created_at")
    list_filter = ("report_type", "is_active", "tenant")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(SavedReport)
class SavedReportAdmin(admin.ModelAdmin):
    list_display = ("id", "report_definition", "status", "generated_at", "tenant")
    list_filter = ("status", "tenant")
    readonly_fields = ("id", "generated_at")


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "saved_report", "export_format", "status", "created_at", "tenant")
    list_filter = ("status", "export_format", "tenant")
    readonly_fields = ("id", "created_at", "completed_at")
