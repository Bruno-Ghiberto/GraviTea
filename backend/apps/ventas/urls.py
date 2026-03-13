"""
Ventas URL configuration.

Provides endpoints for sales management (customers, orders, items).
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, SaleOrderItemViewSet, SaleOrderViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"orders", SaleOrderViewSet, basename="saleorder")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "orders/<uuid:order_pk>/items/",
        SaleOrderItemViewSet.as_view({"get": "list", "post": "create"}),
        name="saleorderitem-list",
    ),
    path(
        "orders/<uuid:order_pk>/items/<uuid:pk>/",
        SaleOrderItemViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="saleorderitem-detail",
    ),
]
