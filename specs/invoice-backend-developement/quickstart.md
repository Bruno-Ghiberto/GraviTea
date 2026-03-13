# Quickstart: Facturacion Module Development

**Feature**: 008-facturacion-backend
**Date**: 2026-02-10
**Prerequisites**: Existing GRAVITEA-ERP backend development environment

---

## 1. Install New Dependency

```bash
cd backend
pip install zeep>=4.0
```

Add to `requirements.txt` (or `pyproject.toml`):
```
zeep>=4.0,<5.0
```

**Note**: `lxml` and `cryptography` are already installed as existing project dependencies.

---

## 2. Register the Django App

Add `apps.facturacion` to `INSTALLED_APPS` in `gravitea/settings/base.py`:

```python
INSTALLED_APPS = [
    # ... existing apps ...
    "apps.facturacion",
]
```

---

## 3. Run Migrations

```bash
cd backend
python manage.py makemigrations facturacion
python manage.py migrate
```

This creates all facturacion tables and applies RLS policies.

---

## 4. Wire URL Routing

Add to `gravitea/urls.py` (or the API router):

```python
urlpatterns = [
    # ... existing routes ...
    path("api/v1/facturacion/", include("apps.facturacion.urls")),
]
```

---

## 5. ARCA Homologation Setup

To test against ARCA's homologation (testing) environment:

### 5a. Obtain Test Certificate

1. Log into [ARCA with Clave Fiscal](https://auth.afip.gob.ar/contribuyente_/login.xhtml)
2. Navigate to "Administracion de Certificados Digitales"
3. Generate a CSR with your physical person's CUIT:
   ```bash
   openssl genrsa -out test_private.key 2048
   openssl req -new -key test_private.key \
     -subj "/C=AR/O=TestCompany/CN=TestSystem/serialNumber=CUIT 20123456789" \
     -out test_request.csr
   ```
4. Upload the CSR to WSASS and download the signed certificate (.crt)
5. Associate the certificate with `wsfe` service in the testing environment

### 5b. Create Test Credentials via API

```bash
# POST /api/v1/facturacion/credentials/
curl -X POST http://localhost:8000/api/v1/facturacion/credentials/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "cuit_holder": "20123456789",
    "certificate_pem": "<PEM content>",
    "private_key_pem": "<PEM content>",
    "is_production": false
  }'
```

### 5c. Create Punto de Venta

```bash
# POST /api/v1/facturacion/puntos-de-venta/
curl -X POST http://localhost:8000/api/v1/facturacion/puntos-de-venta/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "numero": 1,
    "tipo": "electronic",
    "description": "PtoVta Principal"
  }'
```

---

## 6. Test Invoice Issuance

```bash
# POST /api/v1/facturacion/comprobantes/emitir/
curl -X POST http://localhost:8000/api/v1/facturacion/comprobantes/emitir/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "punto_venta_numero": 1,
    "cbte_tipo": 6,
    "concepto": 1,
    "doc_tipo": 99,
    "doc_nro": "0",
    "cbte_fch": "20260310",
    "imp_total": "121.00",
    "imp_neto": "100.00",
    "imp_iva": "21.00",
    "imp_trib": "0.00",
    "imp_op_ex": "0.00",
    "imp_tot_conc": "0.00",
    "mon_id": "PES",
    "mon_cotiz": "1.000000",
    "emitter_condicion_iva": 1,
    "receptor_condicion_iva": 5,
    "alic_iva": [
      {"iva_id": 5, "base_imp": "100.00", "importe": "21.00"}
    ]
  }'
```

Expected response (homologation):
```json
{
  "id": "...",
  "cbte_nro": 1,
  "cae": "12345678901234",
  "cae_fch_vto": "2026-03-20",
  "status": "AUTORIZADO",
  "qr_url": "https://www.afip.gob.ar/fe/qr/?p=..."
}
```

---

## 7. Running Tests

```bash
# All facturacion tests
cd backend && pytest tests/facturacion/ -v

# Unit tests only (no ARCA connection needed)
cd backend && pytest tests/facturacion/unit/ -v

# Integration tests (requires ARCA test credentials + network)
cd backend && pytest tests/facturacion/integration/ -m integration -v
```

---

## 8. ARCA Endpoints Reference

| Environment | Service | URL |
|-------------|---------|-----|
| Homologacion | WSAA | `https://wsaahomo.afip.gov.ar/ws/services/LoginCms` |
| Homologacion | WSFEv1 | `https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL` |
| Production | WSAA | `https://wsaa.afip.gov.ar/ws/services/LoginCms` |
| Production | WSFEv1 | `https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL` |

---

## 9. Key Files

| File | Purpose |
|------|---------|
| `apps/facturacion/apps.py` | Django AppConfig |
| `apps/facturacion/constants.py` | CbteTipo, DocTipo, CondicionIVA enums |
| `apps/facturacion/models.py` | All models (7 entities) |
| `apps/facturacion/validators.py` | Amount validation, service dates |
| `apps/facturacion/services.py` | InvoiceService orchestration |
| `apps/facturacion/arca/wsaa.py` | WSAA authentication client |
| `apps/facturacion/arca/wsfe.py` | WSFEv1 SOAP client |
| `apps/facturacion/arca/caea.py` | CAEA offline authorization |
| `apps/facturacion/arca/exceptions.py` | ARCA error hierarchy |
| `apps/facturacion/qr.py` | Fiscal QR code generation |
| `apps/facturacion/metrics.py` | Prometheus ARCA metrics |
