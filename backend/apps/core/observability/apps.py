"""
Django app configuration for observability module.

Initializes OpenTelemetry tracing and Prometheus metrics on application startup.
"""

from __future__ import annotations

import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ObservabilityConfig(AppConfig):
    """Django app configuration for observability."""

    name = "apps.core.observability"
    label = "observability"
    verbose_name = "Observability"

    def ready(self) -> None:
        """Initialize observability infrastructure on app startup.

        This is called once when Django starts. Initializes:
        1. OpenTelemetry tracer provider (if enabled)
        2. Django instrumentation (if enabled)
        3. Database instrumentation (if enabled)
        4. Prometheus database metrics wrapper
        """
        # Skip initialization only if we're definitely in a management command context
        # that shouldn't have metrics (like makemigrations)
        skip_commands = {"makemigrations", "migrate", "collectstatic", "shell"}
        import sys
        if len(sys.argv) > 1 and sys.argv[1] in skip_commands:
            return

        # For runserver with autoreload, only initialize in the main server process
        # RUN_MAIN is set to 'true' in the child process that handles requests
        if "runserver" in sys.argv:
            if os.environ.get("RUN_MAIN") != "true":
                return

        self._initialize_tracing()
        self._initialize_db_metrics()
        self._initialize_business_metrics()
        self._log_startup_info()

    def _is_web_server(self) -> bool:
        """Check if running in a web server context."""
        # Check for common WSGI/ASGI server indicators
        server_software = os.environ.get("SERVER_SOFTWARE", "")
        return bool(server_software) or "gunicorn" in os.environ.get("_", "")

    def _initialize_tracing(self) -> None:
        """Initialize OpenTelemetry tracing if enabled."""
        if os.environ.get("OTEL_TRACING_ENABLED", "false").lower() != "true":
            logger.debug("OpenTelemetry tracing disabled")
            return

        try:
            from .tracing import get_tracer

            tracer = get_tracer()
            if tracer:
                logger.info(
                    "OpenTelemetry tracing initialized",
                    extra={
                        "service_name": os.environ.get("OTEL_SERVICE_NAME", "gravitea-backend"),
                        "endpoint": os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
                    },
                )

                # Initialize Django instrumentation
                self._instrument_django()
                self._instrument_database()
            else:
                logger.warning("OpenTelemetry tracer initialization returned None")

        except ImportError as e:
            logger.warning(f"OpenTelemetry packages not available: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry: {e}")

    def _instrument_django(self) -> None:
        """Apply OpenTelemetry Django instrumentation."""
        try:
            from opentelemetry.instrumentation.django import DjangoInstrumentor

            if not DjangoInstrumentor().is_instrumented_by_opentelemetry:
                DjangoInstrumentor().instrument()
                logger.debug("Django instrumentation applied")
        except ImportError:
            logger.debug("Django instrumentation not available")
        except Exception as e:
            logger.warning(f"Failed to instrument Django: {e}")

    def _instrument_database(self) -> None:
        """Apply OpenTelemetry psycopg2 instrumentation."""
        try:
            from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

            if not Psycopg2Instrumentor().is_instrumented_by_opentelemetry:
                Psycopg2Instrumentor().instrument(enable_commenter=True)
                logger.debug("psycopg2 instrumentation applied")
        except ImportError:
            logger.debug("psycopg2 instrumentation not available")
        except Exception as e:
            logger.warning(f"Failed to instrument psycopg2: {e}")

    def _initialize_db_metrics(self) -> None:
        """Initialize Prometheus database query metrics.

        Uses Django's connection_created signal to register a wrapper on each
        new database connection, ensuring metrics are captured across all threads.
        """
        try:
            from django.db.backends.signals import connection_created

            from .metrics import record_db_query

            # Execute wrapper function for Django's execute_wrappers API
            def metrics_cursor_wrapper(execute, sql, params, many, context):
                import time

                start = time.perf_counter()
                try:
                    return execute(sql, params, many, context)
                finally:
                    duration = time.perf_counter() - start
                    sql_upper = sql.strip().upper()
                    operation = "OTHER"
                    for op in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                        if sql_upper.startswith(op):
                            operation = op
                            break
                    # Context in Django's execute_wrapper is the connection object
                    try:
                        if hasattr(context, "alias"):
                            alias = context.alias
                        elif isinstance(context, dict) and "connection" in context:
                            alias = context["connection"].alias
                        else:
                            alias = "default"
                    except Exception:
                        alias = "default"
                    record_db_query(alias, operation, duration)

            # Register wrapper on new connections via signal
            def on_connection_created(sender, connection, **kwargs):
                # Check if wrapper is already registered (avoid duplicates)
                wrapper_names = [w.__name__ for w in connection.execute_wrappers if hasattr(w, "__name__")]
                if "metrics_cursor_wrapper" not in wrapper_names:
                    connection.execute_wrappers.append(metrics_cursor_wrapper)
                    logger.debug(f"DB metrics wrapper registered for connection: {connection.alias}")

            # Connect the signal handler
            connection_created.connect(on_connection_created)

            # Also register on any existing connections
            from django.db import connections
            for alias in connections.databases:
                try:
                    conn = connections[alias]
                    on_connection_created(sender=None, connection=conn)
                except Exception:
                    pass  # Connection may not be ready yet

            logger.info("Database metrics instrumentation enabled via connection_created signal")

        except Exception as e:
            logger.warning(f"Failed to initialize database metrics: {e}", exc_info=True)

    def _initialize_business_metrics(self) -> None:
        """Initialize business metrics with default values.

        prometheus-client only exports labeled metrics after they've been used
        at least once. This method "warms up" all business metrics with a
        placeholder tenant_id so they appear in Prometheus immediately.

        This ensures Grafana dashboards show the metrics (even if 0) rather
        than "No data".
        """
        try:
            from .business_metrics import (
                auth_attempts_total,
                auth_failures_total,
                auth_success_total,
                inventory_movements_total,
                orders_total,
                sync_operations_total,
                sync_processing_lag_seconds,
                sync_queue_depth,
            )

            # Use a placeholder tenant for initialization
            # These values will be overwritten by real data when business ops occur
            placeholder_tenant = "__init__"
            placeholder_branch = "__init__"

            # Initialize order status counters
            for status in ["pending", "completed", "cancelled"]:
                orders_total.labels(
                    tenant_id=placeholder_tenant,
                    branch_id=placeholder_branch,
                    status=status,
                ).inc(0)

            # Initialize inventory movement counters
            for operation in ["entrada", "salida", "ajuste", "transferencia"]:
                for product_type in ["materia_prima", "producto_terminado", "insumo"]:
                    inventory_movements_total.labels(
                        tenant_id=placeholder_tenant,
                        branch_id=placeholder_branch,
                        operation=operation,
                        product_type=product_type,
                    ).inc(0)

            # Initialize sync metrics
            for operation_type in ["order", "inventory", "product", "customer"]:
                sync_queue_depth.labels(
                    tenant_id=placeholder_tenant,
                    operation_type=operation_type,
                ).set(0)

                # Initialize sync_operations_total with statuses
                for status in ["success", "failure", "conflict"]:
                    sync_operations_total.labels(
                        tenant_id=placeholder_tenant,
                        operation_type=operation_type,
                        status=status,
                    ).inc(0)

            # sync_processing_lag_seconds only has tenant_id label
            sync_processing_lag_seconds.labels(
                tenant_id=placeholder_tenant,
            ).set(0)

            # Initialize auth metrics
            # Using sanitized method names to avoid exposing sensitive terms
            for method in ["pwd", "jwt", "key"]:
                auth_attempts_total.labels(
                    tenant_id=placeholder_tenant,
                    method=method,
                ).inc(0)
                auth_success_total.labels(
                    tenant_id=placeholder_tenant,
                    method=method,
                ).inc(0)

            # auth_failures_total has reason label (not method)
            # Using sanitized reason names to avoid exposing sensitive terms
            for reason in ["invalid_creds", "expired_jwt", "locked_account", "rate_limited"]:
                auth_failures_total.labels(
                    tenant_id=placeholder_tenant,
                    reason=reason,
                ).inc(0)

            logger.info("Business metrics initialized with default values")

        except ImportError as e:
            logger.warning(f"Business metrics module not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to initialize business metrics: {e}", exc_info=True)

    def _log_startup_info(self) -> None:
        """Log observability configuration at startup."""
        config_info = {
            "metrics_enabled": True,  # Always enabled
            "tracing_enabled": os.environ.get("OTEL_TRACING_ENABLED", "false").lower() == "true",
            "log_format": os.environ.get("LOG_FORMAT", "text"),
            "log_level": os.environ.get("LOG_LEVEL", "INFO"),
        }
        logger.info("Observability module initialized", extra=config_info)
