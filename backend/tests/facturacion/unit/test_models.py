"""
Unit tests for facturacion models.

Covers T018 (ARCACredential), T033 (Comprobante immutability),
and T049b (CAEA-mode invoice unit tests).

T018: Unique constraint (tenant_id, is_production), EncryptedTextField storage,
      CUIT field constraints, certificate expiration system check (arca.W001).
T033: save() raises ValueError for AUTORIZADO/OBSERVADO, delete() always raises,
      DRAFT/RECHAZADO can be updated.
T049b: Comprobante with caea FK stored as DRAFT, batch report transitions
       (DRAFT→AUTORIZADO, DRAFT→RECHAZADO), immutability after authorization.

Spec source: specs/invoice-backend-developement/tasks.md
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.checks import Warning
from django.db import IntegrityError
from django.utils import timezone

from django.db import models as db_models

from apps.facturacion.apps import check_certificate_expiration
from apps.facturacion.constants import ComprobanteStatus, IMMUTABLE_STATUSES
from tests.facturacion.conftest import TEST_CUIT


# ============================================================
# T018: ARCACredential Model Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestARCACredentialModel:
    """Tests for ARCACredential model fields and constraints."""

    def test_create_credential(self, credential_factory):
        """Basic credential creation succeeds."""
        cred = credential_factory()
        assert cred.pk is not None
        assert cred.cuit_holder == TEST_CUIT
        assert cred.is_production is False
        assert cred.is_active is True

    def test_unique_constraint_tenant_env(self, credential_factory):
        """Two credentials with same (tenant, is_production) raises IntegrityError."""
        credential_factory(is_production=False)
        with pytest.raises(IntegrityError):
            credential_factory(is_production=False)

    def test_different_environments_allowed(self, credential_factory):
        """Same tenant can have one production and one homologation credential."""
        homo = credential_factory(is_production=False)
        prod = credential_factory(is_production=True)
        assert homo.pk != prod.pk
        assert homo.is_production is False
        assert prod.is_production is True

    def test_encrypted_field_storage_roundtrip(self, credential_factory):
        """Private key stored via EncryptedTextField is retrievable."""
        from apps.facturacion.models import ARCACredential

        cred = credential_factory()
        # Re-fetch from DB to verify encryption/decryption roundtrip
        fetched = ARCACredential.all_objects.get(pk=cred.pk)
        assert "BEGIN RSA PRIVATE KEY" in fetched.private_key_pem
        assert fetched.private_key_pem == cred.private_key_pem

    def test_encrypted_field_not_plaintext_in_db(self, credential_factory):
        """Private key should not be stored as plaintext in database."""
        from django.db import connection

        cred = credential_factory()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT private_key_pem FROM facturacion_arcacredential WHERE id = %s",
                [str(cred.pk)],
            )
            row = cursor.fetchone()
            # The raw DB value should NOT contain the PEM header if encrypted
            raw_value = row[0] if row else ""
            assert raw_value != cred.private_key_pem or "BEGIN RSA PRIVATE KEY" not in str(
                raw_value
            ), "Private key appears to be stored in plaintext"

    def test_cuit_holder_max_length(self, credential_factory):
        """CUIT holder field enforces max_length=11."""
        from apps.facturacion.models import ARCACredential

        cred = credential_factory()
        field = ARCACredential._meta.get_field("cuit_holder")
        assert field.max_length == 11

    def test_cuit_represented_nullable(self, credential_factory):
        """cuit_represented can be null (no delegation)."""
        cred = credential_factory(cuit_represented=None)
        assert cred.cuit_represented is None

    def test_cuit_represented_with_value(self, credential_factory):
        """cuit_represented stores delegation CUIT."""
        cred = credential_factory(cuit_represented="30999888770")
        assert cred.cuit_represented == "30999888770"

    def test_last_unique_id_default_zero(self, credential_factory):
        """last_unique_id defaults to 0 for new credentials."""
        cred = credential_factory()
        assert cred.last_unique_id == 0

    def test_last_unique_id_increment(self, credential_factory):
        """last_unique_id can be updated (for TRA replay protection)."""
        from apps.facturacion.models import ARCACredential

        cred = credential_factory(last_unique_id=1000)
        cred.last_unique_id = 1001
        cred.save()
        refreshed = ARCACredential.all_objects.get(pk=cred.pk)
        assert refreshed.last_unique_id == 1001

    def test_str_homologation(self, credential_factory):
        """__str__ shows HOMO for non-production credentials."""
        cred = credential_factory(is_production=False)
        assert "HOMO" in str(cred)
        assert TEST_CUIT in str(cred)

    def test_str_production(self, credential_factory):
        """__str__ shows PROD for production credentials."""
        cred = credential_factory(is_production=True)
        assert "PROD" in str(cred)

    def test_soft_disable(self, credential_factory):
        """Setting is_active=False soft-disables without deletion."""
        cred = credential_factory(is_active=True)
        cred.is_active = False
        cred.save()
        assert cred.is_active is False

    def test_certificate_expires_at_stores_datetime(self, credential_factory):
        """certificate_expires_at stores timezone-aware datetime."""
        future = timezone.now() + timedelta(days=365)
        cred = credential_factory(certificate_expires_at=future)
        assert cred.certificate_expires_at is not None
        # Within a second tolerance
        assert abs((cred.certificate_expires_at - future).total_seconds()) < 1

    def test_certificate_expires_at_nullable(self, credential_factory):
        """certificate_expires_at can be null."""
        cred = credential_factory(certificate_expires_at=None)
        assert cred.certificate_expires_at is None

    def test_timestamps_auto(self, credential_factory):
        """created_at and updated_at are auto-populated."""
        cred = credential_factory()
        assert cred.created_at is not None
        assert cred.updated_at is not None


# ============================================================
# T018: Certificate Expiration System Check Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestCertificateExpirationCheck:
    """Tests for the arca.W001 system check (certificate expiration warning)."""

    def test_no_warnings_when_cert_far_from_expiry(self, credential_factory):
        """No warnings when certificate expires in >30 days."""
        credential_factory(certificate_expires_at=timezone.now() + timedelta(days=365))
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 0

    def test_warning_when_cert_expires_within_30_days(self, credential_factory):
        """Warning raised when active cert expires in <30 days."""
        credential_factory(certificate_expires_at=timezone.now() + timedelta(days=15))
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 1
        assert isinstance(warnings[0], Warning)
        assert warnings[0].id == "arca.W001"
        assert "expires in" in warnings[0].msg

    def test_warning_when_cert_expires_tomorrow(self, credential_factory):
        """Warning raised for cert expiring in 1 day."""
        credential_factory(certificate_expires_at=timezone.now() + timedelta(days=1))
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 1
        assert "1 day" in warnings[0].msg or "expires in" in warnings[0].msg

    def test_no_warning_for_inactive_cert(self, credential_factory):
        """Inactive credentials don't trigger warnings."""
        credential_factory(
            certificate_expires_at=timezone.now() + timedelta(days=5),
            is_active=False,
        )
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 0

    def test_no_warning_for_null_expiry(self, credential_factory):
        """Credentials without expiration date don't trigger warnings."""
        credential_factory(certificate_expires_at=None)
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 0

    def test_warning_includes_hint(self, credential_factory):
        """Warning includes rotation hint."""
        credential_factory(certificate_expires_at=timezone.now() + timedelta(days=10))
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 1
        assert "Rotate" in warnings[0].hint

    def test_multiple_expiring_certs(self, credential_factory):
        """Multiple expiring certs produce multiple warnings."""
        # homologation cert expiring
        credential_factory(
            is_production=False,
            certificate_expires_at=timezone.now() + timedelta(days=5),
        )
        # production cert expiring
        credential_factory(
            is_production=True,
            certificate_expires_at=timezone.now() + timedelta(days=10),
        )
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 2

    def test_warning_distinguishes_environment(self, credential_factory):
        """Warning message identifies production vs homologation."""
        credential_factory(
            is_production=True,
            certificate_expires_at=timezone.now() + timedelta(days=5),
        )
        warnings = check_certificate_expiration(None)
        assert len(warnings) == 1
        assert "production" in warnings[0].msg


# ============================================================
# T018: PuntoDeVenta Model Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestPuntoDeVentaModel:
    """Tests for PuntoDeVenta model fields and constraints."""

    def test_create_punto_venta(self, punto_venta_factory):
        """Basic PuntoDeVenta creation succeeds."""
        pv = punto_venta_factory(numero=1)
        assert pv.pk is not None
        assert pv.numero == 1
        assert pv.is_active is True

    def test_unique_constraint_tenant_numero(self, punto_venta_factory):
        """Two PtoVta with same (tenant, numero) raises IntegrityError."""
        punto_venta_factory(numero=5)
        with pytest.raises(IntegrityError):
            punto_venta_factory(numero=5)

    def test_different_numeros_allowed(self, punto_venta_factory):
        """Same tenant can have multiple PtoVta with different numbers."""
        pv1 = punto_venta_factory(numero=1)
        pv2 = punto_venta_factory(numero=2)
        assert pv1.pk != pv2.pk

    def test_str_format(self, punto_venta_factory):
        """__str__ shows zero-padded PtoVta number."""
        pv = punto_venta_factory(numero=1)
        assert str(pv) == "PtoVta 00001"

    def test_str_large_number(self, punto_venta_factory):
        """__str__ with large PtoVta number."""
        pv = punto_venta_factory(numero=99999)
        assert str(pv) == "PtoVta 99999"

    def test_numero_range_check_constraint_field(self, punto_venta_factory):
        """PuntoDeVenta has a check constraint for numero range 1-99999."""
        from apps.facturacion.models import PuntoDeVenta

        check_constraints = [
            c for c in PuntoDeVenta._meta.constraints
            if isinstance(c, db_models.CheckConstraint)
        ]
        assert len(check_constraints) == 1
        assert check_constraints[0].name == "ck_punto_venta_range"

    def test_tipo_default_electronic(self, punto_venta_factory):
        """Default tipo is 'electronic'."""
        pv = punto_venta_factory()
        assert pv.tipo == "electronic"


# ============================================================
# T033: Comprobante Immutability Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestComprobanteImmutability:
    """
    Tests for Comprobante immutability enforcement.

    Rules:
    - AUTORIZADO (CAE obtained): immutable — save() raises ValueError
    - OBSERVADO (CAE with warnings): immutable — save() raises ValueError
    - DRAFT (not yet submitted): mutable
    - RECHAZADO (rejected): mutable (allows retry)
    - delete() always raises ValueError (fiscal records are permanent)
    """

    def test_authorized_cannot_be_modified(self, authorized_comprobante):
        """save() on AUTORIZADO comprobante raises ValueError."""
        authorized_comprobante.imp_total = Decimal("999.000")
        with pytest.raises(ValueError, match="immutable"):
            authorized_comprobante.save()

    def test_observed_cannot_be_modified(self, observed_comprobante):
        """save() on OBSERVADO comprobante raises ValueError."""
        observed_comprobante.imp_total = Decimal("999.000")
        with pytest.raises(ValueError, match="immutable"):
            observed_comprobante.save()

    def test_authorized_status_change_raises(self, authorized_comprobante):
        """Cannot change status of AUTORIZADO comprobante."""
        authorized_comprobante.status = "RECHAZADO"
        with pytest.raises(ValueError, match="immutable"):
            authorized_comprobante.save()

    def test_observed_status_change_raises(self, observed_comprobante):
        """Cannot change status of OBSERVADO comprobante."""
        observed_comprobante.status = "DRAFT"
        with pytest.raises(ValueError, match="immutable"):
            observed_comprobante.save()

    def test_draft_can_be_updated(self, draft_comprobante):
        """DRAFT comprobante can be modified."""
        original_total = draft_comprobante.imp_total
        draft_comprobante.imp_total = Decimal("999.000")
        draft_comprobante.save()
        assert draft_comprobante.imp_total == Decimal("999.000")
        assert draft_comprobante.imp_total != original_total

    def test_draft_status_can_change_to_validando(self, draft_comprobante):
        """DRAFT can transition to VALIDANDO."""
        draft_comprobante.status = ComprobanteStatus.VALIDANDO
        draft_comprobante.save()
        assert draft_comprobante.status == ComprobanteStatus.VALIDANDO

    def test_rejected_can_be_updated(self, rejected_comprobante):
        """RECHAZADO comprobante can be modified (retry flow)."""
        rejected_comprobante.imp_total = Decimal("500.000")
        rejected_comprobante.save()
        assert rejected_comprobante.imp_total == Decimal("500.000")

    def test_rejected_can_change_status(self, rejected_comprobante):
        """RECHAZADO can transition to VALIDANDO (retry)."""
        rejected_comprobante.status = ComprobanteStatus.VALIDANDO
        rejected_comprobante.save()
        assert rejected_comprobante.status == ComprobanteStatus.VALIDANDO

    def test_validando_can_be_updated(self, comprobante_factory):
        """VALIDANDO comprobante can be modified (awaiting response)."""
        cbte = comprobante_factory(status=ComprobanteStatus.VALIDANDO)
        cbte.status = ComprobanteStatus.AUTORIZADO
        cbte.cae = "12345678901234"
        cbte.cae_fch_vto = date.today() + timedelta(days=10)
        cbte.save()
        assert cbte.status == ComprobanteStatus.AUTORIZADO

    def test_delete_draft_raises(self, draft_comprobante):
        """delete() on DRAFT raises ValueError — no fiscal deletion."""
        with pytest.raises(ValueError, match="cannot be deleted"):
            draft_comprobante.delete()

    def test_delete_authorized_raises(self, authorized_comprobante):
        """delete() on AUTORIZADO raises ValueError."""
        with pytest.raises(ValueError, match="cannot be deleted"):
            authorized_comprobante.delete()

    def test_delete_rejected_raises(self, rejected_comprobante):
        """delete() on RECHAZADO raises ValueError."""
        with pytest.raises(ValueError, match="cannot be deleted"):
            rejected_comprobante.delete()

    def test_delete_observed_raises(self, observed_comprobante):
        """delete() on OBSERVADO raises ValueError."""
        with pytest.raises(ValueError, match="cannot be deleted"):
            observed_comprobante.delete()

    def test_immutable_statuses_set(self):
        """IMMUTABLE_STATUSES contains exactly AUTORIZADO and OBSERVADO."""
        assert ComprobanteStatus.AUTORIZADO in IMMUTABLE_STATUSES
        assert ComprobanteStatus.OBSERVADO in IMMUTABLE_STATUSES
        assert len(IMMUTABLE_STATUSES) == 2
        assert ComprobanteStatus.DRAFT not in IMMUTABLE_STATUSES
        assert ComprobanteStatus.RECHAZADO not in IMMUTABLE_STATUSES
        assert ComprobanteStatus.VALIDANDO not in IMMUTABLE_STATUSES

    def test_new_comprobante_save_succeeds(self, comprobante_factory):
        """New comprobante (no pk yet persisted) can be saved."""
        cbte = comprobante_factory()
        assert cbte.pk is not None
        assert cbte.status == ComprobanteStatus.DRAFT


# ============================================================
# T033: Comprobante Unique Constraint Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestComprobanteConstraints:
    """Tests for Comprobante database constraints."""

    def test_unique_fiscal_key(self, comprobante_factory):
        """Duplicate (tenant, punto_venta, cbte_tipo, cbte_nro) raises IntegrityError."""
        comprobante_factory(cbte_tipo=6, cbte_nro=1)
        with pytest.raises(IntegrityError):
            comprobante_factory(cbte_tipo=6, cbte_nro=1)

    def test_different_cbte_tipo_allowed(self, comprobante_factory):
        """Same punto_venta and cbte_nro but different cbte_tipo is allowed."""
        cbte_a = comprobante_factory(cbte_tipo=1, cbte_nro=1)
        cbte_b = comprobante_factory(cbte_tipo=6, cbte_nro=1)
        assert cbte_a.pk != cbte_b.pk

    def test_different_cbte_nro_allowed(self, comprobante_factory):
        """Same punto_venta and cbte_tipo but different cbte_nro is allowed."""
        cbte_1 = comprobante_factory(cbte_tipo=6, cbte_nro=1)
        cbte_2 = comprobante_factory(cbte_tipo=6, cbte_nro=2)
        assert cbte_1.pk != cbte_2.pk

    def test_default_status_draft(self, comprobante_factory):
        """New comprobante defaults to DRAFT status."""
        cbte = comprobante_factory()
        assert cbte.status == ComprobanteStatus.DRAFT

    def test_default_currency_pes(self, comprobante_factory):
        """Default currency is PES (Argentine Peso)."""
        cbte = comprobante_factory()
        assert cbte.mon_id == "PES"
        assert cbte.mon_cotiz == Decimal("1.000000")


# ============================================================
# AlicIva, Tributo, CbteAsoc Model Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestChildEntityModels:
    """Tests for AlicIva, Tributo, CbteAsoc child models."""

    def test_alic_iva_creation(self, draft_comprobante, alic_iva_factory):
        """AlicIva can be created with parent comprobante."""
        iva = alic_iva_factory(
            comprobante=draft_comprobante,
            iva_id=5,
            base_imp=Decimal("100.000"),
            importe=Decimal("21.000"),
        )
        assert iva.pk is not None
        assert iva.comprobante_id == draft_comprobante.pk

    def test_alic_iva_str(self, draft_comprobante, alic_iva_factory):
        """AlicIva __str__ includes IVA code and amounts."""
        iva = alic_iva_factory(comprobante=draft_comprobante)
        assert "IVA" in str(iva)
        assert "5" in str(iva)

    def test_tributo_creation(self, draft_comprobante, tributo_factory):
        """Tributo can be created with parent comprobante."""
        trib = tributo_factory(comprobante=draft_comprobante)
        assert trib.pk is not None
        assert trib.comprobante_id == draft_comprobante.pk

    def test_tributo_str(self, draft_comprobante, tributo_factory):
        """Tributo __str__ includes description."""
        trib = tributo_factory(comprobante=draft_comprobante)
        assert "Ingresos Brutos" in str(trib)

    def test_cbte_asoc_creation(self, draft_comprobante, cbte_asoc_factory):
        """CbteAsoc can be created for NC/ND reference."""
        asoc = cbte_asoc_factory(comprobante=draft_comprobante)
        assert asoc.pk is not None
        assert asoc.comprobante_id == draft_comprobante.pk

    def test_cbte_asoc_str(self, draft_comprobante, cbte_asoc_factory):
        """CbteAsoc __str__ shows associated document key."""
        asoc = cbte_asoc_factory(comprobante=draft_comprobante, tipo=6, pto_vta=1, nro=1)
        result = str(asoc)
        assert "Asoc" in result
        assert "00001" in result


# ============================================================
# CAEA Model Tests
# ============================================================


@pytest.mark.unit
@pytest.mark.django_db
class TestCAEAModel:
    """Tests for CAEA model fields and constraints."""

    def test_create_caea(self, caea_factory):
        """Basic CAEA creation succeeds."""
        caea = caea_factory()
        assert caea.pk is not None
        assert caea.status == "ACTIVE"

    def test_unique_constraint_period(self, caea_factory):
        """Duplicate (tenant, punto_venta, periodo, orden) raises IntegrityError."""
        caea_factory(periodo="202602", orden=1)
        with pytest.raises(IntegrityError):
            caea_factory(periodo="202602", orden=1)

    def test_different_orden_allowed(self, caea_factory):
        """Same periodo but different orden is allowed."""
        q1 = caea_factory(periodo="202602", orden=1)
        q2 = caea_factory(periodo="202602", orden=2)
        assert q1.pk != q2.pk

    def test_caea_code_unique(self, caea_factory):
        """caea_code is globally unique."""
        from apps.facturacion.models import CAEA

        field = CAEA._meta.get_field("caea_code")
        assert field.unique is True

    def test_str_format(self, caea_factory):
        """__str__ includes CAEA code and period info."""
        caea = caea_factory(periodo="202602", orden=1)
        result = str(caea)
        assert "CAEA" in result
        assert "202602" in result
        assert "Q1" in result


# ============================================================
# T049b: CAEA-Mode Invoice Unit Tests
# ============================================================


@pytest.mark.django_db
class TestCAEAModeComprobante:
    """
    Test comprobante behavior in CAEA (offline) mode.

    CAEA-mode comprobantes are stored as DRAFT with a caea FK,
    then batch-reported to ARCA via FECAEARegInformativo.
    """

    def test_comprobante_with_caea_fk_stored_as_draft(
        self, comprobante_factory, caea_factory
    ):
        """CAEA-mode comprobante starts as DRAFT with caea FK."""
        caea = caea_factory()
        cbte = comprobante_factory(
            cbte_nro=600,
            caea=caea,
            status="DRAFT",
        )
        assert cbte.status == "DRAFT"
        assert cbte.caea == caea
        assert cbte.cae is None  # No CAE yet — pending batch report

    def test_caea_comprobante_no_cae_initially(
        self, comprobante_factory, caea_factory
    ):
        """CAEA-mode comprobante has no CAE before batch report."""
        caea = caea_factory()
        cbte = comprobante_factory(cbte_nro=601, caea=caea, status="DRAFT")
        assert cbte.cae is None
        assert cbte.cae_fch_vto is None

    def test_batch_report_transitions_draft_to_autorizado(
        self, comprobante_factory, caea_factory
    ):
        """After batch report succeeds, DRAFT → AUTORIZADO with CAE."""
        caea = caea_factory(caea_code="11112222333344")
        cbte = comprobante_factory(cbte_nro=602, caea=caea, status="DRAFT")

        # Simulate batch report success
        cbte.status = "AUTORIZADO"
        cbte.cae = caea.caea_code
        cbte.cae_fch_vto = caea.fch_vig_hasta
        cbte.save()

        cbte.refresh_from_db()
        assert cbte.status == "AUTORIZADO"
        assert cbte.cae == "11112222333344"
        assert cbte.cae_fch_vto == caea.fch_vig_hasta

    def test_batch_report_autorizado_becomes_immutable(
        self, comprobante_factory, caea_factory
    ):
        """Once AUTORIZADO after batch report, comprobante is immutable."""
        caea = caea_factory(caea_code="55556666777788")
        cbte = comprobante_factory(cbte_nro=603, caea=caea, status="DRAFT")

        # Authorize via batch report
        cbte.status = "AUTORIZADO"
        cbte.cae = caea.caea_code
        cbte.cae_fch_vto = caea.fch_vig_hasta
        cbte.save()

        # Now it should be immutable
        cbte.imp_total = Decimal("999.999")
        with pytest.raises(ValueError, match="Cannot modify"):
            cbte.save()

    def test_batch_report_rejection_keeps_mutable(
        self, comprobante_factory, caea_factory
    ):
        """Rejected batch comprobantes stay mutable for retry."""
        caea = caea_factory()
        cbte = comprobante_factory(cbte_nro=604, caea=caea, status="DRAFT")

        # Simulate rejection
        cbte.status = "RECHAZADO"
        cbte.save()

        cbte.refresh_from_db()
        assert cbte.status == "RECHAZADO"

        # Should still be mutable — can retry
        cbte.status = "DRAFT"
        cbte.save()
        cbte.refresh_from_db()
        assert cbte.status == "DRAFT"

    def test_multiple_comprobantes_linked_to_same_caea(
        self, comprobante_factory, caea_factory
    ):
        """Multiple offline comprobantes can reference the same CAEA."""
        caea = caea_factory()
        cbtes = [
            comprobante_factory(cbte_nro=700 + i, caea=caea, status="DRAFT")
            for i in range(5)
        ]
        assert all(c.caea_id == caea.pk for c in cbtes)
        assert caea.comprobantes.count() == 5

    def test_caea_fk_is_nullable(self, comprobante_factory):
        """Online (non-CAEA) comprobantes have caea=None."""
        cbte = comprobante_factory(cbte_nro=800, status="DRAFT")
        assert cbte.caea is None

    def test_caea_on_delete_restrict(self):
        """CAEA FK uses RESTRICT — cannot delete CAEA with linked comprobantes."""
        from apps.facturacion.models import Comprobante

        caea_field = Comprobante._meta.get_field("caea")
        assert caea_field.remote_field.on_delete.__name__ == "RESTRICT"
