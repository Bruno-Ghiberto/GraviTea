"""
Management command to seed ventas (sales) data for development.

Creates sample customers, sale orders in various lifecycle states, and
order items linked to existing inventory products. Requires seed_data
to have been run first (for tenant, branch, and product data).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Branch, Tenant
from apps.facturacion.constants import CondicionIVA, DocTipo
from apps.inventario.models import Product
from apps.ventas.models import Customer, SaleOrder, SaleOrderItem, SaleOrderStatus


# Valid CUITs (Modulo-11 verified)
CUSTOMER_DATA = [
    {
        "cuit": "30710158254",  # Responsable Inscripto
        "doc_tipo": DocTipo.CUIT,
        "condicion_iva": CondicionIVA.RESPONSABLE_INSCRIPTO,
        "razon_social": "Tech Solutions S.A.",
        "domicilio": "Av. Corrientes 1500, CABA",
        "email": "contacto@techsolutions.com.ar",
        "telefono": "+54 11 4555-0001",
    },
    {
        "cuit": "20277839519",  # Monotributista
        "doc_tipo": DocTipo.CUIT,
        "condicion_iva": CondicionIVA.MONOTRIBUTISTA,
        "razon_social": "Maria Lopez",
        "domicilio": "San Martin 450, Rosario",
        "email": "mlopez@email.com",
        "telefono": "+54 341 4555-0002",
    },
    {
        "cuit": "27183974219",  # Consumidor Final
        "doc_tipo": DocTipo.CUIT,
        "condicion_iva": CondicionIVA.CONSUMIDOR_FINAL,
        "razon_social": "Juan Perez",
        "domicilio": "Belgrano 780, Mendoza",
        "email": "",
        "telefono": "",
    },
    {
        "cuit": "30715625384",  # Exento
        "doc_tipo": DocTipo.CUIT,
        "condicion_iva": CondicionIVA.EXENTO,
        "razon_social": "Fundacion Educativa del Sur",
        "domicilio": "Av. Libertador 3200, CABA",
        "email": "admin@funedsur.org.ar",
        "telefono": "+54 11 4555-0004",
    },
]


class Command(BaseCommand):
    help = "Seed ventas data (customers, orders, items) for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing ventas data before seeding",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(is_active=True).first()
        if not tenant:
            self.stderr.write(
                self.style.ERROR(
                    "No active tenant found. Run 'seed_data' first."
                )
            )
            return

        set_current_tenant_id(tenant.id)
        branch = Branch.objects.filter(tenant=tenant).first()
        if not branch:
            self.stderr.write(
                self.style.ERROR(
                    "No branch found for tenant. Run 'seed_data' first."
                )
            )
            return

        products = list(Product.objects.filter(tenant=tenant, is_active=True)[:5])
        if len(products) < 2:
            self.stderr.write(
                self.style.ERROR(
                    "Need at least 2 active products. Run 'seed_data' first."
                )
            )
            return

        self.stdout.write(
            f"Seeding ventas for tenant '{tenant.name}', "
            f"branch '{branch.name}' ({len(products)} products available)"
        )

        with transaction.atomic():
            if options["clear"]:
                self._clear_data(tenant)

            customers = self._create_customers(tenant)
            orders = self._create_orders(tenant, branch, customers, products)

        self.stdout.write(self.style.SUCCESS("Ventas data seeded successfully!"))
        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(f"Customers: {len(customers)}")
        self.stdout.write(f"Sale Orders: {len(orders)}")
        for order in orders:
            item_count = order.items.count()
            self.stdout.write(
                f"  {order} - {item_count} items, "
                f"total ${order.total_amount}"
            )

    def _clear_data(self, tenant):
        """Clear existing ventas data in reverse dependency order."""
        self.stdout.write("Clearing existing ventas data...")
        SaleOrderItem.all_objects.filter(tenant=tenant).delete()
        SaleOrder.all_objects.filter(tenant=tenant).delete()
        Customer.all_objects.filter(tenant=tenant).delete()
        self.stdout.write("  Ventas data cleared.")

    def _create_customers(self, tenant):
        """Create sample customers."""
        self.stdout.write("Creating customers...")
        customers = []

        for data in CUSTOMER_DATA:
            customer, created = Customer.all_objects.get_or_create(
                tenant=tenant,
                cuit=data["cuit"],
                defaults={
                    "tenant_id": tenant.id,
                    "doc_tipo": data["doc_tipo"],
                    "condicion_iva": data["condicion_iva"],
                    "razon_social": data["razon_social"],
                    "domicilio": data["domicilio"],
                    "email": data["email"],
                    "telefono": data["telefono"],
                },
            )
            customers.append(customer)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: {customer.razon_social}")

        return customers

    def _create_orders(self, tenant, branch, customers, products):
        """Create sale orders in various lifecycle states."""
        self.stdout.write("Creating sale orders...")
        orders = []

        # Order 1: DRAFT with 2 items
        order1 = self._create_order_with_items(
            tenant=tenant,
            branch=branch,
            customer=customers[0],
            items_data=[
                {"product": products[0], "quantity": Decimal("5.0000")},
                {"product": products[1], "quantity": Decimal("3.0000")},
            ],
        )
        orders.append(order1)
        self.stdout.write(f"  Created DRAFT order: {order1.id}")

        # Order 2: CONFIRMED with 3 items
        order2 = self._create_order_with_items(
            tenant=tenant,
            branch=branch,
            customer=customers[1],
            items_data=[
                {"product": products[0], "quantity": Decimal("10.0000")},
                {"product": products[1], "quantity": Decimal("2.0000")},
                {"product": products[min(2, len(products) - 1)], "quantity": Decimal("1.0000")},
            ],
        )
        # Transition to CONFIRMED
        order2.status = SaleOrderStatus.CONFIRMED
        order2.confirmed_at = timezone.now()
        order2.save()
        orders.append(order2)
        self.stdout.write(f"  Created CONFIRMED order: {order2.id}")

        # Order 3: Another DRAFT (single item)
        order3 = self._create_order_with_items(
            tenant=tenant,
            branch=branch,
            customer=customers[2],
            items_data=[
                {"product": products[0], "quantity": Decimal("1.0000")},
            ],
        )
        orders.append(order3)
        self.stdout.write(f"  Created DRAFT order: {order3.id}")

        return orders

    def _create_order_with_items(self, tenant, branch, customer, items_data):
        """Create a sale order with items and recalculate totals."""
        order = SaleOrder.all_objects.create(
            tenant=tenant,
            tenant_id=tenant.id,
            customer=customer,
            branch=branch,
            status=SaleOrderStatus.DRAFT,
            subtotal=Decimal("0.000"),
            total_iva=Decimal("0.000"),
            total_amount=Decimal("0.000"),
        )

        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]
            unit_price = product.unit_price
            subtotal = quantity * unit_price
            tax_rate = getattr(product, "tax_rate", Decimal("21.00"))
            iva_amount = subtotal * (tax_rate / Decimal("100"))

            SaleOrderItem.all_objects.create(
                tenant=tenant,
                tenant_id=tenant.id,
                sale_order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                tax_rate=tax_rate,
                iva_amount=iva_amount,
            )

        order.recalculate_totals()
        return order
