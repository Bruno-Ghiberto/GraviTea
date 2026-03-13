"""
Health check implementations for various dependencies.

Provides check functions for database connectivity, migrations status,
and other infrastructure dependencies.

Per spec.md FR-019 through FR-023 requirements.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.core.health.responses import DependencyCheck

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def check_database() -> DependencyCheck:
    """Check database connectivity and measure latency.

    Executes a simple SELECT 1 query to verify the database connection
    is alive and responsive.

    Returns:
        DependencyCheck with status and latency_ms if healthy,
        or status and error if unhealthy
    """
    try:
        start = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000

        logger.debug("Database health check passed: %.2fms", latency_ms)
        return DependencyCheck.healthy(latency_ms)

    except Exception as e:
        error_msg = str(e)
        logger.warning("Database health check failed: %s", error_msg)
        return DependencyCheck.unhealthy(error_msg)


def check_database_connection() -> DependencyCheck:
    """Check if database connection can be established.

    More lightweight than check_database() - just verifies connection.

    Returns:
        DependencyCheck with status
    """
    try:
        start = time.perf_counter()
        connection.ensure_connection()
        latency_ms = (time.perf_counter() - start) * 1000

        return DependencyCheck.healthy(latency_ms)

    except Exception as e:
        return DependencyCheck.unhealthy(str(e))


def check_migrations() -> DependencyCheck:
    """Check if all database migrations have been applied.

    Used by startup probes to ensure the database schema is up to date
    before the application starts accepting traffic.

    Returns:
        DependencyCheck with status - healthy if no pending migrations
    """
    try:
        start = time.perf_counter()

        # Get the migration executor
        executor = MigrationExecutor(connection)

        # Get unapplied migrations
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        latency_ms = (time.perf_counter() - start) * 1000

        if plan:
            # There are pending migrations
            pending_count = len(plan)
            pending_names = [str(migration) for migration, _ in plan[:5]]  # First 5
            error_msg = f"{pending_count} pending migrations: {', '.join(pending_names)}"
            if pending_count > 5:
                error_msg += f" (and {pending_count - 5} more)"

            logger.warning("Migration check failed: %s", error_msg)
            return DependencyCheck.unhealthy(error_msg)

        logger.debug("Migration check passed: %.2fms", latency_ms)
        return DependencyCheck.healthy(latency_ms)

    except Exception as e:
        error_msg = f"Migration check error: {e}"
        logger.error(error_msg)
        return DependencyCheck.unhealthy(error_msg)


def check_cache() -> DependencyCheck:
    """Check cache backend connectivity.

    Attempts to set and get a test value from the cache.

    Returns:
        DependencyCheck with status and latency_ms if healthy
    """
    try:
        from django.core.cache import cache

        start = time.perf_counter()

        # Try to set and get a test value
        test_key = "_health_check_"
        test_value = "ok"
        cache.set(test_key, test_value, timeout=10)
        result = cache.get(test_key)
        cache.delete(test_key)

        latency_ms = (time.perf_counter() - start) * 1000

        if result == test_value:
            return DependencyCheck.healthy(latency_ms)
        else:
            return DependencyCheck.unhealthy("Cache read/write verification failed")

    except Exception as e:
        return DependencyCheck.unhealthy(str(e))


def get_pending_migration_count() -> int:
    """Return the number of unapplied migrations.

    Returns:
        Count of pending migrations, or -1 if unable to determine.
    """
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        return len(plan)
    except Exception:
        return -1
