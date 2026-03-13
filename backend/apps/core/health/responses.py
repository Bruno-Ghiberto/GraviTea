"""
Health check response structures.

Provides dataclasses for building standardized health check responses
compatible with Kubernetes probes.

Per spec.md FR-019 through FR-023 requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass(slots=True)
class DependencyCheck:
    """Individual dependency health check result.

    Represents the health status of a single dependency (e.g., database, cache).
    Includes latency metrics when healthy or error message when unhealthy.

    Attributes:
        status: Health status - "healthy" or "unhealthy"
        latency_ms: Response time in milliseconds (only when healthy)
        error: Error message (only when unhealthy)
    """

    status: Literal["healthy", "unhealthy"]
    latency_ms: float | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate that latency_ms and error are mutually exclusive."""
        if self.status == "healthy" and self.error is not None:
            raise ValueError("error should not be set when status is 'healthy'")
        if self.status == "unhealthy" and self.latency_ms is not None:
            raise ValueError("latency_ms should not be set when status is 'unhealthy'")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Only includes non-None fields.

        Returns:
            Dict representation suitable for JSON serialization
        """
        result: dict[str, Any] = {"status": self.status}

        if self.latency_ms is not None:
            result["latency_ms"] = round(self.latency_ms, 2)

        if self.error is not None:
            result["error"] = self.error

        return result

    @classmethod
    def healthy(cls, latency_ms: float) -> DependencyCheck:
        """Create a healthy dependency check result.

        Args:
            latency_ms: The response time in milliseconds

        Returns:
            A healthy DependencyCheck instance
        """
        return cls(status="healthy", latency_ms=latency_ms)

    @classmethod
    def unhealthy(cls, error: str) -> DependencyCheck:
        """Create an unhealthy dependency check result.

        Args:
            error: The error message describing the failure

        Returns:
            An unhealthy DependencyCheck instance
        """
        return cls(status="unhealthy", error=error)


@dataclass(slots=True)
class HealthCheckResponse:
    """Health check endpoint response structure.

    Aggregates individual dependency checks into an overall health status.
    The overall status is "unhealthy" if any dependency is unhealthy.

    Attributes:
        status: Overall health status - "healthy" or "unhealthy"
        checks: Dictionary of dependency name to check result
        timestamp: ISO 8601 timestamp of the check
    """

    status: Literal["healthy", "unhealthy"]
    checks: dict[str, DependencyCheck] | None = None
    timestamp: str | None = None

    def __post_init__(self) -> None:
        """Set timestamp if not provided and validate consistency."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

        # Validate that status matches check results
        if self.checks:
            any_unhealthy = any(c.status == "unhealthy" for c in self.checks.values())
            if any_unhealthy and self.status == "healthy":
                raise ValueError(
                    "Overall status must be 'unhealthy' when any dependency is unhealthy"
                )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        result: dict[str, Any] = {"status": self.status}

        if self.checks:
            result["checks"] = {name: check.to_dict() for name, check in self.checks.items()}

        if self.timestamp:
            result["timestamp"] = self.timestamp

        return result

    @classmethod
    def from_checks(cls, checks: dict[str, DependencyCheck]) -> HealthCheckResponse:
        """Create a HealthCheckResponse from dependency checks.

        Automatically determines overall status based on individual checks.

        Args:
            checks: Dictionary mapping dependency names to check results

        Returns:
            A HealthCheckResponse with appropriate overall status
        """
        any_unhealthy = any(c.status == "unhealthy" for c in checks.values())
        status: Literal["healthy", "unhealthy"] = "unhealthy" if any_unhealthy else "healthy"
        return cls(status=status, checks=checks)

    @classmethod
    def simple_healthy(cls) -> HealthCheckResponse:
        """Create a simple healthy response without checks.

        Used for liveness probes that don't need dependency checks.

        Returns:
            A simple healthy HealthCheckResponse
        """
        return cls(status="healthy")

    @classmethod
    def simple_unhealthy(cls, error: str | None = None) -> HealthCheckResponse:
        """Create a simple unhealthy response.

        Args:
            error: Optional error message

        Returns:
            An unhealthy HealthCheckResponse
        """
        return cls(status="unhealthy")
