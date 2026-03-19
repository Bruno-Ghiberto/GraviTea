"""Acopio-specific test fixtures."""

from datetime import date

import pytest


@pytest.fixture
def grain_type_factory(db):
    """Factory for creating GrainType instances."""
    from apps.acopio.models import GrainType

    def create_grain_type(**kwargs):
        defaults = {
            "code": "TRI",
            "arca_codigo": 15,
            "name": "Trigo pan",
            "humedad_base_pct": "14.00",
            "hf_secado_pct": "13.50",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
            "grading_system": "GRADO",
            "is_active": True,
        }
        defaults.update(kwargs)
        return GrainType.objects.create(**defaults)

    return create_grain_type


@pytest.fixture
def seed_grain_types(db):
    """Load all 7 primary grain types via the management command."""
    from django.core.management import call_command

    call_command("seed_grain_reference")


@pytest.fixture
def campana_factory(tenant_context):
    """Factory for creating CampanaConfig instances."""
    from apps.acopio.models import CampanaConfig

    def create_campana(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "campaign_code": "2025/26",
            "start_date": date(2025, 12, 1),
            "end_date": date(2026, 11, 30),
            "is_active": False,
        }
        defaults.update(kwargs)
        return CampanaConfig.objects.create(**defaults)

    return create_campana
