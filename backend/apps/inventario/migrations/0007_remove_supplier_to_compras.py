# T007: SeparateDatabaseAndState migration — remove Supplier from inventario state
#
# state_operations: remove Supplier model from inventario's Django state.
# database_operations: empty — the "supplier" table stays untouched.
#
# Must run AFTER compras 0001_initial registers Supplier there.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0006_remove_product_attributes_product_custom_data_and_more"),
        ("gravitea_compras", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(
                    name="Supplier",
                ),
            ],
            database_operations=[],
        ),
    ]
