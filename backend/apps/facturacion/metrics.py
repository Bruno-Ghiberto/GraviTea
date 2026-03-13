"""
Prometheus metrics for ARCA electronic invoicing.

Instruments WSAA authentication, CAE results, and SOAP call latency.
Omits tenant_id from labels to avoid high-cardinality explosion.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

from prometheus_client import Counter, Histogram

from apps.core.observability.metrics import REGISTRY

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

arca_wsaa_auth_total = Counter(
    "arca_wsaa_auth_total",
    "Total WSAA authentication attempts (LoginCms).",
    labelnames=["result", "environment"],
    registry=REGISTRY,
)

arca_cae_result_total = Counter(
    "arca_cae_result_total",
    "Total CAE authorization results from FECAESolicitar.",
    labelnames=["result", "cbte_tipo"],
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------

arca_soap_duration_seconds = Histogram(
    "arca_soap_duration_seconds",
    "ARCA SOAP call duration in seconds.",
    labelnames=["operation", "environment"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=REGISTRY,
)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def record_wsaa_auth(*, result: str, environment: str) -> None:
    """Record a WSAA LoginCms authentication attempt.

    Args:
        result: "success" or "failure".
        environment: "production" or "homologacion".
    """
    try:
        arca_wsaa_auth_total.labels(
            result=result,
            environment=environment,
        ).inc()
    except Exception:
        logger.warning("Failed to record WSAA auth metric", exc_info=True)


def record_cae_result(*, result: str, cbte_tipo: int) -> None:
    """Record a CAE authorization result.

    Args:
        result: "approved", "rejected", or "observed".
        cbte_tipo: CbteTipo integer code (e.g. 1 for Factura A).
    """
    try:
        arca_cae_result_total.labels(
            result=result,
            cbte_tipo=str(cbte_tipo),
        ).inc()
    except Exception:
        logger.warning("Failed to record CAE result metric", exc_info=True)


def record_soap_duration(
    *, operation: str, environment: str, duration: float
) -> None:
    """Record SOAP call duration.

    Args:
        operation: SOAP operation name (e.g. "LoginCms", "FECAESolicitar").
        environment: "production" or "homologacion".
        duration: Duration in seconds.
    """
    try:
        arca_soap_duration_seconds.labels(
            operation=operation,
            environment=environment,
        ).observe(duration)
    except Exception:
        logger.warning("Failed to record SOAP duration metric", exc_info=True)


@contextmanager
def track_soap_call(
    *, operation: str, environment: str
) -> Generator[None, None, None]:
    """Context manager to time and record a SOAP call.

    Usage::

        with track_soap_call(operation="FECAESolicitar", environment="production"):
            response = client.service.FECAESolicitar(auth, req)
    """
    start = time.monotonic()
    try:
        yield
    finally:
        duration = time.monotonic() - start
        record_soap_duration(
            operation=operation,
            environment=environment,
            duration=duration,
        )
