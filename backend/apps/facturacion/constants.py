"""
ARCA electronic invoicing constants and enumerations.

Defines all comprobante types, document types, IVA conditions,
concepts, and IVA rate codes as used by ARCA (ex-AFIP) WSFEv1.
"""

from django.db import models


# ============================================================
# Comprobante Types (CbteTipo)
# ============================================================

class CbteTipo(models.IntegerChoices):
    """
    ARCA comprobante type codes.

    Organized by letter (A/B/C/M) and document class (Factura/NC/ND).
    """

    # Type A — Responsable Inscripto → Responsable Inscripto
    FACTURA_A = 1, "Factura A"
    NOTA_DEBITO_A = 2, "Nota de Débito A"
    NOTA_CREDITO_A = 3, "Nota de Crédito A"

    # Type B — Responsable Inscripto → Consumidor Final / Monotributista / Exento
    FACTURA_B = 6, "Factura B"
    NOTA_DEBITO_B = 7, "Nota de Débito B"
    NOTA_CREDITO_B = 8, "Nota de Crédito B"

    # Type C — Monotributista / Exento → any
    FACTURA_C = 11, "Factura C"
    NOTA_DEBITO_C = 12, "Nota de Débito C"
    NOTA_CREDITO_C = 13, "Nota de Crédito C"

    # Type M — Responsable Inscripto (under observation) → Responsable Inscripto
    FACTURA_M = 51, "Factura M"
    NOTA_DEBITO_M = 52, "Nota de Débito M"
    NOTA_CREDITO_M = 53, "Nota de Crédito M"


# NC/ND codes for validation
NOTA_CREDITO_CODES = frozenset({
    CbteTipo.NOTA_CREDITO_A,
    CbteTipo.NOTA_CREDITO_B,
    CbteTipo.NOTA_CREDITO_C,
    CbteTipo.NOTA_CREDITO_M,
})

NOTA_DEBITO_CODES = frozenset({
    CbteTipo.NOTA_DEBITO_A,
    CbteTipo.NOTA_DEBITO_B,
    CbteTipo.NOTA_DEBITO_C,
    CbteTipo.NOTA_DEBITO_M,
})

FACTURA_CODES = frozenset({
    CbteTipo.FACTURA_A,
    CbteTipo.FACTURA_B,
    CbteTipo.FACTURA_C,
    CbteTipo.FACTURA_M,
})

# Codes that require CbtesAsoc (NC and ND)
CBTES_ASOC_REQUIRED_CODES = NOTA_CREDITO_CODES | NOTA_DEBITO_CODES

# Letter grouping for type compatibility validation (A→A, B→B, C→C, M→M)
CBTE_TIPO_LETTER = {
    CbteTipo.FACTURA_A: "A",
    CbteTipo.NOTA_DEBITO_A: "A",
    CbteTipo.NOTA_CREDITO_A: "A",
    CbteTipo.FACTURA_B: "B",
    CbteTipo.NOTA_DEBITO_B: "B",
    CbteTipo.NOTA_CREDITO_B: "B",
    CbteTipo.FACTURA_C: "C",
    CbteTipo.NOTA_DEBITO_C: "C",
    CbteTipo.NOTA_CREDITO_C: "C",
    CbteTipo.FACTURA_M: "M",
    CbteTipo.NOTA_DEBITO_M: "M",
    CbteTipo.NOTA_CREDITO_M: "M",
}


# ============================================================
# Document Types (DocTipo)
# ============================================================

class DocTipo(models.IntegerChoices):
    """Buyer document type codes."""

    CUIT = 80, "CUIT"
    CUIL = 86, "CUIL"
    CDI = 87, "CDI"
    LE = 89, "Libreta de Enrolamiento"
    LC = 90, "Libreta Cívica"
    CI_EXTRANJERA = 91, "CI Extranjera"
    EN_TRAMITE = 92, "En trámite"
    ACTA_NACIMIENTO = 93, "Acta de Nacimiento"
    CI_BS_AS = 95, "CI Buenos Aires"
    DNI = 96, "DNI"
    PASAPORTE = 94, "Pasaporte"
    SIN_IDENTIFICAR = 99, "Doc. (Otro) / Sin identificar"
    CI_POLICIA_FEDERAL = 0, "CI Policía Federal"


# ============================================================
# IVA Condition (CondicionIVA)
# ============================================================

class CondicionIVA(models.IntegerChoices):
    """Fiscal responsibility categories for IVA."""

    RESPONSABLE_INSCRIPTO = 1, "IVA Responsable Inscripto"
    EXENTO = 4, "IVA Sujeto Exento"
    CONSUMIDOR_FINAL = 5, "Consumidor Final"
    MONOTRIBUTISTA = 6, "Responsable Monotributo"
    SUJETO_NO_CATEGORIZADO = 7, "Sujeto No Categorizado"
    PROVEEDOR_EXTERIOR = 8, "Proveedor del Exterior"
    CLIENTE_EXTERIOR = 9, "Cliente del Exterior"
    LIBERADO = 10, "IVA Liberado – Ley Nº 19.640"
    MONOTRIBUTISTA_SOCIAL = 13, "Monotributista Social"


# ============================================================
# Concepto (Invoice concept type)
# ============================================================

class Concepto(models.IntegerChoices):
    """What the invoice covers."""

    PRODUCTOS = 1, "Productos"
    SERVICIOS = 2, "Servicios"
    PRODUCTOS_Y_SERVICIOS = 3, "Productos y Servicios"


# ============================================================
# IVA Rate Codes (AlicIvaId)
# ============================================================

class AlicIvaId(models.IntegerChoices):
    """ARCA IVA rate codes with corresponding percentages."""

    NO_GRAVADO = 1, "No Gravado"
    EXENTO = 2, "Exento"
    IVA_0 = 3, "0%"
    IVA_10_5 = 4, "10.5%"
    IVA_21 = 5, "21%"
    IVA_27 = 6, "27%"
    IVA_5 = 8, "5%"
    IVA_2_5 = 9, "2.5%"


# Mapping from AlicIvaId to actual percentage rate
ALIC_IVA_RATE = {
    AlicIvaId.NO_GRAVADO: 0,
    AlicIvaId.EXENTO: 0,
    AlicIvaId.IVA_0: 0,
    AlicIvaId.IVA_10_5: 10.5,
    AlicIvaId.IVA_21: 21,
    AlicIvaId.IVA_27: 27,
    AlicIvaId.IVA_5: 5,
    AlicIvaId.IVA_2_5: 2.5,
}


# ============================================================
# Comprobante Status
# ============================================================

class ComprobanteStatus(models.TextChoices):
    """Comprobante lifecycle status."""

    DRAFT = "DRAFT", "Borrador"
    VALIDANDO = "VALIDANDO", "Validando con ARCA"
    AUTORIZADO = "AUTORIZADO", "Autorizado (CAE otorgado)"
    OBSERVADO = "OBSERVADO", "Observado (CAE con advertencias)"
    RECHAZADO = "RECHAZADO", "Rechazado por ARCA"


# Immutable statuses — records with these statuses cannot be modified
IMMUTABLE_STATUSES = frozenset({
    ComprobanteStatus.AUTORIZADO,
    ComprobanteStatus.OBSERVADO,
})


# ============================================================
# CAEA Status
# ============================================================

class CAEAStatus(models.TextChoices):
    """CAEA lifecycle status."""

    ACTIVE = "ACTIVE", "Activo"
    REPORTED = "REPORTED", "Informado"
    REPORTED_NO_MOVEMENT = "REPORTED_NO_MOVEMENT", "Sin movimiento informado"
    EXPIRED = "EXPIRED", "Vencido"


# ============================================================
# PuntoDeVenta Types
# ============================================================

class PuntoDeVentaTipo(models.TextChoices):
    """Point of sale emission types."""

    ELECTRONIC = "electronic", "Electrónico"
    MANUAL = "manual", "Manual"


# ============================================================
# CbteTipo Resolution Matrix
# ============================================================


def resolver_tipo_comprobante(
    emitter_condition: int,
    receiver_condition: int,
    operation_type: str = "factura",
) -> int:
    """
    Resolve the CbteTipo code from emitter/receiver IVA conditions.

    Args:
        emitter_condition: Emitter CondicionIVA code.
        receiver_condition: Receiver CondicionIVA code.
        operation_type: One of 'factura', 'nota_credito', 'nota_debito'.

    Returns:
        CbteTipo integer code.

    Raises:
        ValueError: If emitter condition is invalid or combination unsupported.
    """
    # Determine the letter based on emitter → receiver
    ri = CondicionIVA.RESPONSABLE_INSCRIPTO
    cf = CondicionIVA.CONSUMIDOR_FINAL
    mono = CondicionIVA.MONOTRIBUTISTA
    exento = CondicionIVA.EXENTO

    if emitter_condition == ri:
        if receiver_condition == ri:
            letter = "A"
        elif receiver_condition in (cf, mono, exento):
            letter = "B"
        else:
            letter = "B"  # Default to B for other receiver types
    elif emitter_condition in (mono, exento):
        letter = "C"
    else:
        raise ValueError(
            f"Unsupported emitter CondicionIVA: {emitter_condition}. "
            f"Only RI ({ri}), Monotributista ({mono}), and Exento ({exento}) can emit."
        )

    # Map (letter, operation_type) → CbteTipo
    _RESOLUTION_MAP = {
        ("A", "factura"): CbteTipo.FACTURA_A,
        ("A", "nota_debito"): CbteTipo.NOTA_DEBITO_A,
        ("A", "nota_credito"): CbteTipo.NOTA_CREDITO_A,
        ("B", "factura"): CbteTipo.FACTURA_B,
        ("B", "nota_debito"): CbteTipo.NOTA_DEBITO_B,
        ("B", "nota_credito"): CbteTipo.NOTA_CREDITO_B,
        ("C", "factura"): CbteTipo.FACTURA_C,
        ("C", "nota_debito"): CbteTipo.NOTA_DEBITO_C,
        ("C", "nota_credito"): CbteTipo.NOTA_CREDITO_C,
    }

    key = (letter, operation_type)
    if key not in _RESOLUTION_MAP:
        raise ValueError(
            f"Invalid operation_type: {operation_type}. "
            f"Must be 'factura', 'nota_credito', or 'nota_debito'."
        )

    return _RESOLUTION_MAP[key]
