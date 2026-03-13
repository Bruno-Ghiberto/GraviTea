"""
Centralized configuration for observability module.

All observability settings are configured via environment variables
with sensible defaults for development.

Environment Variables:
    OTEL_TRACING_ENABLED: Enable OpenTelemetry tracing (default: false)
    OTEL_SERVICE_NAME: Service name for traces (default: gravitea-backend)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    OTEL_SAMPLING_RATIO: Head-based sampling ratio (default: 0.1)
    LOG_FORMAT: Log format - "json" or "text" (default: text)
    LOG_LEVEL: Log level (default: INFO)
    METRICS_ENABLED: Enable Prometheus metrics (default: true)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional


@dataclass(frozen=True)
class MetricsConfig:
    """Configuration for Prometheus metrics."""

    enabled: bool = True
    endpoint: str = "/metrics"
    include_in_schema: bool = False

    @classmethod
    def from_environment(cls) -> "MetricsConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.environ.get("METRICS_ENABLED", "true").lower() == "true",
        )


@dataclass(frozen=True)
class TracingConfig:
    """Configuration for OpenTelemetry tracing."""

    enabled: bool = False
    service_name: str = "gravitea-backend"
    otlp_endpoint: str = "http://localhost:4317"
    sampling_ratio: float = 0.1
    sample_errors: bool = True
    environment: str = "development"
    version: str = "1.0.0"
    scrub_db_statements: bool = True
    scrub_request_bodies: bool = True

    @classmethod
    def from_environment(cls) -> "TracingConfig":
        """Create configuration from environment variables."""
        return cls(
            enabled=os.environ.get("OTEL_TRACING_ENABLED", "false").lower() == "true",
            service_name=os.environ.get("OTEL_SERVICE_NAME", "gravitea-backend"),
            otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            sampling_ratio=float(os.environ.get("OTEL_SAMPLING_RATIO", "0.1")),
            environment=os.environ.get("DJANGO_ENV", "development"),
        )


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for structured logging."""

    format: str = "text"  # "json" or "text"
    level: str = "INFO"
    include_trace_id: bool = True
    scrub_sensitive_data: bool = True

    @classmethod
    def from_environment(cls) -> "LoggingConfig":
        """Create configuration from environment variables."""
        return cls(
            format=os.environ.get("LOG_FORMAT", "text").lower(),
            level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


@dataclass(frozen=True)
class AlertConfig:
    """Configuration for alerting."""

    webhook_url: Optional[str] = None
    rate_limit_window: int = 60
    rate_limit_count: int = 100
    dedup_window: int = 300

    @classmethod
    def from_environment(cls) -> "AlertConfig":
        """Create configuration from environment variables."""
        return cls(
            webhook_url=os.environ.get("ALERT_WEBHOOK_URL"),
            rate_limit_window=int(os.environ.get("ALERT_RATE_LIMIT_WINDOW", "60")),
            rate_limit_count=int(os.environ.get("ALERT_RATE_LIMIT_COUNT", "100")),
            dedup_window=int(os.environ.get("ALERT_DEDUP_WINDOW", "300")),
        )


@dataclass(frozen=True)
class SLOConfig:
    """Configuration for SLO thresholds."""

    error_rate_threshold: float = 0.01  # 1%
    latency_p99_threshold_ms: float = 500  # 500ms
    sync_lag_threshold_seconds: float = 60  # 60 seconds

    @classmethod
    def from_environment(cls) -> "SLOConfig":
        """Create configuration from environment variables."""
        return cls(
            error_rate_threshold=float(os.environ.get("SLO_ERROR_RATE_THRESHOLD", "0.01")),
            latency_p99_threshold_ms=float(os.environ.get("SLO_LATENCY_P99_MS", "500")),
            sync_lag_threshold_seconds=float(os.environ.get("SLO_SYNC_LAG_SECONDS", "60")),
        )


@dataclass
class ObservabilityConfig:
    """Complete observability configuration."""

    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    slo: SLOConfig = field(default_factory=SLOConfig)

    @classmethod
    def from_environment(cls) -> "ObservabilityConfig":
        """Create complete configuration from environment variables."""
        return cls(
            metrics=MetricsConfig.from_environment(),
            tracing=TracingConfig.from_environment(),
            logging=LoggingConfig.from_environment(),
            alerts=AlertConfig.from_environment(),
            slo=SLOConfig.from_environment(),
        )


@lru_cache(maxsize=1)
def get_observability_config() -> ObservabilityConfig:
    """Get the global observability configuration (cached)."""
    return ObservabilityConfig.from_environment()
