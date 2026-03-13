"""
Branch model - physical location (sucursal) of a tenant.

Represents a branch/store location for multi-location retail businesses.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .mixins import TenantBoundModel
from .tenant import Tenant


class Branch(TenantBoundModel):
    """
    Physical location (sucursal) of a tenant.

    Each tenant can have multiple branches for multi-location operations.
    Stock, sales, and users are typically associated with specific branches.

    Attributes:
        id: UUID primary key
        tenant_id: Parent tenant (via TenantBoundModel)
        name: Branch display name
        address: Physical address
        phone: Contact phone number
        coordinates: Lat/Long for logistics
        afip_pos_number: AFIP punto de venta number (unique per tenant)
        is_active: Soft delete flag
        created_at: Record creation timestamp
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, help_text="Unique branch identifier"
    )
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="branches", help_text="Parent tenant"
    )
    name = models.CharField(
        max_length=255, help_text="Branch display name (e.g., 'Casa Central', 'Sucursal Norte')"
    )
    address = models.CharField(
        max_length=500, null=True, blank=True, help_text="Physical street address"
    )
    phone = models.CharField(max_length=50, null=True, blank=True, help_text="Contact phone number")
    coordinates = models.JSONField(
        null=True, blank=True, help_text="Geographic coordinates: {'lat': float, 'lng': float}"
    )
    afip_pos_number = models.IntegerField(
        null=True, blank=True, help_text="AFIP punto de venta number (1-99999)"
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text="Active branch flag")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation timestamp")

    class Meta:
        db_table = "branch"
        ordering = ["name"]
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
        ]
        constraints = [
            # AFIP POS number must be unique per tenant
            models.UniqueConstraint(
                fields=["tenant_id", "afip_pos_number"],
                condition=models.Q(afip_pos_number__isnull=False),
                name="unique_afip_pos_per_tenant",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    def clean(self):
        """Validate branch data."""
        errors = {}

        # Validate AFIP POS number range
        if self.afip_pos_number is not None:
            if self.afip_pos_number < 1 or self.afip_pos_number > 99999:
                errors["afip_pos_number"] = "AFIP POS number must be between 1 and 99999."

        # Validate coordinates schema
        if self.coordinates:
            if not isinstance(self.coordinates, dict):
                errors["coordinates"] = "Coordinates must be a JSON object."
            elif "lat" not in self.coordinates or "lng" not in self.coordinates:
                errors["coordinates"] = "Coordinates must include lat and lng fields."
            else:
                try:
                    lat = float(self.coordinates["lat"])
                    lng = float(self.coordinates["lng"])
                    if not (-90 <= lat <= 90):
                        errors["coordinates"] = "Latitude must be between -90 and 90."
                    if not (-180 <= lng <= 180):
                        errors["coordinates"] = "Longitude must be between -180 and 180."
                except (TypeError, ValueError):
                    errors["coordinates"] = "Latitude and longitude must be numbers."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ensure tenant_id matches the tenant FK
        if self.tenant_id is None and hasattr(self, "tenant") and self.tenant:
            self.tenant_id = self.tenant.id
        elif self.tenant and self.tenant_id != self.tenant.id:
            self.tenant_id = self.tenant.id

        self.full_clean()
        super().save(*args, **kwargs)
