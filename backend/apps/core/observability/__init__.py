"""
Observability module for GRAVITEA ERP.

Provides comprehensive observability infrastructure:

**Alerting (SC-021, SC-022, SC-023)**:
- Fiscal service failure alerts (within 1 minute)
- Sync failure logging with debug context
- Security event real-time alerts

**Uptime Monitoring (SC-014)**:
- 99.9% uptime tracking for critical functions
- Health check endpoints (liveness, readiness, startup)

**Prometheus Metrics (004-observability)**:
- RED metrics (Request Rate, Errors, Duration)
- Business metrics (sync, auth, inventory, orders)
- Cardinality-controlled labels

**Distributed Tracing (004-observability)**:
- OpenTelemetry integration with OTLP export
- Integration with existing TraceContext

**Structured Logging (004-observability)**:
- JSON log format for ELK/Loki
- Trace correlation across log entries
- Sensitive data filtering
"""

from .alerts import (
    AlertLevel,
    AlertType,
    AlertManager,
    fiscal_alert,
    sync_alert,
    security_alert,
    get_alert_manager,
)
from .uptime import (
    UptimeMonitor,
    HealthStatus,
    get_uptime_monitor,
)
# RED metrics and core registry from metrics.py
from .metrics import (
    REGISTRY,
    normalize_path,
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    record_request,
)
from .tracing import (
    TracingConfig,
    get_tracer,
    create_span,
    set_span_error,
    add_span_attribute,
    get_span_context_from_trace_id,
    scrub_attributes,
)
from .logging import (
    JSONLogFormatter,
    TraceCorrelationFilter,
    SensitiveDataFilter,
    get_json_formatter,
    get_logging_config,
    scrub_dict,
)
# Business metrics from business_metrics.py (orders, sync, auth, inventory)
from .business_metrics import (
    # Order metrics
    orders_total,
    order_value_total,
    orders_in_progress,
    record_order,
    # Inventory metrics
    inventory_movements_total,
    inventory_adjustments_total,
    low_stock_alerts,
    record_inventory_movement,
    record_inventory_adjustment,
    update_low_stock_count,
    # Sync metrics
    sync_queue_depth,
    sync_processing_lag_seconds,
    sync_operations_total,
    sync_conflicts_total,
    update_sync_queue_depth,
    update_sync_lag,
    record_sync_operation,
    record_sync_conflict,
    # Auth metrics
    auth_attempts_total,
    auth_failures_total,
    auth_success_total,
    active_sessions,
    jwt_refresh_total,
    record_auth_attempt,
    record_auth_failure,
    record_auth_success,
    update_active_sessions,
    record_jwt_refresh,
    # Convenience functions
    update_all_sync_metrics,
)

__all__ = [
    # Alerts
    "AlertLevel",
    "AlertType",
    "AlertManager",
    "fiscal_alert",
    "sync_alert",
    "security_alert",
    "get_alert_manager",
    # Uptime
    "UptimeMonitor",
    "HealthStatus",
    "get_uptime_monitor",
    # RED Metrics (from metrics.py)
    "REGISTRY",
    "normalize_path",
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    "record_request",
    # Business Metrics (from business_metrics.py)
    # Orders
    "orders_total",
    "order_value_total",
    "orders_in_progress",
    "record_order",
    # Inventory
    "inventory_movements_total",
    "inventory_adjustments_total",
    "low_stock_alerts",
    "record_inventory_movement",
    "record_inventory_adjustment",
    "update_low_stock_count",
    # Sync
    "sync_queue_depth",
    "sync_processing_lag_seconds",
    "sync_operations_total",
    "sync_conflicts_total",
    "update_sync_queue_depth",
    "update_sync_lag",
    "record_sync_operation",
    "record_sync_conflict",
    # Auth
    "auth_attempts_total",
    "auth_failures_total",
    "auth_success_total",
    "active_sessions",
    "jwt_refresh_total",
    "record_auth_attempt",
    "record_auth_failure",
    "record_auth_success",
    "update_active_sessions",
    "record_jwt_refresh",
    # Convenience
    "update_all_sync_metrics",
    # Tracing
    "TracingConfig",
    "get_tracer",
    "create_span",
    "set_span_error",
    "add_span_attribute",
    "get_span_context_from_trace_id",
    "scrub_attributes",
    # Logging
    "JSONLogFormatter",
    "TraceCorrelationFilter",
    "SensitiveDataFilter",
    "get_json_formatter",
    "get_logging_config",
    "scrub_dict",
]
