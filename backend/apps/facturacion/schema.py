"""
drf-spectacular schema definitions for facturacion views.

Provides comprehensive OpenAPI schema documentation for all electronic
invoicing endpoints using @extend_schema and @extend_schema_view decorators.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

from .serializers import (
    ARCACredentialReadSerializer,
    ARCACredentialWriteSerializer,
    ComprobanteReadSerializer,
    PuntoDeVentaSerializer,
)

# ============================================================================
# RFC 7807 Error Response Serializers
# ============================================================================


class FacturacionErrorSerializer(serializers.Serializer):
    """RFC 7807 Problem Details for HTTP APIs error response (facturacion-specific)."""

    type = serializers.CharField(
        help_text="URI reference identifying the problem type",
        default="about:blank",
    )
    title = serializers.CharField(help_text="Short, human-readable summary")
    status = serializers.IntegerField(help_text="HTTP status code")
    detail = serializers.CharField(
        help_text="Human-readable explanation", required=False
    )
    instance = serializers.CharField(
        help_text="URI reference identifying specific occurrence",
        required=False,
    )


class FacturacionValidationErrorSerializer(serializers.Serializer):
    """Validation error response (400 Bad Request) for facturacion module."""

    detail = serializers.CharField(help_text="Error description")
    field_errors = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        help_text="Field-specific validation errors",
        required=False,
    )


# ============================================================================
# PuntoDeVenta ViewSet Schema
# ============================================================================

punto_de_venta_list_schema = extend_schema(
    summary="List puntos de venta",
    description="""
    List puntos de venta (points of sale) with cursor pagination.

    **Filters:**
    - numero: Filter by punto de venta number
    - tipo: Filter by type (CAE or CAEA)
    - is_active: Filter by active status
    """,
    parameters=[
        OpenApiParameter(
            name="numero",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by punto de venta number",
        ),
        OpenApiParameter(
            name="tipo",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by type",
            enum=["CAE", "CAEA"],
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active status",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedPuntoDeVentaList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": PuntoDeVentaSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=FacturacionErrorSerializer,
            description="Authentication required",
        ),
    },
    tags=["facturacion-puntos-de-venta"],
)

punto_de_venta_create_schema = extend_schema(
    summary="Create punto de venta",
    description="""
    Register a new punto de venta (point of sale).

    **Constraints:**
    - Number must be between 1 and 99999.
    - Number must be unique per tenant.
    - Type determines CAE vs CAEA authorization mode.
    """,
    request=PuntoDeVentaSerializer,
    responses={
        201: PuntoDeVentaSerializer,
        400: FacturacionValidationErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="CAE Punto de Venta",
            value={
                "numero": 1,
                "tipo": "CAE",
                "descripcion": "Punto de venta principal",
            },
            request_only=True,
        ),
        OpenApiExample(
            name="CAEA Punto de Venta",
            value={
                "numero": 2,
                "tipo": "CAEA",
                "descripcion": "Punto de venta offline",
            },
            request_only=True,
        ),
    ],
    tags=["facturacion-puntos-de-venta"],
)

punto_de_venta_retrieve_schema = extend_schema(
    summary="Get punto de venta details",
    description="Retrieve punto de venta details.",
    responses={
        200: PuntoDeVentaSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-puntos-de-venta"],
)

punto_de_venta_update_schema = extend_schema(
    summary="Update punto de venta",
    description="Update punto de venta description or active status.",
    request=PuntoDeVentaSerializer,
    responses={
        200: PuntoDeVentaSerializer,
        400: FacturacionValidationErrorSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-puntos-de-venta"],
)

punto_de_venta_partial_update_schema = extend_schema(
    summary="Partial update punto de venta",
    description="Partially update punto de venta fields.",
    request=PuntoDeVentaSerializer,
    responses={
        200: PuntoDeVentaSerializer,
        400: FacturacionValidationErrorSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-puntos-de-venta"],
)

punto_de_venta_destroy_schema = extend_schema(
    summary="Deactivate punto de venta",
    description="Soft-deactivate punto de venta by setting is_active=False.",
    responses={
        204: None,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-puntos-de-venta"],
)

PuntoDeVentaViewSetSchema = extend_schema_view(
    list=punto_de_venta_list_schema,
    create=punto_de_venta_create_schema,
    retrieve=punto_de_venta_retrieve_schema,
    update=punto_de_venta_update_schema,
    partial_update=punto_de_venta_partial_update_schema,
    destroy=punto_de_venta_destroy_schema,
)

# ============================================================================
# ARCACredential ViewSet Schema
# ============================================================================

credential_list_schema = extend_schema(
    summary="List ARCA credentials",
    description="""
    List ARCA (ex-AFIP) credentials with cursor pagination.

    **Security:** Private keys and certificate PEM content are never
    returned in list responses — only metadata and expiry information.
    """,
    parameters=[
        OpenApiParameter(
            name="is_production",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by environment (true=production, false=homologacion)",
        ),
        OpenApiParameter(
            name="is_active",
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description="Filter by active status",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedARCACredentialList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": ARCACredentialReadSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=FacturacionErrorSerializer,
            description="Authentication required",
        ),
    },
    tags=["facturacion-credentials"],
)

credential_create_schema = extend_schema(
    summary="Create ARCA credential",
    description="""
    Register a new ARCA credential with certificate and private key.

    **Security:**
    - Private key is encrypted at rest using AES-256-GCM.
    - Certificate is stored as PEM for WSAA authentication.
    - Only one active credential per environment per tenant is recommended.
    """,
    request=ARCACredentialWriteSerializer,
    responses={
        201: ARCACredentialReadSerializer,
        400: FacturacionValidationErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    examples=[
        OpenApiExample(
            name="Homologacion Credential",
            value={
                "cuit": "20123456789",
                "certificate_pem": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
                "private_key_pem": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
                "is_production": False,
            },
            request_only=True,
        ),
    ],
    tags=["facturacion-credentials"],
)

credential_retrieve_schema = extend_schema(
    summary="Get ARCA credential details",
    description="Retrieve credential metadata. Private key is never returned.",
    responses={
        200: ARCACredentialReadSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-credentials"],
)

credential_update_schema = extend_schema(
    summary="Update ARCA credential",
    description="""
    Update credential for certificate rotation.

    **Use case:** Rotate certificates before expiration.
    Supply new certificate_pem and private_key_pem.
    """,
    request=ARCACredentialWriteSerializer,
    responses={
        200: ARCACredentialReadSerializer,
        400: FacturacionValidationErrorSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-credentials"],
)

credential_partial_update_schema = extend_schema(
    summary="Partial update ARCA credential",
    description="Partially update credential fields (e.g. certificate rotation).",
    request=ARCACredentialWriteSerializer,
    responses={
        200: ARCACredentialReadSerializer,
        400: FacturacionValidationErrorSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-credentials"],
)

credential_destroy_schema = extend_schema(
    summary="Deactivate ARCA credential",
    description="""
    Soft-deactivate credential by setting is_active=False.

    **Warning:** Deactivating a credential will prevent WSAA authentication
    for this environment until a new credential is activated.
    """,
    responses={
        204: None,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-credentials"],
)

ARCACredentialViewSetSchema = extend_schema_view(
    list=credential_list_schema,
    create=credential_create_schema,
    retrieve=credential_retrieve_schema,
    update=credential_update_schema,
    partial_update=credential_partial_update_schema,
    destroy=credential_destroy_schema,
)

# ============================================================================
# Comprobante ViewSet Schema (for future ComprobanteViewSet)
# ============================================================================

comprobante_list_schema = extend_schema(
    summary="List comprobantes",
    description="""
    List electronic comprobantes with cursor pagination and filtering.

    **Immutability:** Authorized comprobantes (AUTORIZADO, OBSERVADO) cannot
    be modified or deleted. They are fiscal records.

    **Filters:**
    - cbte_tipo: Filter by CbteTipo code
    - punto_venta: Filter by punto de venta ID
    - status: Filter by status (BORRADOR, VALIDANDO, AUTORIZADO, RECHAZADO, OBSERVADO)
    - fecha_from: Filter by fecha >= date
    - fecha_to: Filter by fecha <= date
    """,
    parameters=[
        OpenApiParameter(
            name="cbte_tipo",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Filter by CbteTipo code (e.g. 1=Factura A, 6=Factura B)",
        ),
        OpenApiParameter(
            name="punto_venta",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            description="Filter by punto de venta ID",
        ),
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by comprobante status",
            enum=["BORRADOR", "VALIDANDO", "AUTORIZADO", "RECHAZADO", "OBSERVADO"],
        ),
        OpenApiParameter(
            name="fecha_from",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Comprobante date >= this date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="fecha_to",
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            description="Comprobante date <= this date (YYYY-MM-DD)",
        ),
        OpenApiParameter(
            name="cursor",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Pagination cursor",
        ),
    ],
    responses={
        200: inline_serializer(
            name="PaginatedComprobanteList",
            fields={
                "next": serializers.URLField(allow_null=True),
                "previous": serializers.URLField(allow_null=True),
                "results": ComprobanteReadSerializer(many=True),
            },
        ),
        401: OpenApiResponse(
            response=FacturacionErrorSerializer,
            description="Authentication required",
        ),
    },
    tags=["facturacion-comprobantes"],
)

comprobante_retrieve_schema = extend_schema(
    summary="Get comprobante details",
    description="""
    Retrieve comprobante with nested AlicIva, Tributo, and CbteAsoc entries.

    Includes CAE/CAEA authorization data and fiscal QR code URL if authorized.
    """,
    responses={
        200: ComprobanteReadSerializer,
        404: FacturacionErrorSerializer,
        401: FacturacionErrorSerializer,
    },
    tags=["facturacion-comprobantes"],
)

ComprobanteViewSetSchema = extend_schema_view(
    list=comprobante_list_schema,
    retrieve=comprobante_retrieve_schema,
)
