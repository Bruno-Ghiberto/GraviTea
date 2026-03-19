"""Management command to check GrainLot balance consistency.

Iterates all GrainLots, compares total_kg against Sum(movements.quantity_kg),
reports any drift. Does NOT auto-correct (NF-001).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.db.models.functions import Coalesce

from apps.acopio.models import GrainLot


class Command(BaseCommand):
    help = "Check GrainLot balance consistency against movement ledger."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            type=str,
            default=None,
            help="Filter by tenant UUID. If omitted, checks all tenants.",
        )

    def handle(self, *args, **options):
        qs = GrainLot.all_objects.all()
        tenant_id = options.get("tenant")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        # Annotate each lot with the sum of its movements
        qs = qs.annotate(
            ledger_total=Coalesce(
                Sum("movements__quantity_kg"), Decimal("0.000")
            )
        )

        total_checked = 0
        drift_count = 0

        for lot in qs.iterator():
            total_checked += 1
            stored = lot.total_kg
            computed = lot.ledger_total

            if stored != computed:
                drift_count += 1
                delta = computed - stored
                self.stderr.write(
                    self.style.ERROR(
                        f"DRIFT: Lot {lot.lot_code} (pk={lot.pk}): "
                        f"stored={stored}, ledger={computed}, delta={delta}"
                    )
                )

        if drift_count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK: {total_checked} lots checked, no drift detected."
                )
            )
        else:
            self.stderr.write(
                self.style.ERROR(
                    f"FAIL: {drift_count}/{total_checked} lots have balance drift."
                )
            )
