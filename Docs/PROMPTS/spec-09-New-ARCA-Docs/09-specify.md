---
spec: "009"
name: "New ARCA Docs — Blueprint Knowledge Update"
type: Blueprint Update
branch: 009-New-ARCA-Docs
created: 2026-03-18
depends_on: [spec-01, spec-02, spec-03, spec-04, spec-05, spec-06, spec-07, spec-08]
blocks: [spec-10, spec-11, spec-12, spec-13]
qdrant_collections: [arca_api_specs, arca_dev_guides, arca_setup_certs, acopio_research]
---

# Spec-09 Specification Context: New ARCA Docs — Blueprint Knowledge Update

## Feature Description

Spec-09 is an **enrichment pass** over the 9 existing GraviTea blueprint documents.
It replaces approximate or inferred ARCA technical knowledge — written during specs 01–08 from
deep-research markdown files — with **authoritative facts** drawn from official ARCA developer
PDFs now ingested into the Qdrant RAG system.

**Deliverable**: Not new documents. In-place updates to 9 existing files in `Docs/Project Blueprint/`.

### What Changed After Spec-08

After the spec-08 pipeline, a gap analysis identified six ARCA web services either missing
or imprecisely documented in the blueprint suite. Ten official ARCA PDF documents were
subsequently organized into `Docs/ARCA/` and ingested into three Qdrant collections:

| Collection | Content |
|-----------|---------|
| `arca_api_specs` | Technical spec PDFs: WSAA, WSFEv1, WS Padrón A4, SIRE emision-por-lote |
| `arca_dev_guides` | Developer manuals: WSLPG v1.24, WSCPE, SIRE, SIRE IVA, WSCDC v4, and invoice WS |
| `arca_setup_certs` | Certificate procedures: prod chain, homo chain, WSAA obtener/asociar cert |

Newly available precision (not in `acopio_research`):

- **WSCPE** — full SOAP method catalog, XML field lengths, CPE state machine, error codes
- **WSLPG v1.24** — Form 1116 B/C exact XML field names/types/lengths, batch format, error codes
- **SIRE + SIRE IVA** — retention SOAP methods, batch lote spec, IVA-specific SOAP service
- **WSCDC** — grain deposit certificate (entirely absent from specs 01-08)
- **WS Padrón A4 + Constancia Inscripción** — SISA lookup API and response fields
- **WSAA** — TRA XML schema, certificate chain details (prod vs homo), ADMINREL delegation
- **TLS** — minimum version requirements and transition timeline for ARCA connections

### Known Discrepancy to Resolve

`Docs/Project Blueprint/ARCA Grain Integration Guide.md` §5.4 notes that the HLD uses
`descargadoDestinoCPE` — **this is wrong**. The WSDL-authoritative method name is
`confirmarDescargaCPE`. This discrepancy must be corrected in HLD §6 as part of FR-0902.

---

## Current State

All 9 documents below are fully written (specs 01–08 complete). This spec enriches them:

| Priority | Document | Primary ARCA Sections Affected |
|----------|----------|-------------------------------|
| CRITICAL | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | All sections (§3 WSAA, §5 WSCPE, §6 WSLPG); new §7 SIRE detail, §8 WSCDC, §9 WS Padrón, §10 Error Codes |
| HIGH | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | RE/FA/CA ARCA requirement blocks |
| HIGH | `Docs/Project Blueprint/High-Level Design (HLD).md` | §6 Integration Architecture, §12 Security (WSAA cert chain) |
| MEDIUM | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | ADR-007, ADR-018, ADR-020, ADR-027; new WSCDC ADR and WS Padrón ADR |
| MEDIUM | `Docs/Project Blueprint/REST API Design.md` | ARCA proxy endpoints, WSCDC endpoints, error response schemas |
| MEDIUM | `Docs/Project Blueprint/Data Model & Domain Model.md` | CertificadoDepositoCereal entity (new), LiquidacionPrimaria field corrections |
| LOW | `Docs/Project Blueprint/Roadmap.md` | WSCDC Phase 2 milestone, SIRE integration milestone |
| LOW | `Docs/Project Blueprint/PRD.md` | WSCDC feature (new), WS Padrón enrichment |
| MINIMAL | `Docs/Project Blueprint/Product Vision & Scope.md` | WSCDC in Phase 2 scope boundary |

---

## Research Inputs

### Domain Knowledge Protocol

> RULE: NEVER read full research PDFs directly. Use RAG queries via qdrant_search.py.
> Run queries per service section, not all upfront, to avoid token overload.
> After running all RAG queries for a section, inline the key facts as Critical Domain Facts
> before writing. This is the same protocol used in specs 01-08.

### RAG Query Command Reference

```bash
# Auto-routed across all collections (recommended for cross-service facts):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" --all -l 6

# Target ARCA official docs specifically:
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -c arca_dev_guides -l 6
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -c arca_api_specs -l 6
.venv/bin/python scripts/qdrant/qdrant_search.py -q "QUERY" -c arca_setup_certs -l 5

# No query expansion (for exact method/field name lookups):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "confirmarDescargaCPE" --no-expand --all -l 5

# Batch search (run all queries for a section at once, save results):
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
    -q "query 1" -q "query 2" -q "query 3" \
    -o Docs/RAG_results/spec09 -l 6
```

---

### RAG Queries: WSAA (FR-0901)

Run these before writing ARCA Guide §3 and HLD §12:

```bash
# TRA XML schema — complete element structure
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA TRA loginTicketRequest XML schema uniqueId generationTime expirationTime" \
  --all -l 6

# Certificate generation — CSR distinguished name fields
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA certificado producción generación CSR distinguished name campo CN O" \
  --all -l 6

# Certificate association — link cert to web service
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA asociar certificado servicio WSDN CUIT representante" \
  --all -l 6

# Ticket de Acceso — token + sign structure, expiration
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA ticket acceso token sign expiración 24 horas UTC zona horaria ART" \
  --all -l 6

# ADMINREL — delegation and authorized representative
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA delegación ADMINREL DelegarWS representante autorizado tercero" \
  --all -l 6

# Homologación vs producción — environment differences
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA homologación producción diferencia entorno endpoint certificado" \
  --all -l 5

# WSAA error handling — common errors and retry policy
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA error código CMSException LoginFault expiración token renovación" \
  --all -l 5
```

---

### RAG Queries: WSCPE (FR-0902)

Run these before writing ARCA Guide §5 and correcting HLD §6:

```bash
# Method catalog — all SOAP method names (critical: verify confirmarDescargaCPE)
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE SOAP método nombre lista operaciones disponibles" \
  --no-expand --all -l 7

# confirmarDescargaCPE — exact signature, parameters, required fields
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "confirmarDescargaCPE parámetros XML obligatorio campo" \
  --no-expand --all -l 7

# generarCPE / autorizarCPE — carta de porte electrónica creation flow
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE autorizarCPE generarCPE solicitar carta de porte XML campo entrada" \
  --all -l 6

# CPE state machine — all states and transitions
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "CPE estado carátula pendiente autorizado activo descargado rechazado anulado transición" \
  --all -l 6

# XML field catalog — types, lengths, validations
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE campo XML tipo longitud máxima requerido validación tabla" \
  --all -l 6

# Error code catalog — all WSCPE error codes with descriptions
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE error código retorno rechazo descripción tabla catálogo" \
  --all -l 6

# Endpoints — WSDL URLs for homologación and producción
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE endpoint WSDL URL homologación producción servicio" \
  --all -l 5

# CTG field — code structure and grain type relationship
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE CTG código transporte grano especie campo relación" \
  --all -l 6

# NroVuelta / contingency — error handling for failed authorizations
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE contingencia vuelta timeout reintento autorización fallida" \
  --all -l 5

# Destino final — acopiador as destino field validation
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCPE destino acopiador CUIT campo validación destino final planta" \
  --all -l 6
```

---

### RAG Queries: WSLPG (FR-0903)

Run these before writing ARCA Guide §6, Data Model corrections, and REST API corrections:

```bash
# Main liquidation method — parameters and required fields
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG autorizarLiquidacionPrimaria parámetros entrada XML obligatorio" \
  --all -l 7

# Form 1116-B field catalog — compra directa
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "Form 1116-B campo XML tipo longitud tabla compra cuenta propia" \
  --all -l 6

# Form 1116-C field catalog — consignación/comisión
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "Form 1116-C campo XML tipo longitud comisión consignación tabla" \
  --all -l 6

# Retention calculation — IVA and Ganancias tiers from SISA status
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG retención IVA ganancias porcentaje SISA inscripto no inscripto categoría" \
  --all -l 6

# Canje — grain barter fields and specific structure
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG canje campo intercambio insumos granos especie tabla" \
  --all -l 6

# Nota débito / crédito — post-liquidation adjustments
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG nota débito crédito método parámetros ajuste post-liquidación" \
  --all -l 5

# Batch / lote — bulk operation processing format
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG lote batch procesamiento masivo operaciones múltiples" \
  --all -l 5

# Error codes — WSLPG validation and business errors
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG código error validación campo descripción tabla catálogo" \
  --all -l 6

# Anulación — cancellation of a liquidation
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG anularLiquidacion anulación parámetros condición" \
  --all -l 5

# Neto a pagar — final payment calculation components
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG neto pagar productor cálculo fórmula desglose retenciones" \
  --all -l 6

# Peso recibido / conforme — weight fields in liquidation
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSLPG peso recibido ajuste conforme kilos campo merma liquidación" \
  --all -l 6
```

---

### RAG Queries: SIRE + SIRE IVA (FR-0904)

Run these before writing ARCA Guide §7, correcting ADR-027, and enriching SRS:

```bash
# SIRE main SOAP method — emitir retención
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE emitirRetencion SOAP método parámetros entrada XML" \
  --all -l 6

# SIRE retention calculation — tier table with exact percentages
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE retención ganancias IVA porcentaje tabla SISA estado categoría" \
  --all -l 7

# SIRE IVA — dedicated IVA retention SOAP service methods
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE IVA SOAP emitirRetencionIVA método parámetros especificación" \
  --all -l 6

# SIRE batch import — lote file format and processing
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE emision lote batch importación archivo formato estructura registro" \
  --all -l 6

# SIRE constancia retención — proof of retention issuance
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE constancia retención número código consulta descarga" \
  --all -l 5

# SIRE error codes — validation and business errors
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE error código validación CUIT contribuyente tabla descripción" \
  --all -l 5

# SIRE FAQ — common integration questions
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE preguntas frecuentes importación lote errores comunes timeout" \
  --all -l 5

# SIRE acopiadores — specific obligations for grain brokers
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SIRE acopiadores granos obligación retención RG resolución aplicación" \
  --all -l 5

# SISA tier determination — how to query SISA status before retention
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SISA estado consulta antes retención inscripto categoría IVA productor" \
  --all -l 6
```

---

### RAG Queries: WSCDC — Grain Deposit Certificate (FR-0905 — NEW SERVICE)

WSCDC was entirely absent from specs 01-08. Run all of these queries:

```bash
# WSCDC method catalog — all available SOAP operations
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC método SOAP lista operaciones disponibles nombre" \
  --no-expand --all -l 7

# informarDepositoCereal — primary method to register grain receipt
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC informarDepositoCereal parámetros entrada XML campo obligatorio" \
  --no-expand --all -l 7

# XML field catalog — grain types, weight, humidity, establishment
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC campo granoTipo kilogramos humedad establecimiento acopio XML" \
  --all -l 6

# State machine — deposit certificate lifecycle
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC constancia estado ciclo vida pendiente emitida cancelada retirada" \
  --all -l 6

# Retiro / cancelación — withdrawal and cancellation methods
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC informarRetiroCereal anularDepósito método parámetros cancelar" \
  --all -l 6

# Error codes — WSCDC validation errors
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC código error validación campo tabla descripción catálogo" \
  --all -l 6

# Legal obligation — regulatory basis for WSCDC (which RG, which entities)
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC obligación legal RG resolución acopiadores almacenamiento cereal" \
  --all -l 6

# Relationship with WSCPE — same grain movement, different registration
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC WSCPE relación carta de porte depósito cereal misma operación" \
  --all -l 5

# Endpoints — WSDL URL for homologación and producción
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC endpoint WSDL URL homologación producción acceso" \
  --all -l 5

# Grain species codes — which codes are valid for WSCDC
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSCDC especie código grano trigo maíz soja girasol tabla válida" \
  --all -l 6
```

---

### RAG Queries: WS Padrón A4 + Constancia Inscripción (FR-0906)

Run these before writing ARCA Guide §9, REST API endpoint, and SRS requirements:

```bash
# getPersona — main method for CUIT lookup
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "ws_sr_padron_a4 getPersona CUIT parámetros respuesta XML campo" \
  --no-expand --all -l 7

# Response field catalog — IVA category, activities, address
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "padrón respuesta categoría IVA actividad domicilio razón social CUIT" \
  --all -l 6

# SISA status in Padrón response — where to find inscripción status
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "padrón respuesta SISA estado inscripto operadores granos actividad" \
  --all -l 6

# Constancia inscripción — generate official SISA certificate
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "ws_sr_constancia_inscripcion método generarConstancia parámetros respuesta" \
  --no-expand --all -l 6

# SISA padrón — operators of grain: query by CUIT, activity code
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "SISA operadores granos padrón consulta CUIT inscripto categoría retención" \
  --all -l 6

# Usage at romaneo time — validate producer SISA status before acceptance
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "validar productor SISA inscripción antes romaneo recepción granos" \
  --all -l 5

# Error codes and security — Padrón access control, authorization
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WS padrón autorización acceso error código seguridad WSAA token" \
  --all -l 5
```

---

### RAG Queries: Certificate Chain and TLS (FR-0901 + FR-0910)

Run these before writing ARCA Guide §3 certificate section and HLD §12:

```bash
# Production certificate chain — CA hierarchy and validity dates
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA certificado producción cadena CA raíz AFIPRootCA2 Computadores vigencia 2035" \
  --all -l 5

# Homologación certificate chain — test environment chain
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA certificado homologación cadena AC_Raiz_Homo ComputadoresTest vigencia" \
  --all -l 5

# WSASS — test environment adhesion process
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSASS como adherirse entorno pruebas homologación proceso pasos" \
  --all -l 5

# TLS — minimum version and transition timeline
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "TLS ARCA versión mínima 1.2 1.3 cronograma transición protocolo" \
  --all -l 5

# Multi-tenant certificate management — one cert per tenant
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "WSAA múltiples contribuyentes certificado tenant CUIT separado gestión" \
  --all -l 5
```

---

### RAG Queries: General ARCA Fiscal Framework for Acopios

Run these to enrich SRS regulatory requirements and PRD feature descriptions:

```bash
# Regulatory framework — which RGs govern acopiadores' ARCA obligations
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "acopiadores resolución general RG ARCA obligación fiscal granos número" \
  --all -l 6

# Invoice type for grain — comprobante tipo A B C for acopiadores
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "factura electrónica granos acopiadores comprobante tipo A B C liquidación" \
  --all -l 6

# RG 4310 — specific ARCA regulation for grain brokers
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "RG 4310 ARCA acopiadores inscripción obligaciones digitales" \
  --all -l 5

# ARCA grain services architecture — hub-and-spoke integration overview
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "ARCA servicios granos arquitectura integración hub spoke WSAA centro" \
  --all -l 6

# ARCA FAQ — common web services questions applicable to all services
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "preguntas frecuentes web services ARCA timeout reintento error manejo general" \
  --all -l 5

# Ingresos brutos (IIBB) — provincial tax rates for grain operations
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "ingresos brutos IIBB provincia tasa granos acopiadores alícuota" \
  --all -l 5

# Simultaneous obligations — CPE + deposit cert at romaneo reception
.venv/bin/python scripts/qdrant/qdrant_search.py \
  -q "carta de porte depósito cereal simultáneo romaneo recepción múltiple" \
  --all -l 5
```

---

### Source Documents (official ARCA PDFs — reference if RAG is insufficient)

| Doc | Path | Key Content |
|-----|------|-------------|
| WSCPE manual | `Docs/ARCA/WSCPE/manual-wscpe.pdf` | SOAP methods, state machine, XML schemas, error codes |
| WSLPG v1.24 | `Docs/ARCA/WSLPG/manual_wslpg_1.24.pdf` | Form 1116 B/C fields, retention calculation, batch format |
| SIRE manual | `Docs/ARCA/SIRE/manualSIRE.pdf` | Retention SOAP, tier table, constancia |
| SIRE IVA SOAP | `Docs/ARCA/SIRE/SOAP-SIRE-IVA-Manualparaeldesarrollador_V1_0_0.pdf` | IVA-specific SOAP methods |
| SIRE lote spec | `Docs/ARCA/SIRE/SIRE-especificacion-para-emision-por-lote.pdf` | Batch import file format |
| WSCDC v4 | `Docs/ARCA/WSCDC/WSCDC-manual-desarrollador-v4.pdf` | Full deposit certificate lifecycle |
| WS Padrón A4 | `Docs/ARCA/WS Padrón/manual_ws_sr_padron_a4_v1.3.pdf` | getPersona API, response fields |
| WS Constancia | `Docs/ARCA/WS Padrón/manual_ws_sr_ws_constancia_inscripcion.pdf` | SISA inscription certificate API |
| WSAA manual | `Docs/ARCA/WSAA/WSAAmanualDev.pdf` | TRA schema, TA structure, code examples |
| WSAA tech spec | `Docs/ARCA/WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf` | Protocol spec, error codes |
| Cert prod | `Docs/ARCA/Certificados/Produccion/WSAA.ObtenerCertificado.pdf` | Prod cert generation steps |
| WSASS | `Docs/ARCA/Certificados/Testing/WSASS_manual.pdf` | Homo environment setup |
| Arch overview | `Docs/ARCA/ARCA-System-Architecture.md` | System architecture markdown overview |

### Critical Domain Facts (minimum pre-loaded context)

These facts are pre-verified and MUST be used to seed writing. Verify any discrepancies via RAG.

**WSAA:**
- TRA XML contains: `<loginTicketRequest><header><uniqueId>`, `<generationTime>`, `<expirationTime>`, `<service>`
- TA (Ticket de Acceso) returned: `<token>` + `<sign>` — both required as headers on every downstream service call
- TA default validity: ~12 hours (confirm exact from RAG); GraviTea caches TA with 5-minute safety margin
- Production cert chain: AFIPRootCA2 (2015-2035) → Computadores (2024-2035)
- Homologación cert chain: AC_Raiz_Homo (2014-2034) → ComputadoresTest (2022-2030)
- Certificate generation requires CSR with specific DN fields (O, CN, SERIALNUMBER=CUIT-xxxxx)
- ADMINREL: Acopiador can delegate WSAA to GraviTea's certificate via DelegarWS relationship

**WSCPE:**
- **AUTHORITATIVE method name**: `confirmarDescargaCPE` (not `descargadoDestinoCPE` — HLD has a typo)
- WSCPE is Phase 1 of GraviTea MVP (romaneo triggers WSCPE, which triggers WSCDC)
- WSLPG is Phase 2 (grain settlement — separate from reception)
- CPE state machine at minimum: Pendiente → Autorizado → Activo → Descargado (confirmed) → Closed

**WSLPG v1.24:**
- Form 1116-B = compra por cuenta propia (direct purchase); Form 1116-C = comisión/consignación
- Retention tiers (SISA categories — verify exact percentages via RAG):
  - Inscripto IVA responsable: IVA ~8%, Ganancias ~2%
  - Monotributo/exento: higher rates (confirm from RAG)
  - No inscripto: IVA 21%, Ganancias varies
- Batch processing: WSLPG supports bulk lote submission (confirm format via RAG)
- Fields include: nroOrden, codigoGrano, pesoNeto, humidity, precio, CUIT vendedor/comprador

**SIRE:**
- Two separate services: `sire` (general retenciones) + `sire_iva` (IVA-specific SOAP v1.0.0)
- ADR-027 correct label: "SISA-Tier Retention Calculation at WSLPG Filing Time"
- SIRE can process retenciones in batch (lote import spec) — separate from SOAP
- constancia de retención issued after each SIRE transaction

**WSCDC (NEW — entirely absent from specs 01-08):**
- Web Service Constancia de Depósito de Cereal — v4 developer manual
- Acopiadores must inform ARCA when they receive grain into storage
- Separate from WSCPE (movement document) — WSCDC = receipt at destination
- Lifecycle: informar depósito → constancia emitida → informar retiro / anular
- Contains: grain species, kg received, humidity, establishment CUIT, date

**WS Padrón:**
- `ws_sr_padron_a4` v1.3: `getPersona(CUIT)` returns IVA category, fiscal activities, domicile
- `ws_sr_constancia_inscripcion`: generates official SISA inscription certificate PDF
- GraviTea uses WS Padrón at romaneo time to: (a) validate producer CUIT, (b) determine SISA tier → feeds SIRE retention calculation

---

## Functional Requirements

### FR-0901: WSAA Certificate Lifecycle Enrichment

**Target docs**: ARCA Grain Integration Guide §3 (WSAA), HLD §12 (Security)

Replace approximate WSAA descriptions with authoritative facts from `WSAAmanualDev.pdf` and
`Especificacion_Tecnica_WSAA_1.2.2.pdf`:
- Complete TRA XML schema with all elements and data types
- TA structure with token + sign usage on downstream calls
- Production and homologación certificate chains with exact CA names and validity periods
- Certificate generation workflow: CSR → DN fields → ARCA portal submission → download
- ADMINREL delegation: multi-tenant architecture where GraviTea manages certs on behalf of tenants
- Error handling: CMSException, LoginFault, TA expiration and refresh pattern

### FR-0902: WSCPE Method Catalog and State Machine Correction

**Target docs**: ARCA Grain Integration Guide §5 (WSCPE), HLD §6 (Integration Architecture)

From `manual-wscpe.pdf`:
- Replace all WSCPE method descriptions with authoritative SOAP method names and signatures
- Correct `descargadoDestinoCPE` → `confirmarDescargaCPE` in HLD §6 (all occurrences)
- Document complete CPE state machine with all states and valid transitions
- Add XML field catalog: field names, types (string/int/date), max lengths, valid value tables
- Add error code catalog (subset — at minimum the 5 most common errors)
- Add WSDL endpoint URLs for both environments

### FR-0903: WSLPG Form 1116 B/C Field Precision

**Target docs**: ARCA Grain Integration Guide §6 (WSLPG), Data Model §12, REST API Design §10

From `manual_wslpg_1.24.pdf`:
- Add complete Form 1116-B XML field table (name, type, length, required, description)
- Add complete Form 1116-C XML field table with consignment-specific fields
- Add retention calculation table with SISA tier → IVA% + Ganancias% values
- Add canje field definitions (grain-for-supplies barter transaction type)
- Add nota débito/crédito methods for post-liquidation adjustments
- Add batch lote format description
- Add WSLPG error code table (minimum top 10 errors)
- Correct any Data Model fields that differ from authoritative WSLPG schema
- Verify REST API Design WSLPG proxy endpoint parameters match authoritative spec

### FR-0904: SIRE Retention System Documentation

**Target docs**: ARCA Grain Integration Guide §7 (SIRE detail), ADR (ADR-027), SRS (retention requirements)

From `manualSIRE.pdf`, `SOAP-SIRE-IVA-*.pdf`, `SIRE-especificacion-para-emision-por-lote.pdf`:
- Document SIRE SOAP methods: emitirRetencion, consultarRetencion, and others
- Document SIRE IVA SOAP v1.0.0 methods separately (it's a different service)
- Add batch lote import format: file structure, field layout, submission endpoint
- Add SIRE error code catalog
- Confirm and correct ADR-027 label and decision text
- Add SIRE-related SRS requirements with precise references to SOAP methods

### FR-0905: WSCDC Grain Deposit Certificate (NEW SERVICE)

**Target docs**: ARCA Grain Integration Guide (new §8 WSCDC), Data Model (new entity), HLD §6, ADR (new ADR), SRS (new requirements)

From `WSCDC-manual-desarrollador-v4.pdf`:
- Write complete WSCDC section in ARCA Guide: legal obligation, lifecycle, SOAP methods, XML fields, errors
- Add `CertificadoDepositoCereal` entity to Data Model with all WSCDC-mandated fields
- Add WSCDC to HLD §6 integration architecture (alongside WSCPE and WSLPG in the flow)
- Add ADR: "WSCDC — Grain Deposit Certificate Obligation" documenting decision to integrate at romaneo time
- Add SRS requirements: CA-WSCDC-01 through CA-WSCDC-N covering all WSCDC obligations

### FR-0906: WS Padrón A4 and SISA Lookup Documentation

**Target docs**: ARCA Grain Integration Guide (new §9 WS Padrón), REST API Design (SISA validation endpoint), SRS (SISA validation requirements)

From `manual_ws_sr_padron_a4_v1.3.pdf` and `manual_ws_sr_ws_constancia_inscripcion.pdf`:
- Document `getPersona(CUIT)` method: input, full response field catalog, error codes
- Document `ws_sr_constancia_inscripcion` method: purpose, inputs, PDF output
- Explain GraviTea usage pattern: WS Padrón called at romaneo time → SISA tier → feeds SIRE retention
- Add REST API Design endpoint: `GET /api/arca/padron/{cuit}` proxy for SISA validation
- Add SRS requirements for SISA producer validation flow

### FR-0907: ADR Enrichment for ARCA Services

**Target docs**: Architecture Decision Records (ADR).md

Enrich or correct the following existing ADRs:
- **ADR-007 (WSAA)**: Add multi-tenant cert management pattern, ADMINREL delegation decision
- **ADR-018 (WSCPE)**: Correct method name, add state machine reference, add error handling strategy
- **ADR-027 (SIRE)**: Correct label to "SISA-Tier Retention Calculation at WSLPG Filing Time"; add SIRE vs SIRE IVA distinction

Add new ADRs:
- **ADR-0XX (WSCDC)**: Decision to integrate WSCDC at romaneo reception time; synchronous vs deferred
- **ADR-0XX (WS Padrón)**: Decision to call WS Padrón at romaneo time for SISA tier determination; caching strategy

### FR-0908: SRS ARCA Requirements Precision

**Target docs**: Software Requirements Specification (SRS).md

For all existing ARCA-related SRS requirements:
- Replace vague references like "ARCA integration" with specific service name + method
- Add official RG numbers where applicable (from RAG queries on regulatory framework)
- Add explicit acceptance criteria referencing official field/method names
- Add new SRS requirements for WSCDC (FR-0905) and WS Padrón (FR-0906)

### FR-0909: Cross-Service Error Code Catalog

**Target docs**: ARCA Grain Integration Guide (new §10 Error Handling), REST API Design (error section), HLD §6 (resilience)

Compile from all developer manual RAG queries:
- WSCPE error code table (top errors + descriptions)
- WSLPG error code table
- SIRE error code table
- WSCDC error code table
- Common WSAA errors (CMSException, LoginFault, token expired)
- Recommended retry strategy per error class (retryable vs business errors)

### FR-0910: TLS and Protocol Requirements

**Target docs**: ARCA Grain Integration Guide (§3 or dedicated §), HLD §12 (Security)

From `Docs/ARCA/Cronograma TLS/` documentation (query via RAG):
- Document minimum TLS version for ARCA production connections
- Document transition timeline if there is an upcoming TLS 1.0/1.1 deprecation
- Add to HLD §12 security requirements: cipher suite requirements, cert pinning decision

---

## Non-Functional Requirements

### NF-0901: Zero TBD Markers
All ARCA-related "TBD", "TODO", "to be confirmed", "verify from official docs", or "approximate"
annotations across all 9 blueprint documents must be resolved. No placeholders remain.

### NF-0902: Authoritative Source Attribution
Every ARCA technical fact added by this spec must trace to either:
- A RAG-retrieved chunk (note the collection and source doc in a comment during writing)
- A direct citation from an official ARCA PDF section

Inferences and estimates are NOT acceptable. If a fact cannot be confirmed via RAG, run the
manual RAG query against the specific PDF's collection before writing.

### NF-0903: Non-ARCA Content is Frozen
Content not related to ARCA integration is out of scope. Do not edit, improve, or restructure
non-ARCA sections. Scope is strictly additive/corrective for ARCA sections only.

### NF-0904: Cross-Document Consistency
Where the same ARCA technical fact (method name, field, error code) appears across multiple
documents, it MUST be identical. After writing all updates, verify consistency for:
- `confirmarDescargaCPE` — ensure zero instances of `descargadoDestinoCPE` remain
- SISA retention percentages — same values in ARCA Guide, SRS, ADR-027
- WSCDC legal obligation description — consistent across HLD, ADR, SRS

### NF-0905: Document Structure Preservation
Preserve each document's existing section numbering, heading hierarchy, and writing style.
ARCA updates are enrichments (additions + in-place corrections), not rewrites.
Adding new sections (§8 WSCDC, §9 WS Padrón, §10 Error Codes to ARCA Guide) is permitted.

### NF-0906: RAG Over Direct File Reads
Consistent with the project's Domain Knowledge Protocol: all domain facts must come via RAG
queries. Direct PDF reads are a last resort when RAG returns insufficient chunks.
Document which RAG queries were run for each section in the spec (for traceability).

---

## Target Document Update Scope

| Document | Sections Affected | New Sections Added | Change Volume |
|----------|------------------|--------------------|---------------|
| `ARCA Grain Integration Guide.md` | §3 WSAA (cert chain), §5 WSCPE (methods+state machine+errors), §6 WSLPG (fields+retention+errors) | §7 SIRE detail, §8 WSCDC, §9 WS Padrón, §10 Error Codes | LARGE |
| `SRS.md` | All RE/FA/CA ARCA blocks | WSCDC and WS Padrón requirements | MEDIUM |
| `HLD.md` | §6 Integration Architecture (confirmarDescargaCPE fix, WSCDC added), §12 Security (cert chain, TLS) | None | MEDIUM |
| `ADR.md` | ADR-007, ADR-018, ADR-027 enrichment | WSCDC ADR, WS Padrón ADR | MEDIUM |
| `REST API Design.md` | ARCA proxy endpoints (param corrections), error response schemas | WSCDC proxy endpoint, SISA validation endpoint | MEDIUM |
| `Data Model & Domain Model.md` | LiquidacionPrimaria WSLPG field corrections | CertificadoDepositoCereal entity | SMALL |
| `Roadmap.md` | Phase 2 ARCA milestones (WSCDC, SIRE) | None | SMALL |
| `PRD.md` | ARCA feature section (WSCDC new feature, WS Padrón enrichment) | None | SMALL |
| `Product Vision & Scope.md` | Phase 2 ARCA scope boundary (add WSCDC) | None | MINIMAL |

---

## Acceptance Criteria

### AC-0901: ARCA Guide Completeness
ARCA Grain Integration Guide documents ≥ 8 ARCA services/sub-services with official SOAP method
names: WSAA, WSCPE, WSLPG, SIRE (general), SIRE IVA, WSCDC, WS Padrón A4,
WS Constancia Inscripción.

### AC-0902: Method Name Accuracy
Zero instances of `descargadoDestinoCPE` remain in any of the 9 blueprint documents.
`confirmarDescargaCPE` used consistently throughout.

### AC-0903: SIRE Documentation Quality
- ADR-027 label exactly reads: "SISA-Tier Retention Calculation at WSLPG Filing Time"
- ARCA Guide §7 contains SIRE SOAP method names (≥ 2 methods documented)
- A retention tier table with percentages (IVA + Ganancias per SISA category) appears in
  at least one document (ARCA Guide or ADR-027)

### AC-0904: WSCDC New Service Coverage
WSCDC appears in at minimum 5 documents: ARCA Guide (dedicated section with SOAP methods
and XML fields), Data Model (CertificadoDepositoCereal entity), HLD (in integration
architecture §6), ADR (decision record), SRS (requirements block).

### AC-0905: WS Padrón Integration Documented
`ws_sr_padron_a4` `getPersona` method documented with response field catalog in ARCA Guide §9.
REST API Design contains a SISA validation proxy endpoint.
SRS contains at least one WS Padrón requirement.

### AC-0906: Error Code Coverage
ARCA Guide §10 (or equivalent section) contains error code tables for ≥ 3 ARCA services
(WSCPE + WSLPG + at least one of SIRE/WSCDC/WSAA).

### AC-0907: Zero TBD or Approximate Markers
NF-0901 verified: grep for "TBD", "TODO", "confirm", "approximate" yields zero results
in ARCA-related sections across all 9 documents.

### AC-0908: TLS Requirements Documented
HLD §12 and/or ARCA Guide contain the minimum TLS version required by ARCA for production
connections, sourced from official Cronograma TLS documentation.

### AC-0909: Cross-Document Consistency
Same ARCA method name resolves identically across all documents where it appears.
SISA retention percentages are consistent between ARCA Guide, ADR-027, and SRS.

### AC-0910: Non-ARCA Content Unchanged
No substantive changes to non-ARCA content. ARCA Guide, HLD, ADR, SRS, REST API, Data
Model all retain their original structure with enrichment additions only.

### AC-0911: Certificate Chain Details Present
ARCA Guide §3 and HLD §12 contain:
- Production cert chain CA names and validity dates
- Homologación cert chain CA names and validity dates
- CSR generation DN field requirements

---

## Dependencies

### Depends On
- **spec-01 through spec-08** — all 9 blueprint documents must be fully written (complete ✅)
- **Qdrant RAG** — `arca_api_specs`, `arca_dev_guides`, `arca_setup_certs` collections must be ingested
  - Verify: `.venv/bin/python scripts/qdrant/qdrant_search.py -q "WSCPE" -c arca_dev_guides -l 1`
  - If empty: run `cd scripts/qdrant && .venv/bin/python ingest_arca_qdrant.py`

### Blocks
- **spec-10** (Grain Reference Data) — needs correct ARCA grain species codes (WSCPE/WSCDC)
- **spec-11** (Romaneo Core) — needs WSCPE + WSCDC + WS Padrón specs for romaneo integration
- **spec-12** (Storage & Position) — needs WSCDC deposit certificate requirements
- **spec-13** (Producer Accounts) — needs WSLPG + SIRE retention calculation precision

---

## Execution Notes

**Type**: Blueprint Update — single-author execution, no agent teams, no code

**Recommended execution order** (largest/most critical first):
1. ARCA Grain Integration Guide (primary target — WSAA, WSCPE, WSLPG, SIRE, WSCDC, WS Padrón, errors)
2. SRS (ARCA requirements enrichment + new WSCDC/WS Padrón requirements)
3. HLD (WSCPE method fix + WSAA cert chain + WSCDC in integration diagram)
4. ADR (ADR-007/018/027 corrections + new WSCDC + WS Padrón ADRs)
5. REST API Design (WSCDC endpoint + SISA validation + error schemas)
6. Data Model (CertificadoDepositoCereal entity + WSLPG field corrections)
7. Roadmap, PRD, Product Vision (minor updates — confirm WSCDC Phase placement)

**RAG discipline**: Run the queries for ONE service/section at a time, inline the facts,
then write that section. Do NOT run all queries upfront — token budget will be exhausted.

**Writing persona**: `technical-writer` — precision, authoritative tone, table-heavy format
for field catalogs and error codes; no marketing language.

**Tool preference**: Use Serena `find_symbol` / `search_for_pattern` to locate the exact
sections to update within each document, then use `replace_symbol_body` or targeted edits.
Do not rewrite entire documents.
