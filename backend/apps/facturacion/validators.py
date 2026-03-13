"""
ARCA comprobante validators for Gravitea ERP.

Implements amount validation (FR-007), IVA breakdown validation (FR-008),
service date validation (FR-009), tributos validation (FR-010),
and CbtesAsoc type compatibility (US6).
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError

from .constants import (
    CBTE_TIPO_LETTER,
    CBTES_ASOC_REQUIRED_CODES,
    FACTURA_CODES,
    Concepto,
)

logger = logging.getLogger(__name__)

try:
    from gravitea_rust import (  # type: ignore[import]
        validate_importes as _rust_validate_importes,
        validate_iva_breakdown as _rust_validate_iva_breakdown,
    )

    _USE_RUST_COMPUTE = True
except (ImportError, OSError):
    _USE_RUST_COMPUTE = False
    logging.getLogger(__name__).warning(
        "gravitea_rust compute not available — using Python fallback"
    )


# CbteTipo letter groups for IVA conditional validation
_IVA_REQUIRED_LETTERS = frozenset({"A", "B", "M"})
_IVA_PROHIBITED_LETTERS = frozenset({"C"})

_TOLERANCE_ABSOLUTE = Decimal("0.01")
_TOLERANCE_RELATIVE = Decimal("0.0001")  # 0.01%


def _dual_tolerance_eq(expected: Decimal, actual: Decimal) -> bool:
    """
    Check equality within ARCA's dual-tolerance.

    Passes if EITHER condition is met:
    - Absolute: |diff| <= 0.01
    - Relative: |diff| <= 0.01% of |expected|

    Args:
        expected: The calculated reference amount.
        actual: The submitted amount to check.

    Returns:
        True if amounts are within tolerance.
    """
    diff = abs(expected - actual)
    if diff <= _TOLERANCE_ABSOLUTE:
        return True
    if expected != 0 and diff <= _TOLERANCE_RELATIVE * abs(expected):
        return True
    return False


def validate_importes(
    *,
    imp_total: Decimal,
    imp_neto: Decimal,
    imp_iva: Decimal,
    imp_trib: Decimal,
    imp_op_ex: Decimal,
    imp_tot_conc: Decimal,
) -> None:
    """
    Validate the master amount equation with ARCA's dual-tolerance.

    FR-007: ImpTotal = ImpNeto + ImpOpEx + ImpIVA + ImpTrib + ImpTotConc

    Raises:
        ValidationError: If the equation does not balance within tolerance.
    """
    if _USE_RUST_COMPUTE:
        try:
            _rust_validate_importes(
                str(imp_total),
                str(imp_neto),
                str(imp_iva),
                str(imp_trib),
                str(imp_op_ex),
                str(imp_tot_conc),
            )
            return
        except RuntimeError as exc:
            raise ValidationError(str(exc), code="amount_equation_mismatch") from exc

    expected = imp_neto + imp_op_ex + imp_iva + imp_trib + imp_tot_conc

    if not _dual_tolerance_eq(expected, imp_total):
        raise ValidationError(
            f"Amount equation does not balance: "
            f"ImpTotal ({imp_total}) != "
            f"ImpNeto ({imp_neto}) + ImpOpEx ({imp_op_ex}) + "
            f"ImpIVA ({imp_iva}) + ImpTrib ({imp_trib}) + "
            f"ImpTotConc ({imp_tot_conc}) = {expected}. "
            f"Difference: {abs(imp_total - expected)}.",
            code="amount_equation_mismatch",
        )


def validate_iva_breakdown(
    *,
    cbte_tipo: int,
    aliciva_list: list[dict[str, Any]],
    imp_iva: Decimal,
    imp_neto: Decimal,
) -> None:
    """
    Validate IVA breakdown entries against comprobante amounts.

    FR-008:
    - Types A/B/M: AlicIva is MANDATORY (at least one entry).
    - Type C: AlicIva must be EMPTY (IVA omitted entirely).
    - Sum of aliciva importe must equal imp_iva (within tolerance).
    - Sum of aliciva base_imp must equal imp_neto (within tolerance).

    Args:
        cbte_tipo: CbteTipo code.
        aliciva_list: List of dicts with 'iva_id', 'base_imp', 'importe'.
        imp_iva: Total IVA from comprobante header.
        imp_neto: Net taxable amount from comprobante header.

    Raises:
        ValidationError: If IVA breakdown is invalid.
    """
    if _USE_RUST_COMPUTE:
        try:
            aliciva_json = json.dumps(
                [
                    {
                        "iva_id": item["iva_id"],
                        "base_imp": str(item["base_imp"]),
                        "importe": str(item["importe"]),
                    }
                    for item in aliciva_list
                ]
            )
            _rust_validate_iva_breakdown(
                int(cbte_tipo),
                aliciva_json,
                str(imp_iva),
                str(imp_neto),
            )
            return
        except RuntimeError as exc:
            raise ValidationError(str(exc)) from exc

    letter = CBTE_TIPO_LETTER.get(cbte_tipo)

    if letter in _IVA_REQUIRED_LETTERS:
        if not aliciva_list:
            raise ValidationError(
                f"IVA breakdown (AlicIva) is mandatory for CbteTipo {cbte_tipo} "
                f"(Type {letter}). At least one IVA rate entry is required.",
                code="iva_breakdown_required",
            )
    elif letter in _IVA_PROHIBITED_LETTERS:
        if aliciva_list:
            raise ValidationError(
                f"IVA breakdown must be empty for CbteTipo {cbte_tipo} "
                f"(Type {letter}). Type C invoices must omit IVA entirely.",
                code="iva_breakdown_prohibited",
            )
        return

    if not aliciva_list:
        return

    total_importe = sum(Decimal(str(item["importe"])) for item in aliciva_list)
    total_base_imp = sum(Decimal(str(item["base_imp"])) for item in aliciva_list)

    if not _dual_tolerance_eq(imp_iva, total_importe):
        raise ValidationError(
            f"AlicIva importe sum ({total_importe}) does not match "
            f"ImpIVA ({imp_iva}). Difference: {abs(imp_iva - total_importe)}.",
            code="iva_sum_mismatch",
        )

    if not _dual_tolerance_eq(imp_neto, total_base_imp):
        raise ValidationError(
            f"AlicIva base_imp sum ({total_base_imp}) does not match "
            f"ImpNeto ({imp_neto}). Difference: {abs(imp_neto - total_base_imp)}.",
            code="iva_base_sum_mismatch",
        )


def validate_service_dates(
    *,
    concepto: int,
    fch_serv_desde: Any | None,
    fch_serv_hasta: Any | None,
    fch_vto_pago: Any | None,
    cbte_fch: Any | None = None,
) -> None:
    """
    Validate service date fields based on Concepto type.

    FR-009:
    - Concepto=1 (Productos): Dates MUST be omitted.
    - Concepto=2 (Servicios) or 3 (Productos y Servicios): All three MANDATORY.

    Raises:
        ValidationError: If service dates don't match concepto requirements.
    """
    has_dates = any([fch_serv_desde, fch_serv_hasta, fch_vto_pago])
    all_dates = all([fch_serv_desde, fch_serv_hasta, fch_vto_pago])

    if concepto == Concepto.PRODUCTOS:
        if has_dates:
            raise ValidationError(
                "Service dates (FchServDesde, FchServHasta, FchVtoPago) "
                "must be omitted for Concepto=1 (Productos).",
                code="service_dates_not_allowed",
            )
    elif concepto in (Concepto.SERVICIOS, Concepto.PRODUCTOS_Y_SERVICIOS):
        if not all_dates:
            missing = []
            if not fch_serv_desde:
                missing.append("FchServDesde")
            if not fch_serv_hasta:
                missing.append("FchServHasta")
            if not fch_vto_pago:
                missing.append("FchVtoPago")
            raise ValidationError(
                f"Service dates are mandatory for Concepto={concepto}. "
                f"Missing: {', '.join(missing)}.",
                code="service_dates_required",
            )

    # Date ordering validation (only when dates are present)
    if fch_serv_desde and fch_serv_hasta and fch_serv_desde > fch_serv_hasta:
        raise ValidationError(
            f"FchServDesde ({fch_serv_desde}) must not be after "
            f"FchServHasta ({fch_serv_hasta}).",
            code="service_dates_order_invalid",
        )

    if cbte_fch and fch_vto_pago and fch_vto_pago < cbte_fch:
        raise ValidationError(
            f"FchVtoPago ({fch_vto_pago}) must not be before "
            f"CbteFch ({cbte_fch}).",
            code="vto_pago_before_cbte_fch",
        )


def validate_tributos(
    *,
    imp_trib: Decimal,
    tributo_list: list[dict[str, Any]],
) -> None:
    """
    Validate tributos (other taxes) consistency.

    FR-010:
    - If ImpTrib=0: No Tributo entries allowed (XML element omitted entirely).
    - If ImpTrib>0: Sum of tributo importe must equal ImpTrib.

    Raises:
        ValidationError: If tributos don't match ImpTrib.
    """
    if imp_trib == 0:
        if tributo_list:
            raise ValidationError(
                "Tributos must be empty when ImpTrib=0. "
                "The <Tributos> XML element must be omitted entirely.",
                code="tributos_not_allowed",
            )
        return

    if not tributo_list:
        raise ValidationError(
            f"Tributo entries are required when ImpTrib={imp_trib} > 0.",
            code="tributos_required",
        )

    total_importe = sum(Decimal(str(item["importe"])) for item in tributo_list)

    if not _dual_tolerance_eq(imp_trib, total_importe):
        raise ValidationError(
            f"Tributo importe sum ({total_importe}) does not match "
            f"ImpTrib ({imp_trib}). Difference: {abs(imp_trib - total_importe)}.",
            code="tributo_sum_mismatch",
        )


def validate_cbtes_asoc(
    *,
    cbte_tipo: int,
    cbtes_asoc_list: list[dict[str, Any]],
) -> list[str]:
    """
    Validate CbtesAsoc entries for NC/ND comprobantes.

    US6 validation:
    - NC/ND MUST have at least one CbteAsoc entry.
    - Type compatibility: A->A, B->B, C->C, M->M.
    - Local existence check is a soft warning (ARCA is the authority).

    Args:
        cbte_tipo: CbteTipo code of the NC/ND being issued.
        cbtes_asoc_list: List of dicts with 'tipo', 'pto_vta', 'nro'.

    Returns:
        List of warning strings for non-existent local references.

    Raises:
        ValidationError: If type compatibility fails or required associations missing.
    """
    warnings: list[str] = []
    parent_letter = CBTE_TIPO_LETTER.get(cbte_tipo)

    if parent_letter is None:
        raise ValidationError(
            f"Unknown CbteTipo code: {cbte_tipo}.",
            code="unknown_cbte_tipo",
        )

    if cbte_tipo in CBTES_ASOC_REQUIRED_CODES and not cbtes_asoc_list:
        raise ValidationError(
            f"CbtesAsoc is required for CbteTipo {cbte_tipo} "
            f"(Nota de Credito/Debito). At least one associated "
            f"comprobante must be referenced.",
            code="cbtes_asoc_required",
        )

    if cbte_tipo in FACTURA_CODES and cbtes_asoc_list:
        raise ValidationError(
            f"CbtesAsoc must be empty for CbteTipo {cbte_tipo} (Factura). "
            f"Only Notas de Crédito/Débito may reference associated comprobantes.",
            code="cbtes_asoc_not_allowed",
        )

    for i, asoc in enumerate(cbtes_asoc_list):
        asoc_tipo = asoc.get("tipo")
        asoc_letter = CBTE_TIPO_LETTER.get(asoc_tipo)

        if asoc_letter is None:
            raise ValidationError(
                f"CbtesAsoc[{i}]: Unknown associated CbteTipo code: {asoc_tipo}.",
                code="unknown_asoc_cbte_tipo",
            )

        if asoc_letter != parent_letter:
            raise ValidationError(
                f"CbtesAsoc[{i}]: Type incompatible. "
                f"CbteTipo {cbte_tipo} (Type {parent_letter}) cannot reference "
                f"CbteTipo {asoc_tipo} (Type {asoc_letter}). "
                f"Cross-type references are rejected by ARCA (error 202).",
                code="cbtes_asoc_type_mismatch",
            )

        # Soft local existence check — import here to avoid circular imports
        from .models import Comprobante

        pto_vta = asoc.get("pto_vta")
        nro = asoc.get("nro")

        exists = Comprobante.objects.filter(
            cbte_tipo=asoc_tipo,
            punto_venta__numero=pto_vta,
            cbte_nro=nro,
        ).exists()

        if not exists:
            pto_vta_str = f"{pto_vta:05d}" if isinstance(pto_vta, int) else str(pto_vta)
            nro_str = f"{nro:08d}" if isinstance(nro, int) else str(nro)
            warnings.append(
                f"CbtesAsoc[{i}]: Referenced comprobante "
                f"{asoc_tipo}-{pto_vta_str}-{nro_str} "
                f"not found in local database. ARCA is the authority — "
                f"this may still be valid if issued outside this system."
            )

    return warnings
