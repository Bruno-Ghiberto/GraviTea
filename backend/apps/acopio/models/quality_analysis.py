"""QualityAnalysis model — 1:1 satellite of Romaneo."""

import uuid

from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class QualityAnalysis(TenantBoundModel):
    """
    Laboratory quality analysis results for a grain reception.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    OneToOneField to Romaneo enforces exactly one analysis per romaneo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="quality_analyses",
    )
    romaneo = models.OneToOneField(
        "gravitea_acopio.Romaneo",
        on_delete=models.CASCADE,
        related_name="quality_analysis",
    )

    # ── Core parameters (always required) ──────────────────────
    humedad_pct = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Moisture % (Hi for secado formula)."
    )
    materias_extranas_pct = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Foreign matter %."
    )
    granos_danados_pct = models.DecimalField(max_digits=5, decimal_places=2)
    granos_quebrados_pct = models.DecimalField(max_digits=5, decimal_places=2)
    granos_ardidos_pct = models.DecimalField(max_digits=5, decimal_places=2)
    cuerpos_extranos_pct = models.DecimalField(max_digits=5, decimal_places=2)

    # ── Grain-specific parameters (conditionally required) ─────
    peso_hectolitrico_kg = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Hectoliter weight (cereals only).",
    )
    proteina_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Protein % (trigo only).",
    )
    granos_verdes_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Green grains % (soja only).",
    )

    # ── Metadata ───────────────────────────────────────────────
    analysis_timestamp = models.DateTimeField()
    sample_reference = models.CharField(max_length=50, null=True, blank=True)

    # ── Managers ───────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_qualityanalysis"

    def __str__(self) -> str:
        return f"QA for {self.romaneo}"
