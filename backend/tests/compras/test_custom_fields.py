"""
Tests for PurchaseOrder custom fields (T038).

Covers: define fields (text, number, required), create PO with valid custom_data,
create PO missing required field (rejected), update with partial custom_data
(merge behavior), tenant without definitions (custom_data optional),
attempt to update custom_data on confirmed PO (rejected).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework import status

from apps.compras.models import PurchaseOrder, PurchaseOrderStatus, Supplier
from apps.core.models.customization import TenantFieldDefinition

pytestmark = [pytest.mark.django_db(transaction=True)]

PO_URL = "/api/v1/compras/purchase-orders/"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def supplier(tenant_context):
    return Supplier.objects.create(
        tenant=tenant_context,
        name="Custom Fields Supplier",
    )


@pytest.fixture
def po_field_definitions(tenant_context):
    """Create custom field definitions for purchase_order entity type."""
    defs = []
    defs.append(
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            entity_type="purchase_order",
            field_key="project_code",
            label="Project Code",
            field_type="text",
            required=True,
        )
    )
    defs.append(
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            entity_type="purchase_order",
            field_key="priority_level",
            label="Priority Level",
            field_type="integer",
            required=False,
            default_value=1,
        )
    )
    defs.append(
        TenantFieldDefinition.objects.create(
            tenant=tenant_context,
            entity_type="purchase_order",
            field_key="is_urgent",
            label="Is Urgent",
            field_type="boolean",
            required=False,
            default_value=False,
        )
    )
    return defs


def _po_data(supplier, product, custom_data=None, order_number="PO-CF-001"):
    """Helper to build PO creation payload."""
    data = {
        "supplier": str(supplier.id),
        "order_number": order_number,
        "order_date": "2026-02-24",
        "items": [
            {
                "product": str(product.id),
                "quantity": "5.000",
                "unit_price": "10.000",
            }
        ],
    }
    if custom_data is not None:
        data["custom_data"] = custom_data
    return data


# ============================================================
# TestCustomFieldsCreate
# ============================================================


class TestCustomFieldsCreate:
    """Test custom fields on PO creation."""

    def test_create_po_with_valid_custom_data(
        self, authenticated_client, supplier, product, po_field_definitions
    ):
        """Create PO with valid custom_data passes validation."""
        data = _po_data(supplier, product, custom_data={"project_code": "PRJ-100"})
        resp = authenticated_client.post(PO_URL, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["custom_data"]["project_code"] == "PRJ-100"
        # Default values should be applied for missing optional fields
        assert resp.data["custom_data"]["priority_level"] == 1
        assert resp.data["custom_data"]["is_urgent"] is False

    def test_create_po_missing_required_field_rejected(
        self, authenticated_client, supplier, product, po_field_definitions
    ):
        """Create PO without required field is rejected."""
        data = _po_data(
            supplier, product,
            custom_data={"priority_level": 5},
            order_number="PO-CF-002",
        )
        resp = authenticated_client.post(PO_URL, data, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_po_no_definitions_optional(
        self, authenticated_client, supplier, product
    ):
        """Tenant without field definitions can create PO with empty custom_data."""
        data = _po_data(supplier, product, order_number="PO-CF-003")
        resp = authenticated_client.post(PO_URL, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_po_no_definitions_with_arbitrary_data(
        self, authenticated_client, supplier, product
    ):
        """Tenant without definitions can pass arbitrary custom_data (no validation)."""
        data = _po_data(
            supplier, product,
            custom_data={"anything": "goes"},
            order_number="PO-CF-004",
        )
        resp = authenticated_client.post(PO_URL, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["custom_data"]["anything"] == "goes"


# ============================================================
# TestCustomFieldsUpdate
# ============================================================


class TestCustomFieldsUpdate:
    """Test custom fields on PO update."""

    def test_update_custom_data_merge(
        self, authenticated_client, supplier, product, po_field_definitions
    ):
        """Partial update merges custom_data."""
        # Create PO
        data = _po_data(supplier, product, custom_data={"project_code": "PRJ-200"})
        resp = authenticated_client.post(PO_URL, data, format="json")
        po_id = resp.data["id"]

        # Partial update — change priority_level, keep project_code
        patch_data = {"custom_data": {"priority_level": 9}}
        resp_patch = authenticated_client.patch(
            f"{PO_URL}{po_id}/", patch_data, format="json"
        )
        assert resp_patch.status_code == status.HTTP_200_OK
        assert resp_patch.data["custom_data"]["project_code"] == "PRJ-200"
        assert resp_patch.data["custom_data"]["priority_level"] == 9

    def test_update_custom_data_on_confirmed_po_rejected(
        self, authenticated_client, supplier, product, po_field_definitions
    ):
        """Cannot update custom_data on CONFIRMED PO (locked per mutability rules)."""
        # Create + confirm PO
        data = _po_data(
            supplier, product,
            custom_data={"project_code": "PRJ-300"},
            order_number="PO-CF-LOCK",
        )
        resp = authenticated_client.post(PO_URL, data, format="json")
        po_id = resp.data["id"]

        # Confirm the PO
        authenticated_client.post(f"{PO_URL}{po_id}/confirm/")

        # Try to update custom_data — should be rejected
        patch_data = {"custom_data": {"priority_level": 5}}
        resp_patch = authenticated_client.patch(
            f"{PO_URL}{po_id}/", patch_data, format="json"
        )
        assert resp_patch.status_code == status.HTTP_400_BAD_REQUEST
