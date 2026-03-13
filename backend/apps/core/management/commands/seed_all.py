"""
Unified management command to seed ALL ERP data in dependency order.

Chains: seed_data → seed_inventario → seed_ventas → seed_facturacion

This is the single command to populate the entire ERP for development:
    docker compose exec web python manage.py seed_all
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Seed all ERP data in dependency order: "
        "core → inventory → sales → invoicing → purchases → reports"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding (reverse dependency order)",
        )
        parser.add_argument(
            "--skip",
            nargs="*",
            choices=["core", "inventario", "ventas", "facturacion", "compras", "reportes"],
            default=[],
            help="Skip specific modules (e.g., --skip facturacion ventas)",
        )

    def handle(self, *args, **options):
        clear = options["clear"]
        skip = set(options["skip"])

        modules = [
            ("core", "seed_data", "Core (tenant, branches, roles, users, products)"),
            ("inventario", "seed_inventario", "Inventario (stock movements, price history)"),
            ("ventas", "seed_ventas", "Ventas (customers, sale orders)"),
            ("facturacion", "seed_facturacion", "Facturacion (ARCA credentials, comprobantes)"),
            ("compras", "seed_compras", "Compras (purchase orders, goods receipts)"),
            ("reportes", "seed_reportes", "Reportes (report definitions)"),
        ]

        self.stdout.write(self.style.MIGRATE_HEADING(
            "=== GRAVITEA-ERP Full Seed ==="
        ))

        # If clearing, run in reverse order to respect FK dependencies
        if clear:
            self.stdout.write("\nClearing data in reverse dependency order...")
            for module_key, cmd_name, label in reversed(modules):
                if module_key in skip:
                    continue
                self.stdout.write(f"\n--- Clearing: {label} ---")
                try:
                    call_command(cmd_name, clear=True, verbosity=0)
                except Exception as e:
                    self.stderr.write(
                        self.style.WARNING(f"  Warning clearing {cmd_name}: {e}")
                    )

        # Seed in dependency order
        results = {}
        for module_key, cmd_name, label in modules:
            if module_key in skip:
                self.stdout.write(f"\n--- Skipping: {label} ---")
                results[module_key] = "SKIPPED"
                continue

            self.stdout.write(f"\n--- Seeding: {label} ---")
            try:
                call_command(cmd_name, verbosity=1)
                results[module_key] = "OK"
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"  FAILED: {cmd_name}: {e}")
                )
                results[module_key] = f"FAILED: {e}"

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== Seed Summary ==="
        ))
        for module_key, cmd_name, label in modules:
            status = results.get(module_key, "NOT RUN")
            if status == "OK":
                self.stdout.write(self.style.SUCCESS(f"  ✓ {label}"))
            elif status == "SKIPPED":
                self.stdout.write(f"  - {label} (skipped)")
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ {label}: {status}"))

        self.stdout.write(self.style.SUCCESS(
            "\nDone! Login with: admin@gravitea-demo.com / admin123"
        ))
