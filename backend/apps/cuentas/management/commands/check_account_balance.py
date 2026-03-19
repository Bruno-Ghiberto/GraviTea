import sys
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.cuentas.models import AccountMovement, ProducerAccount


class Command(BaseCommand):
    help = "Check ProducerAccount stored balances against AccountMovement ledger sums."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant", type=str, help="UUID of tenant to check (optional)."
        )

    def handle(self, *args, **options):
        qs = ProducerAccount.all_objects.all()
        if options["tenant"]:
            qs = qs.filter(tenant_id=options["tenant"])

        discrepancies = 0
        for account in qs.iterator():
            agg = AccountMovement.objects.filter(
                producer_account=account
            ).aggregate(
                exp_grain=Sum("quantity_kg"),
                exp_ars=Sum("ars_amount"),
                exp_usd=Sum("usd_amount"),
            )
            exp_grain = agg["exp_grain"] or Decimal("0.000")
            exp_ars = agg["exp_ars"] or Decimal("0.000")
            exp_usd = agg["exp_usd"] or Decimal("0.000")

            if account.grain_balance_kg != exp_grain:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} grain_balance_kg "
                        f"stored={account.grain_balance_kg} expected={exp_grain}"
                    )
                )
                discrepancies += 1
            if account.ars_balance != exp_ars:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} ars_balance "
                        f"stored={account.ars_balance} expected={exp_ars}"
                    )
                )
                discrepancies += 1
            if account.usd_balance != exp_usd:
                self.stdout.write(
                    self.style.ERROR(
                        f"ERROR: Account {account.id} usd_balance "
                        f"stored={account.usd_balance} expected={exp_usd}"
                    )
                )
                discrepancies += 1

        if discrepancies == 0:
            self.stdout.write(self.style.SUCCESS("OK: 0 discrepancies"))
        else:
            sys.exit(1)
