"""Tests for Romaneo model, state machine, and immutability."""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.acopio.models import Romaneo


@pytest.mark.django_db
class TestRomaneoCreation:
    """Test romaneo creation and field defaults."""

    def test_create_romaneo_pendiente(self, romaneo_factory):
        """Romaneo is created in PENDIENTE status by default."""
        r = romaneo_factory()
        assert r.status == Romaneo.RomaneoStatus.PENDIENTE
        assert r.pk is not None
        assert r.ts_entrada is not None

    def test_romaneo_number_auto_generated(self, romaneo_factory):
        """romaneo_number is auto-generated in ROM-YYYY-NNNNN format."""
        r = romaneo_factory()
        year = timezone.now().year
        assert r.romaneo_number.startswith(f"ROM-{year}-")
        assert len(r.romaneo_number.split("-")[-1]) == 5

    def test_romaneo_number_sequential(self, romaneo_factory):
        """Successive romaneos get sequential numbers."""
        r1 = romaneo_factory()
        r2 = romaneo_factory()
        seq1 = int(r1.romaneo_number.split("-")[-1])
        seq2 = int(r2.romaneo_number.split("-")[-1])
        assert seq2 == seq1 + 1

    def test_romaneo_str(self, romaneo_factory):
        """__str__ returns number and status."""
        r = romaneo_factory()
        assert r.romaneo_number in str(r)
        assert "PENDIENTE" in str(r)


@pytest.mark.django_db
class TestRomaneoStateMachine:
    """Test valid and invalid state transitions."""

    def test_valid_transition_pendiente_to_en_proceso(self, romaneo_factory):
        r = romaneo_factory()
        r.status = Romaneo.RomaneoStatus.EN_PROCESO
        r.save()
        r.refresh_from_db()
        assert r.status == Romaneo.RomaneoStatus.EN_PROCESO

    def test_valid_transition_en_proceso_to_pesado(self, romaneo_en_proceso):
        romaneo_en_proceso.peso_bruto_kg = Decimal("30000.000")
        romaneo_en_proceso.ts_pesada_bruta = timezone.now()
        romaneo_en_proceso.status = Romaneo.RomaneoStatus.PESADO
        romaneo_en_proceso.save()
        romaneo_en_proceso.refresh_from_db()
        assert romaneo_en_proceso.status == Romaneo.RomaneoStatus.PESADO

    def test_valid_transition_pesado_to_analizado(self, romaneo_pesado):
        romaneo_pesado.ts_analisis = timezone.now()
        romaneo_pesado.status = Romaneo.RomaneoStatus.ANALIZADO
        romaneo_pesado.save()
        romaneo_pesado.refresh_from_db()
        assert romaneo_pesado.status == Romaneo.RomaneoStatus.ANALIZADO

    def test_valid_full_lifecycle(self, romaneo_factory):
        """Walk through all 6 states in sequence."""
        r = romaneo_factory()
        transitions = [
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
            Romaneo.RomaneoStatus.CONFORME,
            Romaneo.RomaneoStatus.CERRADO,
        ]
        for new_status in transitions:
            r.status = new_status
            r.save()
            r.refresh_from_db()
            assert r.status == new_status

    def test_invalid_skip_pendiente_to_pesado(self, romaneo_factory):
        r = romaneo_factory()
        r.status = Romaneo.RomaneoStatus.PESADO
        with pytest.raises(ValueError, match="Invalid state transition"):
            r.save()

    def test_invalid_skip_pendiente_to_analizado(self, romaneo_factory):
        r = romaneo_factory()
        r.status = Romaneo.RomaneoStatus.ANALIZADO
        with pytest.raises(ValueError, match="Invalid state transition"):
            r.save()

    def test_invalid_skip_en_proceso_to_conforme(self, romaneo_en_proceso):
        romaneo_en_proceso.status = Romaneo.RomaneoStatus.CONFORME
        with pytest.raises(ValueError, match="Invalid state transition"):
            romaneo_en_proceso.save()

    def test_invalid_backward_pesado_to_en_proceso(self, romaneo_pesado):
        romaneo_pesado.status = Romaneo.RomaneoStatus.EN_PROCESO
        with pytest.raises(ValueError, match="Invalid state transition"):
            romaneo_pesado.save()

    def test_invalid_backward_conforme_to_analizado(self, romaneo_factory):
        """Backward transition from CONFORME is rejected by state machine."""
        r = romaneo_factory()
        for s in [
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
            Romaneo.RomaneoStatus.CONFORME,
        ]:
            r.status = s
            r.save()
        r.status = Romaneo.RomaneoStatus.ANALIZADO
        with pytest.raises(ValueError, match="Invalid state transition"):
            r.save()


@pytest.mark.django_db
class TestRomaneoImmutability:
    """Test CONFORME and CERRADO immutability gates."""

    def _make_conforme(self, romaneo_factory):
        r = romaneo_factory()
        for s in [
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
            Romaneo.RomaneoStatus.CONFORME,
        ]:
            r.status = s
            r.save()
        return r

    def test_conforme_blocks_field_changes(self, romaneo_factory):
        """Cannot change most fields at CONFORME."""
        r = self._make_conforme(romaneo_factory)
        r.driver_name = "Changed Name"
        with pytest.raises(ValueError, match="CONFORME is immutable"):
            r.save()

    def test_conforme_allows_tare_capture(self, romaneo_factory):
        """Tare capture fields are allowed at CONFORME."""
        r = self._make_conforme(romaneo_factory)
        r.tara_kg = Decimal("12000.000")
        r.peso_neto_bruto_kg = Decimal("18000.000")
        r.ts_tara = timezone.now()
        r.save()
        r.refresh_from_db()
        assert r.tara_kg == Decimal("12000.000")

    def test_conforme_allows_cerrado_transition(self, romaneo_factory):
        """Can transition CONFORME -> CERRADO."""
        r = self._make_conforme(romaneo_factory)
        r.status = Romaneo.RomaneoStatus.CERRADO
        r.save()
        r.refresh_from_db()
        assert r.status == Romaneo.RomaneoStatus.CERRADO

    def test_cerrado_blocks_all_changes(self, romaneo_factory):
        """CERRADO blocks absolutely all changes."""
        r = self._make_conforme(romaneo_factory)
        r.status = Romaneo.RomaneoStatus.CERRADO
        r.save()
        r.refresh_from_db()
        r.tara_kg = Decimal("999.000")
        with pytest.raises(ValueError, match="CERRADO"):
            r.save()

    def test_cerrado_blocks_status_change(self, romaneo_factory):
        """Cannot change status from CERRADO."""
        r = self._make_conforme(romaneo_factory)
        r.status = Romaneo.RomaneoStatus.CERRADO
        r.save()
        r.refresh_from_db()
        r.status = Romaneo.RomaneoStatus.CONFORME
        with pytest.raises(ValueError, match="CERRADO"):
            r.save()


@pytest.mark.django_db
class TestRomaneoTimestamps:
    """Test state transition timestamps."""

    def test_ts_entrada_set_on_creation(self, romaneo_factory):
        r = romaneo_factory()
        assert r.ts_entrada is not None

    def test_ts_pesada_bruta_set_manually(self, romaneo_en_proceso):
        now = timezone.now()
        romaneo_en_proceso.ts_pesada_bruta = now
        romaneo_en_proceso.peso_bruto_kg = Decimal("30000.000")
        romaneo_en_proceso.status = Romaneo.RomaneoStatus.PESADO
        romaneo_en_proceso.save()
        assert romaneo_en_proceso.ts_pesada_bruta == now
