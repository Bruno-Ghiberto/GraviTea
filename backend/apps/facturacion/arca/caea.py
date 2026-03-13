"""
CAEAService — CAEA (Codigo de Autorizacion Electronico Anticipado) client.

Provides methods for CAEA offline invoicing operations via the WSFEv1 WSDL:
    - FECAEASolicitar: request a CAEA code for a punto de venta + period.
    - FECAEARegInformativo: batch-report comprobantes issued offline.
    - FECAEASinMovimientoInformar: report no activity for a CAEA period.

CAEA allows offline invoice issuance: the tenant pre-obtains a CAEA code,
prints it on comprobantes, and later reports them to ARCA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from zeep import Client
from zeep.exceptions import Fault as ZeepFault

from .exceptions import ARCARequestError
from .wsfe import WSFE_WSDL_PRODUCTION, WSFE_WSDL_TESTING
from ..metrics import track_soap_call

logger = logging.getLogger("facturacion.caea")


@dataclass(frozen=True)
class CAEAResult:
    """
    Result from a FECAEASolicitar call.

    Attributes:
        caea: 14-digit CAEA code.
        periodo: Billing period YYYYMM.
        orden: Fortnight order (1 or 2).
        fch_vig_desde: Validity start date YYYYMMDD.
        fch_vig_hasta: Validity end date YYYYMMDD.
        fch_tope_inf: Deadline to report comprobantes YYYYMMDD.
        observations: List of observation dicts from ARCA.
        errors: List of error dicts from ARCA.
    """

    caea: str
    periodo: str
    orden: int
    fch_vig_desde: str
    fch_vig_hasta: str
    fch_tope_inf: str
    observations: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class CAEAInformarResult:
    """
    Result from a FECAEARegInformativo call.

    Attributes:
        resultado: 'A' (approved) or 'R' (rejected) for the batch.
        processed: Number of comprobantes processed.
        rejected: Number of comprobantes rejected.
        observations: List of observation dicts.
        errors: List of error dicts.
    """

    resultado: str
    processed: int = 0
    rejected: int = 0
    observations: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


class CAEAService:
    """
    CAEA service for offline electronic invoicing.

    Communicates with ARCA via the WSFEv1 WSDL to manage CAEA lifecycle:
    solicitation, comprobante reporting, and no-movement declaration.

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
    # FECAEASolicitar
    # ------------------------------------------------------------------

    def solicitar_caea(
        self, pto_vta: int, periodo: str, orden: int
    ) -> CAEAResult:
        """
        Request a CAEA code for a punto de venta and period (FECAEASolicitar).

        The CAEA is valid for one fortnight of the billing period. Must be
        requested before the fortnight starts (5 days in advance).

        Args:
            pto_vta: Punto de venta number (must be CAEA-type).
            periodo: Billing period in YYYYMM format.
            orden: Fortnight order: 1 (days 1-15) or 2 (days 16-end).

        Returns:
            CAEAResult with the CAEA code and validity dates.

        Raises:
            ARCARequestError: If the SOAP call fails or ARCA returns errors.
        """
        try:
            with track_soap_call(
                operation="FECAEASolicitar", environment=self._environment
            ):
                response = self._client.service.FECAEASolicitar(
                    Auth=self._auth_dict(),
                    Periodo=int(periodo),
                    Orden=orden,
                    PtoVta=pto_vta,
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECAEASolicitar fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECAEASolicitar failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        return self._parse_solicitar_response(response)

    def _parse_solicitar_response(self, response: object) -> CAEAResult:
        """Parse FECAEASolicitar response into a CAEAResult."""
        self._check_response_errors(response, "FECAEASolicitar")

        result_get = response.ResultGet
        if result_get is None:
            raise ARCARequestError(
                message="FECAEASolicitar returned empty ResultGet.",
                code="CAEA_EMPTY_RESPONSE",
            )

        observations = []
        if hasattr(result_get, "Observaciones") and result_get.Observaciones:
            observations = [
                {"Code": str(obs.Code), "Msg": obs.Msg}
                for obs in result_get.Observaciones.Obs
            ]

        errors = []
        if response.Errors:
            errors = [
                {"Code": str(err.Code), "Msg": err.Msg}
                for err in response.Errors.Err
            ]

        return CAEAResult(
            caea=result_get.CAEA,
            periodo=str(result_get.Periodo),
            orden=result_get.Orden,
            fch_vig_desde=result_get.FchVigDesde,
            fch_vig_hasta=result_get.FchVigHasta,
            fch_tope_inf=result_get.FchTopeInf,
            observations=observations,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # FECAEARegInformativo
    # ------------------------------------------------------------------

    def informar_comprobantes(
        self, caea: str, comprobantes: list[dict]
    ) -> CAEAInformarResult:
        """
        Report comprobantes issued offline with a CAEA (FECAEARegInformativo).

        Each comprobante dict must include the same fields as FECAESolicitar
        plus the CAEA code. Comprobantes are reported in batch.

        Args:
            caea: 14-digit CAEA code used for the comprobantes.
            comprobantes: List of comprobante dicts. Required keys per item:
                cbte_tipo, punto_venta, concepto, doc_tipo, doc_nro,
                cbte_desde, cbte_hasta, cbte_fch, imp_total, imp_neto,
                imp_iva, imp_trib, imp_op_ex, imp_tot_conc, mon_id,
                mon_cotiz. Optional: alic_iva, tributos, cbtes_asoc.

        Returns:
            CAEAInformarResult with batch processing summary.

        Raises:
            ARCARequestError: If the SOAP call fails.
        """
        if not comprobantes:
            raise ARCARequestError(
                message="No comprobantes to report.",
                code="CAEA_EMPTY_BATCH",
            )

        # All comprobantes in a batch must share the same CbteTipo and PtoVta.
        first = comprobantes[0]
        fe_cab_req = {
            "CantReg": len(comprobantes),
            "PtoVta": first["punto_venta"],
            "CbteTipo": first["cbte_tipo"],
        }

        from .caea_engine import build_det_list

        det_list = build_det_list(comprobantes, caea, self.cuit)

        fe_det_req = {"FECAEADetRequest": det_list}

        try:
            with track_soap_call(
                operation="FECAEARegInformativo",
                environment=self._environment,
            ):
                response = self._client.service.FECAEARegInformativo(
                    Auth=self._auth_dict(),
                    FeCAEARegInfReq={
                        "FeCabReq": fe_cab_req,
                        "FeDetReq": fe_det_req,
                    },
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECAEARegInformativo fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECAEARegInformativo failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        return self._parse_informar_response(response)

    def _parse_informar_response(
        self, response: object
    ) -> CAEAInformarResult:
        """Parse FECAEARegInformativo response into CAEAInformarResult."""
        observations: list[dict] = []
        errors: list[dict] = []
        processed = 0
        rejected = 0

        if response.Errors:
            errors = [
                {"Code": str(err.Code), "Msg": err.Msg}
                for err in response.Errors.Err
            ]

        det_resp = response.FeDetResp
        if det_resp and det_resp.FECAEADetResponse:
            for det in det_resp.FECAEADetResponse:
                processed += 1
                if det.Resultado == "R":
                    rejected += 1
                if det.Observaciones:
                    for obs in det.Observaciones.Obs:
                        observations.append(
                            {"Code": str(obs.Code), "Msg": obs.Msg}
                        )

        resultado = "R" if rejected == processed and processed > 0 else "A"

        if rejected > 0:
            logger.warning(
                "FECAEARegInformativo: %d/%d comprobantes rejected. %s",
                rejected,
                processed,
                observations,
            )

        return CAEAInformarResult(
            resultado=resultado,
            processed=processed,
            rejected=rejected,
            observations=observations,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # FECAEASinMovimientoInformar
    # ------------------------------------------------------------------

    def informar_sin_movimiento(
        self, caea: str, pto_vta: int
    ) -> bool:
        """
        Report no activity for a CAEA period (FECAEASinMovimientoInformar).

        Must be called before the CAEA reporting deadline (fch_tope_inf)
        if no comprobantes were issued during the period.

        Args:
            caea: 14-digit CAEA code.
            pto_vta: Punto de venta number.

        Returns:
            True if the no-movement report was accepted.

        Raises:
            ARCARequestError: If the SOAP call fails or ARCA rejects.
        """
        try:
            with track_soap_call(
                operation="FECAEASinMovimientoInformar",
                environment=self._environment,
            ):
                response = self._client.service.FECAEASinMovimientoInformar(
                    Auth=self._auth_dict(),
                    CAEA=caea,
                    PtoVta=pto_vta,
                )
        except ZeepFault as exc:
            raise ARCARequestError(
                message=f"FECAEASinMovimientoInformar fault: {exc.message}",
                code="WSFE_SOAP_FAULT",
            ) from exc
        except Exception as exc:
            raise ARCARequestError(
                message=f"FECAEASinMovimientoInformar failed: {exc}",
                code="WSFE_REQUEST_ERROR",
            ) from exc

        self._check_response_errors(response, "FECAEASinMovimientoInformar")

        result = response.Resultado
        if result == "R":
            logger.warning("FECAEASinMovimientoInformar rejected for CAEA=%s", caea)
            raise ARCARequestError(
                message="No-movement report rejected by ARCA.",
                code="CAEA_SIN_MOV_REJECTED",
            )

        logger.info(
            "FECAEASinMovimientoInformar accepted for CAEA=%s PtoVta=%s",
            caea,
            pto_vta,
        )
        return True

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
