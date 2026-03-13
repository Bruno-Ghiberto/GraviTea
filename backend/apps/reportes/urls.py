"""
Reportes URL configuration.

Provides endpoints for the reporting infrastructure:
- /definitions/       — ReportDefinition CRUD
- /saved-reports/     — SavedReport CRUD
- /export-jobs/       — ExportJob CRUD
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ExportJobViewSet, ReportDefinitionViewSet, SavedReportViewSet

router = DefaultRouter()
router.register(r"definitions", ReportDefinitionViewSet, basename="reportdefinition")
router.register(r"saved-reports", SavedReportViewSet, basename="savedreport")
router.register(r"export-jobs", ExportJobViewSet, basename="exportjob")

urlpatterns = [
    path("", include(router.urls)),
]
