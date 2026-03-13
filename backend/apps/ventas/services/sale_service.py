"""
Sale service for Gravitea ERP.

Orchestrates the sale lifecycle: confirm (reserve stock + create invoice DRAFT)
and authorize (submit to ARCA + commit stock). Uses dependency injection for
StockService and InvoiceService.

T039-T045, T053 implementation.
"""

from __future__ import annotations

import json as _json
import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.facturacion.constants import (
    CBTE_TIPO_LETTER,
    AlicIvaId,
    CbteTipo,
    ComprobanteStatus,
    Concepto,
    CondicionIVA,
    DocTipo,
    resolver_tipo_comprobante,
)
from apps.facturacion.arca.exceptions import ARCAComprobanteRejected, ARCARequestError
from apps.facturacion.models import AlicIva, Comprobante
from apps.facturacion.services import InvoiceService
from apps.inventario.services.stock_service import InsufficientStockError, StockService

from ..models import SaleOrder, SaleOrderStatus

logger = logging.getLogger("ventas.services")

try:
    from gravitea_rust import calculate_iva_breakdown as _rust_calculate_iva  # type: ignore[import]

    _USE_RUST_COMPUTE = True
except (ImportError, OSError):
    _USE_RUST_COMPUTE = False
    logging.getLogger(__name__).warning(
        "gravitea_rust compute not available — using Python fallback"
    )

# Type C invoices must have EMPTY AlicIva per ARCA validators
_TYPE_C_CBTE_TIPOS = frozenset({
    CbteTipo.FACTURA_C,
    CbteTipo.NOTA_DEBITO_C,
    CbteTipo.NOTA_CREDITO_C,
})

# Reverse mapping: tax_rate percentage → AlicIvaId
_TAX_RATE_TO_ALIC_IVA = {
    Decimal("0.00"): AlicIvaId.IVA_0,
    Decimal("2.50"): AlicIvaId.IVA_2_5,
    Decimal("5.00"): AlicIvaId.IVA_5,
    Decimal("10.50"): AlicIvaId.IVA_10_5,
    Decimal("21.00"): AlicIvaId.IVA_21,
    Decimal("27.00"): AlicIvaId.IVA_27,
}


class SaleServiceError(Exception):
    """Base exception for SaleService operations."""


class SaleConfirmError(SaleServiceError):
    """Raised when sale confirmation fails."""


class SaleAuthorizeError(SaleServiceError):
    """Raised when sale authorization fails."""

    def __init__(self, message: str, arca_errors: dict | list | None = None) -> None:
        self.arca_errors = arca_errors
        super().__init__(message)


class SaleTimeoutError(SaleAuthorizeError):
    """Raised when ARCA authorization fails due to network timeout (recovery attempted)."""

    pass


class SaleService:
    """
    Orchestrates sale lifecycle: confirm and authorize.

    Dependencies are injected for testability:
        - StockService: stock reservation and commitment
        - InvoiceService: ARCA comprobante authorization
    """

    def __init__(
        self,
        stock_service: StockService | None = None,
        invoice_service: InvoiceService | None = None,
    ) -> None:
        self._stock_service = stock_service or StockService()
        self._invoice_service = invoice_service or InvoiceService()

    # ------------------------------------------------------------------
    # T040: confirm_sale
    # ------------------------------------------------------------------

    @transaction.atomic
    def confirm_sale(
        self,
        *,
        order: SaleOrder,
        user: Any = None,
    ) -> dict[str, Any]:
        """
        Confirm a sale order: validate, reserve stock, create Comprobante DRAFT.

        Idempotent: if already CONFIRMED, returns current state without
        double-confirming (T053).

        Args:
            order: The SaleOrder instance (must be DRAFT or already CONFIRMED).
            user: The authenticated user performing the confirmation.

        Returns:
            Dict with confirmation result including stock_reservations
            and comprobante summary.

        Raises:
            SaleConfirmError: If order has no items, is in wrong status,
                or stock is insufficient.
        """
        # T053: Idempotency — if already CONFIRMED, return current state
        if order.status == SaleOrderStatus.CONFIRMED:
            return self._build_confirm_response(order)

        if order.status != SaleOrderStatus.DRAFT:
            raise SaleConfirmError(
                f"Cannot confirm order in status {order.status}. "
                f"Only DRAFT orders can be confirmed."
            )

        # T070: Validate customer fiscal data before proceeding
        customer = order.customer
        if not customer.cuit:
            raise SaleConfirmError(
                "Customer CUIT is required to confirm an order."
            )
        if customer.condicion_iva is None:
            raise SaleConfirmError(
                "Customer condicion_iva is required to confirm an order."
            )

        # Validate order has items
        items = list(
            order.items.select_related("product").all()
        )
        if not items:
            raise SaleConfirmError(
                "Cannot confirm order with no items."
            )

        # Sort items by product_id to prevent ABBA deadlocks
        # when concurrent orders share products (B4 fix)
        items = sorted(items, key=lambda item: str(item.product_id))

        # Reserve stock for each item (T046: creates RESERVED movements)
        branch_id = str(order.branch_id)
        tenant_id = str(order.tenant_id)
        order_id = str(order.id)
        stock_reservations = []

        for item in items:
            product_id = str(item.product_id)
            try:
                self._stock_service.reserve_stock(
                    product_id=product_id,
                    branch_id=branch_id,
                    quantity=item.quantity,
                    tenant_id=tenant_id,
                    sale_order_id=order_id,
                    notes=f"Sale reservation for order {order_id[:8]}",
                )
            except InsufficientStockError as exc:
                # T063: Enrich and propagate for structured API error (T064)
                raise InsufficientStockError(
                    product_id=exc.product_id,
                    branch_id=exc.branch_id,
                    available=exc.available,
                    requested=exc.requested,
                    product_sku=item.product.sku,
                    product_name=item.product.name,
                    branch_name=str(order.branch),
                ) from exc

            stock_reservations.append({
                "product_id": product_id,
                "product_sku": item.product.sku,
                "quantity": item.quantity,
                "status": "RESERVED",
            })

        # T041-T044: Create Comprobante DRAFT via invoice-from-sale helper
        comprobante = self._create_comprobante_from_sale(order, items)

        # Update order status
        order.status = SaleOrderStatus.CONFIRMED
        order.confirmed_at = timezone.now()
        if user:
            order.confirmed_by = user
            order._changed_by = str(user.id)
        order.save()

        logger.info(
            "Sale confirmed: order=%s comprobante=%s items=%d",
            str(order.id)[:8],
            str(comprobante.id)[:8],
            len(items),
        )

        return self._build_confirm_response(order, stock_reservations)

    # ------------------------------------------------------------------
    # T045: authorize_sale
    # ------------------------------------------------------------------

    def authorize_sale(
        self,
        *,
        order: SaleOrder,
        is_production: bool = False,
    ) -> dict[str, Any]:
        """
        Authorize a confirmed sale: submit to ARCA and commit stock.

        T053: Rejects if not CONFIRMED or if already has CAE.
        The ARCA network call runs OUTSIDE any transaction to avoid
        holding DB locks during network I/O.

        Args:
            order: The SaleOrder instance (must be CONFIRMED with linked comprobante).
            is_production: True for production ARCA endpoints.

        Returns:
            Dict with comprobante details including CAE.

        Raises:
            SaleAuthorizeError: If order is not in correct state.
        """
        # T053: Reject if not CONFIRMED
        if order.status != SaleOrderStatus.CONFIRMED:
            raise SaleAuthorizeError(
                f"Cannot authorize order in status {order.status}. "
                f"Only CONFIRMED orders can be authorized."
            )

        # T053: Reject if already has CAE
        if not hasattr(order, "comprobante_direct"):
            raise SaleAuthorizeError(
                "Order has no linked comprobante. Confirm the order first."
            )

        comprobante = order.comprobante_direct

        # T053: Reject if already has CAE (terminal — cannot re-authorize)
        if comprobante.cae:
            raise SaleAuthorizeError(
                f"Order already has CAE: {comprobante.cae}. "
                f"Cannot authorize twice."
            )

        # T059: Allow re-authorization of RECHAZADO comprobantes
        if comprobante.status not in (
            ComprobanteStatus.DRAFT,
            ComprobanteStatus.RECHAZADO,
        ):
            raise SaleAuthorizeError(
                f"Comprobante in status {comprobante.status} cannot be authorized. "
                f"Only DRAFT or RECHAZADO comprobantes can be submitted."
            )

        # T059: For re-authorization after rejection, re-reserve stock
        # (previous reservation was cancelled during rejection handling).
        if comprobante.status == ComprobanteStatus.RECHAZADO:
            self._re_reserve_stock(order)

        # T073: Certificate expiration pre-check
        self._check_certificate_expiry(order, is_production)

        # Authorize the existing comprobante via ARCA.
        # authorize_comprobante() assigns CbteNro, submits to ARCA,
        # and updates the same record in-place (no duplicate creation).
        try:
            authorized = self._invoice_service.authorize_comprobante(
                comprobante=comprobante,
                is_production=is_production,
            )
        except ARCAComprobanteRejected as exc:
            # T056: Cancel stock reservations on rejection
            self._cancel_stock(order)
            logger.warning(
                "ARCA rejected comprobante for order=%s: %s",
                order.id,
                exc.errors if hasattr(exc, "errors") else str(exc),
            )
            raise SaleAuthorizeError(
                f"ARCA rejected comprobante: {exc}",
                arca_errors=comprobante.arca_errors,
            ) from exc
        except ARCARequestError as exc:
            # T071: Timeout — InvoiceService already attempted recovery.
            # Cancel stock reservations and raise timeout-specific error.
            self._cancel_stock(order)
            logger.error(
                "ARCA request failed for order=%s: %s",
                order.id,
                str(exc),
            )
            raise SaleTimeoutError(
                f"ARCA request failed (recovery attempted): {exc}",
                arca_errors=comprobante.arca_errors,
            ) from exc
        except ValueError as exc:
            # Comprobante status/immutability check
            if comprobante.status == ComprobanteStatus.RECHAZADO:
                self._cancel_stock(order)
            raise SaleAuthorizeError(
                f"Comprobante validation error: {exc}"
            ) from exc

        # Commit stock and update order status (separate atomic block
        # to avoid holding DB locks during the ARCA network call above)
        if authorized.status in (
            ComprobanteStatus.AUTORIZADO,
            ComprobanteStatus.OBSERVADO,
        ):
            with transaction.atomic():
                self._commit_stock(order, authorized)

                order.status = SaleOrderStatus.INVOICED
                order.invoiced_at = timezone.now()
                order._changed_by = "arca_authorize"
                order.save()

            logger.info(
                "Sale authorized: order=%s cae=%s status=%s",
                str(order.id)[:8],
                authorized.cae,
                authorized.status,
            )

        result = {
            "order_id": str(order.id),
            "order_status": order.status,
            "comprobante_id": str(authorized.id),
            "comprobante_status": authorized.status,
            "cae": authorized.cae,
            "cae_fch_vto": str(authorized.cae_fch_vto) if authorized.cae_fch_vto else None,
            "cbte_nro": authorized.cbte_nro,
            "imp_total": str(authorized.imp_total),
        }

        if authorized.status == ComprobanteStatus.OBSERVADO:
            result["observaciones"] = authorized.arca_response.get(
                "observaciones", []
            ) if authorized.arca_response else []

        return result

    # ------------------------------------------------------------------
    # T041: Invoice-from-sale helper
    # ------------------------------------------------------------------

    def _create_comprobante_from_sale(
        self,
        order: SaleOrder,
        items: list,
    ) -> Comprobante:
        """
        Create a Comprobante DRAFT from a SaleOrder.

        Determines cbte_tipo via resolver_tipo_comprobante, populates
        all amount/doc fields from order/customer, creates AlicIva rows.
        """
        customer = order.customer
        credential = self._get_credential(order)

        # Determine invoice type
        cbte_tipo = resolver_tipo_comprobante(
            emitter_condition=credential.emitter_condicion_iva,
            receiver_condition=customer.condicion_iva,
        )

        # T068: Validate doc_tipo for Type A invoices (require CUIT/CUIL/CDI)
        letter = CBTE_TIPO_LETTER.get(cbte_tipo)
        if letter == "A" and customer.doc_tipo not in (
            DocTipo.CUIT,
            DocTipo.CUIL,
            DocTipo.CDI,
        ):
            raise SaleConfirmError(
                f"Type A invoices require doc_tipo CUIT, CUIL, or CDI. "
                f"Customer has doc_tipo={customer.doc_tipo}."
            )

        # T043: Amount mapping
        amounts = self._calculate_amounts(order, items, customer.condicion_iva)

        comprobante = Comprobante(
            tenant_id=order.tenant_id,
            punto_venta=self._get_punto_venta(order),
            cbte_tipo=cbte_tipo,
            cbte_nro=0,  # Will be assigned by InvoiceService
            concepto=Concepto.PRODUCTOS,
            doc_tipo=customer.doc_tipo,
            doc_nro=customer.cuit,
            cbte_fch=date.today(),
            imp_total=amounts["imp_total"],
            imp_neto=amounts["imp_neto"],
            imp_iva=amounts["imp_iva"],
            imp_trib=amounts["imp_trib"],
            imp_op_ex=amounts["imp_op_ex"],
            imp_tot_conc=amounts["imp_tot_conc"],
            emitter_cuit=credential.cuit_holder,
            emitter_condicion_iva=credential.emitter_condicion_iva,
            receptor_condicion_iva=customer.condicion_iva,
            status=ComprobanteStatus.DRAFT,
            sale_order=order,
            customer=customer,
        )
        comprobante.save()

        # T042: Create AlicIva rows (Type C must have EMPTY AlicIva per ARCA)
        if cbte_tipo not in _TYPE_C_CBTE_TIPOS:
            self._create_alic_iva(comprobante, items)

        return comprobante

    # ------------------------------------------------------------------
    # T042: IVA breakdown
    # ------------------------------------------------------------------

    @staticmethod
    def _create_alic_iva(comprobante: Comprobante, items: list) -> None:
        """
        Group items by tax_rate and create AlicIva entries.

        Maps tax_rate percentages to ARCA AlicIvaId codes.
        """
        if _USE_RUST_COMPUTE:
            items_json = _json.dumps(
                [
                    {
                        "price": str(item.subtotal),
                        "quantity": "1",
                        "iva_rate": str(item.tax_rate),
                    }
                    for item in items
                ]
            )
            result = _json.loads(_rust_calculate_iva(items_json))
            alic_iva_rows = [
                AlicIva(
                    comprobante=comprobante,
                    iva_id=entry["iva_id"],
                    base_imp=Decimal(entry["base_imp"]),
                    importe=Decimal(entry["importe"]),
                )
                for entry in result
            ]
            if alic_iva_rows:
                AlicIva.objects.bulk_create(alic_iva_rows)
            return

        groups: dict[Decimal, dict[str, Decimal]] = defaultdict(
            lambda: {"base_imp": Decimal("0.000"), "importe": Decimal("0.000")}
        )

        for item in items:
            rate = item.tax_rate
            groups[rate]["base_imp"] += item.subtotal
            groups[rate]["importe"] += item.iva_amount

        alic_iva_rows = []
        for rate, totals in groups.items():
            iva_id = _TAX_RATE_TO_ALIC_IVA.get(rate)
            if iva_id is None:
                logger.warning(
                    "Unknown tax_rate %s — defaulting to IVA_21",
                    rate,
                )
                iva_id = AlicIvaId.IVA_21

            alic_iva_rows.append(
                AlicIva(
                    comprobante=comprobante,
                    iva_id=iva_id,
                    base_imp=totals["base_imp"],
                    importe=totals["importe"],
                )
            )

        if alic_iva_rows:
            AlicIva.objects.bulk_create(alic_iva_rows)

    # ------------------------------------------------------------------
    # T043: Amount mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_amounts(
        order: SaleOrder,
        items: list,
        receptor_condicion_iva: int,
    ) -> dict[str, Decimal]:
        """
        Map order totals to ARCA amount fields.

        imp_total = subtotal + IVA
        imp_neto = subtotal (taxable base)
        imp_iva = total IVA
        imp_trib = 0 (no additional tributos for sales)
        imp_op_ex = 0 for Responsable Inscripto receivers
        imp_tot_conc = 0 for Responsable Inscripto receivers

        Validates: imp_total == imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc
        """
        imp_neto = order.subtotal
        imp_iva = order.total_iva
        imp_trib = Decimal("0.000")
        imp_op_ex = Decimal("0.000")
        imp_tot_conc = Decimal("0.000")
        imp_total = imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc

        # ARCA balance check: computed total must match order.total_amount
        if imp_total != order.total_amount:
            raise SaleConfirmError(
                f"Amount mismatch: computed imp_total={imp_total} "
                f"vs order.total_amount={order.total_amount}"
            )

        return {
            "imp_total": imp_total,
            "imp_neto": imp_neto,
            "imp_iva": imp_iva,
            "imp_trib": imp_trib,
            "imp_op_ex": imp_op_ex,
            "imp_tot_conc": imp_tot_conc,
        }

    # ------------------------------------------------------------------
    # T047: Commit stock after authorization
    # ------------------------------------------------------------------

    def _commit_stock(self, order: SaleOrder, comprobante: Comprobante) -> None:
        """
        Commit reserved stock after successful ARCA authorization.

        Delegates to StockService.commit_reservation().
        """
        self._stock_service.commit_reservation(
            sale_order_id=str(order.id),
            comprobante_id=str(comprobante.id),
        )

    # ------------------------------------------------------------------
    # T055: Cancel stock after ARCA rejection
    # ------------------------------------------------------------------

    def _cancel_stock(self, order: SaleOrder) -> None:
        """
        Cancel reserved stock after ARCA rejection or network failure.

        Delegates to StockService.cancel_reservation() which transitions
        RESERVED movements to CANCELLED and releases snapshot reserved_quantity.
        """
        try:
            self._stock_service.cancel_reservation(
                sale_order_id=str(order.id),
            )
        except ValueError:
            # No RESERVED movements — may have been already cancelled
            logger.warning(
                "No RESERVED movements to cancel for order %s",
                str(order.id)[:8],
            )

    # ------------------------------------------------------------------
    # T059: Re-reserve stock for retry after rejection
    # ------------------------------------------------------------------

    def _re_reserve_stock(self, order: SaleOrder) -> None:
        """
        Re-reserve stock for re-authorization after ARCA rejection.

        After a rejection, stock was cancelled via _cancel_stock().
        Before retrying ARCA, we must re-reserve stock for all order items.

        Raises:
            SaleAuthorizeError: If insufficient stock for re-reservation.
        """
        items = sorted(
            order.items.select_related("product").all(),
            key=lambda item: str(item.product_id),
        )
        branch_id = str(order.branch_id)
        tenant_id = str(order.tenant_id)
        order_id = str(order.id)

        with transaction.atomic():
            for item in items:
                try:
                    self._stock_service.reserve_stock(
                        product_id=str(item.product_id),
                        branch_id=branch_id,
                        quantity=item.quantity,
                        tenant_id=tenant_id,
                        sale_order_id=order_id,
                        notes=f"Re-reservation for retry order {order_id[:8]}",
                    )
                except InsufficientStockError as exc:
                    raise SaleAuthorizeError(
                        f"Insufficient stock for re-reservation of "
                        f"{item.product.sku}: available={exc.available}, "
                        f"requested={exc.requested}"
                    ) from exc

    # ------------------------------------------------------------------
    # T073: Certificate expiration pre-check
    # ------------------------------------------------------------------

    @staticmethod
    def _check_certificate_expiry(order: SaleOrder, is_production: bool) -> None:
        """
        Check ARCA certificate expiration before authorization attempt.

        Raises SaleAuthorizeError if certificate is expired.
        Warns if expiring within 7 days.
        """
        from apps.facturacion.models import ARCACredential

        credential = (
            ARCACredential.all_objects
            .filter(
                tenant_id=order.tenant_id,
                is_production=is_production,
                is_active=True,
            )
            .first()
        )
        if credential is None:
            raise SaleAuthorizeError(
                "No active ARCA credential found for this tenant."
            )

        if credential.certificate_expires_at:
            now = timezone.now()
            if credential.certificate_expires_at <= now:
                raise SaleAuthorizeError(
                    f"ARCA certificate expired at {credential.certificate_expires_at}. "
                    f"Renew the certificate before authorizing invoices."
                )
            days_until_expiry = (credential.certificate_expires_at - now).days
            if days_until_expiry <= 7:
                logger.warning(
                    "ARCA certificate expiring in %d days for tenant %s",
                    days_until_expiry,
                    str(order.tenant_id)[:8],
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_credential(order: SaleOrder):
        """Get the active ARCACredential for the order's tenant."""
        from apps.facturacion.models import ARCACredential

        credential = (
            ARCACredential.all_objects
            .filter(tenant_id=order.tenant_id, is_active=True)
            .first()
        )
        if credential is None:
            raise SaleConfirmError(
                "No active ARCA credential found for this tenant."
            )
        return credential

    @staticmethod
    def _get_punto_venta(order: SaleOrder):
        """Get the first active PuntoDeVenta for the order's tenant."""
        from apps.facturacion.models import PuntoDeVenta

        pto_vta = (
            PuntoDeVenta.all_objects
            .filter(tenant_id=order.tenant_id, is_active=True)
            .first()
        )
        if pto_vta is None:
            raise SaleConfirmError(
                "No active PuntoDeVenta found for this tenant."
            )
        return pto_vta


    def _build_confirm_response(
        self,
        order: SaleOrder,
        stock_reservations: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Build standardized response for confirm_sale."""
        result: dict[str, Any] = {
            "order_id": str(order.id),
            "order_status": order.status,
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None,
        }

        if stock_reservations:
            result["stock_reservations"] = stock_reservations

        if hasattr(order, "comprobante_direct"):
            comp = order.comprobante_direct
            result["comprobante"] = {
                "id": str(comp.id),
                "cbte_tipo": comp.cbte_tipo,
                "status": comp.status,
                "imp_total": str(comp.imp_total),
            }

        return result
