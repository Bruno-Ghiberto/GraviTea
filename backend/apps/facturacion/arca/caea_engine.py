"""CAEA Batch Builder dispatcher — Rust-accelerated det_list construction."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_USE_RUST: bool

try:
    from gravitea_rust import (
        build_caea_batch_request as _rust_build,
    )
    _USE_RUST = True
except (ImportError, OSError):
    _USE_RUST = False
    logger.warning(
        "gravitea_rust ARCA batch builder not available — using Python fallback"
    )

_RUST_BATCH_THRESHOLD = 10


def build_det_list(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Build the FECAEADetRequest list for a CAEA batch."""
    if _USE_RUST and len(comprobantes) > _RUST_BATCH_THRESHOLD:
        return _build_rust(comprobantes, caea, default_cuit)
    return _build_python(comprobantes, caea, default_cuit)


def _build_rust(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Rust-accelerated batch build (GIL released)."""
    comprobantes_json = json.dumps(comprobantes)
    result_json = _rust_build(comprobantes_json, caea, default_cuit)
    return json.loads(result_json)


def _build_python(
    comprobantes: list[dict[str, Any]],
    caea: str,
    default_cuit: str,
) -> list[dict[str, Any]]:
    """Python fallback — extracted from caea.py inner loop."""
    det_list = []
    for cbte in comprobantes:
        det: dict[str, Any] = {
            "Concepto": cbte["concepto"],
            "DocTipo": cbte["doc_tipo"],
            "DocNro": cbte["doc_nro"],
            "CbteDesde": cbte["cbte_desde"],
            "CbteHasta": cbte["cbte_hasta"],
            "CbteFch": cbte["cbte_fch"],
            "ImpTotal": float(cbte["imp_total"]),
            "ImpTotConc": float(cbte["imp_tot_conc"]),
            "ImpNeto": float(cbte["imp_neto"]),
            "ImpOpEx": float(cbte["imp_op_ex"]),
            "ImpTrib": float(cbte["imp_trib"]),
            "ImpIVA": float(cbte["imp_iva"]),
            "MonId": cbte.get("mon_id", "PES"),
            "MonCotiz": float(cbte.get("mon_cotiz", 1)),
            "CAEA": caea,
        }

        if cbte.get("concepto") in (2, 3):
            det["FchServDesde"] = cbte["fch_serv_desde"]
            det["FchServHasta"] = cbte["fch_serv_hasta"]
            det["FchVtoPago"] = cbte["fch_vto_pago"]

        alic_iva = cbte.get("alic_iva")
        if alic_iva:
            det["Iva"] = {
                "AlicIva": [
                    {
                        "Id": item["iva_id"],
                        "BaseImp": float(item["base_imp"]),
                        "Importe": float(item["importe"]),
                    }
                    for item in alic_iva
                ]
            }

        tributos = cbte.get("tributos")
        if tributos and float(cbte.get("imp_trib", 0)) > 0:
            det["Tributos"] = {
                "Tributo": [
                    {
                        "Id": item["tributo_id"],
                        "Desc": item["desc"],
                        "BaseImp": float(item["base_imp"]),
                        "Alic": float(item["alic"]),
                        "Importe": float(item["importe"]),
                    }
                    for item in tributos
                ]
            }

        cbtes_asoc = cbte.get("cbtes_asoc")
        if cbtes_asoc:
            det["CbtesAsoc"] = {
                "CbteAsoc": [
                    {
                        "Tipo": item["tipo"],
                        "PtoVta": item["pto_vta"],
                        "Nro": item["nro"],
                        "Cuit": item.get("cuit", default_cuit),
                    }
                    for item in cbtes_asoc
                ]
            }

        det_list.append(det)
    return det_list
