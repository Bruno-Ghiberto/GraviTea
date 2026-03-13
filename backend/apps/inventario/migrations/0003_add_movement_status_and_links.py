# Hand-crafted migration for StockMovement status and cross-module FKs.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_facturacion", "0003_add_ventas_links_and_emitter_iva"),
        ("gravitea_ventas", "0001_initial"),
        ("inventario", "0002_add_performance_indexes"),
    ]

    operations = [
        # T013: status field
        migrations.AddField(
            model_name="stockmovement",
            name="status",
            field=models.CharField(
                choices=[
                    ("COMMITTED", "Comprometido"),
                    ("RESERVED", "Reservado"),
                    ("CANCELLED", "Cancelado"),
                ],
                db_index=True,
                default="COMMITTED",
                help_text="COMMITTED=final, RESERVED=pending sale, CANCELLED=released",
                max_length=10,
            ),
        ),
        # T014: sale_order FK
        migrations.AddField(
            model_name="stockmovement",
            name="sale_order",
            field=models.ForeignKey(
                blank=True,
                help_text="Originating sale order",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stock_movements",
                to="gravitea_ventas.saleorder",
            ),
        ),
        # T015: comprobante FK
        migrations.AddField(
            model_name="stockmovement",
            name="comprobante",
            field=models.ForeignKey(
                blank=True,
                help_text="Linked authorized invoice",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="stock_movements",
                to="gravitea_facturacion.comprobante",
            ),
        ),
        # T017: composite index
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(
                fields=["tenant_id", "status", "product_id"],
                name="idx_mvmt_tenant_status_prod",
            ),
        ),
    ]
