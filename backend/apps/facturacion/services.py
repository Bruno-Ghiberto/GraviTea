"""
Invoice service for ARCA electronic invoicing.

Supports two authorization modes:

CAE (online):
    auth → ultimo → save DRAFT → VALIDANDO → submit → AUTORIZADO/RECHAZADO.

CAEA (offline):
    auth → ultimo → find active CAEA → save DRAFT with caea FK.
    Comprobante stays DRAFT until batch-reported via FECAEARegInformativo.

Uses @transaction.atomic + select_for_update on PuntoDeVenta to prevent
concurrent CbteNro conflicts.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from .arca import ARCAClient
from .arca.exceptions import ARCAComprobanteRejected, ARCARequestError
from .arca.wsfe import WSFEv1Client
from .constants import CAEAStatus, ComprobanteStatus
from .models import CAEA, AlicIva, CbteAsoc, Comprobante, PuntoDeVenta, Tributo

logger = logging.getLogger("facturacion.services")


class InvoiceService:
    """
    Service for issuing electronic comprobantes via ARCA.

    Handles the complete lifecycle from DRAFT creation through
    CAE authorization, including nested AlicIva/Tributo/CbteAsoc rows.
    """

    def __init__(self) -> None:
        self._arca_client = ARCAClient()

    def issue_comprobante(
        self,
        *,
        tenant_id: str,
        validated_data: dict[str, Any],
        is_production: bool = False,
    ) -> Comprobante:
        """
        Issue a comprobante and request CAE authorization from ARCA.

        Full transactional flow:
            1. Authenticate via WSAA (cached).
            2. Query last authorized CbteNro (FECompUltimoAutorizado).
            3. Save Comprobante as DRAFT with next CbteNro.
            4. Create nested AlicIva, Tributo, CbteAsoc rows.
            5. Set status to VALIDANDO.
            6. Submit to ARCA (FECAESolicitar).
            7. On A/O: update CAE fields, set AUTORIZADO/OBSERVADO.
            8. On R: set RECHAZADO, store errors, re-raise.

        Uses select_for_update on PuntoDeVenta to serialize concurrent
        requests for the same punto_venta + cbte_tipo combination.

        Args:
            tenant_id: UUID of the tenant.
            validated_data: Dict from ComprobanteEmitirSerializer.validated_data.
            is_production: True for production ARCA endpoints.

        Returns:
            The authorized Comprobante instance.

        Raises:
            ARCAAuthError: If WSAA authentication fails.
            ARCAComprobanteRejected: If ARCA rejects the comprobante.
            ARCARequestError: If the SOAP call itself fails.
        """
        return self._issue_with_transaction(
            tenant_id=tenant_id,
            validated_data=validated_data,
            is_production=is_production,
        )

    def authorize_comprobante(
        self,
        *,
        comprobante: Comprobante,
        is_production: bool = False,
    ) -> Comprobante:
        """
        Authorize an existing DRAFT Comprobante via ARCA.

        Unlike issue_comprobante() which creates a new Comprobante,
        this method takes an existing DRAFT (e.g. from SaleService.confirm_sale()),
        assigns it a CbteNro, submits to ARCA, and updates it in-place.

        Flow:
            1. Authenticate via WSAA (cached).
            2. Lock PuntoDeVenta, get next CbteNro.
            3. Update existing Comprobante with CbteNro, set VALIDANDO.
            4. Submit to ARCA (FECAESolicitar).
            5. Update with CAE fields or rejection errors.

        Args:
            comprobante: An existing DRAFT, RECHAZADO, or VALIDANDO Comprobante.
            is_production: True for production ARCA endpoints.

        Returns:
            The same Comprobante instance, updated with authorization result.
            If timeout recovery fails, returns with status=VALIDANDO (caller
            should treat as timeout-pending and retry later).

        Raises:
            ValueError: If comprobante is not in an authorizable status.
            ARCAComprobanteRejected: If ARCA rejects the comprobante.
            ARCAComprobanteRejected: If ARCA rejects the comprobante.
            ARCARequestError: If the SOAP call fails.
        """
        if comprobante.status not in (
            ComprobanteStatus.DRAFT,
            ComprobanteStatus.RECHAZADO,
        ):
            raise ValueError(
                f"Cannot authorize comprobante in status {comprobante.status}. "
                f"Only DRAFT or RECHAZADO comprobantes can be authorized."
            )

        return self._authorize_existing_with_transaction(
            comprobante=comprobante,
            is_production=is_production,
        )

    @transaction.atomic
    def _authorize_existing_with_transaction(
        self,
        *,
        comprobante: Comprobante,
        is_production: bool,
    ) -> Comprobante:
        """Atomic transaction wrapper for authorizing an existing DRAFT."""
        tenant_id = str(comprobante.tenant_id)

        # ── Step 1: Authenticate via WSAA ──
        ctx = self._arca_client.get_auth_context(
            tenant_id, is_production=is_production
        )

        # ── Step 2: Lock PuntoDeVenta to serialize CbteNro allocation ──
        pto_vta = PuntoDeVenta.all_objects.select_for_update().get(
            pk=comprobante.punto_venta_id, tenant_id=tenant_id
        )
        cbte_tipo = comprobante.cbte_tipo

        # ── Step 3: Get last authorized CbteNro from ARCA ──
        wsfe = WSFEv1Client(
            token=ctx.token,
            sign=ctx.sign,
            cuit=ctx.cuit,
            is_production=ctx.is_production,
        )
        ultimo_nro = wsfe.get_ultimo_comprobante(
            pto_vta=pto_vta.numero, cbte_tipo=cbte_tipo
        )
        next_nro = ultimo_nro + 1

        logger.info(
            "Authorizing existing comprobante: tenant=%s pto_vta=%s cbte_tipo=%s nro=%s",
            tenant_id,
            pto_vta.numero,
            cbte_tipo,
            next_nro,
        )

        # ── Step 3b: Check for active CAEA (offline mode) ──
        active_caea = self._find_active_caea(
            tenant_id=tenant_id, punto_venta=pto_vta
        )
        if active_caea is not None:
            # CAEA offline: update existing comprobante with CAEA data
            comprobante.cbte_nro = next_nro
            comprobante.caea = active_caea
            comprobante.cae = active_caea.caea_code
            comprobante.cae_fch_vto = active_caea.fch_vig_hasta
            comprobante.emitter_cuit = ctx.cuit
            comprobante.save()

            logger.info(
                "Comprobante CAEA DRAFT (existing): tenant=%s nro=%s caea=%s",
                tenant_id,
                next_nro,
                active_caea.caea_code,
            )
            return comprobante

        # ── Step 4: Update existing Comprobante with CbteNro ──
        # T059: Clear stale rejection data on retry
        if comprobante.status == ComprobanteStatus.RECHAZADO:
            comprobante.arca_errors = None
            comprobante.arca_response = None

        comprobante.cbte_nro = next_nro
        comprobante.emitter_cuit = ctx.cuit
        comprobante.status = ComprobanteStatus.VALIDANDO
        comprobante.save()

        # ── Step 5: Build ARCA request and submit ──
        validated_data = self._comprobante_to_validated_data(comprobante)
        arca_data = self._build_arca_request(
            validated_data=validated_data,
            pto_vta_numero=pto_vta.numero,
            cbte_nro=next_nro,
            cuit=ctx.cuit,
        )

        try:
            cae_result = wsfe.solicitar_cae(arca_data)
        except ARCAComprobanteRejected as exc:
            comprobante.status = ComprobanteStatus.RECHAZADO
            comprobante.arca_errors = {
                "observations": exc.observations,
                "code": exc.code,
                "message": exc.message,
            }
            comprobante.save()
            logger.warning(
                "Comprobante RECHAZADO (existing): tenant=%s nro=%s reason=%s",
                tenant_id,
                next_nro,
                exc,
            )
            raise
        except ARCARequestError as exc:
            logger.warning(
                "ARCA request failed for existing comprobante, attempting recovery: "
                "tenant=%s nro=%s error=%s",
                tenant_id,
                next_nro,
                exc,
            )
            recovered = self._recover_from_timeout(
                wsfe=wsfe,
                comprobante=comprobante,
                pto_vta_numero=pto_vta.numero,
                cbte_tipo=cbte_tipo,
                cbte_nro=next_nro,
            )
            if recovered:
                return comprobante

            # Recovery failed — mark as RECHAZADO and re-raise
            comprobante.status = ComprobanteStatus.RECHAZADO
            comprobante.arca_errors = {
                "code": "timeout_unrecovered",
                "message": f"Request failed, recovery inconclusive: {exc.message}",
            }
            comprobante.save()
            logger.warning(
                "Timeout unrecovered, set RECHAZADO: tenant=%s nro=%s",
                tenant_id,
                next_nro,
            )
            raise

        # ── Step 6: Approved or Observed ──
        if cae_result.resultado == "O":
            comprobante.status = ComprobanteStatus.OBSERVADO
        else:
            comprobante.status = ComprobanteStatus.AUTORIZADO

        comprobante.cae = cae_result.cae
        comprobante.cae_fch_vto = cae_result.cae_fch_vto
        comprobante.arca_response = asdict(cae_result)
        comprobante.save()

        logger.info(
            "Comprobante %s (existing): tenant=%s nro=%s cae=%s",
            comprobante.status,
            tenant_id,
            next_nro,
            cae_result.cae,
        )

        return comprobante

    @staticmethod
    def _comprobante_to_validated_data(comprobante: Comprobante) -> dict[str, Any]:
        """
        Convert an existing Comprobante to a validated_data dict
        compatible with _build_arca_request().
        """
        data: dict[str, Any] = {
            "punto_venta": str(comprobante.punto_venta_id),
            "cbte_tipo": comprobante.cbte_tipo,
            "concepto": comprobante.concepto,
            "doc_tipo": comprobante.doc_tipo,
            "doc_nro": comprobante.doc_nro,
            "cbte_fch": comprobante.cbte_fch,
            "imp_total": comprobante.imp_total,
            "imp_neto": comprobante.imp_neto,
            "imp_iva": comprobante.imp_iva,
            "imp_trib": comprobante.imp_trib,
            "imp_op_ex": comprobante.imp_op_ex,
            "imp_tot_conc": comprobante.imp_tot_conc,
            "mon_id": comprobante.mon_id,
            "mon_cotiz": comprobante.mon_cotiz,
            "emitter_condicion_iva": comprobante.emitter_condicion_iva,
            "receptor_condicion_iva": comprobante.receptor_condicion_iva,
        }

        if comprobante.fch_serv_desde:
            data["fch_serv_desde"] = comprobante.fch_serv_desde
        if comprobante.fch_serv_hasta:
            data["fch_serv_hasta"] = comprobante.fch_serv_hasta
        if comprobante.fch_vto_pago:
            data["fch_vto_pago"] = comprobante.fch_vto_pago

        # Include AlicIva rows
        alic_iva = list(comprobante.aliciva_set.all())
        if alic_iva:
            data["alic_iva"] = [
                {
                    "iva_id": row.iva_id,
                    "base_imp": row.base_imp,
                    "importe": row.importe,
                }
                for row in alic_iva
            ]

        # Include Tributo rows
        tributos = list(comprobante.tributo_set.all())
        if tributos:
            data["tributos"] = [
                {
                    "tributo_id": row.tributo_id,
                    "desc": row.desc,
                    "base_imp": row.base_imp,
                    "alic": row.alic,
                    "importe": row.importe,
                }
                for row in tributos
            ]

        # Include CbteAsoc rows
        cbtes_asoc = list(comprobante.cbteasoc_set.all())
        if cbtes_asoc:
            data["cbtes_asoc"] = [
                {
                    "tipo": row.tipo,
                    "pto_vta": row.pto_vta,
                    "nro": row.nro,
                    "cuit": row.cuit,
                }
                for row in cbtes_asoc
            ]

        return data

    @transaction.atomic
    def _issue_with_transaction(
        self,
        *,
        tenant_id: str,
        validated_data: dict[str, Any],
        is_production: bool,
    ) -> Comprobante:
        """Atomic transaction wrapper for the full issuance flow."""

        # ── Step 1: Authenticate via WSAA ──
        ctx = self._arca_client.get_auth_context(
            tenant_id, is_production=is_production
        )

        # ── Step 2: Lock PuntoDeVenta to serialize CbteNro allocation ──
        punto_venta_id = validated_data["punto_venta"]
        pto_vta = PuntoDeVenta.all_objects.select_for_update().get(
            pk=punto_venta_id, tenant_id=tenant_id
        )
        cbte_tipo = validated_data["cbte_tipo"]

        # ── Step 3: Get last authorized CbteNro from ARCA ──
        wsfe = WSFEv1Client(
            token=ctx.token,
            sign=ctx.sign,
            cuit=ctx.cuit,
            is_production=ctx.is_production,
        )
        ultimo_nro = wsfe.get_ultimo_comprobante(
            pto_vta=pto_vta.numero, cbte_tipo=cbte_tipo
        )
        next_nro = ultimo_nro + 1

        logger.info(
            "Issuing comprobante: tenant=%s pto_vta=%s cbte_tipo=%s nro=%s",
            tenant_id,
            pto_vta.numero,
            cbte_tipo,
            next_nro,
        )

        # ── Step 3b: Check for active CAEA (offline mode) ──
        active_caea = self._find_active_caea(
            tenant_id=tenant_id, punto_venta=pto_vta
        )
        if active_caea is not None:
            return self._issue_caea_mode(
                tenant_id=tenant_id,
                validated_data=validated_data,
                pto_vta=pto_vta,
                cbte_tipo=cbte_tipo,
                cbte_nro=next_nro,
                caea=active_caea,
                cuit=ctx.cuit,
            )

        # ── Step 4: Create Comprobante as DRAFT (CAE online mode) ──
        comprobante = Comprobante(
            tenant_id=tenant_id,
            punto_venta=pto_vta,
            cbte_tipo=cbte_tipo,
            cbte_nro=next_nro,
            concepto=validated_data["concepto"],
            doc_tipo=validated_data["doc_tipo"],
            doc_nro=validated_data["doc_nro"],
            cbte_fch=validated_data["cbte_fch"],
            fch_serv_desde=validated_data.get("fch_serv_desde"),
            fch_serv_hasta=validated_data.get("fch_serv_hasta"),
            fch_vto_pago=validated_data.get("fch_vto_pago"),
            imp_total=validated_data["imp_total"],
            imp_neto=validated_data["imp_neto"],
            imp_iva=validated_data["imp_iva"],
            imp_trib=validated_data["imp_trib"],
            imp_op_ex=validated_data["imp_op_ex"],
            imp_tot_conc=validated_data["imp_tot_conc"],
            mon_id=validated_data.get("mon_id", "PES"),
            mon_cotiz=validated_data.get("mon_cotiz", 1),
            emitter_cuit=ctx.cuit,
            emitter_condicion_iva=validated_data["emitter_condicion_iva"],
            receptor_condicion_iva=validated_data["receptor_condicion_iva"],
            status=ComprobanteStatus.DRAFT,
        )
        comprobante.save()

        # ── Step 5: Create nested rows ──
        self._create_nested_rows(comprobante, validated_data)

        # ── Step 6: Set VALIDANDO ──
        comprobante.status = ComprobanteStatus.VALIDANDO
        comprobante.save()

        # ── Step 7: Build ARCA request data and submit ──
        arca_data = self._build_arca_request(
            validated_data=validated_data,
            pto_vta_numero=pto_vta.numero,
            cbte_nro=next_nro,
            cuit=ctx.cuit,
        )

        try:
            cae_result = wsfe.solicitar_cae(arca_data)
        except ARCAComprobanteRejected as exc:
            # ── Step 8b: Rejected ──
            comprobante.status = ComprobanteStatus.RECHAZADO
            comprobante.arca_errors = {
                "observations": exc.observations,
                "code": exc.code,
                "message": exc.message,
            }
            comprobante.save()
            logger.warning(
                "Comprobante RECHAZADO: tenant=%s nro=%s reason=%s",
                tenant_id,
                next_nro,
                exc,
            )
            raise
        except ARCARequestError as exc:
            # ── Step 8c: Network/SOAP failure — attempt recovery ──
            logger.warning(
                "ARCA request failed, attempting recovery: tenant=%s nro=%s error=%s",
                tenant_id,
                next_nro,
                exc,
            )
            recovered = self._recover_from_timeout(
                wsfe=wsfe,
                comprobante=comprobante,
                pto_vta_numero=pto_vta.numero,
                cbte_tipo=cbte_tipo,
                cbte_nro=next_nro,
            )
            if recovered:
                return comprobante

            # Recovery failed — mark as RECHAZADO
            comprobante.status = ComprobanteStatus.RECHAZADO
            comprobante.arca_errors = {
                "code": exc.code,
                "message": exc.message,
            }
            comprobante.save()
            logger.error(
                "Recovery failed, comprobante RECHAZADO: tenant=%s nro=%s",
                tenant_id,
                next_nro,
            )
            raise

        # ── Step 8a: Approved or Observed ──
        if cae_result.resultado == "O":
            comprobante.status = ComprobanteStatus.OBSERVADO
        else:
            comprobante.status = ComprobanteStatus.AUTORIZADO

        comprobante.cae = cae_result.cae
        comprobante.cae_fch_vto = cae_result.cae_fch_vto
        comprobante.arca_response = asdict(cae_result)
        comprobante.save()

        logger.info(
            "Comprobante %s: tenant=%s nro=%s cae=%s",
            comprobante.status,
            tenant_id,
            next_nro,
            cae_result.cae,
        )

        return comprobante

    @staticmethod
    def _create_nested_rows(
        comprobante: Comprobante, validated_data: dict[str, Any]
    ) -> None:
        """Bulk-create AlicIva, Tributo, and CbteAsoc rows."""
        alic_iva_data = validated_data.get("alic_iva", [])
        if alic_iva_data:
            AlicIva.objects.bulk_create([
                AlicIva(
                    comprobante=comprobante,
                    iva_id=item["iva_id"],
                    base_imp=item["base_imp"],
                    importe=item["importe"],
                )
                for item in alic_iva_data
            ])

        tributos_data = validated_data.get("tributos", [])
        if tributos_data:
            Tributo.objects.bulk_create([
                Tributo(
                    comprobante=comprobante,
                    tributo_id=item["tributo_id"],
                    desc=item["desc"],
                    base_imp=item["base_imp"],
                    alic=item["alic"],
                    importe=item["importe"],
                )
                for item in tributos_data
            ])

        cbtes_asoc_data = validated_data.get("cbtes_asoc", [])
        if cbtes_asoc_data:
            CbteAsoc.objects.bulk_create([
                CbteAsoc(
                    comprobante=comprobante,
                    tipo=item["tipo"],
                    pto_vta=item["pto_vta"],
                    nro=item["nro"],
                    cuit=item.get("cuit"),
                )
                for item in cbtes_asoc_data
            ])

    @staticmethod
    def _build_arca_request(
        *,
        validated_data: dict[str, Any],
        pto_vta_numero: int,
        cbte_nro: int,
        cuit: str,
    ) -> dict[str, Any]:
        """
        Build the dict expected by WSFEv1Client.solicitar_cae().

        Translates serializer field names to the ARCA request format.
        Dates are formatted as YYYYMMDD strings per ARCA spec.
        """
        data: dict[str, Any] = {
            "punto_venta": pto_vta_numero,
            "cbte_tipo": validated_data["cbte_tipo"],
            "concepto": validated_data["concepto"],
            "doc_tipo": validated_data["doc_tipo"],
            "doc_nro": validated_data["doc_nro"],
            "cbte_nro": cbte_nro,
            "cbte_fch": validated_data["cbte_fch"].strftime("%Y%m%d"),
            "imp_total": validated_data["imp_total"],
            "imp_neto": validated_data["imp_neto"],
            "imp_iva": validated_data["imp_iva"],
            "imp_trib": validated_data["imp_trib"],
            "imp_op_ex": validated_data["imp_op_ex"],
            "imp_tot_conc": validated_data["imp_tot_conc"],
            "mon_id": validated_data.get("mon_id", "PES"),
            "mon_cotiz": validated_data.get("mon_cotiz", 1),
        }

        # Service dates — only for Concepto 2 or 3.
        if validated_data["concepto"] in (2, 3):
            data["fch_serv_desde"] = validated_data["fch_serv_desde"].strftime(
                "%Y%m%d"
            )
            data["fch_serv_hasta"] = validated_data["fch_serv_hasta"].strftime(
                "%Y%m%d"
            )
            data["fch_vto_pago"] = validated_data["fch_vto_pago"].strftime(
                "%Y%m%d"
            )

        # IVA breakdown
        alic_iva = validated_data.get("alic_iva", [])
        if alic_iva:
            data["alic_iva"] = [
                {
                    "iva_id": item["iva_id"],
                    "base_imp": item["base_imp"],
                    "importe": item["importe"],
                }
                for item in alic_iva
            ]

        # Tributos
        tributos = validated_data.get("tributos", [])
        if tributos:
            data["tributos"] = [
                {
                    "tributo_id": item["tributo_id"],
                    "desc": item["desc"],
                    "base_imp": item["base_imp"],
                    "alic": item["alic"],
                    "importe": item["importe"],
                }
                for item in tributos
            ]

        # Associated comprobantes
        cbtes_asoc = validated_data.get("cbtes_asoc", [])
        if cbtes_asoc:
            data["cbtes_asoc"] = [
                {
                    "tipo": item["tipo"],
                    "pto_vta": item["pto_vta"],
                    "nro": item["nro"],
                    "cuit": item.get("cuit", cuit),
                }
                for item in cbtes_asoc
            ]

        return data

    @staticmethod
    def _recover_from_timeout(
        *,
        wsfe: WSFEv1Client,
        comprobante: Comprobante,
        pto_vta_numero: int,
        cbte_tipo: int,
        cbte_nro: int,
    ) -> bool:
        """
        Attempt recovery after a network timeout on FECAESolicitar.

        When ARCA may have processed the request despite the timeout:
            1. FECompUltimoAutorizado: check if ultimo >= our cbte_nro.
            2. FECompConsultar: retrieve the comprobante details and CAE.
            3. If authorized on ARCA side, update local record.

        Args:
            wsfe: Authenticated WSFEv1Client instance.
            comprobante: The local Comprobante record in VALIDANDO state.
            pto_vta_numero: Punto de venta number.
            cbte_tipo: CbteTipo code.
            cbte_nro: The CbteNro we attempted to authorize.

        Returns:
            True if recovery succeeded (comprobante updated), False otherwise.
        """
        try:
            ultimo = wsfe.get_ultimo_comprobante(
                pto_vta=pto_vta_numero, cbte_tipo=cbte_tipo
            )
        except ARCARequestError:
            logger.error(
                "Recovery: FECompUltimoAutorizado also failed for CbteNro=%s",
                cbte_nro,
            )
            return False

        if ultimo < cbte_nro:
            logger.info(
                "Recovery: ultimo=%s < cbte_nro=%s — ARCA did not process the request",
                ultimo,
                cbte_nro,
            )
            return False

        # ARCA's ultimo >= our cbte_nro — it may have been authorized.
        try:
            result = wsfe.consultar_comprobante(
                pto_vta=pto_vta_numero, cbte_tipo=cbte_tipo, cbte_nro=cbte_nro
            )
        except ARCARequestError:
            logger.error(
                "Recovery: FECompConsultar also failed for CbteNro=%s",
                cbte_nro,
            )
            return False

        if result is None:
            logger.warning(
                "Recovery: FECompConsultar returned None for CbteNro=%s",
                cbte_nro,
            )
            return False

        # Check if ARCA actually authorized it.
        arca_resultado = result.get("resultado")
        cae = result.get("cae")

        if not cae or arca_resultado not in ("A", "O"):
            logger.warning(
                "Recovery: CbteNro=%s exists on ARCA but resultado=%s, cae=%s",
                cbte_nro,
                arca_resultado,
                cae,
            )
            return False

        # Success — update local record with recovered data.
        if arca_resultado == "O":
            comprobante.status = ComprobanteStatus.OBSERVADO
        else:
            comprobante.status = ComprobanteStatus.AUTORIZADO

        comprobante.cae = cae
        comprobante.cae_fch_vto = result.get("cae_fch_vto")
        comprobante.arca_response = {
            "recovered": True,
            "resultado": arca_resultado,
            "cae": cae,
            "cae_fch_vto": result.get("cae_fch_vto"),
            "cbte_nro": cbte_nro,
            "imp_total": str(result.get("imp_total", "")),
        }
        comprobante.save()

        logger.info(
            "Recovery SUCCESS: CbteNro=%s recovered as %s with CAE=%s",
            cbte_nro,
            comprobante.status,
            cae,
        )
        return True

    # ------------------------------------------------------------------
    # CAEA offline mode
    # ------------------------------------------------------------------

    @staticmethod
    def _find_active_caea(
        *, tenant_id: str, punto_venta: PuntoDeVenta
    ) -> CAEA | None:
        """
        Find an active CAEA for the punto_venta in the current period.

        Computes the current period (YYYYMM) and fortnight order (1 or 2)
        from today's date, then queries for a matching ACTIVE CAEA.

        Returns:
            The CAEA instance if found, or None.
        """
        today = date.today()
        periodo = today.strftime("%Y%m")
        orden = 1 if today.day <= 15 else 2

        return (
            CAEA.all_objects.filter(
                tenant_id=tenant_id,
                punto_venta=punto_venta,
                periodo=periodo,
                orden=orden,
                status=CAEAStatus.ACTIVE,
            )
            .first()
        )

    def _issue_caea_mode(
        self,
        *,
        tenant_id: str,
        validated_data: dict[str, Any],
        pto_vta: PuntoDeVenta,
        cbte_tipo: int,
        cbte_nro: int,
        caea: CAEA,
        cuit: str,
    ) -> Comprobante:
        """
        Issue a comprobante in CAEA offline mode.

        The comprobante is saved as DRAFT with the CAEA FK set.
        No FECAESolicitar call is made — the comprobante will be
        batch-reported to ARCA later via FECAEARegInformativo.

        The `cae` field stores the CAEA code so that it can be
        printed on the comprobante and QR code immediately.

        Args:
            tenant_id: UUID of the tenant.
            validated_data: Dict from ComprobanteEmitirSerializer.validated_data.
            pto_vta: Locked PuntoDeVenta instance.
            cbte_tipo: CbteTipo code.
            cbte_nro: Next comprobante number.
            caea: The active CAEA instance.
            cuit: Emitter CUIT from auth context.

        Returns:
            The DRAFT Comprobante instance.
        """
        comprobante = Comprobante(
            tenant_id=tenant_id,
            punto_venta=pto_vta,
            cbte_tipo=cbte_tipo,
            cbte_nro=cbte_nro,
            concepto=validated_data["concepto"],
            doc_tipo=validated_data["doc_tipo"],
            doc_nro=validated_data["doc_nro"],
            cbte_fch=validated_data["cbte_fch"],
            fch_serv_desde=validated_data.get("fch_serv_desde"),
            fch_serv_hasta=validated_data.get("fch_serv_hasta"),
            fch_vto_pago=validated_data.get("fch_vto_pago"),
            imp_total=validated_data["imp_total"],
            imp_neto=validated_data["imp_neto"],
            imp_iva=validated_data["imp_iva"],
            imp_trib=validated_data["imp_trib"],
            imp_op_ex=validated_data["imp_op_ex"],
            imp_tot_conc=validated_data["imp_tot_conc"],
            mon_id=validated_data.get("mon_id", "PES"),
            mon_cotiz=validated_data.get("mon_cotiz", 1),
            emitter_cuit=cuit,
            emitter_condicion_iva=validated_data["emitter_condicion_iva"],
            receptor_condicion_iva=validated_data["receptor_condicion_iva"],
            status=ComprobanteStatus.DRAFT,
            caea=caea,
            cae=caea.caea_code,
            cae_fch_vto=caea.fch_vig_hasta,
        )
        comprobante.save()

        self._create_nested_rows(comprobante, validated_data)

        logger.info(
            "Comprobante CAEA DRAFT: tenant=%s pto_vta=%s nro=%s caea=%s",
            tenant_id,
            pto_vta.numero,
            cbte_nro,
            caea.caea_code,
        )

        return comprobante

    # ------------------------------------------------------------------
    # Stale VALIDANDO recovery
    # ------------------------------------------------------------------

    def recover_stale_comprobantes(
        self,
        *,
        stale_threshold_minutes: int = 5,
        is_production: bool = False,
    ) -> dict[str, int]:
        """
        Recover comprobantes stuck in VALIDANDO state.

        Finds comprobantes older than the threshold and attempts to recover
        each one by querying ARCA via FECompConsultar.

        Intended to be called by a Celery periodic task or management command.

        Args:
            stale_threshold_minutes: Minutes after which VALIDANDO is stale.
            is_production: Use production ARCA endpoints.

        Returns:
            Dict with counts: recovered, failed, total.
        """
        cutoff = timezone.now() - timedelta(minutes=stale_threshold_minutes)
        stale_qs = Comprobante.all_objects.filter(
            status=ComprobanteStatus.VALIDANDO,
            created_at__lt=cutoff,
        ).select_related("punto_venta")

        total = 0
        recovered = 0
        failed = 0

        for comprobante in stale_qs.iterator():
            total += 1
            try:
                ctx = self._arca_client.get_auth_context(
                    str(comprobante.tenant_id),
                    is_production=is_production,
                )
                wsfe = WSFEv1Client(
                    token=ctx.token,
                    sign=ctx.sign,
                    cuit=ctx.cuit,
                    is_production=ctx.is_production,
                )
                success = self._recover_from_timeout(
                    wsfe=wsfe,
                    comprobante=comprobante,
                    pto_vta_numero=comprobante.punto_venta.numero,
                    cbte_tipo=comprobante.cbte_tipo,
                    cbte_nro=comprobante.cbte_nro,
                )
                if success:
                    recovered += 1
                else:
                    failed += 1
            except (ARCARequestError, Exception):
                logger.exception(
                    "Recovery failed for comprobante %s (nro=%s)",
                    comprobante.pk,
                    comprobante.cbte_nro,
                )
                failed += 1

        logger.info(
            "Stale VALIDANDO recovery: total=%s recovered=%s failed=%s",
            total,
            recovered,
            failed,
        )
        return {"total": total, "recovered": recovered, "failed": failed}
