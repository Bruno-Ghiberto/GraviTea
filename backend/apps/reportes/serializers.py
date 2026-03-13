"""
Reportes serializers for Gravitea ERP.

Provides serializers for the reporting infrastructure:
ReportDefinitionSerializer, SavedReportSerializer, ExportJobSerializer.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import ExportJob, ReportDefinition, SavedReport


# ============================================================
# ReportDefinition
# ============================================================


class ReportDefinitionSerializer(serializers.ModelSerializer):
    """
    Serializer for ReportDefinition CRUD operations.

    Tenant is injected from request context on create.
    """

    class Meta:
        model = ReportDefinition
        fields = [
            "id",
            "name",
            "report_type",
            "parameters",
            "filters",
            "output_format",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data: dict) -> ReportDefinition:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


# ============================================================
# SavedReport
# ============================================================


class SavedReportSerializer(serializers.ModelSerializer):
    """
    Serializer for SavedReport CRUD operations.

    report_definition_id is a writable UUID field.
    generated_at is set automatically (auto_now_add).
    """

    # Expose as UUID field for create (contract requires report_definition_id)
    report_definition_id = serializers.UUIDField()

    class Meta:
        model = SavedReport
        fields = [
            "id",
            "report_definition_id",
            "generated_at",
            "result_metadata",
            "file_reference",
            "status",
        ]
        read_only_fields = ["id", "generated_at"]

    def validate_report_definition_id(self, value):
        """Ensure report_definition belongs to current tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if not ReportDefinition.objects.filter(pk=value, tenant=tenant).exists():
                raise serializers.ValidationError(
                    "Report definition not found or does not belong to this tenant."
                )
        return value

    def create(self, validated_data: dict) -> SavedReport:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


# ============================================================
# ExportJob
# ============================================================


class ExportJobSerializer(serializers.ModelSerializer):
    """
    Serializer for ExportJob CRUD operations.

    saved_report_id is a writable UUID field.
    status defaults to PENDING on create.
    """

    # Expose as UUID field for create (contract requires saved_report_id)
    saved_report_id = serializers.UUIDField()

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "saved_report_id",
            "export_format",
            "status",
            "file_path",
            "created_at",
            "completed_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_saved_report_id(self, value):
        """Ensure saved_report belongs to current tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            if not SavedReport.objects.filter(pk=value, tenant=tenant).exists():
                raise serializers.ValidationError(
                    "Saved report not found or does not belong to this tenant."
                )
        return value

    def create(self, validated_data: dict) -> ExportJob:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)
