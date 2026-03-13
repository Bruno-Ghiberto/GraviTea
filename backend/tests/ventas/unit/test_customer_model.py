"""
T083: Customer model unit tests.

Tests Customer model defaults, CUIT uniqueness constraint per tenant,
CondicionIVA choices, clean() validation, and __str__ representation.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)
from apps.facturacion.constants import CondicionIVA, DocTipo
from apps.ventas.models import Customer

# Verified Modulo-11 CUITs from ventas conftest
CUIT_RI = "20345678906"
CUIT_MONO = "20111111112"
CUIT_EXENTO = "20222222223"
CUIT_CF = "20000000001"


@pytest.mark.unit
@pytest.mark.django_db
class TestCustomerModel:
    """T083: Customer model behavior."""

    def test_create_customer_defaults(self, customer_factory):
        """New customer has is_active=True by default."""
        customer = customer_factory(cuit=CUIT_RI)
        assert customer.is_active is True

    def test_cuit_uniqueness_per_tenant(
        self, tenant_context, customer_factory, other_tenant
    ):
        """Same CUIT in same tenant → IntegrityError; different tenant → OK."""
        # First customer in primary tenant
        customer_factory(cuit=CUIT_RI)

        # Same CUIT in same tenant → IntegrityError (wrapped in savepoint)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                customer_factory(cuit=CUIT_RI, razon_social="Duplicate Corp")

        # Same CUIT in a different tenant → should succeed
        set_current_tenant_id(other_tenant.id)
        try:
            other_customer = Customer.objects.create(
                tenant=other_tenant,
                cuit=CUIT_RI,
                doc_tipo=DocTipo.CUIT,
                condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
                razon_social="Cross-Tenant Corp",
            )
            assert other_customer.cuit == CUIT_RI
        finally:
            clear_current_tenant_id()
            # Restore primary tenant context
            set_current_tenant_id(tenant_context.id)

    def test_condicion_iva_choices(self, customer_factory):
        """All standard CondicionIVA values are accepted."""
        c_ri = customer_factory(
            cuit=CUIT_RI,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert c_ri.condicion_iva == CondicionIVA.RESPONSABLE_INSCRIPTO

        c_cf = customer_factory(
            cuit=CUIT_CF,
            condicion_iva=CondicionIVA.CONSUMIDOR_FINAL,
        )
        assert c_cf.condicion_iva == CondicionIVA.CONSUMIDOR_FINAL

        c_mono = customer_factory(
            cuit=CUIT_MONO,
            condicion_iva=CondicionIVA.MONOTRIBUTISTA,
        )
        assert c_mono.condicion_iva == CondicionIVA.MONOTRIBUTISTA

        c_ex = customer_factory(
            cuit=CUIT_EXENTO,
            condicion_iva=CondicionIVA.EXENTO,
        )
        assert c_ex.condicion_iva == CondicionIVA.EXENTO

    def test_clean_calls_validate_cuit(self, tenant_context):
        """model.clean() with invalid CUIT raises ValidationError."""
        customer = Customer(
            tenant=tenant_context,
            cuit="20345678901",  # Invalid check digit (should be 6)
            doc_tipo=DocTipo.CUIT,
            condicion_iva=CondicionIVA.RESPONSABLE_INSCRIPTO,
            razon_social="Invalid CUIT Corp",
        )
        with pytest.raises(ValidationError, match="check digit"):
            customer.clean()

    def test_str_representation(self, customer_factory):
        """Customer.__str__ returns 'razon_social (CUIT: cuit)'."""
        customer = customer_factory(
            cuit=CUIT_RI,
            razon_social="ACME S.A.",
        )
        assert str(customer) == f"ACME S.A. (CUIT: {CUIT_RI})"
