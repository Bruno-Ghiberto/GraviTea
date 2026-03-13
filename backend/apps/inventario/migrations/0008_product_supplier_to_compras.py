# T008: State-only migration — redirect Product.supplier FK to compras.Supplier
#
# The database foreign key already points to the "supplier" table,
# which hasn't moved. This only updates Django's internal state.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0007_remove_supplier_to_compras"),
        ("gravitea_compras", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="product",
                    name="supplier",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Default supplier",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products",
                        to="gravitea_compras.supplier",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
