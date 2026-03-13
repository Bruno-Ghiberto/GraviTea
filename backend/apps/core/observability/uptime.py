"""
Uptime monitoring configuration for GRAVITEA ERP.

Implements SC-014: 99.9% uptime for critical sales processing functions.

Provides:
- Health check endpoints for load balancers
- Component health status tracking
- Uptime metrics collection
- Degraded state detection

Usage:
    from apps.core.observability import get_uptime_monitor, HealthStatus

    monitor = get_uptime_monitor()

    # Check overall system health
    status = monitor.get_health()
    if status.is_healthy:
        # System is operational
        pass

    # Record component status
    monitor.record_check("database", healthy=True, latency_ms=5.2)
    monitor.record_check("cache", healthy=False, error="Connection refused")

    # Get metrics for monitoring dashboards
    metrics = monitor.get_metrics()
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from django.conf import settings
from django.db import connection
from django.utils import timezone


class ComponentStatus(str, Enum):
    """Health status for individual components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    component: str
    status: ComponentStatus
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    last_check: datetime = field(default_factory=timezone.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Overall system health status."""

    status: ComponentStatus
    is_healthy: bool
    components: dict[str, HealthCheckResult]
    uptime_percentage: float
    last_downtime: Optional[datetime]
    checks_passed: int
    checks_failed: int
    timestamp: datetime = field(default_factory=timezone.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "status": self.status.value,
            "is_healthy": self.is_healthy,
            "uptime_percentage": round(self.uptime_percentage, 3),
            "last_downtime": (
                self.last_downtime.isoformat() if self.last_downtime else None
            ),
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "timestamp": self.timestamp.isoformat(),
            "components": {
                name: {
                    "status": result.status.value,
                    "latency_ms": result.latency_ms,
                    "error": result.error,
                    "last_check": result.last_check.isoformat(),
                }
                for name, result in self.components.items()
            },
        }


class HealthCheck:
    """Base class for health checks."""

    name: str = "unknown"
    critical: bool = False  # If True, failure = system unhealthy

    def check(self) -> HealthCheckResult:
        """Execute health check. Override in subclasses."""
        raise NotImplementedError


class DatabaseHealthCheck(HealthCheck):
    """Check database connectivity and response time."""

    name = "database"
    critical = True

    def check(self) -> HealthCheckResult:
        """Check database health via simple query."""
        start = time.time()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            latency = (time.time() - start) * 1000

            # Degraded if latency > 100ms
            status = (
                ComponentStatus.HEALTHY
                if latency < 100
                else ComponentStatus.DEGRADED
            )

            return HealthCheckResult(
                component=self.name,
                status=status,
                latency_ms=latency,
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=ComponentStatus.UNHEALTHY,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )


class CacheHealthCheck(HealthCheck):
    """Check cache connectivity (Redis/Memcached)."""

    name = "cache"
    critical = False  # System can operate without cache

    def check(self) -> HealthCheckResult:
        """Check cache health."""
        start = time.time()
        try:
            from django.core.cache import cache

            # Try to set and get a test value
            test_key = "_health_check_test"
            cache.set(test_key, "ok", timeout=10)
            result = cache.get(test_key)
            cache.delete(test_key)

            latency = (time.time() - start) * 1000

            if result == "ok":
                status = (
                    ComponentStatus.HEALTHY
                    if latency < 50
                    else ComponentStatus.DEGRADED
                )
                return HealthCheckResult(
                    component=self.name,
                    status=status,
                    latency_ms=latency,
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=ComponentStatus.DEGRADED,
                    latency_ms=latency,
                    error="Cache read/write mismatch",
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=ComponentStatus.UNHEALTHY,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )


class MigrationHealthCheck(HealthCheck):
    """Check if all migrations are applied."""

    name = "migrations"
    critical = True

    def check(self) -> HealthCheckResult:
        """Check migration status."""
        start = time.time()
        try:
            from django.db.migrations.executor import MigrationExecutor

            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

            latency = (time.time() - start) * 1000

            if plan:
                return HealthCheckResult(
                    component=self.name,
                    status=ComponentStatus.DEGRADED,
                    latency_ms=latency,
                    error=f"{len(plan)} pending migration(s)",
                    metadata={"pending_count": len(plan)},
                )
            else:
                return HealthCheckResult(
                    component=self.name,
                    status=ComponentStatus.HEALTHY,
                    latency_ms=latency,
                )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=ComponentStatus.UNHEALTHY,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )


class DiskSpaceHealthCheck(HealthCheck):
    """Check available disk space."""

    name = "disk_space"
    critical = False

    def __init__(self, threshold_gb: float = 1.0):
        self.threshold_gb = threshold_gb

    def check(self) -> HealthCheckResult:
        """Check available disk space."""
        start = time.time()
        try:
            import shutil

            # Check the Django BASE_DIR disk
            base_dir = getattr(settings, "BASE_DIR", "/")
            usage = shutil.disk_usage(base_dir)
            free_gb = usage.free / (1024**3)
            total_gb = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100

            latency = (time.time() - start) * 1000

            if free_gb < self.threshold_gb:
                status = ComponentStatus.UNHEALTHY
                error = f"Low disk space: {free_gb:.2f} GB free"
            elif used_percent > 85:
                status = ComponentStatus.DEGRADED
                error = f"Disk usage high: {used_percent:.1f}%"
            else:
                status = ComponentStatus.HEALTHY
                error = None

            return HealthCheckResult(
                component=self.name,
                status=status,
                latency_ms=latency,
                error=error,
                metadata={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "used_percent": round(used_percent, 1),
                },
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=ComponentStatus.UNKNOWN,
                error=str(e),
                latency_ms=(time.time() - start) * 1000,
            )


@dataclass
class UptimeMetrics:
    """Uptime tracking metrics."""

    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    downtime_events: list[tuple[datetime, datetime]] = field(default_factory=list)
    component_latencies: dict[str, list[float]] = field(default_factory=dict)
    start_time: datetime = field(default_factory=timezone.now)

    @property
    def uptime_percentage(self) -> float:
        """Calculate uptime percentage."""
        if self.total_checks == 0:
            return 100.0
        return (self.successful_checks / self.total_checks) * 100

    @property
    def last_downtime(self) -> Optional[datetime]:
        """Get last downtime event start."""
        if self.downtime_events:
            return self.downtime_events[-1][0]
        return None


class UptimeMonitor:
    """
    Central uptime monitoring system for SC-014 compliance.

    Target: 99.9% uptime for critical sales processing functions.
    This means max ~8.76 hours downtime per year.
    """

    TARGET_UPTIME = 99.9  # SC-014 requirement

    def __init__(self):
        self._checks: list[HealthCheck] = []
        self._results: dict[str, HealthCheckResult] = {}
        self._metrics = UptimeMetrics()
        self._lock = threading.Lock()
        self._is_healthy = True
        self._last_status_change: Optional[datetime] = None

        # Register default health checks
        self._checks.append(DatabaseHealthCheck())
        self._checks.append(CacheHealthCheck())
        self._checks.append(MigrationHealthCheck())
        self._checks.append(DiskSpaceHealthCheck())

    def add_check(self, check: HealthCheck) -> None:
        """Add a custom health check."""
        self._checks.append(check)

    def remove_check(self, name: str) -> None:
        """Remove a health check by name."""
        self._checks = [c for c in self._checks if c.name != name]

    def record_check(
        self,
        component: str,
        healthy: bool,
        latency_ms: Optional[float] = None,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a manual health check result."""
        status = ComponentStatus.HEALTHY if healthy else ComponentStatus.UNHEALTHY
        result = HealthCheckResult(
            component=component,
            status=status,
            latency_ms=latency_ms,
            error=error,
            metadata=metadata or {},
        )

        with self._lock:
            self._results[component] = result
            self._metrics.total_checks += 1
            if healthy:
                self._metrics.successful_checks += 1
            else:
                self._metrics.failed_checks += 1

            if latency_ms is not None:
                if component not in self._metrics.component_latencies:
                    self._metrics.component_latencies[component] = []
                latencies = self._metrics.component_latencies[component]
                latencies.append(latency_ms)
                # Keep last 100 latency samples
                if len(latencies) > 100:
                    self._metrics.component_latencies[component] = latencies[-100:]

    def run_checks(self) -> HealthStatus:
        """Run all registered health checks and return status."""
        results = {}
        checks_passed = 0
        checks_failed = 0
        critical_failure = False

        for check in self._checks:
            try:
                result = check.check()
                results[check.name] = result

                if result.status == ComponentStatus.HEALTHY:
                    checks_passed += 1
                else:
                    checks_failed += 1
                    if (
                        check.critical
                        and result.status == ComponentStatus.UNHEALTHY
                    ):
                        critical_failure = True

                # Record metrics
                self.record_check(
                    component=check.name,
                    healthy=(result.status == ComponentStatus.HEALTHY),
                    latency_ms=result.latency_ms,
                    error=result.error,
                    metadata=result.metadata,
                )
            except Exception as e:
                results[check.name] = HealthCheckResult(
                    component=check.name,
                    status=ComponentStatus.UNKNOWN,
                    error=str(e),
                )
                checks_failed += 1
                if check.critical:
                    critical_failure = True

        # Determine overall status
        if critical_failure:
            overall_status = ComponentStatus.UNHEALTHY
            is_healthy = False
        elif checks_failed > 0:
            overall_status = ComponentStatus.DEGRADED
            is_healthy = True  # Degraded is still operational
        else:
            overall_status = ComponentStatus.HEALTHY
            is_healthy = True

        # Track status changes for downtime events
        with self._lock:
            if is_healthy != self._is_healthy:
                now = timezone.now()
                if not is_healthy:
                    # Started downtime
                    self._metrics.downtime_events.append((now, now))
                elif self._metrics.downtime_events:
                    # Ended downtime
                    start, _ = self._metrics.downtime_events[-1]
                    self._metrics.downtime_events[-1] = (start, now)
                self._is_healthy = is_healthy
                self._last_status_change = now

            self._results = results

        return HealthStatus(
            status=overall_status,
            is_healthy=is_healthy,
            components=results,
            uptime_percentage=self._metrics.uptime_percentage,
            last_downtime=self._metrics.last_downtime,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
        )

    def get_health(self) -> HealthStatus:
        """Get current health status (runs checks)."""
        return self.run_checks()

    def get_cached_health(self) -> HealthStatus:
        """Get health status from cached results (doesn't run checks)."""
        with self._lock:
            checks_passed = sum(
                1
                for r in self._results.values()
                if r.status == ComponentStatus.HEALTHY
            )
            checks_failed = len(self._results) - checks_passed

            critical_failure = any(
                r.status == ComponentStatus.UNHEALTHY
                and any(c.critical and c.name == name for c in self._checks)
                for name, r in self._results.items()
            )

            if critical_failure:
                overall_status = ComponentStatus.UNHEALTHY
                is_healthy = False
            elif checks_failed > 0:
                overall_status = ComponentStatus.DEGRADED
                is_healthy = True
            else:
                overall_status = ComponentStatus.HEALTHY
                is_healthy = True

            return HealthStatus(
                status=overall_status,
                is_healthy=is_healthy,
                components=self._results.copy(),
                uptime_percentage=self._metrics.uptime_percentage,
                last_downtime=self._metrics.last_downtime,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
            )

    def get_metrics(self) -> dict:
        """Get monitoring metrics for dashboards."""
        with self._lock:
            # Calculate average latencies
            avg_latencies = {}
            for component, latencies in self._metrics.component_latencies.items():
                if latencies:
                    avg_latencies[component] = sum(latencies) / len(latencies)

            # Calculate total downtime
            total_downtime_seconds = 0
            for start, end in self._metrics.downtime_events:
                total_downtime_seconds += (end - start).total_seconds()

            # Calculate uptime since start
            total_seconds = (timezone.now() - self._metrics.start_time).total_seconds()
            actual_uptime = 0.0
            if total_seconds > 0:
                actual_uptime = (
                    (total_seconds - total_downtime_seconds) / total_seconds * 100
                )

            return {
                "target_uptime": self.TARGET_UPTIME,
                "actual_uptime": round(actual_uptime, 3),
                "meeting_sla": actual_uptime >= self.TARGET_UPTIME,
                "total_checks": self._metrics.total_checks,
                "successful_checks": self._metrics.successful_checks,
                "failed_checks": self._metrics.failed_checks,
                "success_rate": round(self._metrics.uptime_percentage, 3),
                "downtime_events_count": len(self._metrics.downtime_events),
                "total_downtime_seconds": total_downtime_seconds,
                "average_latencies_ms": avg_latencies,
                "monitoring_since": self._metrics.start_time.isoformat(),
            }

    def is_meeting_sla(self) -> bool:
        """Check if current uptime meets SC-014 target."""
        metrics = self.get_metrics()
        return metrics["meeting_sla"]


# Global uptime monitor instance
_uptime_monitor: Optional[UptimeMonitor] = None
_monitor_lock = threading.Lock()


def get_uptime_monitor() -> UptimeMonitor:
    """Get or create the global uptime monitor instance."""
    global _uptime_monitor
    with _monitor_lock:
        if _uptime_monitor is None:
            _uptime_monitor = UptimeMonitor()
    return _uptime_monitor
