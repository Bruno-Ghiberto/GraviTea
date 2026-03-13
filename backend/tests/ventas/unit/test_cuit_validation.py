"""
T082: CUIT validation unit tests.

Tests validate_cuit() Modulo-11 algorithm for Argentine tax IDs.
Verifies correct check digit computation, length enforcement,
numeric-only enforcement, and hyphen rejection.

All test CUITs have been manually verified with the Modulo-11 algorithm:
  weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
  check = 11 - (sum(digit * weight) % 11)
  if check == 11 → 0; if check == 10 → 9.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.ventas.validators import validate_cuit


@pytest.mark.unit
class TestCuitValidation:
    """T082: Modulo-11 CUIT validation."""

    # --- Valid CUITs (check digit verified) ---

    def test_valid_cuit_type_20(self):
        """Type-20 CUIT with correct check digit passes validation.

        20345678906: sum=192, 192%11=5, check=11-5=6 → digit 6. ✓
        """
        validate_cuit("20345678906")  # No exception

    def test_valid_cuit_type_30(self):
        """Type-30 empresa CUIT with correct check digit passes validation.

        30111111118: sum=47, 47%11=3, check=11-3=8 → digit 8. ✓
        """
        validate_cuit("30111111118")  # No exception

    def test_valid_cuit_type_27(self):
        """Type-27 CUIT with correct check digit passes validation.

        27333333339: sum=134, 134%11=2, check=11-2=9 → digit 9. ✓
        """
        validate_cuit("27333333339")  # No exception

    # --- Invalid check digit ---

    def test_invalid_check_digit(self):
        """Wrong last digit → ValidationError.

        20345678901: correct check digit is 6, not 1.
        """
        with pytest.raises(ValidationError, match="check digit"):
            validate_cuit("20345678901")

    # --- Length errors ---

    def test_wrong_length_short(self):
        """10-digit CUIT (too short) → ValidationError."""
        with pytest.raises(ValidationError, match="11 digits"):
            validate_cuit("2034567890")

    def test_wrong_length_long(self):
        """12-digit CUIT (too long) → ValidationError."""
        with pytest.raises(ValidationError, match="11 digits"):
            validate_cuit("203456789012")

    # --- Non-numeric ---

    def test_non_numeric(self):
        """CUIT with letters → ValidationError."""
        with pytest.raises(ValidationError, match="11 digits"):
            validate_cuit("2034567890A")

    # --- Empty ---

    def test_empty_cuit(self):
        """Empty string → ValidationError."""
        with pytest.raises(ValidationError, match="11 digits"):
            validate_cuit("")

    # --- Hyphens ---

    def test_cuit_with_hyphens(self):
        """CUIT with hyphens is rejected (we require raw 11 digits).

        "20-34567890-6" has correct digits but wrong format.
        """
        with pytest.raises(ValidationError, match="11 digits"):
            validate_cuit("20-34567890-6")
