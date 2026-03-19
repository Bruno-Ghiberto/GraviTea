"""Acopio-specific test fixtures."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.acopio.models import StorageUnit, GrainLot, GrainMovement


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


@pytest.fixture
def romaneo_factory(tenant_context, branch, admin_user, db):
    """Factory for creating Romaneo instances.

    Creates shared GrainType and CampanaConfig once per factory instance
    to avoid unique constraint violations across multiple calls.
    """
    from apps.acopio.models import CampanaConfig, GrainType, Romaneo

    grain = GrainType.objects.create(
        code="TRIT",
        arca_codigo=999,
        name="Trigo Test",
        humedad_base_pct="14.00",
        hf_secado_pct="13.50",
        manipuleo_fijo_pct="0.25",
        volatil_fijo_pct="0.30",
        grading_system="GRADO",
        is_active=True,
    )
    campaign = CampanaConfig.objects.create(
        tenant=tenant_context,
        campaign_code="2025/26",
        start_date=date(2025, 12, 1),
        end_date=date(2026, 11, 30),
        is_active=False,
    )
    _counter = [0]

    def create_romaneo(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "grain_type": grain,
            "campaign": campaign,
            "branch": branch,
            "patente_chasis": f"AB{_counter[0]:03d}CD",
            "driver_name": "Test Driver",
            "driver_dni": f"{20000000 + _counter[0]}",
            "cpe_numero": f"CPE-{uuid.uuid4().hex[:8].upper()}",
            "producer_cuit": "20123456789",
            "origin_locality": "Pergamino, Buenos Aires",
            "operator_id": admin_user,
        }
        defaults.update(kwargs)
        return Romaneo.objects.create(**defaults)

    return create_romaneo


@pytest.fixture
def romaneo_pendiente(romaneo_factory):
    """A romaneo in PENDIENTE status."""
    return romaneo_factory()


@pytest.fixture
def romaneo_en_proceso(romaneo_factory):
    """A romaneo in EN_PROCESO status."""
    from apps.acopio.models import Romaneo

    r = romaneo_factory()
    r.status = Romaneo.RomaneoStatus.EN_PROCESO
    r.save()
    return r


@pytest.fixture
def romaneo_pesado(romaneo_factory):
    """A romaneo in PESADO status with peso_bruto captured."""
    from apps.acopio.models import Romaneo

    r = romaneo_factory()
    r.status = Romaneo.RomaneoStatus.EN_PROCESO
    r.save()
    r.peso_bruto_kg = Decimal("30000.000")
    r.ts_pesada_bruta = timezone.now()
    r.status = Romaneo.RomaneoStatus.PESADO
    r.save()
    return r


@pytest.fixture
def quality_analysis_factory(tenant_context):
    """Factory for creating QualityAnalysis instances."""
    from apps.acopio.models import QualityAnalysis

    def create_qa(romaneo, **kwargs):
        defaults = {
            "romaneo": romaneo,
            "tenant_id": romaneo.tenant_id,
            "humedad_pct": Decimal("15.20"),
            "materias_extranas_pct": Decimal("1.80"),
            "granos_danados_pct": Decimal("2.00"),
            "granos_quebrados_pct": Decimal("3.00"),
            "granos_ardidos_pct": Decimal("0.50"),
            "cuerpos_extranos_pct": Decimal("0.10"),
            "analysis_timestamp": timezone.now(),
        }
        defaults.update(kwargs)
        return QualityAnalysis.objects.create(**defaults)

    return create_qa


@pytest.fixture
def romaneo_analizado(romaneo_pesado, quality_analysis_factory):
    """A romaneo in ANALIZADO status with QA attached."""
    from apps.acopio.models import Romaneo

    quality_analysis_factory(romaneo_pesado)
    romaneo_pesado.ts_analisis = timezone.now()
    romaneo_pesado.status = Romaneo.RomaneoStatus.ANALIZADO
    romaneo_pesado.save()
    return romaneo_pesado


@pytest.fixture
def merma_table_factory(db):
    """Factory for creating MermaTable instances."""
    from apps.acopio.models import MermaTable

    def create_merma_table(grain_type, **kwargs):
        defaults = {
            "grain_type": grain_type,
            "valid_from": date(2020, 1, 1),
            "valid_to": None,
            "materias_extranas_from_pct": Decimal("0.00"),
            "materias_extranas_to_pct": Decimal("5.00"),
            "zarandeo_deduction_pct": Decimal("1.00"),
        }
        defaults.update(kwargs)
        return MermaTable.objects.create(**defaults)

    return create_merma_table


@pytest.fixture
def tolerance_table_factory(db):
    """Factory for creating ToleranceTable instances."""
    from apps.acopio.models import ToleranceTable

    def create_tolerance(grain_type, **kwargs):
        defaults = {
            "grain_type": grain_type,
            "valid_from": date(2020, 1, 1),
            "valid_to": None,
            "parameter": "humedad",
            "tolerance_pct": Decimal("2.00"),
            "grado_base": 1,
        }
        defaults.update(kwargs)
        return ToleranceTable.objects.create(**defaults)

    return create_tolerance


@pytest.fixture
def storage_unit_factory(tenant_context, branch, admin_user, db):
    """Factory for creating StorageUnit instances."""
    _counter = [0]

    def create(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "name": f"Silo {_counter[0]}",
            "unit_type": StorageUnit.UnitType.SILO_VERTICAL,
            "capacity_tonnes": Decimal("500.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return StorageUnit.objects.create(**defaults)

    return create


@pytest.fixture
def grain_lot_factory(tenant_context, branch, admin_user, db):
    """Factory for creating GrainLot instances.

    Creates shared GrainType, CampanaConfig, and StorageUnit once per factory
    to avoid unique constraint violations across multiple calls.
    """
    from apps.acopio.models import CampanaConfig, GrainType

    grain = GrainType.objects.create(
        code="LOTG",
        arca_codigo=998,
        name="Lot Test Grain",
        humedad_base_pct="14.00",
        hf_secado_pct="13.50",
        manipuleo_fijo_pct="0.25",
        volatil_fijo_pct="0.30",
        grading_system="GRADO",
        is_active=True,
    )
    campaign = CampanaConfig.objects.create(
        tenant=tenant_context,
        campaign_code="2024/25",
        start_date=date(2024, 12, 1),
        end_date=date(2025, 11, 30),
        is_active=False,
    )
    storage = StorageUnit.objects.create(
        tenant=tenant_context,
        branch=branch,
        name="Silo Lot-Factory",
        unit_type=StorageUnit.UnitType.SILO_VERTICAL,
        capacity_tonnes=Decimal("1000.000"),
        created_by=admin_user,
    )
    _counter = [0]

    def create(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "grain_type": grain,
            "campaign": campaign,
            "grado": 1,
            "storage_unit": storage,
            "is_own_grain": False,
            "total_kg": Decimal("0.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return GrainLot.objects.create(**defaults)

    return create


@pytest.fixture
def grain_movement_factory(tenant_context, admin_user, db):
    """Factory for creating GrainMovement instances."""

    def create(grain_lot, **kwargs):
        defaults = {
            "tenant": tenant_context,
            "grain_lot": grain_lot,
            "movement_type": GrainMovement.MovementType.DEPOSIT,
            "quantity_kg": Decimal("10000.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return GrainMovement.objects.create(**defaults)

    return create


@pytest.fixture
def romaneo_conforme(romaneo_factory, storage_unit_factory):
    """A romaneo advanced to CONFORME status with a storage unit assigned.

    Steps through the full lifecycle: PENDIENTE → EN_PROCESO → PESADO → ANALIZADO → CONFORME.
    """
    from apps.acopio.models import QualityAnalysis, Romaneo

    storage = storage_unit_factory()
    r = romaneo_factory()

    # PENDIENTE → EN_PROCESO
    r.status = Romaneo.RomaneoStatus.EN_PROCESO
    r.save()

    # EN_PROCESO → PESADO
    r.peso_bruto_kg = Decimal("30000.000")
    r.ts_pesada_bruta = timezone.now()
    r.status = Romaneo.RomaneoStatus.PESADO
    r.save()

    # PESADO → ANALIZADO (needs QualityAnalysis)
    QualityAnalysis.objects.create(
        romaneo=r,
        tenant_id=r.tenant_id,
        humedad_pct=Decimal("15.20"),
        materias_extranas_pct=Decimal("1.80"),
        granos_danados_pct=Decimal("2.00"),
        granos_quebrados_pct=Decimal("3.00"),
        granos_ardidos_pct=Decimal("0.50"),
        cuerpos_extranos_pct=Decimal("0.10"),
        analysis_timestamp=timezone.now(),
    )
    r.ts_analisis = timezone.now()
    r.status = Romaneo.RomaneoStatus.ANALIZADO
    r.save()

    # ANALIZADO → CONFORME
    r.grado_asignado = 2
    r.bonificacion_rebaja_pct = Decimal("0.00")
    r.peso_neto_conforme_kg = Decimal("28500.000")
    r.storage_unit = storage
    r.status = Romaneo.RomaneoStatus.CONFORME
    r.save()

    return r
