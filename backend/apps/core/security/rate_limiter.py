"""
Rate limiting for API endpoints.

Implements progressive rate limiting for login endpoints following
security best practices for brute-force attack prevention.

Rate limit tiers:
- 5 failed attempts: 5-minute lockout
- 10 failed attempts: 30-minute lockout
- 20 failed attempts: Account locked (admin unlock required)

Usage:
    from apps.core.security.rate_limiter import LoginRateLimiter

    limiter = LoginRateLimiter()

    # Check before login attempt
    if limiter.is_blocked(email, ip_address):
        return Response({"error": "Too many attempts"}, status=429)

    # Record failed attempt
    limiter.record_failure(email, ip_address)

    # Clear on success
    limiter.clear(email, ip_address)
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from django.core.cache import cache

logger = logging.getLogger(__name__)


def _hash_email(email: str) -> str:
    """Return first 12 hex chars of SHA-256 hash of *email* for safe logging."""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:12]


class LockoutTier(Enum):
    """Rate limit tiers with increasing severity."""

    NONE = "none"
    TIER_1 = "tier_1"  # 5 attempts -> 5 min lockout
    TIER_2 = "tier_2"  # 10 attempts -> 30 min lockout
    TIER_3 = "tier_3"  # 20 attempts -> account locked


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    # Tier thresholds (number of failed attempts)
    tier_1_threshold: int = 5
    tier_2_threshold: int = 10
    tier_3_threshold: int = 20

    # Lockout durations in seconds
    tier_1_duration: int = 300  # 5 minutes
    tier_2_duration: int = 1800  # 30 minutes
    tier_3_duration: int = 86400  # 24 hours (until admin unlock)

    # Sliding window for counting attempts (in seconds)
    attempt_window: int = 3600  # 1 hour

    # Cache key prefixes
    cache_prefix: str = "rate_limit"

    # Enable/disable features
    track_by_ip: bool = True
    track_by_email: bool = True
    enable_account_lock: bool = True


class LoginRateLimiter:
    """
    Progressive rate limiter for login endpoints.

    Tracks failed login attempts and implements increasing lockout
    durations based on the number of failures.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize rate limiter with configuration."""
        self.config = config or RateLimitConfig()

    def _get_cache_key(self, identifier: str, key_type: str) -> str:
        """Generate cache key for rate limiting."""
        # Hash the identifier for privacy
        hashed = hashlib.sha256(identifier.lower().encode()).hexdigest()[:16]
        return f"{self.config.cache_prefix}:{key_type}:{hashed}"

    def _get_attempts_key(self, email: str, ip_address: str) -> str:
        """Get cache key for attempt counting."""
        combined = f"{email}:{ip_address}"
        return self._get_cache_key(combined, "attempts")

    def _get_lockout_key(self, email: str, ip_address: str) -> str:
        """Get cache key for lockout status."""
        combined = f"{email}:{ip_address}"
        return self._get_cache_key(combined, "lockout")

    def _get_account_lock_key(self, email: str) -> str:
        """Get cache key for account-level lock."""
        return self._get_cache_key(email, "account_lock")

    def get_attempt_count(self, email: str, ip_address: str) -> int:
        """
        Get current failed attempt count.

        Args:
            email: User email address
            ip_address: Client IP address

        Returns:
            Number of failed attempts in the current window
        """
        key = self._get_attempts_key(email, ip_address)
        attempts = cache.get(key, [])

        # Filter to only count attempts within the window
        now = time.time()
        window_start = now - self.config.attempt_window
        recent_attempts = [t for t in attempts if t > window_start]

        return len(recent_attempts)

    def get_lockout_tier(self, attempt_count: int) -> LockoutTier:
        """
        Determine lockout tier based on attempt count.

        Args:
            attempt_count: Number of failed attempts

        Returns:
            Appropriate lockout tier
        """
        if attempt_count >= self.config.tier_3_threshold:
            return LockoutTier.TIER_3
        elif attempt_count >= self.config.tier_2_threshold:
            return LockoutTier.TIER_2
        elif attempt_count >= self.config.tier_1_threshold:
            return LockoutTier.TIER_1
        return LockoutTier.NONE

    def get_lockout_duration(self, tier: LockoutTier) -> int:
        """Get lockout duration for a tier in seconds."""
        durations = {
            LockoutTier.NONE: 0,
            LockoutTier.TIER_1: self.config.tier_1_duration,
            LockoutTier.TIER_2: self.config.tier_2_duration,
            LockoutTier.TIER_3: self.config.tier_3_duration,
        }
        return durations.get(tier, 0)

    def is_blocked(self, email: str, ip_address: str) -> bool:
        """
        Check if login attempt should be blocked.

        Args:
            email: User email address
            ip_address: Client IP address

        Returns:
            True if the login attempt should be blocked
        """
        # Check account-level lock first (most severe)
        if self.config.enable_account_lock:
            account_lock_key = self._get_account_lock_key(email)
            if cache.get(account_lock_key):
                logger.warning(
                    "Login blocked - account locked: %s",
                    _hash_email(email),
                    extra={"email_hash": _hash_email(email), "ip": ip_address},
                )
                return True

        # Check lockout status
        lockout_key = self._get_lockout_key(email, ip_address)
        lockout_data = cache.get(lockout_key)

        if lockout_data:
            lockout_until = lockout_data.get("until", 0)
            if time.time() < lockout_until:
                remaining = int(lockout_until - time.time())
                logger.warning(
                    "Login blocked - rate limited: %s (%ds remaining)",
                    _hash_email(email),
                    remaining,
                    extra={
                        "email_hash": _hash_email(email),
                        "ip": ip_address,
                        "remaining_seconds": remaining,
                    },
                )
                return True

        return False

    def get_remaining_lockout_time(self, email: str, ip_address: str) -> int:
        """
        Get remaining lockout time in seconds.

        Args:
            email: User email address
            ip_address: Client IP address

        Returns:
            Remaining lockout time in seconds, 0 if not locked out
        """
        lockout_key = self._get_lockout_key(email, ip_address)
        lockout_data = cache.get(lockout_key)

        if lockout_data:
            lockout_until = lockout_data.get("until", 0)
            remaining = lockout_until - time.time()
            return max(0, int(remaining))

        return 0

    def record_failure(self, email: str, ip_address: str) -> LockoutTier:
        """
        Record a failed login attempt.

        Args:
            email: User email address
            ip_address: Client IP address

        Returns:
            The lockout tier that was triggered (if any)
        """
        # Get and update attempt count
        attempts_key = self._get_attempts_key(email, ip_address)
        attempts = cache.get(attempts_key, [])

        # Clean old attempts
        now = time.time()
        window_start = now - self.config.attempt_window
        attempts = [t for t in attempts if t > window_start]

        # Add new attempt
        attempts.append(now)
        cache.set(attempts_key, attempts, timeout=self.config.attempt_window)

        # Determine and apply lockout
        attempt_count = len(attempts)
        tier = self.get_lockout_tier(attempt_count)

        if tier != LockoutTier.NONE:
            self._apply_lockout(email, ip_address, tier, attempt_count)

        logger.info(
            "Failed login recorded: %s (attempt %d)",
            _hash_email(email),
            attempt_count,
            extra={
                "email_hash": _hash_email(email),
                "ip": ip_address,
                "attempt_count": attempt_count,
                "tier": tier.value,
            },
        )

        return tier

    def _apply_lockout(
        self, email: str, ip_address: str, tier: LockoutTier, attempt_count: int
    ) -> None:
        """Apply lockout based on tier."""
        duration = self.get_lockout_duration(tier)
        lockout_until = time.time() + duration

        lockout_key = self._get_lockout_key(email, ip_address)
        lockout_data = {
            "until": lockout_until,
            "tier": tier.value,
            "attempt_count": attempt_count,
            "created_at": time.time(),
        }
        cache.set(lockout_key, lockout_data, timeout=duration)

        logger.warning(
            "Lockout applied: %s - %s for %ds",
            _hash_email(email),
            tier.value,
            duration,
            extra={
                "email_hash": _hash_email(email),
                "ip": ip_address,
                "tier": tier.value,
                "duration": duration,
                "attempt_count": attempt_count,
            },
        )

        # Apply account-level lock for tier 3
        if tier == LockoutTier.TIER_3 and self.config.enable_account_lock:
            self._lock_account(email)

    def _lock_account(self, email: str) -> None:
        """Lock account (tier 3 - requires admin unlock)."""
        account_lock_key = self._get_account_lock_key(email)
        lock_data = {
            "locked_at": time.time(),
            "reason": "excessive_failed_attempts",
        }
        # Account lock persists until admin unlocks
        cache.set(account_lock_key, lock_data, timeout=self.config.tier_3_duration)

        logger.critical(
            "Account locked due to excessive failed attempts: %s",
            _hash_email(email),
            extra={"email_hash": _hash_email(email), "reason": "excessive_failed_attempts"},
        )

    def clear(self, email: str, ip_address: str) -> None:
        """
        Clear rate limiting state after successful login.

        Args:
            email: User email address
            ip_address: Client IP address
        """
        attempts_key = self._get_attempts_key(email, ip_address)
        lockout_key = self._get_lockout_key(email, ip_address)

        cache.delete(attempts_key)
        cache.delete(lockout_key)

        logger.info(
            "Rate limit cleared on successful login: %s",
            _hash_email(email),
            extra={"email_hash": _hash_email(email), "ip": ip_address},
        )

    def unlock_account(self, email: str) -> bool:
        """
        Admin function to unlock a locked account.

        Args:
            email: User email address

        Returns:
            True if account was unlocked, False if not locked
        """
        account_lock_key = self._get_account_lock_key(email)

        if cache.get(account_lock_key):
            cache.delete(account_lock_key)
            logger.info(
                "Account unlocked by admin: %s",
                _hash_email(email),
                extra={"email_hash": _hash_email(email), "action": "admin_unlock"},
            )
            return True

        return False

    def get_status(self, email: str, ip_address: str) -> dict:
        """
        Get rate limiting status for debugging/admin.

        Args:
            email: User email address
            ip_address: Client IP address

        Returns:
            Status dictionary with current state
        """
        attempt_count = self.get_attempt_count(email, ip_address)
        tier = self.get_lockout_tier(attempt_count)
        remaining = self.get_remaining_lockout_time(email, ip_address)

        account_lock_key = self._get_account_lock_key(email)
        account_locked = bool(cache.get(account_lock_key))

        return {
            "email": email,
            "ip_address": ip_address,
            "attempt_count": attempt_count,
            "current_tier": tier.value,
            "is_blocked": self.is_blocked(email, ip_address),
            "remaining_lockout_seconds": remaining,
            "account_locked": account_locked,
            "thresholds": {
                "tier_1": self.config.tier_1_threshold,
                "tier_2": self.config.tier_2_threshold,
                "tier_3": self.config.tier_3_threshold,
            },
        }


# DRF Throttle class for integration with ViewSets
class LoginThrottle:
    """
    DRF-compatible throttle for login endpoints.

    Usage in views.py:
        from rest_framework.throttling import BaseThrottle
        from apps.core.security.rate_limiter import LoginThrottle

        class CustomTokenObtainPairView(TokenObtainPairView):
            throttle_classes = [LoginThrottle]
    """

    scope = "login"

    def __init__(self):
        self.limiter = LoginRateLimiter()
        self._last_email: str = ""
        self._last_ip: str = ""

    def allow_request(self, request, view) -> bool:
        """Check if request should be allowed."""
        self._last_email = request.data.get("email", "")
        self._last_ip = self._get_client_ip(request)

        return not self.limiter.is_blocked(self._last_email, self._last_ip)

    def wait(self) -> Optional[int]:
        """Return seconds until the lockout expires (for Retry-After header)."""
        remaining = self.limiter.get_remaining_lockout_time(
            self._last_email, self._last_ip
        )
        return remaining if remaining > 0 else None

    def _get_client_ip(self, request) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


# Singleton instance for easy import
_default_limiter: Optional[LoginRateLimiter] = None


def get_login_limiter() -> LoginRateLimiter:
    """Get or create default login rate limiter instance."""
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = LoginRateLimiter()
    return _default_limiter
