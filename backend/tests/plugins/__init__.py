"""
Pytest Plugins for Gravitea ERP
================================

Custom pytest plugins for enhanced testing capabilities.

Plugins:
- json_logging: Structured JSON logging for CI/CD integration
"""

from tests.plugins.json_logging import JSONLoggingPlugin, pytest_addoption, pytest_configure

__all__ = [
    "JSONLoggingPlugin",
    "pytest_addoption",
    "pytest_configure",
]
