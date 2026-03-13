"""
T049: ReportDefinition CRUD + filter + tenant isolation tests.

Tests ReportDefinitionViewSet endpoints:
- Create, read, update, delete
- Filter by report_type
- Filter by is_active
- Tenant isolation (cross-tenant access returns 404)
"""

import pytest

BASE_URL = "/api/v1/reportes/definitions/"


def _definition_url(pk):
    """Build detail URL for a report definition."""
    return f"{BASE_URL}{pk}/"


@pytest.fixture
def report_definition_data():
    """Valid payload for creating a ReportDefinition."""
    return {
        "name": "Monthly Sales Report",
        "report_type": "sales",
        "parameters": {"period": "monthly"},
        "filters": {"date_from": "2026-01-01"},
        "output_format": "CSV",
        "is_active": True,
    }


@pytest.fixture
def report_definition(authenticated_client, report_definition_data):
    """Create a ReportDefinition via API and return the response data."""
    response = authenticated_client.post(BASE_URL, report_definition_data, format="json")
    assert response.status_code == 201, response.data
    return response.data


@pytest.mark.integration
@pytest.mark.django_db
class TestReportDefinitionCrud:
    """T049: ReportDefinitionViewSet API CRUD tests."""

    # --- Create ---

    def test_create_report_definition(self, authenticated_client, report_definition_data):
        """POST with valid data → 201 with all fields."""
        response = authenticated_client.post(BASE_URL, report_definition_data, format="json")
        assert response.status_code == 201
        assert response.data["name"] == "Monthly Sales Report"
        assert response.data["report_type"] == "sales"
        assert response.data["output_format"] == "CSV"
        assert response.data["is_active"] is True
        assert "id" in response.data
        assert "created_at" in response.data
        assert "updated_at" in response.data

    def test_create_report_definition_defaults(self, authenticated_client):
        """POST with only required fields → 201 with defaults applied."""
        response = authenticated_client.post(
            BASE_URL,
            {"name": "Minimal Report", "report_type": "stock"},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["output_format"] == "CSV"
        assert response.data["is_active"] is True
        assert response.data["parameters"] == {}
        assert response.data["filters"] == {}

    def test_create_report_definition_missing_required_fields(self, authenticated_client):
        """POST without name → 400 validation error."""
        response = authenticated_client.post(
            BASE_URL,
            {"report_type": "sales"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_report_definition_invalid_type(self, authenticated_client):
        """POST with invalid report_type → 400 validation error."""
        response = authenticated_client.post(
            BASE_URL,
            {"name": "Bad Type", "report_type": "invalid_type"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_report_definition_all_types(self, authenticated_client):
        """POST each valid report_type → 201."""
        valid_types = ["sales", "stock", "purchases", "fiscal", "accounting_export"]
        for i, rtype in enumerate(valid_types):
            response = authenticated_client.post(
                BASE_URL,
                {"name": f"Report {i}", "report_type": rtype},
                format="json",
            )
            assert response.status_code == 201, f"Failed for report_type={rtype}: {response.data}"

    # --- List ---

    def test_list_report_definitions(self, authenticated_client, report_definition):
        """GET /definitions/ returns paginated list with results key."""
        response = authenticated_client.get(BASE_URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    # --- Retrieve ---

    def test_retrieve_report_definition(self, authenticated_client, report_definition):
        """GET /definitions/{id}/ returns full detail."""
        pk = report_definition["id"]
        response = authenticated_client.get(_definition_url(pk))
        assert response.status_code == 200
        assert response.data["id"] == pk
        assert response.data["name"] == report_definition["name"]

    def test_retrieve_nonexistent(self, authenticated_client):
        """GET /definitions/{id}/ with unknown UUID → 404."""
        import uuid
        response = authenticated_client.get(_definition_url(uuid.uuid4()))
        assert response.status_code == 404

    # --- Update ---

    def test_update_report_definition(self, authenticated_client, report_definition):
        """PATCH /definitions/{id}/ → 200 with updated fields."""
        pk = report_definition["id"]
        response = authenticated_client.patch(
            _definition_url(pk),
            {"name": "Updated Report Name"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Updated Report Name"

    def test_full_update_report_definition(self, authenticated_client, report_definition):
        """PUT /definitions/{id}/ → 200 with all fields updated."""
        pk = report_definition["id"]
        response = authenticated_client.put(
            _definition_url(pk),
            {
                "name": "Full Update Report",
                "report_type": "fiscal",
                "parameters": {"quarter": "Q1"},
                "filters": {},
                "output_format": "PDF",
                "is_active": False,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["name"] == "Full Update Report"
        assert response.data["report_type"] == "fiscal"
        assert response.data["output_format"] == "PDF"
        assert response.data["is_active"] is False

    # --- Delete ---

    def test_delete_report_definition(self, authenticated_client, report_definition):
        """DELETE /definitions/{id}/ → 204."""
        pk = report_definition["id"]
        response = authenticated_client.delete(_definition_url(pk))
        assert response.status_code == 204

        # Verify it's gone
        response = authenticated_client.get(_definition_url(pk))
        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.django_db
class TestReportDefinitionFilters:
    """Filter tests for ReportDefinitionViewSet."""

    def test_filter_by_report_type(self, authenticated_client):
        """GET ?report_type=sales returns only sales reports."""
        # Create a sales and a stock report
        authenticated_client.post(
            BASE_URL,
            {"name": "Sales Report", "report_type": "sales"},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"name": "Stock Report", "report_type": "stock"},
            format="json",
        )

        response = authenticated_client.get(BASE_URL, {"report_type": "sales"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["report_type"] == "sales" for r in results)
        names = [r["name"] for r in results]
        assert "Sales Report" in names
        assert "Stock Report" not in names

    def test_filter_by_is_active_true(self, authenticated_client):
        """GET ?is_active=true returns only active definitions."""
        authenticated_client.post(
            BASE_URL,
            {"name": "Active Report", "report_type": "sales", "is_active": True},
            format="json",
        )
        # Create then deactivate one
        resp = authenticated_client.post(
            BASE_URL,
            {"name": "Inactive Report", "report_type": "sales", "is_active": False},
            format="json",
        )
        assert resp.status_code == 201

        response = authenticated_client.get(BASE_URL, {"is_active": "true"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["is_active"] is True for r in results)
        names = [r["name"] for r in results]
        assert "Active Report" in names

    def test_filter_by_is_active_false(self, authenticated_client):
        """GET ?is_active=false returns only inactive definitions."""
        authenticated_client.post(
            BASE_URL,
            {"name": "Active 2", "report_type": "stock", "is_active": True},
            format="json",
        )
        authenticated_client.post(
            BASE_URL,
            {"name": "Inactive 2", "report_type": "stock", "is_active": False},
            format="json",
        )

        response = authenticated_client.get(BASE_URL, {"is_active": "false"})
        assert response.status_code == 200
        results = response.data["results"]
        assert all(r["is_active"] is False for r in results)
        names = [r["name"] for r in results]
        assert "Inactive 2" in names


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.tenant_isolation
class TestReportDefinitionTenantIsolation:
    """Tenant isolation tests for ReportDefinitionViewSet."""

    def test_list_only_own_tenant_definitions(
        self, authenticated_client, other_tenant_client
    ):
        """Tenants only see their own report definitions."""
        # Tenant A creates a definition
        resp_a = authenticated_client.post(
            BASE_URL,
            {"name": "Tenant A Report", "report_type": "sales"},
            format="json",
        )
        assert resp_a.status_code == 201

        # Tenant B creates a definition
        resp_b = other_tenant_client.post(
            BASE_URL,
            {"name": "Tenant B Report", "report_type": "stock"},
            format="json",
        )
        assert resp_b.status_code == 201

        # Tenant A can only see their own
        response_a = authenticated_client.get(BASE_URL)
        names_a = [r["name"] for r in response_a.data["results"]]
        assert "Tenant A Report" in names_a
        assert "Tenant B Report" not in names_a

        # Tenant B can only see their own
        response_b = other_tenant_client.get(BASE_URL)
        names_b = [r["name"] for r in response_b.data["results"]]
        assert "Tenant B Report" in names_b
        assert "Tenant A Report" not in names_b

    def test_cross_tenant_retrieve_returns_404(
        self, authenticated_client, other_tenant_client
    ):
        """Retrieve a report definition from another tenant → 404."""
        # Tenant A creates a definition
        resp = authenticated_client.post(
            BASE_URL,
            {"name": "Tenant A Only", "report_type": "fiscal"},
            format="json",
        )
        assert resp.status_code == 201
        pk = resp.data["id"]

        # Tenant B tries to access it → 404
        response = other_tenant_client.get(_definition_url(pk))
        assert response.status_code == 404

    def test_unauthenticated_access_rejected(self, api_client):
        """Unauthenticated requests → 401."""
        response = api_client.get(BASE_URL)
        assert response.status_code == 401
