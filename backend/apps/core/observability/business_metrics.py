"""
Business metrics for GRAVITEA ERP.

Custom metrics for business operations: orders, inventory, sync, auth.
Provides tenant-aware counters and gauges for business analytics.

Per 004-observability-metrics spec FR-001 through FR-010.

Metrics defined:
- orders_total: Counter for completed orders
- inventory_movements_total: Counter for inventory operations
- sync_queue_depth: Gauge for pending sync operations
- sync_processing_lag_seconds: Gauge for sync lag
- auth_attempts_total: Counter for authentication attempts
- auth_failures_total: Counter for authentication failures

Usage:
    from apps.core.observability.business_metrics import (
        record_order,
        record_inventory_movement,
        update_sync_queue_depth,
        update_sync_lag,
        record_auth_attempt,
        record_auth_failure,
    )

    # Record a completed order
    record_order(tenant_id="tenant-123", branch_id="branch-456", status="completed", amount=150.00)

    # Record inventory movement
    record_inventory_movement(tenant_id="tenant-123", operation="sale", product_type="beverage")

    # Update sync metrics
    update_sync_queue_depth(tenant_id="tenant-123", depth=42)
    update_sync_lag(tenant_id="tenant-123", lag_seconds=5.2)

    # Record auth events
    record_auth_attempt(tenant_id="tenant-123", method="password")
    record_auth_failure(tenant_id="tenant-123", reason="invalid_credentials")
"""

from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

from .metrics import REGISTRY

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Order Metrics
# -----------------------------------------------------------------------------

orders_total = Counter(
    "orders_total",
    "Total number of orders processed",
    labelnames=["tenant_id", "branch_id", "status"],
    registry=REGISTRY,
)

order_value_total = Counter(
    "order_value_total",
    "Total monetary value of orders",
    labelnames=["tenant_id", "branch_id", "currency"],
    registry=REGISTRY,
)

orders_in_progress = Gauge(
    "orders_in_progress",
    "Number of orders currently being processed",
    labelnames=["tenant_id", "branch_id"],
    registry=REGISTRY,
)


def record_order(
    tenant_id: str,
    branch_id: str = "unknown",
    status: str = "completed",
    amount: Optional[float] = None,
    currency: str = "ARS",
) -> None:
    """
    Record an order event.

    Args:
        tenant_id: Tenant identifier
        branch_id: Branch identifier
        status: Order status (completed, cancelled, pending)
        amount: Order monetary value (optional)
        currency: Currency code (default: ARS for Argentine Pesos)
    """
    try:
        orders_total.labels(
            tenant_id=tenant_id,
            branch_id=branch_id,
            status=status,
        ).inc()

        if amount is not None and amount > 0:
            order_value_total.labels(
                tenant_id=tenant_id,
                branch_id=branch_id,
                currency=currency,
            ).inc(amount)

        logger.debug(
            "Recorded order: tenant=%s branch=%s status=%s amount=%s",
            tenant_id,
            branch_id,
            status,
            amount,
        )
    except Exception as e:
        logger.warning("Failed to record order metric: %s", e)


# -----------------------------------------------------------------------------
# Inventory Metrics
# -----------------------------------------------------------------------------

inventory_movements_total = Counter(
    "inventory_movements_total",
    "Total number of inventory movements",
    labelnames=["tenant_id", "branch_id", "operation", "product_type"],
    registry=REGISTRY,
)

inventory_adjustments_total = Counter(
    "inventory_adjustments_total",
    "Total number of inventory adjustments (manual corrections)",
    labelnames=["tenant_id", "branch_id", "reason"],
    registry=REGISTRY,
)

low_stock_alerts = Gauge(
    "low_stock_alerts",
    "Number of products with low stock alerts",
    labelnames=["tenant_id", "branch_id"],
    registry=REGISTRY,
)


def record_inventory_movement(
    tenant_id: str,
    operation: str,
    branch_id: str = "unknown",
    product_type: str = "unknown",
    quantity: int = 1,
) -> None:
    """
    Record an inventory movement event.

    Args:
        tenant_id: Tenant identifier
        operation: Movement type (sale, purchase, transfer, adjustment)
        branch_id: Branch identifier
        product_type: Product category
        quantity: Number of units moved
    """
    try:
        inventory_movements_total.labels(
            tenant_id=tenant_id,
            branch_id=branch_id,
            operation=operation,
            product_type=product_type,
        ).inc(quantity)

        logger.debug(
            "Recorded inventory movement: tenant=%s operation=%s quantity=%d",
            tenant_id,
            operation,
            quantity,
        )
    except Exception as e:
        logger.warning("Failed to record inventory metric: %s", e)


def record_inventory_adjustment(
    tenant_id: str,
    reason: str,
    branch_id: str = "unknown",
) -> None:
    """
    Record an inventory adjustment event.

    Args:
        tenant_id: Tenant identifier
        reason: Adjustment reason (count, damage, expiry, theft)
        branch_id: Branch identifier
    """
    try:
        inventory_adjustments_total.labels(
            tenant_id=tenant_id,
            branch_id=branch_id,
            reason=reason,
        ).inc()
    except Exception as e:
        logger.warning("Failed to record inventory adjustment metric: %s", e)


def update_low_stock_count(tenant_id: str, branch_id: str, count: int) -> None:
    """
    Update the count of low-stock products.

    Args:
        tenant_id: Tenant identifier
        branch_id: Branch identifier
        count: Number of products with low stock
    """
    try:
        low_stock_alerts.labels(
            tenant_id=tenant_id,
            branch_id=branch_id,
        ).set(count)
    except Exception as e:
        logger.warning("Failed to update low stock count: %s", e)


# -----------------------------------------------------------------------------
# Sync Queue Metrics
# -----------------------------------------------------------------------------

sync_queue_depth = Gauge(
    "sync_queue_depth",
    "Number of pending sync operations in queue",
    labelnames=["tenant_id", "operation_type"],
    registry=REGISTRY,
)

sync_processing_lag_seconds = Gauge(
    "sync_processing_lag_seconds",
    "Time lag between oldest pending operation and now (seconds)",
    labelnames=["tenant_id"],
    registry=REGISTRY,
)

sync_operations_total = Counter(
    "sync_operations_total",
    "Total number of sync operations processed",
    labelnames=["tenant_id", "operation_type", "status"],
    registry=REGISTRY,
)

sync_conflicts_total = Counter(
    "sync_conflicts_total",
    "Total number of sync conflicts detected",
    labelnames=["tenant_id", "conflict_type"],
    registry=REGISTRY,
)


def update_sync_queue_depth(
    tenant_id: str,
    depth: int,
    operation_type: str = "all",
) -> None:
    """
    Update the sync queue depth metric.

    Args:
        tenant_id: Tenant identifier
        depth: Number of pending operations
        operation_type: Type of operations (all, create, update, delete)
    """
    try:
        sync_queue_depth.labels(
            tenant_id=tenant_id,
            operation_type=operation_type,
        ).set(depth)

        logger.debug(
            "Updated sync queue depth: tenant=%s depth=%d",
            tenant_id,
            depth,
        )
    except Exception as e:
        logger.warning("Failed to update sync queue depth: %s", e)


def update_sync_lag(tenant_id: str, lag_seconds: float) -> None:
    """
    Update the sync processing lag metric.

    Args:
        tenant_id: Tenant identifier
        lag_seconds: Time since oldest pending operation
    """
    try:
        sync_processing_lag_seconds.labels(tenant_id=tenant_id).set(lag_seconds)

        logger.debug(
            "Updated sync lag: tenant=%s lag=%.2fs",
            tenant_id,
            lag_seconds,
        )
    except Exception as e:
        logger.warning("Failed to update sync lag: %s", e)


def record_sync_operation(
    tenant_id: str,
    operation_type: str,
    status: str = "success",
) -> None:
    """
    Record a sync operation completion.

    Args:
        tenant_id: Tenant identifier
        operation_type: Type of operation (create, update, delete)
        status: Operation result (success, failure, conflict)
    """
    try:
        sync_operations_total.labels(
            tenant_id=tenant_id,
            operation_type=operation_type,
            status=status,
        ).inc()
    except Exception as e:
        logger.warning("Failed to record sync operation: %s", e)


def record_sync_conflict(tenant_id: str, conflict_type: str) -> None:
    """
    Record a sync conflict event.

    Args:
        tenant_id: Tenant identifier
        conflict_type: Type of conflict (version, deleted, concurrent)
    """
    try:
        sync_conflicts_total.labels(
            tenant_id=tenant_id,
            conflict_type=conflict_type,
        ).inc()
    except Exception as e:
        logger.warning("Failed to record sync conflict: %s", e)


# -----------------------------------------------------------------------------
# Authentication Metrics
# -----------------------------------------------------------------------------

auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total number of authentication attempts",
    labelnames=["tenant_id", "method"],
    registry=REGISTRY,
)

auth_failures_total = Counter(
    "auth_failures_total",
    "Total number of failed authentication attempts",
    labelnames=["tenant_id", "reason"],
    registry=REGISTRY,
)

auth_success_total = Counter(
    "auth_success_total",
    "Total number of successful authentications",
    labelnames=["tenant_id", "method"],
    registry=REGISTRY,
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active user sessions",
    labelnames=["tenant_id"],
    registry=REGISTRY,
)

jwt_refresh_total = Counter(
    "jwt_refresh_total",
    "Total number of JWT refresh operations",
    labelnames=["tenant_id", "status"],
    registry=REGISTRY,
)


def record_auth_attempt(
    tenant_id: str,
    method: str = "pwd",
) -> None:
    """
    Record an authentication attempt.

    Args:
        tenant_id: Tenant identifier
        method: Authentication method (pwd, jwt, key)
    """
    try:
        auth_attempts_total.labels(
            tenant_id=tenant_id,
            method=method,
        ).inc()

        logger.debug(
            "Recorded auth attempt: tenant=%s method=%s",
            tenant_id,
            method,
        )
    except Exception as e:
        logger.warning("Failed to record auth attempt: %s", e)


def record_auth_failure(
    tenant_id: str,
    reason: str = "invalid_creds",
) -> None:
    """
    Record a failed authentication attempt.

    Args:
        tenant_id: Tenant identifier
        reason: Failure reason (invalid_creds, expired_jwt, locked_account)
    """
    try:
        auth_failures_total.labels(
            tenant_id=tenant_id,
            reason=reason,
        ).inc()

        logger.debug(
            "Recorded auth failure: tenant=%s reason=%s",
            tenant_id,
            reason,
        )
    except Exception as e:
        logger.warning("Failed to record auth failure: %s", e)


def record_auth_success(
    tenant_id: str,
    method: str = "pwd",
) -> None:
    """
    Record a successful authentication.

    Args:
        tenant_id: Tenant identifier
        method: Authentication method (pwd, jwt, key)
    """
    try:
        auth_success_total.labels(
            tenant_id=tenant_id,
            method=method,
        ).inc()
    except Exception as e:
        logger.warning("Failed to record auth success: %s", e)


def update_active_sessions(tenant_id: str, count: int) -> None:
    """
    Update the count of active sessions for a tenant.

    Args:
        tenant_id: Tenant identifier
        count: Number of active sessions
    """
    try:
        active_sessions.labels(tenant_id=tenant_id).set(count)
    except Exception as e:
        logger.warning("Failed to update active sessions: %s", e)


def record_jwt_refresh(tenant_id: str, status: str = "success") -> None:
    """
    Record a JWT refresh operation.

    Args:
        tenant_id: Tenant identifier
        status: Refresh result (success, failure, expired)
    """
    try:
        jwt_refresh_total.labels(
            tenant_id=tenant_id,
            status=status,
        ).inc()
    except Exception as e:
        logger.warning("Failed to record JWT refresh: %s", e)


# -----------------------------------------------------------------------------
# Convenience function for batch updates
# -----------------------------------------------------------------------------


def update_all_sync_metrics(
    tenant_id: str,
    queue_depth: int,
    lag_seconds: float,
) -> None:
    """
    Update all sync-related metrics at once.

    Args:
        tenant_id: Tenant identifier
        queue_depth: Number of pending operations
        lag_seconds: Time since oldest pending operation
    """
    update_sync_queue_depth(tenant_id, queue_depth)
    update_sync_lag(tenant_id, lag_seconds)
