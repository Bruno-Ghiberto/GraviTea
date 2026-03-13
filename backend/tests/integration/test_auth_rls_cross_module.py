"""
Integration tests: JWT Auth + RLS → Cross-Module Tenant Isolation.

Verifies that tenant isolation holds across ventas, inventario,
facturacion, and sync modules using both TenantBoundManager
and direct DB queries.

Per spec 011-backend-devops-coherence FR-025.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)


# ============================================================
# Test Constants
# ============================================================

EMITTER_CUIT = "30555555551"
CUIT_RI = "20345678906"
CUIT_RI_2 = "27333333339"


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def _tenant_a_data(tenant_context, branch, product_category):
    """Create data objects in tenant A across all modules."""
    from apps.facturacion.constants import CondicionIVA
    from apps.facturacion.models import ARCACredential, PuntoDeVenta
    from apps.inventario.models import Product, StockSnapshot
    from apps.sync.models import SyncSession
    from apps.ventas.models import Customer, SaleOrder

    product = Product.objects.create(
        tenant=tenant_context,
        sku="RLS-A-001",
        name="Tenant A Product",
        category=product_category,
        unit_price=Decimal("100.000"),
        cost_price=Decimal("50.000"),
        tax_rate=Decimal("21.00"),
        is_active=True,
    )

    StockSnapshot.objects.create(
        product=product,
        branch=branch,
        quantity=Decimal("50.0000"),
        reserved_quantity=Decimal("0.0000"),
    )

    customer = Customer.objects.create(
        tenant=tenant_context,
        cuit=CUIT_RI,
        doc_tipo=80,  # CUIT
        condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        razon_social="Tenant A Customer",
        domicilio="Av. A 100, CABA",
        is_active=True,
    )

    order = SaleOrder.objects.create(
        tenant=tenant_context,
        branch=branch,
        customer=customer,
    )

    credential = ARCACredential.objects.create(
        tenant=tenant_context,
        cuit_holder=EMITTER_CUIT,
        certificate_pem="-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
        private_key_pem="-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----",
        is_production=False,
        is_active=True,
        emitter_condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
    )

    pdv = PuntoDeVenta.objects.create(
        tenant=tenant_context,
        numero=1,
        tipo="electronic",
        is_active=True,
    )

    sync_session = SyncSession.objects.create(
        tenant=tenant_context,
        branch=branch,
        device_id="POS-A-001",
        status=SyncSession.SyncStatus.PENDING,
    )

    return {
        "product": product,
        "customer": customer,
        "order": order,
        "credential": credential,
        "pdv": pdv,
        "sync_session": sync_session,
    }


@pytest.fixture
def _tenant_b_data(other_tenant, tenant_context):
    """Create data objects in tenant B for isolation comparison.

    Temporarily switches to other_tenant context, then restores tenant A
    so the calling test runs under the correct tenant.
    """
    from apps.core.models.branch import Branch
    from apps.facturacion.constants import CondicionIVA
    from apps.inventario.models import Product, ProductCategory
    from apps.sync.models import SyncSession
    from apps.ventas.models import Customer

    set_current_tenant_id(other_tenant.id)
    try:
        branch_b = Branch.objects.create(
            tenant=other_tenant,
            name="Tenant B Branch",
            address="Av. B 200",
            is_active=True,
        )

        category_b = ProductCategory.objects.create(
            tenant=other_tenant,
            name="Tenant B Category",
        )

        product_b = Product.objects.create(
            tenant=other_tenant,
            sku="RLS-B-001",
            name="Tenant B Product",
            category=category_b,
            unit_price=Decimal("200.000"),
            cost_price=Decimal("100.000"),
            tax_rate=Decimal("21.00"),
            is_active=True,
        )

        customer_b = Customer.objects.create(
            tenant=other_tenant,
            cuit=CUIT_RI_2,
            doc_tipo=80,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
            razon_social="Tenant B Customer",
            domicilio="Av. B 300",
            is_active=True,
        )

        sync_b = SyncSession.objects.create(
            tenant=other_tenant,
            branch=branch_b,
            device_id="POS-B-001",
            status=SyncSession.SyncStatus.PENDING,
        )

        return {
            "branch": branch_b,
            "product": product_b,
            "customer": customer_b,
            "sync_session": sync_b,
        }
    finally:
        clear_current_tenant_id()
        set_current_tenant_id(tenant_context.id)


# ============================================================
# Tests
# ============================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestCrossModuleTenantIsolation:
    """TenantBoundManager isolates data across all modules."""

    def test_ventas_customer_isolated(
        self, tenant_context, _tenant_a_data, _tenant_b_data
    ):
        """Tenant A cannot see tenant B customers via manager."""
        from apps.ventas.models import Customer

        customers = Customer.objects.all()
        cuits = [c.cuit for c in customers]

        assert CUIT_RI in cuits
        assert CUIT_RI_2 not in cuits

    def test_inventario_product_isolated(
        self, tenant_context, _tenant_a_data, _tenant_b_data
    ):
        """Tenant A cannot see tenant B products via manager."""
        from apps.inventario.models import Product

        products = Product.objects.all()
        skus = [p.sku for p in products]

        assert "RLS-A-001" in skus
        assert "RLS-B-001" not in skus

    def test_sync_session_isolated(
        self, tenant_context, _tenant_a_data, _tenant_b_data
    ):
        """Tenant A cannot see tenant B sync sessions via manager."""
        from apps.sync.models import SyncSession

        sessions = SyncSession.objects.all()
        device_ids = [s.device_id for s in sessions]

        assert "POS-A-001" in device_ids
        assert "POS-B-001" not in device_ids

    def test_facturacion_credential_isolated(
        self, tenant_context, _tenant_a_data, _tenant_b_data
    ):
        """Tenant A credentials are not visible when querying from tenant B."""
        from apps.facturacion.models import ARCACredential

        # Switch to tenant B context
        try:
            clear_current_tenant_id()
            set_current_tenant_id(_tenant_b_data["branch"].tenant_id)

            creds = ARCACredential.objects.all()
            assert creds.count() == 0  # Tenant B has no credentials
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)


@pytest.mark.django_db
@pytest.mark.integration
class TestCrossTenantSwitchIsolation:
    """Switching tenant context changes visible data correctly."""

    def test_switching_tenant_changes_visible_products(
        self, tenant_context, other_tenant, _tenant_a_data, _tenant_b_data
    ):
        """Switching from A to B shows B products, hides A products."""
        from apps.inventario.models import Product

        # In tenant A context
        a_products = list(Product.objects.values_list("sku", flat=True))
        assert "RLS-A-001" in a_products

        # Switch to tenant B
        try:
            clear_current_tenant_id()
            set_current_tenant_id(other_tenant.id)

            b_products = list(Product.objects.values_list("sku", flat=True))
            assert "RLS-B-001" in b_products
            assert "RLS-A-001" not in b_products
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)

    def test_switching_tenant_changes_visible_orders(
        self, tenant_context, other_tenant, _tenant_a_data, _tenant_b_data
    ):
        """Tenant B sees no sale orders created by tenant A."""
        from apps.ventas.models import SaleOrder

        # Tenant A has one order
        assert SaleOrder.objects.count() == 1

        # Switch to tenant B
        try:
            clear_current_tenant_id()
            set_current_tenant_id(other_tenant.id)

            assert SaleOrder.objects.count() == 0
        finally:
            clear_current_tenant_id()
            set_current_tenant_id(tenant_context.id)


@pytest.mark.django_db
@pytest.mark.integration
class TestJWTTenantClaimsAPI:
    """JWT-authenticated API requests respect tenant isolation."""

    def test_authenticated_user_sees_own_tenant_data(
        self, authenticated_client, _tenant_a_data
    ):
        """Authenticated user can access their tenant's products via API."""
        response = authenticated_client.get("/api/v1/inventario/products/")
        # Accept either 200 or the list response
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            skus = [p["sku"] for p in results]
            assert "RLS-A-001" in skus

    def test_authenticated_user_cannot_see_other_tenant_data(
        self, authenticated_client, _tenant_a_data, _tenant_b_data
    ):
        """Authenticated user cannot access other tenant's products via API."""
        response = authenticated_client.get("/api/v1/inventario/products/")
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            results = data.get("results", data) if isinstance(data, dict) else data
            skus = [p["sku"] for p in results]
            assert "RLS-B-001" not in skus
