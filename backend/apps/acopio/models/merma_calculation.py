"""MermaCalculation model — 1:1 immutable satellite of Romaneo."""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class MermaCalculation(TenantBoundModel):
    """
    Immutable merma (loss/shrinkage) calculation for a grain reception.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    OneToOneField to Romaneo enforces exactly one calculation per romaneo.

    FULLY IMMUTABLE: once created, cannot be modified or deleted.
    This follows the same append-only ledger pattern as StockMovement.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="merma_calculations",
    )
    romaneo = models.OneToOneField(
        "gravitea_acopio.Romaneo",
        on_delete=models.CASCADE,
        related_name="merma_calculation",
    )
    merma_table_version = models.ForeignKey(
        "gravitea_acopio.MermaTable",
        on_delete=models.PROTECT,
        related_name="calculations",
    )

    # ── Inputs ─────────────────────────────────────────────────
    peso_neto_bruto_input_kg = models.DecimalField(max_digits=17, decimal_places=3)
    hi_input_pct = models.DecimalField(max_digits=5, decimal_places=2)
    hf_used_pct = models.DecimalField(max_digits=5, decimal_places=2)
    materias_extranas_input_pct = models.DecimalField(max_digits=5, decimal_places=2)

    # ── Intermediate factors ───────────────────────────────────
    zarandeo_pct = models.DecimalField(max_digits=5, decimal_places=2)
    secado_pct = models.DecimalField(max_digits=5, decimal_places=2)
    manipuleo_pct = models.DecimalField(max_digits=5, decimal_places=2)
    volatil_pct = models.DecimalField(max_digits=5, decimal_places=2)

    # ── Intermediate weights ───────────────────────────────────
    peso_post_zarandeo_kg = models.DecimalField(max_digits=17, decimal_places=3)
    peso_post_secado_kg = models.DecimalField(max_digits=17, decimal_places=3)
    peso_post_manipuleo_kg = models.DecimalField(max_digits=17, decimal_places=3)

    # ── Final results ──────────────────────────────────────────
    peso_final_kg = models.DecimalField(max_digits=17, decimal_places=3)
    total_merma_kg = models.DecimalField(max_digits=17, decimal_places=3)
    total_factor_pct = models.DecimalField(max_digits=7, decimal_places=4)

    # ── Metadata ───────────────────────────────────────────────
    calculated_at = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="merma_calculations",
    )

    # ── Managers ───────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_mermacalculation"

    def __str__(self) -> str:
        return f"Merma for {self.romaneo}"

    # ── Immutability enforcement ───────────────────────────────

    def save(self, *args, **kwargs):
        """Enforce full immutability — only INSERT allowed."""
        if not self._state.adding:
            raise ValueError("MermaCalculation is immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion — immutable ledger entry."""
        raise ValueError("MermaCalculation is immutable and cannot be deleted.")
