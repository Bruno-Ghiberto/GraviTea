"""ViewSets for acopio reference data endpoints."""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.acopio.models import CampanaConfig, GrainType, MermaTable, ToleranceTable
from apps.acopio.pagination import ReferenceDataPagination
from apps.acopio.serializers import (
    CampanaConfigSerializer,
    GrainTypeSerializer,
    MermaTableSerializer,
    ToleranceTableSerializer,
)


class GrainTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for grain types. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/grain-types/
    GET /api/v1/acopio/grain-types/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = GrainTypeSerializer
    pagination_class = ReferenceDataPagination
    # GLOBAL: uses standard Manager, NOT TenantBoundManager
    queryset = GrainType.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs


class CampanaConfigViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for campaign configuration. TENANT-SCOPED.

    GET/POST    /api/v1/acopio/campaigns/
    GET/PUT/PATCH/DELETE /api/v1/acopio/campaigns/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CampanaConfigSerializer
    pagination_class = ReferenceDataPagination

    def get_queryset(self):
        # TENANT-SCOPED: TenantBoundManager auto-filters by tenant_id
        qs = CampanaConfig.objects.all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.user.tenant_id)

    # -- Wave 4: campaign close action (T045) ------------------------------

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """POST /campaigns/{id}/close/ — close a campaign year."""
        campaign = self.get_object()

        # Permission check: supervisor or admin only
        if not request.user.has_permission("settings.admin"):
            return Response(
                {"detail": "Only supervisors or admins can close a campaign."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Target campaign is required
        target_campaign_id = request.data.get("target_campaign_id")
        if not target_campaign_id:
            return Response(
                {"detail": "target_campaign_id is required for carry-forward."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.acopio.services.storage import close_campaign

        try:
            result = close_campaign(
                tenant_id=request.user.tenant_id,
                campaign_id=campaign.pk,
                target_campaign_id=target_campaign_id,
                supervisor_id=request.user.pk,
            )
        except PermissionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(result)


class ToleranceTableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for tolerance tables. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/tolerance-tables/
    GET /api/v1/acopio/tolerance-tables/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ToleranceTableSerializer
    pagination_class = ReferenceDataPagination
    queryset = ToleranceTable.objects.select_related("grain_type").all()

    def get_queryset(self):
        qs = super().get_queryset()
        grain_type = self.request.query_params.get("grain_type")
        if grain_type is not None:
            qs = qs.filter(grain_type_id=grain_type)
        valid_from_before = self.request.query_params.get("valid_from_before")
        if valid_from_before is not None:
            qs = qs.filter(valid_from__lte=valid_from_before)
        return qs


class MermaTableViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for merma tables. GLOBAL -- no tenant filtering.

    GET /api/v1/acopio/merma-tables/
    GET /api/v1/acopio/merma-tables/{id}/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MermaTableSerializer
    pagination_class = ReferenceDataPagination
    queryset = MermaTable.objects.select_related("grain_type").all()

    def get_queryset(self):
        qs = super().get_queryset()
        grain_type = self.request.query_params.get("grain_type")
        if grain_type is not None:
            qs = qs.filter(grain_type_id=grain_type)
        return qs
