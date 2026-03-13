"""
Management command to seed inventario (inventory) data for development.

Creates sample categories, suppliers, products, a default price list,
price history entries, and initial stock via PURCHASE movements.
Requires a tenant and branch to exist (run createsuperuser first).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Branch, Tenant
from apps.inventario.models import (
    PriceList,
    Product,
    ProductCategory,
    ProductCostHistory,
    ProductPriceHistory,
    StockMovement,
    Supplier,
)


CATEGORIES = [
    "Herramientas Electricas",
    "Herramientas Manuales",
    "Maquinaria de Jardin",
    "Soldadura y Corte",
    "Insumos y Abrasivos",
    "Seguridad Industrial (EPP)",
    "Fijaciones y Ferreteria",
    "Quimicos y Varios",
]

SUPPLIER_DATA = [
    {
        "name": "DeWalt Argentina",
        "tax_id": "30712345670",
        "email": "ventas@dewalt.com.ar",
        "contact_info": "Tel: +54 11 4555-1000",
        "address": "Av. del Libertador 6350, CABA",
        "lead_time_days": 7,
    },
    {
        "name": "Stanley Black & Decker",
        "tax_id": "30698765435",
        "email": "distribuidores@stanley.com.ar",
        "contact_info": "Tel: +54 11 4555-2000",
        "address": "Panamericana Km 35, Pilar",
        "lead_time_days": 5,
    },
    {
        "name": "Makita Argentina",
        "tax_id": "30711122331",
        "email": "comercial@makita.com.ar",
        "contact_info": "Tel: +54 11 4555-3000",
        "address": "Av. Rivadavia 8200, CABA",
        "lead_time_days": 10,
    },
    {
        "name": "Bremen Herramientas",
        "tax_id": "30709988774",
        "email": "pedidos@bremen.com.ar",
        "contact_info": "Tel: +54 341 4555-4000",
        "address": "Zona Industrial, Rosario",
        "lead_time_days": 3,
    },
    {
        "name": "Lusqtoff S.A.",
        "tax_id": "30714455668",
        "email": "info@lusqtoff.com.ar",
        "contact_info": "Tel: +54 11 4555-5000",
        "address": "Ruta 8 Km 42, San Martin",
        "lead_time_days": 4,
    },
]

# Products: (sku, name, category_index, supplier_index, cost, price, tax_rate, min_stock, initial_qty)
PRODUCT_DATA = [
    # Herramientas Electricas (cat 0)
    ("HE-001", "Taladro percutor 13mm DeWalt DWD024", 0, 0, "28500.00", "42750.00", "21.00", 5, 15),
    ("HE-002", "Atornillador impacto 18V Makita DTD152", 0, 2, "45000.00", "67500.00", "21.00", 3, 10),
    ("HE-003", "Amoladora angular 115mm Stanley STGS7115", 0, 1, "18500.00", "27750.00", "21.00", 8, 20),
    ("HE-004", "Sierra circular 7-1/4 DeWalt DWE560", 0, 0, "52000.00", "78000.00", "21.00", 3, 8),
    # Herramientas Manuales (cat 1)
    ("HM-001", "Juego llaves combinadas 6-32mm Bremen 6580", 1, 3, "12500.00", "18750.00", "21.00", 10, 25),
    ("HM-002", "Juego destornilladores Phillips/Planos Stanley 8pz", 1, 1, "6800.00", "10200.00", "21.00", 15, 30),
    ("HM-003", "Pinza universal 8in Bremen 6020", 1, 3, "4200.00", "6300.00", "21.00", 12, 35),
    ("HM-004", "Cinta metrica 5m Stanley STHT30615", 1, 1, "3500.00", "5250.00", "21.00", 20, 50),
    # Maquinaria de Jardin (cat 2)
    ("MJ-001", "Cortadora cesped a explosion 5.5HP", 2, 4, "185000.00", "277500.00", "21.00", 2, 5),
    ("MJ-002", "Motosierra nafta 18in Lusqtoff", 2, 4, "125000.00", "187500.00", "21.00", 2, 6),
    ("MJ-003", "Desmalezadora 52cc Lusqtoff", 2, 4, "78000.00", "117000.00", "21.00", 3, 8),
    # Soldadura y Corte (cat 3)
    ("SC-001", "Soldadora Inverter 200A Lusqtoff", 3, 4, "95000.00", "142500.00", "21.00", 3, 7),
    ("SC-002", "Mascara soldar fotosensible", 3, 4, "22000.00", "33000.00", "21.00", 5, 12),
    ("SC-003", "Electrodos 6013 2.5mm x 5kg", 3, 4, "8500.00", "12750.00", "21.00", 10, 30),
    # Insumos y Abrasivos (cat 4)
    ("IA-001", "Disco corte metal 115mm x 25u", 4, 3, "4500.00", "6750.00", "21.00", 20, 50),
    ("IA-002", "Disco diamantado 115mm concreto", 4, 3, "6800.00", "10200.00", "21.00", 10, 25),
    ("IA-003", "Mechas HSS 1-10mm juego 19pz", 4, 3, "7200.00", "10800.00", "21.00", 10, 20),
    # Seguridad Industrial EPP (cat 5)
    ("EP-001", "Zapatos seguridad punta acero T42", 5, 3, "25000.00", "37500.00", "21.00", 8, 20),
    ("EP-002", "Guantes nitrilo caja x 100u", 5, 3, "4800.00", "7200.00", "21.00", 15, 40),
    ("EP-003", "Anteojos seguridad transparentes", 5, 3, "2200.00", "3300.00", "21.00", 20, 50),
    # Fijaciones y Ferreteria (cat 6)
    ("FF-001", "Tornillos autoperforantes T2 x 500u", 6, 3, "3800.00", "5700.00", "21.00", 25, 60),
    ("FF-002", "Tarugos nylon 8mm x 1000u", 6, 3, "2500.00", "3750.00", "21.00", 30, 80),
    ("FF-003", "Bulones hexagonales M8x50 x 100u", 6, 3, "5200.00", "7800.00", "21.00", 15, 40),
    # Quimicos y Varios (cat 7)
    ("QV-001", "Silicona neutra transparente 280ml", 7, 3, "2800.00", "4200.00", "21.00", 20, 50),
    ("QV-002", "Espuma poliuretano expandido 750ml", 7, 3, "3500.00", "5250.00", "21.00", 15, 40),
    ("QV-003", "Aceite lubricante tipo WD-40 432ml", 7, 3, "4200.00", "6300.00", "21.00", 15, 35),
]


class Command(BaseCommand):
    help = "Seed inventario data (categories, suppliers, products, stock) for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing inventario data before seeding",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(is_active=True).first()
        if not tenant:
            self.stderr.write(
                self.style.ERROR(
                    "No active tenant found. Run 'createsuperuser' first."
                )
            )
            return

        set_current_tenant_id(tenant.id)
        branch = Branch.objects.filter(tenant=tenant).first()
        if not branch:
            self.stderr.write(
                self.style.ERROR(
                    "No branch found for tenant. Run 'createsuperuser' first."
                )
            )
            return

        self.stdout.write(
            f"Seeding inventario for tenant '{tenant.name}', "
            f"branch '{branch.name}'"
        )

        with transaction.atomic():
            if options["clear"]:
                self._clear_data(tenant)

            categories = self._create_categories(tenant)
            suppliers = self._create_suppliers(tenant)
            price_list = self._create_price_list(tenant)
            products = self._create_products(tenant, categories, suppliers)
            movements = self._create_stock_movements(tenant, branch, products)
            self._create_price_history(products, price_list)
            cost_entries = self._create_cost_history(products)

        self.stdout.write(self.style.SUCCESS("Inventario data seeded!"))
        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(f"Categories: {len(categories)}")
        self.stdout.write(f"Suppliers: {len(suppliers)}")
        self.stdout.write(f"Products: {len(products)}")
        self.stdout.write(f"Price List: {price_list.name}")
        self.stdout.write(f"Stock Movements: {len(movements)}")
        self.stdout.write(f"Cost History: {len(cost_entries)}")

    def _clear_data(self, tenant):
        """Clear existing inventario data in reverse dependency order."""
        self.stdout.write("Clearing existing inventario data...")
        from django.db import connection

        # Disable triggers to bypass stock_movement immutability
        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = replica")
            cursor.execute(
                "DELETE FROM stock_movement WHERE tenant_id = %s",
                [str(tenant.id)],
            )
            cursor.execute(
                "DELETE FROM stock_snapshot WHERE branch_id IN "
                "(SELECT id FROM branch WHERE tenant_id = %s)",
                [str(tenant.id)],
            )
            cursor.execute("SET session_replication_role = DEFAULT")
        ProductCostHistory.objects.filter(
            product__tenant=tenant
        ).delete()
        ProductPriceHistory.objects.filter(
            product__tenant=tenant
        ).delete()
        Product.all_objects.filter(tenant=tenant).delete()
        PriceList.all_objects.filter(tenant=tenant).delete()
        Supplier.all_objects.filter(tenant=tenant).delete()
        ProductCategory.all_objects.filter(tenant=tenant).delete()
        self.stdout.write("  Inventario data cleared.")

    def _create_categories(self, tenant):
        """Create product categories."""
        self.stdout.write("Creating categories...")
        categories = []
        for name in CATEGORIES:
            cat, created = ProductCategory.all_objects.get_or_create(
                tenant=tenant,
                name=name,
                defaults={"tenant_id": tenant.id},
            )
            categories.append(cat)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {cat.name}")
        return categories

    def _create_suppliers(self, tenant):
        """Create suppliers with encrypted fields."""
        self.stdout.write("Creating suppliers...")
        suppliers = []
        for data in SUPPLIER_DATA:
            supplier, created = Supplier.all_objects.get_or_create(
                tenant=tenant,
                name=data["name"],
                defaults={
                    "tenant_id": tenant.id,
                    "tax_id_encrypted": data["tax_id"],
                    "email_encrypted": data["email"],
                    "contact_info_encrypted": data["contact_info"],
                    "address_encrypted": data["address"],
                    "lead_time_days": data["lead_time_days"],
                },
            )
            suppliers.append(supplier)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {supplier.name}")
        return suppliers

    def _create_price_list(self, tenant):
        """Create default price list."""
        self.stdout.write("Creating price list...")
        price_list, created = PriceList.all_objects.get_or_create(
            tenant=tenant,
            name="Lista General",
            defaults={
                "tenant_id": tenant.id,
                "margin_pct": Decimal("50.00"),
                "is_default": True,
            },
        )
        status = "Created" if created else "Exists"
        self.stdout.write(f"  {status}: {price_list.name}")
        return price_list

    def _create_products(self, tenant, categories, suppliers):
        """Create products from the ferreteria catalog."""
        self.stdout.write("Creating products...")
        products = []
        for sku, name, cat_idx, sup_idx, cost, price, tax, min_stk, _ in PRODUCT_DATA:
            product, created = Product.all_objects.get_or_create(
                tenant=tenant,
                sku=sku,
                defaults={
                    "tenant_id": tenant.id,
                    "name": name,
                    "category": categories[cat_idx],
                    "supplier": suppliers[sup_idx],
                    "cost_price": Decimal(cost),
                    "unit_price": Decimal(price),
                    "tax_rate": Decimal(tax),
                    "min_stock": Decimal(str(min_stk)),
                    "is_active": True,
                },
            )
            products.append(product)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: [{sku}] {name}")
        return products

    def _create_stock_movements(self, tenant, branch, products):
        """Create initial PURCHASE stock movements."""
        self.stdout.write("Creating initial stock (PURCHASE movements)...")
        movements = []
        for i, product in enumerate(products):
            initial_qty = PRODUCT_DATA[i][8]  # last element
            movement = StockMovement.all_objects.create(
                tenant=tenant,
                tenant_id=tenant.id,
                product=product,
                branch=branch,
                type=StockMovement.MovementType.PURCHASE,
                quantity_delta=Decimal(str(initial_qty)),
                cost_snapshot=product.cost_price,
                notes="Seed: initial stock purchase",
            )
            movements.append(movement)
        self.stdout.write(f"  Created {len(movements)} PURCHASE movements")
        return movements

    def _create_cost_history(self, products):
        """Create cost history entries for each product."""
        self.stdout.write("Creating cost history...")
        now = timezone.now()
        entries = []
        for product in products:
            entry, created = ProductCostHistory.objects.get_or_create(
                product=product,
                valid_from=now,
                defaults={
                    "cost": product.cost_price,
                    "source_doc": "Seed: initial cost",
                },
            )
            entries.append(entry)
        self.stdout.write(f"  Created {len(entries)} cost history entries")
        return entries

    def _create_price_history(self, products, price_list):
        """Create price history entries for each product."""
        self.stdout.write("Creating price history...")
        now = timezone.now()
        entries = []
        for product in products:
            entry, created = ProductPriceHistory.objects.get_or_create(
                product=product,
                price_list=price_list,
                valid_from=now,
                defaults={
                    "price": product.unit_price,
                    "change_reason": "Seed: initial price",
                },
            )
            entries.append(entry)
        self.stdout.write(f"  Created {len(entries)} price history entries")
        return entries
