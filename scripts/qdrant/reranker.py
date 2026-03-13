"""
Re-ranker for GRAVITEA-ERP Qdrant Pipeline
===========================================
Merges, normalizes, boosts, deduplicates, and re-ranks search results
from multiple collections with different embedding models.

No LLM dependency — pure Python scoring with SequenceMatcher dedup.
"""

from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class SearchResult:
    collection: str
    score: float
    text: str
    source_file: str
    page: int
    section: str
    payload: dict
    breadcrumb: str = ""
    boosted_score: float = 0.0


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def normalize_scores(results: list[SearchResult]) -> list[SearchResult]:
    """Per-collection min-max normalization to [0, 1].

    Critical because qwen3 (~0.6-0.9) and nomic (~0.7-0.95) have
    different score ranges that aren't directly comparable.
    """
    # Group by collection
    by_collection: dict[str, list[SearchResult]] = {}
    for r in results:
        by_collection.setdefault(r.collection, []).append(r)

    for col, col_results in by_collection.items():
        scores = [r.score for r in col_results]
        min_s = min(scores)
        max_s = max(scores)
        spread = max_s - min_s
        if spread < 1e-9:
            # All scores identical — set to 0.5
            for r in col_results:
                r.boosted_score = 0.5
        else:
            for r in col_results:
                r.boosted_score = (r.score - min_s) / spread

    return results


def boost_keyword_matches(
    results: list[SearchResult], query: str
) -> list[SearchResult]:
    """Boost results that contain query keywords in text or section.

    +0.10 per keyword in text, +0.05 per keyword in section title.
    Capped at +0.30 total boost.
    """
    keywords = [w.lower() for w in query.split() if len(w) > 2]
    if not keywords:
        return results

    for r in results:
        boost = 0.0
        text_lower = r.text.lower()
        section_lower = r.section.lower()
        for kw in keywords:
            if kw in text_lower:
                boost += 0.10
            if kw in section_lower:
                boost += 0.05
        r.boosted_score += min(boost, 0.30)

    return results


def apply_collection_weights(
    results: list[SearchResult], weights: dict[str, float]
) -> list[SearchResult]:
    """Multiply boosted_score by per-collection weights from the router."""
    for r in results:
        w = weights.get(r.collection, 1.0)
        r.boosted_score *= w
    return results


def deduplicate(
    results: list[SearchResult], similarity_threshold: float = 0.85
) -> list[SearchResult]:
    """Remove near-duplicate results using SequenceMatcher on first 300 chars.

    Keeps the result with the higher boosted_score.
    """
    if not results:
        return results

    kept: list[SearchResult] = []
    for r in results:
        is_dup = False
        snippet = r.text[:300]
        for k in kept:
            ratio = SequenceMatcher(None, snippet, k.text[:300]).ratio()
            if ratio >= similarity_threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(r)
    return kept


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def rerank(
    results: list[SearchResult],
    query: str,
    collection_weights: dict[str, float] | None = None,
    top_k: int = 10,
    dedup: bool = True,
) -> list[SearchResult]:
    """Full re-ranking pipeline: normalize -> boost -> weight -> dedup -> sort -> truncate."""
    if not results:
        return []

    results = normalize_scores(results)
    results = boost_keyword_matches(results, query)
    if collection_weights:
        results = apply_collection_weights(results, collection_weights)
    if dedup:
        results = deduplicate(results)
    results.sort(key=lambda r: r.boosted_score, reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def format_results(
    results: list[SearchResult],
    query: str,
    show_collection: bool = False,
) -> str:
    """Format re-ranked results as plain text for agent consumption."""
    lines: list[str] = []
    lines.append("=== Qdrant Search Results ===")
    lines.append(f"Query: {query}")
    if show_collection:
        collections_hit = sorted({r.collection for r in results})
        lines.append(f"Collections: {', '.join(collections_hit)}")
    lines.append(f"Results: {len(results)}")
    lines.append("")

    for i, r in enumerate(results, 1):
        lines.append(f"--- Result {i} (score: {r.score:.4f}, ranked: {r.boosted_score:.4f}) ---")
        if show_collection:
            lines.append(f"Collection: {r.collection}")
        lines.append(f"Source: {r.source_file}")
        lines.append(f"Page: {r.page}")
        if r.section:
            lines.append(f"Section: {r.section}")
        if r.breadcrumb:
            lines.append(f"Context: {r.breadcrumb}")
        lines.append("Text:")
        lines.append(r.text)
        lines.append("")

    if not results:
        lines.append("No results found. Try broadening your query or using --all.")

    return "\n".join(lines)
