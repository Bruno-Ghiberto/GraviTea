"""ViewSets for acopio reference data endpoints."""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

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
