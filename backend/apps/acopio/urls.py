"""Acopio URL configuration with DRF router registration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CampanaConfigViewSet,
    GrainTypeViewSet,
    MermaTableViewSet,
    ToleranceTableViewSet,
)

router = DefaultRouter()
router.register(r"grain-types", GrainTypeViewSet, basename="grain-type")
router.register(r"tolerance-tables", ToleranceTableViewSet, basename="tolerance-table")
router.register(r"merma-tables", MermaTableViewSet, basename="merma-table")
router.register(r"campaigns", CampanaConfigViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
]
