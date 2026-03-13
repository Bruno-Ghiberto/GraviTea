"""
drf-spectacular schema definitions for sync views.

Provides OpenAPI schema documentation for offline-first POS synchronization
endpoints, including sync sessions, push/pull operations, and status monitoring.

Follows RFC 7807 error response standards and documents all sync workflows.
"""

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers, status

from apps.core.exceptions.serializers import (
    FieldErrorSerializer,
    ProblemDetailSerializer,
    ValidationErrorSerializer,
)
from apps.sync.serializers import SyncPullSerializer, SyncPushSerializer


# ============================================================================
# Response Serializers for Complex Responses
# ============================================================================


class SyncPushResponseSerializer(serializers.Serializer):
    """Response format for sync push operations."""

    status = serializers.ChoiceField(
        choices=["accepted"], help_text="Operation status (always 'accepted' on success)"
    )
    created = serializers.IntegerField(
        help_text="Number of operations successfully created and queued"
    )
    skipped = serializers.IntegerField(
        help_text="Number of operations skipped due to idempotency (already exist)"
    )
    errors = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of operations that failed validation with error details",
    )
    server_timestamp = serializers.DateTimeField(
        help_text="Server timestamp for sync vector tracking"
    )


class SyncStatusResponseSerializer(serializers.Serializer):
    """Response format for sync status endpoint."""

    device_id = serializers.CharField(help_text="Device identifier")
    status = serializers.CharField(
        help_text="Current sync status (pending, processing, completed, error)"
    )
    last_sync_at = serializers.DateTimeField(
        allow_null=True, help_text="Timestamp of last successful sync"
    )
    pending_operations = serializers.IntegerField(
        help_text="Number of operations pending server-side processing"
    )
    conflicts = serializers.IntegerField(
        help_text="Number of operations with detected conflicts requiring resolution"
    )
    sync_vector = serializers.JSONField(
        help_text="Sync vector state tracking per-entity sync progress"
    )


# ============================================================================
# OpenAPI Examples
# ============================================================================

SYNC_SESSION_CREATE_EXAMPLE = OpenApiExample(
    name="Register POS Terminal",
    description="Register a new POS terminal for offline synchronization",
    value={
        "branch": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "device_id": "POS-BRANCH-001-TERMINAL-01",
    },
    request_only=True,
)

SYNC_SESSION_RESPONSE_EXAMPLE = OpenApiExample(
    name="Registered Session",
    description="Successfully registered sync session",
    value={
        "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        "branch": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "branch_name": "Downtown Store",
        "device_id": "POS-BRANCH-001-TERMINAL-01",
        "last_sync_at": None,
        "sync_vector": {},
        "status": "pending",
        "error_message": None,
        "created_at": "2025-12-03T10:00:00Z",
        "updated_at": "2025-12-03T10:00:00Z",
    },
    response_only=True,
    status_codes=[str(status.HTTP_201_CREATED)],
)

SYNC_PUSH_REQUEST_EXAMPLE = OpenApiExample(
    name="Push Offline Operations",
    description="Push batch of offline operations from POS terminal",
    value={
        "device_id": "POS-BRANCH-001-TERMINAL-01",
        "sync_vector": {"Sale": 42, "Payment": 15},
        "operations": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "operation_type": "create",
                "entity_type": "Sale",
                "entity_id": "local-sale-001",
                "payload": {
                    "items": [
                        {"product_id": "prod-123", "quantity": 2, "unit_price": "19.99"}
                    ],
                    "total": "39.98",
                },
                "client_timestamp": "2025-12-03T09:30:00Z",
            }
        ],
    },
    request_only=True,
)

SYNC_PUSH_RESPONSE_EXAMPLE = OpenApiExample(
    name="Push Accepted",
    description="Operations successfully queued for processing",
    value={
        "status": "accepted",
        "created": 1,
        "skipped": 0,
        "errors": [],
        "server_timestamp": "2025-12-03T10:05:00Z",
    },
    response_only=True,
    status_codes=[str(status.HTTP_200_OK)],
)

SYNC_PULL_REQUEST_EXAMPLE = OpenApiExample(
    name="Pull Server Changes",
    description="Request changes from server since last sync",
    value={
        "device_id": "POS-BRANCH-001-TERMINAL-01",
        "last_sync_at": "2025-12-03T09:00:00Z",
        "entity_types": ["Product", "BranchStock"],
    },
    request_only=True,
)

SYNC_PULL_RESPONSE_EXAMPLE = OpenApiExample(
    name="Pull Changes",
    description="Server changes since last sync",
    value={
        "server_timestamp": "2025-12-03T10:10:00Z",
        "has_more": False,
        "next_cursor": None,
        "changes": {
            "Product": [
                {
                    "id": "prod-123",
                    "sku": "WIDGET-001",
                    "name": "Super Widget",
                    "price": "29.99",
                    "updated_at": "2025-12-03T09:15:00Z",
                }
            ],
            "BranchStock": [
                {
                    "id": "stock-456",
                    "product": "prod-123",
                    "branch": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "quantity": 150,
                    "last_updated": "2025-12-03T09:15:00Z",
                }
            ],
        },
    },
    response_only=True,
    status_codes=[str(status.HTTP_200_OK)],
)

SYNC_STATUS_RESPONSE_EXAMPLE = OpenApiExample(
    name="Sync Status",
    description="Current sync status for device",
    value={
        "device_id": "POS-BRANCH-001-TERMINAL-01",
        "status": "pending",
        "last_sync_at": "2025-12-03T09:00:00Z",
        "pending_operations": 3,
        "conflicts": 0,
        "sync_vector": {"Sale": 42, "Payment": 15},
    },
    response_only=True,
    status_codes=[str(status.HTTP_200_OK)],
)

ERROR_VALIDATION_EXAMPLE = OpenApiExample(
    name="Validation Error",
    description="Request validation failed",
    value={
        "type": "https://api.gravitea.com/errors/validation-error",
        "title": "Validation Error",
        "status": 400,
        "detail": "The request body contains invalid data",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "errors": [
            {
                "field": "device_id",
                "message": "This field is required.",
                "code": "required",
            }
        ],
    },
    response_only=True,
    status_codes=[str(status.HTTP_400_BAD_REQUEST)],
)

ERROR_NOT_FOUND_EXAMPLE = OpenApiExample(
    name="Device Not Found",
    description="Sync session not found for device",
    value={
        "type": "https://api.gravitea.com/errors/not-found",
        "title": "Not Found",
        "status": 404,
        "detail": "Device not registered.",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    },
    response_only=True,
    status_codes=[str(status.HTTP_404_NOT_FOUND)],
)

ERROR_CONFLICT_EXAMPLE = OpenApiExample(
    name="Device Already Registered",
    description="Device ID already exists",
    value={
        "type": "https://api.gravitea.com/errors/validation-error",
        "title": "Validation Error",
        "status": 400,
        "detail": "Device registration validation failed",
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "errors": [
            {
                "field": "device_id",
                "message": "A device with this ID is already registered.",
                "code": "unique",
            }
        ],
    },
    response_only=True,
    status_codes=[str(status.HTTP_400_BAD_REQUEST)],
)

# ============================================================================
# ViewSet Schema Decorators
# ============================================================================

sync_session_viewset_schema = extend_schema_view(
    list=extend_schema(
        summary="List sync sessions",
        description=(
            "Retrieve all registered POS terminals for the current tenant.\n\n"
            "Returns a list of sync sessions with their current status, last sync "
            "timestamp, and branch information. Use this endpoint to monitor all "
            "registered devices and their synchronization state."
        ),
        tags=["Sync Management"],
        responses={
            200: OpenApiResponse(
                description="List of sync sessions retrieved successfully"
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Authentication credentials were not provided or are invalid",
            ),
        },
    ),
    create=extend_schema(
        summary="Register POS terminal",
        description=(
            "Register a new POS terminal for offline synchronization.\n\n"
            "Creates a sync session that tracks the device's synchronization state. "
            "The device_id must be unique within the tenant. Returns the created "
            "session with initial status and empty sync vector.\n\n"
            "**Sync Session Lifecycle:**\n"
            "1. Register device (this endpoint)\n"
            "2. Push offline operations periodically\n"
            "3. Pull server changes periodically\n"
            "4. Monitor status for conflicts or errors\n"
            "5. Unregister device when decommissioning"
        ),
        tags=["Sync Management"],
        examples=[
            SYNC_SESSION_CREATE_EXAMPLE,
            SYNC_SESSION_RESPONSE_EXAMPLE,
            ERROR_CONFLICT_EXAMPLE,
        ],
        responses={
            201: OpenApiResponse(
                description="POS terminal registered successfully"
            ),
            400: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Validation failed - device_id already exists or branch invalid",
                examples=[ERROR_CONFLICT_EXAMPLE],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Authentication credentials required",
            ),
        },
    ),
    retrieve=extend_schema(
        summary="Get sync session details",
        description=(
            "Retrieve detailed information about a specific sync session.\n\n"
            "Returns the session's current status, sync vector state, last sync "
            "timestamp, and any error messages. Use this to inspect a specific "
            "device's synchronization configuration and state."
        ),
        tags=["Sync Management"],
        responses={
            200: OpenApiResponse(
                description="Sync session details retrieved successfully"
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Sync session not found",
                examples=[ERROR_NOT_FOUND_EXAMPLE],
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Authentication required",
            ),
        },
    ),
    destroy=extend_schema(
        summary="Unregister POS terminal",
        description=(
            "Unregister a POS terminal and delete its sync session.\n\n"
            "This removes the sync session and deletes all pending operations for "
            "this device. Use this endpoint when decommissioning a POS terminal or "
            "resetting its sync state.\n\n"
            "**Warning:** This operation cannot be undone. Any pending operations "
            "for this device will be permanently deleted."
        ),
        tags=["Sync Management"],
        responses={
            204: OpenApiResponse(
                description="POS terminal unregistered successfully"
            ),
            404: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Sync session not found",
            ),
            401: OpenApiResponse(
                response=ProblemDetailSerializer,
                description="Authentication required",
            ),
        },
    ),
)


# ============================================================================
# APIView Schema Decorators
# ============================================================================

sync_push_schema = extend_schema(
    summary="Push offline operations",
    description=(
        "Accept batch of operations created offline for server-side processing.\n\n"
        "POS terminals collect operations while offline and push them to the server "
        "when connectivity is restored. Operations use client-generated UUIDs for "
        "idempotency - duplicate operations with the same ID are automatically skipped.\n\n"
        "**Operation Processing:**\n"
        "1. Validate device registration\n"
        "2. Check each operation for idempotency\n"
        "3. Queue new operations for background processing\n"
        "4. Skip operations that already exist\n"
        "5. Return summary with created/skipped/error counts\n\n"
        "**Sync Vector:**\n"
        "The sync_vector tracks the client's current sync state per entity type. "
        "Update this after successful pulls to inform the server of your latest state."
    ),
    tags=["Sync Operations"],
    request=SyncPushSerializer,
    examples=[
        SYNC_PUSH_REQUEST_EXAMPLE,
        SYNC_PUSH_RESPONSE_EXAMPLE,
        ERROR_VALIDATION_EXAMPLE,
        ERROR_NOT_FOUND_EXAMPLE,
    ],
    responses={
        200: OpenApiResponse(
            response=SyncPushResponseSerializer,
            description=(
                "Operations accepted and queued for processing. Check the response "
                "for created/skipped/error counts to verify successful submission."
            ),
            examples=[SYNC_PUSH_RESPONSE_EXAMPLE],
        ),
        400: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Validation failed - invalid operation data or unregistered device",
            examples=[ERROR_VALIDATION_EXAMPLE],
        ),
        404: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Device not registered - register device first",
            examples=[ERROR_NOT_FOUND_EXAMPLE],
        ),
        401: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Authentication required",
        ),
    },
)

sync_pull_schema = extend_schema(
    summary="Pull server changes",
    description=(
        "Retrieve changes from server since last synchronization.\n\n"
        "POS terminals periodically pull changes to stay synchronized with the server. "
        "Changes include new products, stock updates, price changes, and other entity "
        "modifications since the last_sync_at timestamp.\n\n"
        "**Pull Process:**\n"
        "1. Specify last_sync_at timestamp (or omit for initial sync)\n"
        "2. Optionally filter by entity_types (e.g., ['Product', 'BranchStock'])\n"
        "3. Server returns all changes since that timestamp\n"
        "4. Update local database with received changes\n"
        "5. Store server_timestamp for next pull request\n\n"
        "**Pagination:**\n"
        "Large changesets use cursor-based pagination. If has_more is true, use the "
        "next_cursor value in a follow-up request to retrieve additional changes.\n\n"
        "**Entity Types:**\n"
        "Common entity types: Product, BranchStock, Category, PaymentMethod, User"
    ),
    tags=["Sync Operations"],
    request=SyncPullSerializer,
    examples=[
        SYNC_PULL_REQUEST_EXAMPLE,
        SYNC_PULL_RESPONSE_EXAMPLE,
        ERROR_NOT_FOUND_EXAMPLE,
    ],
    responses={
        200: OpenApiResponse(
            description=(
                "Changes retrieved successfully. Apply the changes to your local "
                "database and store server_timestamp for the next pull request."
            ),
            examples=[SYNC_PULL_RESPONSE_EXAMPLE],
        ),
        404: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Device not registered - register device first",
            examples=[ERROR_NOT_FOUND_EXAMPLE],
        ),
        401: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Authentication required",
        ),
    },
)

sync_status_schema = extend_schema(
    summary="Get sync status",
    description=(
        "Retrieve current sync status and pending operations for a device.\n\n"
        "Use this endpoint to monitor sync health and detect issues:\n"
        "- Check for pending operations awaiting server processing\n"
        "- Detect conflicts requiring manual resolution\n"
        "- Verify last successful sync timestamp\n"
        "- Monitor sync vector state\n\n"
        "**Status Values:**\n"
        "- `pending`: Operations queued, not yet processed\n"
        "- `processing`: Server actively processing operations\n"
        "- `completed`: All operations processed successfully\n"
        "- `error`: Processing failed, check error_message\n\n"
        "**Monitoring Recommendations:**\n"
        "- Poll this endpoint every 5-10 minutes during business hours\n"
        "- Alert if pending_operations exceeds threshold (e.g., 100)\n"
        "- Alert if conflicts > 0 - manual intervention required\n"
        "- Alert if status is 'error' for extended period"
    ),
    tags=["Sync Operations"],
    parameters=[
        OpenApiParameter(
            name="device_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Device identifier (e.g., 'POS-BRANCH-001-TERMINAL-01')",
            required=True,
        )
    ],
    examples=[
        SYNC_STATUS_RESPONSE_EXAMPLE,
        ERROR_NOT_FOUND_EXAMPLE,
    ],
    responses={
        200: OpenApiResponse(
            response=SyncStatusResponseSerializer,
            description="Sync status retrieved successfully",
            examples=[SYNC_STATUS_RESPONSE_EXAMPLE],
        ),
        404: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Device not registered - register device first",
            examples=[ERROR_NOT_FOUND_EXAMPLE],
        ),
        401: OpenApiResponse(
            response=ProblemDetailSerializer,
            description="Authentication required",
        ),
    },
)
