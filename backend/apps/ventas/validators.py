"""
CUIT validation for Argentine tax identification numbers.

Implements Modulo-11 check digit algorithm per ARCA specifications.
"""

import logging

from django.core.exceptions import ValidationError

try:
    from gravitea_rust import validate_cuit as _rust_validate_cuit  # type: ignore[import]

    _USE_RUST_COMPUTE = True
except (ImportError, OSError):
    _USE_RUST_COMPUTE = False
    logging.getLogger(__name__).warning(
        "gravitea_rust compute not available — using Python fallback"
    )


def validate_cuit(cuit: str) -> None:
    """
    Validate a CUIT using the Modulo-11 algorithm.

    Args:
        cuit: 11-digit string representing the CUIT.

    Raises:
        ValidationError: If the CUIT is not 11 digits, not numeric,
            or has an invalid check digit.
    """
    if _USE_RUST_COMPUTE:
        try:
            _rust_validate_cuit(cuit)
            return
        except RuntimeError as exc:
            raise ValidationError(str(exc)) from exc

    if not cuit.isdigit() or len(cuit) != 11:
        raise ValidationError("CUIT must be exactly 11 digits.")

    weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(d) * w for d, w in zip(cuit[:10], weights))
    check = 11 - (total % 11)

    if check == 11:
        check = 0
    elif check == 10:
        check = 9  # Special case per ARCA spec

    if check != int(cuit[10]):
        raise ValidationError("CUIT check digit is invalid.")
