"""
Facturacion URL configuration.

Provides endpoints for electronic invoicing (ARCA integration).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ARCACredentialViewSet,
    CAEAViewSet,
    ComprobanteViewSet,
    PuntoDeVentaViewSet,
)

router = DefaultRouter()
router.register(r"puntos-de-venta", PuntoDeVentaViewSet, basename="puntodeventa")
router.register(r"credentials", ARCACredentialViewSet, basename="arcacredential")
router.register(r"comprobantes", ComprobanteViewSet, basename="comprobante")
router.register(r"caeas", CAEAViewSet, basename="caea")

urlpatterns = [
    path("", include(router.urls)),
]
