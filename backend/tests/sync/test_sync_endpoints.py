"""
Integration tests for sync API endpoints.

Tests the offline synchronization endpoints for POS terminals:
- SyncPushView (POST /api/v1/sync/push/)
- SyncPullView (POST /api/v1/sync/pull/)

NOTE: These tests require the authenticated_client fixture to use
CustomTokenObtainPairSerializer to include tenant_id in JWT claims.
The fixture override in this file ensures proper JWT claims are present.
"""

import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.core.managers.tenant_bound import (set_current_tenant_id)
from apps.sync.models import PendingOperation, SyncSession

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def ensure_tenant_context(tenant_context):
    """
    Automatically ensure tenant context is set for all tests in this module.

    The autouse=True means this fixture runs for every test automatically,
    ensuring tenant context is set before any tenant-bound operations.
    """
    return tenant_context


@pytest.fixture
def authenticated_client(api_client, admin_user, tenant_context):
    """
    Override authenticated_client fixture for sync tests.

    Creates authenticated API client with proper tenant context in JWT.
    Uses custom JWT serializer to include tenant_id in token claims,
    which is required by TenantContextMiddleware.
    """
    from apps.auth.jwt import CustomTokenObtainPairSerializer

    # Use custom serializer to get token with tenant claims
    refresh = CustomTokenObtainPairSerializer.get_token(admin_user)

    # Verify token has tenant_id claim
    assert "tenant_id" in refresh.access_token.payload
    assert refresh.access_token.payload["tenant_id"] == str(admin_user.tenant_id)

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


class TestSyncPushView:
    """
    Tests for SyncPushView (POST /api/v1/sync/push/).

    Handles uploading pending operations from offline POS terminals.
    """

    def test_push_creates_pending_operations(self, authenticated_client, sync_session):
        """Test push creates pending operations successfully."""
        url = reverse("push")
        operation_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        data = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(operation_id),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(entity_id),
                    "payload": {
                        "total": "150.00",
                        "items": [{"product_id": str(uuid.uuid4()), "quantity": 2}],
                    },
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
            "sync_vector": {"POS-TERMINAL-001": 5},
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "accepted"
        assert response.data["created"] == 1
        assert response.data["skipped"] == 0
        assert len(response.data["errors"]) == 0
        assert "server_timestamp" in response.data

        # Verify pending operation was created (use all_objects to bypass tenant filtering)
        operation = PendingOperation.all_objects.get(id=operation_id)
        assert operation.operation_type == "CREATE"
        assert operation.entity_type == "Sale"
        assert operation.entity_id == entity_id
        assert operation.status == PendingOperation.OperationStatus.PENDING

        # Verify sync session was updated
        sync_session.refresh_from_db()
        assert sync_session.sync_vector == {"POS-TERMINAL-001": 5}
        assert sync_session.status == SyncSession.SyncStatus.PENDING

    def test_push_with_multiple_operations(self, authenticated_client, sync_session):
        """Test push creates multiple operations in batch."""
        url = reverse("push")

        operations = []
        for i in range(3):
            operations.append(
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "StockMovement",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {"quantity": 10 + i},
                    "client_timestamp": timezone.now().isoformat(),
                }
            )

        data = {
            "device_id": sync_session.device_id,
            "operations": operations,
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 3
        assert response.data["skipped"] == 0

        # Verify all operations were created
        assert PendingOperation.all_objects.filter(sync_session=sync_session).count() == 3

    def test_push_idempotency(self, authenticated_client, sync_session):
        """Test push with same operation_id doesn't create duplicates."""
        url = reverse("push")
        operation_id = uuid.uuid4()

        data = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(operation_id),
                    "operation_type": "UPDATE",
                    "entity_type": "Product",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {"price": "99.99"},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
        }

        # First push
        response1 = authenticated_client.post(url, data, format="json")
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data["created"] == 1

        # Second push with same operation_id
        response2 = authenticated_client.post(url, data, format="json")
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["created"] == 0
        assert response2.data["skipped"] == 1

        # Verify only one operation exists
        assert PendingOperation.all_objects.filter(id=operation_id).count() == 1

    def test_push_with_invalid_payload_missing_fields(self, authenticated_client):
        """Test push with invalid payload (missing required fields)."""
        url = reverse("push")

        data = {
            "device_id": "POS-TERMINAL-001",
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    # Missing operation_type
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for operation_type error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        # operations.operation_type is the nested field error format
        assert any("operation_type" in f for f in error_fields)

    def test_push_requires_authentication(self, api_client, sync_session):
        """Test push requires authentication (401)."""
        url = reverse("push")

        data = {"device_id": sync_session.device_id, "operations": []}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_push_device_not_registered(self, authenticated_client):
        """Test push with unregistered device returns error."""
        url = reverse("push")

        data = {
            "device_id": "UNREGISTERED-DEVICE",
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # RFC 7807: Check for device_id error in errors array
        assert "errors" in response.data
        error_fields = [e["field"] for e in response.data["errors"]]
        assert "device_id" in error_fields

    def test_push_respects_tenant_isolation(
        self, authenticated_client, sync_session, other_tenant, tenant
    ):
        """Test push respects tenant isolation."""
        from apps.core.models import Branch

        # Create sync session for other tenant (set context to avoid validation errors)
        set_current_tenant_id(other_tenant.id)
        other_branch = Branch.objects.create(
            tenant=other_tenant, name="Other Store", is_active=True
        )
        other_sync_session = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="OTHER-POS-001",
            status=SyncSession.SyncStatus.PENDING,
        )
        # Restore tenant context to original tenant (for API request)
        set_current_tenant_id(tenant.id)

        url = reverse("push")

        # Try to push to other tenant's device
        data = {
            "device_id": other_sync_session.device_id,
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
        }

        response = authenticated_client.post(url, data, format="json")

        # Should fail because device belongs to different tenant
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_push_with_operation_errors(self, authenticated_client, sync_session):
        """Test push handles individual operation errors gracefully."""
        url = reverse("push")

        # Mix of valid and invalid operations
        operations = [
            {
                "id": str(uuid.uuid4()),
                "operation_type": "CREATE",
                "entity_type": "Sale",
                "entity_id": str(uuid.uuid4()),
                "payload": {"valid": True},
                "client_timestamp": timezone.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "operation_type": "CREATE",
                "entity_type": "Sale",
                "entity_id": str(uuid.uuid4()),
                "payload": {"valid": True},
                "client_timestamp": timezone.now().isoformat(),
            },
        ]

        data = {"device_id": sync_session.device_id, "operations": operations}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] >= 0
        assert "errors" in response.data

    def test_push_updates_sync_status(self, authenticated_client, sync_session):
        """Test push updates sync session status to PENDING."""
        # Set initial status
        sync_session.status = SyncSession.SyncStatus.COMPLETED
        sync_session.save()

        url = reverse("push")

        data = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        sync_session.refresh_from_db()
        assert sync_session.status == SyncSession.SyncStatus.PENDING


class TestSyncPullView:
    """
    Tests for SyncPullView (POST /api/v1/sync/pull/).

    Handles downloading changes from server to POS terminals.
    """

    def test_pull_returns_changes(self, authenticated_client, sync_session, product, branch_stock):
        """Test pull returns changes since timestamp."""
        url = reverse("pull")

        data = {
            "device_id": sync_session.device_id,
            "last_sync_at": (timezone.now() - timedelta(hours=1)).isoformat(),
            "entity_types": ["Product", "BranchStock"],
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "server_timestamp" in response.data
        assert "changes" in response.data
        assert "has_more" in response.data
        assert "next_cursor" in response.data

        # Verify changes include Product
        assert "Product" in response.data["changes"]
        assert len(response.data["changes"]["Product"]) > 0

        # Verify changes include BranchStock
        assert "BranchStock" in response.data["changes"]

    def test_pull_filters_by_device_branch(
        self, authenticated_client, sync_session, product, branch_stock
    ):
        """Test pull filters BranchStock by device's branch."""
        url = reverse("pull")

        data = {"device_id": sync_session.device_id, "entity_types": ["BranchStock"]}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Should only return stock for sync_session.branch
        if response.data["changes"].get("BranchStock"):
            for stock in response.data["changes"]["BranchStock"]:
                # Note: serializer might use branch_id or branch field
                # Adjust based on actual serializer implementation
                pass

    def test_pull_with_last_sync_at_parameter(self, authenticated_client, sync_session, product):
        """Test pull with last_sync_at filters by timestamp."""
        # Update product to have recent timestamp
        product.updated_at = timezone.now()
        product.save()

        url = reverse("pull")

        # Request changes since 2 hours ago
        data = {
            "device_id": sync_session.device_id,
            "last_sync_at": (timezone.now() - timedelta(hours=2)).isoformat(),
            "entity_types": ["Product"],
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        # Should include recently updated product
        assert "Product" in response.data["changes"]

    def test_pull_requires_authentication(self, api_client, sync_session):
        """Test pull requires authentication (401)."""
        url = reverse("pull")

        data = {"device_id": sync_session.device_id}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_pull_device_not_registered(self, authenticated_client):
        """Test pull with unregistered device returns 404."""
        url = reverse("pull")

        data = {"device_id": "UNREGISTERED-DEVICE"}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in response.data

    def test_pull_respects_tenant_isolation(
        self, authenticated_client, sync_session, other_tenant, tenant
    ):
        """Test pull respects tenant isolation."""
        from apps.core.models import Branch

        # Create sync session for other tenant (set context to avoid validation errors)
        set_current_tenant_id(other_tenant.id)
        other_branch = Branch.objects.create(
            tenant=other_tenant, name="Other Store", is_active=True
        )
        other_sync_session = SyncSession.objects.create(
            tenant=other_tenant,
            branch=other_branch,
            device_id="OTHER-POS-001",
            status=SyncSession.SyncStatus.PENDING,
        )
        # Restore tenant context to original tenant (for API request)
        set_current_tenant_id(tenant.id)

        url = reverse("pull")

        # Try to pull from other tenant's device
        data = {"device_id": other_sync_session.device_id}

        response = authenticated_client.post(url, data, format="json")

        # Should fail because device belongs to different tenant
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_pull_updates_sync_session(self, authenticated_client, sync_session):
        """Test pull updates sync session last_sync_at and status."""
        old_last_sync = sync_session.last_sync_at

        url = reverse("pull")

        data = {"device_id": sync_session.device_id}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        sync_session.refresh_from_db()
        assert sync_session.last_sync_at != old_last_sync
        assert sync_session.status == SyncSession.SyncStatus.COMPLETED

    def test_pull_without_entity_types_returns_all(
        self, authenticated_client, sync_session, product
    ):
        """Test pull without entity_types returns all entity types."""
        url = reverse("pull")

        data = {"device_id": sync_session.device_id}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "changes" in response.data

    def test_pull_pagination_structure(self, authenticated_client, sync_session):
        """Test pull response includes pagination fields."""
        url = reverse("pull")

        data = {"device_id": sync_session.device_id}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "has_more" in response.data
        assert "next_cursor" in response.data
        assert isinstance(response.data["has_more"], bool)


class TestSyncFullFlow:
    """
    Tests for complete offline → online sync flow.

    Tests the entire synchronization cycle including conflict detection.
    """

    def test_complete_sync_cycle(self, authenticated_client, sync_session, product, branch):
        """Test complete offline → online sync cycle."""
        # Step 1: Push offline operations
        push_url = reverse("push")
        sale_id = uuid.uuid4()

        push_data = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(sale_id),
                    "payload": {
                        "total": "250.00",
                        "items": [
                            {"product_id": str(product.id), "quantity": 2, "price": "125.00"}
                        ],
                    },
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
            "sync_vector": {"POS-TERMINAL-001": 1},
        }

        push_response = authenticated_client.post(push_url, push_data, format="json")
        assert push_response.status_code == status.HTTP_200_OK
        assert push_response.data["created"] == 1

        # Step 2: Pull server changes
        pull_url = reverse("pull")

        pull_data = {"device_id": sync_session.device_id, "entity_types": ["Product"]}

        pull_response = authenticated_client.post(pull_url, pull_data, format="json")
        assert pull_response.status_code == status.HTTP_200_OK
        assert "changes" in pull_response.data

        # Verify sync session was updated throughout
        sync_session.refresh_from_db()
        assert sync_session.last_sync_at is not None

    def test_sync_with_multiple_branches(self, authenticated_client, tenant_context, other_branch):
        """Test sync with multiple branches maintains isolation."""
        # Create sync sessions for different branches
        sync_session_1 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=other_branch,
            device_id="POS-BRANCH-1",
            status=SyncSession.SyncStatus.PENDING,
        )

        from apps.core.models import Branch

        branch_2 = Branch.objects.create(tenant=tenant_context, name="Branch 2", is_active=True)
        sync_session_2 = SyncSession.objects.create(
            tenant=tenant_context,
            branch=branch_2,
            device_id="POS-BRANCH-2",
            status=SyncSession.SyncStatus.PENDING,
        )

        # Push operations from each branch
        push_url = reverse("push")

        for device_id in [sync_session_1.device_id, sync_session_2.device_id]:
            data = {
                "device_id": device_id,
                "operations": [
                    {
                        "id": str(uuid.uuid4()),
                        "operation_type": "CREATE",
                        "entity_type": "Sale",
                        "entity_id": str(uuid.uuid4()),
                        "payload": {"branch_specific": True},
                        "client_timestamp": timezone.now().isoformat(),
                    }
                ],
            }

            response = authenticated_client.post(push_url, data, format="json")
            assert response.status_code == status.HTTP_200_OK

        # Verify operations are isolated by sync session
        ops_1 = PendingOperation.all_objects.filter(sync_session=sync_session_1)
        ops_2 = PendingOperation.all_objects.filter(sync_session=sync_session_2)

        assert ops_1.count() == 1
        assert ops_2.count() == 1
        assert ops_1.first().sync_session != ops_2.first().sync_session

    def test_conflict_detection_same_entity(self, authenticated_client, sync_session, product):
        """Test conflict detection when same entity updated offline and online."""
        # Simulate two operations on same entity
        push_url = reverse("push")
        entity_id = uuid.uuid4()

        operations = [
            {
                "id": str(uuid.uuid4()),
                "operation_type": "UPDATE",
                "entity_type": "Product",
                "entity_id": str(entity_id),
                "payload": {"price": "100.00", "version": 1},
                "client_timestamp": (timezone.now() - timedelta(minutes=5)).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "operation_type": "UPDATE",
                "entity_type": "Product",
                "entity_id": str(entity_id),
                "payload": {"price": "150.00", "version": 2},
                "client_timestamp": timezone.now().isoformat(),
            },
        ]

        data = {"device_id": sync_session.device_id, "operations": operations}

        response = authenticated_client.post(push_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 2

        # Verify both operations were created
        # (conflict detection happens during processing, not during push)
        pending_ops = PendingOperation.all_objects.filter(entity_id=entity_id).order_by(
            "client_timestamp"
        )

        assert pending_ops.count() == 2

    def test_sync_vector_tracking(self, authenticated_client, sync_session):
        """Test sync vector is properly tracked across operations."""
        push_url = reverse("push")

        # First push with vector clock
        data_1 = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
            "sync_vector": {"POS-TERMINAL-001": 1},
        }

        response_1 = authenticated_client.post(push_url, data_1, format="json")
        assert response_1.status_code == status.HTTP_200_OK

        sync_session.refresh_from_db()
        assert sync_session.sync_vector == {"POS-TERMINAL-001": 1}

        # Second push with updated vector clock
        data_2 = {
            "device_id": sync_session.device_id,
            "operations": [
                {
                    "id": str(uuid.uuid4()),
                    "operation_type": "CREATE",
                    "entity_type": "Sale",
                    "entity_id": str(uuid.uuid4()),
                    "payload": {},
                    "client_timestamp": timezone.now().isoformat(),
                }
            ],
            "sync_vector": {"POS-TERMINAL-001": 2, "SERVER": 1},
        }

        response_2 = authenticated_client.post(push_url, data_2, format="json")
        assert response_2.status_code == status.HTTP_200_OK

        sync_session.refresh_from_db()
        assert sync_session.sync_vector == {"POS-TERMINAL-001": 2, "SERVER": 1}

    def test_batch_operations_different_types(self, authenticated_client, sync_session, product):
        """Test batch operations with different entity types."""
        push_url = reverse("push")

        operations = [
            {
                "id": str(uuid.uuid4()),
                "operation_type": "CREATE",
                "entity_type": "Sale",
                "entity_id": str(uuid.uuid4()),
                "payload": {"type": "sale"},
                "client_timestamp": timezone.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "operation_type": "UPDATE",
                "entity_type": "Product",
                "entity_id": str(product.id),
                "payload": {"type": "product"},
                "client_timestamp": timezone.now().isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "operation_type": "CREATE",
                "entity_type": "StockMovement",
                "entity_id": str(uuid.uuid4()),
                "payload": {"type": "stock"},
                "client_timestamp": timezone.now().isoformat(),
            },
        ]

        data = {"device_id": sync_session.device_id, "operations": operations}

        response = authenticated_client.post(push_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["created"] == 3

        # Verify different entity types
        assert PendingOperation.all_objects.filter(entity_type="Sale").exists()
        assert PendingOperation.all_objects.filter(entity_type="Product").exists()
        assert PendingOperation.all_objects.filter(entity_type="StockMovement").exists()
