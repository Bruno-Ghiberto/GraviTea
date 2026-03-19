"""GrainMovement model — IMMUTABLE ledger entry for grain stock changes."""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class GrainMovement(TenantBoundModel):
    """
    Immutable grain movement ledger entry.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    FULLY IMMUTABLE: once created, cannot be modified or deleted.
    Follows the same append-only ledger pattern as MermaCalculation.

    NOTE: updated_at is intentionally omitted (immutable model).
    quantity_kg can be negative — WITHDRAWAL and TRANSFER_OUT are stored as negative.
    """

    class MovementType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Depósito"
        WITHDRAWAL = "WITHDRAWAL", "Egreso"
        TRANSFER_IN = "TRANSFER_IN", "Transferencia Entrada"
        TRANSFER_OUT = "TRANSFER_OUT", "Transferencia Salida"
        ADJUSTMENT = "ADJUSTMENT", "Ajuste"

    # ── Identity ────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="grain_movements",
    )
    grain_lot = models.ForeignKey(
        "gravitea_acopio.GrainLot",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=15, choices=MovementType.choices)
    quantity_kg = models.DecimalField(
        max_digits=17, decimal_places=3,
        help_text="Positive=inflow; negative=outflow.",
    )

    # ── Optional references ─────────────────────────────────────
    romaneo = models.ForeignKey(
        "gravitea_acopio.Romaneo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grain_movements",
    )
    reference_document = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="External doc ref for non-romaneo movements.",
    )
    notes = models.TextField(null=True, blank=True)

    # ── Metadata (ADR-034) — NO updated_at (immutable) ─────────
    movement_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grain_movements_created",
    )
    device_id = models.CharField(
        max_length=100, null=True, blank=True,
        help_text="Device provenance (ADR-034).",
    )

    # ── Managers ────────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_grainmovement"
        ordering = ["-movement_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "grain_lot_id", "movement_at"],
                name="idx_gm_tenant_lot_ts",
            ),
            models.Index(
                fields=["tenant_id", "movement_type", "movement_at"],
                name="idx_gm_tenant_type_ts",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_movement_type_display()} {self.quantity_kg} kg"

    # ── Immutability enforcement ────────────────────────────────

    def save(self, *args, **kwargs):
        """Enforce full immutability — only INSERT allowed."""
        if not self._state.adding:
            raise ValueError("GrainMovement is immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion — immutable ledger entry."""
        raise ValueError("GrainMovement is immutable and cannot be deleted.")
