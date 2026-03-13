"""
Sync URL configuration.

Provides endpoints for offline-first POS synchronization.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (SyncPullView, SyncPushView, SyncSessionViewSet,
                    SyncStatusView)

router = DefaultRouter()
router.register(r"sessions", SyncSessionViewSet, basename="session")

urlpatterns = [
    # Sync operations
    path("push/", SyncPushView.as_view(), name="push"),
    path("pull/", SyncPullView.as_view(), name="pull"),
    path("status/<str:device_id>/", SyncStatusView.as_view(), name="status"),
    # Session management
    path("", include(router.urls)),
]
