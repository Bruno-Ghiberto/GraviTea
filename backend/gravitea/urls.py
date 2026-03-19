"""
URL configuration for Gravitea ERP project.

API endpoints follow versioning pattern: /api/v1/
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)

from apps.core.health.views import CombinedHealthView


urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health check endpoints (Kubernetes probes)
    path("health/", include("apps.core.health.urls")),
    # Observability endpoints (Prometheus metrics)
    path("", include("apps.core.observability.urls")),
    # API v1
    path(
        "api/v1/",
        include(
            [
                # Documentation
                path("schema/", SpectacularAPIView.as_view(), name="schema"),
                path(
                    "schema/swagger-ui/",
                    SpectacularSwaggerView.as_view(url_name="schema"),
                    name="swagger-ui",
                ),
                path(
                    "schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
                ),
                # Health check (combined — no auth required)
                path("health/", CombinedHealthView.as_view(), name="health-check"),
                # Authentication
                path("auth/", include("apps.auth.urls")),
                # Inventory
                path("", include("apps.inventario.urls")),
                # Sync (offline support)
                path("sync/", include("apps.sync.urls")),
                # Facturacion (electronic invoicing)
                path("facturacion/", include("apps.facturacion.urls")),
                # Ventas (sales management)
                path("ventas/", include("apps.ventas.urls")),
                # Compras (purchases management)
                path("compras/", include("apps.compras.urls")),
                # Reportes (reporting infrastructure)
                path("reportes/", include("apps.reportes.urls")),
                # Acopio (grain elevator reference data)
                path("acopio/", include("apps.acopio.urls")),
                # Core (customization: field definitions, module config)
                path("", include("apps.core.urls")),
            ]
        ),
    ),
]
