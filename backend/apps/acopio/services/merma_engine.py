"""
Merma calculation service -- Rust FFI wrapper with Python fallback.

Implements the sequential merma formula per Circular CAC 10/86:
  Zarandeo -> Secado -> Manipuleo -> Volatil

Uses Rust engine (gravitea_rust.calculate_merma) for production,
falls back to pure Python for development/testing without Rust toolchain.
"""

from __future__ import annotations

import json
import logging
from decimal import ROUND_HALF_UP, Decimal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rust FFI import with graceful fallback
# ---------------------------------------------------------------------------

try:
    from gravitea_rust import calculate_merma as _rust_calculate_merma

    _USE_RUST = True
    logger.info("Merma engine: using Rust FFI backend")
except ImportError:
    _USE_RUST = False
    logger.info("Merma engine: using Python fallback backend")


# ---------------------------------------------------------------------------
# Pure-Python fallback implementation
# ---------------------------------------------------------------------------

_HUNDRED = Decimal("100")
_ONE = Decimal("1")
_ZERO = Decimal("0")
_Q2 = Decimal("0.01")
_Q3 = Decimal("0.001")
_Q4 = Decimal("0.0001")


def _python_calculate_merma(input_json: str) -> str:
    """
    Pure-Python fallback implementing the same sequential merma formula.

    Accepts and returns JSON strings (same interface as the Rust function).
    """
    data = json.loads(input_json)

    peso_bruto = Decimal(data["peso_neto_bruto_kg"])
    humedad = Decimal(data["humedad_pct"])
    hf = Decimal(data["hf_secado_pct"])
    zarandeo_deduction = Decimal(data["zarandeo_deduction_pct"])
    manipuleo_fijo = Decimal(data["manipuleo_fijo_pct"])
    volatil_fijo = Decimal(data["volatil_fijo_pct"])

    # --- Validate inputs ---
    if peso_bruto <= _ZERO:
        raise ValueError("peso_neto_bruto_kg must be positive")
    if not (_ZERO <= humedad <= _HUNDRED):
        raise ValueError("humedad_pct must be between 0 and 100")
    if not (_ZERO <= hf <= _HUNDRED):
        raise ValueError("hf_secado_pct must be between 0 and 100")

    # --- Step 1: Zarandeo (screening) ---
    zarandeo_pct = zarandeo_deduction
    peso_post_zarandeo = peso_bruto * (_ONE - zarandeo_pct / _HUNDRED)

    # --- Step 2: Secado (drying) ---
    if humedad <= hf:
        secado_pct = _ZERO
        peso_post_secado = peso_post_zarandeo
    else:
        secado_pct = (humedad - hf) / (_HUNDRED - hf) * _HUNDRED
        peso_post_secado = peso_post_zarandeo * (_ONE - secado_pct / _HUNDRED)

    # --- Step 3: Manipuleo (handling) -- only if secado was applied ---
    if secado_pct == _ZERO:
        manipuleo_pct = _ZERO
        peso_post_manipuleo = peso_post_secado
    else:
        manipuleo_pct = manipuleo_fijo
        peso_post_manipuleo = peso_post_secado * (_ONE - manipuleo_pct / _HUNDRED)

    # --- Step 4: Volatil (always applied) ---
    volatil_pct = volatil_fijo
    peso_final = peso_post_manipuleo * (_ONE - volatil_pct / _HUNDRED)

    # --- Derived totals ---
    total_merma = peso_bruto - peso_final
    total_factor = peso_final / peso_bruto

    # Round: 3 dp for weights, 2 dp for percentages, 4 dp for factor
    result = {
        "zarandeo_pct": str(zarandeo_pct.quantize(_Q2, rounding=ROUND_HALF_UP)),
        "secado_pct": str(secado_pct.quantize(_Q2, rounding=ROUND_HALF_UP)),
        "manipuleo_pct": str(manipuleo_pct.quantize(_Q2, rounding=ROUND_HALF_UP)),
        "volatil_pct": str(volatil_pct.quantize(_Q2, rounding=ROUND_HALF_UP)),
        "peso_post_zarandeo_kg": str(
            peso_post_zarandeo.quantize(_Q3, rounding=ROUND_HALF_UP)
        ),
        "peso_post_secado_kg": str(
            peso_post_secado.quantize(_Q3, rounding=ROUND_HALF_UP)
        ),
        "peso_post_manipuleo_kg": str(
            peso_post_manipuleo.quantize(_Q3, rounding=ROUND_HALF_UP)
        ),
        "peso_final_kg": str(peso_final.quantize(_Q3, rounding=ROUND_HALF_UP)),
        "total_merma_kg": str(total_merma.quantize(_Q3, rounding=ROUND_HALF_UP)),
        "total_factor_pct": str(total_factor.quantize(_Q4, rounding=ROUND_HALF_UP)),
    }
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_merma_deductions(params: dict) -> dict[str, Decimal]:
    """
    Public API: calculate merma deductions for a romaneo.

    Args:
        params: dict with keys:
            - peso_neto_bruto_kg: str (Decimal as string)
            - humedad_pct: str
            - hf_secado_pct: str
            - materias_extranas_pct: str
            - zarandeo_deduction_pct: str
            - manipuleo_fijo_pct: str
            - volatil_fijo_pct: str

    Returns:
        dict with all merma output fields (values as Decimal objects):
            - zarandeo_pct, secado_pct, manipuleo_pct, volatil_pct
            - peso_post_zarandeo_kg, peso_post_secado_kg, peso_post_manipuleo_kg
            - peso_final_kg, total_merma_kg, total_factor_pct
    """
    input_json = json.dumps({k: str(v) for k, v in params.items()})

    if _USE_RUST:
        try:
            result_json = _rust_calculate_merma(input_json)
        except Exception:
            logger.warning(
                "Rust merma engine failed, falling back to Python", exc_info=True
            )
            result_json = _python_calculate_merma(input_json)
    else:
        result_json = _python_calculate_merma(input_json)

    raw = json.loads(result_json)
    return {k: Decimal(v) for k, v in raw.items()}


# ---------------------------------------------------------------------------
# MermaTable lookup helper (T031)
# ---------------------------------------------------------------------------


def lookup_merma_table(
    grain_type_id: str,
    materias_extranas_pct: Decimal,
    reference_date: object,
) -> tuple:
    """
    Look up the zarandeo deduction from MermaTable for the given grain type
    and foreign matter percentage, valid at the reference date.

    Args:
        grain_type_id: UUID of the grain type.
        materias_extranas_pct: Decimal -- foreign matter percentage.
        reference_date: date -- typically romaneo.ts_entrada.

    Returns:
        tuple: (merma_table_instance, zarandeo_deduction_pct)

    Raises:
        ValueError: if no matching band found.
    """
    from django.db.models import Q

    from apps.acopio.models import MermaTable

    # Find active band: valid_to is NULL (current) or valid_to >= reference_date
    band = (
        MermaTable.objects.filter(
            grain_type_id=grain_type_id,
            materias_extranas_from_pct__lte=materias_extranas_pct,
            valid_from__lte=reference_date,
        )
        .filter(
            Q(materias_extranas_to_pct__gte=materias_extranas_pct)
            | Q(materias_extranas_to_pct__isnull=True)
        )
        .filter(
            Q(valid_to__gte=reference_date) | Q(valid_to__isnull=True)
        )
        .order_by("-valid_from")
        .first()
    )

    if band is None:
        raise ValueError(
            f"No MermaTable band found for grain_type={grain_type_id}, "
            f"materias_extranas={materias_extranas_pct}%, date={reference_date}"
        )

    return band, band.zarandeo_deduction_pct
