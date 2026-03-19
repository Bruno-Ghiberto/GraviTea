"""Serializers for StorageUnit, GrainLot, and GrainMovement."""

from decimal import Decimal

from rest_framework import serializers

from apps.acopio.models import GrainLot, GrainMovement, StorageUnit


class StorageUnitSerializer(serializers.ModelSerializer):
    """
    StorageUnit list/create/update serializer.

    current_occupancy_kg comes from annotated queryset (not a model field).
    capacity_utilisation_pct is derived: (occupancy / capacity_kg) * 100.
    """

    unit_type_display = serializers.CharField(
        source="get_unit_type_display", read_only=True
    )
    branch_name = serializers.CharField(
        source="branch.name", read_only=True
    )
    current_grain_type_code = serializers.CharField(
        source="current_grain_type.code", read_only=True, default=None
    )
    current_occupancy_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    capacity_utilisation_pct = serializers.SerializerMethodField()

    class Meta:
        model = StorageUnit
        fields = [
            "id",
            "name",
            "unit_type",
            "unit_type_display",
            "branch",
            "branch_name",
            "capacity_tonnes",
            "current_grain_type",
            "current_grain_type_code",
            "is_active",
            "environment_sensor_id",
            "current_occupancy_kg",
            "capacity_utilisation_pct",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "current_occupancy_kg"]

    def get_capacity_utilisation_pct(self, obj) -> Decimal:
        occupancy = getattr(obj, "current_occupancy_kg", None) or Decimal("0")
        capacity_kg = obj.capacity_tonnes * 1000
        if capacity_kg == 0:
            return Decimal("0")
        return round((occupancy / capacity_kg) * 100, 1)


class GrainLotSerializer(serializers.ModelSerializer):
    """
    GrainLot read-only serializer.

    Lots are created internally by the deposit service — no create/update via API.
    """

    grain_type_code = serializers.CharField(
        source="grain_type.code", read_only=True
    )
    campaign_code = serializers.CharField(
        source="campaign.campaign_code", read_only=True
    )
    storage_unit_name = serializers.CharField(
        source="storage_unit.name", read_only=True
    )

    class Meta:
        model = GrainLot
        fields = [
            "id",
            "lot_code",
            "grain_type",
            "grain_type_code",
            "campaign",
            "campaign_code",
            "grado",
            "storage_unit",
            "storage_unit_name",
            "total_kg",
            "is_own_grain",
            "created_at",
        ]
        read_only_fields = fields


class GrainMovementSerializer(serializers.ModelSerializer):
    """
    GrainMovement serializer — append-only.

    GET: all fields read-only.
    POST: movement_type, quantity_kg, reference_document, notes are writable.
    PATCH/PUT/DELETE: 405 (enforced by viewset http_method_names).
    """

    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    romaneo_number = serializers.CharField(
        source="romaneo.romaneo_number", read_only=True, default=None
    )
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GrainMovement
        fields = [
            "id",
            "movement_type",
            "movement_type_display",
            "quantity_kg",
            "movement_at",
            "romaneo",
            "romaneo_number",
            "reference_document",
            "notes",
            "created_by_name",
        ]
        read_only_fields = [
            "id",
            "movement_at",
            "romaneo",
            "romaneo_number",
            "created_by_name",
        ]

    def get_created_by_name(self, obj) -> str | None:
        if obj.created_by:
            return getattr(obj.created_by, "full_name", None) or str(obj.created_by)
        return None


# -- Wave 3: P2 Serializers ------------------------------------------------


class CellSuggestionRequestSerializer(serializers.Serializer):
    """Request body for POST /storage-units/suggest/."""

    grain_type_id = serializers.UUIDField()
    campaign_id = serializers.UUIDField()
    grado = serializers.IntegerField()
    incoming_kg = serializers.DecimalField(max_digits=17, decimal_places=3)
    branch_id = serializers.UUIDField()


class CellSuggestionItemSerializer(serializers.Serializer):
    """Single suggestion item in the suggest response."""

    storage_unit_id = serializers.UUIDField()
    name = serializers.CharField()
    score = serializers.IntegerField()
    reasons = serializers.ListField(child=serializers.CharField())
    available_capacity_kg = serializers.DecimalField(max_digits=17, decimal_places=3)
    current_occupancy_kg = serializers.DecimalField(max_digits=17, decimal_places=3)


class TransferRequestSerializer(serializers.Serializer):
    """Request body for POST /grain-lots/transfer/."""

    source_lot_id = serializers.UUIDField()
    destination_lot_id = serializers.UUIDField()
    quantity_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, min_value=Decimal("0.001")
    )
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        if attrs["source_lot_id"] == attrs["destination_lot_id"]:
            raise serializers.ValidationError(
                {"detail": "Source and destination lots must be different."}
            )
        return attrs


class StockReportUnitSerializer(serializers.Serializer):
    """Per-unit entry in the stock report."""

    storage_unit_id = serializers.UUIDField()
    name = serializers.CharField()
    grain_type_code = serializers.CharField(allow_null=True)
    campaign_code = serializers.CharField(allow_null=True)
    total_kg = serializers.DecimalField(max_digits=17, decimal_places=3)
    capacity_pct = serializers.DecimalField(max_digits=5, decimal_places=1)


class StockReportGrainTypeSerializer(serializers.Serializer):
    """Per-grain-type entry in the stock report."""

    grain_type_code = serializers.CharField()
    total_kg = serializers.DecimalField(max_digits=17, decimal_places=3)


class StockReportCampaignSerializer(serializers.Serializer):
    """Per-campaign entry in the stock report."""

    campaign_code = serializers.CharField()
    total_kg = serializers.DecimalField(max_digits=17, decimal_places=3)


class StockReportSerializer(serializers.Serializer):
    """Response for GET /storage-units/stock-report/."""

    generated_at = serializers.DateTimeField()
    total_capacity_tonnes = serializers.DecimalField(max_digits=17, decimal_places=3)
    total_occupied_kg = serializers.DecimalField(max_digits=17, decimal_places=3)
    utilisation_pct = serializers.DecimalField(max_digits=5, decimal_places=1)
    by_storage_unit = StockReportUnitSerializer(many=True)
    by_grain_type = StockReportGrainTypeSerializer(many=True)
    by_campaign = StockReportCampaignSerializer(many=True)


# -- Wave 4: P3 Serializers ------------------------------------------------


class ReconciliationMeasurementSerializer(serializers.Serializer):
    """Single measurement in a reconciliation request."""

    storage_unit_id = serializers.UUIDField()
    measured_kg = serializers.DecimalField(max_digits=17, decimal_places=3)


class ReconciliationRequestSerializer(serializers.Serializer):
    """Request body for POST /storage-units/reconcile/."""

    branch_id = serializers.UUIDField()
    notes = serializers.CharField(min_length=1)
    measurements = ReconciliationMeasurementSerializer(many=True, min_length=1)
