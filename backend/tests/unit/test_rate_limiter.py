"""
Unit tests for login rate limiter.

Tests the progressive rate limiting system for brute-force protection.

FR-003: Uses consolidated mock_cache_stateful fixture from tests.fixtures.cache
"""

import time

import pytest

from apps.core.security.rate_limiter import (
    LoginRateLimiter,
    LockoutTier,
    RateLimitConfig,
)
from tests.fixtures.cache import mock_cache_stateful


@pytest.mark.unit
class TestRateLimitConfig:
    """Test RateLimitConfig defaults and customization."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.tier_1_threshold == 5
        assert config.tier_2_threshold == 10
        assert config.tier_3_threshold == 20
        assert config.tier_1_duration == 300  # 5 minutes
        assert config.tier_2_duration == 1800  # 30 minutes
        assert config.tier_3_duration == 86400  # 24 hours

    def test_custom_config(self):
        """Test custom configuration."""
        config = RateLimitConfig(
            tier_1_threshold=3,
            tier_2_threshold=6,
            tier_3_threshold=10,
            tier_1_duration=60,
        )

        assert config.tier_1_threshold == 3
        assert config.tier_2_threshold == 6
        assert config.tier_3_threshold == 10
        assert config.tier_1_duration == 60


@pytest.mark.unit
class TestLockoutTier:
    """Test LockoutTier enum."""

    def test_tier_values(self):
        """Test tier enum values."""
        assert LockoutTier.NONE.value == "none"
        assert LockoutTier.TIER_1.value == "tier_1"
        assert LockoutTier.TIER_2.value == "tier_2"
        assert LockoutTier.TIER_3.value == "tier_3"


@pytest.mark.unit
class TestLoginRateLimiter:
    """Test LoginRateLimiter functionality."""

    @pytest.fixture
    def limiter(self):
        """Create limiter with test-friendly config."""
        config = RateLimitConfig(
            tier_1_threshold=3,
            tier_2_threshold=5,
            tier_3_threshold=8,
            tier_1_duration=60,
            tier_2_duration=120,
            tier_3_duration=300,
            attempt_window=600,
        )
        return LoginRateLimiter(config)

    # FR-003: mock_cache fixture removed - using consolidated mock_cache_stateful from tests.fixtures.cache

    def test_initial_state_not_blocked(self, limiter, mock_cache_stateful):
        """Test that new user is not blocked."""
        assert limiter.is_blocked("test@example.com", "192.168.1.1") is False

    def test_get_attempt_count_empty(self, limiter, mock_cache_stateful):
        """Test attempt count starts at zero."""
        count = limiter.get_attempt_count("test@example.com", "192.168.1.1")
        assert count == 0

    def test_get_lockout_tier(self, limiter):
        """Test tier determination based on attempt count."""
        assert limiter.get_lockout_tier(0) == LockoutTier.NONE
        assert limiter.get_lockout_tier(2) == LockoutTier.NONE
        assert limiter.get_lockout_tier(3) == LockoutTier.TIER_1
        assert limiter.get_lockout_tier(4) == LockoutTier.TIER_1
        assert limiter.get_lockout_tier(5) == LockoutTier.TIER_2
        assert limiter.get_lockout_tier(7) == LockoutTier.TIER_2
        assert limiter.get_lockout_tier(8) == LockoutTier.TIER_3
        assert limiter.get_lockout_tier(100) == LockoutTier.TIER_3

    def test_get_lockout_duration(self, limiter):
        """Test lockout duration for each tier."""
        assert limiter.get_lockout_duration(LockoutTier.NONE) == 0
        assert limiter.get_lockout_duration(LockoutTier.TIER_1) == 60
        assert limiter.get_lockout_duration(LockoutTier.TIER_2) == 120
        assert limiter.get_lockout_duration(LockoutTier.TIER_3) == 300

    def test_record_failure_increments_count(self, limiter, mock_cache_stateful):
        """Test that recording failure increments attempt count."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # First failure
        tier = limiter.record_failure(email, ip)
        assert tier == LockoutTier.NONE
        assert limiter.get_attempt_count(email, ip) == 1

        # Second failure
        tier = limiter.record_failure(email, ip)
        assert tier == LockoutTier.NONE
        assert limiter.get_attempt_count(email, ip) == 2

    def test_record_failure_triggers_tier_1(self, limiter, mock_cache_stateful):
        """Test tier 1 lockout after threshold failures."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Record failures up to threshold
        for _ in range(2):
            limiter.record_failure(email, ip)

        # Third failure triggers tier 1
        tier = limiter.record_failure(email, ip)
        assert tier == LockoutTier.TIER_1
        assert limiter.is_blocked(email, ip) is True

    def test_record_failure_triggers_tier_2(self, limiter, mock_cache_stateful):
        """Test tier 2 lockout after threshold failures."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Record failures up to tier 2 threshold
        for i in range(5):
            tier = limiter.record_failure(email, ip)

        assert tier == LockoutTier.TIER_2

    def test_record_failure_triggers_tier_3(self, limiter, mock_cache_stateful):
        """Test tier 3 lockout (account lock) after threshold failures."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Record failures up to tier 3 threshold
        for i in range(8):
            tier = limiter.record_failure(email, ip)

        assert tier == LockoutTier.TIER_3

    def test_clear_resets_state(self, limiter, mock_cache_stateful):
        """Test that clear resets rate limiting state."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Create some failed attempts
        for _ in range(3):
            limiter.record_failure(email, ip)

        assert limiter.is_blocked(email, ip) is True

        # Clear on successful login
        limiter.clear(email, ip)

        # Should no longer be blocked
        assert limiter.is_blocked(email, ip) is False
        assert limiter.get_attempt_count(email, ip) == 0

    def test_unlock_account(self, limiter, mock_cache_stateful):
        """Test admin account unlock."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Lock account with tier 3
        for _ in range(8):
            limiter.record_failure(email, ip)

        # Account should be locked
        status = limiter.get_status(email, ip)
        assert status["account_locked"] is True

        # Admin unlock
        result = limiter.unlock_account(email)
        assert result is True

        # Account should be unlocked
        status = limiter.get_status(email, ip)
        assert status["account_locked"] is False

    def test_unlock_account_not_locked(self, limiter, mock_cache_stateful):
        """Test unlock returns False if not locked."""
        result = limiter.unlock_account("nonexistent@example.com")
        assert result is False

    def test_get_remaining_lockout_time(self, limiter, mock_cache_stateful):
        """Test remaining lockout time calculation."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # No lockout initially
        assert limiter.get_remaining_lockout_time(email, ip) == 0

        # Trigger lockout
        for _ in range(3):
            limiter.record_failure(email, ip)

        # Should have remaining time
        remaining = limiter.get_remaining_lockout_time(email, ip)
        assert remaining > 0
        assert remaining <= 60  # Tier 1 duration

    def test_get_status(self, limiter, mock_cache_stateful):
        """Test status dictionary."""
        email = "test@example.com"
        ip = "192.168.1.1"

        status = limiter.get_status(email, ip)

        assert status["email"] == email
        assert status["ip_address"] == ip
        assert status["attempt_count"] == 0
        assert status["current_tier"] == "none"
        assert status["is_blocked"] is False
        assert status["account_locked"] is False
        assert "thresholds" in status

    def test_different_ips_tracked_separately(self, limiter, mock_cache_stateful):
        """Test that different IPs are tracked separately."""
        email = "test@example.com"
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"

        # Fail from IP 1
        for _ in range(3):
            limiter.record_failure(email, ip1)

        # IP 1 should be blocked, IP 2 should not
        assert limiter.is_blocked(email, ip1) is True
        assert limiter.is_blocked(email, ip2) is False

    def test_different_emails_tracked_separately(self, limiter, mock_cache_stateful):
        """Test that different emails are tracked separately."""
        email1 = "test1@example.com"
        email2 = "test2@example.com"
        ip = "192.168.1.1"

        # Fail for email 1
        for _ in range(3):
            limiter.record_failure(email1, ip)

        # Email 1 should be blocked, email 2 should not
        assert limiter.is_blocked(email1, ip) is True
        assert limiter.is_blocked(email2, ip) is False


@pytest.mark.unit
class TestLoginRateLimiterIntegration:
    """Integration tests with Django cache."""

    @pytest.fixture
    def limiter(self):
        """Create limiter with fast timeouts for testing."""
        config = RateLimitConfig(
            tier_1_threshold=2,
            tier_1_duration=1,  # 1 second lockout
            attempt_window=60,
        )
        return LoginRateLimiter(config)

    @pytest.mark.django_db
    def test_lockout_expires(self, limiter, mock_cache_stateful):
        """Test that lockout expires after duration."""
        email = "test@example.com"
        ip = "192.168.1.1"

        # Trigger lockout
        for _ in range(2):
            limiter.record_failure(email, ip)

        assert limiter.is_blocked(email, ip) is True

        # Wait for lockout to expire
        time.sleep(1.5)

        # Manually clear expired lockout from mock cache to simulate expiry
        # (Real Django cache would handle TTL automatically)
        lockout_key = limiter._get_lockout_key(email, ip)
        mock_cache_stateful._data.pop(lockout_key, None)

        # Should no longer be blocked (lockout expired)
        assert limiter.is_blocked(email, ip) is False
