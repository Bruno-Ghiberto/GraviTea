"""Cuentas-specific test fixtures."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.cuentas.models import AccountMovement, ProducerAccount
from apps.core.encryption.utils import compute_blind_index


@pytest.fixture
def cuentas_grain_type(db):
    """GrainType for cuentas tests (self-contained, no acopio conftest dependency)."""
    from apps.acopio.models import GrainType

    return GrainType.objects.create(
        code="CCPA",
        arca_codigo=997,
        name="Cuentas Test Grain",
        humedad_base_pct="14.00",
        hf_secado_pct="13.50",
        manipuleo_fijo_pct="0.25",
        volatil_fijo_pct="0.30",
        grading_system="GRADO",
        is_active=True,
    )


@pytest.fixture
def cuentas_campaign(tenant_context):
    """CampanaConfig for cuentas tests."""
    from apps.acopio.models import CampanaConfig

    return CampanaConfig.objects.create(
        tenant=tenant_context,
        campaign_code="2025/26-CC",
        start_date=date(2025, 12, 1),
        end_date=date(2026, 11, 30),
        is_active=False,
    )


@pytest.fixture
def cuentas_storage_unit(tenant_context, branch, admin_user, db):
    """StorageUnit for cuentas tests."""
    from apps.acopio.models import StorageUnit

    _counter = [0]

    def create(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "name": f"Silo CC-{_counter[0]}",
            "unit_type": StorageUnit.UnitType.SILO_VERTICAL,
            "capacity_tonnes": Decimal("500.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return StorageUnit.objects.create(**defaults)

    return create


@pytest.fixture
def producer_account_factory(tenant_context, branch, cuentas_grain_type, cuentas_campaign, admin_user, encryption_settings, db):
    """Factory for creating ProducerAccount instances."""
    grain = cuentas_grain_type
    campaign = cuentas_campaign
    _counter = [0]

    def make(cuit="20-12345678-9", **kwargs):
        _counter[0] += 1
        cuit_hash = compute_blind_index(cuit)
        defaults = {
            "tenant": tenant_context,
            "branch": branch,
            "grain_type": grain,
            "campaign": campaign,
            "producer_cuit_encrypted": cuit,
            "producer_cuit_hash": cuit_hash,
            "grain_balance_kg": Decimal("0.000"),
            "ars_balance": Decimal("0.000"),
            "usd_balance": Decimal("0.000"),
            "is_active": True,
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return ProducerAccount.objects.create(**defaults)

    return make


@pytest.fixture
def account_movement_factory(producer_account_factory, admin_user, tenant_context, db):
    """Factory for creating AccountMovement instances."""

    def make(movement_type=AccountMovement.MovementType.CEG_DEPOSIT, account=None, **kwargs):
        if account is None:
            account = producer_account_factory()
        defaults = {
            "tenant": tenant_context,
            "producer_account": account,
            "movement_type": movement_type,
            "quantity_kg": Decimal("0.000"),
            "ars_amount": Decimal("0.000"),
            "usd_amount": Decimal("0.000"),
            "created_by": admin_user,
        }
        defaults.update(kwargs)
        return AccountMovement.objects.create(**defaults)

    return make


@pytest.fixture
def romaneo_conforme_factory(
    tenant_context, branch, cuentas_grain_type, cuentas_campaign,
    cuentas_storage_unit, admin_user, encryption_settings, db,
):
    """Factory for creating a romaneo at ANALIZADO status with all prerequisites.

    The romaneo is left at ANALIZADO (not CONFORME) so tests can call the
    confirmar API endpoint to trigger the full flow including CEG_DEPOSIT.
    Storage unit is assigned and peso_neto_conforme_kg is populated.

    Self-contained — does not depend on acopio conftest fixtures.
    """
    import uuid
    from apps.acopio.models import (
        CampanaConfig, GrainType, MermaTable, QualityAnalysis,
        Romaneo, ToleranceTable,
    )

    _counter = [0]

    def make(**kwargs):
        _counter[0] += 1
        storage = cuentas_storage_unit()

        # Create romaneo
        defaults = {
            "tenant": tenant_context,
            "grain_type": cuentas_grain_type,
            "campaign": cuentas_campaign,
            "branch": branch,
            "patente_chasis": f"CC{_counter[0]:03d}ZZ",
            "driver_name": "Test Driver CC",
            "driver_dni": f"{30000000 + _counter[0]}",
            "cpe_numero": f"CPE-{uuid.uuid4().hex[:8].upper()}",
            "producer_cuit": "20-12345678-9",
            "origin_locality": "Pergamino, Buenos Aires",
            "operator_id": admin_user,
        }
        defaults.update(kwargs)
        r = Romaneo.objects.create(**defaults)

        # Set up merma and tolerance tables for the grain type
        MermaTable.objects.get_or_create(
            grain_type=r.grain_type,
            valid_from=date(2020, 1, 1),
            materias_extranas_from_pct=Decimal("0.00"),
            materias_extranas_to_pct=Decimal("5.00"),
            defaults={
                "valid_to": None,
                "zarandeo_deduction_pct": Decimal("1.00"),
            },
        )
        ToleranceTable.objects.get_or_create(
            grain_type=r.grain_type,
            valid_from=date(2020, 1, 1),
            parameter="humedad",
            defaults={
                "valid_to": None,
                "tolerance_pct": Decimal("2.00"),
                "grado_base": 1,
            },
        )

        # PENDIENTE -> EN_PROCESO
        r.status = Romaneo.RomaneoStatus.EN_PROCESO
        r.save()

        # EN_PROCESO -> PESADO
        r.peso_bruto_kg = Decimal("30000.000")
        r.ts_pesada_bruta = timezone.now()
        r.status = Romaneo.RomaneoStatus.PESADO
        r.save()

        # PESADO -> ANALIZADO (needs QualityAnalysis)
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
        # Assign storage_unit BEFORE saving so it persists in DB
        r.storage_unit = storage
        # Set peso_neto_conforme_kg so tests calling create_ceg_deposit()
        # directly (bypassing the confirmar endpoint) have a valid weight.
        r.peso_neto_conforme_kg = Decimal("28500.000")
        r.save()

        return r

    return make
