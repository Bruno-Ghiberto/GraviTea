"""Tests for storage service layer (spec-12): suggestion, withdrawal, transfer, report, reconcile, campaign close.

These tests define the contract for services that will be implemented by A1.
Tests that import not-yet-implemented services use pytest.importorskip.
"""

from decimal import Decimal

import pytest
from django.db import transaction

from apps.acopio.models import GrainLot, GrainMovement, StorageUnit

pytestmark = [pytest.mark.django_db]


# ============================================================
# Cell Suggestion Service Tests (T022)
# ============================================================


class TestCellSuggestionService:
    """FR-014: suggest_cell ranks compatible storage units by score."""

    def _get_suggest_cell(self):
        from apps.acopio.services.storage import suggest_cell
        return suggest_cell

    def test_grain_type_match_scores_40(
        self, storage_unit_factory, grain_type_factory, grain_lot_factory,
        tenant_context, campana_factory,
    ):
        """Unit with matching grain type scores at least 40 points."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="SOJ", arca_codigo=50, name="Soja")
        campaign = campana_factory()
        unit = storage_unit_factory(current_grain_type=grain)

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=1,
            incoming_kg=Decimal("10000.000"),
        )

        assert len(suggestions) >= 1
        top = suggestions[0]
        assert top.score >= 40

    def test_grade_match_adds_20(
        self, storage_unit_factory, grain_type_factory, grain_lot_factory,
        campana_factory, tenant_context,
    ):
        """Unit with matching grain type AND grade scores 60+."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="TRG", arca_codigo=51, name="Trigo Suggest")
        campaign = campana_factory(campaign_code="25/26A")
        unit = storage_unit_factory(current_grain_type=grain)
        grain_lot_factory(
            storage_unit=unit, grain_type=grain, campaign=campaign,
            grado=2, total_kg=Decimal("1000.000"),
        )

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=2,
            incoming_kg=Decimal("10000.000"),
        )

        matching = [s for s in suggestions if str(s.storage_unit_id) == str(unit.pk)]
        assert len(matching) == 1
        assert matching[0].score >= 60

    def test_campaign_match_adds_10(
        self, storage_unit_factory, grain_type_factory, grain_lot_factory,
        campana_factory, tenant_context,
    ):
        """Unit with matching grain + grade + campaign scores 70."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="TRC", arca_codigo=52, name="Trigo Camp")
        campaign = campana_factory(campaign_code="25/26B")
        unit = storage_unit_factory(current_grain_type=grain)
        grain_lot_factory(
            storage_unit=unit, grain_type=grain, campaign=campaign,
            grado=2, total_kg=Decimal("1000.000"),
        )

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=2,
            incoming_kg=Decimal("10000.000"),
        )

        matching = [s for s in suggestions if str(s.storage_unit_id) == str(unit.pk)]
        assert len(matching) == 1
        assert matching[0].score >= 70

    def test_incompatible_grain_type_excluded(
        self, storage_unit_factory, grain_type_factory, tenant_context,
        campana_factory,
    ):
        """Unit with different grain type is excluded."""
        suggest_cell = self._get_suggest_cell()
        soja = grain_type_factory(code="SOE", arca_codigo=53, name="Soja Excl")
        trigo = grain_type_factory(code="TRE", arca_codigo=54, name="Trigo Excl")
        campaign = campana_factory()
        unit = storage_unit_factory(current_grain_type=soja)

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=trigo.pk,
            campaign_id=campaign.pk,
            grado=1,
            incoming_kg=Decimal("10000.000"),
        )

        unit_ids = [str(s.storage_unit_id) for s in suggestions]
        assert str(unit.pk) not in unit_ids

    def test_insufficient_capacity_excluded(
        self, storage_unit_factory, grain_type_factory, grain_lot_factory,
        grain_movement_factory, tenant_context, campana_factory,
    ):
        """Unit without enough remaining capacity is excluded."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="TRF", arca_codigo=55, name="Trigo Full")
        campaign = campana_factory()
        unit = storage_unit_factory(
            current_grain_type=grain, capacity_tonnes=Decimal("10.000")
        )
        # Fill to near capacity (9500 kg in a 10t unit)
        lot = grain_lot_factory(
            storage_unit=unit, grain_type=grain, grado=1,
            total_kg=Decimal("9500.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("9500.000"))

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=1,
            incoming_kg=Decimal("1000.000"),  # Only 500kg available
        )

        unit_ids = [str(s.storage_unit_id) for s in suggestions]
        assert str(unit.pk) not in unit_ids

    def test_empty_unit_scores_40(
        self, storage_unit_factory, grain_type_factory, tenant_context,
        campana_factory,
    ):
        """Empty unit (no grain type) is compatible and scores 40."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="TRM", arca_codigo=56, name="Trigo Empty")
        campaign = campana_factory()
        unit = storage_unit_factory(current_grain_type=None)

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=1,
            incoming_kg=Decimal("10000.000"),
        )

        matching = [s for s in suggestions if str(s.storage_unit_id) == str(unit.pk)]
        assert len(matching) == 1
        assert matching[0].score == 40

    def test_results_sorted_descending_by_score(
        self, storage_unit_factory, grain_type_factory, grain_lot_factory,
        campana_factory, tenant_context,
    ):
        """Results are sorted by score descending."""
        suggest_cell = self._get_suggest_cell()
        grain = grain_type_factory(code="TRS", arca_codigo=57, name="Trigo Sort")
        campaign = campana_factory(campaign_code="25/26C")

        # Unit A: empty (score=40)
        unit_a = storage_unit_factory(name="Sort Empty", current_grain_type=None)
        # Unit B: grain match + grade + campaign (score=70)
        unit_b = storage_unit_factory(name="Sort Full Match", current_grain_type=grain)
        grain_lot_factory(
            storage_unit=unit_b, grain_type=grain, campaign=campaign,
            grado=2, total_kg=Decimal("1000.000"),
        )

        suggestions = suggest_cell(
            tenant_id=tenant_context.pk,
            branch_id=unit_a.branch_id,
            grain_type_id=grain.pk,
            campaign_id=campaign.pk,
            grado=2,
            incoming_kg=Decimal("10000.000"),
        )

        scores = [s.score for s in suggestions]
        assert scores == sorted(scores, reverse=True)


# ============================================================
# Withdrawal Service Tests (T026)
# ============================================================


class TestCreateWithdrawal:
    """FR-009: create_withdrawal reduces stock atomically."""

    def _get_create_withdrawal(self):
        from apps.acopio.services.storage import create_withdrawal
        return create_withdrawal

    def test_successful_withdrawal_reduces_balance(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Withdrawal creates WITHDRAWAL movement and reduces total_kg."""
        create_withdrawal = self._get_create_withdrawal()
        lot = grain_lot_factory(total_kg=Decimal("20000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("20000.000"))

        movement = create_withdrawal(
            grain_lot=lot,
            quantity_kg=Decimal("5000.000"),
            operator=admin_user,
            reference_document="CPE-OUT-001",
        )

        assert movement.movement_type == GrainMovement.MovementType.WITHDRAWAL
        assert movement.quantity_kg == Decimal("-5000.000")
        lot.refresh_from_db()
        assert lot.total_kg == Decimal("15000.000")

    def test_insufficient_balance_raises(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Withdrawal exceeding balance raises ValueError."""
        create_withdrawal = self._get_create_withdrawal()
        lot = grain_lot_factory(total_kg=Decimal("5000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("5000.000"))

        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            create_withdrawal(
                grain_lot=lot,
                quantity_kg=Decimal("10000.000"),
                operator=admin_user,
            )

    def test_withdrawal_stored_as_negative(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """quantity_kg is stored as negative for WITHDRAWAL."""
        create_withdrawal = self._get_create_withdrawal()
        lot = grain_lot_factory(total_kg=Decimal("20000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("20000.000"))

        movement = create_withdrawal(
            grain_lot=lot,
            quantity_kg=Decimal("8000.000"),
            operator=admin_user,
        )

        assert movement.quantity_kg < 0
        assert movement.quantity_kg == Decimal("-8000.000")

    def test_exact_balance_withdrawal_allowed(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Withdrawing exactly the full balance should succeed."""
        create_withdrawal = self._get_create_withdrawal()
        lot = grain_lot_factory(total_kg=Decimal("10000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        movement = create_withdrawal(
            grain_lot=lot,
            quantity_kg=Decimal("10000.000"),
            operator=admin_user,
        )

        lot.refresh_from_db()
        assert lot.total_kg == Decimal("0.000")


# ============================================================
# Transfer Service Tests (T030)
# ============================================================


class TestTransferGrain:
    """FR-010: transfer_grain creates paired movements atomically."""

    def _get_transfer_grain(self):
        from apps.acopio.services.storage import transfer_grain
        return transfer_grain

    def test_transfer_reduces_source_increases_dest(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Transfer moves grain between lots."""
        transfer_grain = self._get_transfer_grain()
        source = grain_lot_factory(grado=1, total_kg=Decimal("20000.000"))
        grain_movement_factory(source, quantity_kg=Decimal("20000.000"))

        dest_unit = source.storage_unit  # reuse for simplicity
        dest = grain_lot_factory(
            grado=2, total_kg=Decimal("5000.000"),
            lot_code="DEST-LOT",
        )
        grain_movement_factory(dest, quantity_kg=Decimal("5000.000"))

        mv_out, returned_dest = transfer_grain(
            source_lot=source,
            destination_lot=dest,
            quantity_kg=Decimal("10000.000"),
            operator=admin_user,
            notes="Consolidation",
        )

        assert mv_out.movement_type == GrainMovement.MovementType.TRANSFER_OUT
        assert mv_out.quantity_kg == Decimal("-10000.000")
        # Verify TRANSFER_IN was also created
        mv_in = GrainMovement.objects.filter(
            grain_lot=dest, movement_type=GrainMovement.MovementType.TRANSFER_IN,
        ).first()
        assert mv_in is not None
        assert mv_in.quantity_kg == Decimal("10000.000")

        source.refresh_from_db()
        dest.refresh_from_db()
        assert source.total_kg == Decimal("10000.000")
        assert dest.total_kg == Decimal("15000.000")

    def test_insufficient_source_raises(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Transfer exceeding source balance raises ValueError."""
        transfer_grain = self._get_transfer_grain()
        source = grain_lot_factory(grado=1, total_kg=Decimal("5000.000"))
        grain_movement_factory(source, quantity_kg=Decimal("5000.000"))
        dest = grain_lot_factory(grado=2, total_kg=Decimal("0.000"), lot_code="DEST2")

        with pytest.raises(ValueError):
            transfer_grain(
                source_lot=source,
                destination_lot=dest,
                quantity_kg=Decimal("10000.000"),
                operator=admin_user,
            )

    def test_same_lot_raises(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Transfer to same lot raises ValueError."""
        transfer_grain = self._get_transfer_grain()
        lot = grain_lot_factory(total_kg=Decimal("10000.000"))
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        with pytest.raises(ValueError, match="different"):
            transfer_grain(
                source_lot=lot,
                destination_lot=lot,
                quantity_kg=Decimal("5000.000"),
                operator=admin_user,
            )

    def test_atomicity_on_failure(
        self, grain_lot_factory, grain_movement_factory, admin_user,
    ):
        """Failed transfer creates zero movements (atomic rollback)."""
        transfer_grain = self._get_transfer_grain()
        source = grain_lot_factory(grado=1, total_kg=Decimal("1000.000"))
        grain_movement_factory(source, quantity_kg=Decimal("1000.000"))
        dest = grain_lot_factory(grado=2, total_kg=Decimal("0.000"), lot_code="DESTF")

        initial_count = GrainMovement.objects.count()
        with pytest.raises(ValueError):
            transfer_grain(
                source_lot=source,
                destination_lot=dest,
                quantity_kg=Decimal("5000.000"),
                operator=admin_user,
            )

        assert GrainMovement.objects.count() == initial_count


# ============================================================
# Stock Report Service Tests (T034)
# ============================================================


class TestGenerateStockReport:
    """FR-015: generate_stock_report aggregates grain across storage units."""

    def _get_generate_stock_report(self):
        from apps.acopio.services.storage import generate_stock_report
        return generate_stock_report

    def test_aggregation_per_storage_unit(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, branch, tenant_context,
    ):
        """Report shows total kg per storage unit."""
        generate_stock_report = self._get_generate_stock_report()
        grain = grain_type_factory(code="RPA", arca_codigo=60, name="Report A")
        unit_a = storage_unit_factory(name="Report Silo A", current_grain_type=grain)
        unit_b = storage_unit_factory(name="Report Silo B", current_grain_type=grain)

        lot_a = grain_lot_factory(
            storage_unit=unit_a, grain_type=grain, grado=1,
            total_kg=Decimal("10000.000"),
        )
        grain_movement_factory(lot_a, quantity_kg=Decimal("10000.000"))
        lot_b = grain_lot_factory(
            storage_unit=unit_b, grain_type=grain, grado=1,
            total_kg=Decimal("5000.000"), lot_code="RPT-B",
        )
        grain_movement_factory(lot_b, quantity_kg=Decimal("5000.000"))

        report = generate_stock_report(tenant_id=tenant_context.pk, branch_id=branch.pk)

        by_unit = {str(r["storage_unit_id"]): r for r in report["by_storage_unit"]}
        assert Decimal(str(by_unit[str(unit_a.pk)]["total_kg"])) == Decimal("10000.000")
        assert Decimal(str(by_unit[str(unit_b.pk)]["total_kg"])) == Decimal("5000.000")

    def test_aggregation_per_grain_type(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, branch, tenant_context,
    ):
        """Report shows total kg grouped by grain type."""
        generate_stock_report = self._get_generate_stock_report()
        soja = grain_type_factory(code="RPB", arca_codigo=61, name="Soja RPT")
        unit = storage_unit_factory(name="RPT Grain Silo")

        lot = grain_lot_factory(
            storage_unit=unit, grain_type=soja, grado=1,
            total_kg=Decimal("15000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("15000.000"))

        report = generate_stock_report(tenant_id=tenant_context.pk, branch_id=branch.pk)

        by_grain = {r["grain_type_code"]: r for r in report["by_grain_type"]}
        assert "RPB" in by_grain
        assert Decimal(str(by_grain["RPB"]["total_kg"])) == Decimal("15000.000")

    def test_utilisation_pct_calculation(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, branch, tenant_context,
    ):
        """utilisation_pct = (total_occupied / total_capacity) * 100."""
        generate_stock_report = self._get_generate_stock_report()
        grain = grain_type_factory(code="RPC", arca_codigo=62, name="Util PCT")
        # 100t capacity, 50t occupied = 50%
        unit = storage_unit_factory(
            name="Util Silo", capacity_tonnes=Decimal("100.000"),
            current_grain_type=grain,
        )
        # Deactivate any other units to isolate this test
        StorageUnit.objects.exclude(pk=unit.pk).update(is_active=False)

        lot = grain_lot_factory(
            storage_unit=unit, grain_type=grain, grado=1,
            total_kg=Decimal("50000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("50000.000"))

        report = generate_stock_report(tenant_id=tenant_context.pk, branch_id=branch.pk)

        assert report["utilisation_pct"] == pytest.approx(50.0, abs=1.0)


# ============================================================
# Reconciliation Service Tests (T038)
# ============================================================


class TestReconcileService:
    """FR-008: reconcile creates ADJUSTMENT movements for variances."""

    def _get_reconcile(self):
        from apps.acopio.services.storage import reconcile
        return reconcile

    def test_deficit_produces_negative_adjustment(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, admin_user, tenant_context,
    ):
        """Measured < ledger → negative ADJUSTMENT."""
        reconcile = self._get_reconcile()
        grain = grain_type_factory(code="RCA", arca_codigo=70, name="Recon A")
        unit = storage_unit_factory(name="Recon Silo A", current_grain_type=grain)
        lot = grain_lot_factory(
            storage_unit=unit, grain_type=grain, grado=1,
            total_kg=Decimal("10000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        result = reconcile(
            tenant_id=tenant_context.pk,
            measurements=[
                {"storage_unit_id": unit.pk, "measured_kg": Decimal("9500.000")},
            ],
            notes="Monthly count",
            operator_id=admin_user.pk,
        )

        assert len(result["variances"]) == 1
        v = result["variances"][0]
        assert Decimal(str(v["variance_kg"])) == Decimal("-500.000")
        # Adjustment movement created
        adj = GrainMovement.all_objects.get(pk=v["adjustment_movement_id"])
        assert adj.movement_type == GrainMovement.MovementType.ADJUSTMENT
        assert adj.quantity_kg == Decimal("-500.000")

    def test_surplus_produces_positive_adjustment(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, admin_user, tenant_context,
    ):
        """Measured > ledger → positive ADJUSTMENT."""
        reconcile = self._get_reconcile()
        grain = grain_type_factory(code="RCB", arca_codigo=71, name="Recon B")
        unit = storage_unit_factory(name="Recon Silo B", current_grain_type=grain)
        lot = grain_lot_factory(
            storage_unit=unit, grain_type=grain, grado=1,
            total_kg=Decimal("10000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        result = reconcile(
            tenant_id=tenant_context.pk,
            measurements=[
                {"storage_unit_id": unit.pk, "measured_kg": Decimal("10500.000")},
            ],
            notes="Found extra grain",
            operator_id=admin_user.pk,
        )

        v = result["variances"][0]
        assert Decimal(str(v["variance_kg"])) == Decimal("500.000")

    def test_zero_variance_no_movement(
        self, storage_unit_factory, grain_lot_factory, grain_movement_factory,
        grain_type_factory, admin_user, tenant_context,
    ):
        """Zero variance produces no adjustment movement."""
        reconcile = self._get_reconcile()
        grain = grain_type_factory(code="RCC", arca_codigo=72, name="Recon C")
        unit = storage_unit_factory(name="Recon Silo C", current_grain_type=grain)
        lot = grain_lot_factory(
            storage_unit=unit, grain_type=grain, grado=1,
            total_kg=Decimal("10000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        initial_count = GrainMovement.objects.count()
        result = reconcile(
            tenant_id=tenant_context.pk,
            measurements=[
                {"storage_unit_id": unit.pk, "measured_kg": Decimal("10000.000")},
            ],
            notes="Exact match",
            operator_id=admin_user.pk,
        )

        # No new movements
        assert GrainMovement.objects.count() == initial_count

    def test_notes_required(
        self, storage_unit_factory, admin_user, tenant_context,
    ):
        """ADJUSTMENT requires non-empty notes."""
        reconcile = self._get_reconcile()
        unit = storage_unit_factory(name="Recon No Notes")

        with pytest.raises(ValueError, match="[Nn]otes"):
            reconcile(
                tenant_id=tenant_context.pk,
                measurements=[
                    {"storage_unit_id": unit.pk, "measured_kg": Decimal("5000.000")},
                ],
                notes="",
                operator_id=admin_user.pk,
            )


# ============================================================
# Campaign Close Service Tests (T043)
# ============================================================


class TestCampaignCloseService:
    """FR-017: CampaignCloseService validates and closes campaigns."""

    def _get_close_campaign(self):
        from apps.acopio.services.storage import close_campaign
        return close_campaign

    def test_carry_forward_creates_transfer_movements(
        self, grain_lot_factory, grain_movement_factory, admin_user,
        campana_factory, tenant_context,
    ):
        """Carry-forward creates TRANSFER_OUT + TRANSFER_IN for non-zero lots."""
        close_campaign = self._get_close_campaign()
        campaign = campana_factory(campaign_code="24/25A")
        lot = grain_lot_factory(
            campaign=campaign, grado=1, total_kg=Decimal("10000.000"),
        )
        grain_movement_factory(lot, quantity_kg=Decimal("10000.000"))

        new_campaign = campana_factory(campaign_code="25/26D")

        result = close_campaign(
            tenant_id=tenant_context.pk,
            campaign_id=campaign.pk,
            target_campaign_id=new_campaign.pk,
            supervisor_id=admin_user.pk,
        )

        # Should have carry-forward lots
        assert result["lots_carried"] >= 1

    def test_zero_balance_lots_skipped(
        self, grain_lot_factory, admin_user, campana_factory, tenant_context,
    ):
        """Zero-balance lots are NOT carried forward."""
        close_campaign = self._get_close_campaign()
        campaign = campana_factory(campaign_code="24/25B")
        grain_lot_factory(
            campaign=campaign, grado=1, total_kg=Decimal("0.000"),
        )

        new_campaign = campana_factory(campaign_code="25/26E")

        result = close_campaign(
            tenant_id=tenant_context.pk,
            campaign_id=campaign.pk,
            target_campaign_id=new_campaign.pk,
            supervisor_id=admin_user.pk,
        )

        assert result["lots_carried"] == 0
