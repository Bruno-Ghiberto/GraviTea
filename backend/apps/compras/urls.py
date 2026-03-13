"""Compras URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GoodsReceiptViewSet, PurchaseOrderViewSet, SupplierViewSet

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="purchaseorder")
router.register(r"goods-receipts", GoodsReceiptViewSet, basename="goodsreceipt")

urlpatterns = [
    path("", include(router.urls)),
]
