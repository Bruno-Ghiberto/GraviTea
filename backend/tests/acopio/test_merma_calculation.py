"""Tests for merma calculation correctness and MermaCalculation immutability.

Covers:
- Merma formula verification against reference vectors (Circular CAC 10/86)
- Edge cases: dry grain (Hi <= Hf), zero deductions, negative weight
- Hf vs humedad_base confusion detection (~168 kg diff on 30t truck)
- MermaCalculation model immutability enforcement
"""

from decimal import Decimal

import pytest

from apps.acopio.models import MermaCalculation
from apps.acopio.services.merma_engine import calculate_merma_deductions


@pytest.mark.django_db
class TestMermaFormulaCorrectness:
    """Test merma formula using Python fallback."""

    def test_trigo_reference_vector(self):
        """Verify trigo reference vector from api.md spec.

        Input: peso=30000, humedad=15.2, hf=13.5, ME=1.8, zarandeo=1.00,
               manipuleo=0.25, volatil=0.30
        Expected: secado~1.97, peso_post_zarandeo=29700,
                  peso_final~28956.379, total_merma~1043.621, factor~0.9652
        """
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        assert result["zarandeo_pct"] == Decimal("1.00")
        assert result["secado_pct"] == Decimal("1.97")
        assert result["manipuleo_pct"] == Decimal("0.25")
        assert result["volatil_pct"] == Decimal("0.30")
        assert result["peso_post_zarandeo_kg"] == Decimal("29700.000")
        assert result["peso_final_kg"] == Decimal("28956.379")
        assert result["total_merma_kg"] == Decimal("1043.621")
        assert result["total_factor_pct"] == Decimal("0.9652")

    def test_soja_dry_case(self):
        """Hi <= Hf means no secado and no manipuleo.

        When grain arrives drier than the drying reference threshold,
        secado and manipuleo are skipped entirely.
        """
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "12.0",
            "hf_secado_pct": "12.5",
            "materias_extranas_pct": "1.0",
            "zarandeo_deduction_pct": "0.50",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        assert result["secado_pct"] == Decimal("0.00")
        assert result["manipuleo_pct"] == Decimal("0.00")
        # Only zarandeo and volatil applied
        assert result["peso_post_secado_kg"] == result["peso_post_zarandeo_kg"]
        assert result["peso_post_manipuleo_kg"] == result["peso_post_secado_kg"]

    def test_all_zero_deductions_except_volatil(self):
        """Edge case: Hi < Hf and ME=0 produces only volatil deduction."""
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "10000.000",
            "humedad_pct": "10.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "0.0",
            "zarandeo_deduction_pct": "0.00",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
        })
        assert result["zarandeo_pct"] == Decimal("0.00")
        assert result["secado_pct"] == Decimal("0.00")
        assert result["manipuleo_pct"] == Decimal("0.00")
        # Only volatil applied: 10000 * (1 - 0.30/100) = 9970.000
        assert result["peso_post_zarandeo_kg"] == Decimal("10000.000")
        assert result["peso_final_kg"] == Decimal("9970.000")

    def test_hf_vs_humedad_base_error_detection(self):
        """Using hf_secado_pct=13.5 (correct) vs 14.0 (wrong) produces
        detectable difference -- ~168 kg on 30t truck.

        This test exists to document the business-critical distinction
        between hf_secado (drying reference) and humedad_base (commercial
        base moisture). Confusing them causes systematic overbilling.
        """
        correct = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        wrong = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "14.0",  # WRONG: using humedad_base instead
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        difference = abs(correct["peso_final_kg"] - wrong["peso_final_kg"])
        # Expect ~168 kg difference
        assert difference > Decimal("100"), (
            f"Difference {difference} too small -- Hf error undetected"
        )

    def test_negative_weight_rejected(self):
        """Negative peso_neto_bruto_kg raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            calculate_merma_deductions({
                "peso_neto_bruto_kg": "-1000",
                "humedad_pct": "15.0",
                "hf_secado_pct": "13.5",
                "materias_extranas_pct": "1.0",
                "zarandeo_deduction_pct": "1.00",
                "manipuleo_fijo_pct": "0.25",
                "volatil_fijo_pct": "0.30",
            })

    def test_humedad_out_of_range_rejected(self):
        """humedad_pct > 100 raises ValueError."""
        with pytest.raises(ValueError, match="humedad_pct must be between"):
            calculate_merma_deductions({
                "peso_neto_bruto_kg": "30000.000",
                "humedad_pct": "150",
                "hf_secado_pct": "13.5",
                "materias_extranas_pct": "1.0",
                "zarandeo_deduction_pct": "1.00",
                "manipuleo_fijo_pct": "0.25",
                "volatil_fijo_pct": "0.30",
            })

    def test_humedad_equal_to_hf_no_secado(self):
        """Hi == Hf boundary: no secado applied (boundary condition)."""
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "13.5",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.0",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        assert result["secado_pct"] == Decimal("0.00")
        assert result["manipuleo_pct"] == Decimal("0.00")

    def test_high_humidity_produces_large_secado(self):
        """Very wet grain (25%) produces a large secado deduction."""
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "25.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.0",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        # secado_pct = (25.0 - 13.5) / (100 - 13.5) * 100 = 13.29...
        assert result["secado_pct"] > Decimal("13.00")
        assert result["secado_pct"] < Decimal("14.00")

    def test_small_weight_precision(self):
        """Formula maintains 3-decimal-place precision on small weights."""
        result = calculate_merma_deductions({
            "peso_neto_bruto_kg": "100.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })
        # Verify all weight fields have 3 decimal places
        for key in (
            "peso_post_zarandeo_kg",
            "peso_post_secado_kg",
            "peso_post_manipuleo_kg",
            "peso_final_kg",
            "total_merma_kg",
        ):
            val = result[key]
            # Decimal exponent of -3 means 3 decimal places
            assert val.as_tuple().exponent == -3, (
                f"{key}={val} does not have 3 decimal places"
            )


@pytest.mark.django_db
class TestMermaCalculationImmutability:
    """Test MermaCalculation model immutability enforcement."""

    def _create_mc(self, romaneo_pesado, merma_table_factory, admin_user):
        """Helper to create a MermaCalculation instance."""
        mt = merma_table_factory(romaneo_pesado.grain_type)
        return MermaCalculation.objects.create(
            romaneo=romaneo_pesado,
            tenant_id=romaneo_pesado.tenant_id,
            merma_table_version=mt,
            peso_neto_bruto_input_kg=Decimal("30000.000"),
            hi_input_pct=Decimal("15.20"),
            hf_used_pct=Decimal("13.50"),
            materias_extranas_input_pct=Decimal("1.80"),
            zarandeo_pct=Decimal("1.00"),
            secado_pct=Decimal("1.97"),
            manipuleo_pct=Decimal("0.25"),
            volatil_pct=Decimal("0.30"),
            peso_post_zarandeo_kg=Decimal("29700.000"),
            peso_post_secado_kg=Decimal("29116.301"),
            peso_post_manipuleo_kg=Decimal("29043.510"),
            peso_final_kg=Decimal("28956.379"),
            total_merma_kg=Decimal("1043.621"),
            total_factor_pct=Decimal("0.9652"),
            calculated_by=admin_user,
        )

    def test_create_succeeds(self, romaneo_pesado, merma_table_factory, admin_user):
        """INSERT (first save) works correctly."""
        mc = self._create_mc(romaneo_pesado, merma_table_factory, admin_user)
        assert mc.pk is not None
        assert mc.peso_final_kg == Decimal("28956.379")

    def test_save_raises_on_update(self, romaneo_pesado, merma_table_factory, admin_user):
        """UPDATE (second save) raises ValueError -- immutable ledger."""
        mc = self._create_mc(romaneo_pesado, merma_table_factory, admin_user)
        mc.peso_final_kg = Decimal("99999.000")
        with pytest.raises(ValueError, match="immutable"):
            mc.save()

    def test_delete_raises(self, romaneo_pesado, merma_table_factory, admin_user):
        """DELETE raises ValueError -- immutable ledger."""
        mc = self._create_mc(romaneo_pesado, merma_table_factory, admin_user)
        with pytest.raises(ValueError, match="immutable"):
            mc.delete()

    def test_str_representation(self, romaneo_pesado, merma_table_factory, admin_user):
        """__str__ includes the romaneo reference."""
        mc = self._create_mc(romaneo_pesado, merma_table_factory, admin_user)
        assert "Merma for" in str(mc)
