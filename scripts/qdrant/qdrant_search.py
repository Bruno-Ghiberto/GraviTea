#!/usr/bin/env python3
"""
Modular RAG Search Pipeline for GRAVITEA-ERP
=============================================
Orchestrates: route -> expand -> embed -> search -> rerank -> format.

Auto-routes queries to relevant collections when --collection is omitted.
Backward compatible: explicit --collection still works exactly as before.

Usage:
    # Auto-routed (new default)
    python scripts/qdrant/qdrant_search.py -q "FECAESolicitar parametros"

    # Explicit collection (backward compat)
    python scripts/qdrant/qdrant_search.py -q "FECAESolicitar" -c arca_api_specs -l 5

    # Search all collections
    python scripts/qdrant/qdrant_search.py -q "certificado digital" --all

    # Disable expansion, skip re-ranking
    python scripts/qdrant/qdrant_search.py -q "Django ORM" --no-expand --raw
"""

import argparse
import os
import sys

# Fix Windows cp1252 encoding issues with Unicode content from Qdrant
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

from rag_common import (
    ALL_COLLECTION_NAMES,
    QDRANT_URL,
    OLLAMA_URL,
    get_embedding,
    parse_filters,
    resolve_model_for_collection,
    search_qdrant,
    verify_services,
)
from query_router import route_query
from query_expander import expand_query
from reranker import SearchResult, rerank, format_results


def _qdrant_results_to_search_results(
    raw: dict, collection: str
) -> list[SearchResult]:
    """Convert raw Qdrant response to SearchResult objects."""
    results: list[SearchResult] = []
    for hit in raw.get("result", []):
        payload = hit.get("payload", {})
        results.append(SearchResult(
            collection=collection,
            score=hit["score"],
            text=payload.get("text", ""),
            source_file=payload.get("source_file", "unknown"),
            page=payload.get("page", 0),
            section=payload.get("section", ""),
            payload=payload,
            breadcrumb=payload.get("breadcrumb", ""),
        ))
    return results


def _format_raw_results(raw: dict, collection: str, query: str) -> str:
    """Format raw Qdrant results (skip re-ranking) — backward compat output."""
    lines: list[str] = []
    lines.append("=== Qdrant Search Results ===")
    lines.append(f"Collection: {collection}")
    lines.append(f"Query: {query}")
    lines.append(f"Results: {len(raw.get('result', []))}")
    lines.append("")

    for i, hit in enumerate(raw.get("result", []), 1):
        score = hit["score"]
        payload = hit.get("payload", {})
        lines.append(f"--- Result {i} (score: {score:.4f}) ---")
        lines.append(f"Source: {payload.get('source_file', 'unknown')}")
        lines.append(f"Page: {payload.get('page', '?')}")
        section = payload.get("section", "")
        if section:
            lines.append(f"Section: {section}")
        breadcrumb = payload.get("breadcrumb", "")
        if breadcrumb:
            lines.append(f"Context: {breadcrumb}")
        lines.append("Text:")
        lines.append(payload.get("text", ""))
        lines.append("")

    if not raw.get("result"):
        lines.append("No results found. Try broadening your query or checking the collection name.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search documentation in Qdrant (Modular RAG pipeline).",
        epilog=(
            "Examples:\n"
            "  python scripts/qdrant/qdrant_search.py -q 'FECAESolicitar'\n"
            "  python scripts/qdrant/qdrant_search.py -q 'Django ORM' -c wikis\n"
            "  python scripts/qdrant/qdrant_search.py -q 'certificado' --all\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--query", "-q", required=True, help="Search query text")
    parser.add_argument(
        "--collection", "-c",
        choices=ALL_COLLECTION_NAMES,
        default=None,
        help="Qdrant collection (omit for auto-routing)",
    )
    parser.add_argument("--limit", "-l", type=int, default=5, help="Results per collection (default: 5)")
    parser.add_argument("--filter", "-f", action="append", dest="filters", metavar="KEY=VALUE", help="Payload filter (repeatable)")
    parser.add_argument("--all", action="store_true", dest="search_all", help="Search ALL collections")
    parser.add_argument("--no-expand", action="store_true", help="Disable query expansion")
    parser.add_argument("--raw", action="store_true", help="Skip re-ranking, show raw per-collection results")

    args = parser.parse_args()

    # --- Step 1: Route ---
    filters = parse_filters(args.filters)
    targets = route_query(
        args.query,
        explicit_collection=args.collection,
        explicit_filters=filters,
        search_all=args.search_all,
    )
    target_names = [t.collection for t in targets]

    # Verify Qdrant reachability
    try:
        resp = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        resp.raise_for_status()
        existing = {c["name"] for c in resp.json()["result"]["collections"]}
        missing = [name for name in target_names if name not in existing]
        if missing:
            print(f"ERROR: Collections not found in Qdrant: {', '.join(missing)}", file=sys.stderr)
            sys.exit(1)
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to Qdrant at {QDRANT_URL}", file=sys.stderr)
        sys.exit(1)

    # --- Step 2: Expand query ---
    search_query = args.query if args.no_expand else expand_query(args.query)
    if search_query != args.query:
        print(f"[Expanded] {search_query}", file=sys.stderr)

    # Show routing info
    if not args.collection:
        route_info = ", ".join(f"{t.collection}(w={t.weight:.1f})" for t in targets)
        print(f"[Routed] {route_info}", file=sys.stderr)

    # --- Step 3: Embed + Search (with cache for same model) ---
    embedding_cache: dict[str, list[float]] = {}  # model_name -> embedding
    all_search_results: list[SearchResult] = []

    for target in targets:
        model = resolve_model_for_collection(target.collection)

        # Reuse embedding if same model already computed
        if model not in embedding_cache:
            # Verify Ollama has this model
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
                r.raise_for_status()
                models = [m["name"] for m in r.json().get("models", [])]
                if model not in models and f"{model}:latest" not in models:
                    print(f"ERROR: Model '{model}' not found in Ollama", file=sys.stderr)
                    sys.exit(1)
            except requests.ConnectionError:
                print(f"ERROR: Cannot connect to Ollama at {OLLAMA_URL}", file=sys.stderr)
                sys.exit(1)

            embedding_cache[model] = get_embedding(search_query, model, mode="query")

        query_vector = embedding_cache[model]

        # Merge target filters with CLI filters
        search_filters = target.filters
        if filters:
            search_filters = {**(search_filters or {}), **filters}

        raw = search_qdrant(target.collection, query_vector, args.limit, search_filters)

        if args.raw:
            # Raw mode: print per-collection results and continue
            print(_format_raw_results(raw, target.collection, args.query))
            continue

        results = _qdrant_results_to_search_results(raw, target.collection)
        all_search_results.extend(results)

    if args.raw:
        return

    # --- Step 4: Re-rank ---
    collection_weights = {t.collection: t.weight for t in targets}
    show_multi = len(targets) > 1

    ranked = rerank(
        all_search_results,
        args.query,
        collection_weights=collection_weights,
        top_k=args.limit,
        dedup=show_multi,
    )

    # --- Step 5: Format + output ---
    print(format_results(ranked, args.query, show_collection=show_multi))


if __name__ == "__main__":
    main()
