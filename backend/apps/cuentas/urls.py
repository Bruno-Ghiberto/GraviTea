from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.cuentas.views.accounts import (
    AccountMovementViewSet,
    PosicionConsolidadaView,
    ProducerAccountViewSet,
    StatementView,
)

router = DefaultRouter()
router.register("accounts", ProducerAccountViewSet, basename="produceraccount")

urlpatterns = router.urls + [
    # DRF router does NOT auto-nest — explicit nested routes required
    path(
        "accounts/<int:pk>/movements/",
        AccountMovementViewSet.as_view({"get": "list", "post": "create"}),
        name="account-movement-list",
    ),
    path(
        "accounts/<int:pk>/movements/<int:movement_pk>/",
        AccountMovementViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="account-movement-detail",
    ),
    path(
        "accounts/<int:pk>/statement/",
        StatementView.as_view(),
        name="account-statement",
    ),
    path(
        "posicion-consolidada/",
        PosicionConsolidadaView.as_view(),
        name="posicion-consolidada",
    ),
]
