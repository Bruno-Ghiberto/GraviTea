"""StorageUnit model — TENANT-SCOPED physical grain storage location."""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class StorageUnit(TenantBoundModel):
    """
    Physical grain storage location (silo, celda, secadero/bin) per branch.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    Gets TenantBoundManager auto-applied and tenant_id auto-added.

    current_occupancy_kg is NOT stored — computed via annotated queryset:
        Sum("grain_lots__movements__quantity_kg")
    """

    class UnitType(models.TextChoices):
        SILO_VERTICAL = "SILO_VERTICAL", "Silo Vertical"
        CELDA_HORIZONTAL = "CELDA_HORIZONTAL", "Celda Horizontal"
        SECADERO_BIN = "SECADERO_BIN", "Secadero / Bin"

    # ── Identity ────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="storage_units",
    )
    branch = models.ForeignKey(
        "core.Branch",
        on_delete=models.PROTECT,
        related_name="storage_units",
    )
    name = models.CharField(max_length=100)
    unit_type = models.CharField(max_length=20, choices=UnitType.choices)
    capacity_tonnes = models.DecimalField(max_digits=12, decimal_places=3)
    current_grain_type = models.ForeignKey(
        "gravitea_acopio.GrainType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="storage_units",
    )
    is_active = models.BooleanField(default=True)
    environment_sensor_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="IoT sensor anchor (Phase 4).",
    )

    # ── Metadata (ADR-034) ──────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="storage_units_created",
    )

    # ── Managers ────────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_storageunit"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "name"],
                name="uq_storageunit_tenant_branch_name",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "branch_id", "is_active"],
                name="idx_su_tenant_branch_active",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_unit_type_display()})"
