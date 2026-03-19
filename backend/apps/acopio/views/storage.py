"""ViewSets for StorageUnit, GrainLot, and GrainMovement endpoints."""

from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.acopio.models import GrainLot, GrainMovement, StorageUnit
from apps.acopio.pagination import RomaneoPagination
from apps.acopio.serializers.storage import (
    CellSuggestionItemSerializer,
    CellSuggestionRequestSerializer,
    GrainLotSerializer,
    GrainMovementSerializer,
    ReconciliationRequestSerializer,
    StockReportSerializer,
    StorageUnitSerializer,
    TransferRequestSerializer,
)


class StorageUnitViewSet(viewsets.ModelViewSet):
    """
    StorageUnit CRUD with annotated occupancy.

    GET    /storage-units/          -> 200 (list, paginated)
    POST   /storage-units/          -> 201 (create)
    GET    /storage-units/{id}/     -> 200 (detail)
    PATCH  /storage-units/{id}/     -> 200 / 409 (update)
    DELETE /storage-units/{id}/     -> 405 (always rejected)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = StorageUnitSerializer
    pagination_class = RomaneoPagination
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        qs = (
            StorageUnit.objects
            .annotate(
                current_occupancy_kg=Coalesce(
                    Sum("grain_lots__movements__quantity_kg"),
                    Decimal("0.000"),
                )
            )
            .select_related("branch", "current_grain_type")
        )

        branch = self.request.query_params.get("branch")
        if branch:
            qs = qs.filter(branch_id=branch)

        is_active = self.request.query_params.get("is_active", "true")
        qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.user.tenant_id,
            created_by=self.request.user,
        )

    def partial_update(self, request, *args, **kwargs):
        """Guard: cannot deactivate unit with non-zero active stock."""
        instance = self.get_object()
        if (
            request.data.get("is_active") is False
            and instance.grain_lots.filter(total_kg__gt=0).exists()
        ):
            return Response(
                {
                    "type": "active_stock_exists",
                    "detail": "Cannot deactivate storage unit with non-zero grain stock.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Hard delete is always rejected."""
        return Response(
            {"detail": "Use PATCH is_active=false for soft-deactivation."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # -- Wave 3: suggest action (T024) ------------------------------------

    @action(detail=False, methods=["post"], url_path="suggest")
    def suggest(self, request):
        """POST /storage-units/suggest/ — ranked cell suggestions."""
        serializer = CellSuggestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.acopio.services.storage import suggest_cell

        suggestions = suggest_cell(
            tenant_id=request.user.tenant_id,
            branch_id=serializer.validated_data["branch_id"],
            grain_type_id=serializer.validated_data["grain_type_id"],
            campaign_id=serializer.validated_data["campaign_id"],
            grado=serializer.validated_data["grado"],
            incoming_kg=serializer.validated_data["incoming_kg"],
        )

        result = CellSuggestionItemSerializer(suggestions, many=True).data
        return Response({"suggestions": result})

    # -- Wave 3: stock-report action (T036) --------------------------------

    @action(detail=False, methods=["get"], url_path="stock-report")
    def stock_report(self, request):
        """GET /storage-units/stock-report/ — real-time stock report."""
        from apps.acopio.services.storage import generate_stock_report

        report = generate_stock_report(
            tenant_id=request.user.tenant_id,
            branch_id=request.query_params.get("branch"),
            grain_type_id=request.query_params.get("grain_type"),
            campaign_id=request.query_params.get("campaign"),
        )

        result = StockReportSerializer(report).data
        return Response(result)

    # -- Wave 4: reconcile action (T040) -----------------------------------

    @action(detail=False, methods=["post"], url_path="reconcile")
    def reconcile(self, request):
        """POST /storage-units/reconcile/ — physical inventory reconciliation."""
        serializer = ReconciliationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.acopio.services.storage import reconcile as reconcile_service

        try:
            result = reconcile_service(
                tenant_id=request.user.tenant_id,
                measurements=[
                    {
                        "storage_unit_id": str(m["storage_unit_id"]),
                        "measured_kg": m["measured_kg"],
                    }
                    for m in serializer.validated_data["measurements"]
                ],
                operator_id=request.user.pk,
                notes=serializer.validated_data["notes"],
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result)


class GrainLotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GrainLot read-only endpoints.

    GET /grain-lots/          -> 200 (list, paginated)
    GET /grain-lots/{id}/     -> 200 (detail)

    Lots are created internally by the deposit service — no POST/PATCH/DELETE.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GrainLotSerializer
    pagination_class = RomaneoPagination

    def get_queryset(self):
        qs = (
            GrainLot.objects
            .select_related("grain_type", "campaign", "storage_unit")
        )

        storage_unit = self.request.query_params.get("storage_unit")
        if storage_unit:
            qs = qs.filter(storage_unit_id=storage_unit)

        grain_type = self.request.query_params.get("grain_type")
        if grain_type:
            qs = qs.filter(grain_type_id=grain_type)

        campaign = self.request.query_params.get("campaign")
        if campaign:
            qs = qs.filter(campaign_id=campaign)

        is_own_grain = self.request.query_params.get("is_own_grain")
        if is_own_grain is not None:
            qs = qs.filter(is_own_grain=is_own_grain.lower() == "true")

        return qs

    # -- Wave 3: transfer action (T032) -----------------------------------

    @action(detail=False, methods=["post"], url_path="transfer")
    def transfer(self, request):
        """POST /grain-lots/transfer/ — atomic inter-silo grain transfer."""
        serializer = TransferRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.acopio.services.storage import transfer_grain

        try:
            source_lot = GrainLot.objects.get(
                pk=serializer.validated_data["source_lot_id"]
            )
            dest_lot = GrainLot.objects.get(
                pk=serializer.validated_data["destination_lot_id"]
            )
        except GrainLot.DoesNotExist:
            return Response(
                {"detail": "One or both grain lots not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            out_movement, dest_lot = transfer_grain(
                source_lot=source_lot,
                destination_lot=dest_lot,
                quantity_kg=serializer.validated_data["quantity_kg"],
                operator=request.user,
                notes=serializer.validated_data.get("notes"),
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_409_CONFLICT,
            )

        # Fetch the paired TRANSFER_IN movement
        in_movement = GrainMovement.objects.filter(
            grain_lot=dest_lot,
            movement_type=GrainMovement.MovementType.TRANSFER_IN,
            quantity_kg=serializer.validated_data["quantity_kg"],
        ).order_by("-movement_at").first()

        return Response({
            "transfer_out": GrainMovementSerializer(out_movement).data,
            "transfer_in": GrainMovementSerializer(in_movement).data,
        })


class GrainMovementViewSet(viewsets.ModelViewSet):
    """
    GrainMovement append-only endpoints (nested under grain-lots).

    GET  /grain-lots/{grain_lot_pk}/movements/       -> 200 (list)
    POST /grain-lots/{grain_lot_pk}/movements/       -> 201 (create)
    GET  /grain-lots/{grain_lot_pk}/movements/{pk}/  -> 200 (detail)

    PATCH/PUT/DELETE -> 405 (immutable ledger).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GrainMovementSerializer
    pagination_class = RomaneoPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        grain_lot_pk = self.kwargs.get("grain_lot_pk")
        return (
            GrainMovement.objects
            .filter(grain_lot_id=grain_lot_pk)
            .select_related("romaneo", "created_by")
            .order_by("-movement_at")
        )

    def perform_create(self, serializer):
        grain_lot_pk = self.kwargs.get("grain_lot_pk")
        grain_lot = GrainLot.objects.get(pk=grain_lot_pk)
        movement_type = serializer.validated_data["movement_type"]

        if movement_type == GrainMovement.MovementType.WITHDRAWAL:
            from apps.acopio.services.storage import create_withdrawal

            try:
                movement = create_withdrawal(
                    grain_lot=grain_lot,
                    quantity_kg=serializer.validated_data["quantity_kg"],
                    operator=self.request.user,
                    reference_document=serializer.validated_data.get(
                        "reference_document"
                    ),
                    notes=serializer.validated_data.get("notes"),
                )
            except ValueError as e:
                raise drf_serializers.ValidationError({"detail": str(e)})
            serializer.instance = movement
            return  # Movement already created by service

        # Default: save directly (for DEPOSIT created via romaneo flow, not API)
        serializer.save(
            tenant_id=self.request.user.tenant_id,
            grain_lot=grain_lot,
            created_by=self.request.user,
        )
