"""
Management command to seed facturacion (ARCA invoicing) data for development.

Creates test ARCA credentials, puntos de venta, DRAFT comprobantes with
IVA breakdowns, and a fake CAEA for offline-mode testing.
Requires seed_data to have been run first (tenant + branch + products).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.managers.tenant_bound import set_current_tenant_id
from apps.core.models import Tenant
from apps.facturacion.models import (
    CAEA,
    AlicIva,
    ARCACredential,
    CbteAsoc,
    Comprobante,
    PuntoDeVenta,
    Tributo,
)

# Self-signed test certificate (NOT a real credential)
TEST_CERT_PEM = """-----BEGIN CERTIFICATE-----
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

TEST_KEY_PEM = """-----BEGIN RSA PRIVATE KEY-----
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
UVEYFY PhbfkqJ2B14sLPaG+Qe5QibW/7SCfFKe7s7rkKCtSYO85tG7TIhSo0z6g5
kBxMaBiXnRKP0LDiRfnYIjqkHjB3PL2UrPMa8eDaOSbJWjTSM0LSRw==
-----END RSA PRIVATE KEY-----"""

TEST_CUIT = "20304050607"  # Emitter CUIT for test credentials


# Puntos de Venta
PUNTOS_DE_VENTA = [
    {"numero": 1, "tipo": "electronic", "description": "PtoVta Principal - Electrónico"},
    {"numero": 2, "tipo": "electronic", "description": "PtoVta Sucursal Norte"},
    {"numero": 5, "tipo": "electronic", "description": "PtoVta CAEA - Offline"},
]

# DRAFT Comprobantes: realistic Argentine ferreteria invoices
# (cbte_tipo, doc_tipo, doc_nro, concepto, receptor_cond_iva,
#  imp_neto, imp_iva, imp_op_ex, imp_trib, imp_tot_conc, imp_total,
#  mon_id, description, iva_entries, tributo_entries)
COMPROBANTES = [
    # Factura B (6) to Consumidor Final — typical retail sale
    {
        "cbte_tipo": 6,
        "doc_tipo": 96,  # DNI
        "doc_nro": "33445566",
        "concepto": 1,  # Productos
        "receptor_condicion_iva": 5,  # Consumidor Final
        "imp_neto": Decimal("42750.000"),
        "imp_iva": Decimal("8977.500"),
        "imp_op_ex": Decimal("0.000"),
        "imp_trib": Decimal("0.000"),
        "imp_tot_conc": Decimal("0.000"),
        "imp_total": Decimal("51727.500"),
        "description": "Taladro percutor 13mm DeWalt DWD024",
        "iva_entries": [
            {"iva_id": 5, "base_imp": Decimal("42750.000"), "importe": Decimal("8977.500")},
        ],
    },
    # Factura A (1) to Responsable Inscripto — business sale
    {
        "cbte_tipo": 1,
        "doc_tipo": 80,  # CUIT
        "doc_nro": "30712345670",
        "concepto": 1,
        "receptor_condicion_iva": 1,  # Responsable Inscripto
        "imp_neto": Decimal("95000.000"),
        "imp_iva": Decimal("19950.000"),
        "imp_op_ex": Decimal("0.000"),
        "imp_trib": Decimal("855.000"),
        "imp_tot_conc": Decimal("0.000"),
        "imp_total": Decimal("115805.000"),
        "description": "Soldadora Inverter 200A + Máscara fotosensible",
        "iva_entries": [
            {"iva_id": 5, "base_imp": Decimal("95000.000"), "importe": Decimal("19950.000")},
        ],
        "tributo_entries": [
            {
                "tributo_id": 99,
                "desc": "Percepción IIBB CABA",
                "base_imp": Decimal("95000.000"),
                "alic": Decimal("0.90"),
                "importe": Decimal("855.000"),
            },
        ],
    },
    # Factura A (1) to RI — mixed IVA rates
    {
        "cbte_tipo": 1,
        "doc_tipo": 80,
        "doc_nro": "30698765435",
        "concepto": 1,
        "receptor_condicion_iva": 1,
        "imp_neto": Decimal("15000.000"),
        "imp_iva": Decimal("2325.000"),
        "imp_op_ex": Decimal("0.000"),
        "imp_trib": Decimal("0.000"),
        "imp_tot_conc": Decimal("0.000"),
        "imp_total": Decimal("17325.000"),
        "description": "Mechas HSS + Disco diamantado (IVA mixto 21% y 10.5%)",
        "iva_entries": [
            {"iva_id": 5, "base_imp": Decimal("10000.000"), "importe": Decimal("2100.000")},
            {"iva_id": 4, "base_imp": Decimal("5000.000"), "importe": Decimal("225.000")},
        ],
    },
    # Factura B (6) — servicios (concepto 2, requires fch_serv dates)
    {
        "cbte_tipo": 6,
        "doc_tipo": 96,
        "doc_nro": "40556677",
        "concepto": 2,  # Servicios
        "receptor_condicion_iva": 5,
        "imp_neto": Decimal("25000.000"),
        "imp_iva": Decimal("5250.000"),
        "imp_op_ex": Decimal("0.000"),
        "imp_trib": Decimal("0.000"),
        "imp_tot_conc": Decimal("0.000"),
        "imp_total": Decimal("30250.000"),
        "description": "Servicio de mantenimiento cortadora césped",
        "is_service": True,
        "iva_entries": [
            {"iva_id": 5, "base_imp": Decimal("25000.000"), "importe": Decimal("5250.000")},
        ],
    },
    # Nota de Crédito B (8) — refund for first invoice
    {
        "cbte_tipo": 8,
        "doc_tipo": 96,
        "doc_nro": "33445566",
        "concepto": 1,
        "receptor_condicion_iva": 5,
        "imp_neto": Decimal("42750.000"),
        "imp_iva": Decimal("8977.500"),
        "imp_op_ex": Decimal("0.000"),
        "imp_trib": Decimal("0.000"),
        "imp_tot_conc": Decimal("0.000"),
        "imp_total": Decimal("51727.500"),
        "description": "NC por devolución Taladro DeWalt",
        "is_nota_credito": True,
        "iva_entries": [
            {"iva_id": 5, "base_imp": Decimal("42750.000"), "importe": Decimal("8977.500")},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed facturacion data (ARCA credentials, puntos de venta, DRAFT comprobantes) for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing facturacion data before seeding",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(is_active=True).first()
        if not tenant:
            self.stderr.write(
                self.style.ERROR(
                    "No active tenant found. Run 'seed_data' first."
                )
            )
            return

        set_current_tenant_id(tenant.id)

        self.stdout.write(
            f"Seeding facturacion for tenant '{tenant.name}'"
        )

        with transaction.atomic():
            if options["clear"]:
                self._clear_data(tenant)

            credential = self._create_credential(tenant)
            puntos = self._create_puntos_de_venta(tenant)
            comprobantes = self._create_comprobantes(tenant, puntos[0], credential)
            caea = self._create_caea(tenant, puntos[2])

        self.stdout.write(self.style.SUCCESS("Facturacion data seeded!"))
        self.stdout.write(f"\n=== Summary ===")
        self.stdout.write(f"ARCA Credential: {credential.cuit_holder} (homologación)")
        self.stdout.write(f"Puntos de Venta: {len(puntos)}")
        self.stdout.write(f"DRAFT Comprobantes: {len(comprobantes)}")
        self.stdout.write(f"CAEA: {'Created' if caea else 'Skipped'}")

    def _clear_data(self, tenant):
        """Clear existing facturacion data in reverse dependency order."""
        self.stdout.write("Clearing existing facturacion data...")
        # Child records first
        AlicIva.objects.filter(comprobante__tenant=tenant).delete()
        Tributo.objects.filter(comprobante__tenant=tenant).delete()
        CbteAsoc.objects.filter(comprobante__tenant=tenant).delete()
        Comprobante.all_objects.filter(tenant=tenant).delete()
        CAEA.all_objects.filter(tenant=tenant).delete()
        PuntoDeVenta.all_objects.filter(tenant=tenant).delete()
        ARCACredential.all_objects.filter(tenant=tenant).delete()
        self.stdout.write("  Facturacion data cleared.")

    def _create_credential(self, tenant):
        """Create test ARCA credential (homologación environment)."""
        self.stdout.write("Creating ARCA credential...")
        credential, created = ARCACredential.all_objects.get_or_create(
            tenant=tenant,
            is_production=False,
            defaults={
                "tenant_id": tenant.id,
                "cuit_holder": TEST_CUIT,
                "certificate_pem": TEST_CERT_PEM,
                "private_key_pem": TEST_KEY_PEM,
                "is_active": True,
                "certificate_expires_at": timezone.now() + timedelta(days=365),
                "last_unique_id": 0,
                "emitter_condicion_iva": 1,  # Responsable Inscripto
            },
        )
        status = "Created" if created else "Exists"
        self.stdout.write(f"  {status}: CUIT {credential.cuit_holder} (homologación)")
        return credential

    def _create_puntos_de_venta(self, tenant):
        """Create puntos de venta."""
        self.stdout.write("Creating puntos de venta...")
        puntos = []
        for data in PUNTOS_DE_VENTA:
            pv, created = PuntoDeVenta.all_objects.get_or_create(
                tenant=tenant,
                numero=data["numero"],
                defaults={
                    "tenant_id": tenant.id,
                    "tipo": data["tipo"],
                    "description": data["description"],
                    "is_active": True,
                    "fecha_alta": date.today(),
                },
            )
            puntos.append(pv)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  {status}: PtoVta {pv.numero} - {pv.description}")
        return puntos

    def _create_comprobantes(self, tenant, punto_venta, credential):
        """Create DRAFT comprobantes with IVA breakdowns."""
        self.stdout.write("Creating DRAFT comprobantes...")
        comprobantes = []
        today = date.today()

        for i, data in enumerate(COMPROBANTES):
            cbte_nro = i + 1
            cbte_kwargs = {
                "concepto": data["concepto"],
                "doc_tipo": data["doc_tipo"],
                "doc_nro": data["doc_nro"],
                "cbte_fch": today,
                "imp_total": data["imp_total"],
                "imp_neto": data["imp_neto"],
                "imp_iva": data["imp_iva"],
                "imp_trib": data.get("imp_trib", Decimal("0.000")),
                "imp_op_ex": data.get("imp_op_ex", Decimal("0.000")),
                "imp_tot_conc": data.get("imp_tot_conc", Decimal("0.000")),
                "mon_id": "PES",
                "mon_cotiz": Decimal("1.000000"),
                "emitter_cuit": credential.cuit_holder,
                "emitter_condicion_iva": 1,  # Responsable Inscripto
                "receptor_condicion_iva": data["receptor_condicion_iva"],
                "status": "DRAFT",
            }

            # Service dates for concepto 2 or 3
            if data.get("is_service"):
                cbte_kwargs["fch_serv_desde"] = today - timedelta(days=30)
                cbte_kwargs["fch_serv_hasta"] = today
                cbte_kwargs["fch_vto_pago"] = today + timedelta(days=30)

            # Use unique constraint fields as lookup for idempotency
            lookup = {
                "tenant": tenant,
                "punto_venta": punto_venta,
                "cbte_tipo": data["cbte_tipo"],
                "cbte_nro": cbte_nro,
            }
            comprobante, created = Comprobante.all_objects.get_or_create(
                **lookup, defaults=cbte_kwargs,
            )
            comprobantes.append(comprobante)

            if not created:
                tipo_name = {1: "Factura A", 6: "Factura B", 8: "NC B"}.get(
                    data["cbte_tipo"], f"Tipo {data['cbte_tipo']}"
                )
                self.stdout.write(f"  Skipped (exists): {tipo_name} #{cbte_nro}")
                continue

            # Create IVA breakdown entries
            for iva_data in data.get("iva_entries", []):
                AlicIva.objects.get_or_create(
                    comprobante=comprobante,
                    iva_id=iva_data["iva_id"],
                    defaults={
                        "base_imp": iva_data["base_imp"],
                        "importe": iva_data["importe"],
                    },
                )

            # Create tributo entries
            for trib_data in data.get("tributo_entries", []):
                Tributo.objects.get_or_create(
                    comprobante=comprobante,
                    tributo_id=trib_data["tributo_id"],
                    defaults={
                        "desc": trib_data["desc"],
                        "base_imp": trib_data["base_imp"],
                        "alic": trib_data["alic"],
                        "importe": trib_data["importe"],
                    },
                )

            # Create CbteAsoc for nota de credito (references first comprobante)
            if data.get("is_nota_credito") and len(comprobantes) > 1:
                CbteAsoc.objects.get_or_create(
                    comprobante=comprobante,
                    tipo=6,  # References Factura B
                    pto_vta=punto_venta.numero,
                    nro=1,  # References first comprobante
                )

            tipo_name = {1: "Factura A", 6: "Factura B", 8: "NC B"}.get(
                data["cbte_tipo"], f"Tipo {data['cbte_tipo']}"
            )
            self.stdout.write(
                f"  Created: {tipo_name} #{cbte_nro} - "
                f"${data['imp_total']} - {data['description'][:50]}"
            )

        return comprobantes

    def _create_caea(self, tenant, punto_venta):
        """Create a fake CAEA for offline-mode testing."""
        self.stdout.write("Creating fake CAEA (offline mode)...")
        today = date.today()
        # Determine current quincena
        if today.day <= 15:
            orden = 1
            fch_desde = today.replace(day=1)
            fch_hasta = today.replace(day=15)
        else:
            orden = 2
            fch_desde = today.replace(day=16)
            # Last day of month
            next_month = today.replace(day=28) + timedelta(days=4)
            fch_hasta = next_month - timedelta(days=next_month.day)

        periodo = today.strftime("%Y%m")
        fch_tope = fch_hasta + timedelta(days=5)

        caea, created = CAEA.all_objects.get_or_create(
            tenant=tenant,
            punto_venta=punto_venta,
            periodo=periodo,
            orden=orden,
            defaults={
                "tenant_id": tenant.id,
                "caea_code": "98765432109876",  # Fake 14-digit code
                "fch_vig_desde": fch_desde,
                "fch_vig_hasta": fch_hasta,
                "fch_tope_inf": fch_tope,
                "status": "ACTIVE",
            },
        )
        status = "Created" if created else "Exists"
        self.stdout.write(
            f"  {status}: CAEA {caea.caea_code} "
            f"(PtoVta {punto_venta.numero}, {periodo}-Q{orden})"
        )
        return caea
