"""
T094: Invoice type determination tests.

Tests resolver_tipo_comprobante() which maps (emitter CondicionIVA,
receiver CondicionIVA, operation_type) → CbteTipo.

This is the core business rule for Argentine electronic invoicing:
    - RI → RI = Factura A
    - RI → CF/Mono/Exento = Factura B
    - Mono/Exento → Any = Factura C

Also tests SaleService._calculate_amounts for ARCA balance validation.
"""

from decimal import Decimal

import pytest

from apps.facturacion.constants import (
    CbteTipo,
    CondicionIVA,
    resolver_tipo_comprobante,
)


# ============================================================
# T094: resolver_tipo_comprobante — Factura type
# ============================================================


class TestResolverTipoComprobante:
    """Invoice type resolution from emitter/receiver IVA conditions."""

    # --- RI emitter ---

    @pytest.mark.unit
    def test_ri_to_ri_factura_a(self):
        """RI emitter → RI receiver = Factura A (type 1)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert result == CbteTipo.FACTURA_A

    @pytest.mark.unit
    def test_ri_to_cf_factura_b(self):
        """RI emitter → CF receiver = Factura B (type 6)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.CONSUMIDOR_FINAL,
        )
        assert result == CbteTipo.FACTURA_B

    @pytest.mark.unit
    def test_ri_to_mono_factura_b(self):
        """RI emitter → Monotributista receiver = Factura B (type 6)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.MONOTRIBUTISTA,
        )
        assert result == CbteTipo.FACTURA_B

    @pytest.mark.unit
    def test_ri_to_exento_factura_b(self):
        """RI emitter → Exento receiver = Factura B (type 6)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.EXENTO,
        )
        assert result == CbteTipo.FACTURA_B

    # --- Mono emitter ---

    @pytest.mark.unit
    def test_mono_emitter_factura_c(self):
        """Monotributista emitter → any receiver = Factura C (type 11)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.MONOTRIBUTISTA,
            receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert result == CbteTipo.FACTURA_C

    @pytest.mark.unit
    def test_mono_to_cf_factura_c(self):
        """Monotributista emitter → CF receiver = Factura C."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.MONOTRIBUTISTA,
            receiver_condition=CondicionIVA.CONSUMIDOR_FINAL,
        )
        assert result == CbteTipo.FACTURA_C

    # --- Exento emitter ---

    @pytest.mark.unit
    def test_exento_emitter_factura_c(self):
        """Exento emitter → any receiver = Factura C (type 11)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.EXENTO,
            receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert result == CbteTipo.FACTURA_C

    # --- Nota de crédito / débito ---

    @pytest.mark.unit
    def test_ri_to_ri_nota_credito_a(self):
        """RI → RI nota_credito = NC A (type 3)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            operation_type="nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_A

    @pytest.mark.unit
    def test_ri_to_cf_nota_debito_b(self):
        """RI → CF nota_debito = ND B (type 7 or equivalent)."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            receiver_condition=CondicionIVA.CONSUMIDOR_FINAL,
            operation_type="nota_debito",
        )
        assert result == CbteTipo.NOTA_DEBITO_B

    @pytest.mark.unit
    def test_mono_nota_credito_c(self):
        """Mono → any nota_credito = NC C."""
        result = resolver_tipo_comprobante(
            emitter_condition=CondicionIVA.MONOTRIBUTISTA,
            receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            operation_type="nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_C

    # --- Error cases ---

    @pytest.mark.unit
    def test_invalid_emitter_condition_raises(self):
        """CF cannot be an emitter — should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                emitter_condition=CondicionIVA.CONSUMIDOR_FINAL,
                receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
            )

    @pytest.mark.unit
    def test_invalid_operation_type_raises(self):
        """Invalid operation_type should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid operation_type"):
            resolver_tipo_comprobante(
                emitter_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
                receiver_condition=CondicionIVA.RESPONSABLE_INSCRIPTO,
                operation_type="recibo",
            )

    # --- Parametrized comprehensive matrix ---

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "emitter,receiver,expected",
        [
            (CondicionIVA.RESPONSABLE_INSCRIPTO, CondicionIVA.RESPONSABLE_INSCRIPTO, CbteTipo.FACTURA_A),
            (CondicionIVA.RESPONSABLE_INSCRIPTO, CondicionIVA.CONSUMIDOR_FINAL, CbteTipo.FACTURA_B),
            (CondicionIVA.RESPONSABLE_INSCRIPTO, CondicionIVA.MONOTRIBUTISTA, CbteTipo.FACTURA_B),
            (CondicionIVA.RESPONSABLE_INSCRIPTO, CondicionIVA.EXENTO, CbteTipo.FACTURA_B),
            (CondicionIVA.MONOTRIBUTISTA, CondicionIVA.RESPONSABLE_INSCRIPTO, CbteTipo.FACTURA_C),
            (CondicionIVA.MONOTRIBUTISTA, CondicionIVA.CONSUMIDOR_FINAL, CbteTipo.FACTURA_C),
            (CondicionIVA.EXENTO, CondicionIVA.RESPONSABLE_INSCRIPTO, CbteTipo.FACTURA_C),
            (CondicionIVA.EXENTO, CondicionIVA.CONSUMIDOR_FINAL, CbteTipo.FACTURA_C),
        ],
        ids=[
            "RI→RI=A",
            "RI→CF=B",
            "RI→Mono=B",
            "RI→Exento=B",
            "Mono→RI=C",
            "Mono→CF=C",
            "Exento→RI=C",
            "Exento→CF=C",
        ],
    )
    def test_factura_matrix(self, emitter, receiver, expected):
        """Full matrix of emitter→receiver invoice type combinations."""
        result = resolver_tipo_comprobante(
            emitter_condition=emitter,
            receiver_condition=receiver,
        )
        assert result == expected


# ============================================================
# T094: SaleService._calculate_amounts
# ============================================================


class TestCalculateAmounts:
    """ARCA amount mapping and balance validation."""

    @pytest.mark.unit
    def test_amounts_balance_check(self):
        """imp_total == imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc."""
        from apps.ventas.services.sale_service import SaleService

        # Create minimal mock order and items
        from unittest.mock import MagicMock

        order = MagicMock()
        order.subtotal = Decimal("800.000")
        order.total_iva = Decimal("168.000")
        order.total_amount = Decimal("968.000")

        items = []  # Items not used directly in _calculate_amounts
        receptor_condicion_iva = CondicionIVA.RESPONSABLE_INSCRIPTO

        result = SaleService._calculate_amounts(
            order, items, receptor_condicion_iva
        )

        assert result["imp_neto"] == Decimal("800.000")
        assert result["imp_iva"] == Decimal("168.000")
        assert result["imp_trib"] == Decimal("0.000")
        assert result["imp_op_ex"] == Decimal("0.000")
        assert result["imp_tot_conc"] == Decimal("0.000")
        assert result["imp_total"] == Decimal("968.000")

        # Verify balance equation
        total = (
            result["imp_neto"]
            + result["imp_iva"]
            + result["imp_trib"]
            + result["imp_op_ex"]
            + result["imp_tot_conc"]
        )
        assert result["imp_total"] == total
