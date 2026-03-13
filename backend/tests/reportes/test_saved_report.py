"""
T050: SavedReport CRUD + filter + tenant isolation tests.

Tests SavedReportViewSet endpoints:
- Create, read, delete (no update — read-only after creation)
- Filter by status
- Filter by report_definition_id
- Tenant isolation (cross-tenant access returns 404)
"""

import pytest

DEFINITIONS_URL = "/api/v1/reportes/definitions/"
BASE_URL = "/api/v1/reportes/saved-reports/"


def _saved_report_url(pk):
    """Build detail URL for a saved report."""
    return f"{BASE_URL}{pk}/"


@pytest.fixture
def report_definition(authenticated_client):
    """Create a ReportDefinition and return its data."""
    response = authenticated_client.post(
        DEFINITIONS_URL,
        {"name": "Test Definition", "report_type": "sales"},
        format="json",
    )
    assert response.status_code == 201
    return response.data


@pytest.fixture
def saved_report(authenticated_client, report_definition):
    """Create a SavedReport via API and return the response data."""
    response = authenticated_client.post(
        BASE_URL,
        {
            "report_definition_id": report_definition["id"],
            "status": "PENDING",
            "result_metadata": {},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    return response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestSavedReportCrud:
    """T050: SavedReportViewSet API CRUD tests."""

    # --- Create ---

    def test_create_saved_report(self, authenticated_client, report_definition):
        """POST with valid data → 201 with all fields."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "report_definition_id": report_definition["id"],
                "status": "PENDING",
            },
            format="json",
        )
        assert response.status_code == 201
        assert str(response.data["report_definition_id"]) == report_definition["id"]
        assert response.data["status"] == "PENDING"
        assert "id" in response.data
        assert "generated_at" in response.data

    def test_create_saved_report_with_metadata(self, authenticated_client, report_definition):
        """POST with result_metadata → 201 with metadata stored."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "report_definition_id": report_definition["id"],
                "result_metadata": {"row_count": 150, "duration_ms": 432},
                "status": "COMPLETED",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["result_metadata"]["row_count"] == 150
        assert response.data["status"] == "COMPLETED"

    def test_create_saved_report_with_file_reference(
        self, authenticated_client, report_definition
    ):
        """POST with file_reference → 201 with reference stored."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "report_definition_id": report_definition["id"],
                "file_reference": "reports/2026/01/monthly_sales.csv",
                "status": "COMPLETED",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["file_reference"] == "reports/2026/01/monthly_sales.csv"

    def test_create_saved_report_missing_definition(self, authenticated_client):
        """POST without report_definition_id → 400."""
        response = authenticated_client.post(
            BASE_URL,
            {"status": "PENDING"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_saved_report_invalid_status(
        self, authenticated_client, report_definition
    ):
        """POST with invalid status → 400."""
        response = authenticated_client.post(
            BASE_URL,
            {
                "report_definition_id": report_definition["id"],
                "status": "RUNNING",  # Not a valid choice
            },
            format="json",
        )
        assert response.status_code == 400

    # --- List ---

    def test_list_saved_reports(self, authenticated_client, saved_report):
        """GET /saved-reports/ returns paginated list."""
        response = authenticated_client.get(BASE_URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    # --- Retrieve ---

    def test_retrieve_saved_report(self, authenticated_client, saved_report):
        """GET /saved-reports/{id}/ returns detail."""
        pk = saved_report["id"]
        response = authenticated_client.get(_saved_report_url(pk))
        assert response.status_code == 200
        assert response.data["id"] == pk

    def test_retrieve_nonexistent(self, authenticated_client):
        """GET /saved-reports/{id}/ with unknown UUID → 404."""
        import uuid
        response = authenticated_client.get(_saved_report_url(uuid.uuid4()))
        assert response.status_code == 404

    # --- No Update ---

    def test_update_not_allowed(self, authenticated_client, saved_report):
        """PATCH /saved-reports/{id}/ → 405 Method Not Allowed."""
        pk = saved_report["id"]
        response = authenticated_client.patch(
            _saved_report_url(pk),
            {"status": "COMPLETED"},
            format="json",
        )
        assert response.status_code == 405

    # --- Delete ---

    def test_delete_saved_report(self, authenticated_client, saved_report):
        """DELETE /saved-reports/{id}/ → 204."""
        pk = saved_report["id"]
        response = authenticated_client.delete(_saved_report_url(pk))
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(_saved_report_url(pk))
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestSavedReportFilters:
    """Filter tests for SavedReportViewSet."""

    def test_filter_by_status_pending(self, authenticated_client, report_definition):
        """GET ?status=PENDING returns only PENDING reports."""
        # Create PENDING
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": report_definition["id"], "status": "PENDING"},
            format="json",
        )
        # Create COMPLETED
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": report_definition["id"], "status": "COMPLETED"},
            format="json",
        )

        response = authenticated_client.get(BASE_URL, {"status": "PENDING"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["status"] == "PENDING" for r in results)
        assert len(results) >= 1

    def test_filter_by_status_completed(self, authenticated_client, report_definition):
        """GET ?status=COMPLETED returns only COMPLETED reports."""
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": report_definition["id"], "status": "PENDING"},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": report_definition["id"], "status": "COMPLETED"},
            format="json",
        )

        response = authenticated_client.get(BASE_URL, {"status": "COMPLETED"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["status"] == "COMPLETED" for r in results)

    def test_filter_by_report_definition_id(self, authenticated_client):
        """GET ?report_definition_id=X returns only reports for that definition."""
        # Create two report definitions
        resp_a = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Def A", "report_type": "sales"},
            format="json",
        )
        resp_b = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Def B", "report_type": "stock"},
            format="json",
        )
        def_id_a = resp_a.data["id"]
        def_id_b = resp_b.data["id"]

        # Create a saved report for each
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": def_id_a, "status": "PENDING"},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": def_id_b, "status": "PENDING"},
            format="json",
        )

        # Filter by def_id_a
        response = authenticated_client.get(
            BASE_URL, {"report_definition_id": def_id_a}
        )
        assert response.status_code == 200
        results = response.data["results"]
        assert all(str(r["report_definition_id"]) == def_id_a for r in results)
        assert len(results) >= 1


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestSavedReportTenantIsolation:
    """Tenant isolation tests for SavedReportViewSet."""

    def test_cross_tenant_definition_rejected_on_create(
        self, authenticated_client, other_tenant_client
    ):
        """Creating a SavedReport referencing another tenant's definition → 400."""
        # Tenant A creates a definition
        resp = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Tenant A Def", "report_type": "sales"},
            format="json",
        )
        assert resp.status_code == 201
        def_id = resp.data["id"]

        # Tenant B tries to create a SavedReport referencing Tenant A's definition
        response = other_tenant_client.post(
            BASE_URL,
            {"report_definition_id": def_id, "status": "PENDING"},
            format="json",
        )
        assert response.status_code == 400

    def test_list_only_own_tenant_reports(
        self, authenticated_client, other_tenant_client
    ):
        """Tenants only see their own saved reports."""
        # Tenant A creates definition + saved report
        resp_def_a = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "A Def", "report_type": "sales"},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"report_definition_id": resp_def_a.data["id"], "status": "PENDING"},
            format="json",
        )

        # Tenant B creates definition + saved report
        resp_def_b = other_tenant_client.post(
            DEFINITIONS_URL,
            {"name": "B Def", "report_type": "stock"},
            format="json",
        )
        other_tenant_client.post(
            BASE_URL,
            {"report_definition_id": resp_def_b.data["id"], "status": "COMPLETED"},
            format="json",
        )

        # Tenant A list should not include Tenant B's report
        response_a = authenticated_client.get(BASE_URL)
        ids_a = [r["id"] for r in response_a.data["results"]]

        response_b = other_tenant_client.get(BASE_URL)
        ids_b = [r["id"] for r in response_b.data["results"]]

        # No overlap
        assert not set(ids_a) & set(ids_b)

    def test_cross_tenant_retrieve_returns_404(
        self, authenticated_client, other_tenant_client
    ):
        """Retrieve a saved report from another tenant → 404."""
        # Tenant A creates definition + saved report
        resp_def = authenticated_client.post(
            DEFINITIONS_URL,
            {"name": "Isolated Def", "report_type": "fiscal"},
            format="json",
        )
        resp_sr = authenticated_client.post(
            BASE_URL,
            {"report_definition_id": resp_def.data["id"], "status": "PENDING"},
            format="json",
        )
        assert resp_sr.status_code == 201
        pk = resp_sr.data["id"]

        # Tenant B tries to access it → 404
        response = other_tenant_client.get(_saved_report_url(pk))
        assert response.status_code == 404
