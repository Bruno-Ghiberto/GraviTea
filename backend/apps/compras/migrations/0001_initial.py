# T006: SeparateDatabaseAndState migration — register Supplier in compras
#
# state_operations: tell Django that compras now owns the Supplier model.
# database_operations: empty — the "supplier" table already exists from inventario 0001.

import uuid
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models

import apps.core.encryption.fields
import apps.core.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Supplier",
                    fields=[
                        (
                            "id",
                            models.UUIDField(
                                default=uuid.uuid4,
                                editable=False,
                                primary_key=True,
                                serialize=False,
                            ),
                        ),
                        (
                            "name",
                            models.CharField(
                                help_text="Supplier name", max_length=255
                            ),
                        ),
                        (
                            "tax_id_encrypted",
                            apps.core.encryption.fields.EncryptedCharField(
                                blank=True,
                                help_text="Encrypted tax identification number",
                                max_length=150,
                                null=True,
                            ),
                        ),
                        (
                            "tax_id_hash",
                            models.CharField(
                                blank=True,
                                db_index=True,
                                help_text="Blind index for tax_id searches",
                                max_length=64,
                                null=True,
                            ),
                        ),
                        (
                            "contact_info_encrypted",
                            apps.core.encryption.fields.EncryptedTextField(
                                blank=True,
                                help_text="Encrypted contact information",
                                null=True,
                            ),
                        ),
                        (
                            "email_encrypted",
                            apps.core.encryption.fields.EncryptedCharField(
                                blank=True,
                                help_text="Encrypted email address",
                                max_length=355,
                                null=True,
                            ),
                        ),
                        (
                            "email_hash",
                            models.CharField(
                                blank=True,
                                db_index=True,
                                help_text="Blind index for email searches",
                                max_length=64,
                                null=True,
                            ),
                        ),
                        (
                            "address_encrypted",
                            apps.core.encryption.fields.EncryptedTextField(
                                blank=True,
                                help_text="Encrypted physical address",
                                null=True,
                            ),
                        ),
                        (
                            "lead_time_days",
                            models.IntegerField(
                                blank=True,
                                help_text="Expected delivery lead time in days",
                                null=True,
                            ),
                        ),
                        (
                            "current_balance",
                            apps.core.fields.MoneyField(
                                decimal_places=3,
                                default=Decimal("0.000"),
                                help_text="Current account balance (payables)",
                                max_digits=17,
                            ),
                        ),
                        (
                            "is_active",
                            models.BooleanField(
                                db_index=True,
                                default=True,
                                help_text="Active/available flag",
                            ),
                        ),
                        (
                            "custom_data",
                            models.JSONField(
                                blank=True,
                                default=dict,
                                help_text="Tenant-defined custom fields. Validated against TenantFieldDefinition.",
                            ),
                        ),
                        (
                            "created_at",
                            models.DateTimeField(auto_now_add=True),
                        ),
                        (
                            "tenant",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="suppliers",
                                to="core.tenant",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Supplier",
                        "verbose_name_plural": "Suppliers",
                        "db_table": "supplier",
                        "ordering": ["name"],
                    },
                ),
                migrations.AddConstraint(
                    model_name="supplier",
                    constraint=models.UniqueConstraint(
                        fields=["tenant_id", "name"],
                        name="unique_supplier_per_tenant",
                    ),
                ),
                migrations.AddIndex(
                    model_name="supplier",
                    index=models.Index(
                        fields=["custom_data"],
                        name="idx_supplier_custom_data",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
