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
import json
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


def format_results_json(results: list[SearchResult], query: str) -> str:
    """Format re-ranked results as JSON for programmatic consumption."""
    return json.dumps({
        "query": query,
        "results": [
            {
                "collection": r.collection,
                "score": round(r.score, 4),
                "ranked_score": round(r.boosted_score, 4),
                "source_file": r.source_file,
                "section": r.section,
                "breadcrumb": r.breadcrumb,
                "text": r.text,
                "topic": r.payload.get("topic", ""),
                "subtopic": r.payload.get("subtopic", ""),
                "priority": r.payload.get("priority", ""),
            }
            for r in results
        ],
    }, indent=2, ensure_ascii=False)


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
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON for programmatic consumption")
    parser.add_argument("--output", "-o", default=None, metavar="FILE", help="Write output to FILE instead of stdout")

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

    # Verify Qdrant reachability and filter out missing collections
    try:
        resp = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        resp.raise_for_status()
        existing = {c["name"] for c in resp.json()["result"]["collections"]}
        missing = [name for name in target_names if name not in existing]
        if missing:
            if args.collection:
                # Explicit collection requested but not found — hard fail
                print(f"ERROR: Collection not found in Qdrant: {args.collection}", file=sys.stderr)
                sys.exit(1)
            # Auto-routed: skip missing collections gracefully
            print(f"[Skip] Collections not found: {', '.join(missing)}", file=sys.stderr)
            targets = [t for t in targets if t.collection in existing]
            if not targets:
                print("ERROR: No valid collections available after filtering", file=sys.stderr)
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
            raw_text = _format_raw_results(raw, target.collection, args.query)
            if args.output:
                os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
                mode = "a" if len(targets) > 1 else "w"
                with open(args.output, mode, encoding="utf-8") as f:
                    f.write(raw_text)
                    f.write("\n")
            else:
                print(raw_text)
            continue

        results = _qdrant_results_to_search_results(raw, target.collection)
        all_search_results.extend(results)

    if args.raw:
        if args.output and len(targets) > 0:
            print(f"[Saved] {args.output}", file=sys.stderr)
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
    if args.json_output:
        output_text = format_results_json(ranked, args.query)
    else:
        output_text = format_results(ranked, args.query, show_collection=show_multi)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_text)
            f.write("\n")
        print(f"[Saved] {args.output}", file=sys.stderr)
    else:
        print(output_text)


if __name__ == "__main__":
    main()
