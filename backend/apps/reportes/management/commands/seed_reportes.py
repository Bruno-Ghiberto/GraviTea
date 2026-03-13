"""
Management command to seed reportes (reports) data for development.

Creates sample report definitions for sales, stock, and purchases types.
Requires seed_data to have run first (needs tenant).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Tenant
from apps.reportes.models import ReportDefinition


REPORT_DEFINITIONS = [
    {
        "name": "Resumen de Ventas Mensual",
        "report_type": "sales",
        "parameters": {"period": "monthly", "group_by": "product_category"},
        "filters": {"status": "COMPLETED"},
        "output_format": "PDF",
    },
    {
        "name": "Ventas por Vendedor",
        "report_type": "sales",
        "parameters": {"period": "weekly", "group_by": "salesperson"},
        "filters": {},
        "output_format": "EXCEL",
    },
    {
        "name": "Niveles de Stock Actual",
        "report_type": "stock",
        "parameters": {"include_zero_stock": False, "sort_by": "quantity_asc"},
        "filters": {},
        "output_format": "CSV",
    },
    {
        "name": "Productos Bajo Stock Minimo",
        "report_type": "stock",
        "parameters": {"below_minimum": True},
        "filters": {},
        "output_format": "PDF",
    },
    {
        "name": "Historial de Compras por Proveedor",
        "report_type": "purchases",
        "parameters": {"period": "quarterly", "group_by": "supplier"},
        "filters": {"status": "RECEIVED"},
        "output_format": "EXCEL",
    },
    {
        "name": "Reporte Fiscal IVA",
        "report_type": "fiscal",
        "parameters": {"tax_type": "IVA", "period": "monthly"},
        "filters": {},
        "output_format": "PDF",
    },
]


class Command(BaseCommand):
    help = "Seed reportes data: report definitions"

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(name="Gravitea Demo").first()
        if not tenant:
            self.stderr.write(self.style.ERROR(
                "No 'Gravitea Demo' tenant found. Run seed_data first."
            ))
            return

        set_current_tenant_id(tenant.id)

        with transaction.atomic():
            self._seed_report_definitions(tenant)

        self.stdout.write(self.style.SUCCESS("Reportes seed data created."))

    def _seed_report_definitions(self, tenant):
        created_count = 0
        for defn in REPORT_DEFINITIONS:
            _, created = ReportDefinition.objects.get_or_create(
                tenant=tenant,
                name=defn["name"],
                defaults={
                    "report_type": defn["report_type"],
                    "parameters": defn["parameters"],
                    "filters": defn["filters"],
                    "output_format": defn["output_format"],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(f"  Report definitions: {created_count} created, "
                          f"{len(REPORT_DEFINITIONS) - created_count} existing")
