"""
Tests for the seed_reportes management command.

Verifies idempotent execution and expected entity counts.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.reportes.models import ReportDefinition


pytestmark = [pytest.mark.django_db(transaction=True)]


@pytest.fixture
def seeded_core(tenant_context, branch):
    """Ensure core seed data exists (tenant, branch, roles, users)."""
    call_command("seed_data", verbosity=0)
    return tenant_context


class TestSeedReportes:
    """Verify seed_reportes produces expected entities idempotently."""

    def test_seed_creates_report_definitions(self, seeded_core):
        call_command("seed_reportes", verbosity=0)
        assert ReportDefinition.objects.count() >= 6

    def test_seed_idempotent(self, seeded_core):
        """Running twice produces same counts."""
        call_command("seed_reportes", verbosity=0)
        count1 = ReportDefinition.objects.count()

        call_command("seed_reportes", verbosity=0)
        assert ReportDefinition.objects.count() == count1
