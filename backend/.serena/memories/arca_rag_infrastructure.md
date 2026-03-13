# ARCA RAG Infrastructure Reference

## Quick Start
- Qdrant: Docker `qdrant-gravitea`, ports 6333/6334
- Ollama: localhost:11434, model `nomic-embed-text` (768 dims)
- 3 collections: arca_api_specs (1151), arca_dev_guides (1088), arca_setup_certs (65)

## Search Pattern
```python
# Embed query
resp = requests.post("http://localhost:11434/api/embed",
    json={"model": "nomic-embed-text", "input": "search_query: YOUR QUERY"})
emb = resp.json()["embeddings"][0]

# Search with optional filter
resp = requests.post("http://localhost:6333/collections/COLLECTION/points/search",
    json={"vector": emb, "limit": 5, "with_payload": True,
          "filter": {"must": [{"key": "ws_name", "match": {"value": "wsfev1"}}]}})
```

## Useful Filters
| Collection | Field | Values |
|-----------|-------|--------|
| api_specs | ws_name | wsaa, wsfev1, wsmtxca, wsbfev1, wsseg |
| dev_guides | ws_name | wsaa, wsfev1, wsmtxca, wsbfev1, wsseg, wsct, wsfexv1 |
| setup_certs | environment | produccion, testing, general |

## Ingestion Script
```bash
python3 scripts/ingest_arca_qdrant.py                    # all
python3 scripts/ingest_arca_qdrant.py --collection NAME  # one
python3 scripts/ingest_arca_qdrant.py --dry-run          # validate
```

## Do NOT Use
- `zylonai/multilingual-e5-large` → NaN embeddings
- Ollama batch embedding (list input) → concatenates tokens, use single calls
- `mxbai-embed-large` → 512 token ctx limit, chunks exceed it
