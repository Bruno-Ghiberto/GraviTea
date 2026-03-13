"""
Reportes (Reports) models for Gravitea ERP.

Defines ReportDefinition, SavedReport, and ExportJob for the
reporting infrastructure skeleton. No report generation logic —
this module provides the data layer for future report generators.
"""

import uuid

from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


# ============================================================
# ReportDefinition (T040)
# ============================================================


class ReportType(models.TextChoices):
    SALES = "sales", "Ventas"
    STOCK = "stock", "Stock"
    PURCHASES = "purchases", "Compras"
    FISCAL = "fiscal", "Fiscal"
    ACCOUNTING_EXPORT = "accounting_export", "Exportación Contable"


class OutputFormat(models.TextChoices):
    PDF = "PDF", "PDF"
    EXCEL = "EXCEL", "Excel"
    CSV = "CSV", "CSV"


class ReportDefinition(TenantBoundModel):
    """
    Template that defines how a report should be generated.

    Stores report type, parameters, filters and output format.
    Report generation logic is outside this module's scope.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="report_definitions",
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable name for the report definition",
    )
    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        db_index=True,
        help_text="Type of report: sales, stock, purchases, fiscal, accounting_export",
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Report-specific configuration parameters",
    )
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Filter criteria applied during report generation",
    )
    output_format = models.CharField(
        max_length=10,
        choices=OutputFormat.choices,
        default=OutputFormat.CSV,
        help_text="Output format: PDF, EXCEL, or CSV",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this report definition is available for use",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "reportes_reportdefinition"
        ordering = ["-created_at"]
        verbose_name = "Definición de Reporte"
        verbose_name_plural = "Definiciones de Reporte"
        indexes = [
            models.Index(
                fields=["tenant_id", "report_type"],
                name="idx_reportdef_tenant_type",
            ),
            models.Index(
                fields=["tenant_id", "is_active"],
                name="idx_reportdef_tenant_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_report_type_display()})"


# ============================================================
# SavedReport (T041)
# ============================================================


class SavedReportStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    COMPLETED = "COMPLETED", "Completado"
    FAILED = "FAILED", "Fallido"


class SavedReport(TenantBoundModel):
    """
    A saved instance of an executed report.

    Records execution metadata, result reference, and status.
    Linked to the ReportDefinition that was used to generate it.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="saved_reports",
    )
    report_definition = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name="saved_reports",
        help_text="The definition used to generate this report",
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this report execution was initiated",
    )
    result_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Execution metadata: row count, execution time, etc.",
    )
    file_reference = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Path or blob storage key for the generated report file",
    )
    status = models.CharField(
        max_length=20,
        choices=SavedReportStatus.choices,
        default=SavedReportStatus.PENDING,
        db_index=True,
        help_text="Current status: PENDING, COMPLETED, or FAILED",
    )

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "reportes_savedreport"
        ordering = ["-generated_at"]
        verbose_name = "Reporte Guardado"
        verbose_name_plural = "Reportes Guardados"
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_savedreport_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "report_definition_id"],
                name="idx_savedreport_tenant_defn",
            ),
        ]

    def __str__(self) -> str:
        return f"SavedReport {str(self.id)[:8]} [{self.status}]"


# ============================================================
# ExportJob (T042)
# ============================================================


class ExportJobStatus(models.TextChoices):
    PENDING = "PENDING", "Pendiente"
    PROCESSING = "PROCESSING", "Procesando"
    COMPLETED = "COMPLETED", "Completado"
    FAILED = "FAILED", "Fallido"


class ExportJob(TenantBoundModel):
    """
    An export job that converts a SavedReport into a specific file format.

    Tracks progress from submission through completion or failure.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="export_jobs",
    )
    saved_report = models.ForeignKey(
        SavedReport,
        on_delete=models.CASCADE,
        related_name="export_jobs",
        help_text="The saved report being exported",
    )
    export_format = models.CharField(
        max_length=10,
        choices=OutputFormat.choices,
        help_text="Output format for this export job",
    )
    status = models.CharField(
        max_length=20,
        choices=ExportJobStatus.choices,
        default=ExportJobStatus.PENDING,
        db_index=True,
        help_text="Current status: PENDING, PROCESSING, COMPLETED, or FAILED",
    )
    file_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Path to the generated export file",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the export finished (success or failure)",
    )

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "reportes_exportjob"
        ordering = ["-created_at"]
        verbose_name = "Trabajo de Exportación"
        verbose_name_plural = "Trabajos de Exportación"
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_exportjob_tenant_status",
            ),
        ]

    def __str__(self) -> str:
        return f"ExportJob {str(self.id)[:8]} [{self.status}] {self.export_format}"
