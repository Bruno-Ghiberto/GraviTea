"""
Tests for the seed_compras management command.

Verifies idempotent execution and expected entity counts.
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.compras.models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem


pytestmark = [pytest.mark.django_db(transaction=True)]


@pytest.fixture
def seeded_core(tenant_context, branch):
    """Ensure core seed data exists (tenant, branch, roles, users)."""
    call_command("seed_data", verbosity=0)
    call_command("seed_inventario", verbosity=0)
    return tenant_context


class TestSeedCompras:
    """Verify seed_compras produces expected entities idempotently."""

    def test_seed_creates_purchase_orders(self, seeded_core):
        call_command("seed_compras", verbosity=0)
        assert PurchaseOrder.objects.count() >= 5
        assert PurchaseOrderItem.objects.count() >= 5
        assert GoodsReceipt.objects.count() >= 2

    def test_seed_idempotent(self, seeded_core):
        """Running twice produces same counts."""
        call_command("seed_compras", verbosity=0)
        count1_po = PurchaseOrder.objects.count()
        count1_gr = GoodsReceipt.objects.count()

        call_command("seed_compras", verbosity=0)
        assert PurchaseOrder.objects.count() == count1_po
        assert GoodsReceipt.objects.count() == count1_gr
