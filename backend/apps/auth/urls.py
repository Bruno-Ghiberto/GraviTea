"""
Authentication URL configuration.

Provides JWT token endpoints and user management URLs.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (BranchViewSet, CustomTokenObtainPairView, LogoutView,
                    RoleViewSet, UserViewSet)

app_name = "auth"

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"branches", BranchViewSet, basename="branch")

urlpatterns = [
    # JWT Token endpoints
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # User management
    path("", include(router.urls)),
]
