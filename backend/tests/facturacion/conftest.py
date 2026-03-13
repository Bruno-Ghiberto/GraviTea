"""
Facturacion test fixtures and factories.

Provides fixtures for ARCA credential management, punto de venta,
comprobante lifecycle, and related entities (AlicIva, Tributo, CbteAsoc, CAEA).

Model field definitions sourced from specs/invoice-backend-developement/data-model.md.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.managers.tenant_bound import (
    clear_current_tenant_id,
    set_current_tenant_id,
)


# ============================================================
# Test Constants
# ============================================================

# Sample PEM certificate (self-signed, for testing only)
SAMPLE_CERT_PEM = """-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls
b2NhbGhvc3QwHhcNMjUwMTAxMDAwMDAwWhcNMjYwMTAxMDAwMDAwWjAUMRIwEAYD
VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7
7a5n6EHC4C1v3Jl5dExaRWjzMHOFMGbo2VpGOwJElKQHmJlgDCPDMPOsBJHFCpGF
REHhjMKICF0kuFVBiy7Mkmb5G6OMjy3FnJJK3eZaBqGWkFMKQJE8yrGM4pXKrBOG
yjSH0fAalzhSOfFNMJEH7QBYG0FBhzBHMOU3e/j5OPxMF2EKMJ90qWOHBNR50Ch
B9ZwAlcYPikEMOBhFCxui+p05Q3W3hg25G2gF3gCCC6UDFF8kPx5+kQMB2J4EIWE
DIO41UBkjGvQP1rZH5JDGiMZBaU5C8HCRJ5cC5VjfGYBBI/G2L9B6DLZCIoWKHG1
k9DaNWW5c8F/VfnGJP5NAgMBAAEwDQYJKoZIhvcNAQELBQADggEBAGo0RY/PlGOj
HaeTadFczfJjDWR/v2LPCmJ7MLhJaHeFgMGGN/JFQ3JyAt0CVMdGJRFjGWp3WTM0
K+rUOT3Qd7DNajLjM9TMt6BgMNB/J3Pr8e3PyPMTRuDGwUo7RFrwbWNhy7U2FuO3
CUYB/YJNazpIkPOJdkBEn6H/WXRJ2jGXRKBC2DVWJ9c6M0ESABN7KyK+OCIP2CL8
CBh9GRv4o2FLXziSzGNJhS7co0W7tz/XMGNJyjQNaaM3WjZ2N/0W10K/WBST/n+L
K/x2N6BMDL7t8iu0R8PkmAZJBOlMB/5GBnBSaA0Rp8PxFLGJv1UZLiOkBpkN2OB
ZP8cMpMRMfU=
-----END CERTIFICATE-----"""

# Sample PEM private key (for testing only — NOT a real key)
SAMPLE_KEY_PEM = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAu+2uZ+hBwuAtb9yZeXRMWkVo8zBzhTBm6NlaRjsCRJSkB5iZ
YAwjwzDzrASRxQqRhURB4YzCiAhdJLhVQYsuzJJm+RujjI8txZySSt3mWgahlpBT
CkCRPMqxjOKVyqwThso0h9HwGpc4UjnxTTCRB+0AWBtBQYcwRzDlN3v4+Tj8TBdh
CjCfdKljhwTUedAoQfWcAJXGD4pBDDgYRQsbovqdOUN1t4YNuRtoBd4AggulUFRR
fJD8efpEDAdieBCFhAyDuNVAZIxr0D9a2R+SQxojGQWlOQvBwkSeXAuVY3xmAQSP
xti/Qegy2QiKFihxtZPQ2jVluXPBf1X5xiT+TQIDAQABAoIBAC5RgZ+hJZ4jdMoR
KQVNlCOMSb+yAPMBjylO4HBKZW1MMH5JMc+tkD3g/oF7VRQE7X3rKNJnJPF2wMO
5z9+L6m9L6S+MH3JE7SDhG1WJOT6Qs7RQbB0bFRaGOF/p7BnCPIVGDH8N5HnQfR
2RL8ByG0ZPpBpU0y8gMFjJCfMtZR+cHiNnf1O82SDQS8FzOFMG7oJ/boLqXl7ey0
L3LMhNj/F5plI6b+Z5JxIemBFkWwMBkP5fOnMGKm/cJ7xPTYISvDBt6IkO9kIihp
DLG1m1EH+pFLeJq0y3OcdgronXl0K2cvqOPUTBpNFi5IKSKwvJGRp8x+J3SGGXVP
GaiNdOECgYEA7JyYR5BBqVDiCsqxIIiNOmZJVdGqx5b4FaAjYWZudZiPPOdyy4RO
g/2JvPCeS81hj1FuB4EKPXD4yyXPyblmDMyWGbHEb8YScAdXaaGRA7PAkJJQ20M9
c/2kSoI3NwGz40aLl6fsefGfVi5OT2J/tGOMjQMMKjNsxB6RP+6V20ECgYEAzD1k
S46BoXaD8UwPfRFc29cGKInH5DDpIF1WqHE0d8hR6qkOW3E10ASQ0NHl0MkC1xDH
e4yVS/tCYG30Tq/+jcHOQBRF5cJqGgv+K/CfMrj1PtJRYBjZDmAcv1LO1K+tBxfQ
fGFiRWtjB7+bOgjGXf0RE+zZ4lTiPl+g0qOSt00CgYAtPB+rz4OGHQIT5G3Y2aw1
yGCA/Iz+GRWdFJtqfBpM2G3hhN9PV57/S4KX6y0CbE0a3P0xyU0C6xo/9y0a0vI
k6+2M3mIWWMVHEz/a70tRhNd/3PvwHvPaaSdJKt7I7yQr/uPdH6T0aRw4nJqCjxH
LiYYWrAVs7BSd+1FEYEk0QKBgQCW+lE2j7pXBzK2bV9jqPBIhkqxH5MHdftJW2te
ScI7MfQnQ8JiX3NZJvPKUF3Y/1fXMN4f3/KMj0F7KF+2lXyHPxj/FTG3FCo/IVFB
FyNaJyB+b15lf6j6+fZJKCG6pJUBflnQkW/Y61B/kPA9OqXaPqETKKJmmsnJ/b9C
U56nOQKBgQCiYJmnig3pFkXT7VFiS9AGuKPPOXz7Ka1k0TYNDO1g1QZgFB5A0NYj
UVEYFYPhbfkqJ2B14sLPaG+Qe5QibW/7SCfFKe7s7rkKCtSYO85tG7TIhSo0z6g5
kBxMaBiXnRKP0LDiRfnYIjqkHjB3PL2UrPMa8eDaOSbJWjTSM0LSRw==
-----END RSA PRIVATE KEY-----"""

# Standard test CUIT (11 digits, no hyphens)
TEST_CUIT = "20123456786"


# ============================================================
# ARCACredential Fixtures
# ============================================================


@pytest.fixture
def credential_factory(tenant_context):
    """
    Factory for creating ARCACredential instances.

    Usage:
        cred = credential_factory()
        cred = credential_factory(is_production=True)
    """
    from apps.facturacion.models import ARCACredential

    def create_credential(**kwargs):
        defaults = {
            "tenant": tenant_context,
            "cuit_holder": TEST_CUIT,
            "cuit_represented": "",
            "certificate_pem": SAMPLE_CERT_PEM,
            "private_key_pem": SAMPLE_KEY_PEM,
            "is_production": False,
            "is_active": True,
            "certificate_expires_at": timezone.now() + timedelta(days=365),
            "last_unique_id": 0,
        }
        defaults.update(kwargs)
        return ARCACredential.objects.create(**defaults)

    return create_credential


@pytest.fixture
def arca_credential(credential_factory):
    """Create a default homologation ARCACredential."""
    return credential_factory()


@pytest.fixture
def production_credential(credential_factory):
    """Create a production ARCACredential."""
    return credential_factory(is_production=True)


@pytest.fixture
def expiring_credential(credential_factory):
    """Create an ARCACredential expiring within 30 days (triggers arca.W001)."""
    return credential_factory(
        certificate_expires_at=timezone.now() + timedelta(days=15),
    )


# ============================================================
# PuntoDeVenta Fixtures
# ============================================================


@pytest.fixture
def punto_venta_factory(tenant_context):
    """
    Factory for creating PuntoDeVenta instances.

    Usage:
        pv = punto_venta_factory()
        pv = punto_venta_factory(numero=5, tipo="manual")
    """
    from apps.facturacion.models import PuntoDeVenta

    _counter = [0]

    def create_punto_venta(**kwargs):
        _counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "numero": _counter[0],
            "tipo": "electronic",
            "description": f"Test PtoVta {_counter[0]}",
            "is_active": True,
            "fecha_alta": date.today(),
        }
        defaults.update(kwargs)
        return PuntoDeVenta.objects.create(**defaults)

    return create_punto_venta


@pytest.fixture
def punto_venta(punto_venta_factory):
    """Create a default electronic PuntoDeVenta (numero=1)."""
    return punto_venta_factory(numero=1)


@pytest.fixture
def inactive_punto_venta(punto_venta_factory):
    """Create an inactive PuntoDeVenta."""
    return punto_venta_factory(numero=99, is_active=False)


# ============================================================
# Comprobante Fixtures
# ============================================================


@pytest.fixture
def comprobante_factory(tenant_context, punto_venta):
    """
    Factory for creating Comprobante instances.

    Creates DRAFT comprobantes by default. Use status kwarg to override.

    Usage:
        cbte = comprobante_factory()
        cbte = comprobante_factory(cbte_tipo=6, status="AUTORIZADO", cae="12345678901234")
    """
    from apps.facturacion.models import Comprobante

    _nro_counter = [0]

    def create_comprobante(**kwargs):
        _nro_counter[0] += 1
        defaults = {
            "tenant": tenant_context,
            "punto_venta": punto_venta,
            "cbte_tipo": 6,  # Factura B
            "cbte_nro": _nro_counter[0],
            "concepto": 1,  # Products
            "doc_tipo": 80,  # CUIT
            "doc_nro": "20111111112",
            "cbte_fch": date.today(),
            "imp_total": Decimal("121.000"),
            "imp_neto": Decimal("100.000"),
            "imp_iva": Decimal("21.000"),
            "imp_trib": Decimal("0.000"),
            "imp_op_ex": Decimal("0.000"),
            "imp_tot_conc": Decimal("0.000"),
            "mon_id": "PES",
            "mon_cotiz": Decimal("1.000000"),
            "emitter_cuit": TEST_CUIT,
            "emitter_condicion_iva": 1,  # Responsable Inscripto
            "receptor_condicion_iva": 5,  # Consumidor Final
            "status": "DRAFT",
        }
        defaults.update(kwargs)
        return Comprobante.objects.create(**defaults)

    return create_comprobante


@pytest.fixture
def draft_comprobante(comprobante_factory):
    """Create a DRAFT comprobante (mutable)."""
    return comprobante_factory()


@pytest.fixture
def authorized_comprobante(comprobante_factory):
    """Create an AUTORIZADO comprobante (immutable, has CAE)."""
    return comprobante_factory(
        status="AUTORIZADO",
        cae="12345678901234",
        cae_fch_vto=date.today() + timedelta(days=10),
    )


@pytest.fixture
def observed_comprobante(comprobante_factory):
    """Create an OBSERVADO comprobante (immutable, has CAE with warnings)."""
    return comprobante_factory(
        cbte_nro=900,
        status="OBSERVADO",
        cae="98765432109876",
        cae_fch_vto=date.today() + timedelta(days=10),
        arca_errors=[{"Code": "10071", "Msg": "Observacion test"}],
    )


@pytest.fixture
def rejected_comprobante(comprobante_factory):
    """Create a RECHAZADO comprobante (mutable, allows retry)."""
    return comprobante_factory(
        cbte_nro=800,
        status="RECHAZADO",
        arca_errors=[{"Code": "10016", "Msg": "Error en importes"}],
    )


# ============================================================
# AlicIva Fixtures
# ============================================================


@pytest.fixture
def alic_iva_factory():
    """
    Factory for creating AlicIva entries.

    Usage:
        iva = alic_iva_factory(comprobante=cbte, iva_id=5, base_imp=Decimal("100"), importe=Decimal("21"))
    """
    from apps.facturacion.models import AlicIva

    def create_alic_iva(**kwargs):
        defaults = {
            "iva_id": 5,  # 21% General
            "base_imp": Decimal("100.000"),
            "importe": Decimal("21.000"),
        }
        defaults.update(kwargs)
        return AlicIva.objects.create(**defaults)

    return create_alic_iva


# ============================================================
# Tributo Fixtures
# ============================================================


@pytest.fixture
def tributo_factory():
    """
    Factory for creating Tributo entries.

    Usage:
        trib = tributo_factory(comprobante=cbte)
    """
    from apps.facturacion.models import Tributo

    def create_tributo(**kwargs):
        defaults = {
            "tributo_id": 1,  # Ingresos Brutos
            "desc": "Ingresos Brutos CABA",
            "base_imp": Decimal("100.000"),
            "alic": Decimal("3.00"),
            "importe": Decimal("3.000"),
        }
        defaults.update(kwargs)
        return Tributo.objects.create(**defaults)

    return create_tributo


# ============================================================
# CbteAsoc Fixtures
# ============================================================


@pytest.fixture
def cbte_asoc_factory():
    """
    Factory for creating CbteAsoc entries (for NC/ND references).

    Usage:
        asoc = cbte_asoc_factory(comprobante=nc, tipo=6, pto_vta=1, nro=1)
    """
    from apps.facturacion.models import CbteAsoc

    def create_cbte_asoc(**kwargs):
        defaults = {
            "tipo": 6,  # Factura B
            "pto_vta": 1,
            "nro": 1,
            "cuit": TEST_CUIT,
        }
        defaults.update(kwargs)
        return CbteAsoc.objects.create(**defaults)

    return create_cbte_asoc


# ============================================================
# CAEA Fixtures
# ============================================================


@pytest.fixture
def caea_factory(tenant_context, punto_venta):
    """
    Factory for creating CAEA instances.

    Usage:
        caea = caea_factory()
        caea = caea_factory(status="REPORTED")
    """
    from apps.facturacion.models import CAEA

    def create_caea(**kwargs):
        today = date.today()
        defaults = {
            "tenant": tenant_context,
            "punto_venta": punto_venta,
            "caea_code": f"{uuid.uuid4().hex[:14]}",
            "periodo": today.strftime("%Y%m"),
            "orden": 1 if today.day <= 15 else 2,
            "fch_vig_desde": today,
            "fch_vig_hasta": today + timedelta(days=15),
            "fch_tope_inf": today + timedelta(days=20),
            "status": "ACTIVE",
        }
        defaults.update(kwargs)
        return CAEA.objects.create(**defaults)

    return create_caea


@pytest.fixture
def active_caea(caea_factory):
    """Create an ACTIVE CAEA for the current quincena."""
    return caea_factory()


# ============================================================
# Comprobante with IVA Breakdown (Factura A pattern)
# ============================================================


@pytest.fixture
def factura_a_with_iva(comprobante_factory, alic_iva_factory):
    """
    Create a Factura A (CbteTipo=1) with IVA breakdown.

    RI -> RI: imp_neto=1000, IVA 21%=210, imp_total=1210
    """
    cbte = comprobante_factory(
        cbte_tipo=1,  # Factura A
        doc_tipo=80,
        doc_nro="30111111118",
        emitter_condicion_iva=1,  # RI
        receptor_condicion_iva=1,  # RI
        imp_neto=Decimal("1000.000"),
        imp_iva=Decimal("210.000"),
        imp_total=Decimal("1210.000"),
    )
    alic_iva_factory(
        comprobante=cbte,
        iva_id=5,  # 21%
        base_imp=Decimal("1000.000"),
        importe=Decimal("210.000"),
    )
    return cbte


@pytest.fixture
def factura_c_no_iva(comprobante_factory):
    """
    Create a Factura C (CbteTipo=11) — no IVA breakdown allowed.

    Monotributista -> any: imp_total = imp_neto (no IVA lines).
    """
    return comprobante_factory(
        cbte_tipo=11,  # Factura C
        emitter_condicion_iva=6,  # Monotributo
        receptor_condicion_iva=5,  # Consumidor Final
        imp_neto=Decimal("500.000"),
        imp_iva=Decimal("0.000"),
        imp_total=Decimal("500.000"),
    )


# ============================================================
# Service Comprobante (Concepto=2)
# ============================================================


@pytest.fixture
def service_comprobante(comprobante_factory):
    """Create a service comprobante (Concepto=2) requiring date fields."""
    today = date.today()
    return comprobante_factory(
        concepto=2,  # Services
        fch_serv_desde=today - timedelta(days=30),
        fch_serv_hasta=today,
        fch_vto_pago=today + timedelta(days=30),
    )


# ============================================================
# Cross-Tenant Isolation Fixtures
# ============================================================


@pytest.fixture
def other_tenant_credential(other_tenant):
    """Create an ARCACredential in a different tenant for isolation tests."""
    from apps.facturacion.models import ARCACredential

    set_current_tenant_id(other_tenant.id)
    try:
        return ARCACredential.objects.create(
            tenant=other_tenant,
            cuit_holder="30999999990",
            certificate_pem=SAMPLE_CERT_PEM,
            private_key_pem=SAMPLE_KEY_PEM,
            is_production=False,
            is_active=True,
            certificate_expires_at=timezone.now() + timedelta(days=365),
        )
    finally:
        clear_current_tenant_id()


@pytest.fixture
def other_tenant_comprobante(other_tenant):
    """Create a Comprobante in a different tenant for isolation tests."""
    from apps.facturacion.models import Comprobante, PuntoDeVenta

    set_current_tenant_id(other_tenant.id)
    try:
        pv = PuntoDeVenta.objects.create(
            tenant=other_tenant,
            numero=1,
            tipo="electronic",
            is_active=True,
        )
        return Comprobante.objects.create(
            tenant=other_tenant,
            punto_venta=pv,
            cbte_tipo=6,
            cbte_nro=1,
            concepto=1,
            doc_tipo=80,
            doc_nro="20222222223",
            cbte_fch=date.today(),
            imp_total=Decimal("242.000"),
            imp_neto=Decimal("200.000"),
            imp_iva=Decimal("42.000"),
            imp_trib=Decimal("0.000"),
            imp_op_ex=Decimal("0.000"),
            imp_tot_conc=Decimal("0.000"),
            mon_id="PES",
            mon_cotiz=Decimal("1.000000"),
            emitter_cuit="30999999990",
            emitter_condicion_iva=1,
            receptor_condicion_iva=5,
            status="AUTORIZADO",
            cae="99999999999999",
            cae_fch_vto=date.today() + timedelta(days=10),
        )
    finally:
        clear_current_tenant_id()
