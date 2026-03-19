"""ViewSets for Romaneo and QualityAnalysis endpoints."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.acopio.models import MermaCalculation, QualityAnalysis, Romaneo
from apps.acopio.pagination import RomaneoPagination
from apps.acopio.serializers import (
    AnalizarSerializer,
    ConfirmarSerializer,
    MermaCalculationSerializer,
    PesoBrutoSerializer,
    QualityAnalysisSerializer,
    RomaneoDetailSerializer,
    RomaneoSerializer,
    TaraSerializer,
)


class RomaneoViewSet(viewsets.ModelViewSet):
    """
    Romaneo CRUD + state transition actions.

    CRUD:
        POST   /romaneos/          -> 201 (create)
        GET    /romaneos/          -> 200 (list, paginated)
        GET    /romaneos/{id}/     -> 200 (detail with nested QA + MC)
        PATCH  /romaneos/{id}/     -> 200 / 409 (update, immutability guard)

    State transitions (all POST):
        /romaneos/{id}/confirmar-arribo/  PENDIENTE -> EN_PROCESO  (202)
        /romaneos/{id}/peso-bruto/        EN_PROCESO -> PESADO     (200)
        /romaneos/{id}/analizar/          PESADO -> ANALIZADO      (200)
        /romaneos/{id}/confirmar/         ANALIZADO -> CONFORME    (200)
        /romaneos/{id}/tara/              CONFORME only           (200)
        /romaneos/{id}/cerrar/            CONFORME -> CERRADO      (202)

    Preview:
        /romaneos/{id}/merma-preview/     GET, PESADO/ANALIZADO   (200)
    """

    permission_classes = [IsAuthenticated]
    pagination_class = RomaneoPagination
    # Disable PUT (only PATCH allowed)
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return (
            Romaneo.objects
            .select_related(
                "grain_type", "campaign", "branch",
                "storage_unit", "grain_lot",
            )
            .all()
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return RomaneoDetailSerializer
        if self.action == "confirmar_arribo":
            return RomaneoDetailSerializer  # No request body; used for response only
        if self.action == "peso_bruto":
            return PesoBrutoSerializer
        if self.action == "analizar":
            return AnalizarSerializer
        if self.action == "confirmar":
            return ConfirmarSerializer
        if self.action == "tara":
            return TaraSerializer
        return RomaneoSerializer

    def perform_create(self, serializer):
        serializer.save(
            tenant_id=self.request.user.tenant_id,
            operator_id=self.request.user,
        )

    def partial_update(self, request, *args, **kwargs):
        """PATCH with immutability guard for CONFORME/CERRADO."""
        romaneo = self.get_object()
        if romaneo.status in (
            Romaneo.RomaneoStatus.CONFORME,
            Romaneo.RomaneoStatus.CERRADO,
        ):
            return Response(
                {
                    "type": "romaneo_immutable",
                    "detail": f"Romaneo in {romaneo.status} cannot be modified.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().partial_update(request, *args, **kwargs)

    # -- State Transition Actions ------------------------------------------

    def _transition_error(self, romaneo, attempted):
        """Return 409 response for invalid state transitions."""
        return Response(
            {
                "type": "invalid_state_transition",
                "current_status": romaneo.status,
                "attempted_transition": attempted,
            },
            status=status.HTTP_409_CONFLICT,
        )

    @action(detail=True, methods=["post"], url_path="confirmar-arribo")
    def confirmar_arribo(self, request, pk=None):
        """PENDIENTE -> EN_PROCESO. Returns 202 (async WSCPE enqueued)."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.PENDIENTE:
            return self._transition_error(romaneo, "confirmar_arribo")
        romaneo.status = Romaneo.RomaneoStatus.EN_PROCESO
        romaneo.save()
        return Response(
            RomaneoDetailSerializer(romaneo).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["post"], url_path="peso-bruto")
    def peso_bruto(self, request, pk=None):
        """EN_PROCESO -> PESADO. Captures peso_bruto_kg."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.EN_PROCESO:
            return self._transition_error(romaneo, "peso_bruto")

        serializer = PesoBrutoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        romaneo.peso_bruto_kg = serializer.validated_data["peso_bruto_kg"]
        romaneo.ts_pesada_bruta = timezone.now()
        romaneo.status = Romaneo.RomaneoStatus.PESADO
        romaneo.save()
        return Response(RomaneoDetailSerializer(romaneo).data)

    @action(detail=True, methods=["post"], url_path="analizar")
    def analizar(self, request, pk=None):
        """PESADO -> ANALIZADO. Creates QualityAnalysis record."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.PESADO:
            return self._transition_error(romaneo, "analizar")

        serializer = AnalizarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qa_data = serializer.validated_data.copy()
        sample_ref = qa_data.pop("sample_reference", None)

        QualityAnalysis.objects.create(
            romaneo=romaneo,
            tenant_id=romaneo.tenant_id,
            analysis_timestamp=timezone.now(),
            sample_reference=sample_ref or "",
            **qa_data,
        )

        romaneo.ts_analisis = timezone.now()
        romaneo.laboratorista_id = request.user
        romaneo.status = Romaneo.RomaneoStatus.ANALIZADO
        romaneo.save()
        return Response(RomaneoDetailSerializer(romaneo).data)

    @action(detail=True, methods=["post"], url_path="confirmar")
    def confirmar(self, request, pk=None):
        """
        ANALIZADO -> CONFORME. IMMUTABILITY GATE.

        Triggers merma calculation, creates MermaCalculation record,
        assigns grade, pins tolerance table version.
        """
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.ANALIZADO:
            return self._transition_error(romaneo, "confirmar")

        serializer = ConfirmarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qa = romaneo.quality_analysis
        grain = romaneo.grain_type

        # Lookup merma table band
        from apps.acopio.services.merma_engine import (
            calculate_merma_deductions,
            lookup_merma_table,
        )

        reference_date = (
            romaneo.ts_entrada.date() if romaneo.ts_entrada else timezone.now().date()
        )
        merma_table, zarandeo_deduction = lookup_merma_table(
            grain_type_id=grain.id,
            materias_extranas_pct=qa.materias_extranas_pct,
            reference_date=reference_date,
        )

        # Calculate merma deductions
        merma_result = calculate_merma_deductions({
            "peso_neto_bruto_kg": str(romaneo.peso_bruto_kg),
            "humedad_pct": str(qa.humedad_pct),
            "hf_secado_pct": str(grain.hf_secado_pct),
            "materias_extranas_pct": str(qa.materias_extranas_pct),
            "zarandeo_deduction_pct": str(zarandeo_deduction),
            "manipuleo_fijo_pct": str(grain.manipuleo_fijo_pct),
            "volatil_fijo_pct": str(grain.volatil_fijo_pct),
        })

        # Create immutable MermaCalculation record
        MermaCalculation.objects.create(
            romaneo=romaneo,
            tenant_id=romaneo.tenant_id,
            merma_table_version=merma_table,
            peso_neto_bruto_input_kg=romaneo.peso_bruto_kg,
            hi_input_pct=qa.humedad_pct,
            hf_used_pct=grain.hf_secado_pct,
            materias_extranas_input_pct=qa.materias_extranas_pct,
            zarandeo_pct=merma_result["zarandeo_pct"],
            secado_pct=merma_result["secado_pct"],
            manipuleo_pct=merma_result["manipuleo_pct"],
            volatil_pct=merma_result["volatil_pct"],
            peso_post_zarandeo_kg=merma_result["peso_post_zarandeo_kg"],
            peso_post_secado_kg=merma_result["peso_post_secado_kg"],
            peso_post_manipuleo_kg=merma_result["peso_post_manipuleo_kg"],
            peso_final_kg=merma_result["peso_final_kg"],
            total_merma_kg=merma_result["total_merma_kg"],
            total_factor_pct=merma_result["total_factor_pct"],
            calculated_by=request.user,
        )

        # Grade assignment
        grado = serializer.validated_data.get("grado_asignado")

        # Look up tolerance table version for pinning
        from django.db.models import Q

        from apps.acopio.models import ToleranceTable

        tolerance = (
            ToleranceTable.objects
            .filter(
                grain_type=grain,
                valid_from__lte=reference_date,
            )
            .filter(Q(valid_to__gte=reference_date) | Q(valid_to__isnull=True))
            .order_by("-valid_from")
            .first()
        )

        # Bonificacion/rebaja calculation based on grading system
        bonificacion_rebaja = None
        if grain.grading_system == "GRADO" and grado is not None and tolerance:
            # For GRADO system: look up bonificacion/rebaja from tolerance table
            # Grade 1 = standard, Grade 2/3 = rebaja (negative adjustment)
            if grado == 1:
                bonificacion_rebaja = None  # No adjustment for Grade 1
            elif grado in (2, 3):
                bonificacion_rebaja = -(grado - 1) * tolerance.tolerance_pct
        elif grain.grading_system == "TOLERANCE":
            grado = 0  # Oleaginosas always grade 0

        # Update romaneo with results — all-or-nothing with deposit + account
        with transaction.atomic():
            romaneo.grado_asignado = grado
            romaneo.bonificacion_rebaja_pct = bonificacion_rebaja
            romaneo.tolerance_table_version = tolerance
            romaneo.peso_neto_conforme_kg = merma_result["peso_final_kg"]
            romaneo.status = Romaneo.RomaneoStatus.CONFORME
            romaneo.save()

            if not romaneo.storage_unit:
                raise DRFValidationError(
                    {"storage_unit": "Must be set before confirming."}
                )

            is_own_grain = False  # MVP default; NOT a Romaneo model field

            from apps.acopio.services.storage import create_deposit_from_romaneo

            create_deposit_from_romaneo(
                romaneo=romaneo,
                storage_unit=romaneo.storage_unit,
                is_own_grain=is_own_grain,
            )

            if not is_own_grain:
                from apps.cuentas.services.accounts import create_ceg_deposit

                create_ceg_deposit(romaneo, operator=request.user)

        return Response(RomaneoDetailSerializer(romaneo).data)

    @action(detail=True, methods=["post"], url_path="tara")
    def tara(self, request, pk=None):
        """Capture tare weight while CONFORME. Computes peso_neto_bruto_kg."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.CONFORME:
            return self._transition_error(romaneo, "tara")

        serializer = TaraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tara_kg = serializer.validated_data["tara_kg"]

        # Validate bruto > tara
        if romaneo.peso_bruto_kg and tara_kg >= romaneo.peso_bruto_kg:
            return Response(
                {"tara_kg": ["tara_kg must be less than peso_bruto_kg."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        romaneo.tara_kg = tara_kg
        romaneo.peso_neto_bruto_kg = romaneo.peso_bruto_kg - tara_kg
        romaneo.ts_tara = timezone.now()
        romaneo.save()
        return Response(RomaneoDetailSerializer(romaneo).data)

    @action(detail=True, methods=["post"], url_path="cerrar")
    def cerrar(self, request, pk=None):
        """CONFORME -> CERRADO. Requires tara_kg present. Returns 202."""
        romaneo = self.get_object()
        if romaneo.status != Romaneo.RomaneoStatus.CONFORME:
            return self._transition_error(romaneo, "cerrar")

        if not romaneo.tara_kg:
            return Response(
                {"detail": "Cannot close romaneo without tara_kg."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        romaneo.status = Romaneo.RomaneoStatus.CERRADO
        romaneo.save()
        return Response(
            RomaneoDetailSerializer(romaneo).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=True, methods=["get"], url_path="merma-preview")
    def merma_preview(self, request, pk=None):
        """Non-persisting merma preview. Available at PESADO/ANALIZADO."""
        romaneo = self.get_object()

        if romaneo.status not in (
            Romaneo.RomaneoStatus.PESADO,
            Romaneo.RomaneoStatus.ANALIZADO,
        ):
            return self._transition_error(romaneo, "merma_preview")

        # Check QA exists
        try:
            qa = romaneo.quality_analysis
        except QualityAnalysis.DoesNotExist:
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": "No quality analysis exists for this romaneo.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        grain = romaneo.grain_type

        from apps.acopio.services.merma_engine import (
            calculate_merma_deductions,
            lookup_merma_table,
        )

        reference_date = (
            romaneo.ts_entrada.date() if romaneo.ts_entrada else timezone.now().date()
        )

        try:
            _, zarandeo_deduction = lookup_merma_table(
                grain_type_id=grain.id,
                materias_extranas_pct=qa.materias_extranas_pct,
                reference_date=reference_date,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        peso_input = romaneo.peso_bruto_kg
        if not peso_input:
            return Response(
                {"detail": "peso_bruto_kg not yet captured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        merma_result = calculate_merma_deductions({
            "peso_neto_bruto_kg": str(peso_input),
            "humedad_pct": str(qa.humedad_pct),
            "hf_secado_pct": str(grain.hf_secado_pct),
            "materias_extranas_pct": str(qa.materias_extranas_pct),
            "zarandeo_deduction_pct": str(zarandeo_deduction),
            "manipuleo_fijo_pct": str(grain.manipuleo_fijo_pct),
            "volatil_fijo_pct": str(grain.volatil_fijo_pct),
        })

        # Return as string values (same format as MermaCalculation fields)
        return Response({k: str(v) for k, v in merma_result.items()})


class QualityAnalysisViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Nested QA endpoints under romaneo.

    POST   /romaneos/{romaneo_pk}/quality-analysis/   -> 201 (create)
    GET    /romaneos/{romaneo_pk}/quality-analysis/    -> 200 (retrieve)
    PATCH  /romaneos/{romaneo_pk}/quality-analysis/    -> 200/409 (update)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = QualityAnalysisSerializer

    def get_romaneo(self):
        return get_object_or_404(
            Romaneo.objects.all(),
            pk=self.kwargs["romaneo_pk"],
        )

    def get_queryset(self):
        return QualityAnalysis.objects.filter(
            romaneo_id=self.kwargs["romaneo_pk"],
        )

    def get_object(self):
        """Return the single QA for this romaneo (1:1 relationship)."""
        return get_object_or_404(self.get_queryset())

    def list(self, request, *args, **kwargs):
        """GET on collection returns the single QA (if exists) or 404."""
        try:
            instance = self.get_object()
        except Exception:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Create QA. Guard: romaneo in EN_PROCESO or PESADO."""
        romaneo = self.get_romaneo()
        if romaneo.status not in (
            Romaneo.RomaneoStatus.EN_PROCESO,
            Romaneo.RomaneoStatus.PESADO,
        ):
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": f"Cannot create QA when romaneo is {romaneo.status}.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Use AnalizarSerializer for write operations
        serializer = AnalizarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        qa_data = serializer.validated_data.copy()
        sample_ref = qa_data.pop("sample_reference", None)

        qa = QualityAnalysis.objects.create(
            romaneo=romaneo,
            tenant_id=romaneo.tenant_id,
            analysis_timestamp=timezone.now(),
            sample_reference=sample_ref or "",
            **qa_data,
        )

        return Response(
            QualityAnalysisSerializer(qa).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Update QA. Guard: romaneo in ANALIZADO only."""
        romaneo = self.get_romaneo()
        if romaneo.status != Romaneo.RomaneoStatus.ANALIZADO:
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": (
                        f"Cannot update QA when romaneo is {romaneo.status}. "
                        "Only ANALIZADO allowed."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        """PATCH QA. Same guard as update."""
        romaneo = self.get_romaneo()
        if romaneo.status != Romaneo.RomaneoStatus.ANALIZADO:
            return Response(
                {
                    "type": "invalid_state_transition",
                    "detail": (
                        f"Cannot update QA when romaneo is {romaneo.status}. "
                        "Only ANALIZADO allowed."
                    ),
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().partial_update(request, *args, **kwargs)
