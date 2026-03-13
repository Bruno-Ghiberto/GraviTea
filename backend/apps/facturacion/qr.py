"""
Fiscal QR code generation for ARCA electronic invoices.

Generates the mandatory QR code URL per ARCA RG 4291 for authorized
comprobantes. The QR encodes fiscal data as a base64url JSON payload
pointing to ARCA's verification endpoint.

Usage:
    url = generate_fiscal_qr_data(comprobante)
    # Render `url` as QR image on the printed/PDF comprobante.
"""

from __future__ import annotations

import base64
import json

from .constants import IMMUTABLE_STATUSES

# ARCA fiscal QR verification endpoint.
QR_BASE_URL = "https://www.afip.gob.ar/fe/qr/"


def _safe_int(value: str | None) -> int:
    """Safely convert doc_nro to int, returning 0 for non-numeric values."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def generate_fiscal_qr_data(comprobante) -> str:
    """
    Generate the fiscal QR code URL for an authorized comprobante.

    Builds a JSON payload with all required fiscal fields, base64url-encodes
    it, and returns the full ARCA verification URL.

    Args:
        comprobante: An authorized/observed Comprobante instance with a
            valid CAE.

    Returns:
        Full URL string for QR code rendering.

    Raises:
        ValueError: If the comprobante is not authorized (no CAE).
    """
    if comprobante.status not in IMMUTABLE_STATUSES:
        raise ValueError(
            f"Cannot generate fiscal QR for comprobante with status "
            f"'{comprobante.status}'. Only AUTORIZADO/OBSERVADO "
            f"comprobantes have a CAE."
        )

    if not comprobante.cae:
        raise ValueError(
            "Cannot generate fiscal QR: comprobante has no CAE."
        )

    qr_data = {
        "ver": 1,
        "fecha": comprobante.cbte_fch.strftime("%Y-%m-%d"),
        "cuit": int(comprobante.emitter_cuit.replace("-", "")),
        "ptoVta": comprobante.punto_venta.numero,
        "tipoCmp": comprobante.cbte_tipo,
        "nroCmp": comprobante.cbte_nro,
        "importe": float(comprobante.imp_total),
        "moneda": comprobante.mon_id,
        "ctz": float(comprobante.mon_cotiz),
        "tipoDocRec": comprobante.doc_tipo,
        "nroDocRec": _safe_int(comprobante.doc_nro),
        "tipoCodAut": "A" if comprobante.caea_id else "E",
        "codAut": int(comprobante.cae),
    }

    payload = base64.urlsafe_b64encode(
        json.dumps(qr_data, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    return f"{QR_BASE_URL}?p={payload}"
