"""
Inventario URL configuration.

Provides endpoints for product and stock management.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (CategoryViewSet, PriceListViewSet,
                    ProductCostHistoryViewSet, ProductPriceHistoryViewSet,
                    ProductViewSet, StockMovementViewSet)

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"movements", StockMovementViewSet, basename="movement")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"price-lists", PriceListViewSet, basename="pricelist")
router.register(r"price-history", ProductPriceHistoryViewSet, basename="pricehistory")
router.register(r"cost-history", ProductCostHistoryViewSet, basename="costhistory")

urlpatterns = [
    path("", include(router.urls)),
]
