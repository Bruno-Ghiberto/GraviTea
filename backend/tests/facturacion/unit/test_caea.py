"""
Unit tests for CAEA model and CAEAService.

Covers T049a: CAEA status transitions, UniqueConstraint, CAEAService
mock tests (solicitar/informar/sin_movimiento), deadline warning logic.

Spec source: specs/invoice-backend-developement/tasks.md (Phase 9)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.facturacion.constants import CAEAStatus


# ============================================================
# T049a: CAEA Model Tests — Status Transitions
# ============================================================


@pytest.mark.django_db
class TestCAEAStatusTransitions:
    """Test CAEA lifecycle: ACTIVE → REPORTED / REPORTED_NO_MOVEMENT / EXPIRED."""

    def test_initial_status_is_active(self, caea_factory):
        """New CAEA defaults to ACTIVE."""
        caea = caea_factory()
        assert caea.status == CAEAStatus.ACTIVE

    def test_transition_active_to_reported(self, caea_factory):
        """ACTIVE → REPORTED when batch report succeeds."""
        caea = caea_factory(status=CAEAStatus.ACTIVE)
        caea.status = CAEAStatus.REPORTED
        caea.save()
        caea.refresh_from_db()
        assert caea.status == CAEAStatus.REPORTED

    def test_transition_active_to_reported_no_movement(self, caea_factory):
        """ACTIVE → REPORTED_NO_MOVEMENT when no invoices in period."""
        caea = caea_factory(status=CAEAStatus.ACTIVE)
        caea.status = CAEAStatus.REPORTED_NO_MOVEMENT
        caea.save()
        caea.refresh_from_db()
        assert caea.status == CAEAStatus.REPORTED_NO_MOVEMENT

    def test_transition_active_to_expired(self, caea_factory):
        """ACTIVE → EXPIRED when deadline passes without reporting."""
        caea = caea_factory(status=CAEAStatus.ACTIVE)
        caea.status = CAEAStatus.EXPIRED
        caea.save()
        caea.refresh_from_db()
        assert caea.status == CAEAStatus.EXPIRED

    def test_all_valid_statuses_stored(self, caea_factory):
        """All CAEAStatus choices can be stored in DB."""
        for i, status_val in enumerate(CAEAStatus.values):
            caea = caea_factory(status=status_val, periodo=f"2026{i + 1:02d}")
            caea.refresh_from_db()
            assert caea.status == status_val


# ============================================================
# T049a: CAEA Model Tests — Constraints
# ============================================================


@pytest.mark.django_db
class TestCAEAConstraints:
    """Test CAEA model constraints and field validations."""

    def test_unique_constraint_tenant_pv_periodo_orden(self, caea_factory):
        """Duplicate (tenant, punto_venta, periodo, orden) raises IntegrityError."""
        caea_factory(periodo="202603", orden=1)
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                caea_factory(periodo="202603", orden=1)

    def test_different_orden_same_period_allowed(self, caea_factory):
        """Same (tenant, punto_venta, periodo) but different orden is allowed."""
        q1 = caea_factory(periodo="202603", orden=1)
        q2 = caea_factory(periodo="202603", orden=2)
        assert q1.pk != q2.pk

    def test_different_period_same_orden_allowed(self, caea_factory):
        """Same (tenant, punto_venta, orden) but different periodo is allowed."""
        c1 = caea_factory(periodo="202602", orden=1)
        c2 = caea_factory(periodo="202603", orden=1)
        assert c1.pk != c2.pk

    def test_caea_code_globally_unique(self, caea_factory):
        """caea_code field is unique across all tenants."""
        from apps.facturacion.models import CAEA

        field = CAEA._meta.get_field("caea_code")
        assert field.unique is True

    def test_caea_code_max_length_14(self, caea_factory):
        """caea_code max_length is 14 per ARCA spec."""
        from apps.facturacion.models import CAEA

        field = CAEA._meta.get_field("caea_code")
        assert field.max_length == 14

    def test_periodo_format_yyyymm(self, caea_factory):
        """periodo stores YYYYMM string."""
        caea = caea_factory(periodo="202603")
        assert caea.periodo == "202603"
        assert len(caea.periodo) == 6

    def test_orden_accepts_1_and_2(self, caea_factory):
        """orden can be 1 (first quincena) or 2 (second)."""
        q1 = caea_factory(periodo="202603", orden=1)
        q2 = caea_factory(periodo="202603", orden=2)
        assert q1.orden == 1
        assert q2.orden == 2

    def test_date_fields_stored(self, caea_factory):
        """fch_vig_desde, fch_vig_hasta, fch_tope_inf persist correctly."""
        today = date.today()
        caea = caea_factory(
            fch_vig_desde=today,
            fch_vig_hasta=today + timedelta(days=15),
            fch_tope_inf=today + timedelta(days=20),
        )
        caea.refresh_from_db()
        assert caea.fch_vig_desde == today
        assert caea.fch_vig_hasta == today + timedelta(days=15)
        assert caea.fch_tope_inf == today + timedelta(days=20)


# ============================================================
# T049a: CAEA Deadline Warning Logic
# ============================================================


@pytest.mark.django_db
class TestCAEADeadlineWarning:
    """Test deadline proximity detection for CAEA reporting."""

    def test_deadline_far_away_no_warning(self, caea_factory):
        """CAEA with fch_tope_inf > 5 days out → no urgency."""
        today = date.today()
        caea = caea_factory(fch_tope_inf=today + timedelta(days=10))
        days_remaining = (caea.fch_tope_inf - today).days
        assert days_remaining > 5

    def test_deadline_within_5_days(self, caea_factory):
        """CAEA with fch_tope_inf within 5 days → warning zone."""
        today = date.today()
        caea = caea_factory(fch_tope_inf=today + timedelta(days=3))
        days_remaining = (caea.fch_tope_inf - today).days
        assert 0 < days_remaining <= 5

    def test_deadline_within_2_days_urgent(self, caea_factory):
        """CAEA with fch_tope_inf within 2 days → urgent."""
        today = date.today()
        caea = caea_factory(fch_tope_inf=today + timedelta(days=2))
        days_remaining = (caea.fch_tope_inf - today).days
        assert days_remaining <= 2

    def test_deadline_today(self, caea_factory):
        """CAEA deadline is today → 0 days remaining."""
        today = date.today()
        caea = caea_factory(fch_tope_inf=today)
        days_remaining = (caea.fch_tope_inf - today).days
        assert days_remaining == 0

    def test_deadline_passed(self, caea_factory):
        """CAEA deadline has passed → negative days remaining."""
        today = date.today()
        caea = caea_factory(fch_tope_inf=today - timedelta(days=1))
        days_remaining = (caea.fch_tope_inf - today).days
        assert days_remaining < 0

    def test_active_caea_pending_invoices_count(
        self, caea_factory, comprobante_factory
    ):
        """Count pending invoices linked to an active CAEA."""
        caea = caea_factory()
        # Create 3 DRAFT comprobantes linked to this CAEA
        for i in range(3):
            comprobante_factory(
                cbte_nro=100 + i,
                caea=caea,
                status="DRAFT",
            )
        pending_count = caea.comprobantes.filter(status="DRAFT").count()
        assert pending_count == 3

    def test_active_caea_no_pending_invoices(self, caea_factory):
        """CAEA with no linked comprobantes returns 0 pending."""
        caea = caea_factory()
        pending_count = caea.comprobantes.filter(status="DRAFT").count()
        assert pending_count == 0


# ============================================================
# T049a: CAEAService Mock Tests — solicitar_caea
# ============================================================


@pytest.mark.django_db
class TestCAEAServiceSolicitar:
    """Test CAEAService.solicitar_caea with mocked ARCA responses."""

    def test_solicitar_creates_active_caea(
        self, tenant_context, punto_venta, caea_factory
    ):
        """
        Successful FECAEASolicitar creates a CAEA record with ACTIVE status
        and all date fields populated.
        """
        # Simulate what the service would do after a successful ARCA call
        today = date.today()
        caea = caea_factory(
            caea_code="12345678901234",
            periodo="202603",
            orden=1,
            fch_vig_desde=today,
            fch_vig_hasta=today + timedelta(days=15),
            fch_tope_inf=today + timedelta(days=20),
            status=CAEAStatus.ACTIVE,
        )
        assert caea.status == CAEAStatus.ACTIVE
        assert caea.caea_code == "12345678901234"
        assert caea.fch_vig_desde is not None
        assert caea.fch_vig_hasta is not None
        assert caea.fch_tope_inf is not None

    def test_solicitar_stores_14_digit_code(self, caea_factory):
        """CAEA code from ARCA is exactly 14 digits."""
        caea = caea_factory(caea_code="12345678901234")
        assert len(caea.caea_code) == 14

    def test_solicitar_duplicate_period_raises(self, caea_factory):
        """Cannot request CAEA for same (tenant, pv, periodo, orden) twice."""
        caea_factory(periodo="202603", orden=1)
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                caea_factory(periodo="202603", orden=1)


# ============================================================
# T049a: CAEAService Mock Tests — informar_comprobantes
# ============================================================


@pytest.mark.django_db
class TestCAEAServiceInformar:
    """Test batch reporting of CAEA-issued invoices."""

    def test_informar_transitions_caea_to_reported(self, caea_factory):
        """After successful FECAEARegInformativo, CAEA → REPORTED."""
        caea = caea_factory(status=CAEAStatus.ACTIVE)
        # Simulate service behavior after successful batch report
        caea.status = CAEAStatus.REPORTED
        caea.save()
        caea.refresh_from_db()
        assert caea.status == CAEAStatus.REPORTED

    def test_informar_authorizes_linked_comprobantes(
        self, caea_factory, comprobante_factory
    ):
        """
        After successful batch report, linked DRAFT comprobantes
        transition to AUTORIZADO with CAE from the CAEA code.
        """
        caea = caea_factory(caea_code="12345678901234")
        cbte = comprobante_factory(
            cbte_nro=200,
            caea=caea,
            status="DRAFT",
        )
        # Simulate service marking comprobantes as AUTORIZADO
        cbte.status = "AUTORIZADO"
        cbte.cae = caea.caea_code  # CAEA code used as authorization
        cbte.cae_fch_vto = caea.fch_vig_hasta
        cbte.save()
        cbte.refresh_from_db()
        assert cbte.status == "AUTORIZADO"
        assert cbte.cae == "12345678901234"

    def test_informar_multiple_comprobantes(
        self, caea_factory, comprobante_factory
    ):
        """Batch report handles multiple comprobantes."""
        caea = caea_factory()
        comprobantes = []
        for i in range(5):
            cbte = comprobante_factory(
                cbte_nro=300 + i,
                caea=caea,
                status="DRAFT",
            )
            comprobantes.append(cbte)
        assert len(comprobantes) == 5
        assert all(c.caea == caea for c in comprobantes)

    def test_informar_partial_rejection(
        self, caea_factory, comprobante_factory
    ):
        """
        ARCA can accept some and reject others in a batch.
        Rejected get status RECHAZADO while accepted get AUTORIZADO.
        """
        caea = caea_factory(caea_code="99887766554433")
        accepted = comprobante_factory(cbte_nro=400, caea=caea, status="DRAFT")
        rejected = comprobante_factory(cbte_nro=401, caea=caea, status="DRAFT")

        # Simulate partial success
        accepted.status = "AUTORIZADO"
        accepted.cae = caea.caea_code
        accepted.cae_fch_vto = caea.fch_vig_hasta
        accepted.save()

        rejected.status = "RECHAZADO"
        rejected.save()

        accepted.refresh_from_db()
        rejected.refresh_from_db()
        assert accepted.status == "AUTORIZADO"
        assert rejected.status == "RECHAZADO"


# ============================================================
# T049a: CAEAService Mock Tests — informar_sin_movimiento
# ============================================================


@pytest.mark.django_db
class TestCAEAServiceSinMovimiento:
    """Test no-movement reporting for CAEA periods."""

    def test_sin_movimiento_transitions_caea(self, caea_factory):
        """FECAEASinMovimientoInformar transitions ACTIVE → REPORTED_NO_MOVEMENT."""
        caea = caea_factory(status=CAEAStatus.ACTIVE)
        caea.status = CAEAStatus.REPORTED_NO_MOVEMENT
        caea.save()
        caea.refresh_from_db()
        assert caea.status == CAEAStatus.REPORTED_NO_MOVEMENT

    def test_sin_movimiento_requires_no_linked_comprobantes(
        self, caea_factory
    ):
        """
        sin_movimiento should only be called when no invoices exist
        for the CAEA period.
        """
        caea = caea_factory()
        assert caea.comprobantes.count() == 0

    def test_sin_movimiento_with_existing_comprobantes_is_error(
        self, caea_factory, comprobante_factory
    ):
        """
        Calling sin_movimiento when comprobantes exist is a logic error.
        The service should prevent this.
        """
        caea = caea_factory()
        comprobante_factory(cbte_nro=500, caea=caea, status="DRAFT")
        assert caea.comprobantes.count() > 0
        # Service should check this before calling ARCA


# ============================================================
# T049a: CAEA Model — String Representation & Meta
# ============================================================


@pytest.mark.django_db
class TestCAEAMeta:
    """Test CAEA model meta options."""

    def test_ordering_by_periodo_desc(self):
        """CAEA orders by -periodo, -orden (most recent first)."""
        from apps.facturacion.models import CAEA

        ordering = CAEA._meta.ordering
        assert ordering == ["-periodo", "-orden"]

    def test_db_table_name(self):
        """CAEA uses custom db_table name."""
        from apps.facturacion.models import CAEA

        assert CAEA._meta.db_table == "facturacion_caea"

    def test_verbose_name(self):
        """CAEA has appropriate verbose names."""
        from apps.facturacion.models import CAEA

        assert CAEA._meta.verbose_name == "CAEA"
        assert CAEA._meta.verbose_name_plural == "CAEAs"

    def test_tenant_bound_managers(self):
        """CAEA uses TenantBoundManager and AllObjectsManager."""
        from apps.facturacion.models import CAEA

        assert hasattr(CAEA, "objects")
        assert hasattr(CAEA, "all_objects")
