"""Model unit tests for acopio reference data (GrainType, CampanaConfig, ToleranceTable, MermaTable)."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


@pytest.mark.django_db
class TestGrainType:
    """GrainType model unit tests (AC-10-001, AC-10-012)."""

    def test_grain_type_creation(self, grain_type_factory) -> None:
        gt = grain_type_factory()
        assert gt.code == "TRI"
        assert gt.arca_codigo == 15
        assert gt.name == "Trigo pan"

    def test_grain_type_unique_code(self, grain_type_factory) -> None:
        grain_type_factory(code="TRI", arca_codigo=15)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                grain_type_factory(code="TRI", arca_codigo=99)

    def test_grain_type_unique_arca_codigo(self, grain_type_factory) -> None:
        grain_type_factory(code="TRI", arca_codigo=15)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                grain_type_factory(code="XXX", arca_codigo=15)

    def test_hf_not_equal_humedad_base(self, seed_grain_types) -> None:
        """AC-10-011: Hf != humedad_base for applicable grains."""
        from apps.acopio.models import GrainType

        grains_where_differ = GrainType.objects.exclude(code="CEB_C")
        for gt in grains_where_differ:
            assert gt.hf_secado_pct != gt.humedad_base_pct, (
                f"{gt.code}: hf_secado_pct ({gt.hf_secado_pct}) must differ "
                f"from humedad_base_pct ({gt.humedad_base_pct})"
            )

    def test_grain_type_str_repr(self, grain_type_factory) -> None:
        gt = grain_type_factory()
        assert str(gt) == "TRI - Trigo pan"


@pytest.mark.django_db
class TestCampanaConfig:
    """CampanaConfig model unit tests (AC-10-003)."""

    def test_campana_creation(self, campana_factory) -> None:
        campana = campana_factory()
        assert campana.campaign_code == "2025/26"

    def test_campana_code_format_validation(self, campana_factory) -> None:
        campana = campana_factory()
        campana.campaign_code = "2025-26"  # Wrong format
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_consecutive_years_validation(self, campana_factory) -> None:
        campana = campana_factory()
        campana.campaign_code = "2025/27"  # Not consecutive
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_date_range_validation(self, campana_factory) -> None:
        campana = campana_factory(
            start_date=date(2026, 12, 1),
            end_date=date(2025, 11, 30),  # end before start
        )
        with pytest.raises(ValidationError):
            campana.full_clean()

    def test_campana_one_active_per_tenant(self, campana_factory) -> None:
        campana_factory(campaign_code="2024/25", is_active=True)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                campana_factory(campaign_code="2025/26", is_active=True)

    def test_wslpg_code_conversion(self, campana_factory) -> None:
        campana = campana_factory(campaign_code="2025/26")
        assert campana.wslpg_code == "2526"

    def test_campana_tenant_isolation(self, campana_factory, other_tenant) -> None:
        """AC-10-008: Campaigns are tenant-scoped."""
        from apps.acopio.models import CampanaConfig
        from apps.core.managers.tenant_bound import set_current_tenant_id

        campana_factory()  # Created for primary tenant
        set_current_tenant_id(other_tenant.id)
        assert CampanaConfig.objects.count() == 0  # Other tenant sees nothing


@pytest.mark.django_db
class TestToleranceTable:
    """ToleranceTable model unit tests (AC-10-004)."""

    def test_tolerance_versioning(self, seed_grain_types) -> None:
        from apps.acopio.models import GrainType, ToleranceTable

        trigo = GrainType.objects.get(code="TRI")
        active = ToleranceTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        )
        assert active.count() > 0


@pytest.mark.django_db
class TestMermaTable:
    """MermaTable model unit tests (AC-10-005)."""

    def test_merma_bands_ordering(self, seed_grain_types) -> None:
        from apps.acopio.models import GrainType, MermaTable

        trigo = GrainType.objects.get(code="TRI")
        bands = MermaTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        ).order_by("materias_extranas_from_pct")
        assert bands.count() > 0
