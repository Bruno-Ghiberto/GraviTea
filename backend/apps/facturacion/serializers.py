"""
Facturacion serializers for Gravitea ERP.

Provides serializers for electronic invoicing entities: PuntoDeVenta,
ARCACredential, and Comprobante management.
"""

from __future__ import annotations

import logging as _logging
import re
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

try:
    from gravitea_rust import validate_cuit as _rust_validate_cuit  # type: ignore[import]

    _USE_RUST_COMPUTE = True
except (ImportError, OSError):
    _USE_RUST_COMPUTE = False
    _logging.getLogger(__name__).warning(
        "gravitea_rust compute not available — using Python fallback"
    )

from .constants import (
    CBTES_ASOC_REQUIRED_CODES,
    FACTURA_CODES,
    AlicIvaId,
    CbteTipo,
    Concepto,
    CondicionIVA,
    DocTipo,
)
from .models import (
    CAEA,
    AlicIva,
    ARCACredential,
    CbteAsoc,
    Comprobante,
    PuntoDeVenta,
    Tributo,
)
from .validators import (
    validate_cbtes_asoc,
    validate_importes,
    validate_iva_breakdown,
    validate_service_dates,
    validate_tributos,
)


# ============================================================
# CUIT Validation
# ============================================================

_CUIT_PATTERN = re.compile(r"^\d{11}$")
_CUIT_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def _validate_cuit(value: str) -> str:
    """Validate CUIT format (11 digits) and check digit."""
    if _USE_RUST_COMPUTE:
        try:
            _rust_validate_cuit(value)
            return value
        except RuntimeError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    if not _CUIT_PATTERN.match(value):
        raise serializers.ValidationError(
            "CUIT must be exactly 11 digits with no hyphens."
        )
    digits = [int(d) for d in value]
    total = sum(d * w for d, w in zip(digits[:10], _CUIT_WEIGHTS))
    check = 11 - (total % 11)
    if check == 11:
        check = 0
    elif check == 10:
        check = 9
    if digits[10] != check:
        raise serializers.ValidationError("Invalid CUIT check digit.")
    return value


# ============================================================
# PuntoDeVenta
# ============================================================


class PuntoDeVentaSerializer(serializers.ModelSerializer):
    """
    PuntoDeVenta serializer for read and write operations.

    Validates numero uniqueness within tenant and injects tenant
    from request context on create.
    """

    class Meta:
        model = PuntoDeVenta
        fields = [
            "id",
            "numero",
            "tipo",
            "description",
            "is_active",
            "fecha_alta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_numero(self, value: int) -> int:
        """Validate numero uniqueness within tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            queryset = PuntoDeVenta.objects.filter(tenant=tenant, numero=value)

            # Exclude current instance for updates
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                raise serializers.ValidationError(
                    "A punto de venta with this number already exists."
                )
        return value

    def create(self, validated_data: dict) -> PuntoDeVenta:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


# ============================================================
# ARCACredential
# ============================================================


class ARCACredentialWriteSerializer(serializers.ModelSerializer):
    """
    ARCACredential serializer for create/update operations.

    Validates PEM format, CUIT check digit, and environment
    uniqueness per tenant.
    """

    class Meta:
        model = ARCACredential
        fields = [
            "cuit_holder",
            "cuit_represented",
            "certificate_pem",
            "private_key_pem",
            "is_production",
        ]

    def validate_cuit_holder(self, value: str) -> str:
        """Validate CUIT holder format and check digit."""
        return _validate_cuit(value)

    def validate_cuit_represented(self, value: str | None) -> str | None:
        """Validate represented CUIT if provided."""
        if value:
            return _validate_cuit(value)
        return value

    def validate_certificate_pem(self, value: str) -> str:
        """Validate PEM certificate format."""
        stripped = value.strip()
        if not stripped.startswith("-----BEGIN CERTIFICATE-----"):
            raise serializers.ValidationError(
                "Certificate must be in PEM format "
                "(begin with -----BEGIN CERTIFICATE-----)."
            )
        if not stripped.endswith("-----END CERTIFICATE-----"):
            raise serializers.ValidationError(
                "Certificate must be in PEM format "
                "(end with -----END CERTIFICATE-----)."
            )
        return stripped

    def validate_private_key_pem(self, value: str) -> str:
        """Validate PEM private key format."""
        stripped = value.strip()
        # Accept both RSA and generic PRIVATE KEY headers
        valid_starts = (
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----",
        )
        valid_ends = (
            "-----END RSA PRIVATE KEY-----",
            "-----END PRIVATE KEY-----",
        )
        if not any(stripped.startswith(s) for s in valid_starts):
            raise serializers.ValidationError(
                "Private key must be in PEM format."
            )
        if not any(stripped.endswith(s) for s in valid_ends):
            raise serializers.ValidationError(
                "Private key must be in PEM format."
            )
        return stripped

    def validate(self, data: dict) -> dict:
        """Validate environment uniqueness per tenant."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            tenant = request.user.tenant
            is_production = data.get("is_production", False)
            queryset = ARCACredential.objects.filter(
                tenant=tenant, is_production=is_production
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                env = "production" if is_production else "homologacion"
                raise serializers.ValidationError(
                    f"A credential for {env} environment already exists."
                )
        return data

    def create(self, validated_data: dict) -> ARCACredential:
        """Inject tenant from request context."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["tenant"] = request.user.tenant
        return super().create(validated_data)


class ARCACredentialReadSerializer(serializers.ModelSerializer):
    """
    ARCACredential serializer for read operations.

    Redacts private_key_pem — never exposes secrets over the API.
    """

    class Meta:
        model = ARCACredential
        fields = [
            "id",
            "cuit_holder",
            "cuit_represented",
            "is_production",
            "is_active",
            "certificate_expires_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


# ============================================================
# Comprobante (nested child serializers)
# ============================================================


class AlicIvaReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for IVA rate breakdown entries."""

    class Meta:
        model = AlicIva
        fields = ["id", "iva_id", "base_imp", "importe"]
        read_only_fields = fields


class TributoReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for other tax entries."""

    class Meta:
        model = Tributo
        fields = ["id", "tributo_id", "desc", "base_imp", "alic", "importe"]
        read_only_fields = fields


class CbteAsocReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for associated comprobante references."""

    class Meta:
        model = CbteAsoc
        fields = ["id", "tipo", "pto_vta", "nro", "cuit"]
        read_only_fields = fields


class ComprobanteReadSerializer(serializers.ModelSerializer):
    """
    Comprobante serializer for read operations.

    Includes nested AlicIva, Tributo, and CbteAsoc entries.
    Exposes a computed qr_url for authorized comprobantes.
    Formats amounts to 2 decimal places for display.
    """

    aliciva_set = AlicIvaReadSerializer(many=True, read_only=True)
    tributo_set = TributoReadSerializer(many=True, read_only=True)
    cbteasoc_set = CbteAsocReadSerializer(many=True, read_only=True)
    punto_venta_numero = serializers.IntegerField(
        source="punto_venta.numero", read_only=True
    )
    sale_order_id = serializers.UUIDField(
        source="sale_order.id", read_only=True, default=None,
    )
    customer_name = serializers.CharField(
        source="customer.razon_social", read_only=True, default=None,
    )
    qr_url = serializers.SerializerMethodField()

    # Display amounts with 2 decimal places
    imp_total = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)
    imp_neto = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)
    imp_iva = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)
    imp_trib = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)
    imp_op_ex = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)
    imp_tot_conc = serializers.DecimalField(max_digits=17, decimal_places=2, coerce_to_string=True)

    class Meta:
        model = Comprobante
        fields = [
            "id",
            "punto_venta",
            "punto_venta_numero",
            "cbte_tipo",
            "cbte_nro",
            "concepto",
            "doc_tipo",
            "doc_nro",
            "cbte_fch",
            "fch_serv_desde",
            "fch_serv_hasta",
            "fch_vto_pago",
            "imp_total",
            "imp_neto",
            "imp_iva",
            "imp_trib",
            "imp_op_ex",
            "imp_tot_conc",
            "mon_id",
            "mon_cotiz",
            "emitter_cuit",
            "emitter_condicion_iva",
            "receptor_condicion_iva",
            "cae",
            "cae_fch_vto",
            "caea",
            "status",
            "arca_errors",
            "created_at",
            "sale_order_id",
            "customer_name",
            "qr_url",
            "aliciva_set",
            "tributo_set",
            "cbteasoc_set",
        ]
        read_only_fields = fields

    def get_qr_url(self, obj: Comprobante) -> str | None:
        """Return QR URL for authorized comprobantes only."""
        if obj.status in ("AUTORIZADO", "OBSERVADO") and obj.cae:
            try:
                from .qr import generate_fiscal_qr_data

                return generate_fiscal_qr_data(obj)
            except (ValueError, Exception):
                return None
        return None


# ============================================================
# Comprobante Emit (write serializer for CAE issuance)
# ============================================================


class AlicIvaEmitSerializer(serializers.Serializer):
    """Nested writable serializer for IVA rate breakdown entries."""

    iva_id = serializers.ChoiceField(
        choices=AlicIvaId.choices,
        help_text="ARCA IVA code (3=0%, 4=10.5%, 5=21%, 6=27%, 8=5%, 9=2.5%)",
    )
    base_imp = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Taxable base amount",
    )
    importe = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="IVA amount",
    )


class TributoEmitSerializer(serializers.Serializer):
    """Nested writable serializer for other tax entries."""

    tributo_id = serializers.IntegerField(
        min_value=1,
        help_text="ARCA tributo code",
    )
    desc = serializers.CharField(
        max_length=255,
        help_text="Tributo description",
    )
    base_imp = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Taxable base amount",
    )
    alic = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        help_text="Tax rate percentage",
    )
    importe = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Tributo amount",
    )


class CbteAsocEmitSerializer(serializers.Serializer):
    """Nested writable serializer for associated comprobante references."""

    tipo = serializers.ChoiceField(
        choices=CbteTipo.choices,
        help_text="Associated CbteTipo code",
    )
    pto_vta = serializers.IntegerField(
        min_value=1,
        max_value=99999,
        help_text="Associated punto de venta number",
    )
    nro = serializers.IntegerField(
        min_value=1,
        help_text="Associated comprobante number",
    )
    cuit = serializers.CharField(
        max_length=11,
        required=False,
        help_text="Associated CUIT (defaults to emitter CUIT)",
    )

    def validate_cuit(self, value: str) -> str:
        """Validate CUIT if provided."""
        if value:
            return _validate_cuit(value)
        return value


class ComprobanteEmitirSerializer(serializers.Serializer):
    """
    Serializer for CAE invoice issuance (FECAESolicitar).

    Accepts comprobante data with nested AlicIva, Tributo, and CbteAsoc
    entries. Runs all ARCA validators (amounts, IVA breakdown, service
    dates, tributos, CbtesAsoc type compatibility) in the validate() method.

    This is a plain Serializer (not ModelSerializer) because the service
    layer handles Comprobante creation after ARCA authorization.
    """

    # Punto de venta
    punto_venta = serializers.UUIDField(
        help_text="UUID of the PuntoDeVenta to issue against",
    )

    # Comprobante header
    cbte_tipo = serializers.ChoiceField(
        choices=CbteTipo.choices,
        help_text="CbteTipo code",
    )
    concepto = serializers.ChoiceField(
        choices=Concepto.choices,
        help_text="1=Productos, 2=Servicios, 3=Ambos",
    )
    doc_tipo = serializers.ChoiceField(
        choices=DocTipo.choices,
        help_text="Buyer document type code",
    )
    doc_nro = serializers.CharField(
        max_length=20,
        help_text="Buyer document number",
    )
    cbte_fch = serializers.DateField(
        help_text="Invoice date (YYYY-MM-DD)",
    )

    # Service dates — conditional on Concepto
    fch_serv_desde = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Service start date (required for Concepto 2,3)",
    )
    fch_serv_hasta = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Service end date (required for Concepto 2,3)",
    )
    fch_vto_pago = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Payment due date (required for Concepto 2,3)",
    )

    # Amounts — DECIMAL(17,3)
    imp_total = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Total amount",
    )
    imp_neto = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        help_text="Net taxable amount",
    )
    imp_iva = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        default=Decimal("0"),
        help_text="Total IVA amount",
    )
    imp_trib = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        default=Decimal("0"),
        help_text="Other taxes total",
    )
    imp_op_ex = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        default=Decimal("0"),
        help_text="IVA-exempt amount",
    )
    imp_tot_conc = serializers.DecimalField(
        max_digits=17,
        decimal_places=3,
        min_value=Decimal("0"),
        default=Decimal("0"),
        help_text="Non-taxable conceptual amount",
    )

    # Currency
    mon_id = serializers.CharField(
        max_length=3,
        default="PES",
        help_text="Currency code (PES=ARS)",
    )
    mon_cotiz = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        min_value=Decimal("0.000001"),
        default=Decimal("1"),
        help_text="Exchange rate",
    )

    # Emitter / Receptor
    emitter_condicion_iva = serializers.ChoiceField(
        choices=CondicionIVA.choices,
        help_text="Emitter IVA condition code",
    )
    receptor_condicion_iva = serializers.ChoiceField(
        choices=CondicionIVA.choices,
        help_text="Buyer IVA condition code",
    )

    # Nested arrays
    alic_iva = AlicIvaEmitSerializer(
        many=True,
        required=False,
        default=list,
        help_text="IVA rate breakdown entries",
    )
    tributos = TributoEmitSerializer(
        many=True,
        required=False,
        default=list,
        help_text="Other tax entries",
    )
    cbtes_asoc = CbteAsocEmitSerializer(
        many=True,
        required=False,
        default=list,
        help_text="Associated comprobante references (NC/ND)",
    )

    def validate_punto_venta(self, value: str) -> str:
        """Verify PuntoDeVenta exists and belongs to tenant."""
        request = self.context.get("request")
        if not request:
            return value
        tenant = request.user.tenant
        if not PuntoDeVenta.objects.filter(
            id=value, tenant=tenant, is_active=True
        ).exists():
            raise serializers.ValidationError(
                "Punto de venta not found or inactive."
            )
        return value

    def validate(self, data: dict) -> dict:
        """
        Run all ARCA cross-field validators.

        Calls validate_importes (FR-007), validate_iva_breakdown (FR-008),
        validate_service_dates (FR-009), validate_tributos (FR-010),
        and validate_cbtes_asoc (US6).

        Django ValidationErrors from validators are translated to DRF
        ValidationErrors for consistent API responses.
        """
        errors = {}

        # FR-007: Amount equation
        try:
            validate_importes(
                imp_total=data["imp_total"],
                imp_neto=data["imp_neto"],
                imp_iva=data["imp_iva"],
                imp_trib=data["imp_trib"],
                imp_op_ex=data["imp_op_ex"],
                imp_tot_conc=data["imp_tot_conc"],
            )
        except DjangoValidationError as exc:
            errors["imp_total"] = exc.messages

        # FR-008: IVA breakdown
        try:
            validate_iva_breakdown(
                cbte_tipo=data["cbte_tipo"],
                aliciva_list=data.get("alic_iva", []),
                imp_iva=data["imp_iva"],
                imp_neto=data["imp_neto"],
            )
        except DjangoValidationError as exc:
            errors["alic_iva"] = exc.messages

        # FR-009: Service dates
        try:
            validate_service_dates(
                concepto=data["concepto"],
                fch_serv_desde=data.get("fch_serv_desde"),
                fch_serv_hasta=data.get("fch_serv_hasta"),
                fch_vto_pago=data.get("fch_vto_pago"),
            )
        except DjangoValidationError as exc:
            errors["fch_serv_desde"] = exc.messages

        # FR-010: Tributos
        try:
            validate_tributos(
                imp_trib=data["imp_trib"],
                tributo_list=data.get("tributos", []),
            )
        except DjangoValidationError as exc:
            errors["tributos"] = exc.messages

        # US6: CbtesAsoc — forbidden for Facturas, required for NC/ND
        cbtes_asoc_list = data.get("cbtes_asoc", [])
        if data["cbte_tipo"] in FACTURA_CODES and cbtes_asoc_list:
            errors["cbtes_asoc"] = [
                "Facturas (A/B/C/M) must not include associated comprobantes."
            ]
        else:
            try:
                warnings = validate_cbtes_asoc(
                    cbte_tipo=data["cbte_tipo"],
                    cbtes_asoc_list=cbtes_asoc_list,
                )
                if warnings:
                    data["_cbtes_asoc_warnings"] = warnings
            except DjangoValidationError as exc:
                errors["cbtes_asoc"] = exc.messages

        if errors:
            raise serializers.ValidationError(errors)

        return data


# ============================================================
# CAEA Serializers
# ============================================================


class CAEAReadSerializer(serializers.ModelSerializer):
    """Read-only serializer for CAEA objects."""

    punto_venta_numero = serializers.IntegerField(
        source="punto_venta.numero", read_only=True
    )

    class Meta:
        model = CAEA
        fields = [
            "id",
            "punto_venta",
            "punto_venta_numero",
            "caea_code",
            "periodo",
            "orden",
            "fch_vig_desde",
            "fch_vig_hasta",
            "fch_tope_inf",
            "status",
            "created_at",
        ]
        read_only_fields = fields


class CAEASolicitarSerializer(serializers.Serializer):
    """Write serializer for requesting a new CAEA from ARCA."""

    punto_venta = serializers.UUIDField(
        help_text="UUID of the PuntoDeVenta to request CAEA for.",
    )
    periodo = serializers.RegexField(
        regex=r"^\d{6}$",
        help_text="Period in YYYYMM format (e.g. '202602').",
    )
    orden = serializers.ChoiceField(
        choices=[(1, "Primera quincena"), (2, "Segunda quincena")],
        help_text="1 = first quincena, 2 = second quincena.",
    )

    def validate_punto_venta(self, value: str) -> str:
        """Validate that the PuntoDeVenta exists and is active."""
        try:
            pto_vta = PuntoDeVenta.objects.get(pk=value)
        except PuntoDeVenta.DoesNotExist:
            raise serializers.ValidationError("Punto de venta not found.")
        if not pto_vta.is_active:
            raise serializers.ValidationError("Punto de venta is inactive.")
        return value

    def validate_periodo(self, value: str) -> str:
        """Validate YYYYMM period format has valid month."""
        month = int(value[4:6])
        if not 1 <= month <= 12:
            raise serializers.ValidationError(
                "Invalid month in periodo. Must be 01-12."
            )
        return value
