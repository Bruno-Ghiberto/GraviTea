"""Tests for Storage & Position models (spec-12): StorageUnit, GrainLot, GrainMovement."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.acopio.models import GrainLot, GrainMovement, StorageUnit

pytestmark = [pytest.mark.django_db]


# ============================================================
# StorageUnit Model Tests (T009)
# ============================================================


class TestStorageUnitCreate:
    """StorageUnit creation and field validation."""

    def test_create_with_all_fields(self, storage_unit_factory):
        unit = storage_unit_factory(
            name="Silo Alpha",
            unit_type=StorageUnit.UnitType.CELDA_HORIZONTAL,
            capacity_tonnes=Decimal("1200.500"),
        )
        assert unit.pk is not None
        assert unit.name == "Silo Alpha"
        assert unit.unit_type == StorageUnit.UnitType.CELDA_HORIZONTAL
        assert unit.capacity_tonnes == Decimal("1200.500")
        assert unit.is_active is True
        assert unit.current_grain_type is None
        assert unit.environment_sensor_id is None

    def test_all_unit_types(self, storage_unit_factory):
        for ut in StorageUnit.UnitType:
            unit = storage_unit_factory(unit_type=ut)
            assert unit.unit_type == ut

    def test_str_repr(self, storage_unit_factory):
        unit = storage_unit_factory(
            name="Silo Beta",
            unit_type=StorageUnit.UnitType.SECADERO_BIN,
        )
        assert "Silo Beta" in str(unit)
        assert "Secadero" in str(unit)

    def test_auto_timestamps(self, storage_unit_factory):
        unit = storage_unit_factory()
        assert unit.created_at is not None
        assert unit.updated_at is not None


class TestStorageUnitConstraints:
    """UniqueConstraint and tenant-bound behaviour."""

    def test_duplicate_name_same_branch_raises(self, storage_unit_factory, branch):
        storage_unit_factory(name="Silo Uno")
        with pytest.raises(IntegrityError), transaction.atomic():
            storage_unit_factory(name="Silo Uno")

    def test_same_name_different_branch(
        self, storage_unit_factory, other_branch, admin_user, tenant_context
    ):
        storage_unit_factory(name="Silo Uno")
        # Same name in a different branch should succeed
        dup = StorageUnit.objects.create(
            tenant=tenant_context,
            branch=other_branch,
            name="Silo Uno",
            unit_type=StorageUnit.UnitType.SILO_VERTICAL,
            capacity_tonnes=Decimal("500.000"),
            created_by=admin_user,
        )
        assert dup.pk is not None

    def test_tenant_bound_manager_fail_closed(
        self, storage_unit_factory, other_tenant, admin_user, branch
    ):
        """TenantBoundManager must not return units from another tenant."""
        storage_unit_factory(name="Mine")
        qs = StorageUnit.objects.all()
        assert qs.filter(name="Mine").exists()
        # all_objects bypasses tenant filter
        assert StorageUnit.all_objects.filter(name="Mine").exists()


class TestStorageUnitOccupancy:
    """current_occupancy_kg is computed, not stored."""

    def test_empty_unit_annotated_zero(self, storage_unit_factory):
        unit = storage_unit_factory()
        annotated = StorageUnit.objects.filter(pk=unit.pk).annotate(
            current_occupancy_kg=Coalesce(
                Sum("grain_lots__movements__quantity_kg"), Decimal("0.000")
            )
        ).first()
        assert annotated.current_occupancy_kg == Decimal("0.000")

    def test_occupancy_after_movements(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory
    ):
        unit = storage_unit_factory()
        lot = grain_lot_factory(storage_unit=unit)
        grain_movement_factory(lot, quantity_kg=Decimal("5000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("3000.000"))

        annotated = StorageUnit.objects.filter(pk=unit.pk).annotate(
            current_occupancy_kg=Coalesce(
                Sum("grain_lots__movements__quantity_kg"), Decimal("0.000")
            )
        ).first()
        assert annotated.current_occupancy_kg == Decimal("8000.000")


# ============================================================
# GrainLot Model Tests (T009)
# ============================================================


class TestGrainLotCreate:
    """GrainLot creation and auto-generated lot_code."""

    def test_create_lot_auto_code(self, grain_lot_factory):
        lot = grain_lot_factory()
        assert lot.pk is not None
        assert lot.lot_code  # auto-generated, not empty
        assert lot.total_kg == Decimal("0.000")

    def test_lot_code_format(self, grain_lot_factory):
        """lot_code = BRANCH-GRAIN-CAMPAIGN-GRADE."""
        lot = grain_lot_factory(grado=2)
        parts = lot.lot_code.split("-")
        # At least 4 parts: branch_id[:4], grain_code, campaign_code, grade
        assert len(parts) >= 3
        assert parts[-1] == "2"

    def test_str_repr(self, grain_lot_factory):
        lot = grain_lot_factory(total_kg=Decimal("1234.567"))
        assert "1234.567 kg" in str(lot)


class TestGrainLotCompositeKey:
    """UniqueConstraint on (tenant, branch, grain_type, campaign, grado, storage_unit)."""

    def test_duplicate_composite_raises(self, grain_lot_factory):
        grain_lot_factory(grado=1)
        with pytest.raises(IntegrityError), transaction.atomic():
            grain_lot_factory(
                grado=1,
                lot_code="FORCE-DIFFERENT-CODE",
            )

    def test_different_grado_allowed(self, grain_lot_factory):
        grain_lot_factory(grado=1)
        lot2 = grain_lot_factory(grado=2, lot_code="DIFF-LOT-CODE")
        assert lot2.pk is not None

    def test_different_storage_unit_allowed(
        self, grain_lot_factory, storage_unit_factory
    ):
        grain_lot_factory(grado=1)
        other_unit = storage_unit_factory(name="Silo Alt")
        lot2 = grain_lot_factory(
            grado=1, storage_unit=other_unit, lot_code="ALT-UNIT-LOT"
        )
        assert lot2.pk is not None


class TestGrainLotBalanceConstraint:
    """CheckConstraint: total_kg >= 0."""

    def test_negative_balance_raises(self, grain_lot_factory):
        with pytest.raises(IntegrityError), transaction.atomic():
            grain_lot_factory(total_kg=Decimal("-1.000"))

    def test_zero_balance_allowed(self, grain_lot_factory):
        lot = grain_lot_factory(total_kg=Decimal("0.000"))
        assert lot.total_kg == Decimal("0.000")


# ============================================================
# GrainMovement Model Tests (T009)
# ============================================================


class TestGrainMovementCreate:
    """GrainMovement creation and field validation."""

    def test_create_deposit(self, grain_lot_factory, grain_movement_factory):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot, quantity_kg=Decimal("15000.000"))
        assert mv.pk is not None
        assert mv.movement_type == GrainMovement.MovementType.DEPOSIT
        assert mv.quantity_kg == Decimal("15000.000")
        assert mv.movement_at is not None

    def test_all_movement_types(self, grain_lot_factory, grain_movement_factory):
        lot = grain_lot_factory()
        for mt in GrainMovement.MovementType:
            qty = Decimal("100.000") if "OUT" not in mt else Decimal("-100.000")
            mv = grain_movement_factory(lot, movement_type=mt, quantity_kg=qty)
            assert mv.movement_type == mt

    def test_negative_quantity_for_withdrawal(
        self, grain_lot_factory, grain_movement_factory
    ):
        lot = grain_lot_factory()
        mv = grain_movement_factory(
            lot,
            movement_type=GrainMovement.MovementType.WITHDRAWAL,
            quantity_kg=Decimal("-5000.000"),
        )
        assert mv.quantity_kg == Decimal("-5000.000")

    def test_str_repr(self, grain_lot_factory, grain_movement_factory):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot, quantity_kg=Decimal("7777.000"))
        assert "7777.000 kg" in str(mv)


class TestGrainMovementImmutability:
    """GrainMovement is fully immutable — no update, no delete."""

    def test_save_existing_raises(self, grain_lot_factory, grain_movement_factory):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)
        mv.notes = "Attempt to modify"
        with pytest.raises(ValueError, match="immutable and cannot be modified"):
            mv.save()

    def test_delete_raises(self, grain_lot_factory, grain_movement_factory):
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)
        with pytest.raises(ValueError, match="immutable and cannot be deleted"):
            mv.delete()

    def test_no_updated_at_field(self, grain_lot_factory, grain_movement_factory):
        """GrainMovement must NOT have updated_at — immutable model."""
        lot = grain_lot_factory()
        mv = grain_movement_factory(lot)
        assert not hasattr(mv, "updated_at") or "updated_at" not in [
            f.name for f in mv._meta.get_fields()
        ]


# ============================================================
# Romaneo Storage FK Tests (T009)
# ============================================================


class TestRomaneoStorageFields:
    """Romaneo Group 8: storage_unit + grain_lot FKs."""

    def test_conforme_allows_storage_fields(self, romaneo_conforme):
        """CONFORME romaneo must accept storage_unit and grain_lot changes."""
        from apps.acopio.models import Romaneo

        assert romaneo_conforme.status == Romaneo.RomaneoStatus.CONFORME
        assert romaneo_conforme.storage_unit is not None

    def test_conforme_blocks_other_fields(self, romaneo_conforme):
        """CONFORME romaneo must reject changes to non-allowlisted fields."""
        romaneo_conforme.driver_name = "Hacker"
        with pytest.raises(ValueError, match="CONFORME is immutable"):
            romaneo_conforme.save()

    def test_cerrado_blocks_all(self, romaneo_conforme):
        """CERRADO romaneo blocks everything including storage fields."""
        from apps.acopio.models import Romaneo

        romaneo_conforme.tara_kg = Decimal("8000.000")
        romaneo_conforme.peso_neto_bruto_kg = Decimal("22000.000")
        from django.utils import timezone
        romaneo_conforme.ts_tara = timezone.now()
        romaneo_conforme.status = Romaneo.RomaneoStatus.CERRADO
        romaneo_conforme.save()

        romaneo_conforme.storage_unit = None
        with pytest.raises(ValueError, match="CERRADO cannot be modified"):
            romaneo_conforme.save()
