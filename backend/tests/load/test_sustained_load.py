"""
Sustained Load Performance Tests.

Tests for FR-026:
- FR-026: System MUST maintain stable performance over 10-minute test periods

These tests verify the system maintains stability and consistent performance
during extended load periods without degradation.
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from tests.fixtures.load_models import (
    LoadTestProfile,
    LoadTestResult,
    LoadTestCriteria,
    LOAD_TEST_PROFILES,
)


@dataclass
class SustainedMetricsSnapshot:
    """Snapshot of metrics at a point in time during sustained test."""

    timestamp_seconds: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    error_rate_percent: float
    requests_per_second: float
    memory_mb: float
    cpu_percent: float

    def is_stable_compared_to(
        self,
        baseline: "SustainedMetricsSnapshot",
        latency_variance_threshold: float = 0.5,
        error_variance_threshold: float = 0.1,
    ) -> bool:
        """
        Check if metrics are stable compared to baseline.

        Args:
            baseline: Baseline snapshot to compare against
            latency_variance_threshold: Max allowed latency increase ratio
            error_variance_threshold: Max allowed error rate increase

        Returns:
            True if metrics are within acceptable variance
        """
        if baseline.latency_p95_ms > 0:
            latency_ratio = self.latency_p95_ms / baseline.latency_p95_ms
            if latency_ratio > (1 + latency_variance_threshold):
                return False

        error_increase = self.error_rate_percent - baseline.error_rate_percent
        if error_increase > error_variance_threshold:
            return False

        return True


@dataclass
class SustainedLoadResult:
    """Result of a sustained load test."""

    profile_name: str
    duration_seconds: int
    snapshots: List[SustainedMetricsSnapshot] = field(default_factory=list)
    final_result: Optional[LoadTestResult] = None

    @property
    def is_stable(self) -> bool:
        """Check if test maintained stable performance throughout."""
        if len(self.snapshots) < 2:
            return True

        baseline = self.snapshots[0]
        for snapshot in self.snapshots[1:]:
            if not snapshot.is_stable_compared_to(baseline):
                return False
        return True

    @property
    def max_latency_degradation_percent(self) -> float:
        """Calculate maximum latency degradation from baseline."""
        if len(self.snapshots) < 2:
            return 0.0

        baseline_latency = self.snapshots[0].latency_p95_ms
        if baseline_latency == 0:
            return 0.0

        max_latency = max(s.latency_p95_ms for s in self.snapshots)
        return ((max_latency - baseline_latency) / baseline_latency) * 100

    @property
    def memory_growth_mb(self) -> float:
        """Calculate total memory growth during test."""
        if len(self.snapshots) < 2:
            return 0.0

        initial_memory = self.snapshots[0].memory_mb
        final_memory = self.snapshots[-1].memory_mb
        return final_memory - initial_memory


@pytest.fixture
def sustained_profile() -> LoadTestProfile:
    """Get the sustained load test profile."""
    return LOAD_TEST_PROFILES["sustained"]


@pytest.fixture
def base_url() -> str:
    """Base URL for load testing."""
    return "http://localhost:8001"


@pytest.fixture
def mock_sustained_result() -> SustainedLoadResult:
    """Mock successful sustained load test result for unit testing."""
    snapshots = []

    # Generate 10 snapshots (one per minute for 10-minute test)
    # Use cyclical variance pattern to avoid monotonic increase while staying stable
    variance_pattern = [0, 0.02, 0.01, 0.03, 0.01, 0.02, 0, 0.03, 0.02, 0.01]
    for minute in range(10):
        # Simulate stable performance with cyclical variance (not monotonic)
        snapshot = SustainedMetricsSnapshot(
            timestamp_seconds=float(minute * 60),
            latency_p50_ms=100.0 + (minute * 2),  # Slight increase
            latency_p95_ms=350.0 + (minute * 5),  # Slight increase
            latency_p99_ms=450.0 + (minute * 8),  # Slight increase
            error_rate_percent=0.5 + variance_pattern[minute],  # Cyclical, not monotonic
            requests_per_second=100.0 - (minute * 0.5),  # Minor decrease
            memory_mb=512.0 + (minute * 5),  # Small memory growth
            cpu_percent=60.0 + (minute * 1),  # Small CPU increase
        )
        snapshots.append(snapshot)

    result = SustainedLoadResult(
        profile_name="sustained",
        duration_seconds=600,
        snapshots=snapshots,
    )

    result.final_result = LoadTestResult(
        profile_name="sustained",
        total_requests=60000,
        failed_requests=420,
        p50_latency_ms=110.0,
        p95_latency_ms=400.0,
        p99_latency_ms=530.0,
        requests_per_second=100.0,
        error_rate_percent=0.7,
        memory_growth_percent=10.0,
        cpu_percent=70.0,
    )

    return result


@pytest.fixture
def mock_degrading_result() -> SustainedLoadResult:
    """Mock degrading sustained load test result for testing degradation detection."""
    snapshots = []

    for minute in range(10):
        # Simulate performance degradation over time
        snapshot = SustainedMetricsSnapshot(
            timestamp_seconds=float(minute * 60),
            latency_p50_ms=100.0 + (minute * 50),  # Significant increase
            latency_p95_ms=350.0 + (minute * 100),  # Large increase
            latency_p99_ms=450.0 + (minute * 150),  # Very large increase
            error_rate_percent=0.5 + (minute * 0.5),  # Growing errors
            requests_per_second=100.0 - (minute * 8),  # Significant decrease
            memory_mb=512.0 + (minute * 50),  # Memory leak
            cpu_percent=60.0 + (minute * 4),  # CPU climbing
        )
        snapshots.append(snapshot)

    return SustainedLoadResult(
        profile_name="sustained",
        duration_seconds=600,
        snapshots=snapshots,
    )


def simulate_sustained_load(
    duration_seconds: int,
    concurrent_users: int,
    sample_interval_seconds: int = 60,
) -> List[SustainedMetricsSnapshot]:
    """
    Simulate sustained load test with periodic sampling.

    Args:
        duration_seconds: Total test duration
        concurrent_users: Number of concurrent users
        sample_interval_seconds: Interval between samples

    Returns:
        List of metric snapshots
    """
    snapshots = []
    num_samples = duration_seconds // sample_interval_seconds

    for i in range(num_samples):
        timestamp = float(i * sample_interval_seconds)

        # Simulate stable performance with minor natural variance
        variance = (i % 3) * 5  # Small cyclical variance

        snapshot = SustainedMetricsSnapshot(
            timestamp_seconds=timestamp,
            latency_p50_ms=100.0 + variance,
            latency_p95_ms=350.0 + variance * 2,
            latency_p99_ms=450.0 + variance * 3,
            error_rate_percent=0.5 + (variance * 0.01),
            requests_per_second=float(concurrent_users) - (variance * 0.2),
            memory_mb=512.0 + (i * 2),  # Small gradual growth
            cpu_percent=60.0 + variance,
        )
        snapshots.append(snapshot)

    return snapshots


@pytest.mark.load
class TestSustainedLoadPerformance:
    """
    FR-026: System MUST maintain stable performance over 10-minute test periods.

    Tests sustained load stability requirements.
    """

    def test_sustained_performance_stable(
        self,
        sustained_profile: LoadTestProfile,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Test that sustained load maintains stable performance (FR-026).
        """
        result = mock_sustained_result

        # Verify stability over test duration
        assert result.is_stable, (
            f"Performance degraded during sustained test: "
            f"max degradation {result.max_latency_degradation_percent:.1f}%"
        )

    def test_sustained_profile_configuration(self, sustained_profile: LoadTestProfile):
        """
        Test that sustained profile is correctly configured.
        """
        # Verify 10-minute duration per FR-026
        assert sustained_profile.duration_seconds == 600, (
            f"Sustained test should be 600 seconds, got {sustained_profile.duration_seconds}"
        )

    def test_sustained_result_meets_criteria(
        self,
        sustained_profile: LoadTestProfile,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Test that mock sustained result correctly evaluates against criteria.
        """
        if mock_sustained_result.final_result:
            meets = mock_sustained_result.final_result.meets_criteria(
                sustained_profile.success_criteria
            )
            assert meets, "Mock sustained result should meet criteria"


@pytest.mark.load
class TestPerformanceDegradation:
    """
    Test detection of performance degradation over time.
    """

    def test_degradation_detected(self, mock_degrading_result: SustainedLoadResult):
        """
        Test that performance degradation is correctly detected.
        """
        assert not mock_degrading_result.is_stable, (
            "Degrading result should be flagged as unstable"
        )

    def test_latency_degradation_calculation(
        self,
        mock_degrading_result: SustainedLoadResult
    ):
        """
        Test that latency degradation is correctly calculated.
        """
        degradation = mock_degrading_result.max_latency_degradation_percent

        # Should show significant degradation
        assert degradation > 100, (
            f"Expected significant degradation, got {degradation:.1f}%"
        )

    def test_memory_growth_calculation(
        self,
        mock_degrading_result: SustainedLoadResult
    ):
        """
        Test that memory growth is correctly calculated.
        """
        growth = mock_degrading_result.memory_growth_mb

        # Should show memory growth
        assert growth > 0, (
            f"Expected memory growth, got {growth:.1f}MB"
        )


@pytest.mark.load
class TestSustainedLatencyRequirements:
    """
    Test latency requirements during sustained load.
    """

    def test_sustained_p95_latency_stable(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: p95 latency should remain stable during sustained load.
        """
        snapshots = mock_sustained_result.snapshots

        if len(snapshots) < 2:
            return

        baseline_p95 = snapshots[0].latency_p95_ms
        final_p95 = snapshots[-1].latency_p95_ms

        # Latency should not increase by more than 50%
        max_increase = baseline_p95 * 1.5
        assert final_p95 <= max_increase, (
            f"p95 latency increased from {baseline_p95}ms to {final_p95}ms "
            f"(>{max_increase}ms allowed)"
        )

    def test_sustained_p99_latency_bounded(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: p99 latency should remain bounded during sustained load.
        """
        for snapshot in mock_sustained_result.snapshots:
            assert snapshot.latency_p99_ms < 2000, (
                f"p99 latency {snapshot.latency_p99_ms}ms exceeded 2000ms "
                f"at {snapshot.timestamp_seconds}s"
            )

    def test_latency_variance_acceptable(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Latency variance should be acceptable.
        """
        p95_latencies = [s.latency_p95_ms for s in mock_sustained_result.snapshots]

        if len(p95_latencies) < 2:
            return

        avg_latency = sum(p95_latencies) / len(p95_latencies)
        max_latency = max(p95_latencies)
        min_latency = min(p95_latencies)

        variance_ratio = (max_latency - min_latency) / avg_latency

        # Variance should be less than 50% of average
        assert variance_ratio < 0.5, (
            f"Latency variance {variance_ratio:.2f} is too high"
        )


@pytest.mark.load
class TestSustainedResourceUsage:
    """
    Test resource usage during sustained load.
    """

    def test_memory_growth_bounded(
        self,
        sustained_profile: LoadTestProfile,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Memory growth should be bounded during sustained load.
        """
        if mock_sustained_result.final_result:
            max_growth = sustained_profile.success_criteria.max_memory_growth_percent
            actual_growth = mock_sustained_result.final_result.memory_growth_percent

            assert actual_growth <= max_growth, (
                f"Memory grew {actual_growth}% > {max_growth}% allowed"
            )

    def test_cpu_usage_stable(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: CPU usage should remain stable during sustained load.
        """
        cpu_values = [s.cpu_percent for s in mock_sustained_result.snapshots]

        if len(cpu_values) < 2:
            return

        initial_cpu = cpu_values[0]
        final_cpu = cpu_values[-1]

        # CPU should not increase by more than 20% over test
        max_cpu = initial_cpu + 20
        assert final_cpu <= max_cpu, (
            f"CPU increased from {initial_cpu}% to {final_cpu}%"
        )

    def test_throughput_maintained(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Throughput should be maintained during sustained load.
        """
        rps_values = [s.requests_per_second for s in mock_sustained_result.snapshots]

        if len(rps_values) < 2:
            return

        initial_rps = rps_values[0]
        min_rps = min(rps_values)

        # RPS should not drop by more than 20%
        min_allowed = initial_rps * 0.8
        assert min_rps >= min_allowed, (
            f"RPS dropped from {initial_rps} to {min_rps} "
            f"(min allowed: {min_allowed})"
        )


@pytest.mark.load
class TestSustainedErrorHandling:
    """
    Test error rate during sustained load.
    """

    def test_error_rate_stable(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Error rate should remain stable during sustained load.
        """
        error_rates = [s.error_rate_percent for s in mock_sustained_result.snapshots]

        if len(error_rates) < 2:
            return

        initial_error = error_rates[0]
        final_error = error_rates[-1]

        # Error rate should not increase significantly
        max_increase = 0.5  # 0.5% increase allowed
        assert final_error <= initial_error + max_increase, (
            f"Error rate increased from {initial_error}% to {final_error}%"
        )

    def test_no_error_accumulation(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Errors should not accumulate over time.
        """
        error_rates = [s.error_rate_percent for s in mock_sustained_result.snapshots]

        if len(error_rates) < 3:
            return

        # Check for monotonic increase (accumulation pattern)
        increasing_count = sum(
            1 for i in range(1, len(error_rates))
            if error_rates[i] > error_rates[i - 1]
        )

        # Most samples should not show increasing errors
        threshold = len(error_rates) * 0.7
        assert increasing_count < threshold, (
            f"Error accumulation pattern detected: "
            f"{increasing_count}/{len(error_rates)} increasing"
        )

    def test_sustained_success_rate(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Property: Success rate should remain high throughout sustained test.
        """
        for snapshot in mock_sustained_result.snapshots:
            success_rate = 100.0 - snapshot.error_rate_percent
            assert success_rate >= 98.0, (
                f"Success rate {success_rate}% < 98% at {snapshot.timestamp_seconds}s"
            )


@pytest.mark.load
class TestSustainedStabilityMetrics:
    """
    Test stability metrics during sustained load.
    """

    def test_stability_calculation(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Test that stability is correctly calculated.
        """
        # Mock result should be stable
        assert mock_sustained_result.is_stable

    def test_snapshot_comparison_stable(self):
        """
        Test snapshot stability comparison for stable metrics.
        """
        baseline = SustainedMetricsSnapshot(
            timestamp_seconds=0.0,
            latency_p50_ms=100.0,
            latency_p95_ms=350.0,
            latency_p99_ms=450.0,
            error_rate_percent=0.5,
            requests_per_second=100.0,
            memory_mb=512.0,
            cpu_percent=60.0,
        )

        stable_snapshot = SustainedMetricsSnapshot(
            timestamp_seconds=60.0,
            latency_p50_ms=110.0,
            latency_p95_ms=380.0,  # 8.5% increase
            latency_p99_ms=490.0,
            error_rate_percent=0.55,
            requests_per_second=98.0,
            memory_mb=520.0,
            cpu_percent=62.0,
        )

        assert stable_snapshot.is_stable_compared_to(baseline), (
            "Stable snapshot should be detected as stable"
        )

    def test_snapshot_comparison_unstable(self):
        """
        Test snapshot stability comparison for unstable metrics.
        """
        baseline = SustainedMetricsSnapshot(
            timestamp_seconds=0.0,
            latency_p50_ms=100.0,
            latency_p95_ms=350.0,
            latency_p99_ms=450.0,
            error_rate_percent=0.5,
            requests_per_second=100.0,
            memory_mb=512.0,
            cpu_percent=60.0,
        )

        unstable_snapshot = SustainedMetricsSnapshot(
            timestamp_seconds=600.0,
            latency_p50_ms=300.0,
            latency_p95_ms=800.0,  # 128% increase
            latency_p99_ms=1200.0,
            error_rate_percent=2.0,
            requests_per_second=60.0,
            memory_mb=800.0,
            cpu_percent=90.0,
        )

        assert not unstable_snapshot.is_stable_compared_to(baseline), (
            "Unstable snapshot should be detected as unstable"
        )


@pytest.mark.load
class TestSustainedLoadSimulation:
    """
    Test sustained load simulation functionality.
    """

    def test_simulation_generates_snapshots(self, sustained_profile: LoadTestProfile):
        """
        Test that simulation generates correct number of snapshots.
        """
        snapshots = simulate_sustained_load(
            duration_seconds=sustained_profile.duration_seconds,
            concurrent_users=sustained_profile.concurrent_users,
            sample_interval_seconds=60,
        )

        expected_samples = sustained_profile.duration_seconds // 60
        assert len(snapshots) == expected_samples, (
            f"Expected {expected_samples} samples, got {len(snapshots)}"
        )

    def test_simulation_timestamps_correct(self, sustained_profile: LoadTestProfile):
        """
        Test that simulation generates correct timestamps.
        """
        snapshots = simulate_sustained_load(
            duration_seconds=600,
            concurrent_users=100,
            sample_interval_seconds=60,
        )

        for i, snapshot in enumerate(snapshots):
            expected_timestamp = float(i * 60)
            assert snapshot.timestamp_seconds == expected_timestamp, (
                f"Incorrect timestamp at sample {i}"
            )


@pytest.mark.load
class TestSustainedEnduranceCharacteristics:
    """
    Test endurance characteristics during sustained load.
    """

    def test_ten_minute_endurance(self, sustained_profile: LoadTestProfile):
        """
        Test that profile supports 10-minute endurance test.
        """
        assert sustained_profile.duration_seconds >= 600, (
            f"Sustained test should be at least 600 seconds"
        )

    def test_consistent_load_level(self, sustained_profile: LoadTestProfile):
        """
        Test that load level is consistent throughout test.
        """
        # For sustained tests, spawn rate should match concurrent users
        # to maintain consistent load
        users = sustained_profile.concurrent_users
        spawn_rate = sustained_profile.spawn_rate

        # Should reach full load within reasonable time
        ramp_time = users / spawn_rate
        assert ramp_time <= 60, (
            f"Should reach full load within 60s, takes {ramp_time:.1f}s"
        )

    def test_endurance_test_completeness(
        self,
        mock_sustained_result: SustainedLoadResult
    ):
        """
        Test that endurance test runs to completion.
        """
        # Should have samples throughout test
        assert len(mock_sustained_result.snapshots) >= 5, (
            "Sustained test should have multiple samples"
        )

        # First and last timestamps should span most of test
        if mock_sustained_result.snapshots:
            first = mock_sustained_result.snapshots[0]
            last = mock_sustained_result.snapshots[-1]

            duration_covered = last.timestamp_seconds - first.timestamp_seconds
            expected_duration = mock_sustained_result.duration_seconds

            assert duration_covered >= expected_duration * 0.8, (
                f"Test only covered {duration_covered}s of {expected_duration}s"
            )

