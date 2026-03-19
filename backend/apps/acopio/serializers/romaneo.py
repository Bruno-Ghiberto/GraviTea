"""Serializers for Romaneo, QualityAnalysis, and MermaCalculation."""

from decimal import Decimal

from rest_framework import serializers

from apps.acopio.models import MermaCalculation, QualityAnalysis, Romaneo


class QualityAnalysisSerializer(serializers.ModelSerializer):
    """Read-only nested serializer for QualityAnalysis."""

    class Meta:
        model = QualityAnalysis
        fields = [
            "id",
            "humedad_pct",
            "materias_extranas_pct",
            "granos_danados_pct",
            "granos_quebrados_pct",
            "peso_hectolitrico_kg",
            "proteina_pct",
            "granos_verdes_pct",
            "granos_ardidos_pct",
            "cuerpos_extranos_pct",
            "analysis_timestamp",
            "sample_reference",
        ]
        read_only_fields = fields


class MermaCalculationSerializer(serializers.ModelSerializer):
    """Read-only nested serializer for MermaCalculation."""

    class Meta:
        model = MermaCalculation
        fields = [
            "id",
            "merma_table_version",
            "peso_neto_bruto_input_kg",
            "hi_input_pct",
            "hf_used_pct",
            "materias_extranas_input_pct",
            "zarandeo_pct",
            "secado_pct",
            "manipuleo_pct",
            "volatil_pct",
            "peso_post_zarandeo_kg",
            "peso_post_secado_kg",
            "peso_post_manipuleo_kg",
            "peso_final_kg",
            "total_merma_kg",
            "total_factor_pct",
            "calculated_at",
            "calculated_by",
        ]
        read_only_fields = fields


class RomaneoSerializer(serializers.ModelSerializer):
    """
    Romaneo list/create serializer.

    For list: returns summary fields.
    For create: accepts writable fields only, auto-sets status=PENDIENTE.
    """

    class Meta:
        model = Romaneo
        fields = [
            "id",
            "romaneo_number",
            "status",
            "grain_type",
            "campaign",
            "branch",
            "ts_entrada",
            "patente_chasis",
            "patente_acoplado",
            "driver_name",
            "driver_dni",
            "peso_bruto_kg",
            "tara_kg",
            "peso_neto_bruto_kg",
            "cpe_numero",
            "ctg_codigo",
            "producer_cuit",
            "origin_locality",
            "operator_id",
            "device_id",
            "grado_asignado",
            "bonificacion_rebaja_pct",
            "peso_neto_conforme_kg",
        ]
        read_only_fields = [
            "id",
            "romaneo_number",
            "status",
            "ts_entrada",
            "peso_neto_bruto_kg",
            "grado_asignado",
            "bonificacion_rebaja_pct",
            "peso_neto_conforme_kg",
        ]


class RomaneoDetailSerializer(serializers.ModelSerializer):
    """
    Romaneo detail serializer with nested QualityAnalysis and MermaCalculation.

    Used for retrieve (GET /romaneos/{id}/).
    """

    quality_analysis = QualityAnalysisSerializer(read_only=True)
    merma_calculation = MermaCalculationSerializer(read_only=True)

    class Meta:
        model = Romaneo
        fields = [
            "id",
            "romaneo_number",
            "status",
            "grain_type",
            "campaign",
            "branch",
            "ts_entrada",
            "ts_pesada_bruta",
            "ts_calado",
            "ts_analisis",
            "ts_descarga",
            "ts_tara",
            "patente_chasis",
            "patente_acoplado",
            "driver_name",
            "driver_dni",
            "peso_bruto_kg",
            "tara_kg",
            "peso_neto_bruto_kg",
            "weighbridge_device",
            "cpe_numero",
            "ctg_codigo",
            "producer_cuit",
            "origin_locality",
            "operator_id",
            "laboratorista_id",
            "device_id",
            "grado_asignado",
            "bonificacion_rebaja_pct",
            "tolerance_table_version",
            "peso_neto_conforme_kg",
            "quality_analysis",
            "merma_calculation",
        ]
        read_only_fields = fields


class PesoBrutoSerializer(serializers.Serializer):
    """Serializer for peso bruto capture action."""

    peso_bruto_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, min_value=Decimal("0.001")
    )


class TaraSerializer(serializers.Serializer):
    """Serializer for tara capture action."""

    tara_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, min_value=Decimal("0.001")
    )


class AnalizarSerializer(serializers.Serializer):
    """Serializer for analizar (quality analysis) action."""

    humedad_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    materias_extranas_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    granos_danados_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    granos_quebrados_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    peso_hectolitrico_kg = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    proteina_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    granos_verdes_pct = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    granos_ardidos_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    cuerpos_extranos_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    sample_reference = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )


class ConfirmarSerializer(serializers.Serializer):
    """Serializer for confirmar action (ANALIZADO -> CONFORME)."""

    grado_asignado = serializers.IntegerField(required=False, allow_null=True)
