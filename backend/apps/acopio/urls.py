"""Acopio URL configuration with DRF router registration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CampanaConfigViewSet,
    GrainTypeViewSet,
    MermaTableViewSet,
    QualityAnalysisViewSet,
    RomaneoViewSet,
    ToleranceTableViewSet,
)

router = DefaultRouter()
router.register(r"grain-types", GrainTypeViewSet, basename="grain-type")
router.register(r"tolerance-tables", ToleranceTableViewSet, basename="tolerance-table")
router.register(r"merma-tables", MermaTableViewSet, basename="merma-table")
router.register(r"campaigns", CampanaConfigViewSet, basename="campaign")
router.register(r"romaneos", RomaneoViewSet, basename="romaneo")

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

urlpatterns = qa_patterns + [
    path("", include(router.urls)),
]
