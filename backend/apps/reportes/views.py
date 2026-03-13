"""
Reportes views for Gravitea ERP.

Provides ViewSets for ReportDefinition, SavedReport, and ExportJob
with tenant isolation via TenantBoundManager and cursor pagination.
"""

from __future__ import annotations

import logging

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.auth.permissions import HasModulePermission
from apps.core.pagination import StandardCursorPagination

from .models import ExportJob, ReportDefinition, SavedReport


class SavedReportPagination(StandardCursorPagination):
    """Cursor pagination for SavedReport (uses generated_at instead of created_at)."""

    ordering = "-generated_at"
from .serializers import (
    ExportJobSerializer,
    ReportDefinitionSerializer,
    SavedReportSerializer,
)

logger = logging.getLogger("reportes")


# ============================================================
# ReportDefinition
# ============================================================


class ReportDefinitionViewSet(viewsets.ModelViewSet):
    """
    ReportDefinition CRUD viewset.

    Endpoints:
        GET    /api/v1/reportes/definitions/        - List definitions
        POST   /api/v1/reportes/definitions/        - Create definition
        GET    /api/v1/reportes/definitions/{id}/    - Get definition detail
        PUT    /api/v1/reportes/definitions/{id}/    - Full update
        PATCH  /api/v1/reportes/definitions/{id}/    - Partial update
        DELETE /api/v1/reportes/definitions/{id}/    - Delete definition
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "reports"
    pagination_class = StandardCursorPagination
    serializer_class = ReportDefinitionSerializer

    def get_queryset(self) -> QuerySet[ReportDefinition]:
        """Return report definitions for current tenant with optional filters."""
        qs = ReportDefinition.objects.all()

        params = self.request.query_params

        report_type = params.get("report_type")
        if report_type is not None:
            qs = qs.filter(report_type=report_type)

        is_active = params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs


# ============================================================
# SavedReport
# ============================================================


class SavedReportViewSet(viewsets.ModelViewSet):
    """
    SavedReport viewset.

    Endpoints:
        GET    /api/v1/reportes/saved-reports/        - List saved reports
        POST   /api/v1/reportes/saved-reports/        - Create saved report
        GET    /api/v1/reportes/saved-reports/{id}/    - Get saved report detail
        DELETE /api/v1/reportes/saved-reports/{id}/    - Delete saved report
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "reports"
    pagination_class = SavedReportPagination
    serializer_class = SavedReportSerializer
    # No PUT/PATCH — SavedReports are not editable after creation
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[SavedReport]:
        """Return saved reports for current tenant with optional filters."""
        qs = SavedReport.objects.select_related("report_definition").all()

        params = self.request.query_params

        status_param = params.get("status")
        if status_param is not None:
            qs = qs.filter(status=status_param)

        report_definition_id = params.get("report_definition_id")
        if report_definition_id is not None:
            qs = qs.filter(report_definition_id=report_definition_id)

        return qs


# ============================================================
# ExportJob
# ============================================================


class ExportJobViewSet(viewsets.ModelViewSet):
    """
    ExportJob viewset.

    Endpoints:
        GET    /api/v1/reportes/export-jobs/        - List export jobs
        POST   /api/v1/reportes/export-jobs/        - Create export job
        GET    /api/v1/reportes/export-jobs/{id}/    - Get export job detail
    """

    permission_classes = [IsAuthenticated, HasModulePermission]
    module_name = "reports"
    action_permissions = {
        "create": "reports.export",
    }
    pagination_class = StandardCursorPagination
    serializer_class = ExportJobSerializer
    # No PUT/PATCH/DELETE — ExportJobs are managed by the export worker
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> QuerySet[ExportJob]:
        """Return export jobs for current tenant with optional filters."""
        qs = ExportJob.objects.select_related("saved_report").all()

        params = self.request.query_params

        status_param = params.get("status")
        if status_param is not None:
            qs = qs.filter(status=status_param)

        return qs
