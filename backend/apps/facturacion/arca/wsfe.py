"""
WSFEv1 (Web Service de Factura Electronica v1) client.

Provides methods for:
    - FECompUltimoAutorizado: get last authorized comprobante number.
    - FECAESolicitar: request CAE authorization for a comprobante.
    - FECompConsultar: query an existing comprobante (recovery).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from zeep import Client
from zeep.exceptions import Fault as ZeepFault

from .exceptions import ARCAComprobanteRejected, ARCARequestError
from ..metrics import record_cae_result, track_soap_call

logger = logging.getLogger("facturacion.wsfe")

# WSDL URLs for WSFEv1.
WSFE_WSDL_TESTING = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
WSFE_WSDL_PRODUCTION = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"


@dataclass(frozen=True)
class CAEResult:
    """
    Result from a FECAESolicitar call.

    Attributes:
        resultado: 'A' (approved), 'O' (observed), or 'R' (rejected).
        cae: 14-digit CAE code (present for A and O).
        cae_fch_vto: CAE expiration date string YYYYMMDD.
        cbte_nro: Authorized comprobante number.
        observations: List of observation dicts from ARCA.
        errors: List of error dicts from ARCA.
    """

    resultado: str
    cae: str | None = None
    cae_fch_vto: str | None = None
    cbte_nro: int = 0
    observations: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


class WSFEv1Client:
    """
    WSFEv1 client for electronic invoice authorization.

    Requires a valid Token+Sign pair from WSAA authentication.
    All methods communicate with ARCA via SOAP using zeep.

    Args:
        token: WSAA authentication token.
        sign: WSAA authentication signature.
        cuit: Effective CUIT for the invoicing operation.
        is_production: Use production endpoint if True.
    """

    def __init__(
        self,
        token: str,
        sign: str,
        cuit: str,
        *,
        is_production: bool = False,
    ) -> None:
        self.token = token
        self.sign = sign
        self.cuit = cuit
        self._environment = "production" if is_production else "homologacion"
        wsdl_url = WSFE_WSDL_PRODUCTION if is_production else WSFE_WSDL_TESTING
        self._client = Client(wsdl_url)

    def _auth_dict(self) -> dict:
        """Auth block required by all WSFEv1 methods."""
        return {"Token": self.token, "Sign": self.sign, "Cuit": self.cuit}

    # ------------------------------------------------------------------
    # FECompUltimoAutorizado
    # ------------------------------------------------------------------

    def get_ultimo_comprobante(
        self, pto_vta: int, cbte_tipo: int
    ) -> int:
        """
        Get the last authorized comprobante number (FECompUltimoAutorizado).

        This is a read-only query. Does not authorize or modify anything.

        Args:
            pto_vta: Punto de venta number.
            cbte_tipo: Comprobante type code.

        Returns:
            Last authorized CbteNro (0 if none exist).

        Raises:
            ARCARequestError: If the SOAP call fails.
        """
        try:
            with track_soap_call(operation="FECompUltimoAutorizado", environment=self._environment):
                response = self._client.service.FECompUltimoAutorizado(
                    Auth=self._auth_dict(),
                    PtoVta=pto_vta,
                    CbteTipo=cbte_tipo,
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECompUltimoAutorizado fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECompUltimoAutorizado failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        self._check_response_errors(response, "FECompUltimoAutorizado")
        return response.CbteNro

    # ------------------------------------------------------------------
    # FECAESolicitar
    # ------------------------------------------------------------------

    def solicitar_cae(self, data: dict) -> CAEResult:
        """
        Request CAE authorization for a comprobante (FECAESolicitar).

        Builds the FECAEReq structure from the data dict and handles
        all three possible outcomes: A (approved), O (observed), R (rejected).

        Args:
            data: Dict with comprobante fields. Required keys:
                punto_venta, cbte_tipo, concepto, doc_tipo, doc_nro,
                cbte_nro, cbte_fch, imp_total, imp_neto, imp_iva,
                imp_trib, imp_op_ex, imp_tot_conc, mon_id, mon_cotiz.
                Optional: fch_serv_desde, fch_serv_hasta, fch_vto_pago,
                alic_iva (list), tributos (list), cbtes_asoc (list).

        Returns:
            CAEResult with authorization details.

        Raises:
            ARCAComprobanteRejected: If ARCA rejects the comprobante (R).
            ARCARequestError: If the SOAP call itself fails.
        """
        fe_cab_req = {
            "CantReg": 1,
            "PtoVta": data["punto_venta"],
            "CbteTipo": data["cbte_tipo"],
        }

        det = {
            "Concepto": data["concepto"],
            "DocTipo": data["doc_tipo"],
            "DocNro": data["doc_nro"],
            "CbteDesde": data["cbte_nro"],
            "CbteHasta": data["cbte_nro"],
            "CbteFch": data["cbte_fch"],
            "ImpTotal": float(data["imp_total"]),
            "ImpTotConc": float(data["imp_tot_conc"]),
            "ImpNeto": float(data["imp_neto"]),
            "ImpOpEx": float(data["imp_op_ex"]),
            "ImpTrib": float(data["imp_trib"]),
            "ImpIVA": float(data["imp_iva"]),
            "MonId": data.get("mon_id", "PES"),
            "MonCotiz": float(data.get("mon_cotiz", 1)),
        }

        # Service dates — only for Concepto 2 or 3.
        if data.get("concepto") in (2, 3):
            det["FchServDesde"] = data["fch_serv_desde"]
            det["FchServHasta"] = data["fch_serv_hasta"]
            det["FchVtoPago"] = data["fch_vto_pago"]

        # IVA breakdown — omit element entirely if empty.
        alic_iva = data.get("alic_iva")
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

        # Tributos — omit element entirely if ImpTrib=0 or empty.
        tributos = data.get("tributos")
        if tributos and Decimal(str(data["imp_trib"])) > 0:
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

        # Associated comprobantes (NC/ND references).
        cbtes_asoc = data.get("cbtes_asoc")
        if cbtes_asoc:
            det["CbtesAsoc"] = {
                "CbteAsoc": [
                    {
                        "Tipo": item["tipo"],
                        "PtoVta": item["pto_vta"],
                        "Nro": item["nro"],
                        "Cuit": item.get("cuit", self.cuit),
                    }
                    for item in cbtes_asoc
                ]
            }

        fe_det_req = {"FECAEDetRequest": [det]}

        try:
            with track_soap_call(operation="FECAESolicitar", environment=self._environment):
                response = self._client.service.FECAESolicitar(
                    Auth=self._auth_dict(),
                    FeCAEReq={"FeCabReq": fe_cab_req, "FeDetReq": fe_det_req},
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECAESolicitar fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECAESolicitar failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        return self._parse_cae_response(response, cbte_tipo=data["cbte_tipo"])

    def _parse_cae_response(self, response: object, cbte_tipo: int) -> CAEResult:
        """
        Parse FECAESolicitar response into a CAEResult.

        Handles Resultado: A (approved), O (observed), R (rejected).
        For R, raises ARCAComprobanteRejected. For A and O, returns
        the CAEResult with any observations attached.
        """
        det = response.FeDetResp.FECAEDetResponse[0]

        observations = []
        if det.Observaciones:
            observations = [
                {"Code": str(obs.Code), "Msg": obs.Msg}
                for obs in det.Observaciones.Obs
            ]

        errors = []
        if response.Errors:
            errors = [
                {"Code": str(err.Code), "Msg": err.Msg}
                for err in response.Errors.Err
            ]

        result = CAEResult(
            resultado=det.Resultado,
            cae=det.CAE if det.CAE else None,
            cae_fch_vto=det.CAEFchVto if det.CAEFchVto else None,
            cbte_nro=det.CbteDesde,
            observations=observations,
            errors=errors,
        )

        _result_map = {"A": "approved", "O": "observed", "R": "rejected"}
        record_cae_result(
            result=_result_map.get(det.Resultado, "unknown"),
            cbte_tipo=cbte_tipo,
        )

        if det.Resultado == "R":
            logger.warning(
                "CAE rejected for CbteNro=%s: %s", det.CbteDesde, errors or observations
            )
            raise ARCAComprobanteRejected(
                message="Comprobante rejected by ARCA.",
                code="CAE_REJECTED",
                observations=observations,
            )

        if det.Resultado == "O":
            logger.warning(
                "CAE approved with observations for CbteNro=%s: %s",
                det.CbteDesde,
                observations,
            )

        return result

    # ------------------------------------------------------------------
    # FECompConsultar
    # ------------------------------------------------------------------

    def consultar_comprobante(
        self, pto_vta: int, cbte_tipo: int, cbte_nro: int
    ) -> dict | None:
        """
        Query an existing comprobante (FECompConsultar).

        Used for recovery after network failures: check if ARCA
        authorized the comprobante despite the timeout.

        Args:
            pto_vta: Punto de venta number.
            cbte_tipo: Comprobante type code.
            cbte_nro: Comprobante number to query.

        Returns:
            Dict with comprobante details if found, None if not.

        Raises:
            ARCARequestError: If the SOAP call fails.
        """
        try:
            with track_soap_call(operation="FECompConsultar", environment=self._environment):
                response = self._client.service.FECompConsultar(
                    Auth=self._auth_dict(),
                    FeCompConsReq={
                        "CbteTipo": cbte_tipo,
                        "CbteNro": cbte_nro,
                        "PtoVta": pto_vta,
                    },
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECompConsultar fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECompConsultar failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        if response.Errors:
            # Comprobante not found is not an error per se.
            return None

        result_get = response.ResultGet
        if result_get is None:
            return None

        return {
            "cbte_nro": result_get.CbteDesde,
            "cbte_fch": result_get.CbteFch,
            "imp_total": result_get.ImpTotal,
            "resultado": result_get.Resultado,
            "cae": result_get.CodAutorizacion,
            "cae_fch_vto": result_get.FchVto,
            "emision_tipo": result_get.EmisionTipo,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_response_errors(response: object, method_name: str) -> None:
        """Check for ARCA-level errors in the response and raise if found."""
        if response.Errors:
            err = response.Errors.Err[0]
            raise ARCARequestError(
                message=f"{method_name} error: [{err.Code}] {err.Msg}",
                code=str(err.Code),
            )
