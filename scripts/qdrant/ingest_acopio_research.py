"""
Acopio Research Markdown Ingestion Script for Qdrant RAG
========================================================
Thin wrapper around rag_common -- keeps only the topic/metadata mapping
and orchestration logic for the markdown research corpus.

Collection:
  - acopio_research: 30 research documents on grain handling, regulation,
    operations, market analysis, and data models.

Usage:
  python scripts/qdrant/ingest_acopio_research.py [--dry-run] [--file FILENAME]
"""

import argparse
import logging
import re
import sys
import time
from pathlib import Path

from rag_common import (
    COLLECTION_REGISTRY,
    build_markdown_breadcrumbs,
    chunk_markdown_sections,
    ensure_collection_exists,
    extract_markdown_sections,
    find_project_root,
    generate_point_id,
    get_embeddings_batch,
    upsert_to_qdrant,
    verify_services,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest-acopio")

PROJECT_ROOT = find_project_root()
DOCS_ROOT = PROJECT_ROOT / "Docs" / "Researches" / "Markdown"
COLLECTION_NAME = "acopio_research"

# ---------------------------------------------------------------------------
# Topic / subtopic / priority mapping from filename pattern X.Y
# ---------------------------------------------------------------------------

TOPIC_MAP: dict[str, tuple[str, dict[str, str]]] = {
    "1": ("regulatory", {
        "1": "ctg", "2": "wscpe", "3": "liquidacion_1116",
        "4": "registro_operadores", "5": "provincial_taxes", "6": "ley_granos",
    }),
    "2": ("operations", {
        "1": "daily_workflow", "2": "quality_standards", "3": "producer_accounts",
        "4": "pricing_contracts", "5": "merma", "6": "campaign",
    }),
    "3": ("infrastructure", {"1": "weighbridge", "2": "lab_equipment"}),
    "4": ("market", {"1": "software_map", "2": "agis_competitive", "3": "pain_points"}),
    "5": ("afip_services", {"1": "wslpg", "2": "integration_architecture"}),
    "6": ("go_to_market", {"1": "market_sizing", "2": "accountant_channel", "3": "trade_associations"}),
    "7": ("financial", {"1": "chart_of_accounts", "2": "inventory_valuation", "3": "withholding_taxes"}),
    "8": ("data_model", {"1": "grain_types", "2": "ctg_state_machine", "3": "romaneo", "4": "form_1116_fields"}),
    "9": ("ai_ml", {"1": "grain_storage_ai"}),
    "10": ("open_source", {"1": "afip_libraries"}),
}

PRIORITY_MAP: dict[str, str] = {
    "1.1": "P0", "1.2": "P0", "1.3": "P0", "1.4": "P1", "1.5": "P1", "1.6": "P2",
    "2.1": "P0", "2.2": "P0", "2.3": "P0", "2.4": "P1", "2.5": "P1", "2.6": "P1",
    "3.1": "P1", "3.2": "P2",
    "4.1": "P0", "4.2": "P0", "4.3": "P1",
    "5.1": "P0", "5.2": "P1",
    "6.1": "P0", "6.2": "P1", "6.3": "P2",
    "7.1": "P1", "7.2": "P1", "7.3": "P0",
    "8.1": "P0", "8.2": "P0", "8.3": "P1", "8.4": "P0",
    "9.1": "P2",
    "10.1": "P1",
}

# Regex to parse "X.Y Title.md" where X can be multi-digit (e.g. 10.1)
_FILENAME_RE = re.compile(r"^(\d+)\.(\d+)\s+.+\.md$")


def detect_metadata(filename: str) -> dict[str, str]:
    """Parse 'X.Y Title.md' and return topic, subtopic, priority, source_file.

    Falls back to sensible defaults when the filename does not match
    the expected pattern or the major/minor numbers are not in the maps.
    """
    result: dict[str, str] = {
        "topic": "unknown",
        "subtopic": "unknown",
        "priority": "P2",
        "source_file": filename,
    }

    m = _FILENAME_RE.match(filename)
    if not m:
        log.warning("Filename '%s' does not match X.Y pattern, using defaults", filename)
        return result

    major = m.group(1)
    minor = m.group(2)
    file_key = f"{major}.{minor}"

    topic_entry = TOPIC_MAP.get(major)
    if topic_entry:
        topic_name, subtopic_map = topic_entry
        result["topic"] = topic_name
        result["subtopic"] = subtopic_map.get(minor, "unknown")
    else:
        log.warning("Unknown major topic '%s' in filename '%s'", major, filename)

    result["priority"] = PRIORITY_MAP.get(file_key, "P2")

    return result


# ---------------------------------------------------------------------------
# Per-file ingestion
# ---------------------------------------------------------------------------


def ingest_file(md_path: Path, dry_run: bool = False) -> int:
    """Ingest a single markdown file into the acopio_research collection.

    Returns the number of chunks produced.
    """
    filename = md_path.name
    metadata = detect_metadata(filename)

    log.info("  Reading: %s (%.1f KB)", filename, md_path.stat().st_size / 1024)
    log.info("    topic=%s  subtopic=%s  priority=%s",
             metadata["topic"], metadata["subtopic"], metadata["priority"])

    sections = extract_markdown_sections(md_path)
    if not sections:
        log.warning("  No sections extracted from %s", filename)
        return 0
    log.info("  Extracted %d sections", len(sections))

    breadcrumbs = build_markdown_breadcrumbs(sections)
    chunks = chunk_markdown_sections(sections, COLLECTION_NAME, breadcrumbs)
    log.info("  Created %d chunks", len(chunks))

    if dry_run:
        for c in chunks[:3]:
            section_label = c["section"][:40] if c["section"] else "(no heading)"
            log.info("    [%s] %s... (%d chars)",
                     section_label, c["text"][:80], len(c["text"]))
        if len(chunks) > 3:
            log.info("    ... and %d more chunks", len(chunks) - 3)
        return len(chunks)

    # Embed context_text (breadcrumb + raw) instead of raw text
    model_name = COLLECTION_REGISTRY[COLLECTION_NAME].model.name
    texts_to_embed = [c["context_text"] for c in chunks]
    log.info("  Generating embeddings (%d chunks)...", len(texts_to_embed))
    embeddings = get_embeddings_batch(texts_to_embed, model_name, mode="document")

    # Build Qdrant points
    points: list[dict] = []
    for chunk, embedding in zip(chunks, embeddings):
        payload: dict[str, str | int] = {
            "text": chunk["text"],
            "source_file": filename,
            "topic": metadata["topic"],
            "subtopic": metadata["subtopic"],
            "priority": metadata["priority"],
            "section": chunk["section"],
            "breadcrumb": chunk["breadcrumb"],
            "chunk_index": chunk["chunk_index"],
            "collection": COLLECTION_NAME,
        }

        point_id = generate_point_id(filename, chunk["page"], chunk["chunk_index"])
        points.append({"id": point_id, "vector": embedding, "payload": payload})

    log.info("  Upserting %d points to %s...", len(points), COLLECTION_NAME)
    upsert_to_qdrant(COLLECTION_NAME, points)
    return len(points)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest acopio research markdown files into Qdrant"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview chunks without embedding/upserting",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Ingest a single file by name (e.g. '2.1 Day-to-Day Operations of an Acopiador.md')",
    )
    args = parser.parse_args()

    log.info("Acopio Research Ingestion")
    log.info("Docs root: %s", DOCS_ROOT)

    if not DOCS_ROOT.exists():
        log.error("Research directory not found: %s", DOCS_ROOT)
        sys.exit(1)

    cfg = COLLECTION_REGISTRY[COLLECTION_NAME]
    log.info("Collection: %s (chunk=%d, overlap=%d)",
             COLLECTION_NAME, cfg.chunk_config.max_chars, cfg.chunk_config.overlap_chars)

    model_name = cfg.model.name
    if not verify_services(model_name):
        if not args.dry_run:
            log.error("Services not ready. Aborting.")
            sys.exit(1)
        log.warning("Services not ready, but continuing with --dry-run")

    if not args.dry_run:
        ensure_collection_exists(COLLECTION_NAME)

    # Resolve file list
    if args.file:
        target = DOCS_ROOT / args.file
        if not target.exists():
            log.error("File not found: %s", target)
            sys.exit(1)
        md_files = [target]
    else:
        md_files = sorted(DOCS_ROOT.glob("*.md"))

    if not md_files:
        log.error("No markdown files found in %s", DOCS_ROOT)
        sys.exit(1)

    total_chunks = 0
    processed_files = 0
    skipped_files = 0
    start = time.time()

    log.info("=" * 60)
    log.info("Ingesting %d files into '%s'", len(md_files), COLLECTION_NAME)
    log.info("=" * 60)

    for md_path in md_files:
        try:
            count = ingest_file(md_path, dry_run=args.dry_run)
            total_chunks += count
            if count > 0:
                processed_files += 1
            else:
                skipped_files += 1
        except Exception:
            log.exception("  Failed to ingest %s", md_path.name)
            skipped_files += 1

    elapsed = time.time() - start
    log.info("")
    log.info("=" * 60)
    log.info("INGESTION COMPLETE (%.1fs)", elapsed)
    log.info("=" * 60)
    log.info("  Collection: %s", COLLECTION_NAME)
    log.info("  Files processed: %d/%d", processed_files, len(md_files))
    if skipped_files:
        log.info("  Files skipped: %d", skipped_files)
    log.info("  Total chunks: %d", total_chunks)
    if args.dry_run:
        log.info("  (DRY RUN - no data was written)")


if __name__ == "__main__":
    main()
