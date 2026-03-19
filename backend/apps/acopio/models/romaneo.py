"""Romaneo model — TENANT-SCOPED grain reception document."""

import uuid

from django.conf import settings
from django.db import models

from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant


class RomaneoStatus(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROCESO = "EN_PROCESO", "En Proceso"
    PESADO = "PESADO", "Pesado"
    ANALIZADO = "ANALIZADO", "Analizado"
    CONFORME = "CONFORME", "Conforme"
    CERRADO = "CERRADO", "Cerrado"


class Romaneo(TenantBoundModel):
    """
    Grain reception document (romaneo) per branch.

    TENANT-SCOPED entity — inherits TenantBoundModel.
    Gets TenantBoundManager auto-applied and tenant_id auto-added.

    Lifecycle: PENDIENTE -> EN_PROCESO -> PESADO -> ANALIZADO -> CONFORME -> CERRADO
    CERRADO is fully immutable. CONFORME allows only tare capture fields.
    """

    RomaneoStatus = RomaneoStatus

    VALID_TRANSITIONS = {
        RomaneoStatus.PENDIENTE: RomaneoStatus.EN_PROCESO,
        RomaneoStatus.EN_PROCESO: RomaneoStatus.PESADO,
        RomaneoStatus.PESADO: RomaneoStatus.ANALIZADO,
        RomaneoStatus.ANALIZADO: RomaneoStatus.CONFORME,
        RomaneoStatus.CONFORME: RomaneoStatus.CERRADO,
    }

    # ── Group 1: Identity ──────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="romaneos",
    )
    romaneo_number = models.CharField(
        max_length=20,
        help_text="Auto-generated ROM-YYYY-NNNNN per branch.",
    )
    status = models.CharField(
        max_length=15,
        choices=RomaneoStatus.choices,
        default=RomaneoStatus.PENDIENTE,
    )

    # ── Group 2: References ────────────────────────────────────
    grain_type = models.ForeignKey(
        "gravitea_acopio.GrainType",
        on_delete=models.PROTECT,
        related_name="romaneos",
    )
    campaign = models.ForeignKey(
        "gravitea_acopio.CampanaConfig",
        on_delete=models.PROTECT,
        related_name="romaneos",
    )
    branch = models.ForeignKey(
        "core.Branch",
        on_delete=models.PROTECT,
        related_name="romaneos",
    )

    # ── Group 3: Timestamps ────────────────────────────────────
    ts_entrada = models.DateTimeField(auto_now_add=True)
    ts_pesada_bruta = models.DateTimeField(null=True, blank=True)
    ts_calado = models.DateTimeField(
        null=True, blank=True, help_text="Sampling timestamp."
    )
    ts_analisis = models.DateTimeField(null=True, blank=True)
    ts_descarga = models.DateTimeField(null=True, blank=True)
    ts_tara = models.DateTimeField(null=True, blank=True)

    # ── Group 4: Vehicle / Driver ──────────────────────────────
    patente_chasis = models.CharField(max_length=15)
    patente_acoplado = models.CharField(max_length=15, null=True, blank=True)
    driver_name = models.CharField(max_length=200)
    driver_dni = models.CharField(max_length=20)

    # ── Group 5: Weights ───────────────────────────────────────
    peso_bruto_kg = models.DecimalField(
        max_digits=17, decimal_places=3, null=True, blank=True
    )
    tara_kg = models.DecimalField(
        max_digits=17, decimal_places=3, null=True, blank=True
    )
    peso_neto_bruto_kg = models.DecimalField(
        max_digits=17, decimal_places=3, null=True, blank=True
    )
    weighbridge_device = models.CharField(
        max_length=100, null=True, blank=True, help_text="Placeholder for weighbridge integration."
    )

    # ── Group 6: Documents / Origin ────────────────────────────
    cpe_numero = models.CharField(max_length=20)
    ctg_codigo = models.CharField(max_length=20, null=True, blank=True)
    producer_cuit = models.CharField(max_length=13)
    origin_locality = models.CharField(max_length=200)

    # ── Group 7: Operators / Results ───────────────────────────
    operator_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="romaneos_operated",
    )
    laboratorista_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneos_analyzed",
    )
    device_id = models.CharField(max_length=100, null=True, blank=True)
    grado_asignado = models.IntegerField(null=True, blank=True)
    bonificacion_rebaja_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    tolerance_table_version = models.ForeignKey(
        "gravitea_acopio.ToleranceTable",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="romaneos_graded",
    )
    peso_neto_conforme_kg = models.DecimalField(
        max_digits=17, decimal_places=3, null=True, blank=True
    )

    # ── Group 8: Storage (spec-12) ──────────────────────────────
    storage_unit = models.ForeignKey(
        "gravitea_acopio.StorageUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneos",
    )
    grain_lot = models.ForeignKey(
        "gravitea_acopio.GrainLot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="romaneos",
    )

    # ── Managers ───────────────────────────────────────────────
    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "acopio_romaneo"
        ordering = ["-ts_entrada"]
        indexes = [
            models.Index(
                fields=["tenant_id", "status", "ts_entrada"],
                name="idx_romaneo_tenant_status_ts",
            ),
            models.Index(
                fields=["tenant_id", "branch_id", "ts_entrada"],
                name="idx_romaneo_tenant_branch_ts",
            ),
            models.Index(
                fields=["tenant_id", "campaign_id", "grain_type_id"],
                name="idx_romaneo_tenant_camp_grain",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cpe_numero"],
                name="uq_romaneo_tenant_cpe",
            ),
            models.UniqueConstraint(
                fields=["tenant", "romaneo_number"],
                name="uq_romaneo_tenant_number",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.romaneo_number} ({self.status})"

    # ── Lifecycle hooks ────────────────────────────────────────

    def save(self, *args, **kwargs):
        """
        Save with state-machine validation and partial immutability.

        Rules:
        1. CERRADO: absolutely no changes allowed.
        2. CONFORME: only tare capture fields (tara_kg, peso_neto_bruto_kg,
           ts_tara) and status transition to CERRADO allowed.
        3. State transitions must follow VALID_TRANSITIONS.
        4. romaneo_number is auto-generated on first save.
        """
        is_new = self._state.adding

        if not is_new:
            existing = Romaneo.all_objects.get(pk=self.pk)

            # CERRADO: absolutely no changes allowed
            if existing.status == RomaneoStatus.CERRADO:
                raise ValueError("Romaneo CERRADO cannot be modified.")

            # CONFORME: only tare capture and status->CERRADO allowed
            if existing.status == RomaneoStatus.CONFORME:
                allowed_fields = {
                    "tara_kg", "peso_neto_bruto_kg", "ts_tara", "status",
                    "storage_unit_id", "grain_lot_id",  # spec-12: deposit service sets these at CONFORME
                }
                for field in self._meta.get_fields():
                    if not hasattr(field, "attname"):
                        continue
                    attr = field.attname
                    if attr in allowed_fields or attr == "id":
                        continue
                    old_val = getattr(existing, attr, None)
                    new_val = getattr(self, attr, None)
                    if old_val != new_val:
                        raise ValueError(
                            f"Romaneo CONFORME is immutable. Cannot change '{attr}'."
                        )

            # State transition validation
            if existing.status != self.status:
                expected = self.VALID_TRANSITIONS.get(RomaneoStatus(existing.status))
                if expected is None or self.status != expected:
                    raise ValueError(
                        f"Invalid state transition: {existing.status} -> {self.status}. "
                        f"Expected: {existing.status} -> {expected}."
                    )

        # Auto-generate romaneo_number on first save
        if is_new and not self.romaneo_number:
            self.romaneo_number = self._generate_romaneo_number()

        super().save(*args, **kwargs)

    def _generate_romaneo_number(self) -> str:
        """Generate sequential romaneo number: ROM-YYYY-NNNNN per tenant+branch."""
        from django.utils import timezone

        year = timezone.now().year
        prefix = f"ROM-{year}-"
        last = (
            Romaneo.all_objects.filter(
                tenant_id=self.tenant_id,
                branch_id=self.branch_id,
                romaneo_number__startswith=prefix,
            )
            .order_by("-romaneo_number")
            .values_list("romaneo_number", flat=True)
            .first()
        )
        if last:
            seq = int(last.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:05d}"
