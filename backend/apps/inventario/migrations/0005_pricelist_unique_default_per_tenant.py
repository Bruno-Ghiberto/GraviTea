"""Add partial unique index to enforce one default PriceList per tenant.

Fixes H-004: The application-level ``save()`` unset is racy under
concurrent writes.  This database-level constraint is authoritative.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0004_add_rls_policies"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="pricelist",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_default=True),
                fields=("tenant_id",),
                name="unique_default_pricelist_per_tenant",
            ),
        ),
    ]
