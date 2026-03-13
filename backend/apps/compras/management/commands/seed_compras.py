"""
Management command to seed compras (purchases) data for development.

Creates sample purchase orders in various states, PO items referencing
existing seeded products and suppliers, and goods receipts with lines.
Requires seed_data + seed_inventario to have run first.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.compras.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseOrderStatus,
    Supplier,
)
from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Branch, Tenant
from apps.inventario.models import Product


class Command(BaseCommand):
    help = "Seed compras data: purchase orders, items, goods receipts"

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(name="Gravitea Demo").first()
        if not tenant:
            self.stderr.write(self.style.ERROR(
                "No 'Gravitea Demo' tenant found. Run seed_data first."
            ))
            return

        set_current_tenant_id(tenant.id)
        branch = Branch.objects.filter(tenant=tenant).first()
        if not branch:
            self.stderr.write(self.style.ERROR("No branch found."))
            return

        suppliers = list(Supplier.objects.all()[:3])
        if not suppliers:
            self.stderr.write(self.style.ERROR(
                "No suppliers found. Run seed_inventario first."
            ))
            return

        products = list(Product.objects.all()[:6])
        if len(products) < 4:
            self.stderr.write(self.style.ERROR(
                "Need at least 4 products. Run seed_inventario first."
            ))
            return

        with transaction.atomic():
            self._seed_purchase_orders(tenant, branch, suppliers, products)

        self.stdout.write(self.style.SUCCESS("Compras seed data created."))

    def _seed_purchase_orders(self, tenant, branch, suppliers, products):
        today = timezone.now().date()

        # PO-001: DRAFT (no items yet scenario is common but we add items)
        po1, _ = PurchaseOrder.objects.get_or_create(
            tenant=tenant,
            order_number="PO-SEED-001",
            defaults={
                "supplier": suppliers[0],
                "order_date": today,
                "status": PurchaseOrderStatus.DRAFT,
                "notes": "Draft PO for review",
            },
        )
        if _:
            PurchaseOrderItem.objects.create(
                purchase_order=po1,
                product=products[0],
                quantity=Decimal("10.000"),
                unit_price=Decimal("150.00"),
            )
            PurchaseOrderItem.objects.create(
                purchase_order=po1,
                product=products[1],
                quantity=Decimal("5.000"),
                unit_price=Decimal("320.50"),
            )
            self.stdout.write(f"  Created PO-SEED-001 (DRAFT, 2 items)")

        # PO-002: CONFIRMED
        po2, _ = PurchaseOrder.objects.get_or_create(
            tenant=tenant,
            order_number="PO-SEED-002",
            defaults={
                "supplier": suppliers[1],
                "order_date": today,
                "status": PurchaseOrderStatus.CONFIRMED,
                "notes": "Confirmed, awaiting delivery",
            },
        )
        if _:
            PurchaseOrderItem.objects.create(
                purchase_order=po2,
                product=products[2],
                quantity=Decimal("20.000"),
                unit_price=Decimal("85.00"),
            )
            PurchaseOrderItem.objects.create(
                purchase_order=po2,
                product=products[3],
                quantity=Decimal("15.000"),
                unit_price=Decimal("42.75"),
            )
            self.stdout.write(f"  Created PO-SEED-002 (CONFIRMED, 2 items)")

        # PO-003: PARTIAL_RECEIVED with a goods receipt
        po3, created_po3 = PurchaseOrder.objects.get_or_create(
            tenant=tenant,
            order_number="PO-SEED-003",
            defaults={
                "supplier": suppliers[0],
                "order_date": today,
                "status": PurchaseOrderStatus.PARTIAL_RECEIVED,
                "notes": "Partial delivery received",
            },
        )
        if created_po3:
            poi3a = PurchaseOrderItem.objects.create(
                purchase_order=po3,
                product=products[0],
                quantity=Decimal("30.000"),
                unit_price=Decimal("150.00"),
                received_quantity=Decimal("15.000"),
            )
            poi3b = PurchaseOrderItem.objects.create(
                purchase_order=po3,
                product=products[4] if len(products) > 4 else products[1],
                quantity=Decimal("10.000"),
                unit_price=Decimal("200.00"),
                received_quantity=Decimal("10.000"),
            )
            gr3, _ = GoodsReceipt.objects.get_or_create(
                tenant=tenant,
                receipt_number="GR-SEED-001",
                defaults={
                    "purchase_order": po3,
                },
            )
            if _:
                GoodsReceiptLine.objects.create(
                    goods_receipt=gr3,
                    purchase_order_item=poi3a,
                    product=poi3a.product,
                    quantity_received=Decimal("15.000"),
                )
                GoodsReceiptLine.objects.create(
                    goods_receipt=gr3,
                    purchase_order_item=poi3b,
                    product=poi3b.product,
                    quantity_received=Decimal("10.000"),
                )
            self.stdout.write(f"  Created PO-SEED-003 (PARTIAL_RECEIVED, 1 GR)")

        # PO-004: RECEIVED (fully received)
        po4, created_po4 = PurchaseOrder.objects.get_or_create(
            tenant=tenant,
            order_number="PO-SEED-004",
            defaults={
                "supplier": suppliers[2 % len(suppliers)],
                "order_date": today,
                "status": PurchaseOrderStatus.RECEIVED,
                "notes": "Fully received",
            },
        )
        if created_po4:
            poi4 = PurchaseOrderItem.objects.create(
                purchase_order=po4,
                product=products[3],
                quantity=Decimal("25.000"),
                unit_price=Decimal("42.75"),
                received_quantity=Decimal("25.000"),
            )
            gr4, _ = GoodsReceipt.objects.get_or_create(
                tenant=tenant,
                receipt_number="GR-SEED-002",
                defaults={
                    "purchase_order": po4,
                },
            )
            if _:
                GoodsReceiptLine.objects.create(
                    goods_receipt=gr4,
                    purchase_order_item=poi4,
                    product=poi4.product,
                    quantity_received=Decimal("25.000"),
                )
            self.stdout.write(f"  Created PO-SEED-004 (RECEIVED, 1 GR)")

        # PO-005: CANCELLED
        po5, _ = PurchaseOrder.objects.get_or_create(
            tenant=tenant,
            order_number="PO-SEED-005",
            defaults={
                "supplier": suppliers[0],
                "order_date": today,
                "status": PurchaseOrderStatus.CANCELLED,
                "notes": "Cancelled by supplier",
            },
        )
        if _:
            PurchaseOrderItem.objects.create(
                purchase_order=po5,
                product=products[2],
                quantity=Decimal("50.000"),
                unit_price=Decimal("85.00"),
            )
            self.stdout.write(f"  Created PO-SEED-005 (CANCELLED, 1 item)")
