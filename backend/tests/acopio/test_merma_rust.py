"""Rust FFI parity tests -- compare Rust and Python merma implementations.

All tests in this module require the ``gravitea_rust`` extension to be
installed.  When the Rust toolchain is not available (CI without maturin,
developer without Rust, etc.) every test is automatically skipped via
``pytest.importorskip`` in the autouse fixture.
"""

import json
from decimal import Decimal

import pytest


def _rust_available() -> bool:
    """Check if the Rust FFI extension is importable."""
    try:
        from gravitea_rust import calculate_merma  # noqa: F401
        return True
    except ImportError:
        return False


class TestRustPythonParity:
    """Compare Rust and Python merma implementations for identical results.

    Both backends receive a JSON string and return a JSON string.  The
    expected invariant is bit-exact equality on every output field.
    """

    @pytest.fixture(autouse=True)
    def _skip_if_no_rust(self):
        pytest.importorskip("gravitea_rust")

    def _compare(self, params: dict) -> None:
        """Run the same input through Rust and Python, assert identical output."""
        from gravitea_rust import calculate_merma as rust_fn
        from apps.acopio.services.merma_engine import _python_calculate_merma

        input_json = json.dumps({k: str(v) for k, v in params.items()})

        rust_result = json.loads(rust_fn(input_json))
        python_result = json.loads(_python_calculate_merma(input_json))

        for key in rust_result:
            rust_val = Decimal(rust_result[key])
            python_val = Decimal(python_result[key])
            assert rust_val == python_val, (
                f"Mismatch on {key}: Rust={rust_val}, Python={python_val}"
            )

    # ---- Grain-type parity vectors ----------------------------------------

    def test_trigo_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })

    def test_maiz_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "28000.000",
            "humedad_pct": "16.5",
            "hf_secado_pct": "14.5",
            "materias_extranas_pct": "2.0",
            "zarandeo_deduction_pct": "1.50",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
        })

    def test_soja_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "32000.000",
            "humedad_pct": "12.0",
            "hf_secado_pct": "12.5",
            "materias_extranas_pct": "1.0",
            "zarandeo_deduction_pct": "0.50",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.20",
        })

    def test_girasol_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "25000.000",
            "humedad_pct": "12.0",
            "hf_secado_pct": "11.0",
            "materias_extranas_pct": "3.0",
            "zarandeo_deduction_pct": "2.00",
            "manipuleo_fijo_pct": "0.15",
            "volatil_fijo_pct": "0.25",
        })

    def test_sorgo_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "29000.000",
            "humedad_pct": "15.0",
            "hf_secado_pct": "14.5",
            "materias_extranas_pct": "0.5",
            "zarandeo_deduction_pct": "0.25",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
        })

    def test_cebada_parity(self):
        self._compare({
            "peso_neto_bruto_kg": "27000.000",
            "humedad_pct": "14.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.2",
            "zarandeo_deduction_pct": "0.75",
            "manipuleo_fijo_pct": "0.10",
            "volatil_fijo_pct": "0.30",
        })

    # ---- Edge-case parity vectors -----------------------------------------

    def test_dry_grain_parity(self):
        """Hi <= Hf: no secado, no manipuleo."""
        self._compare({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "11.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.0",
            "zarandeo_deduction_pct": "0.50",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })

    def test_zero_zarandeo_parity(self):
        """ME=0 -> zarandeo=0."""
        self._compare({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "15.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "0.0",
            "zarandeo_deduction_pct": "0.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })

    def test_high_humidity_parity(self):
        """25% humidity -- large secado deduction."""
        self._compare({
            "peso_neto_bruto_kg": "30000.000",
            "humedad_pct": "25.0",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "2.0",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })

    def test_small_weight_parity(self):
        """100 kg load -- precision on small numbers."""
        self._compare({
            "peso_neto_bruto_kg": "100.000",
            "humedad_pct": "15.2",
            "hf_secado_pct": "13.5",
            "materias_extranas_pct": "1.8",
            "zarandeo_deduction_pct": "1.00",
            "manipuleo_fijo_pct": "0.25",
            "volatil_fijo_pct": "0.30",
        })


class TestRustErrorHandling:
    """Test that the Rust FFI raises proper errors for invalid input."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_rust(self):
        pytest.importorskip("gravitea_rust")

    def test_invalid_json(self):
        from gravitea_rust import calculate_merma
        with pytest.raises((ValueError, Exception)):
            calculate_merma("not json")

    def test_negative_weight(self):
        from gravitea_rust import calculate_merma
        with pytest.raises((ValueError, Exception)):
            calculate_merma(json.dumps({
                "peso_neto_bruto_kg": "-1000",
                "humedad_pct": "15.0",
                "hf_secado_pct": "13.5",
                "materias_extranas_pct": "1.0",
                "zarandeo_deduction_pct": "1.00",
                "manipuleo_fijo_pct": "0.25",
                "volatil_fijo_pct": "0.30",
            }))

    def test_out_of_range_humidity(self):
        from gravitea_rust import calculate_merma
        with pytest.raises((ValueError, Exception)):
            calculate_merma(json.dumps({
                "peso_neto_bruto_kg": "30000",
                "humedad_pct": "150",
                "hf_secado_pct": "13.5",
                "materias_extranas_pct": "1.0",
                "zarandeo_deduction_pct": "1.00",
                "manipuleo_fijo_pct": "0.25",
                "volatil_fijo_pct": "0.30",
            }))

    def test_missing_field(self):
        from gravitea_rust import calculate_merma
        with pytest.raises((ValueError, KeyError, Exception)):
            calculate_merma(json.dumps({
                "peso_neto_bruto_kg": "30000",
                # Missing other required fields
            }))
