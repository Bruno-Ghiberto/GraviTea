"""
Unit tests for facturacion constants and CbteTipo resolution.

Tests the resolver_tipo_comprobante function covering:
- All valid emitter → receiver CondicionIVA combinations
- All operation types (factura, nota_credito, nota_debito)
- Invalid emitter conditions raising ValueError
- Invalid operation types raising ValueError
- Enum integrity and frozenset groupings
"""

import pytest

from apps.facturacion.constants import (
    ALIC_IVA_RATE,
    CBTE_TIPO_LETTER,
    CBTES_ASOC_REQUIRED_CODES,
    AlicIvaId,
    CAEAStatus,
    CbteTipo,
    ComprobanteStatus,
    Concepto,
    CondicionIVA,
    DocTipo,
    FACTURA_CODES,
    IMMUTABLE_STATUSES,
    NOTA_CREDITO_CODES,
    NOTA_DEBITO_CODES,
    PuntoDeVentaTipo,
    resolver_tipo_comprobante,
)


# ============================================================
# CbteTipo Resolution: RI Emitter
# ============================================================


@pytest.mark.unit
class TestCbteTipoResolutionRI:
    """RI (Responsable Inscripto) emitter → various receivers."""

    def test_ri_to_ri_factura(self):
        """RI → RI = Factura A (code 1)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_A

    def test_ri_to_ri_nota_credito(self):
        """RI → RI = Nota de Crédito A (code 3)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_A

    def test_ri_to_ri_nota_debito(self):
        """RI → RI = Nota de Débito A (code 2)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "nota_debito",
        )
        assert result == CbteTipo.NOTA_DEBITO_A

    def test_ri_to_cf_factura(self):
        """RI → Consumidor Final = Factura B (code 6)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.CONSUMIDOR_FINAL,
            "factura",
        )
        assert result == CbteTipo.FACTURA_B

    def test_ri_to_cf_nota_credito(self):
        """RI → Consumidor Final = Nota de Crédito B (code 8)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.CONSUMIDOR_FINAL,
            "nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_B

    def test_ri_to_cf_nota_debito(self):
        """RI → Consumidor Final = Nota de Débito B (code 7)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.CONSUMIDOR_FINAL,
            "nota_debito",
        )
        assert result == CbteTipo.NOTA_DEBITO_B

    def test_ri_to_monotributista_factura(self):
        """RI → Monotributista = Factura B (code 6)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.MONOTRIBUTISTA,
            "factura",
        )
        assert result == CbteTipo.FACTURA_B

    def test_ri_to_exento_factura(self):
        """RI → Exento = Factura B (code 6)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.EXENTO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_B

    def test_ri_to_other_defaults_to_b(self):
        """RI → other receiver types default to B."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.SUJETO_NO_CATEGORIZADO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_B

    def test_ri_to_cliente_exterior_factura(self):
        """RI → Cliente del Exterior = Factura B."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.CLIENTE_EXTERIOR,
            "factura",
        )
        assert result == CbteTipo.FACTURA_B


# ============================================================
# CbteTipo Resolution: Monotributista Emitter
# ============================================================


@pytest.mark.unit
class TestCbteTipoResolutionMono:
    """Monotributista emitter → always Type C."""

    def test_mono_to_ri_factura(self):
        """Monotributista → RI = Factura C (code 11)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_mono_to_cf_factura(self):
        """Monotributista → CF = Factura C (code 11)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.CONSUMIDOR_FINAL,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_mono_to_mono_factura(self):
        """Monotributista → Monotributista = Factura C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.MONOTRIBUTISTA,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_mono_to_exento_factura(self):
        """Monotributista → Exento = Factura C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.EXENTO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_mono_nota_credito(self):
        """Monotributista → any = Nota de Crédito C (code 13)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_C

    def test_mono_nota_debito(self):
        """Monotributista → any = Nota de Débito C (code 12)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTISTA,
            CondicionIVA.CONSUMIDOR_FINAL,
            "nota_debito",
        )
        assert result == CbteTipo.NOTA_DEBITO_C


# ============================================================
# CbteTipo Resolution: Exento Emitter
# ============================================================


@pytest.mark.unit
class TestCbteTipoResolutionExento:
    """Exento emitter → always Type C."""

    def test_exento_to_ri_factura(self):
        """Exento → RI = Factura C (code 11)."""
        result = resolver_tipo_comprobante(
            CondicionIVA.EXENTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_exento_to_cf_factura(self):
        """Exento → CF = Factura C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.EXENTO,
            CondicionIVA.CONSUMIDOR_FINAL,
            "factura",
        )
        assert result == CbteTipo.FACTURA_C

    def test_exento_nota_credito(self):
        """Exento → any = Nota de Crédito C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.EXENTO,
            CondicionIVA.EXENTO,
            "nota_credito",
        )
        assert result == CbteTipo.NOTA_CREDITO_C

    def test_exento_nota_debito(self):
        """Exento → any = Nota de Débito C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.EXENTO,
            CondicionIVA.MONOTRIBUTISTA,
            "nota_debito",
        )
        assert result == CbteTipo.NOTA_DEBITO_C


# ============================================================
# CbteTipo Resolution: Error Cases
# ============================================================


@pytest.mark.unit
class TestCbteTipoResolutionErrors:
    """Invalid emitter conditions and operation types."""

    def test_invalid_emitter_consumidor_final(self):
        """Consumidor Final cannot emit invoices."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.CONSUMIDOR_FINAL,
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                "factura",
            )

    def test_invalid_emitter_sujeto_no_categorizado(self):
        """Sujeto No Categorizado cannot emit."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.SUJETO_NO_CATEGORIZADO,
                CondicionIVA.CONSUMIDOR_FINAL,
                "factura",
            )

    def test_invalid_emitter_proveedor_exterior(self):
        """Proveedor del Exterior cannot emit."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.PROVEEDOR_EXTERIOR,
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                "factura",
            )

    def test_invalid_emitter_cliente_exterior(self):
        """Cliente del Exterior cannot emit."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.CLIENTE_EXTERIOR,
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                "factura",
            )

    def test_invalid_emitter_liberado(self):
        """IVA Liberado cannot emit."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.LIBERADO,
                CondicionIVA.CONSUMIDOR_FINAL,
                "factura",
            )

    def test_invalid_emitter_monotributista_social(self):
        """Monotributista Social cannot emit (not in valid emitters list)."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(
                CondicionIVA.MONOTRIBUTISTA_SOCIAL,
                CondicionIVA.CONSUMIDOR_FINAL,
                "factura",
            )

    def test_invalid_operation_type(self):
        """Invalid operation_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid operation_type"):
            resolver_tipo_comprobante(
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                "recibo",
            )

    def test_empty_operation_type(self):
        """Empty operation_type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid operation_type"):
            resolver_tipo_comprobante(
                CondicionIVA.RESPONSABLE_INSCRIPTO,
                CondicionIVA.CONSUMIDOR_FINAL,
                "",
            )

    def test_invalid_emitter_raw_integer(self):
        """Raw integer not in valid emitters raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported emitter CondicionIVA"):
            resolver_tipo_comprobante(999, CondicionIVA.CONSUMIDOR_FINAL, "factura")


# ============================================================
# Enum Integrity Tests
# ============================================================


@pytest.mark.unit
class TestEnumIntegrity:
    """Verify enum values match ARCA specification."""

    def test_cbte_tipo_factura_codes(self):
        """Factura codes: A=1, B=6, C=11, M=51."""
        assert CbteTipo.FACTURA_A == 1
        assert CbteTipo.FACTURA_B == 6
        assert CbteTipo.FACTURA_C == 11
        assert CbteTipo.FACTURA_M == 51

    def test_cbte_tipo_nc_codes(self):
        """NC codes: A=3, B=8, C=13, M=53."""
        assert CbteTipo.NOTA_CREDITO_A == 3
        assert CbteTipo.NOTA_CREDITO_B == 8
        assert CbteTipo.NOTA_CREDITO_C == 13
        assert CbteTipo.NOTA_CREDITO_M == 53

    def test_cbte_tipo_nd_codes(self):
        """ND codes: A=2, B=7, C=12, M=52."""
        assert CbteTipo.NOTA_DEBITO_A == 2
        assert CbteTipo.NOTA_DEBITO_B == 7
        assert CbteTipo.NOTA_DEBITO_C == 12
        assert CbteTipo.NOTA_DEBITO_M == 52

    def test_cbte_tipo_has_12_members(self):
        """CbteTipo has exactly 12 members (A/B/C/M x F/NC/ND)."""
        assert len(CbteTipo) == 12

    def test_doc_tipo_common_codes(self):
        """DocTipo common codes: CUIT=80, DNI=96."""
        assert DocTipo.CUIT == 80
        assert DocTipo.DNI == 96
        assert DocTipo.SIN_IDENTIFICAR == 99

    def test_condicion_iva_codes(self):
        """CondicionIVA key codes."""
        assert CondicionIVA.RESPONSABLE_INSCRIPTO == 1
        assert CondicionIVA.EXENTO == 4
        assert CondicionIVA.CONSUMIDOR_FINAL == 5
        assert CondicionIVA.MONOTRIBUTISTA == 6

    def test_concepto_codes(self):
        """Concepto: 1=Products, 2=Services, 3=Both."""
        assert Concepto.PRODUCTOS == 1
        assert Concepto.SERVICIOS == 2
        assert Concepto.PRODUCTOS_Y_SERVICIOS == 3
        assert len(Concepto) == 3

    def test_alic_iva_id_codes(self):
        """AlicIvaId key codes: 0%=3, 10.5%=4, 21%=5, 27%=6."""
        assert AlicIvaId.IVA_0 == 3
        assert AlicIvaId.IVA_10_5 == 4
        assert AlicIvaId.IVA_21 == 5
        assert AlicIvaId.IVA_27 == 6
        assert AlicIvaId.IVA_5 == 8
        assert AlicIvaId.IVA_2_5 == 9

    def test_alic_iva_rate_mapping(self):
        """ALIC_IVA_RATE maps codes to correct percentages."""
        assert ALIC_IVA_RATE[AlicIvaId.IVA_21] == 21
        assert ALIC_IVA_RATE[AlicIvaId.IVA_10_5] == 10.5
        assert ALIC_IVA_RATE[AlicIvaId.IVA_27] == 27
        assert ALIC_IVA_RATE[AlicIvaId.IVA_5] == 5
        assert ALIC_IVA_RATE[AlicIvaId.IVA_2_5] == 2.5
        assert ALIC_IVA_RATE[AlicIvaId.EXENTO] == 0

    def test_comprobante_status_values(self):
        """ComprobanteStatus has correct string values."""
        assert ComprobanteStatus.DRAFT == "DRAFT"
        assert ComprobanteStatus.VALIDANDO == "VALIDANDO"
        assert ComprobanteStatus.AUTORIZADO == "AUTORIZADO"
        assert ComprobanteStatus.OBSERVADO == "OBSERVADO"
        assert ComprobanteStatus.RECHAZADO == "RECHAZADO"

    def test_caea_status_values(self):
        """CAEAStatus has correct string values."""
        assert CAEAStatus.ACTIVE == "ACTIVE"
        assert CAEAStatus.REPORTED == "REPORTED"
        assert CAEAStatus.REPORTED_NO_MOVEMENT == "REPORTED_NO_MOVEMENT"
        assert CAEAStatus.EXPIRED == "EXPIRED"

    def test_punto_venta_tipo_values(self):
        """PuntoDeVentaTipo choices."""
        assert PuntoDeVentaTipo.ELECTRONIC == "electronic"
        assert PuntoDeVentaTipo.MANUAL == "manual"


# ============================================================
# Frozenset Grouping Tests
# ============================================================


@pytest.mark.unit
class TestCodeGroupings:
    """Verify code groupings are correct and complete."""

    def test_factura_codes_contains_all_facturas(self):
        """FACTURA_CODES contains exactly codes 1, 6, 11, 51."""
        assert FACTURA_CODES == frozenset({1, 6, 11, 51})

    def test_nota_credito_codes_contains_all_nc(self):
        """NOTA_CREDITO_CODES contains exactly codes 3, 8, 13, 53."""
        assert NOTA_CREDITO_CODES == frozenset({3, 8, 13, 53})

    def test_nota_debito_codes_contains_all_nd(self):
        """NOTA_DEBITO_CODES contains exactly codes 2, 7, 12, 52."""
        assert NOTA_DEBITO_CODES == frozenset({2, 7, 12, 52})

    def test_cbtes_asoc_required_is_nc_plus_nd(self):
        """CBTES_ASOC_REQUIRED_CODES = NC + ND codes."""
        assert CBTES_ASOC_REQUIRED_CODES == NOTA_CREDITO_CODES | NOTA_DEBITO_CODES
        assert len(CBTES_ASOC_REQUIRED_CODES) == 8  # 4 NC + 4 ND

    def test_factura_codes_no_overlap_with_nc_nd(self):
        """Factura codes do not overlap with NC or ND codes."""
        assert FACTURA_CODES.isdisjoint(NOTA_CREDITO_CODES)
        assert FACTURA_CODES.isdisjoint(NOTA_DEBITO_CODES)

    def test_all_codes_covered_by_groupings(self):
        """All 12 CbteTipo values are covered by the three groupings."""
        all_grouped = FACTURA_CODES | NOTA_CREDITO_CODES | NOTA_DEBITO_CODES
        all_values = frozenset(ct.value for ct in CbteTipo)
        assert all_grouped == all_values

    def test_cbte_tipo_letter_complete(self):
        """CBTE_TIPO_LETTER maps all 12 CbteTipo values."""
        assert len(CBTE_TIPO_LETTER) == 12
        for ct in CbteTipo:
            assert ct in CBTE_TIPO_LETTER

    def test_cbte_tipo_letter_values(self):
        """CBTE_TIPO_LETTER maps to correct letters."""
        assert CBTE_TIPO_LETTER[CbteTipo.FACTURA_A] == "A"
        assert CBTE_TIPO_LETTER[CbteTipo.FACTURA_B] == "B"
        assert CBTE_TIPO_LETTER[CbteTipo.FACTURA_C] == "C"
        assert CBTE_TIPO_LETTER[CbteTipo.FACTURA_M] == "M"
        # NC/ND share the same letter as their Factura
        assert CBTE_TIPO_LETTER[CbteTipo.NOTA_CREDITO_A] == "A"
        assert CBTE_TIPO_LETTER[CbteTipo.NOTA_DEBITO_B] == "B"

    def test_immutable_statuses_contains_autorizado_observado(self):
        """IMMUTABLE_STATUSES = {AUTORIZADO, OBSERVADO}."""
        assert IMMUTABLE_STATUSES == frozenset({
            ComprobanteStatus.AUTORIZADO,
            ComprobanteStatus.OBSERVADO,
        })

    def test_immutable_statuses_excludes_mutable(self):
        """DRAFT, VALIDANDO, RECHAZADO are NOT immutable."""
        assert ComprobanteStatus.DRAFT not in IMMUTABLE_STATUSES
        assert ComprobanteStatus.VALIDANDO not in IMMUTABLE_STATUSES
        assert ComprobanteStatus.RECHAZADO not in IMMUTABLE_STATUSES
