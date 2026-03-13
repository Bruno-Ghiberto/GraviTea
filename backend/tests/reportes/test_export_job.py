"""
T051: ExportJob CRUD + filter + tenant isolation tests.

Tests ExportJobViewSet endpoints:
- Create, read (no update, no delete — worker-managed)
- Filter by status
- Tenant isolation (cross-tenant access returns 404)
"""

import pytest

DEFINITIONS_URL = "/api/v1/reportes/definitions/"
SAVED_REPORTS_URL = "/api/v1/reportes/saved-reports/"
BASE_URL = "/api/v1/reportes/export-jobs/"


def _export_job_url(pk):
    """Build detail URL for an export job."""
    return f"{BASE_URL}{pk}/"


@pytest.fixture
def report_definition(authenticated_client):
    """Create a ReportDefinition and return its data."""
    response = authenticated_client.post(
        DEFINITIONS_URL,
        {"name": "Export Test Def", "report_type": "sales"},
        format="json",
    )
    assert response.status_code == 201
    return response.data


@pytest.fixture
def saved_report(authenticated_client, report_definition):
    """Create a SavedReport and return its data."""
    response = authenticated_client.post(
        SAVED_REPORTS_URL,
        {
            "report_definition_id": report_definition["id"],
            "status": "COMPLETED",
        },
        format="json",
    )
    assert response.status_code == 201
    return response.data


@pytest.fixture
def export_job(authenticated_client, saved_report):
    """Create an ExportJob via API and return the response data."""
    response = authenticated_client.post(
        BASE_URL,
        {
            "saved_report_id": saved_report["id"],
            "export_format": "CSV",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestExportJobCrud:
    """T051: ExportJobViewSet API CRUD tests."""

    # --- Create ---

    def test_create_export_job_csv(self, authenticated_client, saved_report):
        """POST with CSV format → 201 with PENDING status."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "saved_report_id": saved_report["id"],
                "export_format": "CSV",
            },
            format="json",
        )
        assert response.status_code == 201
        assert str(response.data["saved_report_id"]) == saved_report["id"]
        assert response.data["export_format"] == "CSV"
        assert response.data["status"] == "PENDING"
        assert "id" in response.data
        assert "created_at" in response.data
        assert response.data["completed_at"] is None
        assert response.data["file_path"] is None

    def test_create_export_job_pdf(self, authenticated_client, saved_report):
        """POST with PDF format → 201."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "saved_report_id": saved_report["id"],
                "export_format": "PDF",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["export_format"] == "PDF"
        assert response.data["status"] == "PENDING"

    def test_create_export_job_excel(self, authenticated_client, saved_report):
        """POST with EXCEL format → 201."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "saved_report_id": saved_report["id"],
                "export_format": "EXCEL",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["export_format"] == "EXCEL"

    def test_create_export_job_missing_saved_report(self, authenticated_client):
        """POST without saved_report_id → 400."""
        response = authenticated_client.post(
            BASE_URL,
            {"export_format": "CSV"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_export_job_invalid_format(self, authenticated_client, saved_report):
        """POST with invalid export_format → 400."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "saved_report_id": saved_report["id"],
                "export_format": "WORD",  # Not a valid choice
            },
            format="json",
        )
        assert response.status_code == 400

    def test_create_export_job_missing_format(self, authenticated_client, saved_report):
        """POST without export_format → 400."""
        response = authenticated_client.post(
            BASE_URL,
            {"saved_report_id": saved_report["id"]},
            format="json",
        )
        assert response.status_code == 400

    # --- List ---

    def test_list_export_jobs(self, authenticated_client, export_job):
        """GET /export-jobs/ returns paginated list."""
        response = authenticated_client.get(BASE_URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    # --- Retrieve ---

    def test_retrieve_export_job(self, authenticated_client, export_job):
        """GET /export-jobs/{id}/ returns detail."""
        pk = export_job["id"]
        response = authenticated_client.get(_export_job_url(pk))
        assert response.status_code == 200
        assert response.data["id"] == pk
        assert response.data["export_format"] == export_job["export_format"]

    def test_retrieve_nonexistent(self, authenticated_client):
        """GET /export-jobs/{id}/ with unknown UUID → 404."""
        import uuid
        response = authenticated_client.get(_export_job_url(uuid.uuid4()))
        assert response.status_code == 404

    # --- No Update / No Delete ---

    def test_update_not_allowed(self, authenticated_client, export_job):
        """PATCH /export-jobs/{id}/ → 405 Method Not Allowed (worker-managed)."""
        pk = export_job["id"]
        response = authenticated_client.patch(
            _export_job_url(pk),
            {"status": "COMPLETED"},
            format="json",
        )
        assert response.status_code == 405

    def test_delete_not_allowed(self, authenticated_client, export_job):
        """DELETE /export-jobs/{id}/ → 405 Method Not Allowed (worker-managed)."""
        pk = export_job["id"]
        response = authenticated_client.delete(_export_job_url(pk))
        assert response.status_code == 405


@pytest.mark.integration
@pytest.mark.django_db
class TestExportJobFilters:
    """Filter tests for ExportJobViewSet."""

    def test_filter_by_status(self, authenticated_client, saved_report):
        """GET ?status=PENDING returns only PENDING export jobs."""
        # Create a PENDING job
        authenticated_client.post(
            BASE_URL,
            {"saved_report_id": saved_report["id"], "export_format": "CSV"},
            format="json",
        )
        # Note: We can't directly set status=COMPLETED via API (it's read-only)
        # but we can test that filter works with the default PENDING status

        response = authenticated_client.get(BASE_URL, {"status": "PENDING"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["status"] == "PENDING" for r in results)
        assert len(results) >= 1

    def test_filter_by_status_no_match(self, authenticated_client, saved_report):
        """GET ?status=FAILED with no failed jobs → empty results."""
        # Create a PENDING job
        authenticated_client.post(
            BASE_URL,
            {"saved_report_id": saved_report["id"], "export_format": "CSV"},
            format="json",
        )

        response = authenticated_client.get(BASE_URL, {"status": "FAILED"})
        assert response.status_code == 200
        assert len(response.data["results"]) == 0


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestExportJobTenantIsolation:
    """Tenant isolation tests for ExportJobViewSet."""

    def test_cross_tenant_saved_report_rejected_on_create(
        self, authenticated_client, other_tenant_client
    ):
        """Creating an ExportJob referencing another tenant's saved report → 400."""
        # Tenant A creates definition + saved report
        resp_def = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Isolated Def", "report_type": "sales"},
            format="json",
        )
        resp_sr = authenticated_client.post(
            SAVED_REPORTS_URL,
            {"report_definition_id": resp_def.data["id"], "status": "COMPLETED"},
            format="json",
        )
        assert resp_sr.status_code == 201
        sr_id = resp_sr.data["id"]

        # Tenant B tries to create an ExportJob referencing Tenant A's saved report
        response = other_tenant_client.post(
            BASE_URL,
            {"saved_report_id": sr_id, "export_format": "CSV"},
            format="json",
        )
        assert response.status_code == 400

    def test_list_only_own_tenant_export_jobs(
        self, authenticated_client, other_tenant_client
    ):
        """Tenants only see their own export jobs."""
        # Tenant A setup: definition + saved report + export job
        resp_def_a = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "A Def", "report_type": "sales"},
            format="json",
        )
        resp_sr_a = authenticated_client.post(
            SAVED_REPORTS_URL,
            {"report_definition_id": resp_def_a.data["id"], "status": "COMPLETED"},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"saved_report_id": resp_sr_a.data["id"], "export_format": "CSV"},
            format="json",
        )

        # Tenant B setup: definition + saved report + export job
        resp_def_b = other_tenant_client.post(
            DEFINITIONS_URL,
            {"name": "B Def", "report_type": "stock"},
            format="json",
        )
        resp_sr_b = other_tenant_client.post(
            SAVED_REPORTS_URL,
            {"report_definition_id": resp_def_b.data["id"], "status": "COMPLETED"},
            format="json",
        )
        other_tenant_client.post(
            BASE_URL,
            {"saved_report_id": resp_sr_b.data["id"], "export_format": "PDF"},
            format="json",
        )

        # Tenant A list should not include Tenant B's export jobs
        response_a = authenticated_client.get(BASE_URL)
        ids_a = [r["id"] for r in response_a.data["results"]]

        response_b = other_tenant_client.get(BASE_URL)
        ids_b = [r["id"] for r in response_b.data["results"]]

        # No overlap
        assert not set(ids_a) & set(ids_b)

    def test_cross_tenant_retrieve_returns_404(
        self, authenticated_client, other_tenant_client
    ):
        """Retrieve an export job from another tenant → 404."""
        # Tenant A creates full chain
        resp_def = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Hidden Def", "report_type": "fiscal"},
            format="json",
        )
        resp_sr = authenticated_client.post(
            SAVED_REPORTS_URL,
            {"report_definition_id": resp_def.data["id"], "status": "COMPLETED"},
            format="json",
        )
        resp_job = authenticated_client.post(
            BASE_URL,
            {"saved_report_id": resp_sr.data["id"], "export_format": "CSV"},
            format="json",
        )
        assert resp_job.status_code == 201
        pk = resp_job.data["id"]

        # Tenant B tries to access it → 404
        response = other_tenant_client.get(_export_job_url(pk))
        assert response.status_code == 404

    def test_unauthenticated_access_rejected(self, api_client):
        """Unauthenticated requests → 401."""
        response = api_client.get(BASE_URL)
        assert response.status_code == 401
