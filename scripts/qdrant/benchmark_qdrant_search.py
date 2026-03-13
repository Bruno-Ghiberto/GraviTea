"""
Benchmark Qdrant search quality with qwen3-embedding:4b
Compares against baseline scores from nomic-embed-text.

Uses rag_common for embedding and search — no duplicated helpers.
"""

import time

import requests

from rag_common import (
    QDRANT_URL,
    OLLAMA_URL,
    MODELS,
    get_embedding,
    search_qdrant,
)

OLLAMA_MODEL = MODELS["qwen3"].name

# Baseline queries with expected behavior from nomic-embed-text
BASELINE_QUERIES = [
    {
        "query": "codigos de error en factura electronica",
        "collection": "arca_api_specs",
        "baseline_score": 0.73,
        "expected_source": "error codes, validation rules",
    },
    {
        "query": "como generar ticket de acceso WSAA",
        "collection": "arca_dev_guides",
        "baseline_score": 0.77,
        "expected_source": "WSAA authentication flow",
    },
    {
        "query": "obtener certificado digital para produccion",
        "collection": "arca_setup_certs",
        "baseline_score": 0.80,
        "expected_source": "certificate generation procedures",
    },
    {
        "query": "FECAESolicitar parametros obligatorios",
        "collection": "arca_api_specs",
        "baseline_score": 0.74,
        "expected_source": "WSFEv1 method specification",
    },
    {
        "query": "tipos de comprobante permitidos",
        "collection": "arca_api_specs",
        "baseline_score": 0.81,
        "expected_source": "CbteTipo enumeration",
    },
]


def benchmark_query(query_data: dict) -> dict:
    """Run single benchmark query and return results."""
    query = query_data["query"]
    collection = query_data["collection"]
    baseline = query_data["baseline_score"]

    print(f"\nQuery: '{query}'")
    print(f"Collection: {collection}")
    print(f"Baseline (nomic-embed-text): {baseline:.3f}")

    start_time = time.time()
    embedding = get_embedding(query, OLLAMA_MODEL, mode="query")
    embed_time = time.time() - start_time

    start_time = time.time()
    results = search_qdrant(collection, embedding, limit=3)
    search_time = time.time() - start_time

    if results["result"]:
        top_result = results["result"][0]
        score = top_result["score"]
        source = top_result["payload"]["source_file"]
        section = top_result["payload"].get("section", "")
        text_preview = top_result["payload"]["text"][:120]

        improvement = ((score - baseline) / baseline) * 100

        print(f"qwen3-embedding:4b: {score:.3f} ({improvement:+.1f}% vs baseline)")
        print(f"Source: {source}")
        if section:
            print(f"Section: {section}")
        print(f"Preview: {text_preview}...")
        print(f"Timings: embed={embed_time:.3f}s, search={search_time:.3f}s")

        return {
            "query": query,
            "baseline": baseline,
            "score": score,
            "improvement_pct": improvement,
            "source": source,
            "embed_time": embed_time,
            "search_time": search_time,
            "correct": True,
        }
    else:
        print("No results found!")
        return {
            "query": query,
            "baseline": baseline,
            "score": 0.0,
            "improvement_pct": -100.0,
            "source": "NONE",
            "embed_time": embed_time,
            "search_time": search_time,
            "correct": False,
        }


def main():
    print("=" * 80)
    print("Qdrant Search Quality Benchmark")
    print(f"Model: {OLLAMA_MODEL} (Qwen3-embedding 4B, 2560 dims)")
    print("=" * 80)

    # Verify services
    try:
        resp = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        resp.raise_for_status()
        collections = [c["name"] for c in resp.json()["result"]["collections"]]
        print(f"\nQdrant collections: {', '.join(collections)}")
    except Exception as e:
        print(f"Error: Qdrant not reachable: {e}")
        return

    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        if OLLAMA_MODEL not in models and f"{OLLAMA_MODEL}:latest" not in models:
            print(f"Error: Model {OLLAMA_MODEL} not found in Ollama")
            return
        print(f"Ollama model: {OLLAMA_MODEL}")
    except Exception as e:
        print(f"Error: Ollama not reachable: {e}")
        return

    # Run benchmarks
    results = []
    for query_data in BASELINE_QUERIES:
        result = benchmark_query(query_data)
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    avg_baseline = sum(r["baseline"] for r in results) / len(results)
    avg_new = sum(r["score"] for r in results) / len(results)
    avg_improvement = ((avg_new - avg_baseline) / avg_baseline) * 100

    print(f"\nAverage scores:")
    print(f"  nomic-embed-text (baseline):     {avg_baseline:.3f}")
    print(f"  qwen3-embedding:4b:               {avg_new:.3f} ({avg_improvement:+.1f}%)")

    print(f"\nScore improvements:")
    for r in results:
        status = "+" if r["correct"] else "x"
        print(f"  {status} {r['query'][:50]:50s} {r['improvement_pct']:+6.1f}%")

    print(f"\nTimings:")
    avg_embed = sum(r["embed_time"] for r in results) / len(results)
    avg_search = sum(r["search_time"] for r in results) / len(results)
    print(f"  Average embedding time: {avg_embed:.3f}s")
    print(f"  Average search time:    {avg_search:.3f}s")

    print(f"\nExpected improvement: 0.73-0.81 -> 0.80-0.93 (research prediction)")
    print(f"Actual improvement:   {avg_baseline:.2f} -> {avg_new:.2f}")

    if avg_new >= 0.80:
        print(f"\n+ Performance meets research expectations!")
    else:
        print(f"\n! Performance below expectations (target: >=0.80, got: {avg_new:.2f})")


if __name__ == "__main__":
    main()
