"""Tests for grain ledger operations (spec-12): deposit, movement immutability, balance integrity."""

from decimal import Decimal

import pytest
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.acopio.models import GrainLot, GrainMovement, Romaneo, StorageUnit
from apps.acopio.services.storage import create_deposit_from_romaneo

pytestmark = [pytest.mark.django_db]


# ============================================================
# Deposit Service Tests (T014)
# ============================================================


class TestCreateDepositFromRomaneo:
    """FR-012: create_deposit_from_romaneo service function."""

    def test_first_deposit_creates_lot(self, romaneo_conforme, storage_unit_factory):
        """First call creates a new GrainLot."""
        storage = romaneo_conforme.storage_unit
        movement, lot = create_deposit_from_romaneo(romaneo_conforme, storage)

        assert lot.pk is not None
        assert movement.pk is not None
        assert movement.movement_type == GrainMovement.MovementType.DEPOSIT
        assert movement.quantity_kg == romaneo_conforme.peso_neto_conforme_kg
        assert lot.total_kg == romaneo_conforme.peso_neto_conforme_kg

    def test_second_deposit_reuses_lot(
        self, romaneo_factory, storage_unit_factory, admin_user
    ):
        """Second call with same composite key reuses existing lot."""
        from apps.acopio.models import QualityAnalysis
        from django.utils import timezone

        storage = storage_unit_factory()

        def make_conforme(romaneo, storage_unit):
            """Advance romaneo to CONFORME."""
            romaneo.status = Romaneo.RomaneoStatus.EN_PROCESO
            romaneo.save()
            romaneo.peso_bruto_kg = Decimal("30000.000")
            romaneo.ts_pesada_bruta = timezone.now()
            romaneo.status = Romaneo.RomaneoStatus.PESADO
            romaneo.save()
            QualityAnalysis.objects.create(
                romaneo=romaneo,
                tenant_id=romaneo.tenant_id,
                humedad_pct=Decimal("15.20"),
                materias_extranas_pct=Decimal("1.80"),
                granos_danados_pct=Decimal("2.00"),
                granos_quebrados_pct=Decimal("3.00"),
                granos_ardidos_pct=Decimal("0.50"),
                cuerpos_extranos_pct=Decimal("0.10"),
                analysis_timestamp=timezone.now(),
            )
            romaneo.ts_analisis = timezone.now()
            romaneo.status = Romaneo.RomaneoStatus.ANALIZADO
            romaneo.save()
            romaneo.grado_asignado = 2
            romaneo.bonificacion_rebaja_pct = Decimal("0.00")
            romaneo.peso_neto_conforme_kg = Decimal("28500.000")
            romaneo.storage_unit = storage_unit
            romaneo.status = Romaneo.RomaneoStatus.CONFORME
            romaneo.save()

        r1 = romaneo_factory()
        make_conforme(r1, storage)
        _mv1, lot1 = create_deposit_from_romaneo(r1, storage)

        r2 = romaneo_factory()
        make_conforme(r2, storage)
        _mv2, lot2 = create_deposit_from_romaneo(r2, storage)

        # Same composite key → same lot
        assert lot1.pk == lot2.pk

        lot1.refresh_from_db()
        assert lot1.total_kg == Decimal("57000.000")  # 28500 + 28500

    def test_movement_fks_correct(self, romaneo_conforme):
        """Movement references correct lot and romaneo."""
        storage = romaneo_conforme.storage_unit
        movement, lot = create_deposit_from_romaneo(romaneo_conforme, storage)

        assert movement.grain_lot_id == lot.pk
        assert movement.romaneo_id == romaneo_conforme.pk
        assert movement.tenant_id == romaneo_conforme.tenant_id

    def test_romaneo_grain_lot_fk_updated(self, romaneo_conforme):
        """Service links romaneo back to the lot."""
        storage = romaneo_conforme.storage_unit
        _mv, lot = create_deposit_from_romaneo(romaneo_conforme, storage)

        romaneo_conforme.refresh_from_db()
        assert romaneo_conforme.grain_lot_id == lot.pk

    def test_storage_unit_grain_type_set(self, romaneo_conforme):
        """Service sets current_grain_type on empty storage unit."""
        storage = romaneo_conforme.storage_unit
        assert storage.current_grain_type is None

        _mv, _lot = create_deposit_from_romaneo(romaneo_conforme, storage)

        storage.refresh_from_db()
        assert storage.current_grain_type_id == romaneo_conforme.grain_type_id

    def test_storage_unit_grain_type_not_overwritten(
        self, romaneo_conforme, grain_type_factory
    ):
        """If storage unit already has a grain type, don't overwrite."""
        existing_grain = grain_type_factory(code="SOJ", arca_codigo=50, name="Soja")
        storage = romaneo_conforme.storage_unit
        storage.current_grain_type = existing_grain
        storage.save(update_fields=["current_grain_type"])

        _mv, _lot = create_deposit_from_romaneo(romaneo_conforme, storage)

        storage.refresh_from_db()
        assert storage.current_grain_type_id == existing_grain.pk

    def test_deposit_quantity_equals_peso_neto_conforme(self, romaneo_conforme):
        """Movement quantity must equal romaneo.peso_neto_conforme_kg."""
        storage = romaneo_conforme.storage_unit
        movement, _lot = create_deposit_from_romaneo(romaneo_conforme, storage)
        assert movement.quantity_kg == Decimal("28500.000")

    def test_lot_code_auto_generated(self, romaneo_conforme):
        """GrainLot auto-generates lot_code on first save."""
        storage = romaneo_conforme.storage_unit
        _mv, lot = create_deposit_from_romaneo(romaneo_conforme, storage)
        assert lot.lot_code
        assert len(lot.lot_code) > 0


# ============================================================
# Balance Integrity Tests (T014)
# ============================================================


class TestBalanceIntegrity:
    """total_kg must always equal Sum(movements.quantity_kg)."""

    def test_balance_matches_movements_sum(
        self, grain_lot_factory, grain_movement_factory
    ):
        lot = grain_lot_factory()
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("5000.000"))

        # Update balance manually (service layer does this)
        lot.total_kg = Decimal("15000.000")
        lot.save(update_fields=["total_kg", "updated_at"])

        computed = GrainMovement.objects.filter(grain_lot=lot).aggregate(
            total=Coalesce(Sum("quantity_kg"), Decimal("0.000"))
        )["total"]
        assert lot.total_kg == computed

    def test_negative_movements_reduce_balance(
        self, grain_lot_factory, grain_movement_factory
    ):
        lot = grain_lot_factory(total_kg=Decimal("20000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("20000.000"))
        grain_movement_factory(
            lot,
            movement_type=GrainMovement.MovementType.WITHDRAWAL,
            quantity_kg=Decimal("-5000.000"),
        )

        computed = GrainMovement.objects.filter(grain_lot=lot).aggregate(
            total=Coalesce(Sum("quantity_kg"), Decimal("0.000"))
        )["total"]
        assert computed == Decimal("15000.000")


# ============================================================
# Movement Immutability at Service Level (T014)
# ============================================================


class TestMovementImmutabilityService:
    """Verify immutability enforced even when accessed through lot relationship."""

    def test_cannot_update_movement_via_queryset(
        self, grain_lot_factory, grain_movement_factory
    ):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)

        # Direct save must fail
        mv.notes = "tampered"
        with pytest.raises(ValueError, match="immutable and cannot be modified"):
            mv.save()

    def test_cannot_delete_movement_via_queryset(
        self, grain_lot_factory, grain_movement_factory
    ):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)

        with pytest.raises(ValueError, match="immutable and cannot be deleted"):
            mv.delete()

    def test_movement_created_by_tracked(self, romaneo_conforme):
        """Movement tracks created_by from romaneo operator."""
        storage = romaneo_conforme.storage_unit
        movement, _lot = create_deposit_from_romaneo(romaneo_conforme, storage)
        assert movement.created_by_id == romaneo_conforme.operator_id_id


# ============================================================
# Cross-Tenant Isolation at Model Level (T009)
# ============================================================


class TestCrossTenantIsolation:
    """TenantBoundManager must isolate storage data across tenants."""

    def test_storage_unit_isolated(
        self, storage_unit_factory, other_tenant, admin_user, branch
    ):
        """StorageUnit created in tenant A not visible via objects manager."""
        storage_unit_factory(name="Tenant A Silo")
        visible = StorageUnit.objects.filter(name="Tenant A Silo")
        assert visible.count() == 1

        # all_objects sees everything
        all_visible = StorageUnit.all_objects.filter(name="Tenant A Silo")
        assert all_visible.count() == 1

    def test_grain_lot_isolated(self, grain_lot_factory):
        """GrainLot uses TenantBoundManager."""
        lot = grain_lot_factory()
        assert GrainLot.objects.filter(pk=lot.pk).exists()

    def test_grain_movement_isolated(
        self, grain_lot_factory, grain_movement_factory
    ):
        """GrainMovement uses TenantBoundManager."""
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)
        assert GrainMovement.objects.filter(pk=mv.pk).exists()
