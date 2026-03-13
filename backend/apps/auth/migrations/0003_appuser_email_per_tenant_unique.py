"""
Migration: Change AppUser.email from global unique to per-tenant unique.

Removes the global unique=True constraint on email and adds a composite
UniqueConstraint on (tenant_id, email) to allow the same email across
different tenants while preserving uniqueness within a tenant.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gravitea_auth", "0002_add_rls_policies"),
    ]

    operations = [
        # Step 1: Remove the global unique index on email
        migrations.AlterField(
            model_name="appuser",
            name="email",
            field=models.EmailField(
                max_length=255,
                help_text="Login email address",
            ),
        ),
        # Step 2: Add composite unique constraint (tenant_id, email)
        migrations.AddConstraint(
            model_name="appuser",
            constraint=models.UniqueConstraint(
                fields=["tenant_id", "email"],
                name="unique_email_per_tenant",
            ),
        ),
    ]
