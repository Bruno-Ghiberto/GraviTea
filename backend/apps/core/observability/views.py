"""
Views for observability endpoints.

Provides the /metrics endpoint for Prometheus scraping and
optional tenant-filtered metrics access.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

from django.http import HttpResponse
from django.views import View
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .metrics import REGISTRY

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger(__name__)


class MetricsView(View):
    """Prometheus metrics endpoint.

    Serves Prometheus metrics in the standard exposition format.
    This endpoint should be accessible without authentication for
    Prometheus scraping, but tenant-specific metrics are only
    included when authenticated.

    Per 004-observability-metrics spec:
    - GET /metrics returns all aggregated metrics
    - Response time should be < 100ms
    - Content-Type: text/plain; version=0.0.4; charset=utf-8

    Security considerations:
    - Unauthenticated access returns aggregate metrics only
    - Authenticated access may include tenant-specific detail
    - No PII or secrets should be exposed in metric labels
    """

    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest) -> HttpResponse:
        """Serve Prometheus metrics.

        Args:
            request: The HTTP request

        Returns:
            HttpResponse with metrics in Prometheus exposition format
        """
        start_time = time.perf_counter()

        try:
            # Generate metrics from our custom registry
            metrics_output = generate_latest(REGISTRY)

            # Calculate response time for monitoring
            response_time_ms = (time.perf_counter() - start_time) * 1000

            if response_time_ms > 100:
                logger.warning(
                    f"Metrics endpoint took {response_time_ms:.2f}ms (target: <100ms)"
                )

            response = HttpResponse(
                metrics_output,
                content_type=CONTENT_TYPE_LATEST,
            )

            # Add cache headers to prevent caching
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

            return response

        except Exception as e:
            logger.exception(f"Failed to generate metrics: {e}")
            return HttpResponse(
                f"# Error generating metrics: {e}\n",
                content_type="text/plain; charset=utf-8",
                status=500,
            )

    def head(self, request: HttpRequest) -> HttpResponse:
        """Handle HEAD requests for metrics endpoint.

        Args:
            request: The HTTP request

        Returns:
            HttpResponse with appropriate headers
        """
        response = HttpResponse(content_type=CONTENT_TYPE_LATEST)
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


def metrics_view(request: HttpRequest) -> HttpResponse:
    """Function-based view wrapper for MetricsView.

    This wrapper provides a simpler integration option for URL routing.

    Args:
        request: The HTTP request

    Returns:
        HttpResponse with metrics in Prometheus exposition format
    """
    return MetricsView.as_view()(request)
