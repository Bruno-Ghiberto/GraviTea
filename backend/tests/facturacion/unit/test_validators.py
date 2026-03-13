"""
Unit tests for facturacion validators.

Tests validate_importes (dual-tolerance), validate_iva_breakdown (mandatory A/B,
prohibited C), validate_service_dates (Concepto-conditional),
validate_tributos (omit when ImpTrib=0), and validate_cbtes_asoc (NC/ND
association rules, Factura prohibition, type compatibility, local existence).

Spec source: specs/invoice-backend-developement/tasks.md T030, T045
Patterns: skills/gravitea-invoice/SKILL.md (Patterns 5, 6)
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError


# ============================================================
# validate_importes Tests
# ============================================================


@pytest.mark.unit
class TestValidateImportes:
    """
    Tests for validate_importes — ARCA amount field validation.

    Rule: ImpTotal = ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc
    Dual-tolerance:
      PASS if |calculated - declared| / max(|calculated|, 1) <= 0.0001 (0.01% relative)
        OR if |calculated - declared| <= 0.01 (1 centavo absolute)
    """

    def test_exact_match(self):
        """Amounts that sum exactly should pass."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("121.00"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("21.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_exact_match_large_amounts(self):
        """Large amounts that sum exactly should pass."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("1234567.89"),
            imp_neto=Decimal("1000000.00"),
            imp_iva=Decimal("210000.00"),
            imp_trib=Decimal("15000.00"),
            imp_op_ex=Decimal("5567.89"),
            imp_tot_conc=Decimal("4000.00"),
        )

    def test_all_zero(self):
        """All-zero amounts should pass (valid degenerate case)."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("0.00"),
            imp_neto=Decimal("0.00"),
            imp_iva=Decimal("0.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_missing_optional_fields_default_zero(self):
        """When optional components are zero, equation still balances."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("100.00"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("0.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_mismatch_raises_value_error(self):
        """Clear mismatch raises ValidationError."""
        from apps.facturacion.validators import validate_importes

        with pytest.raises(ValidationError) as exc_info:
            validate_importes(
                imp_total=Decimal("200.00"),
                imp_neto=Decimal("100.00"),
                imp_iva=Decimal("21.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )
        assert exc_info.value.code == "amount_equation_mismatch"

    def test_mismatch_by_one_peso(self):
        """Off by 1 peso (exceeds both tolerances) raises ValidationError."""
        from apps.facturacion.validators import validate_importes

        with pytest.raises(ValidationError):
            validate_importes(
                imp_total=Decimal("122.00"),
                imp_neto=Decimal("100.00"),
                imp_iva=Decimal("21.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )

    def test_absolute_tolerance_pass(self):
        """Error within 1 centavo absolute tolerance should pass."""
        from apps.facturacion.validators import validate_importes

        # Calculated sum = 121.00, declared = 121.01 -> absolute error = 0.01 -> pass
        validate_importes(
            imp_total=Decimal("121.01"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("21.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_absolute_tolerance_boundary_fail(self):
        """Error of 0.02 (> 0.01 absolute) on small amounts should fail."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 1.00, declared = 1.02 -> absolute = 0.02 > 0.01
        # Relative = 0.02 / 1 = 0.02 > 0.0001
        # Both fail -> ValidationError
        with pytest.raises(ValidationError):
            validate_importes(
                imp_total=Decimal("1.02"),
                imp_neto=Decimal("1.00"),
                imp_iva=Decimal("0.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )

    def test_relative_tolerance_pass_large_amount(self):
        """Error within 0.01% relative tolerance on large amount should pass."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 1000000.00, declared = 1000000.09
        # Absolute error = 0.09 > 0.01 (absolute fails)
        # Relative error = 0.09 / 1000000 = 0.00000009 < 0.0001 (relative passes)
        # One passes -> overall passes
        validate_importes(
            imp_total=Decimal("1000000.09"),
            imp_neto=Decimal("1000000.00"),
            imp_iva=Decimal("0.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_relative_tolerance_fail_small_amount(self):
        """Same absolute error fails relative tolerance on small amounts."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 10.00, declared = 10.05
        # Absolute error = 0.05 > 0.01 (absolute fails)
        # Relative error = 0.05 / 10 = 0.005 > 0.0001 (relative fails)
        # Both fail -> ValidationError
        with pytest.raises(ValidationError):
            validate_importes(
                imp_total=Decimal("10.05"),
                imp_neto=Decimal("10.00"),
                imp_iva=Decimal("0.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )

    def test_negative_amounts_not_allowed(self):
        """Negative imp_total with positive components should fail."""
        from apps.facturacion.validators import validate_importes

        with pytest.raises(ValidationError):
            validate_importes(
                imp_total=Decimal("-100.00"),
                imp_neto=Decimal("100.00"),
                imp_iva=Decimal("0.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )

    def test_all_components_present(self):
        """Full breakdown with all non-zero components should pass."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("157.50"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("21.00"),
            imp_trib=Decimal("3.50"),
            imp_op_ex=Decimal("25.00"),
            imp_tot_conc=Decimal("8.00"),
        )

    def test_rounding_quantize_to_two_decimals(self):
        """Amounts with >2 decimal places within absolute tolerance should pass."""
        from apps.facturacion.validators import validate_importes

        # 100.005 + 21.004 = 121.009, imp_total=121.01 -> diff = 0.001 <= 0.01 -> pass
        validate_importes(
            imp_total=Decimal("121.01"),
            imp_neto=Decimal("100.005"),
            imp_iva=Decimal("21.004"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_dual_tolerance_relative_pass_absolute_fail(self):
        """Relative tolerance passes but absolute fails -> overall passes (OR logic)."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 500000.00, declared = 500000.04
        # Absolute error = 0.04 > 0.01 (FAIL)
        # Relative error = 0.04 / 500000 = 0.00000008 < 0.0001 (PASS)
        # OR logic -> passes
        validate_importes(
            imp_total=Decimal("500000.04"),
            imp_neto=Decimal("500000.00"),
            imp_iva=Decimal("0.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_dual_tolerance_absolute_pass_relative_fail(self):
        """Absolute tolerance passes but relative fails -> overall passes (OR logic)."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 5.00, declared = 5.01
        # Absolute error = 0.01 <= 0.01 (PASS)
        # Relative error = 0.01 / 5 = 0.002 > 0.0001 (FAIL)
        # OR logic -> passes
        validate_importes(
            imp_total=Decimal("5.01"),
            imp_neto=Decimal("5.00"),
            imp_iva=Decimal("0.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_dual_tolerance_both_fail(self):
        """Both tolerances fail -> raises ValidationError."""
        from apps.facturacion.validators import validate_importes

        # Calculated = 50.00, declared = 50.10
        # Absolute error = 0.10 > 0.01 (FAIL)
        # Relative error = 0.10 / 50 = 0.002 > 0.0001 (FAIL)
        with pytest.raises(ValidationError):
            validate_importes(
                imp_total=Decimal("50.10"),
                imp_neto=Decimal("50.00"),
                imp_iva=Decimal("0.00"),
                imp_trib=Decimal("0.00"),
                imp_op_ex=Decimal("0.00"),
                imp_tot_conc=Decimal("0.00"),
            )

    def test_integer_string_amounts(self):
        """Integer-valued Decimal amounts should be handled correctly."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("100"),
            imp_neto=Decimal("100"),
            imp_iva=Decimal("0"),
            imp_trib=Decimal("0"),
            imp_op_ex=Decimal("0"),
            imp_tot_conc=Decimal("0"),
        )

    def test_numeric_input(self):
        """Decimal inputs from numeric values should be accepted."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("121.00"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("21.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )

    def test_decimal_input(self):
        """Decimal inputs should be accepted."""
        from apps.facturacion.validators import validate_importes

        validate_importes(
            imp_total=Decimal("121.00"),
            imp_neto=Decimal("100.00"),
            imp_iva=Decimal("21.00"),
            imp_trib=Decimal("0.00"),
            imp_op_ex=Decimal("0.00"),
            imp_tot_conc=Decimal("0.00"),
        )


# ============================================================
# validate_iva_breakdown Tests
# ============================================================


@pytest.mark.unit
class TestValidateIvaBreakdown:
    """
    Tests for validate_iva_breakdown -- IVA line validation per cbte_tipo.

    Rules:
    - Type A/B/M: AlicIva is MANDATORY (at least one entry)
    - Type C: AlicIva is PROHIBITED (no IVA lines allowed)
    - Sum of AlicIva.importe must match imp_iva
    - Sum of AlicIva.base_imp must match imp_neto
    """

    def test_factura_a_with_iva_valid(self):
        """Factura A (CbteTipo=1) with IVA breakdown passes."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=1,
            aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}],
            imp_iva=Decimal("21.00"),
            imp_neto=Decimal("100.00"),
        )

    def test_factura_b_with_iva_valid(self):
        """Factura B (CbteTipo=6) with IVA breakdown passes."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=6,
            aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}],
            imp_iva=Decimal("21.00"),
            imp_neto=Decimal("100.00"),
        )

    def test_factura_m_with_iva_valid(self):
        """Factura M (CbteTipo=51) with IVA breakdown passes."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=51,
            aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}],
            imp_iva=Decimal("21.00"),
            imp_neto=Decimal("100.00"),
        )

    def test_factura_a_missing_iva_raises(self):
        """Factura A without IVA breakdown raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=1,
                aliciva_list=[],
                imp_iva=Decimal("21.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_breakdown_required"

    def test_nota_debito_a_missing_iva_raises(self):
        """Nota de Debito A (CbteTipo=2) without IVA breakdown raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=2,
                aliciva_list=[],
                imp_iva=Decimal("10.50"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_breakdown_required"

    def test_nota_credito_b_missing_iva_raises(self):
        """Nota de Credito B (CbteTipo=8) without IVA breakdown raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=8,
                aliciva_list=[],
                imp_iva=Decimal("21.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_breakdown_required"

    def test_factura_c_no_iva_valid(self):
        """Factura C (CbteTipo=11) without IVA breakdown passes."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=11,
            aliciva_list=[],
            imp_iva=Decimal("0.00"),
            imp_neto=Decimal("100.00"),
        )

    def test_nota_credito_c_no_iva_valid(self):
        """Nota de Credito C (CbteTipo=13) without IVA breakdown passes."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=13,
            aliciva_list=[],
            imp_iva=Decimal("0.00"),
            imp_neto=Decimal("100.00"),
        )

    def test_factura_c_with_iva_raises(self):
        """Factura C with IVA breakdown raises ValidationError (prohibited)."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=11,
                aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}],
                imp_iva=Decimal("0.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_breakdown_prohibited"

    def test_nota_debito_c_with_iva_raises(self):
        """Nota de Debito C (CbteTipo=12) with IVA breakdown raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=12,
                aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")}],
                imp_iva=Decimal("0.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_breakdown_prohibited"

    def test_iva_importe_sum_mismatch_raises(self):
        """Sum of AlicIva.importe != imp_iva raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=1,
                aliciva_list=[{"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("10.00")}],
                imp_iva=Decimal("21.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_sum_mismatch"

    def test_iva_base_imp_sum_mismatch_raises(self):
        """Sum of AlicIva.base_imp != imp_neto raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=1,
                aliciva_list=[{"iva_id": 5, "base_imp": Decimal("50.00"), "importe": Decimal("21.00")}],
                imp_iva=Decimal("21.00"),
                imp_neto=Decimal("100.00"),
            )
        assert exc_info.value.code == "iva_base_sum_mismatch"

    def test_multiple_iva_rates_valid(self):
        """Multiple IVA rates summing correctly should pass."""
        from apps.facturacion.validators import validate_iva_breakdown

        validate_iva_breakdown(
            cbte_tipo=1,
            aliciva_list=[
                {"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")},
                {"iva_id": 4, "base_imp": Decimal("100.00"), "importe": Decimal("10.50")},
            ],
            imp_iva=Decimal("31.50"),
            imp_neto=Decimal("200.00"),
        )

    def test_multiple_iva_rates_importe_mismatch(self):
        """Multiple IVA rates with wrong total raises ValidationError."""
        from apps.facturacion.validators import validate_iva_breakdown

        with pytest.raises(ValidationError) as exc_info:
            validate_iva_breakdown(
                cbte_tipo=6,
                aliciva_list=[
                    {"iva_id": 5, "base_imp": Decimal("100.00"), "importe": Decimal("21.00")},
                    {"iva_id": 4, "base_imp": Decimal("100.00"), "importe": Decimal("10.50")},
                ],
                imp_iva=Decimal("30.00"),
                imp_neto=Decimal("200.00"),
            )
        assert exc_info.value.code == "iva_sum_mismatch"


# ============================================================
# validate_service_dates Tests
# ============================================================


@pytest.mark.unit
class TestValidateServiceDates:
    """
    Tests for validate_service_dates -- Concepto-conditional date rules.

    Rules:
    - Concepto=1 (Productos): fch_serv_desde, fch_serv_hasta, fch_vto_pago MUST BE OMITTED
    - Concepto=2 (Servicios) or 3 (Productos y Servicios): dates are MANDATORY
    - Date logic: fch_serv_desde <= fch_serv_hasta
    - Date logic: fch_vto_pago >= cbte_fch
    """

    def test_concepto_1_no_dates_valid(self):
        """Concepto=1 (Productos) without service dates passes."""
        from apps.facturacion.validators import validate_service_dates

        validate_service_dates(
            concepto=1,
            fch_serv_desde=None,
            fch_serv_hasta=None,
            fch_vto_pago=None,
        )

    def test_concepto_1_with_dates_raises(self):
        """Concepto=1 (Productos) with service dates raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=1,
                fch_serv_desde=today - timedelta(days=30),
                fch_serv_hasta=today,
                fch_vto_pago=today + timedelta(days=30),
            )
        assert exc_info.value.code == "service_dates_not_allowed"

    def test_concepto_1_partial_dates_raises(self):
        """Concepto=1 with any single date field set raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=1,
                fch_serv_desde=date.today(),
                fch_serv_hasta=None,
                fch_vto_pago=None,
            )
        assert exc_info.value.code == "service_dates_not_allowed"

    def test_concepto_2_with_all_dates_valid(self):
        """Concepto=2 (Servicios) with all dates passes."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        validate_service_dates(
            concepto=2,
            fch_serv_desde=today - timedelta(days=30),
            fch_serv_hasta=today,
            fch_vto_pago=today + timedelta(days=30),
            cbte_fch=today,
        )

    def test_concepto_3_with_all_dates_valid(self):
        """Concepto=3 (Productos y Servicios) with all dates passes."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        validate_service_dates(
            concepto=3,
            fch_serv_desde=today - timedelta(days=15),
            fch_serv_hasta=today,
            fch_vto_pago=today + timedelta(days=15),
            cbte_fch=today,
        )

    def test_concepto_2_missing_all_dates_raises(self):
        """Concepto=2 without any dates raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=2,
                fch_serv_desde=None,
                fch_serv_hasta=None,
                fch_vto_pago=None,
            )
        assert exc_info.value.code == "service_dates_required"

    def test_concepto_3_missing_fch_serv_desde_raises(self):
        """Concepto=3 missing fch_serv_desde raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=3,
                fch_serv_desde=None,
                fch_serv_hasta=today,
                fch_vto_pago=today + timedelta(days=30),
            )
        assert exc_info.value.code == "service_dates_required"

    def test_concepto_2_missing_fch_serv_hasta_raises(self):
        """Concepto=2 missing fch_serv_hasta raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=2,
                fch_serv_desde=today - timedelta(days=30),
                fch_serv_hasta=None,
                fch_vto_pago=today + timedelta(days=30),
            )
        assert exc_info.value.code == "service_dates_required"

    def test_concepto_2_missing_fch_vto_pago_raises(self):
        """Concepto=2 missing fch_vto_pago raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=2,
                fch_serv_desde=today - timedelta(days=30),
                fch_serv_hasta=today,
                fch_vto_pago=None,
            )
        assert exc_info.value.code == "service_dates_required"

    def test_desde_after_hasta_raises(self):
        """fch_serv_desde > fch_serv_hasta raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=2,
                fch_serv_desde=today + timedelta(days=1),
                fch_serv_hasta=today,
                fch_vto_pago=today + timedelta(days=30),
                cbte_fch=today,
            )
        assert exc_info.value.code == "service_dates_order_invalid"

    def test_desde_equals_hasta_valid(self):
        """fch_serv_desde == fch_serv_hasta (same day service) passes."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        validate_service_dates(
            concepto=2,
            fch_serv_desde=today,
            fch_serv_hasta=today,
            fch_vto_pago=today + timedelta(days=30),
            cbte_fch=today,
        )

    def test_vto_pago_before_cbte_fch_raises(self):
        """fch_vto_pago < cbte_fch raises ValidationError."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        with pytest.raises(ValidationError) as exc_info:
            validate_service_dates(
                concepto=2,
                fch_serv_desde=today - timedelta(days=30),
                fch_serv_hasta=today,
                fch_vto_pago=today - timedelta(days=1),
                cbte_fch=today,
            )
        assert exc_info.value.code == "vto_pago_before_cbte_fch"

    def test_vto_pago_equals_cbte_fch_valid(self):
        """fch_vto_pago == cbte_fch (same day payment) passes."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        validate_service_dates(
            concepto=2,
            fch_serv_desde=today - timedelta(days=30),
            fch_serv_hasta=today,
            fch_vto_pago=today,
            cbte_fch=today,
        )

    def test_concepto_default_to_1(self):
        """Concepto=1 (Productos) with explicit param and no dates passes."""
        from apps.facturacion.validators import validate_service_dates

        validate_service_dates(
            concepto=1,
            fch_serv_desde=None,
            fch_serv_hasta=None,
            fch_vto_pago=None,
        )

    def test_vto_pago_falls_back_to_fch_serv_desde(self):
        """When cbte_fch is absent, fch_vto_pago ordering check is skipped."""
        from apps.facturacion.validators import validate_service_dates

        today = date.today()
        validate_service_dates(
            concepto=2,
            fch_serv_desde=today - timedelta(days=30),
            fch_serv_hasta=today,
            fch_vto_pago=today,
        )


# ============================================================
# validate_tributos Tests
# ============================================================


@pytest.mark.unit
class TestValidateTributos:
    """
    Tests for validate_tributos -- Tributo element omission rule.

    Rule: If ImpTrib = 0, <Tributos> element MUST NOT be sent (omit entirely).
    If ImpTrib > 0, at least one tributo entry is required.
    Sum of tributo.importe must match imp_trib.
    """

    def test_zero_imp_trib_no_tributos_valid(self):
        """ImpTrib=0 with empty tributos list passes."""
        from apps.facturacion.validators import validate_tributos

        validate_tributos(imp_trib=Decimal("0.00"), tributo_list=[])

    def test_zero_imp_trib_with_tributos_raises(self):
        """ImpTrib=0 with tributos present raises ValidationError (must omit)."""
        from apps.facturacion.validators import validate_tributos

        tributos = [
            {"tributo_id": 1, "desc": "IIBB", "base_imp": Decimal("100.00"),
             "alic": Decimal("3.00"), "importe": Decimal("3.00")},
        ]
        with pytest.raises(ValidationError) as exc_info:
            validate_tributos(imp_trib=Decimal("0.00"), tributo_list=tributos)
        assert exc_info.value.code == "tributos_not_allowed"

    def test_nonzero_imp_trib_with_matching_tributos_valid(self):
        """ImpTrib > 0 with tributos summing correctly passes."""
        from apps.facturacion.validators import validate_tributos

        tributos = [
            {"tributo_id": 1, "desc": "IIBB", "base_imp": Decimal("100.00"),
             "alic": Decimal("3.50"), "importe": Decimal("3.50")},
        ]
        validate_tributos(imp_trib=Decimal("3.50"), tributo_list=tributos)

    def test_nonzero_imp_trib_empty_tributos_raises(self):
        """ImpTrib > 0 with no tributos raises ValidationError."""
        from apps.facturacion.validators import validate_tributos

        with pytest.raises(ValidationError) as exc_info:
            validate_tributos(imp_trib=Decimal("5.00"), tributo_list=[])
        assert exc_info.value.code == "tributos_required"

    def test_tributos_sum_mismatch_raises(self):
        """Sum of tributo.importe != imp_trib raises ValidationError."""
        from apps.facturacion.validators import validate_tributos

        tributos = [
            {"tributo_id": 1, "desc": "IIBB", "base_imp": Decimal("100.00"),
             "alic": Decimal("3.00"), "importe": Decimal("3.00")},
        ]
        # Sum = 3.00 but imp_trib = 10.00
        with pytest.raises(ValidationError) as exc_info:
            validate_tributos(imp_trib=Decimal("10.00"), tributo_list=tributos)
        assert exc_info.value.code == "tributo_sum_mismatch"

    def test_multiple_tributos_valid(self):
        """Multiple tributos summing correctly passes."""
        from apps.facturacion.validators import validate_tributos

        tributos = [
            {"tributo_id": 1, "desc": "IIBB CABA", "base_imp": Decimal("100.00"),
             "alic": Decimal("3.00"), "importe": Decimal("3.00")},
            {"tributo_id": 2, "desc": "IIBB PBA", "base_imp": Decimal("100.00"),
             "alic": Decimal("3.50"), "importe": Decimal("3.50")},
        ]
        validate_tributos(imp_trib=Decimal("6.50"), tributo_list=tributos)

    def test_missing_imp_trib_defaults_zero(self):
        """Explicit Decimal zero for imp_trib with empty tributos passes."""
        from apps.facturacion.validators import validate_tributos

        validate_tributos(imp_trib=Decimal("0.00"), tributo_list=[])

    def test_string_imp_trib_zero(self):
        """Integer-valued Decimal zero for imp_trib passes."""
        from apps.facturacion.validators import validate_tributos

        validate_tributos(imp_trib=Decimal("0"), tributo_list=[])


# ============================================================
# T045: CbtesAsoc Validation -- Type Compatibility & Requirements
# ============================================================


@pytest.mark.unit
class TestValidateCbtesAsoc:
    """T045: CbteAsoc type compatibility and requirement validation (no DB)."""

    def test_unknown_parent_cbte_tipo_raises(self):
        """Unknown CbteTipo code for the parent comprobante raises."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(cbte_tipo=999, cbtes_asoc_list=[])
        assert exc_info.value.code == "unknown_cbte_tipo"

    @pytest.mark.parametrize(
        "cbte_tipo", [3, 8, 13, 53], ids=["NC_A", "NC_B", "NC_C", "NC_M"]
    )
    def test_nc_requires_cbtes_asoc(self, cbte_tipo):
        """Nota de Credito types require at least one CbteAsoc entry."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(cbte_tipo=cbte_tipo, cbtes_asoc_list=[])
        assert exc_info.value.code == "cbtes_asoc_required"

    @pytest.mark.parametrize(
        "cbte_tipo", [2, 7, 12, 52], ids=["ND_A", "ND_B", "ND_C", "ND_M"]
    )
    def test_nd_requires_cbtes_asoc(self, cbte_tipo):
        """Nota de Debito types require at least one CbteAsoc entry."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(cbte_tipo=cbte_tipo, cbtes_asoc_list=[])
        assert exc_info.value.code == "cbtes_asoc_required"

    @pytest.mark.parametrize(
        "cbte_tipo", [1, 6, 11, 51], ids=["FA_A", "FA_B", "FA_C", "FA_M"]
    )
    def test_factura_rejects_cbtes_asoc(self, cbte_tipo):
        """Factura types must NOT have CbtesAsoc entries."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(
                cbte_tipo=cbte_tipo,
                cbtes_asoc_list=[{"tipo": cbte_tipo, "pto_vta": 1, "nro": 1}],
            )
        assert exc_info.value.code == "cbtes_asoc_not_allowed"

    @pytest.mark.parametrize(
        "cbte_tipo", [1, 6, 11, 51], ids=["FA_A", "FA_B", "FA_C", "FA_M"]
    )
    def test_factura_without_cbtes_asoc_passes(self, cbte_tipo):
        """Factura types with empty CbtesAsoc pass validation."""
        from apps.facturacion.validators import validate_cbtes_asoc

        result = validate_cbtes_asoc(cbte_tipo=cbte_tipo, cbtes_asoc_list=[])
        assert result == []

    def test_type_mismatch_raises(self):
        """Cross-type reference (NC A -> Factura B) raises ValidationError."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(
                cbte_tipo=3,  # NC A (letter A)
                cbtes_asoc_list=[
                    {"tipo": 6, "pto_vta": 1, "nro": 1},  # Factura B (letter B)
                ],
            )
        assert exc_info.value.code == "cbtes_asoc_type_mismatch"

    def test_type_mismatch_error_includes_letter_info(self):
        """Type mismatch error includes both letter types and ARCA error 202."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(
                cbte_tipo=3,  # NC A
                cbtes_asoc_list=[
                    {"tipo": 6, "pto_vta": 1, "nro": 1},  # Factura B
                ],
            )
        msg = exc_info.value.message
        assert "Type A" in msg
        assert "Type B" in msg
        assert "error 202" in msg

    def test_unknown_asoc_cbte_tipo_raises(self):
        """Unknown CbteTipo in a CbtesAsoc entry raises ValidationError."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(
                cbte_tipo=3,  # NC A (valid parent)
                cbtes_asoc_list=[
                    {"tipo": 999, "pto_vta": 1, "nro": 1},
                ],
            )
        assert exc_info.value.code == "unknown_asoc_cbte_tipo"

    def test_unknown_asoc_includes_entry_index(self):
        """Unknown asoc type error includes the CbtesAsoc entry index."""
        from apps.facturacion.validators import validate_cbtes_asoc

        with pytest.raises(ValidationError) as exc_info:
            validate_cbtes_asoc(
                cbte_tipo=3,
                cbtes_asoc_list=[
                    {"tipo": 999, "pto_vta": 1, "nro": 1},
                ],
            )
        assert "CbtesAsoc[0]" in exc_info.value.message


# ============================================================
# T045: CbtesAsoc Local Existence Check (requires database)
# ============================================================


@pytest.mark.django_db
class TestValidateCbtesAsocExistence:
    """T045: CbteAsoc local existence check with TenantBoundManager isolation."""

    def test_existing_comprobante_no_warning(self, comprobante_factory):
        """NC B referencing an existing Factura B in same tenant -> no warnings."""
        from apps.facturacion.validators import validate_cbtes_asoc

        factura = comprobante_factory(cbte_tipo=6)  # Factura B, auto-numbered

        warnings = validate_cbtes_asoc(
            cbte_tipo=8,  # NC B (same letter B)
            cbtes_asoc_list=[{
                "tipo": 6,
                "pto_vta": factura.punto_venta.numero,
                "nro": factura.cbte_nro,
            }],
        )
        assert warnings == []

    def test_nonexistent_comprobante_returns_warning(self, tenant_context):
        """Referencing a non-existent comprobante returns a soft warning."""
        from apps.facturacion.validators import validate_cbtes_asoc

        warnings = validate_cbtes_asoc(
            cbte_tipo=8,  # NC B
            cbtes_asoc_list=[{"tipo": 6, "pto_vta": 1, "nro": 99999}],
        )
        assert len(warnings) == 1
        assert "not found in local database" in warnings[0]
        assert "ARCA is the authority" in warnings[0]

    def test_mixed_existence_partial_warnings(self, comprobante_factory):
        """Multiple entries: existing -> no warning, missing -> one warning."""
        from apps.facturacion.validators import validate_cbtes_asoc

        factura = comprobante_factory(cbte_tipo=6)

        warnings = validate_cbtes_asoc(
            cbte_tipo=8,  # NC B
            cbtes_asoc_list=[
                {
                    "tipo": 6,
                    "pto_vta": factura.punto_venta.numero,
                    "nro": factura.cbte_nro,
                },
                {"tipo": 6, "pto_vta": 1, "nro": 88888},  # doesn't exist
            ],
        )
        assert len(warnings) == 1
        assert "CbtesAsoc[1]" in warnings[0]

    def test_warning_format_padded_numbers(self, tenant_context):
        """Warning message contains zero-padded pto_vta (5 digits) and nro (8 digits)."""
        from apps.facturacion.validators import validate_cbtes_asoc

        warnings = validate_cbtes_asoc(
            cbte_tipo=8,
            cbtes_asoc_list=[{"tipo": 6, "pto_vta": 5, "nro": 42}],
        )
        assert len(warnings) == 1
        assert "00005" in warnings[0]
        assert "00000042" in warnings[0]

    def test_cross_tenant_comprobante_not_visible(
        self, tenant_context, other_tenant_comprobante
    ):
        """Comprobante in different tenant is invisible via TenantBoundManager.

        other_tenant_comprobante: cbte_tipo=6, pto_vta=1, cbte_nro=1 in other tenant.
        From primary tenant context, this reference should not be found.
        """
        from apps.core.managers.tenant_bound import set_current_tenant_id

        from apps.facturacion.validators import validate_cbtes_asoc

        # Restore primary tenant context
        # (other_tenant_comprobante fixture clears tenant during setup)
        set_current_tenant_id(tenant_context.id)

        warnings = validate_cbtes_asoc(
            cbte_tipo=8,  # NC B (same letter B as tipo 6)
            cbtes_asoc_list=[{"tipo": 6, "pto_vta": 1, "nro": 1}],
        )
        assert len(warnings) == 1
        assert "not found in local database" in warnings[0]
