# User Guide: Qdrant RAG for GRAVITEA-ERP

**Target Audience**: GRAVITEA development team working on ARCA electronic invoicing integration
**Last Updated**: 2026-02-09
**Project Context**: Multi-tenant ERP with ARCA electronic invoicing requirements

---

## Table of Contents

1. [What Is This?](#what-is-this)
2. [Architecture](#architecture)
3. [Setup](#setup)
4. [Collections & Data](#collections--data)
5. [Searching](#searching)
6. [Using RAG for Invoice Module Design](#using-rag-for-invoice-module-design)
7. [Quick Reference](#quick-reference)
8. [Troubleshooting](#troubleshooting)

---

## What Is This?

Qdrant is a **vector database** running locally on your machine inside a Docker container. It stores embeddings (numerical representations) of all 20 ARCA PDF documents, enabling **semantic search** — you ask questions in natural Spanish and it finds the most relevant document chunks.

**What runs where**:

| Component | Runs On | Address |
|-----------|---------|---------|
| Qdrant (vector DB) | Docker container on your PC | `localhost:6333` |
| Ollama (embedding engine) | Native app on your PC | `localhost:11434` |
| Embedding model (`nomic-embed-text`) | Your GPU (RTX 4070 Ti) | via Ollama |
| PDFs | Your disk (`Docs/ARCA/`) | Local files |
| Ingestion scripts | Python on your PC | `scripts/qdrant/` |

**Nothing goes to the cloud.** All embedding and search happens locally.

---

## Architecture

```
  You type a question (Spanish)
         │
         ▼
  ┌──────────────────┐
  │  Ollama (local)   │  Converts your question into a 768-dim vector
  │  nomic-embed-text │  using your RTX 4070 Ti GPU
  └────────┬─────────┘
           │ query vector
           ▼
  ┌──────────────────┐
  │  Qdrant (Docker)  │  Finds the closest vectors using cosine similarity
  │  localhost:6333   │  Returns the original text chunks + metadata
  └────────┬─────────┘
           │
     ┌─────┼─────────────────┐
     │     │                 │
┌────▼───────┐ ┌──────▼──────┐ ┌──────▼────────┐
│api_specs   │ │ dev_guides  │ │ setup_certs   │
│1,151 chunks│ │1,088 chunks │ │  65 chunks    │
│ 5 PDFs     │ │ 7 PDFs      │ │  8 PDFs       │
└────────────┘ └─────────────┘ └───────────────┘
```

### Embedding Configuration

```
Model:          nomic-embed-text (137M params, F16 quantization)
Dimensions:     768
Context:        8,192 tokens
Distance:       Cosine similarity
Doc prefix:     "search_document: {text}"
Query prefix:   "search_query: {query}"
Language:       Multilingual (handles Spanish ARCA docs well)
```

### Models Tested and Rejected

| Model | Dims | Issue |
|-------|------|-------|
| `zylonai/multilingual-e5-large` | 1024 | Produces NaN embeddings in Ollama 0.15.6 |
| `mxbai-embed-large` | 1024 | 512-token context limit, too short for our chunks |

---

## Setup

### Prerequisites

- Docker Desktop installed and running
- Ollama installed (`https://ollama.com/download/windows` or `winget install Ollama.Ollama`)

### Step 1: Start Qdrant Container

If the container already exists:
```bash
docker start qdrant-gravitea
```

If creating from scratch:
```bash
docker run -d \
  --name qdrant-gravitea \
  -p 6333:6333 -p 6334:6334 \
  -v "C:\Users\Ghibe\Documents\Gravitea\GRAVITEA-ERP\.qdrant_storage:/qdrant/storage" \
  qdrant/qdrant:v1.16.3
```

### Step 2: Pull Embedding Model

```bash
ollama pull nomic-embed-text
```

### Step 3: Verify Everything

```bash
# Qdrant running?
curl -s http://localhost:6333/collections | python3 -m json.tool

# Ollama running?
curl -s http://localhost:11434/api/tags

# Model available?
ollama list
```

Or use the verification script:
```bash
bash scripts/qdrant/verify_qdrant_setup.sh
```

### Step 4: Ingest PDFs

```bash
# All collections
python3 scripts/qdrant/ingest_arca_qdrant.py

# Single collection
python3 scripts/qdrant/ingest_arca_qdrant.py --collection arca_api_specs

# Dry run (validate chunks without writing)
python3 scripts/qdrant/ingest_arca_qdrant.py --dry-run
```

Ingestion is **idempotent** — running it again overwrites existing points (deterministic UUID5 IDs).

---

## Collections & Data

**ARCA collections: 2,304 points from 20 PDFs across 3 collections. Wikis collection ingested separately.**

### `arca_api_specs` — 1,151 points

Technical specifications: error codes, WSDL schemas, validation rules, field-level docs.

| PDF | Web Service | Points | Content Focus |
|-----|------------|--------|---------------|
| Especificacion_Tecnica_WSAA_1.2.2.pdf | WSAA | 28 | Auth token XML, signing, endpoints |
| wsfev1-RG-4291.pdf | WSFEv1 | 420 | Invoice issuance, error codes, field validation |
| wsmtxca-RG-2904.pdf | WSMTXCA | 531 | Item-level invoicing, WSDL, full field specs |
| wsbfev1-RG-5427-y-2861.pdf | WSBFEV1 | 106 | Fiscal bonds, error codes |
| wsseg-RG-2668.pdf | WSSEG | 66 | Insurance WS, field specs |

- **Chunk size**: max 1,200 chars (~300 tokens) — optimized for table rows and error code granularity
- **Overlap**: 150 chars
- **Payload indexes**: `ws_name`, `section`, `source_file`

### `arca_dev_guides` — 1,088 points

Developer manuals: code examples, authentication workflows, endpoint URLs, integration patterns.

| PDF | Web Service | Points | Content Focus |
|-----|------------|--------|---------------|
| manual-desarrollador-ARCA-COMPG-v4-1.pdf | WSFEv1 | 275 | Main dev guide, FECAESolicitar flows |
| WSAAmanualDev.pdf | WSAA | 43 | Auth client examples (PHP, C#, Java, PowerShell) |
| WSFEX-Manualparaeldesarrollador_V3.1.1.pdf | WSFEXv1 | 119 | Export invoicing, dev patterns |
| WSBFEV1-ManualParaElDesarrollador_V3_0.pdf | WSBFEV1 | 65 | Fiscal bonds dev guide |
| WSSEG-ManualParaElDesarrollador_ARCA.pdf | WSSEG | 40 | Insurance dev guide |
| Manual_Desarrollador_WSCT_v1.6.4.pdf | WSCT | 151 | Tourism dev guide |
| Web-Service-MTXCA-v25.pdf | WSMTXCA | 395 | Item-level invoicing dev guide |

- **Chunk size**: max 1,800 chars (~450 tokens) — preserves code examples intact
- **Overlap**: 200 chars
- **Payload indexes**: `ws_name`, `section`, `source_file`

### `arca_setup_certs` — 65 points

Certificate generation, environment setup, WS delegation, TLS migration.

| PDF | Environment | Points | Content Focus |
|-----|------------|--------|---------------|
| WSAA.ObtenerCertificado.pdf | Produccion | 9 | Cert generation steps |
| wsaa_obtener_certificado_produccion.pdf | Produccion | 5 | Prod cert request flow |
| wsaa_asociar_certificado_a_wsn_produccion.pdf | Produccion | 3 | Cert-to-WS association |
| ADMINREL.DelegarWS.pdf | Produccion | 17 | WS delegation procedures |
| WSASS_como_adherirse.pdf | Testing | 8 | Testing environment enrollment |
| WSASS_manual.pdf | Testing | 20 | WSASS self-service management |
| Arquitectura overview | General | 2 | SOAP architecture, X.509 auth |
| Cronograma TLS | General | 1 | TLS 1.2 migration schedule |

- **Chunk size**: max 2,000 chars (~500 tokens) — keeps procedural steps together
- **Overlap**: 200 chars
- **Payload indexes**: `environment`, `procedure_type`, `source_file`

### `wikis` — General Reference Docs

English-language framework documentation and security handbooks. Uses `nomic-embed-text` (768 dims) — a better fit for English technical docs with 3.3x smaller vectors than qwen3.

| PDF | Topic | Content Focus |
|-----|-------|---------------|
| django-readthedocs-io-en-5.2.x.pdf | Django | Full Django 5.2 framework docs |
| jwt-handbook-v0_14_2.pdf | JWT | JWT security handbook |

- **Embedding model**: `nomic-embed-text` (768 dims, 8K context)
- **Chunk size**: max 2,000 chars (~500 tokens)
- **Overlap**: 250 chars
- **Payload indexes**: `topic`, `doc_type`, `source_file`

```bash
# Ingest wikis
python3 scripts/qdrant/ingest_wikis_qdrant.py

# Search wikis
python3 scripts/qdrant/qdrant_search.py --query "Django select_related vs prefetch_related" --collection wikis --limit 5
```

---

## Searching

### Search Quality Baseline

| Query (Spanish) | Collection | Top Score | Correct? |
|-----------------|-----------|-----------|----------|
| "codigos de error en factura electronica" | api_specs | 0.73 | Yes |
| "como generar ticket de acceso WSAA" | dev_guides | 0.77 | Yes |
| "obtener certificado digital para produccion" | setup_certs | 0.80 | Yes |
| "FECAESolicitar parametros obligatorios" | api_specs | 0.74 | Yes |
| "ciclo de vida del CAE comprobante autorizado" | dev_guides | 0.76 | Yes |
| "tipos de comprobante permitidos" (filter: wsfev1) | api_specs | 0.81 | Yes |
| "consultar ultimo comprobante autorizado" (filter: wsmtxca) | api_specs | 0.78 | Yes |
| "configurar certificado testing" (filter: testing) | setup_certs | 0.72 | Yes |

Filtered search (by `ws_name`, `environment`) narrows results to the specified web service or environment.

### Search via Python Script (Current Method)

Until the MCP server connection is fixed, search via:

```bash
python scripts/qdrant/qdrant_search.py --query "FECAESolicitar campos obligatorios" --collection arca_api_specs --limit 5
```

### Search via curl

```bash
# Generate embedding
VECTOR=$(curl -s http://localhost:11434/api/embed \
  -d '{"model":"nomic-embed-text","input":"search_query: codigos de error WSFEv1"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['embeddings'][0])")

# Search Qdrant
curl -s http://localhost:6333/collections/arca_api_specs/points/search \
  -H "Content-Type: application/json" \
  -d "{\"vector\": $VECTOR, \"limit\": 5, \"with_payload\": true}"
```

---

## Using RAG for Invoice Module Design

### Key Queries for Module Design

| Design Task | Query | Collection | Filter |
|-------------|-------|-----------|--------|
| Comprobante model fields | "campos obligatorios FECAESolicitar" | api_specs | ws_name=wsfev1 |
| Error handling | "codigos de error rechazo comprobante" | api_specs | ws_name=wsfev1 |
| IVA types & rates | "alicuotas IVA tipos" | api_specs | ws_name=wsfev1 |
| Currency codes | "FEParamGetTiposMonedas" | api_specs | ws_name=wsfev1 |
| Document types | "FEParamGetTiposDoc tipos documento" | api_specs | ws_name=wsfev1 |
| CAE authorization flow | "solicitar CAE FECAESolicitar" | dev_guides | ws_name=wsfev1 |
| WSAA token generation | "LoginCms ticket acceso" | dev_guides | ws_name=wsaa |
| Certificate setup | "generar certificado digital" | setup_certs | environment=produccion |
| CAEA flow (offline) | "CAEA contingencia" | dev_guides | ws_name=wsfev1 |
| Export invoices | "factura exportacion" | dev_guides | ws_name=wsfexv1 |
| Item-level invoicing | "detalle items comprobante" | api_specs | ws_name=wsmtxca |
| Fiscal QR code | "codigo QR comprobante" | dev_guides | ws_name=wsfev1 |

### Web Services Relevant to Invoice Module

| WS | Purpose | Priority | Collection Coverage |
|----|---------|----------|--------------------|
| **WSFEv1** | Standard invoice issuance (RG-4291) | Critical | api_specs + dev_guides |
| **WSAA** | Authentication (token/ticket) | Critical | api_specs + dev_guides + setup_certs |
| **WSMTXCA** | Item-level invoicing (RG-2904) | High | api_specs + dev_guides |
| **WSFEXv1** | Export invoicing | Medium | dev_guides only |
| **WSBFEV1** | Fiscal bonds | Low | api_specs + dev_guides |
| **WSCT** | Tourism | Low | dev_guides only |
| **WSSEG** | Insurance | Low | api_specs + dev_guides |

### Retrieval Strategy

1. **Start with `arca_api_specs`** (filter by `ws_name`) — field definitions, validation rules, error codes
2. **Then `arca_dev_guides`** (filter by `ws_name`) — implementation patterns, code examples, endpoint URLs
3. **Use `arca_setup_certs`** only for environment/deployment questions

---

## Quick Reference

```bash
# Check infrastructure status
docker ps --filter "name=qdrant"
curl -s http://localhost:6333/collections | python3 -m json.tool
curl -s http://localhost:11434/api/tags

# Re-ingest (idempotent)
python3 scripts/qdrant/ingest_arca_qdrant.py                              # all collections
python3 scripts/qdrant/ingest_arca_qdrant.py --collection arca_api_specs  # single collection
python3 scripts/qdrant/ingest_arca_qdrant.py --dry-run                    # validate without writing

# Collection point counts
curl -s http://localhost:6333/collections/arca_api_specs | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['result']['points_count'])"

# Qdrant Web UI
# Open in browser: http://localhost:6333/dashboard

# Restart Qdrant
docker restart qdrant-gravitea

# View Qdrant logs
docker logs qdrant-gravitea -f
```

---

## Troubleshooting

### "Qdrant connection refused"

```bash
# Check if container is running
docker ps --filter name=qdrant-gravitea

# If stopped
docker start qdrant-gravitea

# If container doesn't exist, recreate it
docker run -d \
  --name qdrant-gravitea \
  -p 6333:6333 -p 6334:6334 \
  -v "C:\Users\Ghibe\Documents\Gravitea\GRAVITEA-ERP\.qdrant_storage:/qdrant/storage" \
  qdrant/qdrant:v1.16.3
```

### "Ollama model not found"

```bash
ollama list                     # check installed models
ollama pull nomic-embed-text    # pull missing model
curl http://localhost:11434/api/tags  # verify Ollama is running
# If not running, start Ollama from Start menu
```

### "MCP tools not showing up in Claude Code"

The Qdrant MCP server (`@mhalder/qdrant-mcp-server`) has npm peer dependency conflicts. See `claudedocs/ARCA_RAG_STATUS.md` section 2.1 for current status and workaround options.

### "Embeddings take too long"

```bash
# Check Ollama is using GPU
ollama ps

# Verify model size
ollama show nomic-embed-text

# nomic-embed-text (137M params) should embed in <100ms per chunk on RTX 4070 Ti
# Full corpus (2,304 chunks): ~3-5 minutes on GPU
```

### "NaN embeddings"

If you see NaN values in embeddings, you're likely using `zylonai/multilingual-e5-large` — this is a known Ollama bug. Switch to `nomic-embed-text`:

```bash
ollama pull nomic-embed-text
# Re-run ingestion with the new model
python3 scripts/qdrant/ingest_arca_qdrant.py
```

---

## File Reference

| File | Purpose |
|------|---------|
| `scripts/qdrant/ingest_arca_qdrant.py` | ARCA PDF ingestion (qwen3-embedding:4b, 2560 dims) |
| `scripts/qdrant/ingest_wikis_qdrant.py` | Wiki PDF ingestion (nomic-embed-text, 768 dims) |
| `scripts/qdrant/qdrant_search.py` | CLI search tool (auto-detects model per collection) |
| `scripts/qdrant/benchmark_qdrant_search.py` | Benchmark ARCA search quality |
| `scripts/qdrant/recreate_qdrant_collections.ps1` | Recreate all collections (PowerShell) |
| `scripts/qdrant/verify_qdrant_setup.sh` | Infrastructure verification script |
| `Docs/ARCA/` | Source PDFs (20 files, ~35MB) |
| `.qdrant_storage/` | Qdrant persistent data (Docker volume) |
| `claudedocs/ARCA_RAG_STATUS.md` | Full status doc with roadmap |
| `claudedocs/PROMPT_EMBEDDING_RESEARCH.md` | Research prompt for better embedding models |

---

*Last Updated: 2026-02-09*
*Project: GRAVITEA-ERP*
