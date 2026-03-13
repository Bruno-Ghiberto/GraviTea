---
name: gravitea-invoice
description: >
  Electronic invoicing patterns for GRAVITEA-ERP using Argentina's ARCA (ex-AFIP) system.
  Covers WSAA authentication, WSFEv1 invoice issuance, CAE lifecycle, TRA generation,
  comprobante types (A/B/C/M), fiscal QR codes, and multi-tenant certificate management.
  Trigger: When editing apps/facturacion/, working with ARCA integration, CAE generation,
  invoice PDF rendering, or fiscal QR codes.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
  source: ARCA Technical Manual (Notion) + AFIP WSFEv1 Specification
---

# Gravitea Invoice Skill

Patterns for Argentina's electronic invoicing via ARCA (ex-AFIP), covering the full lifecycle: WSAA authentication, WSFEv1 comprobante issuance, CAE authorization, fiscal document generation, and QR codes.

## When to Use

- Creating or modifying invoice models (Comprobante, ComprobanteLinea, ARCACredential)
- Implementing WSAA authentication flow (TRA generation, CMS signing, Token+Sign)
- Working with WSFEv1 methods (FECompUltimoAutorizado, FECAESolicitar)
- Building invoice PDF generation with mandatory fiscal QR
- Managing ARCA certificates (.crt/.key) per tenant
- Handling comprobante types (A, B, C, M) based on fiscal conditions
- Configuring testing vs production ARCA endpoints

---

## Critical Patterns

### Pattern 1: WSAA Authentication Flow

**WSAA (Web Service de Autenticacion y Autorizacion) grants a Token+Sign pair valid for 12 hours. Cache it and reuse until expiration.**

```python
# apps/facturacion/arca/wsaa.py
import datetime
from lxml import etree
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from django.utils import timezone


class WSAAClient:
    """
    WSAA authentication client for ARCA.

    Flow:
    1. Generate TRA (LoginTicketRequest) XML
    2. Sign TRA with tenant's private key (CMS/PKCS#7)
    3. Send signed TRA to WSAA endpoint
    4. Receive Token + Sign (valid 12h)
    """

    # CRITICAL: Use separate endpoints for testing vs production
    WSAA_URL_TESTING = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
    WSAA_URL_PRODUCTION = "https://wsaa.afip.gov.ar/ws/services/LoginCms"

    def generate_tra(self, service: str = "wsfe") -> str:
        """
        Generate TRA (LoginTicketRequest) XML.

        Rules:
        - uniqueId: Timestamp-based, monotonically increasing (NEVER fixed or repeated)
        - generationTime: now - 5 min (NTP synced)
        - expirationTime: now + 10 min (NTP synced)
        - service: Exact string for target WS ('wsfe' for invoicing)
        """
        now = timezone.now()

        tra = etree.Element("loginTicketRequest", version="1.0")

        header = etree.SubElement(tra, "header")

        unique_id = etree.SubElement(header, "uniqueId")
        unique_id.text = str(int(now.timestamp()))  # Monotonic, never repeated

        gen_time = etree.SubElement(header, "generationTime")
        gen_time.text = (now - datetime.timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

        exp_time = etree.SubElement(header, "expirationTime")
        exp_time.text = (now + datetime.timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )

        svc = etree.SubElement(tra, "service")
        svc.text = service

        return etree.tostring(tra, xml_declaration=True, encoding="UTF-8")

    def sign_tra(self, tra_xml: bytes, private_key_pem: bytes, cert_pem: bytes) -> bytes:
        """
        Sign TRA with CMS/PKCS#7 using tenant's private key + certificate.

        Args:
            tra_xml: TRA XML content
            private_key_pem: Tenant's private key (.key)
            cert_pem: Tenant's certificate (.crt)

        Returns:
            Base64-encoded CMS signature
        """
        private_key = serialization.load_pem_private_key(private_key_pem, password=None)
        certificate = x509.load_pem_x509_certificate(cert_pem)

        # Build PKCS#7 signed data (CMS)
        signed = (
            pkcs7.PKCS7SignatureBuilder()
            .set_data(tra_xml)
            .add_signer(certificate, private_key, hashes.SHA256())
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
        )

        return base64.b64encode(signed)
```

**TRA Generation Rules**:

| Field | Rule | Avoid |
|-------|------|-------|
| `uniqueId` | Timestamp-based `int(time.time())`, monotonically increasing | Fixed values, random IDs, sequential (0,1,2...) |
| `generationTime` | `now - 5 min` (NTP synced) | Long windows, exact clock times, unsynced servers |
| `expirationTime` | `now + 5-10 min` (NTP synced) | Windows > 15 min, unsynced servers |
| `service` | Exact string: `wsfe` for invoicing | Hardcoded without config, reusing TRA for other WS |

---

### Pattern 2: Token+Sign Caching

**Token+Sign is valid for 12 hours. Cache per tenant to avoid unnecessary WSAA calls.**

```python
# apps/facturacion/arca/auth_cache.py
from django.core.cache import cache
from django.utils import timezone


class ARCAAuthCache:
    """
    Cache WSAA Token+Sign per tenant.

    Token validity: 12 hours from WSAA.
    Cache TTL: 11 hours (1 hour safety margin).
    """

    CACHE_TTL = 11 * 60 * 60  # 11 hours in seconds

    @classmethod
    def get_cache_key(cls, tenant_id: str, service: str = "wsfe") -> str:
        return f"arca_auth:{tenant_id}:{service}"

    @classmethod
    def get_token_sign(cls, tenant_id: str) -> tuple[str, str] | None:
        """
        Get cached Token+Sign for tenant.

        Returns:
            Tuple of (token, sign) or None if expired/missing.
        """
        data = cache.get(cls.get_cache_key(tenant_id))
        if data:
            return data["token"], data["sign"]
        return None

    @classmethod
    def set_token_sign(cls, tenant_id: str, token: str, sign: str) -> None:
        """Cache Token+Sign with 11h TTL (1h safety margin)."""
        cache.set(
            cls.get_cache_key(tenant_id),
            {"token": token, "sign": sign, "cached_at": timezone.now().isoformat()},
            cls.CACHE_TTL,
        )

    @classmethod
    def invalidate(cls, tenant_id: str) -> None:
        """Force re-authentication for tenant."""
        cache.delete(cls.get_cache_key(tenant_id))
```

---

### Pattern 3: WSFEv1 Invoice Issuance

**The invoice flow is strictly sequential: authenticate -> get last number -> request CAE.**

```python
# apps/facturacion/arca/wsfe.py
from decimal import Decimal
from zeep import Client


class WSFEv1Client:
    """
    WSFEv1 (Web Service de Factura Electronica v1).

    Issues comprobantes A, B, C, M (without item detail) and obtains CAE.
    Requires valid Token+Sign from WSAA.
    """

    WSFEV1_URL_TESTING = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
    WSFEV1_URL_PRODUCTION = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"

    def __init__(self, token: str, sign: str, cuit: str, testing: bool = False):
        self.token = token
        self.sign = sign
        self.cuit = cuit
        self.client = Client(
            self.WSFEV1_URL_TESTING if testing else self.WSFEV1_URL_PRODUCTION
        )

    def _auth_dict(self) -> dict:
        """Auth block required by all WSFEv1 methods."""
        return {"Token": self.token, "Sign": self.sign, "Cuit": self.cuit}

    def get_ultimo_comprobante(self, punto_venta: int, cbte_tipo: int) -> int:
        """
        FECompUltimoAutorizado: Get last authorized comprobante number.

        This method is READ-ONLY. It does NOT authorize anything or generate CAE.
        It only needs PtoVta + CbteTipo.

        Returns:
            Last authorized CbteNro for this PtoVta + CbteTipo.
        """
        response = self.client.service.FECompUltimoAutorizado(
            Auth=self._auth_dict(),
            PtoVta=punto_venta,
            CbteTipo=cbte_tipo,
        )

        if response.Errors:
            raise ARCAError(response.Errors.Err[0].Code, response.Errors.Err[0].Msg)

        return response.CbteNro

    def solicitar_cae(self, comprobante_data: dict) -> dict:
        """
        FECAESolicitar: Request CAE for a comprobante.

        Sends to ARCA:
        "For this CUIT, PtoVta, CbteTipo, CbteNro, with these amounts,
        authorize this invoice and return the CAE."

        Args:
            comprobante_data: Dict with all required invoice fields.

        Returns:
            Dict with CAE, CAEFchVto, and result details.
        """
        fe_cab_req = {
            "CantReg": 1,
            "PtoVta": comprobante_data["punto_venta"],
            "CbteTipo": comprobante_data["cbte_tipo"],
        }

        fe_det_req = {
            "FECAEDetRequest": [{
                "Concepto": comprobante_data["concepto"],
                "DocTipo": comprobante_data["doc_tipo"],
                "DocNro": comprobante_data["doc_nro"],
                "CbteDesde": comprobante_data["cbte_nro"],
                "CbteHasta": comprobante_data["cbte_nro"],
                "CbteFch": comprobante_data["cbte_fch"],
                "ImpTotal": comprobante_data["imp_total"],
                "ImpTotConc": comprobante_data["imp_tot_conc"],
                "ImpNeto": comprobante_data["imp_neto"],
                "ImpOpEx": comprobante_data["imp_op_ex"],
                "ImpTrib": comprobante_data["imp_trib"],
                "ImpIVA": comprobante_data["imp_iva"],
                "MonId": comprobante_data.get("mon_id", "PES"),
                "MonCotiz": comprobante_data.get("mon_cotiz", 1),
            }]
        }

        response = self.client.service.FECAESolicitar(
            Auth=self._auth_dict(),
            FeCAEReq={"FeCabReq": fe_cab_req, "FeDetReq": fe_det_req},
        )

        det = response.FeDetResp.FECAEDetResponse[0]

        if det.Resultado != "A":  # A=Aprobado, R=Rechazado
            observations = []
            if det.Observaciones:
                observations = [
                    {"code": obs.Code, "msg": obs.Msg}
                    for obs in det.Observaciones.Obs
                ]
            raise ARCAError(
                code="CAE_REJECTED",
                message=f"CAE rejected: {observations}",
                observations=observations,
            )

        return {
            "cae": det.CAE,
            "cae_fch_vto": det.CAEFchVto,
            "resultado": det.Resultado,
            "cbte_nro": det.CbteDesde,
        }


class ARCAError(Exception):
    """ARCA service error with code and observations."""

    def __init__(self, code, message, observations=None):
        self.code = code
        self.message = message
        self.observations = observations or []
        super().__init__(f"ARCA Error {code}: {message}")
```

---

### Pattern 4: Comprobante Types & Fiscal Conditions

**Comprobante type depends on the fiscal condition of emitter and receiver.**

| CbteTipo | Code | Emitter Condition | Receiver |
|----------|------|-------------------|----------|
| Factura A | 1 | Responsable Inscripto | Responsable Inscripto |
| Factura B | 6 | Responsable Inscripto | Consumidor Final / Monotributo / Exento |
| Factura C | 11 | Monotributo / IVA Exento | Any |
| Factura M | 51 | Responsable Inscripto (new/flagged) | Responsable Inscripto |

```python
# apps/facturacion/constants.py
from enum import IntEnum


class CbteTipo(IntEnum):
    """ARCA comprobante type codes."""
    FACTURA_A = 1
    NOTA_DEBITO_A = 2
    NOTA_CREDITO_A = 3
    FACTURA_B = 6
    NOTA_DEBITO_B = 7
    NOTA_CREDITO_B = 8
    FACTURA_C = 11
    NOTA_DEBITO_C = 12
    NOTA_CREDITO_C = 13
    FACTURA_M = 51


class DocTipo(IntEnum):
    """Receiver document type codes."""
    CUIT = 80
    CUIL = 86
    CDI = 87
    DNI = 96
    CONSUMIDOR_FINAL = 99  # No document required


class CondicionIVA(IntEnum):
    """IVA fiscal condition codes."""
    RESPONSABLE_INSCRIPTO = 1
    MONOTRIBUTO = 6
    EXENTO = 4
    CONSUMIDOR_FINAL = 5


class Concepto(IntEnum):
    """Invoice concept type."""
    PRODUCTOS = 1
    SERVICIOS = 2
    PRODUCTOS_Y_SERVICIOS = 3


def resolver_tipo_comprobante(
    emitter_condition: CondicionIVA,
    receiver_condition: CondicionIVA,
) -> CbteTipo:
    """
    Determine comprobante type based on fiscal conditions.

    Decision tree:
    - Emitter is Monotributo or Exento -> Factura C
    - Emitter is Resp. Inscripto + Receiver is Resp. Inscripto -> Factura A
    - Emitter is Resp. Inscripto + Receiver is other -> Factura B
    """
    if emitter_condition in (CondicionIVA.MONOTRIBUTO, CondicionIVA.EXENTO):
        return CbteTipo.FACTURA_C

    if emitter_condition == CondicionIVA.RESPONSABLE_INSCRIPTO:
        if receiver_condition == CondicionIVA.RESPONSABLE_INSCRIPTO:
            return CbteTipo.FACTURA_A
        return CbteTipo.FACTURA_B

    raise ValueError(f"Unsupported emitter condition: {emitter_condition}")
```

---

### Pattern 5: Amount Fields Validation

**ARCA enforces strict mathematical relationships between amount fields.**

```python
# apps/facturacion/validators.py
from decimal import Decimal, ROUND_HALF_UP


def validate_importes(data: dict) -> None:
    """
    Validate ARCA amount field relationships with dual-tolerance validation.

    ARCA requires:
    ImpTotal = ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc

    ARCA dual-tolerance validation (critical for production):
    VALID if: |calculated - declared| / max(|calculated|, 1) <= 0.0001 (0.01% relative error)
      OR if: |calculated - declared| <= 0.01 (1 centavo absolute error)

    All amounts must be Decimal with 2 decimal places.

    Source: R2 p.131 (confidence 0.8125), backend-architect analysis
    """
    imp_total = Decimal(str(data["imp_total"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    imp_neto = Decimal(str(data["imp_neto"])).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    imp_iva = Decimal(str(data.get("imp_iva", 0))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    imp_trib = Decimal(str(data.get("imp_trib", 0))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    imp_op_ex = Decimal(str(data.get("imp_op_ex", 0))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    imp_tot_conc = Decimal(str(data.get("imp_tot_conc", 0))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    calculated = imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc

    # ARCA dual-tolerance validation
    absolute_error = abs(imp_total - calculated)
    relative_error = absolute_error / max(abs(calculated), Decimal('1'))

    # Pass if relative error <= 0.01% OR absolute error <= 1 centavo
    if relative_error > Decimal('0.0001') and absolute_error > Decimal('0.01'):
        raise ValueError(
            f"ImpTotal ({imp_total}) != ImpNeto ({imp_neto}) + ImpIVA ({imp_iva}) "
            f"+ ImpTrib ({imp_trib}) + ImpOpEx ({imp_op_ex}) + ImpTotConc ({imp_tot_conc}) "
            f"= {calculated}. Absolute error: {absolute_error}, Relative error: {relative_error}"
        )


def validate_service_dates(data: dict) -> None:
    """
    Validate service date fields based on Concepto (invoice concept).

    CRITICAL RULES:
    - Concepto=1 (Productos): Service date fields MUST BE OMITTED (not sent in XML)
    - Concepto=2 or 3 (Servicios): Service date fields are MANDATORY

    Service date fields: FchServDesde, FchServHasta, FchVtoPago

    ARCA will reject with error 10049 if:
    - Fields are missing when Concepto=2 or 3
    - Fields are present when Concepto=1

    Source: R2 p.29 (confidence 0.7778), requirements-analyst analysis
    """
    concepto = data.get("concepto", 1)
    has_dates = any(
        data.get(f) for f in ["fch_serv_desde", "fch_serv_hasta", "fch_vto_pago"]
    )

    if concepto == 1 and has_dates:
        raise ValueError(
            "Service dates (FchServDesde, FchServHasta, FchVtoPago) must be OMITTED "
            "when Concepto=1 (Productos). Do not send these fields in the XML request."
        )

    if concepto in (2, 3):
        if not all(data.get(f) for f in ["fch_serv_desde", "fch_serv_hasta", "fch_vto_pago"]):
            raise ValueError(
                "Service dates (FchServDesde, FchServHasta, FchVtoPago) are MANDATORY "
                "when Concepto=2 (Servicios) or 3 (Productos y Servicios). Error 10049."
            )

        # Validate date logic
        if data["fch_serv_desde"] > data["fch_serv_hasta"]:
            raise ValueError("FchServDesde must be <= FchServHasta")
        if data["fch_vto_pago"] < data.get("cbte_fch", data["fch_serv_desde"]):
            raise ValueError("FchVtoPago must be >= CbteFch")


# Amount field definitions
AMOUNT_FIELDS = {
    "ImpTotal": "Total amount of the invoice",
    "ImpNeto": "Net taxable amount (base for IVA calculation)",
    "ImpIVA": "Total IVA amount (21%, 10.5%, 27%, etc.)",
    "ImpTrib": "Other taxes/tributes (Ingresos Brutos, etc.) - OMIT <Tributos> element if 0",
    "ImpOpEx": "Amount exempt from IVA",
    "ImpTotConc": "Non-taxable amount (conceptos no gravados)",
}


# CRITICAL: Tributos XML Generation Rule
# If ImpTrib = 0, the <Tributos> element must NOT be sent at all.
# NOT: <Tributos></Tributos> (empty element)
# BUT: Complete omission from XML structure
# Source: R1 errors 10025-10029, backend-architect analysis
```

---

### Pattern 6: Comprobante Model (Immutable after CAE)

**Authorized comprobantes are immutable. Once CAE is obtained, the record cannot be modified.**

```python
# apps/facturacion/models.py
from apps.core.models import TenantBoundModel
from apps.core.encryption.fields import EncryptedTextField


class Comprobante(TenantBoundModel):
    """
    Electronic invoice authorized by ARCA.

    Immutable after CAE authorization. To correct, issue a
    Nota de Credito (credit note) referencing this comprobante.

    Fields match ARCA WSFEv1 naming for traceability.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"                  # CbteNro reserved, not yet submitted
        VALIDANDO = "VALIDANDO", "Validating"     # Sent to ARCA, awaiting response
        AUTORIZADO = "AUTORIZADO", "Authorized"   # CAE obtained (immutable)
        OBSERVADO = "OBSERVADO", "Observed"       # CAE granted with warnings (immutable)
        RECHAZADO = "RECHAZADO", "Rejected"       # ARCA rejected, allows retry

    # ARCA fiscal identifiers
    punto_venta = models.PositiveIntegerField()
    cbte_tipo = models.PositiveSmallIntegerField()  # CbteTipo enum
    cbte_nro = models.PositiveBigIntegerField()     # Sequential per PtoVta+CbteTipo

    # Dates
    cbte_fch = models.DateField(help_text="Invoice date (YYYYMMDD for ARCA)")
    created_at = models.DateTimeField(auto_now_add=True)

    # Emitter data (from tenant)
    emitter_cuit = models.CharField(max_length=13)
    emitter_condicion_iva = models.PositiveSmallIntegerField()

    # Receiver data
    receptor_doc_tipo = models.PositiveSmallIntegerField()  # DocTipo enum
    receptor_doc_nro = models.CharField(max_length=20)
    receptor_condicion_iva = models.PositiveSmallIntegerField()

    # Concept
    concepto = models.PositiveSmallIntegerField(default=1)  # Concepto enum

    # Amounts — DECIMAL(17,3) per Constitution Section I; display precision is 2 decimals (serializer-level)
    imp_total = models.DecimalField(max_digits=17, decimal_places=3)
    imp_neto = models.DecimalField(max_digits=17, decimal_places=3)
    imp_iva = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
    imp_trib = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
    imp_op_ex = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))
    imp_tot_conc = models.DecimalField(max_digits=17, decimal_places=3, default=Decimal("0"))

    # Currency
    mon_id = models.CharField(max_length=3, default="PES")  # PES = ARS
    mon_cotiz = models.DecimalField(max_digits=10, decimal_places=6, default=Decimal("1"))

    # CAE (populated after ARCA authorization)
    cae = models.CharField(max_length=14, null=True, blank=True, db_index=True)
    cae_fch_vto = models.DateField(null=True, blank=True)

    # Status and audit
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    arca_result = models.JSONField(null=True, blank=True)  # Full ARCA response snapshot
    observations = models.JSONField(null=True, blank=True)  # ARCA observations/events

    # Reference to sale/transaction that originated this invoice
    reference_id = models.UUIDField(null=True, blank=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "punto_venta", "cbte_tipo", "cbte_nro"],
                name="uq_comprobante_fiscal",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "cbte_fch"]),
        ]

    def save(self, *args, **kwargs):
        """Enforce immutability for authorized comprobantes."""
        if self.pk:
            existing = Comprobante.all_objects.filter(pk=self.pk).first()
            if existing and existing.status in (self.Status.AUTORIZADO, self.Status.OBSERVADO):
                raise ValueError(
                    "Authorized comprobantes are immutable. "
                    "Issue a Nota de Credito to correct."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of comprobantes."""
        raise ValueError(
            "Comprobantes cannot be deleted. "
            "Issue a Nota de Credito instead."
        )
```

---

### Pattern 7: Tenant ARCA Credentials

**Each tenant has its own CUIT, certificate, and punto de venta configuration. Private keys are stored encrypted.**

```python
# apps/facturacion/models.py
from apps.core.encryption.fields import EncryptedTextField


class ARCACredential(TenantBoundModel):
    """
    ARCA authentication credentials per tenant.

    Stores the digital certificate (.crt) and encrypted private key (.key)
    required for WSAA authentication. Each tenant may have multiple
    certificates (for key rotation).
    """

    cuit = models.CharField(max_length=11, help_text="Tenant's CUIT (11 digits, no hyphens)")
    certificate_pem = models.TextField(help_text="X.509 certificate in PEM format (.crt)")
    private_key_pem = EncryptedTextField(help_text="RSA private key in PEM format (.key)")
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Certificate expiration date"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "cuit"],
                condition=models.Q(is_active=True),
                name="uq_active_arca_credential_per_tenant",
            ),
        ]


class PuntoDeVenta(TenantBoundModel):
    """
    Punto de venta configuration per tenant.

    Each PtoVta is registered with ARCA for electronic invoicing.
    A tenant may have multiple PtoVta for different branches.
    """

    numero = models.PositiveIntegerField(help_text="Punto de venta number (1-99999)")
    branch = models.ForeignKey(
        "core.Branch", on_delete=models.PROTECT, null=True, blank=True,
        help_text="Branch associated with this PtoVta"
    )
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=100, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "numero"],
                name="uq_punto_venta_per_tenant",
            ),
        ]
```

---

### Pattern 8: Mandatory Fiscal QR Code

**The QR code is mandatory on every comprobante. It is generated locally and must point to ARCA's verification servers.**

```python
# apps/facturacion/qr.py
import json
import base64
from datetime import date


def generate_fiscal_qr_data(comprobante) -> str:
    """
    Generate the data URL for the mandatory fiscal QR code.

    The QR is generated LOCALLY and printed on the comprobante.
    It encodes fiscal data and points to ARCA's verification servers.

    Required by ARCA regulation on all electronic invoices.

    Returns:
        Full URL for QR code generation (to be rendered as QR image).
    """
    qr_data = {
        "ver": 1,
        "fecha": comprobante.cbte_fch.strftime("%Y-%m-%d"),
        "cuit": int(comprobante.emitter_cuit.replace("-", "")),
        "ptoVta": comprobante.punto_venta,
        "tipoCmp": comprobante.cbte_tipo,
        "nroCmp": comprobante.cbte_nro,
        "importe": float(comprobante.imp_total),
        "moneda": comprobante.mon_id,
        "ctz": float(comprobante.mon_cotiz),
        "tipoDocRec": comprobante.receptor_doc_tipo,
        "nroDocRec": int(comprobante.receptor_doc_nro),
        "tipoCodAut": "E",  # E = CAE
        "codAut": int(comprobante.cae),
    }

    # Base64 encode the JSON payload
    payload = base64.urlsafe_b64encode(
        json.dumps(qr_data, separators=(",", ":")).encode()
    ).decode()

    return f"https://www.afip.gob.ar/fe/qr/?p={payload}"
```

---

### Pattern 9: Complete Invoice Issuance Service

**Orchestrates the full flow: auth -> last number -> CAE request -> persist.**

```python
# apps/facturacion/services.py
from django.db import transaction


class InvoiceService:
    """
    Orchestrates the complete invoice issuance flow.

    Flow:
    1. Authenticate with WSAA (or use cached Token+Sign)
    2. Get last authorized CbteNro (FECompUltimoAutorizado)
    3. Calculate next CbteNro = last + 1
    4. Save comprobante as DRAFT in DB
    5. Request CAE (FECAESolicitar)
    6. Update comprobante with CAE and status AUTORIZADO
    """

    @transaction.atomic
    def issue_comprobante(
        self,
        tenant,
        punto_venta: int,
        cbte_tipo: int,
        invoice_data: dict,
    ) -> Comprobante:
        # Step 1: Get or refresh WSAA auth
        credential = ARCACredential.objects.get(tenant=tenant, is_active=True)
        token, sign = self._get_auth(tenant, credential)

        wsfe = WSFEv1Client(
            token=token,
            sign=sign,
            cuit=credential.cuit,
            testing=tenant.arca_testing_mode,
        )

        # Step 2: Get last authorized number
        last_nro = wsfe.get_ultimo_comprobante(punto_venta, cbte_tipo)
        next_nro = last_nro + 1

        # Step 3: Save as DRAFT (reserve the number)
        comprobante = Comprobante.objects.create(
            tenant=tenant,
            punto_venta=punto_venta,
            cbte_tipo=cbte_tipo,
            cbte_nro=next_nro,
            status=Comprobante.Status.DRAFT,
            emitter_cuit=credential.cuit,
            **invoice_data,
        )

        # Step 4: Request CAE
        try:
            comprobante.status = Comprobante.Status.VALIDANDO
            comprobante.save()

            cae_result = wsfe.solicitar_cae({
                "punto_venta": punto_venta,
                "cbte_tipo": cbte_tipo,
                "cbte_nro": next_nro,
                **invoice_data,
            })

            # Step 5: Update with CAE (now immutable)
            comprobante.cae = cae_result["cae"]
            comprobante.cae_fch_vto = cae_result["cae_fch_vto"]
            comprobante.status = Comprobante.Status.AUTORIZADO
            comprobante.arca_result = cae_result
            comprobante.save()

        except ARCAError as e:
            comprobante.status = Comprobante.Status.RECHAZADO
            comprobante.observations = e.observations
            comprobante.arca_result = {"error": str(e)}
            comprobante.save()
            raise

        return comprobante

    def _get_auth(self, tenant, credential) -> tuple[str, str]:
        """Get cached or fresh Token+Sign."""
        cached = ARCAAuthCache.get_token_sign(str(tenant.id))
        if cached:
            return cached

        wsaa = WSAAClient()
        tra = wsaa.generate_tra(service="wsfe")
        signed_tra = wsaa.sign_tra(
            tra, credential.private_key_pem.encode(), credential.certificate_pem.encode()
        )
        token, sign = wsaa.login(signed_tra)
        ARCAAuthCache.set_token_sign(str(tenant.id), token, sign)
        return token, sign
```

---

### Pattern 10: Post-CAE Mandatory Data

**After CAE authorization, these fields MUST be stored and displayed.**

**Database persistence** (all required):

| Field | Source | Purpose |
|-------|--------|---------|
| `cbte_tipo` | Request | Comprobante type (A/B/C/M) |
| `punto_venta` | Request | Punto de venta |
| `cbte_nro` | FECompUltimoAutorizado + 1 | Sequential number |
| `cae` | FECAESolicitar response | Unique authorization code |
| `cae_fch_vto` | FECAESolicitar response | CAE expiration date |
| `cbte_fch` | Request | Emission date |
| `arca_result` | Full response | Audit snapshot |
| `observations` | Response observations | ARCA events/warnings |

**Mandatory on printed/PDF comprobante**:

- Comprobante type (A / B / C)
- Punto de venta + numero completo
- Date
- Emitter data (razon social, CUIT, domicilio, condicion IVA)
- Receiver data (nombre, doc type + number, condicion IVA)
- All amount fields
- **CAE number**
- **CAE expiration date**
- **Fiscal QR code** (mandatory, generated locally)

---

## Decision Tree

```
Issuing an invoice?
|-- Get fiscal conditions
|   |-- Emitter is Monotributo/Exento? -> Factura C
|   |-- Emitter RI + Receiver RI? -> Factura A
|   +-- Emitter RI + Receiver other? -> Factura B
|
|-- Need Token+Sign?
|   |-- Cached and valid? -> Reuse (12h TTL)
|   +-- Expired/missing? -> Generate TRA -> Sign CMS -> Call WSAA
|
|-- Getting CbteNro?
|   |-- Call FECompUltimoAutorizado(PtoVta, CbteTipo)
|   +-- next_nro = last_nro + 1
|
|-- Requesting CAE?
|   |-- Validate amounts: ImpTotal = ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc
|   |-- Call FECAESolicitar
|   |-- Resultado = "A"? -> Store CAE + mark AUTORIZADO (immutable)
|   |-- Resultado = "O"? -> Store CAE + observations + mark OBSERVADO (immutable)
|   +-- Resultado = "R"? -> Store errors + mark RECHAZADO (allows retry)
|
+-- After CAE obtained?
    |-- Store in DB (immutable)
    |-- Generate PDF with mandatory fields
    |-- Generate fiscal QR code
    +-- Deliver (email, download, print)

Correcting an authorized invoice?
|-- NEVER modify the original comprobante
|-- Issue Nota de Credito referencing original
+-- Nota de Credito follows same ARCA flow

Testing vs Production?
|-- WSAA: wsaahomo.afip.gov.ar (test) vs wsaa.afip.gov.ar (prod)
|-- WSFEv1: wswhomo.afip.gov.ar (test) vs servicios1.afip.gov.ar (prod)
+-- Certificates: Test certs via WSASS with clave fiscal
```

---

## Anti-Patterns (What NOT to Do)

### Anti-Pattern 1: Modifying Authorized Comprobantes

```python
# FORBIDDEN - Authorized comprobantes are immutable
comprobante = Comprobante.objects.get(cae="12345678901234")
comprobante.imp_total = Decimal("999.99")  # Will raise ValueError
comprobante.save()

# CORRECT - Issue a Nota de Credito
nota_credito = invoice_service.issue_comprobante(
    tenant=tenant,
    punto_venta=comprobante.punto_venta,
    cbte_tipo=CbteTipo.NOTA_CREDITO_A,  # Credit note type
    invoice_data={...},  # Reference original comprobante
)
```

### Anti-Pattern 2: Fixed or Repeated uniqueId in TRA

```python
# FORBIDDEN - Fixed uniqueId causes WSAA rejection
unique_id.text = "1"  # Will fail after first use

# FORBIDDEN - Sequential counter (0, 1, 2...) - replay attack risk
unique_id.text = str(counter)  # Attackers can reuse old signatures

# FORBIDDEN - Random IDs (not monotonic)
unique_id.text = str(random.randint(1, 99999))

# CORRECT - Timestamp-based, monotonically increasing
unique_id.text = str(int(timezone.now().timestamp()))

# CRITICAL: Timestamp-based prevents replay attacks and ensures uniqueness
# Source: R2 p.32 (confidence 0.7016), security-engineer analysis
```

### Anti-Pattern 3: Skipping CbteNro Sequence

```python
# FORBIDDEN - Never hardcode or skip comprobante numbers
cbte_nro = 500  # Random number -> ARCA will reject

# CORRECT - Always query last authorized + 1
last = wsfe.get_ultimo_comprobante(punto_venta, cbte_tipo)
next_nro = last + 1
```

### Anti-Pattern 4: Storing Private Keys Unencrypted

```python
# FORBIDDEN - Plain text private key in database
private_key = models.TextField()  # Anyone with DB access can read

# CORRECT - Use EncryptedTextField (AES-256-GCM)
private_key_pem = EncryptedTextField()  # Encrypted at rest
```

### Anti-Pattern 5: Missing Amount Validation

```python
# FORBIDDEN - Sending amounts without validation
wsfe.solicitar_cae({
    "imp_total": 121.00,
    "imp_neto": 100.00,
    "imp_iva": 20.00,  # 100 + 20 != 121 -> ARCA rejects
    ...
})

# CORRECT - Always validate the amount equation first
validate_importes(invoice_data)
wsfe.solicitar_cae(invoice_data)
```

### Anti-Pattern 6: Incorrect Certificate DN Format

```python
# FORBIDDEN - Certificate DN with hyphens in CUIT
# CSR serialNumber: "CUIT 20-12345678-9"  # ARCA will REJECT

# FORBIDDEN - Missing space after "CUIT"
# CSR serialNumber: "CUIT20123456789"  # ARCA will REJECT

# CORRECT - CUIT with 11 digits, NO hyphens, space after "CUIT"
# CSR serialNumber: "CUIT 20123456789"

# Example CSR generation:
openssl req -new -key private.key \
  -subj "/C=AR/O=MiEmpresa/CN=MiSistema/serialNumber=CUIT 20123456789" \
  -out request.csr

# CRITICAL: Format must be exactly "CUIT " + 11 digits (no hyphens)
# Source: R3 p.7 (confidence 0.8275), security-engineer analysis
```

---

## Testing

### WSASS Testing Environment

ARCA provides a testing environment (homologacion) accessible with a clave fiscal for physical persons. Test certificates can be obtained through WSASS.

```python
# tests/facturacion/test_wsfe.py
import pytest
from decimal import Decimal


@pytest.mark.unit
class TestComprobanteTypeResolution:
    def test_ri_to_ri_returns_factura_a(self):
        """Resp. Inscripto to Resp. Inscripto = Factura A."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert result == CbteTipo.FACTURA_A

    def test_ri_to_cf_returns_factura_b(self):
        """Resp. Inscripto to Consumidor Final = Factura B."""
        result = resolver_tipo_comprobante(
            CondicionIVA.RESPONSABLE_INSCRIPTO,
            CondicionIVA.CONSUMIDOR_FINAL,
        )
        assert result == CbteTipo.FACTURA_B

    def test_monotributo_returns_factura_c(self):
        """Monotributo emitter always = Factura C."""
        result = resolver_tipo_comprobante(
            CondicionIVA.MONOTRIBUTO,
            CondicionIVA.RESPONSABLE_INSCRIPTO,
        )
        assert result == CbteTipo.FACTURA_C


@pytest.mark.unit
class TestAmountValidation:
    def test_valid_amounts_pass(self):
        """Valid amount equation does not raise."""
        validate_importes({
            "imp_total": Decimal("121.00"),
            "imp_neto": Decimal("100.00"),
            "imp_iva": Decimal("21.00"),
            "imp_trib": Decimal("0.00"),
            "imp_op_ex": Decimal("0.00"),
            "imp_tot_conc": Decimal("0.00"),
        })

    def test_invalid_total_raises(self):
        """Mismatched total raises ValueError."""
        with pytest.raises(ValueError, match="ImpTotal"):
            validate_importes({
                "imp_total": Decimal("999.00"),
                "imp_neto": Decimal("100.00"),
                "imp_iva": Decimal("21.00"),
            })


@pytest.mark.unit
class TestFiscalQR:
    def test_qr_url_format(self, comprobante_factory):
        """QR URL points to AFIP verification server."""
        comprobante = comprobante_factory(cae="12345678901234")
        url = generate_fiscal_qr_data(comprobante)

        assert url.startswith("https://www.afip.gob.ar/fe/qr/?p=")


@pytest.mark.integration
@pytest.mark.django_db
class TestComprobanteImmutability:
    def test_cannot_modify_authorized(self, comprobante_factory):
        """Authorized comprobantes cannot be modified."""
        comprobante = comprobante_factory(status=Comprobante.Status.AUTORIZADO)
        comprobante.imp_total = Decimal("999.99")

        with pytest.raises(ValueError, match="immutable"):
            comprobante.save()

    def test_cannot_delete_comprobante(self, comprobante_factory):
        """Comprobantes cannot be deleted."""
        comprobante = comprobante_factory()

        with pytest.raises(ValueError, match="cannot be deleted"):
            comprobante.delete()
```

---

## NTP Synchronization

**Critical**: WSAA rejects TRA if server clock is off by more than a few minutes.

```python
# apps/facturacion/checks.py
from django.core.checks import Warning, register
import subprocess


@register()
def check_ntp_sync(app_configs, **kwargs):
    """Warn if server clock may be out of sync."""
    errors = []
    try:
        # Check NTP sync status (Linux)
        result = subprocess.run(
            ["timedatectl", "show", "--property=NTPSynchronized"],
            capture_output=True, text=True, timeout=5,
        )
        if "NTPSynchronized=yes" not in result.stdout:
            errors.append(
                Warning(
                    "Server clock may not be NTP synchronized. "
                    "ARCA WSAA requires accurate time.",
                    hint="Ensure NTP is configured and synchronized.",
                    id="facturacion.W001",
                )
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # Non-Linux or timedatectl unavailable
    return errors
```

---

## Commands

```bash
# Run invoice tests
cd backend && pytest tests/facturacion/ -v

# Run unit tests only (no ARCA connection)
cd backend && pytest tests/facturacion/ -m "unit" -v

# Run integration tests (requires ARCA test credentials)
cd backend && pytest tests/facturacion/ -m "integration" -v

# Check amount validation
cd backend && python manage.py shell -c "
from apps.facturacion.validators import validate_importes
from decimal import Decimal
validate_importes({
    'imp_total': Decimal('121.00'),
    'imp_neto': Decimal('100.00'),
    'imp_iva': Decimal('21.00'),
    'imp_trib': Decimal('0'), 'imp_op_ex': Decimal('0'), 'imp_tot_conc': Decimal('0'),
})
print('Amounts valid')
"

# Test comprobante type resolution
cd backend && python manage.py shell -c "
from apps.facturacion.constants import resolver_tipo_comprobante, CondicionIVA
print(resolver_tipo_comprobante(CondicionIVA.RESPONSABLE_INSCRIPTO, CondicionIVA.CONSUMIDOR_FINAL))
"
```

---

## Developer Checklist

Before submitting invoicing-related code, verify:

- [ ] WSAA Token+Sign cached per tenant (11h TTL, not 12h)
- [ ] TRA uses timestamp-based uniqueId (`int(time.time())`) and NTP-synced times
- [ ] CbteNro obtained via FECompUltimoAutorizado (never hardcoded)
- [ ] Amount equation validated: ImpTotal = ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc
- [ ] Authorized comprobantes are immutable (no UPDATE/DELETE)
- [ ] Corrections use Nota de Credito, not modification
- [ ] Private keys stored with EncryptedTextField
- [ ] Fiscal QR code generated on every comprobante
- [ ] QR points to `https://www.afip.gob.ar/fe/qr/`
- [ ] Testing uses homologacion endpoints (wsaahomo/wswhomo)
- [ ] Production uses production endpoints (wsaa/servicios1)
- [ ] Tenant isolation enforced on credentials and comprobantes
- [ ] ARCA response snapshot stored for audit trail

---

## ARCA Official References

- [Architecture General](https://www.afip.gob.ar/ws/documentacion/arquitectura-general.asp)
- [Certificates](https://www.afip.gob.ar/ws/documentacion/certificados.asp)
- [WSAA Documentation](https://www.afip.gob.ar/ws/documentacion/wsaa.asp)
- [Certificate Authorities](https://www.afip.gob.ar/ws/documentacion/autoridades-certificantes.asp)
- [WSFEv1 Documentation](https://www.afip.gob.ar/ws/documentacion/ws-factura-electronica.asp)
- [Service Catalog](https://www.afip.gob.ar/ws/documentacion/catalogo.asp)
- [WSAA Delegate WS](https://www.afip.gob.ar/ws/WSAA/ADMINREL.DelegarWS.pdf)
- [WSAA Technical Spec v1.2.2](https://www.afip.gob.ar/ws/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf)
- [Obtain Certificate](https://www.afip.gob.ar/ws/WSAA/ObtenerCertificado.pdf)
- [WSAA Developer Manual](https://www.afip.gob.ar/ws/WSAA/WSAAmanualDev.pdf)
- [Associate Cert to WS Production](https://www.afip.gob.ar/ws/WSAA/wsaa_asociar_certificado_a_wsn_produccion.pdf)
- [WSASS Enrollment](https://www.afip.gob.ar/ws/WSASS/WSASS_como_adherirse.pdf)
- [WSASS Manual](https://www.afip.gob.ar/ws/WSASS/WSASS_manual.pdf)
- [Developer Manual ARCA COMPG v4.1](https://www.afip.gob.ar/ws/documentacion/manuales/manual-desarrollador-ARCA-COMPG-v4-1.pdf) (highlighted in Notion)

---

## Resources

- **Models**: See `backend/apps/facturacion/models.py`
- **ARCA Client**: See `backend/apps/facturacion/arca/wsfe.py`
- **WSAA Client**: See `backend/apps/facturacion/arca/wsaa.py`
- **Constants**: See `backend/apps/facturacion/constants.py`
- **Validators**: See `backend/apps/facturacion/validators.py`
- **QR Generator**: See `backend/apps/facturacion/qr.py`
- **Tests**: See `backend/tests/facturacion/`

---

*Last updated: 2026-02-07*
*Service: WSFEv1 | Auth: WSAA | Regulation: ARCA (ex-AFIP)*
