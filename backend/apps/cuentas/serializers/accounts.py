from decimal import Decimal

from rest_framework import serializers

from apps.cuentas.models import AccountMovement, ProducerAccount


class ProducerAccountSerializer(serializers.ModelSerializer):
    producer_cuit = serializers.CharField(
        source="producer_cuit_encrypted", read_only=True
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    grain_type_code = serializers.CharField(source="grain_type.code", read_only=True)
    grain_type_name = serializers.CharField(source="grain_type.name", read_only=True)
    campaign_label = serializers.CharField(source="campaign.campaign_code", read_only=True)

    class Meta:
        model = ProducerAccount
        fields = [
            "id",
            "producer_cuit",
            "branch",
            "branch_name",
            "grain_type",
            "grain_type_code",
            "grain_type_name",
            "campaign",
            "campaign_label",
            "grain_balance_kg",
            "ars_balance",
            "usd_balance",
            "is_active",
            "created_at",
            "updated_at",
        ]
        # NEVER include producer_cuit_encrypted or producer_cuit_hash


class AccountMovementSerializer(serializers.ModelSerializer):
    movement_type_display = serializers.CharField(
        source="get_movement_type_display", read_only=True
    )
    romaneo_numero = serializers.CharField(
        source="romaneo.numero", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    class Meta:
        model = AccountMovement
        fields = [
            "id",
            "movement_type",
            "movement_type_display",
            "quantity_kg",
            "ars_amount",
            "usd_amount",
            "romaneo",
            "romaneo_numero",
            "reference_document",
            "notes",
            "movement_at",
            "created_by_name",
        ]
        read_only_fields = fields


class ManualMovementSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(
        choices=AccountMovement.MovementType.choices,
    )
    quantity_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, default=Decimal("0.000")
    )
    ars_amount = serializers.DecimalField(
        max_digits=17, decimal_places=3, default=Decimal("0.000")
    )
    usd_amount = serializers.DecimalField(
        max_digits=17, decimal_places=3, default=Decimal("0.000")
    )
    reference_document = serializers.CharField(max_length=200)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_movement_type(self, value):
        from apps.cuentas.services.accounts import MANUAL_TYPES

        if value not in MANUAL_TYPES:
            raise serializers.ValidationError(
                f"{value} cannot be created manually.",
                code="invalid_movement_type",
            )
        return value

    def validate(self, attrs):
        mt = attrs.get("movement_type")
        ars = attrs.get("ars_amount", Decimal("0.000"))
        usd = attrs.get("usd_amount", Decimal("0.000"))

        if mt in (
            AccountMovement.MovementType.SERVICE_CHARGE,
            AccountMovement.MovementType.RETENTION_DEDUCTION,
        ) and ars > 0:
            raise serializers.ValidationError(
                {"ars_amount": "Must be zero or negative for this movement type."},
                code="sign_violation",
            )
        if mt == AccountMovement.MovementType.RETIRO:
            if ars > 0 or usd > 0:
                raise serializers.ValidationError(
                    {"ars_amount": "Retiro must have non-positive amounts."},
                    code="sign_violation",
                )
        return attrs


class BranchBreakdownSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField(read_only=True)
    branch_name = serializers.CharField(
        source="branch__name", read_only=True
    )
    grain_balance_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    ars_balance = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    usd_balance = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )


class GrainSummarySerializer(serializers.Serializer):
    grain_type_id = serializers.UUIDField(read_only=True)
    grain_type_code = serializers.CharField(
        source="grain_type__code", read_only=True
    )
    grain_type_name = serializers.CharField(
        source="grain_type__name", read_only=True
    )
    total_grain_kg = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    total_ars = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    total_usd = serializers.DecimalField(
        max_digits=17, decimal_places=3, read_only=True
    )
    branch_breakdown = BranchBreakdownSerializer(many=True, read_only=True)


class PosicionConsolidadaSerializer(serializers.Serializer):
    producer_cuit = serializers.CharField(read_only=True)
    campaign_id = serializers.UUIDField(read_only=True)
    campaign_label = serializers.CharField(read_only=True)
    summary = GrainSummarySerializer(many=True, read_only=True)
