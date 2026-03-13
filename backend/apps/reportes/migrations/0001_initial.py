# Generated migration for reportes module
# Models: ReportDefinition, SavedReport, ExportJob

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0003_businesstemplate_tenantfielddefinition_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportDefinition",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_definitions",
                        to="core.tenant",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=200,
                        help_text="Human-readable name for the report definition",
                    ),
                ),
                (
                    "report_type",
                    models.CharField(
                        max_length=30,
                        choices=[
                            ("sales", "Ventas"),
                            ("stock", "Stock"),
                            ("purchases", "Compras"),
                            ("fiscal", "Fiscal"),
                            ("accounting_export", "Exportación Contable"),
                        ],
                        db_index=True,
                        help_text="Type of report: sales, stock, purchases, fiscal, accounting_export",
                    ),
                ),
                (
                    "parameters",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Report-specific configuration parameters",
                    ),
                ),
                (
                    "filters",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Filter criteria applied during report generation",
                    ),
                ),
                (
                    "output_format",
                    models.CharField(
                        max_length=10,
                        choices=[
                            ("PDF", "PDF"),
                            ("EXCEL", "Excel"),
                            ("CSV", "CSV"),
                        ],
                        default="CSV",
                        help_text="Output format: PDF, EXCEL, or CSV",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        db_index=True,
                        help_text="Whether this report definition is available for use",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Definición de Reporte",
                "verbose_name_plural": "Definiciones de Reporte",
                "db_table": "reportes_reportdefinition",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="SavedReport",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_reports",
                        to="core.tenant",
                    ),
                ),
                (
                    "report_definition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="saved_reports",
                        to="gravitea_reportes.reportdefinition",
                        help_text="The definition used to generate this report",
                    ),
                ),
                (
                    "generated_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this report execution was initiated",
                    ),
                ),
                (
                    "result_metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Execution metadata: row count, execution time, etc.",
                    ),
                ),
                (
                    "file_reference",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        null=True,
                        help_text="Path or blob storage key for the generated report file",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("PENDING", "Pendiente"),
                            ("COMPLETED", "Completado"),
                            ("FAILED", "Fallido"),
                        ],
                        db_index=True,
                        default="PENDING",
                        help_text="Current status: PENDING, COMPLETED, or FAILED",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reporte Guardado",
                "verbose_name_plural": "Reportes Guardados",
                "db_table": "reportes_savedreport",
                "ordering": ["-generated_at"],
            },
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="export_jobs",
                        to="core.tenant",
                    ),
                ),
                (
                    "saved_report",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="export_jobs",
                        to="gravitea_reportes.savedreport",
                        help_text="The saved report being exported",
                    ),
                ),
                (
                    "export_format",
                    models.CharField(
                        max_length=10,
                        choices=[
                            ("PDF", "PDF"),
                            ("EXCEL", "Excel"),
                            ("CSV", "CSV"),
                        ],
                        help_text="Output format for this export job",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("PENDING", "Pendiente"),
                            ("PROCESSING", "Procesando"),
                            ("COMPLETED", "Completado"),
                            ("FAILED", "Fallido"),
                        ],
                        db_index=True,
                        default="PENDING",
                        help_text="Current status: PENDING, PROCESSING, COMPLETED, or FAILED",
                    ),
                ),
                (
                    "file_path",
                    models.CharField(
                        blank=True,
                        max_length=500,
                        null=True,
                        help_text="Path to the generated export file",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "completed_at",
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        help_text="Timestamp when the export finished (success or failure)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Trabajo de Exportación",
                "verbose_name_plural": "Trabajos de Exportación",
                "db_table": "reportes_exportjob",
                "ordering": ["-created_at"],
            },
        ),
        # Indexes for ReportDefinition
        migrations.AddIndex(
            model_name="reportdefinition",
            index=models.Index(
                fields=["tenant_id", "report_type"],
                name="idx_reportdef_tenant_type",
            ),
        ),
        migrations.AddIndex(
            model_name="reportdefinition",
            index=models.Index(
                fields=["tenant_id", "is_active"],
                name="idx_reportdef_tenant_active",
            ),
        ),
        # Indexes for SavedReport
        migrations.AddIndex(
            model_name="savedreport",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="idx_savedreport_tenant_status",
            ),
        ),
        migrations.AddIndex(
            model_name="savedreport",
            index=models.Index(
                fields=["tenant_id", "report_definition_id"],
                name="idx_savedreport_tenant_defn",
            ),
        ),
        # Indexes for ExportJob
        migrations.AddIndex(
            model_name="exportjob",
            index=models.Index(
                fields=["tenant_id", "status"],
                name="idx_exportjob_tenant_status",
            ),
        ),
    ]
