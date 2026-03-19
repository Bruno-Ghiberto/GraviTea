"""Tests for QualityAnalysis model."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.acopio.models import QualityAnalysis


@pytest.mark.django_db
class TestQualityAnalysisCreation:

    def test_create_qa_with_all_params(self, romaneo_pesado, quality_analysis_factory):
        qa = quality_analysis_factory(
            romaneo_pesado,
            peso_hectolitrico_kg=Decimal("78.50"),
            proteina_pct=Decimal("11.20"),
            granos_verdes_pct=None,
        )
        assert qa.pk is not None
        assert qa.humedad_pct == Decimal("15.20")
        assert qa.materias_extranas_pct == Decimal("1.80")
        assert qa.peso_hectolitrico_kg == Decimal("78.50")

    def test_create_qa_minimal(self, romaneo_pesado, quality_analysis_factory):
        """Create QA with only required fields (nullable fields omitted)."""
        qa = quality_analysis_factory(romaneo_pesado)
        assert qa.pk is not None
        assert qa.peso_hectolitrico_kg is None
        assert qa.proteina_pct is None
        assert qa.granos_verdes_pct is None

    def test_qa_str(self, romaneo_pesado, quality_analysis_factory):
        qa = quality_analysis_factory(romaneo_pesado)
        assert str(romaneo_pesado) in str(qa)


@pytest.mark.django_db
class TestQualityAnalysisOneToOne:

    def test_duplicate_qa_raises_integrity_error(self, romaneo_pesado, quality_analysis_factory):
        """OneToOne constraint prevents duplicate QA for same romaneo."""
        quality_analysis_factory(romaneo_pesado)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                quality_analysis_factory(romaneo_pesado)

    def test_qa_accessible_from_romaneo(self, romaneo_pesado, quality_analysis_factory):
        qa = quality_analysis_factory(romaneo_pesado)
        assert romaneo_pesado.quality_analysis == qa


@pytest.mark.django_db
class TestQualityAnalysisPrecision:

    def test_decimal_precision(self, romaneo_pesado, quality_analysis_factory):
        qa = quality_analysis_factory(
            romaneo_pesado,
            humedad_pct=Decimal("15.25"),
            materias_extranas_pct=Decimal("1.80"),
        )
        qa.refresh_from_db()
        assert qa.humedad_pct == Decimal("15.25")
        assert qa.materias_extranas_pct == Decimal("1.80")
