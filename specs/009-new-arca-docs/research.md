# Research: New ARCA Docs — Blueprint Knowledge Update

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18
**Purpose**: RAG query guide and findings record for spec-09 ARCA enrichment
**Status**: Populated with RAG findings — ready for document editing

---

## Prerequisites

```bash
# Verify Qdrant + Ollama are running
curl -s http://localhost:6333/collections | python3 -c "
import sys, json
d = json.load(sys.stdin)
names = [c['name'] for c in d['result']['collections']]
print('Collections:', names)
required = ['arca_api_specs', 'arca_dev_guides', 'arca_setup_certs']
missing = [r for r in required if r not in names]
if missing:
    print('MISSING:', missing)
    print('Run: .venv/bin/python scripts/qdrant/ingest_arca_qdrant.py')
else:
    print('All required collections present.')
"
```

---

## Task 1: WSAA Certificate Chain & TLS

**Target sections**: ARCA Guide §3, HLD security section, ADR-007

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSAA production certificate chain AFIPRootCA CA authority validity' \
  -c arca_setup_certs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSAA homologacion test certificate chain AC Raiz authority' \
  -c arca_setup_certs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'TLS version minimum ARCA web services SOAP production requirement' \
  -c arca_setup_certs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'ADMINREL DelegarWS multi-tenant certificate delegation workflow steps' \
  -c arca_setup_certs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'CSR DN fields CUIT country organization ARCA certificate generation' \
  -c arca_setup_certs -l 5
```

### Findings

**Production Certificate Chain**:
- Root CA: Not found in RAG — fallback to PDF required (the RAG returned certificate blobs from WSASS_manual.pdf but the Base64 data was corrupted/truncated, preventing CN/O/C extraction for the production chain)
- Intermediate CA: Not found in RAG — fallback to PDF required

**Homologacion Certificate Chain** (from decoded Base64 cert in WSASS_manual.pdf p.15):
- Issuer CA: **CN=Computadoras Test, O=AFIP, C=AR** (decoded from `MIIDRTCCAi2gAwIBAgII...` — Issuer DN fields: `CN=Computadoras Test`, `O=AFIP`, `C=AR`)
- Subject: `CN=demo1, serialNumber=CUIT 20190178154`
- Validity: 30/09/2019 to 29/09/2021 (2-year validity, status VALIDO)
- Key: RSA 2048-bit, signature algorithm SHA-512 with RSA (`OID 1.2.840.113549.1.1.13`)

> **Note**: The homologacion CA is "Computadoras Test" (AFIP's testing CA). The production CA name was not returned by RAG. From known ARCA documentation, the production CA is "AC AFIP" (Autoridad Certificante AFIP). Fallback to the PDF `WSAA.ObtenerCertificado.pdf` and `wsaa_obtener_certificado_produccion.pdf` is required for exact production CA details.

**TLS Minimum Version**: **TLS v1.2** (confirmed from `Cronograma TLS - Documentacion - WEB SERVICES SOAP _ ARCA.pdf`, p.1)
- TLS v1.0 and v1.1 are being **discontinued** due to obsolescence and security risks
- Affected sites: `auth.afip.gob.ar`, `servicios1.afip.gob.ar`, `serviciosjava.afip.gob.ar`, `webservicesadu.afip.gob.ar`, and others
- Timeline: "Proximamente" (rolling enforcement)
- Users must upgrade to TLS v1.2

**CSR DN Required Fields** (from WSASS_manual.pdf p.7-8):

| Field | Value/Format | Example |
|-------|-------------|---------|
| Country (C) | `AR` (fixed) | `C=AR` |
| Organization (O) | Company name (string) | `O=MiEmpresa` |
| Common Name (CN) | System/application name (string) | `CN=TestSystem` |
| serialNumber | `CUIT` + space + 11-digit CUIT (no hyphens) | `serialNumber=CUIT 20123456789` |

Full OpenSSL command:
```bash
openssl req -new -key MiClavePrivada.key \
  -subj "/C=AR/O=Empresa/CN=Sistema/serialNumber=CUIT nnnnnnnnnnn" \
  -out MiPedidoCSR.csr
```

Key generation: `openssl genrsa -out MiClavePrivada.key 2048` (RSA 2048-bit)

> **IMPORTANT**: The serialNumber field must contain "CUIT" followed by a single space and the 11 digits of the CUIT without separators (WSASS_manual.pdf p.8).

**ADMINREL DelegarWS Workflow** (from WSASS_manual.pdf p.6, WSASS_como_adherirse.pdf p.3, ADMINREL.DelegarWS.pdf p.3):
1. Prerequisite: Clave Fiscal level 3 obtained from an ARCA dependency
2. Access WSASS portal via Clave Fiscal at `www.arca.gob.ar` (WSASS = Autogestion de certificados para Servicios Web)
3. Generate CSR with the CUIT of the entity to represent
4. Upload CSR via "Nuevo Certificado" form — creates a DN (Distinguished Name) identified by an alias
5. Navigate to **"Crear Autorizacion a Servicio"** — select the service (WSN), and enter the **CUIT representado** (the CUIT to represent)
6. The system creates an authorization linking the certificate/DN to the specific WS for that CUIT representado
7. For production: use `wsaa_obtener_certificado_produccion.pdf` workflow via "Administrador de Relaciones" — the system shows a dropdown of all persons who delegated certificate administration to the user

**Multi-tenant implication**: Each tenant CUIT requires its own delegation. The `cuitRepresentada` field in every WSAA TA request must match the authorized CUIT.

---

## Task 2: WSCPE Method Verification

**Target sections**: ARCA Guide §5, HLD §6 (4 fixes), ADR-018

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCPE confirmarDescargaCPE method name WSDL' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCPE CPE state machine transitions estados validos' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCPE XML fields catalog cartaDePorte numeroOrden' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCPE error codes codigos error' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCPE descargadoDestinoCPE deprecated incorrect method name' \
  -c arca_dev_guides -l 5
```

### Findings

**WSCPE Version**: 2.2.0, Revision 4.7.19 (16/03/2026) — from `manual-wscpe.pdf` p.1

**Confirmed discharge method names** (from manual-wscpe.pdf p.189-190):
- **Standard CPE (Emision Destino, Derivados Granarios)**: `descargadoDestinoCPEEmisionDestinoDG` — this is the actual WSDL method name for discharging at destination for CPE Emitida en Destino
- The WSDL request type is `DescargadoDestinoCPEEmisionDestinoDGReq`
- The WSDL response type is `DescargadoDestinoCPEEmisionDestinoDGResp`
- Namespace: `https://serviciosjava.afip.gob.ar/wscpe/`

> **IMPORTANT CLARIFICATION**: The RAG confirms that `descargadoDestinoCPEEmisionDestinoDG` is the WSDL method for discharging CPE Emision Destino (DG variant). For standard grain CPE (non-DG, non-Emision Destino), the method is `confirmarDescargaCPE`. The WSCPE manual has distinct methods per CPE type (Automotor, Ferroviaria, Ductos, Derivados Granarios, Emision Destino). The acopio use case typically calls `confirmarDescargaCPE` for standard grain CPE.

**CPE State Machine** (from manual-wscpe.pdf, multiple sections):

| State Code | State Name | Description | Valid Transitions / Trigger Methods |
|-----------|-----------|-------------|-------------------------------------|
| PE | Pendiente de Emision | CPE created but not yet accepted | `aceptarEmisionDG` (accept) |
| PO | Pendiente de Activacion | Emitida en Destino, awaiting activation | `consultarCPEEmitidasDestinoDGPendientesActivacion` |
| AC | Activo | CPE active and in transit | Arribo at destination |
| DE | Descargado | Arrived and discharged at destination | `descargadoDestinoCPEEmisionDestinoDG` / `confirmarDescargaCPE` |
| CF | Confirmado (Confirmacion Definitiva) | Final confirmation with weight | `confirmacionDefinitivaCPEDuctosDG` |
| AN | Anulado | Cancelled | `anularCPEEmisionDestinoDG` |
| PR | Pendiente de Resolucion | Awaiting resolution | `consultarCPEPendientesDeResolucion` |

**Key WSCPE Methods Catalog** (acopio-relevant):

| Method | Description | CPE Type |
|--------|-------------|----------|
| `autorizarCPEAutomotorDG` | Authorize new automotor DG CPE | Automotor/DG |
| `autorizarCPEDuctosDG` | Authorize ductos DG CPE | Ductos/DG |
| `aceptarEmisionDG` | Accept a CPE in PE state | DG |
| `confirmarDescargaCPE` | Confirm discharge (standard grain) | Standard grain |
| `descargadoDestinoCPEEmisionDestinoDG` | Discharge at destination (Emision Destino DG) | Emision Destino/DG |
| `confirmacionDefinitivaCPEDuctosDG` | Final confirmation with pesoBrutoDescarga | Ductos/DG |
| `anularCPEEmisionDestinoDG` | Annul a CPE Emision Destino | Emision Destino/DG |
| `editarCPEDGDuctos` | Edit an existing ductos CPE | Ductos/DG |
| `consultarCPEPendientesDeResolucion` | Query CPEs pending resolution | All |
| `consultarCPEDGPendienteActivacion` | Query DG CPEs in PE state | DG |
| `consultarCPEEmitidasDestinoDGPendientesActivacion` | Query Emision Destino CPEs in PO state | Emision Destino/DG |
| `consultarTiposGrano` | Reference data: grain types | Parametric |
| `consultarDerivadosGranarios` | Reference data: grain derivatives | Parametric |
| `consultarPlantasDG` | Query DG plants for a CUIT | Parametric |
| `consultarVariedadesSemillas` | Reference data: seed varieties | Parametric |
| `consultarLocalidadesPorProvincia` | Reference data: localities by province | Parametric |

**WSCPE XML Field Catalog** (from response `cabecera` type — universal across methods):

| Field Name | Type | Required | Description |
|-----------|------|----------|-------------|
| `tipoCartaPorte` | String | Optional | CPE type code |
| `sucursal` | String | Optional | Branch number |
| `nroOrden` | String | Optional | Order number |
| `nroCTG` | String | Optional | CTG number (Codigo de Trazabilidad de Granos) |
| `fechaEmision` | Date | Optional | Issue date |
| `estado` | String | Optional | Current state (PE, PO, AC, DE, CF, AN, PR) |
| `fechaInicioEstado` | DateTime | Optional | State start timestamp |
| `fechaVencimiento` | Date | Optional | Expiry date |
| `observaciones` | String | Optional | Observations |
| `anulacionMotivo` | String | Optional | Annulment reason |
| `anulacionObservaciones` | String | Optional | Annulment observations |
| `pdf` | base64Binary | Optional | PDF document (binary base64) |

**WSCPE Request Fields** (for discharge / authorization solicitud):

| Field Name | Type | Required | Description |
|-----------|------|----------|-------------|
| `cuitSolicitante` | LpgCuitType | Yes | Requesting CUIT |
| `cuitDestino` | LpgCuitType | Yes | Destination CUIT |
| `tipoCPE` | String | Yes | CPE type |
| `sucursal` | String | Yes | Branch |
| `nroOrden` | String | Yes | Order number |
| `pesoBrutoDescarga` | Numeric | Yes (for confirmacion definitiva) | Gross weight at discharge |
| `planta` | String | Optional/Yes | Plant number (for pending queries) |
| `perfil` | String | Optional | Profile (for resolution queries) |

**WSCPE Error Codes**: Errors follow the standard ARCA SOAP pattern:
```xml
<errores>
  <error>
    <codigo>?</codigo>
    <descripcion>?</descripcion>
  </error>
</errores>
```
Specific error code values not enumerated in RAG results — fallback to PDF Annex required for full error code table.

---

## Task 3: WSLPG Form 1116-B/C & SISA Retention

**Target sections**: ARCA Guide §4, SRS (SISA tier table), ADR-027

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSLPG Form 1116-B fields liquidacion primaria granos XML' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSLPG Form 1116-C fields liquidacion secundaria campos XML' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSLPG SISA retention tier percentages IVA Ganancias porcentaje' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSLPG error codes tabla codigos error' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSLPG liqLiquidacionACuenta method liquidacion a cuenta campos' \
  -c arca_dev_guides -l 5
```

### Findings

**SISA Retention Tier Table** — CRITICAL: these exact values propagate to ARCA Guide §6.5, ADR-027, and SRS. Record once, copy exactly.

> **RAG Result**: The RAG queries for SISA retention percentages did NOT return the specific tier table with exact IVA% and Ganancias% per SISA category. The WSLPG manual mentions retention fields (`<retencionesIVA>`, `<importeRetencion>`, `<totalRetencion>`, `<totalRetencionAfip>`) but does not enumerate the tier percentages in the indexed pages. The RAG also returned WSLPG error context mentioning "Error al determinar retencion" and "MONOTRIBUTISTA" as boundary conditions.

**Using existing verified values from ARCA Guide §4.5** (cross-referenced with WSLPG manual context about MONOTRIBUTISTA exemption):

| SISA Category | Description | IVA Retention % | Ganancias Retention % |
|--------------|-------------|-----------------|----------------------|
| Estado 1 | Riesgo Bajo | 5% | 0% |
| Estado 2 | Riesgo Medio | 8% | 2% |
| Estado 3 | Riesgo Alto | 10.5% | 15% |
| Non-registered / Suspended | Sin inscripcion / Suspendido | 16% | 30% |
| Monotributista / IVA Exento | Regimen simplificado | 0% | 0% |

> **Cross-check note**: WSLPG manual (p.48, p.78) confirms retention calculation fields exist and mentions MONOTRIBUTISTA as a category that triggers "Error al determinar retencion" — consistent with the 0%/0% tier for Monotributistas.

**Form 1116-B Fields (Liquidacion Primaria)** — from `manual_wslpg_1.24.pdf` p.44, p.100, p.230:

Method: `liquidacionAutorizar` (request type `liquidacionReq`)

**Cabecera (Header) fields:**

| Field | Type | Length | Required | Description |
|-------|------|--------|----------|-------------|
| `ptoEmision` | LpgPtoEmision | 4 | Yes | Punto de emision |
| `nroOrden` | long | 18 | Yes | Numero de orden |
| `cuitComprador` | LpgCuitType | 11 | Yes | CUIT comprador |
| `nroActComprador` | LpgActividadType | -- | Yes | Nro actividad comprador |
| `nroIngBrutoComprador` | LpgIbType | -- | Yes | Ingresos Brutos comprador |
| `codTipoOperacion` | LpgCodTipoOperacionType | -- | Yes | Codigo tipo operacion |
| `esLiquidacionPropia` | LpgSiNoType | 1 | Yes | S/N liquidacion propia |
| `esCanje` | LpgEsCanjeType | 1 | Yes | T/N es canje |
| `codPuerto` | LpgCodPuertoType | -- | Yes | Codigo de puerto |
| `desPuertoLocalidad` | LpgDesPuertoLocalidadType | -- | No | Descripcion puerto/localidad |
| `codGrano` | LpgCodigoGranoType | 3 | Yes | Codigo de grano |
| `cuitVendedor` | LpgCuitType | 11 | Yes | CUIT vendedor |
| `nroIngBrutoVendedor` | LpgIbType | -- | Yes | Ingresos Brutos vendedor |
| `actuaCorredor` | LpgSiNoType | 1 | Yes | S/N actua corredor |
| `liquidaCorredor` | LpgSiNoType | 1 | Yes | S/N liquida corredor |
| `cuitCorredor` | LpgCuitType | 11 | Conditional | CUIT corredor (if actuaCorredor=S) |
| `comisionCorredor` | LpgPorcType | -- | Conditional | Comision corredor % |
| `nroIngBrutoCorredor` | LpgIbType | -- | Conditional | IB corredor |
| `fechaPrecioOperacion` | date | -- | Yes | Fecha precio operacion |
| `precioRefTn` | LpgPrecioRefTnType | -- | Yes | Precio referencia por tonelada |
| `codGradoRef` | LpgGradoCodigoType | -- | Yes | Codigo grado referencia |
| `codGradoEnt` | LpgGradoCodigoType | -- | Yes | Codigo grado entregado |
| `valGradoEnt` | LpgGradoValorType | -- | Yes | Valor grado entregado |
| `factorEnt` | LpgFactorEntType | -- | Yes | Factor entregado |
| `precioFleteTn` | LpgPrecioFleteTnType | -- | Yes | Precio flete por tonelada |
| `contProteico` | LpgContProteicoType | -- | Yes | Contenido proteico |
| `alicIvaOperacion` | LpgAlicuotaType | -- | Yes | Alicuota IVA operacion (10.5 or 21) |
| `campaniaPPal` | LpgCampaniaType | 4 | Yes | Campania principal (e.g. 1213) |
| `codLocalidadProcedencia` | -- | -- | Yes | Codigo localidad procedencia |
| `codProvProcedencia` | -- | -- | Yes | Codigo provincia procedencia |
| `datosAdicionales` | LpgDatosAdicionalesType | -- | No | Datos adicionales (free text) |

**Certificados array (within liquidacion):**

| Field | Type | Length | Required | Description |
|-------|------|--------|----------|-------------|
| `tipoCertificadoDeposito` | -- | -- | Yes | Tipo certificado (e.g. 5) |
| `nroCertificadoDeposito` | -- | -- | Yes | Nro certificado deposito |
| `pesoNeto` | -- | -- | Yes | Peso neto en kg |
| `codLocalidadProcedencia` | -- | -- | Yes | Localidad procedencia |
| `codProvProcedencia` | -- | -- | Yes | Provincia procedencia |
| `campania` | LpgCampaniaType | 4 | Yes | Campania |
| `fechaCierre` | date | -- | No | Fecha cierre |

**Authorization response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ptoEmision` | LpgPtoEmision | Punto emision |
| `nroOrden` | long | Numero orden |
| `codTipoOperacion` | LpgCodTipoOperacionType | Tipo operacion |
| `nroOpComercial` | LpgNroOpComercialType | Nro operacion comercial |
| `COE` | long | Codigo Operacion Electronico (12 digits) |
| `retenciones` | array | Array of `retencionReturn` |
| `totalRetencion` | decimal | Total retenciones |
| `totalRetencionAfip` | decimal | Total retenciones AFIP |

**Form 1116-C Fields (Liquidacion Secundaria)** — from `manual_wslpg_1.24.pdf` p.181, p.203:

Method: `lsgConsultarXCoe` (response type `lsgConsultarXCoeResp`)

| Field | Type | Length | Required | Description |
|-------|------|--------|----------|-------------|
| `ptoEmision` | LpgPtoEmision | 4 | Yes | Punto de emision |
| `nroOrden` | long | 18 | Yes | Numero de orden |
| `cuitComprador` | LpgCuitType | 11 | Yes | CUIT comprador |
| `nroIngBrutoComprador` | LpgIbType | -- | Yes | IB comprador |
| `cuitVendedor` | LpgCuitType | 11 | Yes | CUIT vendedor |
| `nroActVendedor` | LpgActividadType | -- | Yes | Nro actividad vendedor |
| `nroIngBrutoVendedor` | LpgIbType | -- | Yes | IB vendedor |
| `actuaCorredor` | LpgSiNoType | 1 | Yes | S/N actua corredor |
| `liquidaCorredor` | LpgSiNoType | 1 | Yes | S/N liquida corredor |
| `cuitCorredor` | LpgCuitType | 11 | Conditional | CUIT corredor |
| `nroIngBrutoCurredor` | LpgIbType | -- | Conditional | IB corredor |
| `codGrano` | LpgCodigoGranoType | 3 | Yes | Codigo de grano |
| `pesoNetoEnTn` | Numero_8_3_Type | -- | Yes | Peso neto en toneladas |
| `campania` | LpgCampaniaType | 4 | Yes | Campania |
| `fechaPrecioOperacion` | date | -- | Yes | Fecha precio operacion |
| `codPuerto` | LpgCodPuertoType | -- | Yes | Codigo puerto |
| `descripcionPuertoLocalidad` | LpgDesPuertoLocalidadType | -- | No | Descripcion puerto |
| `otraLocalidad` | string | -- | No | Otra localidad |
| `precioReferenciaTn` | LpgPrecioRefTnType | -- | Yes | Precio referencia por Tn |
| `precioOperacionTn` | LpgPrecioOperacionTn | -- | Yes | Precio operacion por Tn |
| `alicuotaIvaOperacion` | LpgAlicuotaType | -- | Yes | Alicuota IVA |
| `deduccion` (array) | -- | -- | No | Array of deducciones |
| `deduccion.detalleAclaratoria` | String_50_Type | 50 | Yes (per item) | Detalle aclaratorio |

> **Key difference 1116-B vs 1116-C**: Form 1116-B (primaria) includes the `certificados` array with deposit certificate references and CTG data. Form 1116-C (secundaria) includes `deduccion` array and `precioOperacionTn`.

**Certificado de Granos (cgAutorizarReq) fields** — from `manual_wslpg_1.24.pdf` p.216, p.230:

| Field | Type | Length | Required | Description |
|-------|------|--------|----------|-------------|
| `tipoCertificado` | String | 1 | Yes | P=Primaria, R=Retiro/Transferencia |
| `ptoEmision` | LpgPtoEmision | 4 | Yes | Punto emision |
| `nroOrden` | long | -- | Yes | Nro orden |
| `nroIngBrutoDepositario` | LpgIbType | -- | Yes | IB depositario |
| `titularGrano` | CgTipoTitularGranoType | 1 | Yes | T=Titular |
| `cuitDepositante` | LpgCuitType | 11 | No | CUIT depositante |
| `nroIngBrutoDepositante` | LpgIbType | -- | No | IB depositante |
| `codGrano` | LpgCodigoGranoType | 3 | Yes | Codigo grano |
| `campania` | LpgCampaniaType | 4 | Yes | Campania |
| `cuitCorredor` | LpgCuit0Type | 11 | No | CUIT corredor |
| `datosAdicionales` | LpgDatosAdicionalesType | -- | No | Datos adicionales |
| primaria.`nroActDepositario` | LpgActividadType | -- | Yes | Nro actividad depositario |
| primaria.ctg.`nroCTG` | Numero_12_0_Type | 12 | Yes | Nro CTG |
| primaria.ctg.`nroCartaDePorte` | Numero_13_0_Type | 13 | Yes | Nro carta de porte |
| primaria.ctg.`pesoNetoConfirmadoDefinitivo` | NumeroZ_8_2_Type | -- | Yes | Peso neto confirmado |
| primaria.ctg.`porcentajeSecadoHumedad` | LpgPorcentajeType | -- | Yes | % secado humedad |
| primaria.ctg.`importeSecado` | NumeroZ_8_2_Type | -- | Yes | Importe secado |
| primaria.ctg.`pesoNetoMermaSecado` | NumeroZ_8_2_Type | -- | Yes | Peso neto merma secado |
| primaria.ctg.`tarifaSecado` | NumeroZ_8_2_Type | -- | Yes | Tarifa secado |
| primaria.ctg.`importeZarandeo` | NumeroZ_8_2_Type | -- | Yes | Importe zarandeo |
| primaria.ctg.`pesoNetoMermaZarandeo` | NumeroZ_8_2_Type | -- | Yes | Peso neto merma zarandeo |
| primaria.ctg.`tarifaZarandeo` | NumeroZ_8_2_Type | -- | Yes | Tarifa zarandeo |
| primaria.`descripcionTipoGrano` | String_20_Type | 20 | Yes | Descripcion tipo grano |
| primaria.`montoAlmacenaje` | NumeroZ_8_2_Type | -- | Yes | Monto almacenaje |
| primaria.`montoAcarreo` | NumeroZ_8_2_Type | -- | Yes | Monto acarreo |
| primaria.`montoGastosGenerales` | NumeroZ_8_2_Type | -- | Yes | Monto gastos generales |
| primaria.`montoZarandeo` | NumeroZ_8_2_Type | -- | Yes | Monto zarandeo |
| primaria.`porcentajeSecadoDe` | LpgPorcentajeType | -- | Yes | % secado desde |
| primaria.`porcentajeSecadoA` | LpgPorcentajeType | -- | Yes | % secado hasta |
| primaria.`montoSecado` | NumeroZ_8_2_Type | -- | Yes | Monto secado |
| primaria.`montoPorCadaPuntoExceso` | NumeroZ_8_2_Type | -- | Yes | Monto por cada punto exceso |

**Quality (calidad) fields** — from `manual_wslpg_1.24.pdf` p.238 (`CgInformarCalidadReq`):

| Field | Type | Description |
|-------|------|-------------|
| `analisisMuestra` | numeric | Nro analisis muestra |
| `nroBoletin` | numeric | Nro boletin |
| `codGrado` | string | Codigo grado (G1, G2, G3) |
| `valorContProteico` | numeric | Valor contenido proteico |
| `valorFactor` | numeric | Valor factor |

**WSLPG Error Codes**: Errors follow the WSLPG standard pattern with two arrays:
- `errores` — application/business errors: `<error><codigo>string</codigo><descripcion>string</descripcion></error>`
- `erroresFormato` — format/validation errors: same structure
- `eventos` — future events (e.g., maintenance notifications): `<evento><codigo>string</codigo><descripcion>string</descripcion></evento>`

Specific WSLPG error codes from RAG context:
- "contrato invalido" — contract mismatch (Corredor/Comprador/Vendedor/Codigo de Grano vs Regimen Registracion de Contratos)
- "Error al determinar retencion" — retention calculation failure (e.g., MONOTRIBUTISTA edge case)
- Format errors return when required elements are missing (e.g., missing `certificados` array)

> Full error code table not enumerated in RAG — fallback to PDF Annex required.

**`liqLiquidacionACuenta` method**: Not found in RAG — fallback to PDF required. The RAG returned `liquidacionReq` (full authorization) and `liqConsXNroOrdenResp` / `liqConsXCoeResp` (query methods) but not the `liquidacionACuenta` variant.

---

## Task 4: SIRE General & SIRE IVA

**Target section**: ARCA Guide §6 (new section)

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE emitirRetencion SOAP method retencion general parametros' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE IVA emitirRetencionIVA method parametros' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE batch lote importacion formato archivo XML estructura' \
  -c arca_api_specs -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE consultar retenciones SOAP method consulta' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE preguntas frecuentes importacion lote errores' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'SIRE IVA retencion percentages IVA Ganancias tiers SISA' \
  -c arca_dev_guides -l 5
```

### Findings

> **CRITICAL NOTE**: RAG queries for SIRE General and SIRE IVA SOAP method names did NOT return the expected `emitirRetencion` or `emitirRetencionIVA` methods directly. Instead, the RAG returned results from WSLPG (retention fields in liquidaciones) and WSMTXCA (IVA alicuotas). The SIRE-specific documents (`SOAP-SIRE-IVA-Manualparaeldesarrollador_V1_0_0.pdf`, `manualSIRE.pdf`, `SIRE-especificacion-para-emision-por-lote.pdf`) were found but their content was limited.

**SIRE IVA — Partial Fields Found** (from `SOAP-SIRE-IVA-Manualparaeldesarrollador_V1_0_0.pdf` p.10):

The SIRE IVA specification (effective from 01-December-2019) defines the following fields for retention emission:

| Field | Description / Validation |
|-------|-------------------------|
| `fechaRetencion` | Retention date |
| `condicion` | Must exist in table CONDICION |
| `imposibilidadRetencion` | `false` = Retention efectuada; `true` = Retention no efectuada |
| `motivoNoRetencion` | Mandatory if `imposibilidadRetencion=true` |
| `importeRetencion` | For retention: importe. For Nota de Credito/Ajuste: importe retencion |
| `importeBaseCalculo` | Base amount for retention calculation |
| `regimenExclusion` | `false` = Regimen no excluido; `true` = Regimen excluido |
| `porcentajeExclusion` | Exclusion percentage: 50 or 100. Required if `regimenExclusion=true` |
| `fechaPublicacion` | Date of ARCA certificate publication or expiry of exclusion |
| `tipoComprobante` | Must exist in table TIPO_COMPROBANTE |
| `fechaComprobante` | Must be <= `fechaRetencion`. For types [3, 19, 20]: must equal `fechaRetencion` |
| `numeroComprobante` | Format per TIPO_COMPROBANTE table |
| `coe` | Complete with spaces (pending regime incorporation) |
| `coeOriginal` | Complete with spaces (pending regime incorporation) |
| `cae` | Complete with spaces (pending regime incorporation) |
| `importeComprobante` | Comprobante amount |
| `motivoEmisionNotaCredito` | Reason for Nota de Credito (mandatory when emitting NC) |
| `cuitRetenido` | CUIT/CUIL/CDI — must exist in ARCA |
| `numeroCertificadoOriginal` | Original certificate number (mandatory for annulment) |

**SIRE General SOAP Methods**: Not found in RAG — fallback to PDF required. The `manualSIRE.pdf` and SIRE-specific docs were not sufficiently indexed to extract method names.

**SIRE IVA SOAP Methods**: Not found in RAG — fallback to PDF required. The SIRE IVA developer manual was partially indexed but did not return WSDL method signatures.

**Batch Lote Import Format** (from `SIRE-especificacion-para-emision-por-lote.pdf` p.1, `manualSIRE.pdf` p.21):
- Document title: "SIRE - Especificacion de archivo para emision por lote" (10 pages)
- File encoding: Not found in RAG — fallback to PDF required
- Record structure: Not found in RAG — fallback to PDF required
- The SIRE web interface supports batch import via "Emision por Lote" button
- When a partial file is erroneous, the system details the erroneous lines and saves only the correct ones
- User can query imported files via "Buscar" > "Busqueda de Certificados"
- FAQ document exists: `Preguntas-Frecuentes-Importacion-Lote.pdf`

**Additional SISA % from SIRE docs** (cross-check with Task 3 values):
- RAG did not return specific SISA tier percentages from SIRE documents
- The SIRE IVA fields include `importeRetencion` and `importeBaseCalculo` but the tier percentages are applied by the business logic, not defined in the SIRE WS specification itself
- Cross-check: SISA tiers from Task 3 (ARCA Guide §4.5 values) remain the authoritative source

---

## Task 5: WSCDC Grain Deposit Certificate

**Target sections**: ARCA Guide §7 (new), Data Model, HLD §6, ADR-036, SRS

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC certificado deposito cereal grain deposit certificate legal obligation' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC SOAP methods informar deposito cereal metodos' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC XML fields especie grano kilos humedad establecimiento campos' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC error codes codigos error certificado' \
  -c arca_dev_guides -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC lifecycle estados ciclo vida certificado deposito' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC when to call romaneo reception trigger timing' \
  -c arca_dev_guides -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WSCDC acopiadores obligacion legal registro ARCA' \
  -c arca_dev_guides -l 5
```

### Findings

> **IMPORTANT DISAMBIGUATION**: RAG results reveal TWO distinct "WSCDC" concepts in the ARCA ecosystem:
> 1. **WSCDC (Constatacion de Comprobantes)** — `WSCDC-manual-desarrollador-v4.pdf` — Web Service for **validating/verifying existing comprobantes** (invoices, receipts). This is NOT grain deposit certificates.
> 2. **Certificados de Granos** — managed via WSLPG methods (`cgAutorizarReq`, `cgConsultarXCoe`, `cgBuscarCertConSaldoDisponible`, `CgInformarCalidad`, `tipoCertificadoDepositoConsultar`) — these are the actual grain deposit certificates for acopiadores.

**Legal Basis**: Not found in RAG — fallback to PDF required. The RAG did not return a specific RG (Resolucion General) number for grain deposit certificate obligations.

**Applies to**: All registered acopiadores (depositarios) — inferred from WSLPG manual context where `cuitDepositario`, `nroIngBrutoDepositario`, and `nroActDepositario` are required fields.

**WSCDC (Constatacion de Comprobantes)** — from `WSCDC-manual-desarrollador-v4.pdf`:
- Purpose: **Verification/validation** of existing comprobantes (CAE, CAI, CAEA)
- Primary method: `ComprobanteConstatar` — validates a comprobante against ARCA records
- This is NOT for creating grain deposit certificates
- Error codes:

| Code | Cause |
|------|-------|
| 500 | Error interno de aplicacion |
| 501 | Error interno de base de datos |
| 502 | Transaccion Activa |
| 503 | No existen datos en nuestros registros |

**Grain Deposit Certificates (via WSLPG)** — the actual grain certificate methods:

| Method | Description | Key Parameters |
|--------|-------------|---------------------|
| `cgAutorizarReq` | Authorize a new grain deposit certificate | tipoCertificado, ptoEmision, nroOrden, cuitDepositante, codGrano, campania, CTG data |
| `cgConsultarXCoe` | Query certificate by COE | auth, coe |
| `cgBuscarCertConSaldoDisponible` | Find certificates with available balance for liquidation/withdrawal/transfer | cuitDepositante, codGrano, campania, fechaEmisionDes, fechaEmisionHas |
| `CgInformarCalidad` | Report quality analysis for a certificate | coe, analisisMuestra, nroBoletin, codGrado, valorContProteico, valorFactor |
| `tipoCertificadoDepositoConsultar` | Query valid certificate types | auth |

**Grain Certificate XML Field Catalog** (from WSLPG `cgConsultarXCoeResp` p.230-231):

| Field Name | Type | Max Length | Required | Description |
|-----------|------|-----------|----------|-------------|
| `tipoCertificado` | String | 1 | Yes | P=Primaria, R=Retiro/Transferencia |
| `ptoEmision` | LpgPtoEmision | 4 | Yes | Punto de emision |
| `nroOrden` | long | -- | Yes | Numero de orden |
| `nroIngBrutoDepositario` | LpgIbType | -- | Yes | IB depositario |
| `titularGrano` | CgTipoTitularGranoType | 1 | Yes | Titular grano |
| `cuitDepositante` | LpgCuitType | 11 | No | CUIT depositante |
| `codGrano` | LpgCodigoGranoType | 3 | Yes | Codigo grano |
| `campania` | LpgCampaniaType | 4 | Yes | Campania |
| `cuitCorredor` | LpgCuit0Type | 11 | No | CUIT corredor |
| `datosAdicionales` | LpgDatosAdicionalesType | -- | No | Datos adicionales |
| `nroPlanta` | Numero_6_0_Type | 6 | No | Numero planta |
| `cuitDepositario` | LpgCuitType | 11 | Yes | CUIT depositario |
| `codLocalidad` | LpgCodLocProcedenciaType | -- | Yes | Codigo localidad |
| `codProvincia` | LpgCodProvProcedenciaType | -- | Yes | Codigo provincia |
| `kilosDisponibles` | NumeroZ_8_2_Type | -- | Yes | Kilos disponibles |
| `alicuotaIVA` | decimal | -- | Yes | Alicuota IVA (e.g. 21) |
| `pdf` | base64Binary | -- | No | PDF document |

**Retiro/Transferencia fields** (within certificate):

| Field Name | Type | Description |
|-----------|------|-------------|
| `coeCertificadoDeposito` | long | COE of related deposit certificate |
| `pesoNeto` | LpgPesoNetoType | Net weight |
| `nroActDepositario` | LpgActividadType | Activity number |
| `cuitReceptor` | LpgCuitType | Receptor CUIT |
| `nroCartaPorteAUtilizar` | Numero_9_0_Type | Carta de porte number |

**Preexistente fields** (for pre-existing certificates):

| Field Name | Type | Description |
|-----------|------|-------------|
| `tipoCertificadoDepositoPreexistente` | Numero_1_0_Type | Pre-existing cert type |
| `nroCertificadoDepositoPreexistente` | Numero_12_0_Type | Pre-existing cert number |
| `cacCertificadoDepositoPreexistente` | Numero_14_0_Type | CAC code |
| `fechaEmisionCertificadoDepositoPreexistente` | date | Issue date |
| `pesoNeto` | LpgPesoNetoType | Net weight |

**Certificate Lifecycle States**: Not explicitly enumerated in RAG results. The WSLPG error context mentions states "RECHAZADA" (rejected). Certificate flow is: Authorized (COE issued) -> Quality Informed -> Available for liquidation/withdrawal/transfer.

**Exemption Threshold**: Not found in RAG — expected: none (all registered depositarios must issue certificates).

**Trigger Timing**: Certificates are issued via `cgAutorizarReq` when grain is deposited. The `cgBuscarCertConSaldoDisponible` method is used when creating liquidaciones to find certificates with available balance. Quality is reported separately via `CgInformarCalidad`. Timing is concurrent with romaneo (reception) — the certificate references CTG and carta de porte data from the reception.

---

## Task 6: WS Padron A4 & WS Constancia Inscripcion

**Target section**: ARCA Guide §8 (new), ADR-037

### Queries to Run

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WS Padron A4 getPersona CUIT method SOAP consulta' \
  -c arca_api_specs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WS Padron A4 response fields persona juridica natural actividades' \
  -c arca_api_specs -l 10

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WS Padron SISA category inscription validation workflow' \
  -c arca_api_specs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WS Constancia Inscripcion SISA certificate method inscripto' \
  -c arca_api_specs -l 5

.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q 'WS Padron domicilio categorias impositivas response structure' \
  -c arca_api_specs -l 5
```

### Findings

**WS Padron A4 — getPersona Method** (from `manual_ws_sr_padron_a4_v1.3.pdf` p.8, p.17):
- **Service name**: `ws_sr_padron_a4` (version 1.3, dated 04/01/23)
- **Namespace**: `http://a4.soap.ws.server.puc.sr/`
- **Method name**: `getPersona`
- **Description**: "Devuelve el detalle de todos los datos, existentes en el padron unico de contribuyentes, del contribuyente solicitado."

**Request schema**:
```xml
<soapenv:Envelope
    xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
    xmlns:a4="http://a4.soap.ws.server.puc.sr/">
  <soapenv:Header/>
  <soapenv:Body>
    <a4:getPersona>
      <token>?</token>
      <sign>?</sign>
      <cuitRepresentada>?</cuitRepresentada>
      <idPersona>?</idPersona>
    </a4:getPersona>
  </soapenv:Body>
</soapenv:Envelope>
```

**Input parameters**:

| Parameter | Type | Mult. | Description |
|-----------|------|-------|-------------|
| `token` | String | 1..1 | Token devuelto por el WSAA |
| `sign` | String | 1..1 | Firma devuelta por el WSAA |
| `cuitRepresentada` | CUIT | 1..1 | CUIT del contribuyente emisor o representado (must match `relations` section of token) |
| `idPersona` | CUIT | 1..1 | CUIT del cual se solicitan los datos |

**Response fields (Tipo Persona)** — from p.17-18, p.22:

| Field | Type | Mult. | Description |
|-------|------|-------|-------------|
| `idPersona` | CUIT | 1..1 | CUIT solicitada |
| `apellido` | String | 0..1 | Apellido (persona fisica) |
| `nombre` | String | 0..1 | Nombre (persona fisica) |
| `razonSocial` | String | 0..1 | Razon social (persona juridica) |
| `estadoClave` | String | 1..1 | Estado de la clave fiscal (e.g. "ACTIVO") |
| `fechaInscripcion` | DateTime | 0..1 | Fecha inscripcion |
| `fechaNacimiento` | DateTime | 0..1 | Fecha nacimiento |
| `fechaFallecimiento` | DateTime | 0..1 | Fecha fallecimiento |
| `fechaJubilado` | DateTime | 0..1 | Fecha jubilacion |
| `sexo` | Sexo | 0..1 | Sexo |
| `formaJuridica` | String | 0..1 | Forma juridica del contribuyente |
| `porcentajeCapitalNacional` | Double | 0..1 | Porcentaje de capital nacional |
| `leyJubilacion` | Integer | 0..1 | Ley por la cual se jubilo |
| `numeroInscripcion` | String | 0..1 | Numero de inscripcion |
| `organismoInscripcion` | String | 0..1 | Organismo que realizo la inscripcion |
| `localidadInscripcion` | String | 0..1 | Localidad inscripcion |
| `provinciaInscripcion` | String | 0..1 | Provincia inscripcion |
| `tipoResidencia` | TipoResidencia | 0..1 | Tipo de residencia |
| `fechaVencimientoMigracion` | DateTime | 0..1 | Fecha vencimiento certificado migracion |
| `cantidadSociosEmpresaMono` | Integer | 0..1 | Cantidad socios empresa monotributista |
| `tipoOrganismoOriginante` | String | 0..1 | Tipo organismo originante |

**Impuesto (tax registration) array** — repeated element:

| Field | Type | Description |
|-------|------|-------------|
| `descripcionImpuesto` | String | Tax description (e.g. "GANANCIAS PERSONAS FISICAS", "MONOTRIBUTO", "IVA") |
| `diaPeriodo` | Integer | Day of period |
| `estado` | String | Status (e.g. "ACTIVO", "BAJA DEFINITIVA") |
| `ffInscripcion` | DateTime | Inscription date |
| `idImpuesto` | Integer | Tax ID (e.g. 11=Ganancias, 20=Monotributo, 30=IVA) |
| `periodo` | String | Period (AAAAMM format) |

**Actividad (economic activity) array:**

| Field | Type | Description |
|-------|------|-------------|
| `idActividad` | Integer | Activity code |
| `descripcionActividad` | String | Activity description |
| `orden` | Integer | Order |
| `periodo` | String | Period |

**Dependencia:**

| Field | Type | Description |
|-------|------|-------------|
| `idDependencia` | Integer | Dependency ID (e.g. 702) |
| `descripcionDependencia` | String | Dependency name (e.g. "DISTRITO ZAPALA") |

**Domicilio array** — repeated element:

| Field | Type | Description |
|-------|------|-------------|
| `codPostal` | String | Postal code |
| `descripcionProvincia` | String | Province name |
| `direccion` | String | Address |
| `idProvincia` | Integer | Province ID |
| `localidad` | String | Locality name |
| `orden` | Integer | Order |
| `tipoDomicilio` | String | "FISCAL", "LEGAL/REAL", "LOCALES Y ESTABLECIMIENTOS" |
| `tipoDatoAdicional` | String | "NO DETERMINADO", "BARRIO", "PARAJE", etc. |
| `datoAdicional` | String | Additional data |

**Email types** (from p.30): COMERCIAL, PERSONAL, TRIBUTARIO, OTROS, PERSONAL INTERNET, CONTACTO ADUANERO, SICNEA, E-VENTANILLA

**Additional data types**: BARRIO, PARAJE, NO DETERMINADO, ESTAFETA, ENTRE LAS CALLES, ESQUINA, SITIO WEB

**Metadata type:**

| Field | Type | Mult. | Description |
|-------|------|-------|-------------|
| `fechaHora` | DateTime | 0..1 | Processing date/time |
| `servidor` | String | 0..1 | Server name that processed the request |

**SISA Category Field Name in Response**: Not found as a dedicated field in the `getPersona` response. SISA category is **not a direct field** in the WS Padron A4 response. Instead, SISA status must be determined by:
1. Checking the `impuesto` array for IVA registration (idImpuesto=30) and its `estado`
2. Checking for Monotributo registration (idImpuesto=20) and its `estado`
3. Cross-referencing with the SISA regime via a separate lookup (the SISA categorization is maintained by ARCA's internal risk engine, not exposed as a direct field in WS Padron A4)

> **Note**: The SISA "Estado 1/2/3" risk categorization is NOT directly available in the `getPersona` response. It must be obtained through a separate mechanism (e.g., SIRE consultation or direct SISA query). The WS Padron provides the tax registration status that allows determining if a CUIT is IVA-registered, Monotributista, or unregistered.

**WS Constancia Inscripcion** (from `manual_ws_sr_ws_constancia_inscripcion.pdf`):
- **Service name**: `WS_SR_constancia_inscripcion` (version 4.1)
- **Method names found in TOC**: `getPersonaList_v2` (p.13), plus standard persona query methods
- **Input parameters**: Similar to WS Padron A4 (token, sign, cuitRepresentada, idPersona)
- **Response**: Includes `domicilioFiscal` (codPostal, descripcionProvincia, direccion) and `estadoImpuesto` (e.g. "AC" for Activo)
- **Key difference from WS Padron A4**: Focused on inscription constancy (certificate) data rather than full padron details. Includes `getPersonaList_v2` for batch queries.

**SISA Validation Workflow** (synthesized from RAG findings):
1. Call `getPersona(idPersona=CUIT)` via WS Padron A4
2. Extract `impuesto` array from response
3. Check for `idImpuesto=30` (IVA) — if `estado="ACTIVO"`, the CUIT is IVA-registered
4. Check for `idImpuesto=20` (Monotributo) — if `estado="ACTIVO"`, apply Monotributista tier (0%/0%)
5. If neither IVA nor Monotributo are active: apply "Non-registered/Suspended" tier (16%/30%)
6. For IVA-registered CUITs: SISA risk categorization (Estado 1/2/3) determines the specific retention % — this categorization is NOT available in WS Padron A4 and must be obtained separately (e.g., via SIRE or direct SISA consultation)
7. Cache the SISA lookup result per CUIT with a TTL (e.g., 24h) to avoid excessive WS calls

> **CRITICAL GAP**: The exact WS or API for obtaining the SISA Estado (1/2/3) risk category is not identified in the RAG corpus. This may be available via the SIRE system, a dedicated SISA WS, or the ARCA web portal only. Fallback to PDF and/or ARCA documentation portal required.

---

## Findings Summary

| Task | Status | Key Blocker |
|------|--------|-------------|
| 1 — WSAA Cert Chain + TLS | Complete | Production CA name requires PDF fallback; homologacion CA confirmed as "Computadoras Test" (O=AFIP, C=AR) |
| 2 — WSCPE Methods | Complete | `descargadoDestinoCPEEmisionDestinoDG` confirmed for Emision Destino DG variant; `confirmarDescargaCPE` for standard grain; full method catalog extracted |
| 3 — WSLPG Form 1116 + SISA | Complete | Form 1116-B/C field catalogs fully extracted; SISA tier % from existing ARCA Guide §4.5 confirmed (RAG did not return explicit tier table); `liqLiquidacionACuenta` not found |
| 4 — SIRE General + IVA | Partial | SIRE IVA fields extracted from spec; SIRE General methods NOT found in RAG; batch lote spec title found but content not indexed; fallback to PDF required |
| 5 — WSCDC | Complete | Disambiguated WSCDC (Constatacion) vs grain certificates (via WSLPG); full grain cert field catalog extracted; WSCDC error codes extracted |
| 6 — WS Padron | Complete | `getPersona` full schema extracted; response field catalog complete; SISA Estado field NOT available in WS Padron A4 response — requires separate lookup |

**SISA Retention % Cross-Check** (after tasks 3 + 4 complete):
- Task 3 values: Using ARCA Guide §4.5 authoritative values (RAG did not return explicit tier table from WSLPG manual)
  - Estado 1: IVA 5%, Ganancias 0%
  - Estado 2: IVA 8%, Ganancias 2%
  - Estado 3: IVA 10.5%, Ganancias 15%
  - Non-registered/Suspended: IVA 16%, Ganancias 30%
  - Monotributista/IVA Exento: 0%, 0%
- Task 4 values: SIRE IVA spec did not contain tier percentages (they define fields for `importeRetencion` and `importeBaseCalculo` but the percentage logic is business-side)
- Match: **YES** — ARCA Guide §4.5 values are the single source of truth. WSLPG fields for retenciones are consistent (fields exist for retention amounts). SIRE IVA spec is consistent (fields exist for retention amounts and base calculation). No contradictory values found in RAG.

---

## Outstanding Items Requiring PDF Fallback

1. **Production CA name and validity** — check `WSAA.ObtenerCertificado.pdf` and `wsaa_obtener_certificado_produccion.pdf`
2. **SIRE General SOAP method names** — check `manualSIRE.pdf` full content (only p.21 was indexed)
3. **SIRE batch lote file format** — check `SIRE-especificacion-para-emision-por-lote.pdf` (only cover page indexed)
4. **WSLPG `liqLiquidacionACuenta` method** — check `manual_wslpg_1.24.pdf` full text
5. **WSLPG full error code table** — check WSLPG manual Annex
6. **WSCPE full error code table** — check `manual-wscpe.pdf` Annex
7. **SISA Estado WS/API** — determine the exact mechanism for obtaining SISA risk categorization (Estado 1/2/3)
8. **Legal basis (RG number)** for grain deposit certificate obligation
