"""
Consolidated cache mock fixtures.

FR-003: Consolidate duplicate mock_cache fixture.

This module provides centralized cache mocking for rate limiting tests,
eliminating duplicate fixture definitions across the test suite.
"""

from unittest.mock import MagicMock, patch
from typing import Optional, Callable
import pytest

from tests.constants import (
    RATE_LIMIT_LOCKOUT_5,
    RATE_LIMIT_LOCKOUT_30,
    RATE_LIMIT_PERMANENT,
)


@pytest.fixture
def mock_cache():
    """
    Consolidated cache mock fixture for rate limiting tests.

    FR-003: Consolidate duplicate mock_cache fixture

    Replaces duplicate definitions that were in:
    - tests/security/test_rate_limiting.py:80-98
    - tests/security/test_rate_limiting.py:320-339

    PROVIDES:
    - Mocked cache.get() returning None by default
    - Mocked cache.set() that tracks calls
    - Mocked cache.incr() for rate limit counters
    - Mocked cache.delete() for cleanup
    - Mocked cache.add() for atomic operations

    SCOPE: function (fresh mock per test)
    AUTOUSE: false (opt-in only)

    USAGE:
        def test_rate_limit(mock_cache):
            mock_cache.get.return_value = 5  # 5 previous attempts
            # test rate limiting behavior
    """
    mock = MagicMock()

    # Default behaviors
    mock.get.return_value = None
    mock.set.return_value = True
    mock.incr.return_value = 1
    mock.delete.return_value = True
    mock.add.return_value = True
    mock.decr.return_value = 0
    mock.touch.return_value = True
    mock.expire.return_value = True

    with patch("django.core.cache.cache", mock):
        yield mock


@pytest.fixture
def mock_cache_with_attempts():
    """
    Factory fixture for cache mock pre-configured with failed login attempts.

    USAGE:
        def test_lockout_after_5_attempts(mock_cache_with_attempts):
            mock = mock_cache_with_attempts(attempts=5)
            # Test that 6th attempt triggers lockout
    """

    def _factory(
        attempts: int = 0,
        lockout_until: Optional[float] = None,
        is_locked: bool = False,
    ) -> MagicMock:
        mock = MagicMock()

        def get_side_effect(key: str):
            if "attempts" in key:
                return attempts
            if "lockout" in key:
                return lockout_until
            if "locked" in key:
                return is_locked
            return None

        mock.get.side_effect = get_side_effect
        mock.set.return_value = True
        mock.incr.return_value = attempts + 1
        mock.delete.return_value = True
        mock.add.return_value = True

        return mock

    return _factory


@pytest.fixture
def mock_cache_lockout_scenario():
    """
    Factory fixture for testing progressive lockout scenarios.

    USAGE:
        def test_progressive_lockout(mock_cache_lockout_scenario):
            mock = mock_cache_lockout_scenario(
                threshold=RATE_LIMIT_LOCKOUT_5,
                current_attempts=4
            )
            # Test behavior at threshold boundary
    """

    def _factory(
        threshold: int = RATE_LIMIT_LOCKOUT_5,
        current_attempts: int = 0,
        lockout_active: bool = False,
        lockout_remaining_seconds: Optional[int] = None,
    ) -> MagicMock:
        mock = MagicMock()
        state = {
            "attempts": current_attempts,
            "locked": lockout_active,
            "lockout_until": lockout_remaining_seconds,
        }

        def get_side_effect(key: str):
            if "attempts" in key:
                return state["attempts"]
            if "locked" in key:
                return state["locked"]
            if "lockout" in key or "until" in key:
                return state["lockout_until"]
            return None

        def incr_side_effect(key: str, delta: int = 1):
            if "attempts" in key:
                state["attempts"] += delta
                # Auto-lockout when threshold reached
                if state["attempts"] >= threshold:
                    state["locked"] = True
                return state["attempts"]
            return 1

        mock.get.side_effect = get_side_effect
        mock.incr.side_effect = incr_side_effect
        mock.set.return_value = True
        mock.delete.return_value = True
        mock.add.return_value = True

        return mock

    return _factory


@pytest.fixture
def mock_cache_rate_window():
    """
    Factory fixture for testing rate limiting within time windows.

    USAGE:
        def test_rate_limit_window(mock_cache_rate_window):
            mock = mock_cache_rate_window(
                requests_in_window=99,
                window_limit=100
            )
            # Test that 100th request is allowed but 101st is blocked
    """

    def _factory(
        requests_in_window: int = 0,
        window_limit: int = 100,
        window_expiry_seconds: int = 60,
    ) -> MagicMock:
        mock = MagicMock()
        state = {"count": requests_in_window}

        def get_side_effect(key: str):
            if "rate" in key or "window" in key:
                return state["count"]
            return None

        def incr_side_effect(key: str, delta: int = 1):
            state["count"] += delta
            return state["count"]

        def add_side_effect(key: str, value, timeout=None):
            if state["count"] == 0:
                state["count"] = value
                return True
            return False

        mock.get.side_effect = get_side_effect
        mock.incr.side_effect = incr_side_effect
        mock.add.side_effect = add_side_effect
        mock.set.return_value = True
        mock.delete.return_value = True

        # Store config for assertions
        mock._window_limit = window_limit
        mock._window_expiry = window_expiry_seconds

        return mock

    return _factory


@pytest.fixture
def mock_redis_cache():
    """
    Mock specifically for Redis-based cache operations.

    Provides additional Redis-specific methods like pipeline, lock, etc.

    USAGE:
        def test_redis_specific_operation(mock_redis_cache):
            mock_redis_cache.lock.return_value.__enter__ = MagicMock()
            # Test Redis lock behavior
    """
    mock = MagicMock()

    # Basic cache operations
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.incr.return_value = 1
    mock.decr.return_value = 0

    # Redis-specific operations
    mock.lock.return_value = MagicMock()
    mock.lock.return_value.__enter__ = MagicMock(return_value=True)
    mock.lock.return_value.__exit__ = MagicMock(return_value=False)

    pipeline_mock = MagicMock()
    pipeline_mock.execute.return_value = []
    mock.pipeline.return_value = pipeline_mock

    mock.ttl.return_value = -1
    mock.expire.return_value = True
    mock.exists.return_value = False

    with patch("django.core.cache.cache", mock):
        yield mock


@pytest.fixture
def mock_cache_stateful():
    """
    Stateful cache mock that maintains data between operations.

    FR-003: Consolidated fixture replacing duplicate definitions in test_rate_limiter.py

    This fixture provides a cache mock that actually stores and retrieves data,
    useful for testing rate limiting and other stateful cache operations.

    The mock patches 'apps.core.security.rate_limiter.cache' and provides:
    - get: retrieves stored values
    - set: stores values
    - delete: removes values
    - _data: direct access to cache data for test inspection

    USAGE:
        def test_rate_limit_behavior(mock_cache_stateful):
            # Access stored data directly
            assert mock_cache_stateful._data == {}
    """
    cache_data = {}

    def mock_get(key, default=None):
        return cache_data.get(key, default)

    def mock_set(key, value, timeout=None):
        cache_data[key] = value

    def mock_delete(key):
        cache_data.pop(key, None)

    with patch("apps.core.security.rate_limiter.cache") as mock:
        mock.get = MagicMock(side_effect=mock_get)
        mock.set = MagicMock(side_effect=mock_set)
        mock.delete = MagicMock(side_effect=mock_delete)
        mock._data = cache_data  # For test inspection
        yield mock
