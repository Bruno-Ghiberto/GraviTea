"""Add updated_at field to Comprobante and CAEA models.

Auto-generated migration for FIX-3 (D5-002) and FIX-4 (D5-004).
"""

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_facturacion", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="comprobante",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
            ),
        ),
        migrations.AddField(
            model_name="caea",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
            ),
        ),
    ]
