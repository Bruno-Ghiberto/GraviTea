"""
Facturacion views for Gravitea ERP.

Provides ViewSets for electronic invoicing entities: PuntoDeVenta,
ARCACredential, and Comprobante management + emission.
"""

from __future__ import annotations

import logging
from datetime import datetime as dt

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from apps.core.pagination import StandardCursorPagination

from .arca import ARCAClient
from .arca.caea import CAEAService
from .arca.exceptions import ARCAAuthError, ARCAComprobanteRejected, ARCARequestError
from .constants import CAEAStatus
from .models import CAEA, ARCACredential, Comprobante, PuntoDeVenta
from .qr import generate_fiscal_qr_data
from .schema import (
    ARCACredentialViewSetSchema,
    ComprobanteViewSetSchema,
    FacturacionErrorSerializer,
    PuntoDeVentaViewSetSchema,
)
from .serializers import (
    ARCACredentialReadSerializer,
    ARCACredentialWriteSerializer,
    CAEAReadSerializer,
    CAEASolicitarSerializer,
    ComprobanteEmitirSerializer,
    ComprobanteReadSerializer,
    PuntoDeVentaSerializer,
)
from .services import InvoiceService

logger = logging.getLogger("facturacion")


@PuntoDeVentaViewSetSchema
class PuntoDeVentaViewSet(viewsets.ModelViewSet):
    """
    PuntoDeVenta management viewset.

    Endpoints:
        GET    /api/v1/facturacion/puntos-de-venta/        - List PtoVta
        POST   /api/v1/facturacion/puntos-de-venta/        - Create PtoVta
        GET    /api/v1/facturacion/puntos-de-venta/{id}/   - Get PtoVta detail
        PATCH  /api/v1/facturacion/puntos-de-venta/{id}/   - Update PtoVta
        DELETE /api/v1/facturacion/puntos-de-venta/{id}/   - Soft delete PtoVta
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    serializer_class = PuntoDeVentaSerializer

    def get_queryset(self) -> QuerySet[PuntoDeVenta]:
        """Return puntos de venta for current tenant with optimized queries."""
        return PuntoDeVenta.objects.select_related("tenant").all()

    def perform_destroy(self, instance: PuntoDeVenta) -> None:
        """Soft delete punto de venta by deactivating."""
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        logger.info("PuntoDeVenta deactivated: %s", instance)


@ARCACredentialViewSetSchema
class ARCACredentialViewSet(viewsets.ModelViewSet):
    """
    ARCACredential management viewset.

    Supports create, list, retrieve, partial_update for cert rotation,
    and soft-deactivate on destroy. Switches serializer for read vs write.

    Endpoints:
        GET    /api/v1/facturacion/credentials/        - List credentials
        POST   /api/v1/facturacion/credentials/        - Create credential
        GET    /api/v1/facturacion/credentials/{id}/   - Get credential detail
        PATCH  /api/v1/facturacion/credentials/{id}/   - Update (cert rotation)
        DELETE /api/v1/facturacion/credentials/{id}/   - Soft deactivate
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination

    def get_queryset(self) -> QuerySet[ARCACredential]:
        """Return credentials for current tenant."""
        return ARCACredential.objects.select_related("tenant").all()

    def get_serializer_class(self) -> type[Serializer]:
        """Switch serializer for read vs write operations."""
        if self.action in ("create", "update", "partial_update"):
            return ARCACredentialWriteSerializer
        return ARCACredentialReadSerializer

    def create(self, request, *args, **kwargs):
        """Create credential and return read serializer (without secrets)."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        read_serializer = ARCACredentialReadSerializer(write_serializer.instance)
        headers = self.get_success_headers(read_serializer.data)
        return Response(
            read_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_destroy(self, instance: ARCACredential) -> None:
        """Soft deactivate credential instead of deleting."""
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        logger.info("ARCACredential deactivated: %s", instance)


@ComprobanteViewSetSchema
class ComprobanteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Comprobante (electronic invoice) viewset.

    Provides read-only list/retrieve for existing comprobantes and a custom
    ``emitir`` action that creates + authorizes a comprobante via ARCA.

    Endpoints:
        GET    /api/v1/facturacion/comprobantes/         - List comprobantes
        GET    /api/v1/facturacion/comprobantes/{id}/     - Get comprobante detail
        POST   /api/v1/facturacion/comprobantes/emitir/   - Issue new comprobante
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    serializer_class = ComprobanteReadSerializer

    def get_queryset(self) -> QuerySet[Comprobante]:
        """
        Return comprobantes for the current tenant with optimized queries.

        Supports filtering via query parameters:
            - cbte_tipo: int — CbteTipo code
            - punto_venta: UUID — PuntoDeVenta ID
            - status: str — ComprobanteStatus value
            - fecha_from: date — cbte_fch >= date
            - fecha_to: date — cbte_fch <= date
        """
        qs = (
            Comprobante.objects.select_related("punto_venta")
            .prefetch_related("aliciva_set", "tributo_set", "cbteasoc_set")
            .all()
        )

        params = self.request.query_params

        cbte_tipo = params.get("cbte_tipo")
        if cbte_tipo is not None:
            qs = qs.filter(cbte_tipo=int(cbte_tipo))

        punto_venta = params.get("punto_venta")
        if punto_venta is not None:
            qs = qs.filter(punto_venta_id=punto_venta)

        status_param = params.get("status")
        if status_param is not None:
            qs = qs.filter(status=status_param)

        fecha_from = params.get("fecha_from")
        if fecha_from is not None:
            qs = qs.filter(cbte_fch__gte=fecha_from)

        fecha_to = params.get("fecha_to")
        if fecha_to is not None:
            qs = qs.filter(cbte_fch__lte=fecha_to)

        return qs

    @extend_schema(
        summary="Issue a new comprobante",
        description="""
        Create and authorize a comprobante via ARCA (FECAESolicitar).

        **Flow:**
        1. Validate input data.
        2. Authenticate via WSAA (cached).
        3. Allocate next CbteNro (FECompUltimoAutorizado).
        4. Submit to ARCA for CAE authorization.
        5. Return the authorized comprobante.

        **Possible outcomes:**
        - **201**: Comprobante authorized (AUTORIZADO) or observed (OBSERVADO).
        - **400**: Input validation errors.
        - **422**: ARCA rejected the comprobante (RECHAZADO). Includes
          observations and error details from ARCA.
        - **502**: ARCA service unavailable or authentication failure.
        """,
        request=ComprobanteEmitirSerializer,
        responses={
            201: ComprobanteReadSerializer,
            400: OpenApiResponse(
                description="Validation error",
            ),
            422: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="Comprobante rejected by ARCA",
            ),
            502: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="ARCA service error",
            ),
        },
        examples=[
            OpenApiExample(
                name="Factura B - Producto",
                value={
                    "punto_venta": "a1b2c3d4-...",
                    "cbte_tipo": 6,
                    "concepto": 1,
                    "doc_tipo": 80,
                    "doc_nro": "20345678901",
                    "cbte_fch": "2026-02-10",
                    "imp_total": "1210.00",
                    "imp_neto": "1000.00",
                    "imp_iva": "210.00",
                    "imp_trib": "0.00",
                    "imp_op_ex": "0.00",
                    "imp_tot_conc": "0.00",
                    "emitter_condicion_iva": 1,
                    "receptor_condicion_iva": 5,
                    "alic_iva": [
                        {"iva_id": 5, "base_imp": "1000.00", "importe": "210.00"}
                    ],
                },
                request_only=True,
            ),
        ],
        tags=["facturacion-comprobantes"],
    )
    @action(detail=False, methods=["post"], url_path="emitir")
    def emitir(self, request: Request) -> Response:
        """Issue a new comprobante and request CAE authorization from ARCA."""
        serializer = ComprobanteEmitirSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            comprobante = InvoiceService().issue_comprobante(
                tenant_id=str(request.user.tenant_id),
                validated_data=serializer.validated_data,
            )
        except ARCAComprobanteRejected as exc:
            logger.warning(
                "emitir: comprobante rejected for tenant=%s: %s",
                request.user.tenant_id,
                exc,
            )
            return Response(
                {
                    "type": "urn:gravitea:facturacion:comprobante-rejected",
                    "title": "Comprobante rejected by ARCA",
                    "status": 422,
                    "detail": exc.message,
                    "arca_code": exc.code,
                    "observations": exc.observations,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except (ARCARequestError, ARCAAuthError) as exc:
            logger.error(
                "emitir: ARCA error for tenant=%s: %s",
                request.user.tenant_id,
                exc,
            )
            return Response(
                {
                    "type": "urn:gravitea:facturacion:arca-error",
                    "title": "ARCA service error",
                    "status": 502,
                    "detail": "ARCA service unavailable. Please try again later.",
                    "arca_code": exc.code,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        read_serializer = ComprobanteReadSerializer(comprobante)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Get fiscal QR code URL",
        description="""
        Return the fiscal QR code URL for an authorized comprobante.

        The QR URL points to ARCA's verification endpoint with a base64url-encoded
        JSON payload containing all required fiscal data per RG 4291.

        Only available for comprobantes with status AUTORIZADO or OBSERVADO.
        """,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "qr_url": {
                        "type": "string",
                        "format": "uri",
                        "description": "ARCA fiscal verification URL for QR rendering",
                    },
                },
            },
            400: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="Comprobante not authorized — no QR available",
            ),
            404: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="Comprobante not found",
            ),
        },
        tags=["facturacion-comprobantes"],
    )
    @action(detail=True, methods=["get"], url_path="qr")
    def qr(self, request: Request, pk: str = None) -> Response:
        """Return the fiscal QR code URL for an authorized comprobante."""
        comprobante = self.get_object()

        try:
            qr_url = generate_fiscal_qr_data(comprobante)
        except ValueError as exc:
            return Response(
                {
                    "type": "urn:gravitea:facturacion:qr-unavailable",
                    "title": "QR code unavailable",
                    "status": 400,
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"qr_url": qr_url})

    # T054: Authorize an existing DRAFT comprobante
    @extend_schema(
        summary="Authorize an existing DRAFT comprobante",
        description="""
        Submit an existing DRAFT comprobante to ARCA for CAE authorization.

        Used for comprobantes created from the sale confirmation flow
        (or any other flow that creates DRAFT comprobantes).

        **Flow:**
        1. Validate comprobante is in DRAFT status.
        2. Authenticate via WSAA (cached).
        3. Allocate next CbteNro (FECompUltimoAutorizado).
        4. Submit to ARCA for CAE authorization.
        5. Return the authorized comprobante.
        """,
        responses={
            200: ComprobanteReadSerializer,
            409: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="Comprobante not in DRAFT status",
            ),
            422: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="Comprobante rejected by ARCA",
            ),
            502: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="ARCA service error",
            ),
        },
        tags=["facturacion-comprobantes"],
    )
    @action(detail=True, methods=["post"], url_path="authorize")
    def authorize(self, request: Request, pk: str = None) -> Response:
        """Authorize a DRAFT comprobante via ARCA."""
        from .constants import ComprobanteStatus

        comprobante = self.get_object()

        if comprobante.status != ComprobanteStatus.DRAFT:
            return Response(
                {
                    "type": "urn:gravitea:facturacion:not-draft",
                    "title": "Comprobante is not in DRAFT status",
                    "status": 409,
                    "detail": (
                        f"Cannot authorize comprobante in status {comprobante.status}. "
                        f"Only DRAFT comprobantes can be authorized."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            authorized = InvoiceService().authorize_comprobante(
                comprobante=comprobante,
            )
        except ARCAComprobanteRejected as exc:
            return Response(
                {
                    "type": "urn:gravitea:facturacion:comprobante-rejected",
                    "title": "Comprobante rejected by ARCA",
                    "status": 422,
                    "detail": exc.message,
                    "arca_code": exc.code,
                    "observations": exc.observations,
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except (ARCARequestError, ARCAAuthError) as exc:
            return Response(
                {
                    "type": "urn:gravitea:facturacion:arca-error",
                    "title": "ARCA service error",
                    "status": 502,
                    "detail": "ARCA service unavailable. Please try again later.",
                    "arca_code": exc.code,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        read_serializer = ComprobanteReadSerializer(authorized)
        return Response(read_serializer.data, status=status.HTTP_200_OK)


class CAEAViewSet(viewsets.ReadOnlyModelViewSet):
    """
    CAEA (offline invoicing code) management viewset.

    Provides read-only list/retrieve for existing CAEAs and custom actions
    to request, report, and declare no-movement for CAEA periods.

    Endpoints:
        GET    /api/v1/facturacion/caeas/                    - List CAEAs
        GET    /api/v1/facturacion/caeas/{id}/                - Get CAEA detail
        POST   /api/v1/facturacion/caeas/solicitar/           - Request new CAEA
        POST   /api/v1/facturacion/caeas/{id}/sin-movimiento/ - Report no movement
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardCursorPagination
    serializer_class = CAEAReadSerializer

    def get_queryset(self) -> QuerySet[CAEA]:
        """Return CAEAs for current tenant with optimized queries."""
        return CAEA.objects.select_related("punto_venta").all()

    @extend_schema(
        summary="Request a new CAEA from ARCA",
        description="""
        Request a CAEA code for a punto de venta and billing period.

        **Flow:**
        1. Validate input (punto_venta, periodo, orden).
        2. Authenticate via WSAA (cached).
        3. Call FECAEASolicitar.
        4. Save CAEA record and return it.

        **Possible outcomes:**
        - **201**: CAEA issued successfully.
        - **400**: Validation errors (invalid periodo, inactive punto_venta).
        - **502**: ARCA service error.
        """,
        request=CAEASolicitarSerializer,
        responses={
            201: CAEAReadSerializer,
            400: OpenApiResponse(description="Validation error"),
            502: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="ARCA service error",
            ),
        },
        tags=["facturacion-caea"],
    )
    @action(detail=False, methods=["post"], url_path="solicitar")
    def solicitar(self, request: Request) -> Response:
        """Request a new CAEA code from ARCA for a punto de venta + period."""
        serializer = CAEASolicitarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pto_vta_id = serializer.validated_data["punto_venta"]
        periodo = serializer.validated_data["periodo"]
        orden = serializer.validated_data["orden"]

        pto_vta = PuntoDeVenta.objects.get(pk=pto_vta_id)

        try:
            # Determine environment from active credential
            credential = ARCACredential.objects.filter(
                tenant_id=str(request.user.tenant_id), is_active=True
            ).first()
            is_production = credential.is_production if credential else False

            arca_client = ARCAClient()
            ctx = arca_client.get_auth_context(
                str(request.user.tenant_id), is_production=is_production
            )

            caea_svc = CAEAService(
                token=ctx.token,
                sign=ctx.sign,
                cuit=ctx.cuit,
                is_production=ctx.is_production,
            )
            result = caea_svc.solicitar_caea(
                pto_vta=pto_vta.numero, periodo=periodo, orden=orden
            )
        except (ARCARequestError, ARCAAuthError) as exc:
            logger.error(
                "solicitar CAEA failed: tenant=%s error=%s",
                request.user.tenant_id,
                exc,
            )
            return Response(
                {
                    "type": "urn:gravitea:facturacion:arca-error",
                    "title": "ARCA service error",
                    "status": 502,
                    "detail": "ARCA service unavailable. Please try again later.",
                    "arca_code": exc.code,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Parse ARCA date strings (YYYYMMDD) to date objects.
        caea = CAEA(
            tenant_id=request.user.tenant_id,
            punto_venta=pto_vta,
            caea_code=result.caea,
            periodo=result.periodo,
            orden=result.orden,
            fch_vig_desde=dt.strptime(result.fch_vig_desde, "%Y%m%d").date(),
            fch_vig_hasta=dt.strptime(result.fch_vig_hasta, "%Y%m%d").date(),
            fch_tope_inf=dt.strptime(result.fch_tope_inf, "%Y%m%d").date(),
            status=CAEAStatus.ACTIVE,
        )
        caea.save()

        logger.info(
            "CAEA issued: tenant=%s caea=%s periodo=%s orden=%s",
            request.user.tenant_id,
            result.caea,
            result.periodo,
            result.orden,
        )

        read_serializer = CAEAReadSerializer(caea)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Report no movement for a CAEA period",
        description="""
        Declare that no comprobantes were issued during this CAEA period.

        Must be called before the CAEA reporting deadline (fch_tope_inf).
        Updates the CAEA status to REPORTED_NO_MOVEMENT.

        **Possible outcomes:**
        - **200**: No-movement report accepted.
        - **400**: CAEA not in ACTIVE status.
        - **502**: ARCA service error.
        """,
        request=None,
        responses={
            200: CAEAReadSerializer,
            400: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="CAEA not in ACTIVE status",
            ),
            502: OpenApiResponse(
                response=FacturacionErrorSerializer,
                description="ARCA service error",
            ),
        },
        tags=["facturacion-caea"],
    )
    @action(detail=True, methods=["post"], url_path="sin-movimiento")
    def sin_movimiento(self, request: Request, pk: str = None) -> Response:
        """Report no movement for a CAEA period to ARCA."""
        caea = self.get_object()

        if caea.status != CAEAStatus.ACTIVE:
            return Response(
                {
                    "type": "urn:gravitea:facturacion:caea-not-active",
                    "title": "CAEA not active",
                    "status": 400,
                    "detail": (
                        f"Cannot report no-movement: CAEA status is {caea.status}."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Determine environment from active credential
            credential = ARCACredential.objects.filter(
                tenant_id=str(request.user.tenant_id), is_active=True
            ).first()
            is_production = credential.is_production if credential else False

            arca_client = ARCAClient()
            ctx = arca_client.get_auth_context(
                str(request.user.tenant_id), is_production=is_production
            )

            caea_svc = CAEAService(
                token=ctx.token,
                sign=ctx.sign,
                cuit=ctx.cuit,
                is_production=ctx.is_production,
            )
            caea_svc.informar_sin_movimiento(
                caea=caea.caea_code, pto_vta=caea.punto_venta.numero
            )
        except (ARCARequestError, ARCAAuthError) as exc:
            logger.error(
                "sin_movimiento failed: tenant=%s caea=%s error=%s",
                request.user.tenant_id,
                caea.caea_code,
                exc,
            )
            return Response(
                {
                    "type": "urn:gravitea:facturacion:arca-error",
                    "title": "ARCA service error",
                    "status": 502,
                    "detail": "ARCA service unavailable. Please try again later.",
                    "arca_code": exc.code,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        caea.status = CAEAStatus.REPORTED_NO_MOVEMENT
        caea.save(update_fields=["status", "updated_at"])

        logger.info(
            "CAEA sin movimiento reported: tenant=%s caea=%s",
            request.user.tenant_id,
            caea.caea_code,
        )

        read_serializer = CAEAReadSerializer(caea)
        return Response(read_serializer.data)
