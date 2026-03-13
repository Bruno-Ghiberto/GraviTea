"""
Tenant model - root entity for multi-tenant data isolation.

Represents a customer organization (empresa cliente) in the Gravitea ERP system.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class Tenant(models.Model):
    """
    Root entity representing a customer organization.

    All business data is scoped to a tenant for complete data isolation.
    Tenants do not inherit from TenantBoundModel as they are the root.

    Attributes:
        id: UUID primary key
        name: Business display name
        tax_id: CUIT/RUT (plain, not encrypted as it's organizational)
        fiscal_config_public: Non-sensitive fiscal configuration (puntos de venta)
        fiscal_secrets_ref: Reference to Google Secret Manager for credentials
        plan_type: Subscription tier (FREE, PRO, ENTERPRISE)
        valid_until: Subscription expiration date
        is_active: Soft delete flag
        created_at: Record creation timestamp
    """

    PLAN_CHOICES = [
        ("FREE", "Free"),
        ("PRO", "Pro"),
        ("ENTERPRISE", "Enterprise"),
    ]

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique tenant identifier"
    )
    name = models.CharField(max_length=255, help_text="Business name")
    tax_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="CUIT/RUT tax identification number",
    )
    fiscal_config_public = models.JSONField(
        null=True,
        blank=True,
        help_text="Non-sensitive fiscal configuration (puntos de venta, IVA condition)",
    )
    fiscal_secrets_ref = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Reference to Google Secret Manager for AFIP credentials",
    )
    plan_type = models.CharField(
        max_length=20, choices=PLAN_CHOICES, default="FREE", help_text="Subscription tier"
    )
    valid_until = models.DateTimeField(
        null=True, blank=True, help_text="Subscription expiration date (NULL for FREE tier)"
    )
    is_active = models.BooleanField(
        default=True, db_index=True, help_text="Active tenant flag (False = suspended)"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation timestamp")

    class Meta:
        db_table = "tenant"
        ordering = ["name"]
        verbose_name = "Tenant"
        verbose_name_plural = "Tenants"

    def __str__(self):
        return f"{self.name} ({self.plan_type})"

    def clean(self):
        """Validate tenant data."""
        errors = {}

        # Non-FREE plans require valid_until
        if self.plan_type != "FREE" and not self.valid_until:
            errors["valid_until"] = "Expiration date is required for paid plans."

        # Fiscal operations require secrets reference
        if self.fiscal_config_public and not self.fiscal_secrets_ref:
            errors["fiscal_secrets_ref"] = (
                "Fiscal secrets reference is required when fiscal config is set."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_fiscal_enabled(self) -> bool:
        """Check if tenant has fiscal invoicing enabled."""
        return bool(self.fiscal_secrets_ref and self.fiscal_config_public)

    @property
    def is_subscription_valid(self) -> bool:
        """Check if subscription is currently valid."""
        if self.plan_type == "FREE":
            return True
        if not self.valid_until:
            return False
        from django.utils import timezone

        return self.valid_until > timezone.now()
