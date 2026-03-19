"""Storage & Position service layer — grain deposit, withdrawal, transfer, and reporting."""

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.acopio.models import GrainLot, GrainMovement, StorageUnit


def create_deposit_from_romaneo(
    romaneo,
    storage_unit: StorageUnit,
    is_own_grain: bool = False,
) -> tuple[GrainMovement, GrainLot]:
    """FR-012: Create deposit movement from confirmed romaneo.

    Atomically:
    1. Get-or-create a GrainLot for the composite key.
    2. Create an immutable DEPOSIT GrainMovement.
    3. Update the lot running balance.
    4. Set storage_unit's current_grain_type if empty.
    5. Link romaneo back to the lot.

    Returns:
        (movement, lot) tuple.
    """
    with transaction.atomic():
        lot, _created = GrainLot.objects.select_for_update().get_or_create(
            tenant=romaneo.tenant,
            branch=romaneo.branch,
            grain_type=romaneo.grain_type,
            campaign=romaneo.campaign,
            grado=romaneo.grado_asignado or 0,
            storage_unit=storage_unit,
            defaults={
                "is_own_grain": is_own_grain,
                "total_kg": Decimal("0.000"),
                "created_by": romaneo.operator_id,
            },
        )

        quantity = romaneo.peso_neto_conforme_kg
        movement = GrainMovement.objects.create(
            tenant=romaneo.tenant,
            grain_lot=lot,
            movement_type=GrainMovement.MovementType.DEPOSIT,
            quantity_kg=quantity,
            romaneo=romaneo,
            created_by=romaneo.operator_id,
        )

        lot.total_kg += quantity
        lot.save(update_fields=["total_kg", "updated_at"])

        # Update storage unit grain type if empty
        if storage_unit.current_grain_type is None:
            storage_unit.current_grain_type = romaneo.grain_type
            storage_unit.save(update_fields=["current_grain_type", "updated_at"])

        # Link romaneo back to lot (requires CONFORME allowlist update)
        romaneo.grain_lot = lot
        romaneo.save(update_fields=["grain_lot_id"])

    return movement, lot


def _generate_lot_code(branch, grain_type, campaign, grado: int) -> str:
    """Generate lot code: BRANCH-GRAIN-CAMPAIGN-GRADE."""
    branch_code = (
        branch.code if hasattr(branch, "code") else str(branch.pk)[:4]
    )
    grain_code = grain_type.code
    campaign_code = campaign.campaign_code.replace("/", "")
    return f"{branch_code}-{grain_code}-{campaign_code}-{grado}"


# ── T027: Withdrawal service ───────────────────────────────────


def create_withdrawal(
    grain_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    reference_document: str | None = None,
    notes: str | None = None,
) -> GrainMovement:
    """FR-015: Record grain dispatch. Rejects if insufficient balance.

    Stores quantity_kg as NEGATIVE (outflow convention).
    """
    with transaction.atomic():
        lot = GrainLot.objects.select_for_update().get(pk=grain_lot.pk)
        if lot.total_kg < quantity_kg:
            raise ValueError(
                f"Insufficient grain stock. Lot '{lot.lot_code}' has {lot.total_kg} kg "
                f"but attempted withdrawal is {quantity_kg} kg."
            )
        movement = GrainMovement.objects.create(
            tenant=lot.tenant,
            grain_lot=lot,
            movement_type=GrainMovement.MovementType.WITHDRAWAL,
            quantity_kg=-quantity_kg,  # Stored NEGATIVE for outflow
            reference_document=reference_document,
            notes=notes,
            created_by=operator,
        )
        lot.total_kg -= quantity_kg
        lot.save(update_fields=["total_kg", "updated_at"])
    return movement


# ── T031: Transfer service ─────────────────────────────────────


def transfer_grain(
    source_lot: GrainLot,
    destination_lot: GrainLot,
    quantity_kg: Decimal,
    operator,
    notes: str | None = None,
) -> tuple[GrainMovement, GrainLot]:
    """FR-016: Atomic inter-silo transfer with PK-ordered locking.

    Returns:
        (out_movement, destination_lot) tuple.
    """
    if source_lot.pk == destination_lot.pk:
        raise ValueError("Source and destination lots must be different.")

    with transaction.atomic():
        # Lock in ascending PK order to prevent deadlock
        pks = sorted([source_lot.pk, destination_lot.pk])
        locked = list(
            GrainLot.objects.select_for_update()
            .filter(pk__in=pks)
            .order_by("pk")
        )
        src = next(lot for lot in locked if lot.pk == source_lot.pk)
        dst = next(lot for lot in locked if lot.pk == destination_lot.pk)

        if src.total_kg < quantity_kg:
            raise ValueError(
                f"Insufficient source balance: {src.total_kg} kg < {quantity_kg} kg"
            )

        out_mv = GrainMovement.objects.create(
            tenant=src.tenant,
            grain_lot=src,
            movement_type=GrainMovement.MovementType.TRANSFER_OUT,
            quantity_kg=-quantity_kg,
            notes=notes,
            created_by=operator,
        )
        GrainMovement.objects.create(
            tenant=dst.tenant,
            grain_lot=dst,
            movement_type=GrainMovement.MovementType.TRANSFER_IN,
            quantity_kg=quantity_kg,
            notes=notes,
            created_by=operator,
        )

        src.total_kg -= quantity_kg
        src.save(update_fields=["total_kg", "updated_at"])
        dst.total_kg += quantity_kg
        dst.save(update_fields=["total_kg", "updated_at"])

    return out_mv, dst


# ── T023: Cell suggestion service ──────────────────────────────


@dataclass
class CellSuggestion:
    """Ranked suggestion for where to deposit incoming grain."""

    storage_unit_id: uuid.UUID
    name: str
    score: int
    reasons: list[str] = field(default_factory=list)
    available_capacity_kg: Decimal = Decimal("0.000")
    current_occupancy_kg: Decimal = Decimal("0.000")


def suggest_cell(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID,
    grain_type_id: uuid.UUID,
    campaign_id: uuid.UUID,
    grado: int,
    incoming_kg: Decimal,
) -> list[CellSuggestion]:
    """FR-004: Rank compatible storage units for incoming grain.

    Scoring:
    - 40 pts: grain type match (current_grain_type matches OR unit is empty)
    - +20 pts: grade match (existing lot with same grado in that unit)
    - +10 pts: campaign match (existing lot with same campaign in that unit)

    Excludes:
    - Units with incompatible grain type (occupied with different grain)
    - Units with insufficient remaining capacity for incoming_kg
    """
    units = (
        StorageUnit.objects.filter(
            tenant_id=tenant_id,
            branch_id=branch_id,
            is_active=True,
        )
        .annotate(
            current_occupancy_kg=Coalesce(
                Sum("grain_lots__movements__quantity_kg"),
                Decimal("0.000"),
            )
        )
        .select_related("current_grain_type")
    )

    # Preload existing lots for grade/campaign matching
    existing_lots = GrainLot.objects.filter(
        tenant_id=tenant_id,
        branch_id=branch_id,
        total_kg__gt=0,
    ).values_list("storage_unit_id", "grain_type_id", "campaign_id", "grado")

    # Build lookup: storage_unit_id -> set of (grain_type_id, campaign_id, grado)
    lot_lookup: dict[uuid.UUID, set[tuple]] = {}
    for su_id, gt_id, camp_id, gr in existing_lots:
        lot_lookup.setdefault(su_id, set()).add((gt_id, camp_id, gr))

    suggestions: list[CellSuggestion] = []

    for unit in units:
        capacity_kg = unit.capacity_tonnes * 1000
        available_kg = capacity_kg - unit.current_occupancy_kg

        # Exclude: insufficient capacity
        if available_kg < incoming_kg:
            continue

        score = 0
        reasons: list[str] = []

        is_empty = unit.current_grain_type is None
        type_matches = (
            unit.current_grain_type_id == grain_type_id if not is_empty else False
        )

        # Exclude: incompatible grain type (occupied with different grain)
        if not is_empty and not type_matches:
            continue

        # +40: grain type match or empty
        if type_matches:
            score += 40
            reasons.append("grain type match")
        elif is_empty:
            score += 40
            reasons.append("empty unit -- compatible")

        # Check existing lots in this unit for grade/campaign match
        unit_lots = lot_lookup.get(unit.pk, set())
        has_grade_match = any(
            gt == grain_type_id and gr == grado for gt, _, gr in unit_lots
        )
        has_campaign_match = any(
            gt == grain_type_id and camp == campaign_id
            for gt, camp, _ in unit_lots
        )

        if has_grade_match:
            score += 20
            reasons.append("grade match")
        if has_campaign_match:
            score += 10
            reasons.append("campaign match")

        suggestions.append(
            CellSuggestion(
                storage_unit_id=unit.pk,
                name=unit.name,
                score=score,
                reasons=reasons,
                available_capacity_kg=available_kg,
                current_occupancy_kg=unit.current_occupancy_kg,
            )
        )

    # Sort by score descending, then name ascending for ties
    suggestions.sort(key=lambda s: (-s.score, s.name))
    return suggestions


# ── T035: Stock report service ─────────────────────────────────


def generate_stock_report(
    tenant_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    grain_type_id: uuid.UUID | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict:
    """FR-017: Real-time stock report from GrainMovement ledger.

    Returns aggregated totals by storage unit, grain type, and campaign,
    plus total warehouse capacity utilisation.
    """
    # Base filters
    lot_filters = {"tenant_id": tenant_id}
    unit_filters = {"tenant_id": tenant_id, "is_active": True}
    if branch_id:
        lot_filters["branch_id"] = branch_id
        unit_filters["branch_id"] = branch_id
    if grain_type_id:
        lot_filters["grain_type_id"] = grain_type_id
    if campaign_id:
        lot_filters["campaign_id"] = campaign_id

    # By storage unit (with grain type and campaign info)
    by_unit_qs = (
        GrainLot.objects.filter(**lot_filters, total_kg__gt=0)
        .values(
            "storage_unit_id",
            "storage_unit__name",
            "grain_type__code",
            "campaign__campaign_code",
            "storage_unit__capacity_tonnes",
        )
        .annotate(total_kg=Sum("total_kg"))
        .order_by("storage_unit__name", "grain_type__code")
    )

    by_storage_unit = []
    for row in by_unit_qs:
        capacity_kg = row["storage_unit__capacity_tonnes"] * 1000
        capacity_pct = (
            float(row["total_kg"] / capacity_kg * 100)
            if capacity_kg > 0
            else 0.0
        )
        by_storage_unit.append({
            "storage_unit_id": row["storage_unit_id"],
            "name": row["storage_unit__name"],
            "grain_type_code": row["grain_type__code"],
            "campaign_code": row["campaign__campaign_code"],
            "total_kg": str(row["total_kg"]),
            "capacity_pct": round(capacity_pct, 1),
        })

    # By grain type
    by_grain_type_qs = (
        GrainLot.objects.filter(**lot_filters, total_kg__gt=0)
        .values("grain_type__code")
        .annotate(total_kg=Sum("total_kg"))
        .order_by("grain_type__code")
    )
    by_grain_type = [
        {"grain_type_code": row["grain_type__code"], "total_kg": str(row["total_kg"])}
        for row in by_grain_type_qs
    ]

    # By campaign
    by_campaign_qs = (
        GrainLot.objects.filter(**lot_filters, total_kg__gt=0)
        .values("campaign__campaign_code")
        .annotate(total_kg=Sum("total_kg"))
        .order_by("campaign__campaign_code")
    )
    by_campaign = [
        {"campaign_code": row["campaign__campaign_code"], "total_kg": str(row["total_kg"])}
        for row in by_campaign_qs
    ]

    # Total capacity and occupancy
    units = StorageUnit.objects.filter(**unit_filters)
    total_capacity_tonnes = units.aggregate(
        total=Coalesce(Sum("capacity_tonnes"), Decimal("0.000"))
    )["total"]

    total_occupied_kg = (
        GrainLot.objects.filter(**lot_filters)
        .aggregate(total=Coalesce(Sum("total_kg"), Decimal("0.000")))
    )["total"]

    total_capacity_kg = total_capacity_tonnes * 1000
    utilisation_pct = (
        round(float(total_occupied_kg / total_capacity_kg * 100), 1)
        if total_capacity_kg > 0
        else 0.0
    )

    return {
        "generated_at": timezone.now().isoformat(),
        "total_capacity_tonnes": str(total_capacity_tonnes),
        "total_occupied_kg": str(total_occupied_kg),
        "utilisation_pct": utilisation_pct,
        "by_storage_unit": by_storage_unit,
        "by_grain_type": by_grain_type,
        "by_campaign": by_campaign,
    }


# ── T039: Reconciliation service ───────────────────────────────


def reconcile(
    tenant_id: uuid.UUID,
    measurements: list[dict],
    operator_id: uuid.UUID,
    notes: str,
) -> dict:
    """FR-008: Physical inventory reconciliation.

    Computes ledger balance per storage unit, creates ADJUSTMENT movements
    for non-zero variances.

    Args:
        measurements: list of {"storage_unit_id": UUID, "measured_kg": Decimal}
        notes: mandatory — raises ValueError if blank.

    Returns:
        dict with variances list and total_variance_kg.
    """
    if not notes or not notes.strip():
        raise ValueError("Notes are required for reconciliation adjustments.")

    from apps.auth.models import AppUser

    operator = AppUser.objects.get(pk=operator_id)

    variances = []
    total_variance = Decimal("0.000")

    with transaction.atomic():
        for entry in measurements:
            su_id = entry["storage_unit_id"]
            measured_kg = Decimal(str(entry["measured_kg"]))

            storage_unit = StorageUnit.objects.get(
                pk=su_id, tenant_id=tenant_id,
            )

            # Compute ledger balance as sum of all lot totals in this unit
            ledger_kg = (
                GrainLot.objects.filter(
                    tenant_id=tenant_id,
                    storage_unit_id=su_id,
                ).aggregate(
                    total=Coalesce(Sum("total_kg"), Decimal("0.000"))
                )["total"]
            )

            variance_kg = measured_kg - ledger_kg

            adjustment_movement_id = None
            if variance_kg != Decimal("0.000"):
                # Find the primary lot for this unit to attach adjustment to.
                # Use the lot with the largest balance; if no lots exist, skip.
                lots = list(
                    GrainLot.objects.filter(
                        tenant_id=tenant_id,
                        storage_unit_id=su_id,
                    )
                    .select_for_update()
                    .order_by("-total_kg")
                )
                if lots:
                    target_lot = lots[0]
                    movement = GrainMovement.objects.create(
                        tenant_id=tenant_id,
                        grain_lot=target_lot,
                        movement_type=GrainMovement.MovementType.ADJUSTMENT,
                        quantity_kg=variance_kg,
                        notes=notes,
                        created_by=operator,
                    )
                    target_lot.total_kg += variance_kg
                    target_lot.save(update_fields=["total_kg", "updated_at"])
                    adjustment_movement_id = movement.pk

            variances.append({
                "storage_unit_id": su_id,
                "storage_unit_name": storage_unit.name,
                "ledger_kg": str(ledger_kg),
                "measured_kg": str(measured_kg),
                "variance_kg": str(variance_kg),
                "adjustment_movement_id": adjustment_movement_id,
            })
            total_variance += variance_kg

    return {
        "reconciliation_id": str(uuid.uuid4()),
        "performed_at": timezone.now().isoformat(),
        "variances": variances,
        "total_variance_kg": str(total_variance),
    }


# ── T044: Campaign close service ───────────────────────────────


class CampaignCloseService:
    """FR-009: Campaign year close with carry-forward movements."""

    @staticmethod
    def close_campaign(
        tenant_id: uuid.UUID,
        campaign_id: uuid.UUID,
        target_campaign_id: uuid.UUID,
        supervisor_id: uuid.UUID,
    ) -> dict:
        """Close a campaign and carry forward non-zero lots to the target campaign.

        Validation:
        - All romaneos in the campaign must be CONFORME or CERRADO.
        - Raises ValueError with offender list if any are in intermediate states.

        Operations (atomic):
        1. For each non-zero lot: create TRANSFER_OUT, get_or_create target lot,
           create TRANSFER_IN, update balances.
        2. Mark CampanaConfig.is_active = False.
        """
        from apps.acopio.models import CampanaConfig, Romaneo
        from apps.acopio.models.romaneo import RomaneoStatus
        from apps.auth.models import AppUser

        supervisor = AppUser.objects.get(pk=supervisor_id)

        # Validate all romaneos are in final state
        non_final = list(
            Romaneo.all_objects.filter(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
            )
            .exclude(status__in=[RomaneoStatus.CONFORME, RomaneoStatus.CERRADO])
            .values_list("romaneo_number", "status")
        )
        if non_final:
            offenders = [
                {"romaneo_number": num, "status": st} for num, st in non_final
            ]
            raise ValueError(
                f"Cannot close campaign: {len(non_final)} romaneo(s) not in final state. "
                f"Offenders: {offenders}"
            )

        with transaction.atomic():
            source_campaign = CampanaConfig.all_objects.select_for_update().get(
                pk=campaign_id, tenant_id=tenant_id,
            )
            target_campaign = CampanaConfig.all_objects.get(
                pk=target_campaign_id, tenant_id=tenant_id,
            )

            # Get all non-zero lots for the source campaign
            source_lots = list(
                GrainLot.objects.select_for_update().filter(
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    total_kg__gt=0,
                )
            )

            carried_lots = []
            movements_created = 0

            for src_lot in source_lots:
                carry_kg = src_lot.total_kg

                # TRANSFER_OUT from source lot
                GrainMovement.objects.create(
                    tenant_id=tenant_id,
                    grain_lot=src_lot,
                    movement_type=GrainMovement.MovementType.TRANSFER_OUT,
                    quantity_kg=-carry_kg,
                    notes=f"Campaign close carry-forward to {target_campaign.campaign_code}",
                    created_by=supervisor,
                )
                src_lot.total_kg = Decimal("0.000")
                src_lot.save(update_fields=["total_kg", "updated_at"])
                movements_created += 1

                # Get or create target lot with same composite key but new campaign
                target_lot, _created = GrainLot.objects.select_for_update().get_or_create(
                    tenant_id=tenant_id,
                    branch=src_lot.branch,
                    grain_type=src_lot.grain_type,
                    campaign=target_campaign,
                    grado=src_lot.grado,
                    storage_unit=src_lot.storage_unit,
                    defaults={
                        "is_own_grain": src_lot.is_own_grain,
                        "total_kg": Decimal("0.000"),
                        "created_by": supervisor,
                    },
                )

                # TRANSFER_IN to target lot
                GrainMovement.objects.create(
                    tenant_id=tenant_id,
                    grain_lot=target_lot,
                    movement_type=GrainMovement.MovementType.TRANSFER_IN,
                    quantity_kg=carry_kg,
                    notes=f"Campaign close carry-forward from {source_campaign.campaign_code}",
                    created_by=supervisor,
                )
                target_lot.total_kg += carry_kg
                target_lot.save(update_fields=["total_kg", "updated_at"])
                movements_created += 1

                carried_lots.append({
                    "source_lot_code": src_lot.lot_code,
                    "target_lot_code": target_lot.lot_code,
                    "carried_kg": str(carry_kg),
                })

            # Mark source campaign as closed
            source_campaign.is_active = False
            source_campaign.save(update_fields=["is_active"])

        return {
            "campaign_code": source_campaign.campaign_code,
            "target_campaign_code": target_campaign.campaign_code,
            "lots_carried": len(carried_lots),
            "movements_created": movements_created,
            "carried_lots": carried_lots,
        }


# Convenience alias
close_campaign = CampaignCloseService.close_campaign
