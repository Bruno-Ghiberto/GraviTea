# Session: ARCA RAG Ingestion (2026-02-09)

## What Was Done
- Analyzed 20 ARCA PDFs in `Docs/ARCA/` to classify content types
- Designed 3-collection Qdrant architecture (api_specs, dev_guides, setup_certs)
- Created collections with 768-dim vectors (Cosine distance) + payload indexes
- Built ingestion script: `scripts/ingest_arca_qdrant.py`
- Ingested all 20 PDFs: **2,304 total points** across 3 collections
- Verified search quality with 8 test queries (scores 0.68-0.81)
- Wrote status document: `claudedocs/ARCA_RAG_STATUS.md`

## Collections Summary
- `arca_api_specs`: 1,151 points (5 files) - error codes, WSDL, validation rules
- `arca_dev_guides`: 1,088 points (7 files) - dev manuals, code examples
- `arca_setup_certs`: 65 points (8 files) - cert setup, environment procedures

## Embedding Model Decision
- **Selected**: `nomic-embed-text` (768 dims, 8192 ctx, 137M params)
- **Rejected**: `zylonai/multilingual-e5-large` (NaN bug in Ollama 0.15.6)
- **Rejected**: `mxbai-embed-large` (512 token context too short for chunks)
- Prefixes: `search_document: ` for docs, `search_query: ` for queries

## Chunking Strategy
- api_specs: max 1200 chars, overlap 150 (small for table granularity)
- dev_guides: max 1800 chars, overlap 200 (preserve code examples)
- setup_certs: max 2000 chars, overlap 200 (keep steps together)
- Final `_hard_split()` enforcement pass catches oversized chunks

## Key Bugs Fixed
1. NaN embeddings from multilingual-e5-large → switched model
2. Ollama `/api/embed` with list input concatenates tokens → use single-text calls
3. Chunks exceeding max_chars from sentence-splitting path → added enforcement pass

## Pending
- Fix Qdrant MCP server (npm peer dependency conflict)
- Build `query_arca.py` CLI for Claude Code to search during dev sessions
- Cross-collection unified search
- Reranking layer for precision improvement

## Filtered Search Works
- `ws_name` filter: wsfev1, wsmtxca, wsaa, wsbfev1, wsseg, wsct, wsfexv1
- `environment` filter: produccion, testing, general
- `procedure_type` filter: cert_generation, cert_association, ws_delegation, etc.
