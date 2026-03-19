"""Acopio URL configuration with DRF router registration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CampanaConfigViewSet,
    GrainLotViewSet,
    GrainMovementViewSet,
    GrainTypeViewSet,
    MermaTableViewSet,
    QualityAnalysisViewSet,
    RomaneoViewSet,
    StorageUnitViewSet,
    ToleranceTableViewSet,
)

router = DefaultRouter()
router.register(r"grain-types", GrainTypeViewSet, basename="grain-type")
router.register(r"tolerance-tables", ToleranceTableViewSet, basename="tolerance-table")
router.register(r"merma-tables", MermaTableViewSet, basename="merma-table")
router.register(r"campaigns", CampanaConfigViewSet, basename="campaign")
router.register(r"romaneos", RomaneoViewSet, basename="romaneo")
router.register(r"storage-units", StorageUnitViewSet, basename="storage-unit")
router.register(r"grain-lots", GrainLotViewSet, basename="grain-lot")

# Nested QA routes (not on the main router since it's a 1:1 nested resource)
qa_patterns = [
    path(
        "romaneos/<uuid:romaneo_pk>/quality-analysis/",
        QualityAnalysisViewSet.as_view(
            {"get": "list", "post": "create", "patch": "partial_update"}
        ),
        name="romaneo-quality-analysis",
    ),
]

# Nested movements routes (manual path for 1:N nested resource)
movement_patterns = [
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/",
        GrainMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="grain-lot-movements-list",
    ),
    path(
        "grain-lots/<uuid:grain_lot_pk>/movements/<uuid:pk>/",
        GrainMovementViewSet.as_view({"get": "retrieve"}),
        name="grain-lot-movements-detail",
    ),
]

urlpatterns = qa_patterns + movement_patterns + [
    path("", include(router.urls)),
]
