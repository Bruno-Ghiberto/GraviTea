"""Tests for grain reference seed data (management command + fixture integrity)."""

from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.acopio.models import GrainType, MermaTable, ToleranceTable


@pytest.mark.django_db
class TestSeedGrainReference:
    """Tests for the seed_grain_reference management command."""

    def test_seed_creates_grain_types(self) -> None:
        call_command("seed_grain_reference")
        assert GrainType.objects.count() >= 7

    def test_seed_idempotency(self) -> None:
        call_command("seed_grain_reference")
        count_after_first = GrainType.objects.count()
        call_command("seed_grain_reference")
        count_after_second = GrainType.objects.count()
        assert count_after_first == count_after_second

    def test_seed_dry_run(self) -> None:
        call_command("seed_grain_reference", dry_run=True)
        assert GrainType.objects.count() == 0

    def test_soja_hf_correctness(self) -> None:
        call_command("seed_grain_reference")
        soja = GrainType.objects.get(code="SOJ")
        assert soja.hf_secado_pct == Decimal("12.50"), (
            f"Soja Hf must be 12.50, got {soja.hf_secado_pct}"
        )

    def test_tolerance_entries_exist(self) -> None:
        call_command("seed_grain_reference")
        for code in ["TRI", "MAI", "SOJ", "GIR", "SOR"]:
            gt = GrainType.objects.get(code=code)
            assert ToleranceTable.objects.filter(grain_type=gt).count() > 0

    def test_merma_bands_no_gaps(self) -> None:
        call_command("seed_grain_reference")
        trigo = GrainType.objects.get(code="TRI")
        bands = MermaTable.objects.filter(
            grain_type=trigo, valid_to__isnull=True
        ).order_by("materias_extranas_from_pct")
        assert bands.count() > 0
        for i in range(1, len(bands)):
            prev_to = bands[i - 1].materias_extranas_to_pct
            curr_from = bands[i].materias_extranas_from_pct
            if prev_to is not None:
                assert curr_from > prev_to or curr_from == prev_to
