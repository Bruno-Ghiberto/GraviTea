"""Admin registration for acopio models."""

from django.contrib import admin

from .models import (
    CampanaConfig,
    GrainType,
    MermaCalculation,
    MermaTable,
    QualityAnalysis,
    Romaneo,
    ToleranceTable,
)


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


@admin.register(Romaneo)
class RomaneoAdmin(admin.ModelAdmin):
    list_display = ["romaneo_number", "status", "grain_type", "branch", "ts_entrada", "producer_cuit"]
    list_filter = ["status", "grain_type", "branch"]
    search_fields = ["romaneo_number", "cpe_numero", "patente_chasis", "producer_cuit"]
    readonly_fields = ["romaneo_number", "ts_entrada", "peso_neto_bruto_kg", "peso_neto_conforme_kg"]


@admin.register(QualityAnalysis)
class QualityAnalysisAdmin(admin.ModelAdmin):
    list_display = ["romaneo", "humedad_pct", "materias_extranas_pct", "analysis_timestamp"]
    list_filter = ["analysis_timestamp"]
    search_fields = ["romaneo__romaneo_number"]
    readonly_fields = ["analysis_timestamp"]


@admin.register(MermaCalculation)
class MermaCalculationAdmin(admin.ModelAdmin):
    list_display = ["romaneo", "peso_final_kg", "total_merma_kg", "total_factor_pct", "calculated_at"]
    list_filter = ["calculated_at"]
    search_fields = ["romaneo__romaneo_number"]
    readonly_fields = [
        "romaneo", "merma_table_version", "peso_neto_bruto_input_kg",
        "hi_input_pct", "hf_used_pct", "materias_extranas_input_pct",
        "zarandeo_pct", "secado_pct", "manipuleo_pct", "volatil_pct",
        "peso_post_zarandeo_kg", "peso_post_secado_kg", "peso_post_manipuleo_kg",
        "peso_final_kg", "total_merma_kg", "total_factor_pct",
        "calculated_at", "calculated_by",
    ]
