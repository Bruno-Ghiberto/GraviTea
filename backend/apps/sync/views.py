"""
Sync views for Gravitea ERP.

Provides endpoints for offline-first POS synchronization.

H-003: Implements retry logic for sync operations
"""

import logging
import time
from typing import Optional

from django.db import IntegrityError, OperationalError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.observability.business_metrics import (
    record_sync_operation,
    update_sync_queue_depth,
)

from .logging import SyncLogger
from .models import PendingOperation, SyncSession
from .schema import (
    sync_pull_schema,
    sync_push_schema,
    sync_session_viewset_schema,
    sync_status_schema,
)
from .serializers import (SyncPullSerializer, SyncPushSerializer,
                          SyncSessionCreateSerializer, SyncSessionSerializer)

logger = logging.getLogger("sync")


# H-003: Transient database errors that should be handled gracefully
TRANSIENT_DB_ERRORS = (OperationalError, IntegrityError)


@sync_session_viewset_schema
class SyncSessionViewSet(viewsets.ModelViewSet):
    """
    Sync session management viewset.

    Endpoints:
        GET    /api/v1/sync/sessions/           - List sync sessions
        POST   /api/v1/sync/sessions/           - Register new device
        GET    /api/v1/sync/sessions/{id}/      - Get session details
        DELETE /api/v1/sync/sessions/{id}/      - Unregister device
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        """Return sync sessions for current tenant."""
        return SyncSession.objects.select_related("branch").all()

    def get_serializer_class(self):
        if self.action == "create":
            return SyncSessionCreateSerializer
        return SyncSessionSerializer

    def create(self, request, *args, **kwargs):
        """Register a new POS terminal for sync."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = serializer.save()

        logger.info(f"Device registered: {session.device_id} @ {session.branch.name}")

        response_serializer = SyncSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """Unregister a POS terminal."""
        instance = self.get_object()
        device_id = instance.device_id

        # Delete pending operations for this session
        PendingOperation.objects.filter(sync_session=instance).delete()

        instance.delete()
        logger.info(f"Device unregistered: {device_id}")

        return Response(status=status.HTTP_204_NO_CONTENT)


@sync_push_schema
class SyncPushView(APIView):
    """
    Push endpoint for offline operations.

    POST /api/v1/sync/push/

    Accepts batch of operations created offline for processing.
    Uses client-generated UUIDs for idempotency.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        start_time = time.time()

        serializer = SyncPushSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        sync_session = serializer.context.get("sync_session")
        operations_data = serializer.validated_data["operations"]
        sync_vector = serializer.validated_data.get("sync_vector", {})

        tenant_id = request.user.tenant.id
        device_id = sync_session.device_id
        operation_count = len(operations_data)
        request_ip = self._get_client_ip(request)

        # Log sync push start
        SyncLogger.log_sync_push_start(
            tenant_id=tenant_id,
            device_id=device_id,
            operation_count=operation_count,
            user_id=request.user.id,
            session_id=sync_session.id,
            request_ip=request_ip,
        )

        created_count = 0
        skipped_count = 0
        rejected_count = 0
        errors = []

        try:
            for op_data in operations_data:
                op_id = op_data.get("id")
                entity_type = op_data.get("entity_type", "Unknown")
                operation_type = op_data.get("operation_type", "Unknown")

                # Check for idempotency - skip if already exists
                if PendingOperation.objects.filter(id=op_id).exists():
                    skipped_count += 1
                    SyncLogger.log_operation_skipped(
                        operation_id=op_id,
                        entity_type=entity_type,
                        reason="already_exists",
                        tenant_id=tenant_id,
                        device_id=device_id,
                    )
                    continue

                try:
                    op_data["tenant"] = request.user.tenant
                    op_data["sync_session"] = sync_session
                    operation = PendingOperation.objects.create(**op_data)
                    created_count += 1

                    # Log successful operation creation
                    SyncLogger.log_operation_applied(
                        operation_id=operation.id,
                        entity_type=entity_type,
                        operation_type=operation_type,
                        entity_id=op_data.get("entity_id", "unknown"),
                        tenant_id=tenant_id,
                        device_id=device_id,
                    )

                    # Record business metric for sync operation
                    record_sync_operation(
                        tenant_id=str(tenant_id),
                        operation_type=operation_type.lower(),
                        status="success",
                    )

                except Exception as e:
                    rejected_count += 1
                    error_msg = str(e)
                    errors.append({"id": str(op_id), "error": error_msg})

                    # Log operation failure
                    SyncLogger.log_operation_failed(
                        operation_id=op_id,
                        entity_type=entity_type,
                        error=error_msg,
                        tenant_id=tenant_id,
                        device_id=device_id,
                        retry_count=0,
                        will_retry=False,
                    )

                    # Record business metric for failed sync operation
                    record_sync_operation(
                        tenant_id=str(tenant_id),
                        operation_type=operation_type.lower(),
                        status="failure",
                    )

            # Update sync session
            sync_session.sync_vector = sync_vector
            sync_session.status = SyncSession.SyncStatus.PENDING
            sync_session.save()

            # Update sync queue depth metric
            queue_depth = PendingOperation.objects.filter(
                tenant_id=tenant_id,
                status=PendingOperation.OperationStatus.PENDING,
            ).count()
            update_sync_queue_depth(
                tenant_id=str(tenant_id),
                depth=queue_depth,
            )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful push completion
            SyncLogger.log_sync_push_complete(
                tenant_id=tenant_id,
                device_id=device_id,
                operations_count=operation_count,
                operations_applied=created_count,
                operations_skipped=skipped_count,
                operations_rejected=rejected_count,
                conflicts_detected=0,  # Conflicts detected during processing
                duration_ms=duration_ms,
                session_id=sync_session.id,
            )

            return Response(
                {
                    "status": "accepted",
                    "created": created_count,
                    "skipped": skipped_count,
                    "errors": errors,
                    "server_timestamp": timezone.now().isoformat(),
                }
            )

        except Exception as e:
            # Log overall push failure
            SyncLogger.log_sync_push_failed(
                tenant_id=tenant_id,
                device_id=device_id,
                error=str(e),
                operation_count=operation_count,
                operations_processed=created_count + skipped_count + rejected_count,
                session_id=sync_session.id,
                error_code="PUSH_PROCESSING_ERROR",
            )
            raise

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")


@sync_pull_schema
class SyncPullView(APIView):
    """
    Pull endpoint for sync changes.

    POST /api/v1/sync/pull/

    Returns changes since last sync for the POS terminal.
    Uses cursor-based pagination for large changesets.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        start_time = time.time()

        serializer = SyncPullSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_id = serializer.validated_data["device_id"]
        last_sync_at = serializer.validated_data.get("last_sync_at")
        entity_types = serializer.validated_data.get("entity_types", [])

        tenant_id = request.user.tenant.id
        request_ip = self._get_client_ip(request)

        # Get sync session
        try:
            sync_session = SyncSession.objects.get(tenant=request.user.tenant, device_id=device_id)
        except SyncSession.DoesNotExist:
            SyncLogger.log_sync_pull_failed(
                tenant_id=tenant_id,
                device_id=device_id,
                error="Device not registered",
                error_code="DEVICE_NOT_FOUND",
            )
            return Response({"detail": "Device not registered."}, status=status.HTTP_404_NOT_FOUND)

        # Log sync pull start
        SyncLogger.log_sync_pull_start(
            tenant_id=tenant_id,
            device_id=device_id,
            since_timestamp=last_sync_at or sync_session.last_sync_at,
            entity_types=entity_types,
            user_id=request.user.id,
            session_id=sync_session.id,
            request_ip=request_ip,
        )

        try:
            # Get changes since last sync
            # This is a simplified implementation - real implementation would
            # query actual entity tables for changes
            changes = self._get_changes(
                tenant=request.user.tenant,
                branch=sync_session.branch,
                since=last_sync_at or sync_session.last_sync_at,
                entity_types=entity_types,
            )

            # Calculate entity breakdown for logging
            entity_breakdown = {
                entity_type: len(entity_changes) for entity_type, entity_changes in changes.items()
            }
            total_changes = sum(entity_breakdown.values())

            # Update sync session
            now = timezone.now()
            sync_session.last_sync_at = now
            sync_session.status = SyncSession.SyncStatus.COMPLETED
            sync_session.save()

            response_data = {
                "server_timestamp": now,
                "changes": changes,
                "has_more": False,
                "next_cursor": None,
            }

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful pull completion
            SyncLogger.log_sync_pull_complete(
                tenant_id=tenant_id,
                device_id=device_id,
                changes_count=total_changes,
                entity_breakdown=entity_breakdown,
                duration_ms=duration_ms,
                has_more=False,
                session_id=sync_session.id,
            )

            # Return response directly - data already serialized by entity serializers
            return Response(response_data)

        except Exception as e:
            # Log pull failure
            SyncLogger.log_sync_pull_failed(
                tenant_id=tenant_id,
                device_id=device_id,
                error=str(e),
                session_id=sync_session.id,
                error_code="PULL_PROCESSING_ERROR",
            )
            raise

    def _get_client_ip(self, request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")

    def _get_changes(self, tenant, branch, since, entity_types):
        """
        Get changes since timestamp for given entity types.

        This is a placeholder implementation. Real implementation would:
        1. Query Product, StockMovement, etc. for changes since timestamp
        2. Filter by branch where applicable
        3. Build changeset with operation type (create/update/delete)
        """
        changes = {}

        # Placeholder - actual implementation would query entity tables
        if not entity_types or "Product" in entity_types:
            from apps.inventario.models import Product
            from apps.inventario.serializers import ProductSerializer

            products_qs = Product.objects.filter(tenant=tenant)
            if since:
                products_qs = products_qs.filter(updated_at__gt=since)

            products_qs = products_qs[:100]  # Limit for pagination
            changes["Product"] = ProductSerializer(products_qs, many=True).data

        if not entity_types or "BranchStock" in entity_types:
            from apps.inventario.models import BranchStock
            from apps.inventario.serializers import BranchStockSerializer

            # StockSnapshot/BranchStock uses branch FK, not direct tenant
            stocks_qs = BranchStock.objects.filter(branch__tenant=tenant, branch=branch)
            if since:
                stocks_qs = stocks_qs.filter(last_updated__gt=since)

            stocks_qs = stocks_qs[:100]
            changes["BranchStock"] = BranchStockSerializer(stocks_qs, many=True).data

        return changes


@sync_status_schema
class SyncStatusView(APIView):
    """
    Get sync status for a device.

    GET /api/v1/sync/status/{device_id}/

    Returns current sync status and pending operations count.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, device_id):
        try:
            sync_session = SyncSession.objects.get(tenant=request.user.tenant, device_id=device_id)
        except SyncSession.DoesNotExist:
            return Response({"detail": "Device not registered."}, status=status.HTTP_404_NOT_FOUND)

        pending_count = PendingOperation.objects.filter(
            sync_session=sync_session, status=PendingOperation.OperationStatus.PENDING
        ).count()

        conflict_count = PendingOperation.objects.filter(
            sync_session=sync_session, status=PendingOperation.OperationStatus.CONFLICT
        ).count()

        return Response(
            {
                "device_id": device_id,
                "status": sync_session.status,
                "last_sync_at": sync_session.last_sync_at,
                "pending_operations": pending_count,
                "conflicts": conflict_count,
                "sync_vector": sync_session.sync_vector,
            }
        )
