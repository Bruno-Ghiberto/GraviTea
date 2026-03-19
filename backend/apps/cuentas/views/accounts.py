import datetime

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cuentas.models import AccountMovement, ProducerAccount
from apps.cuentas.serializers.accounts import (
    AccountMovementSerializer,
    ManualMovementSerializer,
    PosicionConsolidadaSerializer,
    ProducerAccountSerializer,
)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


class AccountCursorPagination(CursorPagination):
    ordering = "-created_at"
    page_size = 25


class MovementCursorPagination(CursorPagination):
    ordering = "-movement_at"
    page_size = 50


# ---------------------------------------------------------------------------
# ProducerAccountViewSet
# ---------------------------------------------------------------------------


class ProducerAccountViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = AccountCursorPagination
    serializer_class = ProducerAccountSerializer

    def get_queryset(self):
        tenant = self.request.user.tenant
        qs = ProducerAccount.objects.filter(tenant=tenant).select_related(
            "branch", "grain_type", "campaign", "created_by"
        )

        # CUIT blind index filter
        if cuit := self.request.query_params.get("producer_cuit"):
            from apps.core.encryption.utils import compute_blind_index

            qs = qs.filter(producer_cuit_hash=compute_blind_index(cuit))

        # Optional FK filters
        for param in ("grain_type", "campaign", "branch"):
            if val := self.request.query_params.get(param):
                qs = qs.filter(**{f"{param}_id": val})

        if is_active := self.request.query_params.get("is_active"):
            qs = qs.filter(is_active=is_active.lower() != "false")

        return qs

    @extend_schema(
        summary="List producer accounts",
        description=(
            "Returns cursor-paginated list of producer accounts for the tenant."
        ),
        parameters=[
            OpenApiParameter(
                "producer_cuit",
                OpenApiTypes.STR,
                description="Filter by CUIT (blind index equality)",
            ),
            OpenApiParameter(
                "grain_type",
                OpenApiTypes.UUID,
                description="Filter by grain type ID",
            ),
            OpenApiParameter(
                "campaign",
                OpenApiTypes.UUID,
                description="Filter by campaign ID",
            ),
            OpenApiParameter(
                "branch",
                OpenApiTypes.UUID,
                description="Filter by branch ID",
            ),
            OpenApiParameter(
                "is_active",
                OpenApiTypes.BOOL,
                description="Filter by active status",
            ),
            OpenApiParameter(
                "cursor",
                OpenApiTypes.STR,
                description="Opaque cursor for pagination",
            ),
        ],
        responses={200: ProducerAccountSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve producer account",
        description="Returns a single producer account by ID.",
        responses={200: ProducerAccountSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# AccountMovementViewSet
# ---------------------------------------------------------------------------


class AccountMovementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = MovementCursorPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ManualMovementSerializer
        return AccountMovementSerializer

    def get_queryset(self):
        tenant = self.request.user.tenant
        account_pk = self.kwargs.get("pk")
        qs = AccountMovement.objects.filter(
            producer_account_id=account_pk,
            tenant=tenant,
        ).select_related("producer_account", "romaneo", "created_by")

        if mt := self.request.query_params.get("movement_type"):
            qs = qs.filter(movement_type=mt)
        if df := self.request.query_params.get("date_from"):
            qs = qs.filter(movement_at__gte=df)
        if dt := self.request.query_params.get("date_to"):
            qs = qs.filter(movement_at__lt=dt)

        return qs

    def perform_create(self, serializer):
        from apps.cuentas.services.accounts import (
            MANUAL_TYPES,
            SUPERVISOR_ONLY_TYPES,
            ManualMovementService,
        )

        movement_type = serializer.validated_data["movement_type"]
        if movement_type not in MANUAL_TYPES:
            raise ValidationError(
                {"movement_type": f"{movement_type} cannot be created manually."},
                code="invalid_movement_type",
            )
        if movement_type in SUPERVISOR_ONLY_TYPES:
            if not self.request.user.has_permission("settings.admin"):
                raise PermissionDenied(code="permission_denied")

        account_pk = self.kwargs.get("pk")
        account = get_object_or_404(
            ProducerAccount, pk=account_pk, tenant=self.request.user.tenant
        )
        ManualMovementService.create_manual_movement(
            account=account,
            operator=self.request.user,
            **serializer.validated_data,
        )

    def update(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed.", "code": "append_only_violation"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Method not allowed.", "code": "append_only_violation"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @extend_schema(
        summary="List account movements",
        description="Returns cursor-paginated movement ledger for a producer account.",
        parameters=[
            OpenApiParameter(
                "movement_type",
                OpenApiTypes.STR,
                description="Filter by movement type (e.g. CEG_DEPOSIT)",
            ),
            OpenApiParameter(
                "date_from",
                OpenApiTypes.DATETIME,
                description="Filter movements on or after this datetime (ISO8601)",
            ),
            OpenApiParameter(
                "date_to",
                OpenApiTypes.DATETIME,
                description="Filter movements before this datetime (ISO8601)",
            ),
            OpenApiParameter(
                "cursor",
                OpenApiTypes.STR,
                description="Opaque cursor for pagination",
            ),
        ],
        responses={200: AccountMovementSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Retrieve account movement",
        description="Returns a single movement by ID.",
        responses={200: AccountMovementSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Create manual movement",
        description=(
            "Create a manual movement entry. Allowed types: SERVICE_CHARGE, "
            "RETIRO, RETENTION_DEDUCTION, ADJUSTMENT. ADJUSTMENT requires "
            "supervisor permission (settings.admin)."
        ),
        request=ManualMovementSerializer,
        responses={201: AccountMovementSerializer},
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# PosicionConsolidadaView
# ---------------------------------------------------------------------------


class PosicionConsolidadaView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Consolidated position",
        description=(
            "Compute cross-branch consolidated grain position for a producer "
            "in a campaign."
        ),
        parameters=[
            OpenApiParameter(
                "producer_cuit",
                OpenApiTypes.STR,
                required=True,
                description="CUIT to look up (blind index search)",
            ),
            OpenApiParameter(
                "campaign_id",
                OpenApiTypes.UUID,
                required=True,
                description="Campaign ID to aggregate",
            ),
        ],
        responses={200: PosicionConsolidadaSerializer},
    )
    def get(self, request):
        from apps.acopio.models import CampanaConfig
        from apps.cuentas.services.statements import PosicionConsolidadaService

        producer_cuit = request.query_params.get("producer_cuit")
        campaign_id = request.query_params.get("campaign_id")
        if not producer_cuit or not campaign_id:
            return Response(
                {
                    "detail": "producer_cuit and campaign_id are required.",
                    "code": "missing_param",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign = get_object_or_404(
            CampanaConfig, pk=campaign_id, tenant=request.user.tenant
        )
        result = PosicionConsolidadaService.compute(
            request.user.tenant, producer_cuit, campaign
        )
        data = {
            "producer_cuit": producer_cuit,
            "campaign_id": campaign.pk,
            "campaign_label": campaign.campaign_code,
            "summary": result,
        }
        serializer = PosicionConsolidadaSerializer(data)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# StatementView
# ---------------------------------------------------------------------------


class StatementView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Account statement",
        description=(
            "Generate an account statement for a date range. Returns grain "
            "and monetary ledgers with opening/closing balances."
        ),
        parameters=[
            OpenApiParameter(
                "date_from",
                OpenApiTypes.DATE,
                required=True,
                description="Statement period start (YYYY-MM-DD, inclusive)",
            ),
            OpenApiParameter(
                "date_to",
                OpenApiTypes.DATE,
                required=True,
                description="Statement period end (YYYY-MM-DD, inclusive)",
            ),
        ],
    )
    def get(self, request, pk):
        from apps.cuentas.services.statements import StatementService

        account = get_object_or_404(
            ProducerAccount, pk=pk, tenant=request.user.tenant
        )
        date_from_str = request.query_params.get("date_from")
        date_to_str = request.query_params.get("date_to")
        if not date_from_str or not date_to_str:
            return Response(
                {"detail": "date_from and date_to are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            date_from = datetime.date.fromisoformat(date_from_str)
            date_to = datetime.date.fromisoformat(date_to_str)
        except ValueError:
            return Response(
                {"detail": "Invalid date format. Use ISO8601 (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if date_from > date_to:
            return Response(
                {"detail": "date_from must not be after date_to."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        stmt = StatementService.generate(account, date_from, date_to)

        # Build structured response matching contracts/accounts-api.md
        grain_movements = []
        monetary_movements = []
        for m in stmt["movements"]:
            base = {
                "id": str(m.id),
                "movement_type": m.movement_type,
                "movement_at": m.movement_at.isoformat(),
                "reference_document": m.reference_document,
                "notes": m.notes,
            }
            if m.quantity_kg:
                grain_movements.append({**base, "quantity_kg": str(m.quantity_kg)})
            if m.ars_amount or m.usd_amount:
                monetary_movements.append(
                    {
                        **base,
                        "ars_amount": str(m.ars_amount),
                        "usd_amount": str(m.usd_amount),
                    }
                )

        return Response(
            {
                "account_id": str(account.pk),
                "producer_cuit": account.producer_cuit,
                "grain_type_code": account.grain_type.code,
                "campaign_label": account.campaign.campaign_code,
                "branch_name": account.branch.name,
                "date_from": date_from_str,
                "date_to": date_to_str,
                "grain_ledger": {
                    "opening_balance_kg": str(stmt["opening_balance_kg"]),
                    "movements": grain_movements,
                    "closing_balance_kg": str(stmt["closing_balance_kg"]),
                },
                "monetary_ledger": {
                    "opening_ars": str(stmt["opening_ars"]),
                    "opening_usd": str(stmt["opening_usd"]),
                    "movements": monetary_movements,
                    "closing_ars": str(stmt["closing_ars"]),
                    "closing_usd": str(stmt["closing_usd"]),
                },
            }
        )
