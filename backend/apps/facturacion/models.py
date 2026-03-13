"""
Electronic invoicing models for Gravitea ERP.

Implements ARCA (ex-AFIP) fiscal document entities with tenant isolation,
immutable ledger pattern for authorized comprobantes, and encrypted
credential storage.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models

from apps.core.encryption.fields import EncryptedTextField
from apps.core.managers.tenant_bound import AllObjectsManager, TenantBoundManager
from apps.core.models.mixins import TenantBoundModel
from apps.core.models.tenant import Tenant

from .constants import (
    CAEAStatus,
    ComprobanteStatus,
    CondicionIVA,
    IMMUTABLE_STATUSES,
    PuntoDeVentaTipo,
)


# ============================================================
# ARCACredential
# ============================================================


class ARCACredential(TenantBoundModel):
    """
    ARCA authentication credentials per tenant, per environment.

    Stores X.509 certificate and RSA private key (AES-256-GCM encrypted)
    for WSAA authentication. One credential per (tenant, environment) pair.

    Attributes:
        cuit_holder: Certificate holder CUIT (11 digits, no hyphens).
        cuit_represented: Represented company CUIT (delegation model).
        certificate_pem: X.509 certificate in PEM format.
        private_key_pem: RSA private key (encrypted at rest).
        is_production: True=production, False=homologacion.
        is_active: Soft-disable without deletion.
        certificate_expires_at: Certificate expiration for system check warnings.
        last_unique_id: Last TRA uniqueId for replay protection.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="arca_credentials",
    )
    cuit_holder = models.CharField(
        max_length=11,
        help_text="Certificate holder CUIT (11 digits, no hyphens)",
    )
    cuit_represented = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        help_text="Represented company CUIT (delegation model)",
    )
    certificate_pem = models.TextField(
        help_text="X.509 certificate in PEM format",
    )
    private_key_pem = EncryptedTextField(
        help_text="RSA private key (AES-256-GCM encrypted at rest)",
    )
    is_production = models.BooleanField(
        default=False,
        help_text="True=production, False=homologacion",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft-disable without deletion",
    )
    certificate_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Certificate expiration (for system check warnings)",
    )
    last_unique_id = models.BigIntegerField(
        default=0,
        help_text="Last TRA uniqueId for replay protection",
    )
    # T020: Emitter IVA condition for invoice type resolution
    emitter_condicion_iva = models.PositiveSmallIntegerField(
        choices=CondicionIVA.choices,
        default=CondicionIVA.RESPONSABLE_INSCRIPTO,
        help_text="Emitter IVA condition for invoice type resolution",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "facturacion_arcacredential"
        verbose_name = "ARCA Credential"
        verbose_name_plural = "ARCA Credentials"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "is_production"],
                name="uq_arca_credential_tenant_env",
            ),
        ]

    def __str__(self) -> str:
        env = "PROD" if self.is_production else "HOMO"
        return f"ARCA {env} - CUIT {self.cuit_holder}"


# ============================================================
# PuntoDeVenta
# ============================================================


class PuntoDeVenta(TenantBoundModel):
    """
    Registered point of sale for electronic invoicing.

    Attributes:
        numero: PtoVta number (1-99999).
        tipo: Emission type (electronic/manual).
        description: Human-readable label.
        is_active: Active flag.
        fecha_alta: ARCA registration date.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="puntos_de_venta",
    )
    numero = models.PositiveIntegerField(
        help_text="Punto de venta number (1-99999)",
    )
    tipo = models.CharField(
        max_length=20,
        choices=PuntoDeVentaTipo.choices,
        default=PuntoDeVentaTipo.ELECTRONIC,
        help_text="Emission type",
    )
    description = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Human-readable label",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Active flag",
    )
    fecha_alta = models.DateField(
        null=True,
        blank=True,
        help_text="ARCA registration date",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "facturacion_puntodeventa"
        ordering = ["numero"]
        verbose_name = "Punto de Venta"
        verbose_name_plural = "Puntos de Venta"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "numero"],
                name="uq_punto_venta_tenant",
            ),
            models.CheckConstraint(
                check=models.Q(numero__gte=1, numero__lte=99999),
                name="ck_punto_venta_range",
            ),
        ]

    def __str__(self) -> str:
        return f"PtoVta {self.numero:05d}"


# ============================================================
# Comprobante
# ============================================================


class Comprobante(TenantBoundModel):
    """
    Immutable fiscal document ledger entry.

    Central entity for ARCA electronic invoicing. Authorized and observed
    comprobantes are immutable — corrections via Nota de Crédito only.

    Immutability Rules:
        - save() raises ValueError for AUTORIZADO/OBSERVADO records.
        - delete() always raises ValueError — comprobantes are never deleted.
        - DRAFT and RECHAZADO are mutable (allow edits and retry).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.RESTRICT,
        related_name="comprobantes",
    )
    punto_venta = models.ForeignKey(
        PuntoDeVenta,
        on_delete=models.RESTRICT,
        related_name="comprobantes",
        help_text="Associated punto de venta",
    )
    cbte_tipo = models.PositiveSmallIntegerField(
        help_text="CbteTipo code (1,2,3,6,7,8,11,12,13,51,52,53)",
    )
    cbte_nro = models.PositiveBigIntegerField(
        help_text="Sequential number per PtoVta+CbteTipo",
    )
    concepto = models.PositiveSmallIntegerField(
        default=1,
        help_text="1=Productos, 2=Servicios, 3=Ambos",
    )
    doc_tipo = models.PositiveSmallIntegerField(
        help_text="Buyer document type (DocTipo code)",
    )
    doc_nro = models.CharField(
        max_length=20,
        help_text="Buyer document number",
    )
    cbte_fch = models.DateField(
        help_text="Invoice date",
    )
    fch_serv_desde = models.DateField(
        null=True,
        blank=True,
        help_text="Service start date (Concepto 2,3)",
    )
    fch_serv_hasta = models.DateField(
        null=True,
        blank=True,
        help_text="Service end date (Concepto 2,3)",
    )
    fch_vto_pago = models.DateField(
        null=True,
        blank=True,
        help_text="Payment due date (Concepto 2,3)",
    )

    # Amount fields — all DecimalField(17,3) per constitution
    imp_total = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Total amount",
    )
    imp_neto = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Net taxable amount",
    )
    imp_iva = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Total IVA",
    )
    imp_trib = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Other taxes total",
    )
    imp_op_ex = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="IVA-exempt amount",
    )
    imp_tot_conc = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Non-taxable conceptual amount",
    )

    # Currency
    mon_id = models.CharField(
        max_length=3,
        default="PES",
        help_text="Currency code (PES=ARS)",
    )
    mon_cotiz = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=Decimal("1.000000"),
        help_text="Exchange rate",
    )

    # Emitter / Receptor info
    emitter_cuit = models.CharField(
        max_length=11,
        help_text="Emitter CUIT (11 digits)",
    )
    emitter_condicion_iva = models.PositiveSmallIntegerField(
        help_text="Emitter CondicionIVA code",
    )
    receptor_condicion_iva = models.PositiveSmallIntegerField(
        help_text="Buyer CondicionIVA code",
    )

    # Cross-module links (T018-T019)
    sale_order = models.OneToOneField(
        "gravitea_ventas.SaleOrder",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="comprobante_direct",
        help_text="Originating sale order (null for standalone invoices)",
    )
    customer = models.ForeignKey(
        "gravitea_ventas.Customer",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="comprobantes",
        help_text="Customer (from sale order or standalone)",
    )

    # ARCA authorization
    cae = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        db_index=True,
        help_text="14-digit CAE from ARCA",
    )
    cae_fch_vto = models.DateField(
        null=True,
        blank=True,
        help_text="CAE expiration date",
    )
    caea = models.ForeignKey(
        "CAEA",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="comprobantes",
        help_text="CAEA reference (offline mode)",
    )

    # Lifecycle
    status = models.CharField(
        max_length=12,
        choices=ComprobanteStatus.choices,
        default=ComprobanteStatus.DRAFT,
        db_index=True,
        help_text="Comprobante lifecycle status",
    )

    # ARCA response snapshots
    arca_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Full ARCA response snapshot",
    )
    arca_errors = models.JSONField(
        null=True,
        blank=True,
        help_text="ARCA error/observation details",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "facturacion_comprobante"
        ordering = ["-created_at"]
        verbose_name = "Comprobante"
        verbose_name_plural = "Comprobantes"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "punto_venta", "cbte_tipo", "cbte_nro"],
                name="uq_comprobante_fiscal",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tenant_id", "status"],
                name="idx_comprobante_tenant_status",
            ),
            models.Index(
                fields=["tenant_id", "cbte_fch"],
                name="idx_comprobante_tenant_date",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Cbte {self.cbte_tipo}-{self.punto_venta_id and self.punto_venta.numero:05d}-"
            f"{self.cbte_nro:08d} [{self.status}]"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Enforce immutability for authorized/observed comprobantes.

        DRAFT and RECHAZADO records are mutable.
        AUTORIZADO and OBSERVADO records cannot be modified.
        Also validates sale_order↔customer consistency (T021).
        """
        if self.pk:
            try:
                existing = Comprobante.all_objects.get(pk=self.pk)
            except Comprobante.DoesNotExist:
                existing = None
            if existing and existing.status in IMMUTABLE_STATUSES:
                raise ValueError(
                    f"Cannot modify comprobante with status '{existing.status}'. "
                    f"Authorized/Observed comprobantes are immutable. "
                    f"Use Nota de Crédito for corrections."
                )

        # T021: If sale_order is set, customer must match sale_order.customer
        if self.sale_order_id and self.customer_id:
            from apps.ventas.models import SaleOrder

            so_customer_id = (
                SaleOrder.all_objects.filter(pk=self.sale_order_id)
                .values_list("customer_id", flat=True)
                .first()
            )
            if so_customer_id and so_customer_id != self.customer_id:
                raise ValueError(
                    "Comprobante customer must match the sale order's customer."
                )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """Comprobantes are never deleted — fiscal records are permanent."""
        raise ValueError(
            "Comprobantes cannot be deleted. "
            "Fiscal records are permanent per ARCA regulations. "
            "Use Nota de Crédito for corrections."
        )


# ============================================================
# AlicIva
# ============================================================


class AlicIva(models.Model):
    """
    IVA rate breakdown entry for a comprobante.

    No tenant_id — inherits tenant scope from parent Comprobante via FK.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    comprobante = models.ForeignKey(
        Comprobante,
        on_delete=models.RESTRICT,
        related_name="aliciva_set",
        help_text="Parent comprobante",
    )
    iva_id = models.PositiveSmallIntegerField(
        help_text="ARCA IVA code (3=0%, 4=10.5%, 5=21%, 6=27%, 8=5%, 9=2.5%)",
    )
    base_imp = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Taxable base amount",
    )
    importe = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="IVA amount",
    )

    class Meta:
        db_table = "facturacion_aliciva"
        verbose_name = "Alícuota IVA"
        verbose_name_plural = "Alícuotas IVA"

    def __str__(self) -> str:
        return f"IVA {self.iva_id}: base={self.base_imp} imp={self.importe}"


# ============================================================
# Tributo
# ============================================================


class Tributo(models.Model):
    """
    Other tax/tribute entry for a comprobante (e.g., Ingresos Brutos).

    No tenant_id — inherits tenant scope from parent Comprobante via FK.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    comprobante = models.ForeignKey(
        Comprobante,
        on_delete=models.RESTRICT,
        related_name="tributo_set",
        help_text="Parent comprobante",
    )
    tributo_id = models.PositiveSmallIntegerField(
        help_text="ARCA tribute type code",
    )
    desc = models.CharField(
        max_length=100,
        help_text="Tax description",
    )
    base_imp = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Taxable base",
    )
    alic = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Tax rate (%)",
    )
    importe = models.DecimalField(
        max_digits=17,
        decimal_places=3,
        help_text="Tax amount",
    )

    class Meta:
        db_table = "facturacion_tributo"
        verbose_name = "Tributo"
        verbose_name_plural = "Tributos"

    def __str__(self) -> str:
        return f"Tributo {self.tributo_id}: {self.desc} = {self.importe}"


# ============================================================
# CbteAsoc
# ============================================================


class CbteAsoc(models.Model):
    """
    Associated comprobante reference for Nota de Crédito/Débito.

    No tenant_id — inherits tenant scope from parent Comprobante via FK.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    comprobante = models.ForeignKey(
        Comprobante,
        on_delete=models.RESTRICT,
        related_name="cbteasoc_set",
        help_text="Parent NC/ND comprobante",
    )
    tipo = models.PositiveSmallIntegerField(
        help_text="Associated CbteTipo code",
    )
    pto_vta = models.PositiveIntegerField(
        help_text="Associated PtoVta number",
    )
    nro = models.PositiveBigIntegerField(
        help_text="Associated CbteNro",
    )
    cuit = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        help_text="Associated emitter CUIT (optional)",
    )

    class Meta:
        db_table = "facturacion_cbteasoc"
        verbose_name = "Comprobante Asociado"
        verbose_name_plural = "Comprobantes Asociados"

    def __str__(self) -> str:
        return f"Asoc {self.tipo}-{self.pto_vta:05d}-{self.nro:08d}"


# ============================================================
# CAEA
# ============================================================


class CAEA(TenantBoundModel):
    """
    Pre-authorized offline code for biweekly periods.

    Used for CAEA offline invoicing mode where comprobantes are
    issued locally and batch-reported to ARCA within deadline.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.RESTRICT,
        related_name="caeas",
    )
    punto_venta = models.ForeignKey(
        PuntoDeVenta,
        on_delete=models.RESTRICT,
        related_name="caeas",
        help_text="Associated punto de venta",
    )
    caea_code = models.CharField(
        max_length=14,
        unique=True,
        help_text="14-digit CAEA from ARCA",
    )
    periodo = models.CharField(
        max_length=6,
        help_text="Period YYYYMM",
    )
    orden = models.PositiveSmallIntegerField(
        help_text="1=first quincena, 2=second",
    )
    fch_vig_desde = models.DateField(
        help_text="Validity start date",
    )
    fch_vig_hasta = models.DateField(
        help_text="Validity end date",
    )
    fch_tope_inf = models.DateField(
        help_text="Reporting deadline",
    )
    status = models.CharField(
        max_length=20,
        choices=CAEAStatus.choices,
        default=CAEAStatus.ACTIVE,
        db_index=True,
        help_text="CAEA lifecycle status",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantBoundManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = "facturacion_caea"
        ordering = ["-periodo", "-orden"]
        verbose_name = "CAEA"
        verbose_name_plural = "CAEAs"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "punto_venta", "periodo", "orden"],
                name="uq_caea_period",
            ),
        ]

    def __str__(self) -> str:
        return f"CAEA {self.caea_code} ({self.periodo}-Q{self.orden})"
