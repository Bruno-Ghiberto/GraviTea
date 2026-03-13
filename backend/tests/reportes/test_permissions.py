"""
Permission tests for Reportes (Reports) module.

Verifies HasModulePermission enforcement on ReportDefinition, SavedReport,
and ExportJob ViewSets, including reports.export for ExportJob creation.
"""

from __future__ import annotations

import pytest
from rest_framework import status

from apps.reportes.models import ReportDefinition, SavedReport


pytestmark = [pytest.mark.django_db(transaction=True)]

DEFINITIONS_URL = "/api/v1/reportes/definitions/"
SAVED_REPORTS_URL = "/api/v1/reportes/saved-reports/"
EXPORT_JOBS_URL = "/api/v1/reportes/export-jobs/"


@pytest.fixture
def report_definition(tenant_context):
    """Create a test report definition."""
    return ReportDefinition.objects.create(
        tenant=tenant_context,
        name="Sales Summary",
        report_type="sales",
        parameters={"period": "monthly"},
        is_active=True,
    )


@pytest.fixture
def saved_report(tenant_context, report_definition):
    """Create a test saved report."""
    return SavedReport.objects.create(
        tenant=tenant_context,
        report_definition=report_definition,
        result_metadata={"total": 100},
        status="COMPLETED",
    )


# ============================================================
# Unauthenticated Access
# ============================================================


class TestUnauthenticatedAccess:
    """Unauthenticated requests should return 401."""

    def test_definitions_list_unauthenticated(self, api_client):
        resp = api_client.get(DEFINITIONS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_saved_reports_list_unauthenticated(self, api_client):
        resp = api_client.get(SAVED_REPORTS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_jobs_list_unauthenticated(self, api_client):
        resp = api_client.get(EXPORT_JOBS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================
# Admin User (has reports.*)
# ============================================================


class TestAdminPermissions:
    """Admin role has full reports permissions — should succeed."""

    def test_admin_can_list_definitions(self, authenticated_client):
        resp = authenticated_client.get(DEFINITIONS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_create_definition(self, authenticated_client, tenant_context):
        resp = authenticated_client.post(
            DEFINITIONS_URL,
            {
                "name": "Stock Report",
                "report_type": "stock",
                "parameters": {},
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_admin_can_delete_definition(self, authenticated_client, report_definition):
        resp = authenticated_client.delete(f"{DEFINITIONS_URL}{report_definition.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_admin_can_list_saved_reports(self, authenticated_client):
        resp = authenticated_client.get(SAVED_REPORTS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_list_export_jobs(self, authenticated_client):
        resp = authenticated_client.get(EXPORT_JOBS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_can_create_export_job(self, authenticated_client, saved_report):
        resp = authenticated_client.post(
            EXPORT_JOBS_URL,
            {
                "saved_report_id": str(saved_report.id),
                "export_format": "PDF",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


# ============================================================
# Viewer User (has reports.read ONLY)
# ============================================================


class TestViewerPermissions:
    """Viewer role has reports.read — can GET but not POST/DELETE."""

    def test_viewer_can_list_definitions(self, viewer_client):
        resp = viewer_client.get(DEFINITIONS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create_definition(self, viewer_client):
        resp = viewer_client.post(
            DEFINITIONS_URL,
            {"name": "Blocked", "report_type": "sales", "parameters": {}},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_delete_definition(self, viewer_client, report_definition):
        resp = viewer_client.delete(f"{DEFINITIONS_URL}{report_definition.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_can_list_saved_reports(self, viewer_client):
        resp = viewer_client.get(SAVED_REPORTS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_can_list_export_jobs(self, viewer_client):
        resp = viewer_client.get(EXPORT_JOBS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_viewer_cannot_create_export_job(self, viewer_client, saved_report):
        """ExportJob creation requires reports.export, viewer only has reports.read."""
        resp = viewer_client.post(
            EXPORT_JOBS_URL,
            {
                "saved_report_id": str(saved_report.id),
                "export_format": "PDF",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ============================================================
# Sales User (NO reports permissions)
# ============================================================


class TestSalesUserDenied:
    """Sales role lacks reports.* permissions — should get 403."""

    def test_sales_cannot_list_definitions(self, sales_client):
        resp = sales_client.get(DEFINITIONS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_list_saved_reports(self, sales_client):
        resp = sales_client.get(SAVED_REPORTS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_list_export_jobs(self, sales_client):
        resp = sales_client.get(EXPORT_JOBS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_sales_cannot_create_export_job(self, sales_client, saved_report):
        resp = sales_client.post(
            EXPORT_JOBS_URL,
            {
                "saved_report_id": str(saved_report.id),
                "export_format": "CSV",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
