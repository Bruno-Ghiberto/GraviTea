# Hand-crafted migration for ventas integration fields.
# Does NOT touch pre-existing tenant_id migration state mismatch.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_facturacion", "0002_add_updated_at_comprobante_caea"),
        ("gravitea_ventas", "0001_initial"),
    ]

    operations = [
        # T020: emitter_condicion_iva on ARCACredential
        migrations.AddField(
            model_name="arcacredential",
            name="emitter_condicion_iva",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "IVA Responsable Inscripto"),
                    (4, "IVA Sujeto Exento"),
                    (5, "Consumidor Final"),
                    (6, "Responsable Monotributo"),
                    (7, "Sujeto No Categorizado"),
                    (8, "Proveedor del Exterior"),
                    (9, "Cliente del Exterior"),
                    (10, "IVA Liberado – Ley Nº 19.640"),
                    (13, "Monotributista Social"),
                ],
                default=1,
                help_text="Emitter IVA condition for invoice type resolution",
            ),
        ),
        # T018: sale_order OneToOneField on Comprobante
        migrations.AddField(
            model_name="comprobante",
            name="sale_order",
            field=models.OneToOneField(
                blank=True,
                help_text="Originating sale order (null for standalone invoices)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="comprobante_direct",
                to="gravitea_ventas.saleorder",
            ),
        ),
        # T019: customer FK on Comprobante
        migrations.AddField(
            model_name="comprobante",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                help_text="Customer (from sale order or standalone)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="comprobantes",
                to="gravitea_ventas.customer",
            ),
        ),
    ]
