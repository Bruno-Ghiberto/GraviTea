"""Serializers for acopio reference data models."""

from rest_framework import serializers

from apps.acopio.models import CampanaConfig, GrainType, MermaTable, ToleranceTable


class GrainTypeSerializer(serializers.ModelSerializer):
    """
    GrainType serializer for API responses.

    Field mapping per REST API Design v1.0 Section 4.1:
    - API field 'codigo' maps to model field 'arca_codigo'
    - API field 'nombre' maps to model field 'name'
    """

    codigo = serializers.IntegerField(source="arca_codigo", read_only=True)
    nombre = serializers.CharField(source="name", read_only=True)

    class Meta:
        model = GrainType
        fields = [
            "id",
            "code",
            "codigo",       # -> arca_codigo
            "nombre",       # -> name
            "humedad_base_pct",
            "hf_secado_pct",
            "manipuleo_fijo_pct",
            "volatil_fijo_pct",
            "grading_system",
            "is_active",
        ]
        read_only_fields = fields


class CampanaConfigSerializer(serializers.ModelSerializer):
    """CampanaConfig serializer -- tenant-scoped, full CRUD."""

    class Meta:
        model = CampanaConfig
        fields = [
            "id",
            "campaign_code",
            "start_date",
            "end_date",
            "is_active",
            "notes",
        ]
        read_only_fields = ["id"]


class ToleranceTableSerializer(serializers.ModelSerializer):
    """ToleranceTable serializer -- read-only, GLOBAL."""

    class Meta:
        model = ToleranceTable
        fields = [
            "id",
            "grain_type",
            "valid_from",
            "valid_to",
            "parameter",
            "tolerance_pct",
            "grado_base",
            "source_resolution",
        ]
        read_only_fields = fields


class MermaTableSerializer(serializers.ModelSerializer):
    """MermaTable serializer -- read-only, GLOBAL."""

    class Meta:
        model = MermaTable
        fields = [
            "id",
            "grain_type",
            "valid_from",
            "valid_to",
            "materias_extranas_from_pct",
            "materias_extranas_to_pct",
            "zarandeo_deduction_pct",
        ]
        read_only_fields = fields
