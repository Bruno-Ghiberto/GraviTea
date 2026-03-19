from decimal import Decimal

from django.db.models import Sum

from apps.core.encryption.utils import compute_blind_index
from apps.cuentas.models import AccountMovement, ProducerAccount


class PosicionConsolidadaService:
    @staticmethod
    def compute(tenant, producer_cuit: str, campaign):
        cuit_hash = compute_blind_index(producer_cuit)
        accounts = ProducerAccount.objects.filter(
            tenant=tenant,
            producer_cuit_hash=cuit_hash,
            campaign=campaign,
            is_active=True,
        ).select_related("grain_type", "branch")

        # Group by grain_type
        summary = accounts.values(
            "grain_type_id", "grain_type__code", "grain_type__name"
        ).annotate(
            total_grain_kg=Sum("grain_balance_kg"),
            total_ars=Sum("ars_balance"),
            total_usd=Sum("usd_balance"),
        )

        # Branch breakdown per grain_type
        result = []
        for row in summary:
            branches = accounts.filter(grain_type_id=row["grain_type_id"]).values(
                "branch_id",
                "branch__name",
                "grain_balance_kg",
                "ars_balance",
                "usd_balance",
            )
            result.append({**row, "branch_breakdown": list(branches)})
        return result


class StatementService:
    @staticmethod
    def generate(account, date_from, date_to):
        # Opening balance = sum of all movements before date_from
        pre = AccountMovement.objects.filter(
            producer_account=account,
            movement_at__lt=date_from,
        ).aggregate(
            grain=Sum("quantity_kg"),
            ars=Sum("ars_amount"),
            usd=Sum("usd_amount"),
        )
        opening_grain = pre["grain"] or Decimal("0.000")
        opening_ars = pre["ars"] or Decimal("0.000")
        opening_usd = pre["usd"] or Decimal("0.000")

        # Period movements
        period_mvts = list(
            AccountMovement.objects.filter(
                producer_account=account,
                movement_at__date__range=(date_from, date_to),
            )
            .order_by("movement_at")
            .select_related("romaneo", "created_by")
        )

        # Compute closing
        grain_delta = sum((m.quantity_kg for m in period_mvts), Decimal("0.000"))
        ars_delta = sum((m.ars_amount for m in period_mvts), Decimal("0.000"))
        usd_delta = sum((m.usd_amount for m in period_mvts), Decimal("0.000"))

        return {
            "opening_balance_kg": opening_grain,
            "opening_ars": opening_ars,
            "opening_usd": opening_usd,
            "movements": period_mvts,
            "closing_balance_kg": opening_grain + grain_delta,
            "closing_ars": opening_ars + ars_delta,
            "closing_usd": opening_usd + usd_delta,
        }
