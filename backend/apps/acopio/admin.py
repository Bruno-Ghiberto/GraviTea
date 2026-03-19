"""Admin registration for acopio models."""

from django.contrib import admin

from .models import CampanaConfig, GrainType, MermaTable, ToleranceTable


@admin.register(GrainType)
class GrainTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "arca_codigo", "name", "grading_system", "is_active"]
    list_filter = ["grading_system", "is_active"]
    search_fields = ["code", "name"]


@admin.register(CampanaConfig)
class CampanaConfigAdmin(admin.ModelAdmin):
    list_display = ["campaign_code", "tenant", "start_date", "end_date", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["campaign_code"]


@admin.register(ToleranceTable)
class ToleranceTableAdmin(admin.ModelAdmin):
    list_display = ["grain_type", "parameter", "grado_base", "tolerance_pct", "valid_from", "valid_to"]
    list_filter = ["parameter", "valid_to"]
    search_fields = ["grain_type__code", "parameter"]


@admin.register(MermaTable)
class MermaTableAdmin(admin.ModelAdmin):
    list_display = ["grain_type", "materias_extranas_from_pct", "materias_extranas_to_pct", "zarandeo_deduction_pct", "valid_from", "valid_to"]
    list_filter = ["valid_to"]
    search_fields = ["grain_type__code"]
