"""GrainLot model — TENANT-SCOPED grain lot within a storage unit."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class GrainLot(TenantBoundModel):
    """
    Segregated grain lot inside a StorageUnit, keyed by composite identity.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    Composite key: (tenant, branch, grain_type, campaign, grado, storage_unit).

    Running balance (total_kg) is updated atomically by the service layer
    on each GrainMovement. Must always equal Sum(movements.quantity_kg).
    """

    # ── Identity ────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="grain_lots",
    )
    lot_code = models.CharField(
        max_length=100,
        help_text="Auto-generated: BRANCH-GRAIN-CAMPAIGN-GRADE.",
    )

    # ── Composite key fields ────────────────────────────────────
    branch = models.ForeignKey(
        "core.Branch",
        on_delete=models.PROTECT,
        related_name="grain_lots",
    )
    grain_type = models.ForeignKey(
        "gravitea_acopio.GrainType",
        on_delete=models.PROTECT,
        related_name="grain_lots",
    )
    campaign = models.ForeignKey(
        "gravitea_acopio.CampanaConfig",
        on_delete=models.PROTECT,
        related_name="grain_lots",
    )
    grado = models.IntegerField(help_text="1/2/3 for cereals; 0 for oleaginosas.")
    storage_unit = models.ForeignKey(
        "gravitea_acopio.StorageUnit",
        on_delete=models.PROTECT,
        related_name="grain_lots",
    )

    # ── Balance ─────────────────────────────────────────────────
    total_kg = models.DecimalField(
        max_digits=17, decimal_places=3, default=Decimal("0.000"),
    )
    is_own_grain = models.BooleanField(
        default=False,
        help_text="ADR-020: True→1.3.XX (own); False→8.1.XX (third-party custody).",
    )

    # ── Metadata (ADR-034) ──────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grain_lots_created",
    )

    # ── Managers ────────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_grainlot"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "branch", "grain_type", "campaign", "grado", "storage_unit"],
                name="uq_grainlot_composite_identity",
            ),
            models.CheckConstraint(
                check=Q(total_kg__gte=0),
                name="chk_grainlot_nonnegative_balance",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "storage_unit_id"],
                name="idx_gl_tenant_storage",
            ),
            models.Index(
                fields=["tenant_id", "campaign_id", "grain_type_id"],
                name="idx_gl_tenant_camp_grain",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.lot_code} ({self.total_kg} kg)"

    # ── Auto lot_code generation ────────────────────────────────

    def save(self, *args, **kwargs):
        if not self.lot_code:
            self.lot_code = self._generate_lot_code()
        super().save(*args, **kwargs)

    def _generate_lot_code(self) -> str:
        """Generate lot code: BRANCH-GRAIN-CAMPAIGN-GRADE."""
        branch_code = (
            self.branch.code
            if hasattr(self.branch, "code")
            else str(self.branch_id)[:4]
        )
        grain_code = self.grain_type.code
        campaign_code = self.campaign.campaign_code.replace("/", "")
        return f"{branch_code}-{grain_code}-{campaign_code}-{self.grado}"
