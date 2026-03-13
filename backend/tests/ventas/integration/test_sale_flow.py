"""
T090 + T091: Sale lifecycle integration tests.

T090 — confirm_sale: DRAFT → CONFIRMED with stock reservation + Comprobante DRAFT.
T091 — authorize_sale: CONFIRMED → INVOICED with ARCA CAE + stock commit.

Tests use SaleService with mocked StockService and InvoiceService
(dependency injection) to isolate the orchestration logic from
external services.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.facturacion.constants import (
    CbteTipo,
    ComprobanteStatus,
    CondicionIVA,
)
from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)
from apps.inventario.models import Product, StockSnapshot
from apps.inventario.services.stock_service import InsufficientStockError, StockService
from apps.ventas.models import SaleOrder, SaleOrderStatus
from apps.ventas.services.sale_service import (
    SaleAuthorizeError,
    SaleConfirmError,
    SaleService,
    SaleTimeoutError,
)


# ============================================================
# T090: confirm_sale integration tests
# ============================================================


@pytest.mark.django_db
class TestConfirmSale:
    """SaleService.confirm_sale() orchestration tests."""

    @pytest.mark.integration
    def test_confirm_draft_order_transitions_to_confirmed(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta
    ):
        """DRAFT order with items → CONFIRMED after confirm_sale."""
        order = draft_order_with_items
        assert order.status == SaleOrderStatus.DRAFT

        result = sale_service.confirm_sale(order=order)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.CONFIRMED
        assert order.confirmed_at is not None
        assert result["order_status"] == SaleOrderStatus.CONFIRMED

    @pytest.mark.integration
    def test_confirm_sale_reserves_stock_for_each_item(
        self, sale_service, mock_stock_service, draft_order_with_items,
        arca_credential, punto_de_venta,
    ):
        """confirm_sale calls reserve_stock for each line item."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)

        # 2 items → 2 reserve_stock calls
        assert mock_stock_service.reserve_stock.call_count == 2

    @pytest.mark.integration
    def test_confirm_sale_reserve_stock_call_args(
        self, sale_service, mock_stock_service, draft_order_with_items,
        arca_credential, punto_de_venta,
    ):
        """confirm_sale passes correct args to reserve_stock for each item."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)

        # 2 items → 2 reserve_stock calls
        assert mock_stock_service.reserve_stock.call_count == 2

        # Verify first call includes branch_id, tenant_id, sale_order_id
        call_kwargs = mock_stock_service.reserve_stock.call_args_list[0].kwargs
        assert call_kwargs["branch_id"] == str(order.branch_id)
        assert call_kwargs["tenant_id"] == str(order.tenant_id)
        assert call_kwargs["sale_order_id"] == str(order.id)

    @pytest.mark.integration
    def test_confirm_sale_creates_comprobante_draft(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """confirm_sale creates a linked Comprobante in DRAFT status."""
        from apps.facturacion.models import Comprobante

        order = draft_order_with_items
        result = sale_service.confirm_sale(order=order)

        # Comprobante linked via OneToOneField
        order.refresh_from_db()
        assert hasattr(order, "comprobante_direct")

        comp = order.comprobante_direct
        assert comp.status == ComprobanteStatus.DRAFT
        assert comp.sale_order_id == order.id
        assert comp.customer_id == order.customer_id

    @pytest.mark.integration
    def test_confirm_sale_comprobante_has_correct_cbte_tipo(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """Comprobante cbte_tipo matches resolver (RI emitter → RI customer = A)."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)

        comp = order.comprobante_direct
        assert comp.cbte_tipo == CbteTipo.FACTURA_A

    @pytest.mark.integration
    def test_confirm_sale_comprobante_amounts_match_order(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """Comprobante amounts match order totals."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)

        comp = order.comprobante_direct
        assert comp.imp_neto == order.subtotal
        assert comp.imp_iva == order.total_iva
        assert comp.imp_total == order.total_amount

    @pytest.mark.integration
    def test_confirm_sale_creates_alic_iva_rows(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """confirm_sale creates AlicIva rows grouped by tax rate."""
        from apps.facturacion.models import AlicIva

        order = draft_order_with_items
        sale_service.confirm_sale(order=order)

        comp = order.comprobante_direct
        alic_rows = list(comp.aliciva_set.all())

        # All items have 21% IVA → 1 aggregated AlicIva row
        assert len(alic_rows) == 1
        assert alic_rows[0].base_imp == order.subtotal
        assert alic_rows[0].importe == order.total_iva

    @pytest.mark.integration
    def test_confirm_sale_type_c_no_alic_iva(
        self, sale_service, draft_order_with_items,
        punto_de_venta,
    ):
        """Type C invoice (Mono emitter) must have EMPTY AlicIva per ARCA."""
        from apps.facturacion.constants import CondicionIVA
        from apps.facturacion.models import AlicIva, ARCACredential

        order = draft_order_with_items

        # Create Mono emitter credential (instead of RI)
        ARCACredential.objects.create(
            tenant=order.tenant,
            cuit_holder="20999999990",
            certificate_pem="-----BEGIN CERTIFICATE-----\nMIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls\nb2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD\nVQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7\n-----END CERTIFICATE-----",
            private_key_pem="-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEAu+2uZ+hBwuAtb9yZeXRMWkVo8zBzhTBm6NlaRjsCRJSkB5iZ\n-----END RSA PRIVATE KEY-----",
            is_production=False,
            is_active=True,
            emitter_condicion_iva=CondicionIVA.MONOTRIBUTISTA,
        )
        # Deactivate the RI credential if present
        ARCACredential.all_objects.filter(
            tenant_id=order.tenant_id,
            emitter_condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        ).update(is_active=False)

        sale_service.confirm_sale(order=order)

        comp = order.comprobante_direct
        assert comp.cbte_tipo == CbteTipo.FACTURA_C
        # ARCA requires Type C to have NO AlicIva rows
        assert comp.aliciva_set.count() == 0

    @pytest.mark.integration
    def test_confirm_sale_sets_confirmed_by(
        self, sale_service, draft_order_with_items, admin_user,
        arca_credential, punto_de_venta,
    ):
        """confirm_sale records the user who confirmed."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order, user=admin_user)

        order.refresh_from_db()
        assert order.confirmed_by == admin_user

    # --- Error cases ---

    @pytest.mark.integration
    def test_confirm_no_items_raises_error(
        self, sale_service, sale_order_factory, customer_ri,
        arca_credential, punto_de_venta,
    ):
        """Cannot confirm order with no items."""
        order = sale_order_factory(customer=customer_ri)

        with pytest.raises(SaleConfirmError, match="no items"):
            sale_service.confirm_sale(order=order)

    @pytest.mark.integration
    def test_confirm_insufficient_stock_raises_error(
        self, mock_stock_service, mock_invoice_service,
        draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """InsufficientStockError from StockService propagates directly."""
        mock_stock_service.reserve_stock.side_effect = InsufficientStockError(
            product_id="test-product",
            branch_id="test-branch",
            available=Decimal("2.0000"),
            requested=Decimal("5.0000"),
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )
        order = draft_order_with_items

        with pytest.raises(InsufficientStockError, match="Insufficient stock"):
            svc.confirm_sale(order=order)

    @pytest.mark.integration
    def test_confirm_invoiced_order_raises_error(
        self, sale_service, sale_order_factory, customer_ri,
    ):
        """Cannot confirm an INVOICED order."""
        # Create order directly as CONFIRMED first, then force INVOICED
        order = sale_order_factory(customer=customer_ri, status="DRAFT")
        # Manually set status bypassing save() validation for test setup
        SaleOrder.all_objects.filter(pk=order.pk).update(status="INVOICED")
        order.refresh_from_db()

        with pytest.raises(SaleConfirmError, match="Cannot confirm order"):
            sale_service.confirm_sale(order=order)

    # --- T053: Idempotency ---

    @pytest.mark.integration
    def test_confirm_already_confirmed_is_idempotent(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """T053: Re-confirming a CONFIRMED order returns current state without errors."""
        order = draft_order_with_items
        result1 = sale_service.confirm_sale(order=order)

        # Second confirm should be idempotent
        order.refresh_from_db()
        result2 = sale_service.confirm_sale(order=order)

        assert result2["order_status"] == SaleOrderStatus.CONFIRMED
        assert result2["order_id"] == str(order.id)


# ============================================================
# T091: authorize_sale integration tests
# ============================================================


@pytest.mark.django_db
class TestAuthorizeSale:
    """SaleService.authorize_sale() orchestration tests."""

    @pytest.fixture
    def confirmed_order(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """A CONFIRMED order with Comprobante DRAFT, ready for authorization."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)
        order.refresh_from_db()
        return order

    @pytest.mark.integration
    def test_authorize_transitions_to_invoiced(
        self, sale_service, confirmed_order,
    ):
        """CONFIRMED order → INVOICED after authorize_sale."""
        order = confirmed_order
        result = sale_service.authorize_sale(order=order)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED
        assert order.invoiced_at is not None

    @pytest.mark.integration
    def test_authorize_returns_cae(
        self, sale_service, confirmed_order,
    ):
        """authorize_sale response includes CAE from ARCA."""
        result = sale_service.authorize_sale(order=confirmed_order)

        assert result["cae"] is not None
        assert len(result["cae"]) == 14  # Standard CAE length
        assert result["comprobante_status"] == ComprobanteStatus.AUTORIZADO

    @pytest.mark.integration
    def test_authorize_commits_stock(
        self, sale_service, mock_stock_service, confirmed_order,
    ):
        """authorize_sale calls commit_reservation on StockService."""
        sale_service.authorize_sale(order=confirmed_order)

        mock_stock_service.commit_reservation.assert_called_once()
        call_kwargs = mock_stock_service.commit_reservation.call_args.kwargs
        assert call_kwargs["sale_order_id"] == str(confirmed_order.id)

    @pytest.mark.integration
    def test_authorize_calls_invoice_service(
        self, sale_service, mock_invoice_service, confirmed_order,
    ):
        """authorize_sale delegates to InvoiceService.authorize_comprobante."""
        sale_service.authorize_sale(order=confirmed_order)

        mock_invoice_service.authorize_comprobante.assert_called_once()
        call_kwargs = mock_invoice_service.authorize_comprobante.call_args.kwargs
        assert call_kwargs["comprobante"] == confirmed_order.comprobante_direct

    @pytest.mark.integration
    def test_authorize_observado_still_invoiced(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """OBSERVADO status (CAE with warnings) still transitions to INVOICED."""
        result_mock = MagicMock()
        result_mock.status = ComprobanteStatus.OBSERVADO
        result_mock.cae = "71234567890123"
        result_mock.cae_fch_vto = date(2026, 3, 15)
        result_mock.cbte_nro = 1
        result_mock.imp_total = Decimal("968.000")
        result_mock.id = uuid.uuid4()
        result_mock.arca_response = {"observaciones": [{"code": "10063", "msg": "Warning"}]}
        mock_invoice_service.authorize_comprobante.return_value = result_mock

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )
        order = confirmed_order

        result = svc.authorize_sale(order=order)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED
        assert result["comprobante_status"] == ComprobanteStatus.OBSERVADO
        assert "observaciones" in result

    @pytest.mark.integration
    def test_authorize_rejected_no_status_change(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """RECHAZADO status does NOT transition to INVOICED — stays CONFIRMED."""
        result_mock = MagicMock()
        result_mock.status = ComprobanteStatus.RECHAZADO
        result_mock.cae = None
        result_mock.cae_fch_vto = None
        result_mock.cbte_nro = 0
        result_mock.imp_total = Decimal("968.000")
        result_mock.id = uuid.uuid4()
        result_mock.arca_response = {"errores": [{"code": "10016", "msg": "Rejected"}]}
        mock_invoice_service.authorize_comprobante.return_value = result_mock

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )
        order = confirmed_order

        result = svc.authorize_sale(order=order)

        order.refresh_from_db()
        assert order.status == SaleOrderStatus.CONFIRMED  # NOT INVOICED
        assert result["cae"] is None
        assert result["comprobante_status"] == ComprobanteStatus.RECHAZADO

    @pytest.mark.integration
    def test_authorize_rejected_no_stock_commit(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """RECHAZADO → commit_reservation should NOT be called."""
        result_mock = MagicMock()
        result_mock.status = ComprobanteStatus.RECHAZADO
        result_mock.cae = None
        result_mock.cae_fch_vto = None
        result_mock.cbte_nro = 0
        result_mock.imp_total = Decimal("968.000")
        result_mock.id = uuid.uuid4()
        result_mock.arca_response = None
        mock_invoice_service.authorize_comprobante.return_value = result_mock

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )
        svc.authorize_sale(order=confirmed_order)

        mock_stock_service.commit_reservation.assert_not_called()

    # --- Error cases ---

    @pytest.mark.integration
    def test_authorize_draft_order_raises_error(
        self, sale_service, draft_order_with_items,
    ):
        """Cannot authorize a DRAFT order — must confirm first."""
        with pytest.raises(SaleAuthorizeError, match="Cannot authorize"):
            sale_service.authorize_sale(order=draft_order_with_items)

    @pytest.mark.integration
    def test_authorize_already_has_cae_raises_error(
        self, sale_service, mock_invoice_service, confirmed_order,
    ):
        """T053: Cannot authorize twice — order already has CAE."""
        # First authorization
        sale_service.authorize_sale(order=confirmed_order)

        # Force order back to CONFIRMED for the second attempt
        confirmed_order.refresh_from_db()
        SaleOrder.all_objects.filter(pk=confirmed_order.pk).update(
            status=SaleOrderStatus.CONFIRMED
        )
        confirmed_order.refresh_from_db()

        # The comprobante now has a CAE set (from mock)
        # But the real comprobante's cae field is from the DB, not the mock return.
        # Need to update the actual comprobante to have a CAE
        comp = confirmed_order.comprobante_direct
        comp.cae = "71234567890123"
        comp.status = ComprobanteStatus.AUTORIZADO
        # Save without triggering immutability check — use update()
        from apps.facturacion.models import Comprobante

        Comprobante.all_objects.filter(pk=comp.pk).update(
            cae="71234567890123",
            status=ComprobanteStatus.AUTORIZADO,
        )
        confirmed_order.refresh_from_db()

        with pytest.raises(SaleAuthorizeError, match="already has CAE"):
            sale_service.authorize_sale(order=confirmed_order)

    @pytest.mark.integration
    def test_authorize_no_comprobante_raises_error(
        self, sale_service, sale_order_factory, customer_ri,
    ):
        """Cannot authorize order without linked Comprobante."""
        order = sale_order_factory(customer=customer_ri, status="DRAFT")
        # Force to CONFIRMED without confirm_sale (no comprobante created)
        SaleOrder.all_objects.filter(pk=order.pk).update(status="CONFIRMED")
        order.refresh_from_db()

        with pytest.raises(SaleAuthorizeError, match="no linked comprobante"):
            sale_service.authorize_sale(order=order)


# ============================================================
# T092: Rejection recovery tests
# ============================================================


@pytest.mark.django_db
class TestRejectionRecovery:
    """T092: ARCA rejection → stock cancellation → recovery → re-authorize flow."""

    @pytest.fixture
    def confirmed_order(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """A CONFIRMED order ready for authorization."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)
        order.refresh_from_db()
        return order

    # --- 1. test_authorize_rejection_releases_stock ---

    @pytest.mark.integration
    def test_authorize_rejection_releases_stock(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        ARCA rejection → cancel_reservation called (stock released),
        commit_reservation NOT called. Order stays CONFIRMED.
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCAComprobanteRejected(message="Rejected", code="10016")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError):
            svc.authorize_sale(order=confirmed_order)

        # cancel_reservation MUST be called to release reserved stock
        mock_stock_service.cancel_reservation.assert_called_once()
        cancel_kwargs = mock_stock_service.cancel_reservation.call_args.kwargs
        assert cancel_kwargs["sale_order_id"] == str(confirmed_order.id)

        # commit_reservation must NOT be called
        mock_stock_service.commit_reservation.assert_not_called()

        # Order stays CONFIRMED (not reverted to DRAFT)
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED
        assert confirmed_order.invoiced_at is None

    # --- 2. test_authorize_rejection_error_details ---

    @pytest.mark.integration
    def test_authorize_rejection_error_details(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        ARCA rejection → SaleAuthorizeError carries structured arca_errors
        from the comprobante (set by InvoiceService before raising).
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected

        arca_error_payload = [
            {"code": "10016", "msg": "Fecha de comprobante fuera de rango"},
            {"code": "10048", "msg": "Tipo de documento receptor no valido"},
        ]

        def rejection_with_arca_errors(**kwargs):
            """Simulate InvoiceService updating comprobante before raising."""
            kwargs["comprobante"].arca_errors = arca_error_payload
            raise ARCAComprobanteRejected(
                message="Fecha de comprobante fuera de rango",
                code="10016",
                observations=arca_error_payload,
            )

        mock_invoice_service.authorize_comprobante.side_effect = (
            rejection_with_arca_errors
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError) as exc_info:
            svc.authorize_sale(order=confirmed_order)

        error = exc_info.value
        # SaleAuthorizeError.arca_errors contains the structured error list
        assert error.arca_errors == arca_error_payload
        assert "ARCA rejected" in str(error)

        # Order stays CONFIRMED for retry
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED

    # --- 3. test_reauthorize_after_rejection_success ---

    @pytest.mark.integration
    def test_reauthorize_after_rejection_success(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        Full rejection recovery: reject → RECHAZADO → re-authorize →
        re-reserve stock → ARCA accepts → commit stock → INVOICED.
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected
        from apps.facturacion.models import Comprobante as CompModel

        comp = confirmed_order.comprobante_direct

        # First attempt: ARCA rejects (InvoiceService sets RECHAZADO)
        def rejection_sets_rechazado(**kwargs):
            CompModel.all_objects.filter(pk=comp.pk).update(
                status=ComprobanteStatus.RECHAZADO,
                arca_errors=[{"code": "10016", "msg": "Fecha fuera de rango"}],
            )
            raise ARCAComprobanteRejected(
                message="Fecha fuera de rango", code="10016",
            )

        mock_invoice_service.authorize_comprobante.side_effect = (
            rejection_sets_rechazado
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError):
            svc.authorize_sale(order=confirmed_order)

        # Verify rejection state
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED
        mock_stock_service.cancel_reservation.assert_called_once()

        # Reset mock call counts for second attempt
        mock_stock_service.reset_mock()
        mock_stock_service.reserve_stock.return_value = True
        mock_stock_service.commit_reservation.return_value = None

        # Second attempt: ARCA accepts (issue fixed by operator)
        success_result = MagicMock()
        success_result.status = ComprobanteStatus.AUTORIZADO
        success_result.cae = "71234567890123"
        success_result.cae_fch_vto = date(2026, 3, 15)
        success_result.cbte_nro = 1
        success_result.imp_total = Decimal("968.000")
        success_result.id = comp.id
        success_result.arca_response = None

        mock_invoice_service.authorize_comprobante.side_effect = None
        mock_invoice_service.authorize_comprobante.return_value = success_result

        result = svc.authorize_sale(order=confirmed_order)

        # T059: Re-reservation occurred (2 items → 2 reserve_stock calls)
        assert mock_stock_service.reserve_stock.call_count == 2
        # Stock committed after successful authorization
        mock_stock_service.commit_reservation.assert_called_once()

        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.INVOICED
        assert result["cae"] == "71234567890123"

    # --- 4. test_reauthorize_after_rejection_insufficient_stock ---

    @pytest.mark.integration
    def test_reauthorize_after_rejection_insufficient_stock(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        Rejection → RECHAZADO → retry but stock depleted by another sale →
        SaleAuthorizeError. Order stays CONFIRMED.
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected
        from apps.facturacion.models import Comprobante as CompModel

        comp = confirmed_order.comprobante_direct

        # First attempt: ARCA rejects, sets RECHAZADO
        def rejection_sets_rechazado(**kwargs):
            CompModel.all_objects.filter(pk=comp.pk).update(
                status=ComprobanteStatus.RECHAZADO,
            )
            raise ARCAComprobanteRejected(message="Error", code="10016")

        mock_invoice_service.authorize_comprobante.side_effect = (
            rejection_sets_rechazado
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError):
            svc.authorize_sale(order=confirmed_order)

        confirmed_order.refresh_from_db()

        # Reset mocks — simulate another sale depleted the stock
        mock_stock_service.reset_mock()
        mock_stock_service.reserve_stock.side_effect = InsufficientStockError(
            product_id="test-product",
            branch_id="test-branch",
            available=Decimal("1.0000"),
            requested=Decimal("5.0000"),
        )

        # Clear the authorize mock so it doesn't re-raise the old exception
        mock_invoice_service.authorize_comprobante.side_effect = None
        mock_invoice_service.authorize_comprobante.return_value = MagicMock()

        # Second attempt: re-reservation fails due to insufficient stock
        with pytest.raises(SaleAuthorizeError, match="Insufficient stock"):
            svc.authorize_sale(order=confirmed_order)

        # Order stays CONFIRMED — not INVOICED, not DRAFT
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED
        # commit_reservation never called (failed before ARCA call)
        mock_stock_service.commit_reservation.assert_not_called()

    # --- 5. test_cancel_reservation_transitions_movements ---

    @pytest.mark.integration
    def test_cancel_reservation_transitions_movements(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        Direct verification: _cancel_stock delegates to
        StockService.cancel_reservation(sale_order_id).
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCAComprobanteRejected(message="Rejected", code="10016")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError):
            svc.authorize_sale(order=confirmed_order)

        # Verify exact call signature
        mock_stock_service.cancel_reservation.assert_called_once_with(
            sale_order_id=str(confirmed_order.id),
        )

    # --- Additional coverage: timeout cancels stock (same as rejection) ---

    @pytest.mark.integration
    def test_timeout_cancels_stock_and_raises_timeout_error(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T071: ARCARequestError (timeout, recovery failed) → cancel_reservation
        called, SaleTimeoutError raised (subclass of SaleAuthorizeError).
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCARequestError("Connection timed out")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError):
            svc.authorize_sale(order=confirmed_order)

        # Stock cancelled on timeout (same as rejection)
        mock_stock_service.cancel_reservation.assert_called_once()
        mock_stock_service.commit_reservation.assert_not_called()

        # Order stays CONFIRMED
        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED

    # --- Recovery: retry after timeout succeeds ---

    @pytest.mark.integration
    def test_timeout_retry_after_timeout_succeeds(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T074: After timeout (comprobante stays DRAFT) → retry authorize_sale
        → ARCA accepts → stock committed → INVOICED.
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        comp = confirmed_order.comprobante_direct

        # First attempt: timeout (recovery fails)
        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCARequestError("Connection timed out")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError):
            svc.authorize_sale(order=confirmed_order)

        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED

        # Reset mocks for retry
        mock_stock_service.reset_mock()
        mock_stock_service.reserve_stock.return_value = True
        mock_stock_service.commit_reservation.return_value = None

        # Second attempt: ARCA accepts
        success_result = MagicMock()
        success_result.status = ComprobanteStatus.AUTORIZADO
        success_result.cae = "71234567890123"
        success_result.cae_fch_vto = date(2026, 3, 15)
        success_result.cbte_nro = 1
        success_result.imp_total = Decimal("968.000")
        success_result.id = comp.id
        success_result.arca_response = None

        mock_invoice_service.authorize_comprobante.side_effect = None
        mock_invoice_service.authorize_comprobante.return_value = success_result

        result = svc.authorize_sale(order=confirmed_order)

        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.INVOICED
        assert result["cae"] == "71234567890123"
        mock_stock_service.commit_reservation.assert_called_once()


# ============================================================
# T093: Timeout recovery tests
# ============================================================


@pytest.mark.django_db
class TestTimeoutRecovery:
    """T093: ARCA timeout → SaleTimeoutError → retry recovery.

    Tests the T071-T074 timeout recovery flow where InvoiceService
    handles FECAESolicitar timeout internally via _recover_from_timeout.
    If recovery also fails, InvoiceService raises ARCARequestError.
    SaleService catches it, cancels stock, and raises SaleTimeoutError
    (a subclass of SaleAuthorizeError for caller distinction).
    On retry, comprobante stays DRAFT → authorize_sale can be called again.
    """

    @pytest.fixture
    def confirmed_order(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """A CONFIRMED order ready for authorization."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)
        order.refresh_from_db()
        return order

    # --- 1. SaleTimeoutError is a distinct subclass ---

    @pytest.mark.integration
    def test_timeout_raises_sale_timeout_error_not_generic(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T071: ARCARequestError → SaleTimeoutError (which IS-A SaleAuthorizeError).
        Callers can distinguish timeout from rejection by exception type.
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCARequestError("Connection timed out")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError) as exc_info:
            svc.authorize_sale(order=confirmed_order)

        # Verify it IS a SaleAuthorizeError (subclass)
        assert isinstance(exc_info.value, SaleAuthorizeError)
        # But it IS specifically a SaleTimeoutError
        assert type(exc_info.value) is SaleTimeoutError

    # --- 2. SaleTimeoutError carries arca_errors ---

    @pytest.mark.integration
    def test_timeout_error_carries_arca_errors(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T071: SaleTimeoutError.arca_errors populated from comprobante.arca_errors
        (set by InvoiceService during recovery attempt).
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        arca_error_payload = [{"code": "timeout", "msg": "Connection timed out"}]

        def timeout_with_arca_errors(**kwargs):
            kwargs["comprobante"].arca_errors = arca_error_payload
            raise ARCARequestError("Connection timed out")

        mock_invoice_service.authorize_comprobante.side_effect = (
            timeout_with_arca_errors
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError) as exc_info:
            svc.authorize_sale(order=confirmed_order)

        assert exc_info.value.arca_errors == arca_error_payload

    # --- 3. Order stays CONFIRMED after timeout ---

    @pytest.mark.integration
    def test_timeout_order_stays_confirmed(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T072: After SaleTimeoutError, order remains CONFIRMED.
        invoiced_at stays None. Order is ready for retry.
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCARequestError("Timeout")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError):
            svc.authorize_sale(order=confirmed_order)

        confirmed_order.refresh_from_db()
        assert confirmed_order.status == SaleOrderStatus.CONFIRMED
        assert confirmed_order.invoiced_at is None

    # --- 4. Stock cancelled, not committed ---

    @pytest.mark.integration
    def test_timeout_stock_cancelled_not_committed(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        T071: Timeout → cancel_reservation called (stock released),
        commit_reservation NOT called. Same stock handling as rejection.
        """
        from apps.facturacion.arca.exceptions import ARCARequestError

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCARequestError("Timeout")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleTimeoutError):
            svc.authorize_sale(order=confirmed_order)

        mock_stock_service.cancel_reservation.assert_called_once_with(
            sale_order_id=str(confirmed_order.id),
        )
        mock_stock_service.commit_reservation.assert_not_called()

    # --- 5. Rejection raises SaleAuthorizeError, NOT SaleTimeoutError ---

    @pytest.mark.integration
    def test_rejection_does_not_raise_timeout_error(
        self, mock_stock_service, mock_invoice_service, confirmed_order,
    ):
        """
        ARCAComprobanteRejected → SaleAuthorizeError (NOT SaleTimeoutError).
        Timeout and rejection are distinguishable by exception type.
        """
        from apps.facturacion.arca.exceptions import ARCAComprobanteRejected

        mock_invoice_service.authorize_comprobante.side_effect = (
            ARCAComprobanteRejected(message="Rejected", code="10016")
        )

        svc = SaleService(
            stock_service=mock_stock_service,
            invoice_service=mock_invoice_service,
        )

        with pytest.raises(SaleAuthorizeError) as exc_info:
            svc.authorize_sale(order=confirmed_order)

        # It's a SaleAuthorizeError but NOT a SaleTimeoutError
        assert not isinstance(exc_info.value, SaleTimeoutError)


# ============================================================
# T073: Certificate expiration pre-check tests
# ============================================================


@pytest.mark.django_db
class TestCertificateExpiry:
    """T073: Certificate expiration pre-check before ARCA authorization."""

    @pytest.fixture
    def confirmed_order(
        self, sale_service, draft_order_with_items, arca_credential, punto_de_venta,
    ):
        """A CONFIRMED order ready for authorization."""
        order = draft_order_with_items
        sale_service.confirm_sale(order=order)
        order.refresh_from_db()
        return order

    @pytest.mark.integration
    def test_expired_certificate_blocks_authorization(
        self, sale_service, confirmed_order, arca_credential,
    ):
        """
        T073: Expired ARCA certificate → SaleAuthorizeError before
        authorize_comprobante is even called.
        """
        from apps.facturacion.models import ARCACredential

        # Set certificate to expired (yesterday)
        ARCACredential.all_objects.filter(pk=arca_credential.pk).update(
            certificate_expires_at=timezone.now() - timedelta(days=1),
        )

        with pytest.raises(SaleAuthorizeError, match="certificate expired"):
            sale_service.authorize_sale(order=confirmed_order)

    @pytest.mark.integration
    def test_deactivated_credential_blocks_authorization(
        self, sale_service, confirmed_order, arca_credential,
    ):
        """
        T073: No active ARCA credential → SaleAuthorizeError.
        """
        from apps.facturacion.models import ARCACredential

        # Deactivate credential after confirm (which already happened)
        ARCACredential.all_objects.filter(pk=arca_credential.pk).update(
            is_active=False,
        )

        with pytest.raises(SaleAuthorizeError, match="No active ARCA credential"):
            sale_service.authorize_sale(order=confirmed_order)

    @pytest.mark.integration
    def test_expiring_soon_warns_but_allows(
        self, sale_service, confirmed_order, arca_credential,
    ):
        """
        T073: Certificate expiring within 7 days → logs warning but
        authorization proceeds normally.
        """
        from apps.facturacion.models import ARCACredential

        # Set certificate to expire in 5 days
        ARCACredential.all_objects.filter(pk=arca_credential.pk).update(
            certificate_expires_at=timezone.now() + timedelta(days=5),
        )

        # Should NOT raise — authorization proceeds
        result = sale_service.authorize_sale(order=confirmed_order)
        assert result["cae"] is not None


# ============================================================
# T097: Concurrent stock reservation tests
# ============================================================


@pytest.mark.django_db(transaction=True)
class TestConcurrentStockReservation:
    """T097: Concurrent confirm_sale with real StockService locking."""

    @staticmethod
    def _create_stock_snapshot(product, branch, quantity):
        """Create a StockSnapshot with a given quantity for a product at a branch."""
        return StockSnapshot.objects.create(
            product=product,
            branch=branch,
            quantity=quantity,
            reserved_quantity=Decimal("0.0000"),
        )

    @staticmethod
    def _confirm_in_thread(svc, order, tenant_id):
        """
        Run confirm_sale in a separate thread with tenant context.

        Returns the result dict on success, or the exception on failure.
        Each thread gets its own DB connection which must be closed on exit.
        """
        from django.db import connection

        try:
            set_current_tenant_id(tenant_id)
            return svc.confirm_sale(order=order)
        except Exception as exc:
            return exc
        finally:
            clear_current_tenant_id()
            connection.close()

    @pytest.mark.skip(reason="Requires PostgreSQL for concurrent select_for_update (SQLite uses file-level locking)")
    @pytest.mark.integration
    def test_concurrent_confirm_first_succeeds_second_fails(
        self,
        tenant_context,
        branch,
        customer_ri,
        product,
        arca_credential,
        punto_de_venta,
        sale_order_factory,
        sale_order_item_factory,
    ):
        """
        T097: Two concurrent confirm_sale calls on the same product.
        Product has quantity=5, each order requests 3.
        One must succeed (reserved=3), the other must fail (insufficient stock).
        """
        # Setup: StockSnapshot with quantity=5
        self._create_stock_snapshot(product, branch, Decimal("5.0000"))

        # Create two DRAFT orders, each with 1 item requesting quantity=3
        order1 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order1,
            product=product,
            quantity=Decimal("3.0000"),
            unit_price=product.unit_price,
            tax_rate=product.tax_rate,
        )
        order1.recalculate_totals()
        order1.refresh_from_db()

        # Second order needs a different product instance for unique constraint
        # but we want the SAME physical product for the stock contention test.
        # SaleOrderItem has a unique constraint per (sale_order, product) — not cross-order.
        order2 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order2,
            product=product,
            quantity=Decimal("3.0000"),
            unit_price=product.unit_price,
            tax_rate=product.tax_rate,
        )
        order2.recalculate_totals()
        order2.refresh_from_db()

        # Real StockService + mocked InvoiceService
        mock_inv = MagicMock()
        svc = SaleService(stock_service=StockService(), invoice_service=mock_inv)
        tenant_id = tenant_context.id

        # Run both concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(self._confirm_in_thread, svc, order1, tenant_id)
            f2 = executor.submit(self._confirm_in_thread, svc, order2, tenant_id)

            results = [f1.result(timeout=10), f2.result(timeout=10)]

        # Classify results
        successes = [r for r in results if isinstance(r, dict)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}"
        assert isinstance(failures[0], InsufficientStockError)

        # Verify snapshot: only the winner's reservation is recorded
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.reserved_quantity == Decimal("3.0000")

    @pytest.mark.skip(reason="Requires PostgreSQL for concurrent select_for_update (SQLite uses file-level locking)")
    @pytest.mark.integration
    def test_concurrent_confirm_both_succeed_within_capacity(
        self,
        tenant_context,
        branch,
        customer_ri,
        product,
        arca_credential,
        punto_de_venta,
        sale_order_factory,
        sale_order_item_factory,
    ):
        """
        T097: Two concurrent confirm_sale calls, both within stock capacity.
        Product has quantity=10, each order requests 3. Both must succeed.
        """
        # Setup: StockSnapshot with quantity=10
        self._create_stock_snapshot(product, branch, Decimal("10.0000"))

        # Two DRAFT orders, each requesting 3
        order1 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order1,
            product=product,
            quantity=Decimal("3.0000"),
            unit_price=product.unit_price,
            tax_rate=product.tax_rate,
        )
        order1.recalculate_totals()
        order1.refresh_from_db()

        order2 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order2,
            product=product,
            quantity=Decimal("3.0000"),
            unit_price=product.unit_price,
            tax_rate=product.tax_rate,
        )
        order2.recalculate_totals()
        order2.refresh_from_db()

        mock_inv = MagicMock()
        svc = SaleService(stock_service=StockService(), invoice_service=mock_inv)
        tenant_id = tenant_context.id

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(self._confirm_in_thread, svc, order1, tenant_id)
            f2 = executor.submit(self._confirm_in_thread, svc, order2, tenant_id)

            results = [f1.result(timeout=10), f2.result(timeout=10)]

        # Both should succeed
        successes = [r for r in results if isinstance(r, dict)]
        failures = [r for r in results if isinstance(r, Exception)]

        assert len(successes) == 2, (
            f"Expected 2 successes, got {len(successes)}. "
            f"Failures: {[str(e) for e in failures]}"
        )

        # Verify snapshot: total reserved = 3 + 3 = 6
        snapshot = StockSnapshot.objects.get(product=product, branch=branch)
        assert snapshot.reserved_quantity == Decimal("6.0000")

        # Both orders should be CONFIRMED
        order1.refresh_from_db()
        order2.refresh_from_db()
        assert order1.status == SaleOrderStatus.CONFIRMED
        assert order2.status == SaleOrderStatus.CONFIRMED

    @pytest.mark.skip(reason="Requires PostgreSQL for concurrent select_for_update (SQLite uses file-level locking)")
    @pytest.mark.integration
    def test_concurrent_confirm_deadlock_prevention(
        self,
        tenant_context,
        branch,
        customer_ri,
        product,
        arca_credential,
        punto_de_venta,
        sale_order_factory,
        sale_order_item_factory,
    ):
        """
        T097: Two orders with shared products in reverse order.
        Order 1: items [A, B]. Order 2: items [B, A].
        Without product_id sorting in confirm_sale → ABBA deadlock.
        With sorting (line 146 of sale_service.py) → both complete safely.
        Timeout of 5 seconds detects deadlock.
        """
        product_a = product  # TEST-001 from fixture

        # Create second product
        product_b = Product.objects.create(
            tenant=tenant_context,
            sku="TEST-DEADLOCK-B",
            name="Deadlock Test Product B",
            description="Second product for deadlock test",
            unit_price=Decimal("200.000"),
            cost_price=Decimal("80.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        )

        # Stock for both products
        self._create_stock_snapshot(product_a, branch, Decimal("20.0000"))
        self._create_stock_snapshot(product_b, branch, Decimal("20.0000"))

        # Order 1: items [A, B]
        order1 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order1,
            product=product_a,
            quantity=Decimal("2.0000"),
            unit_price=product_a.unit_price,
            tax_rate=product_a.tax_rate,
        )
        sale_order_item_factory(
            sale_order=order1,
            product=product_b,
            quantity=Decimal("2.0000"),
            unit_price=product_b.unit_price,
            tax_rate=product_b.tax_rate,
        )
        order1.recalculate_totals()
        order1.refresh_from_db()

        # Order 2: items [B, A] (reverse insertion order)
        order2 = sale_order_factory(customer=customer_ri)
        sale_order_item_factory(
            sale_order=order2,
            product=product_b,
            quantity=Decimal("2.0000"),
            unit_price=product_b.unit_price,
            tax_rate=product_b.tax_rate,
        )
        sale_order_item_factory(
            sale_order=order2,
            product=product_a,
            quantity=Decimal("2.0000"),
            unit_price=product_a.unit_price,
            tax_rate=product_a.tax_rate,
        )
        order2.recalculate_totals()
        order2.refresh_from_db()

        mock_inv = MagicMock()
        svc = SaleService(stock_service=StockService(), invoice_service=mock_inv)
        tenant_id = tenant_context.id

        # 5-second timeout to detect deadlocks
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(self._confirm_in_thread, svc, order1, tenant_id)
            f2 = executor.submit(self._confirm_in_thread, svc, order2, tenant_id)

            r1 = f1.result(timeout=5)
            r2 = f2.result(timeout=5)

        # Both must succeed (no deadlock, no timeout)
        assert isinstance(r1, dict), f"Order 1 failed: {r1}"
        assert isinstance(r2, dict), f"Order 2 failed: {r2}"

        # Both CONFIRMED
        order1.refresh_from_db()
        order2.refresh_from_db()
        assert order1.status == SaleOrderStatus.CONFIRMED
        assert order2.status == SaleOrderStatus.CONFIRMED

        # Verify stock: each product reserved 2+2=4
        snap_a = StockSnapshot.objects.get(product=product_a, branch=branch)
        snap_b = StockSnapshot.objects.get(product=product_b, branch=branch)
        assert snap_a.reserved_quantity == Decimal("4.0000")
        assert snap_b.reserved_quantity == Decimal("4.0000")


# ============================================================
# T090+T091: End-to-end flow
# ============================================================


@pytest.mark.django_db
class TestSaleLifecycleFlow:
    """Complete sale lifecycle: DRAFT → CONFIRMED → INVOICED."""

    @pytest.mark.integration
    def test_full_lifecycle_draft_to_invoiced(
        self, sale_service, draft_order_with_items, admin_user,
        arca_credential, punto_de_venta,
    ):
        """Full flow: create → confirm → authorize."""
        order = draft_order_with_items

        # Step 1: Confirm
        confirm_result = sale_service.confirm_sale(order=order, user=admin_user)
        order.refresh_from_db()
        assert order.status == SaleOrderStatus.CONFIRMED
        assert "comprobante" in confirm_result

        # Step 2: Authorize
        auth_result = sale_service.authorize_sale(order=order)
        order.refresh_from_db()
        assert order.status == SaleOrderStatus.INVOICED
        assert auth_result["cae"] is not None

    @pytest.mark.integration
    def test_invoiced_order_is_immutable(
        self, sale_service, draft_order_with_items, admin_user,
        arca_credential, punto_de_venta,
    ):
        """INVOICED order cannot be modified (model-level enforcement)."""
        order = draft_order_with_items

        sale_service.confirm_sale(order=order, user=admin_user)
        order.refresh_from_db()
        sale_service.authorize_sale(order=order)
        order.refresh_from_db()

        assert order.status == SaleOrderStatus.INVOICED

        # Attempting to modify an INVOICED order should raise ValueError
        order.subtotal = Decimal("999.000")
        with pytest.raises(ValueError, match="Cannot modify invoiced"):
            order.save()
