"""
Wiki Documentation Ingestion Script for Qdrant RAG
====================================================
Thin wrapper around rag_common — keeps only the wiki file list
and orchestration logic.

Collection:
  - wikis: General reference docs (Django, JWT, Rust)

Usage:
  python scripts/qdrant/ingest_wikis_qdrant.py [--dry-run]
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from rag_common import (
    COLLECTION_REGISTRY,
    build_page_breadcrumbs,
    chunk_pages,
    ensure_collection_exists,
    extract_pages,
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
log = logging.getLogger("ingest-wikis")

PROJECT_ROOT = find_project_root()
COLLECTION_NAME = "wikis"

# ---------------------------------------------------------------------------
# File map: path relative to PROJECT_ROOT, plus metadata per doc
# ---------------------------------------------------------------------------

WIKI_FILES: list[dict] = [
    {
        "path": "backend/Docs/django-readthedocs-io-en-5.2.x.pdf",
        "topic": "django",
        "doc_type": "framework_docs",
        "version": "5.2",
    },
    {
        "path": "Docs/Wikis/jwt-handbook-v0_14_2.pdf",
        "topic": "jwt",
        "doc_type": "security_handbook",
        "version": "0.14.2",
    },
    {
        "path": "Docs/Userguides/The Rust Programming Language.pdf",
        "topic": "rust",
        "doc_type": "language_reference",
        "version": "1.90.0",
    },
]


def ingest_file(file_config: dict, dry_run: bool = False) -> int:
    """Ingest a single PDF into the wikis collection. Returns chunk count."""
    rel_path = file_config["path"]
    pdf_path = PROJECT_ROOT / rel_path

    if not pdf_path.exists():
        log.warning("File not found: %s", pdf_path)
        return 0

    log.info("  Reading: %s (%.1f MB)", rel_path, pdf_path.stat().st_size / 1_048_576)
    pages = extract_pages(pdf_path)
    if not pages:
        log.warning("  No extractable text in %s", rel_path)
        return 0
    log.info("  Extracted %d pages with text", len(pages))

    # Build breadcrumbs using topic as doc title
    doc_title = file_config.get("topic", "")
    breadcrumbs = build_page_breadcrumbs(pages, doc_title=doc_title)

    # Chunk with contextual breadcrumbs
    chunks = chunk_pages(pages, COLLECTION_NAME, breadcrumbs)
    log.info("  Created %d chunks", len(chunks))

    if dry_run:
        for c in chunks[:3]:
            log.info("    [p%d] %s... (%d chars)", c["page"], c["text"][:80], len(c["text"]))
        if len(chunks) > 3:
            log.info("    ... and %d more chunks", len(chunks) - 3)
        return len(chunks)

    # Embed context_text (breadcrumb + raw) instead of raw text
    model_name = COLLECTION_REGISTRY[COLLECTION_NAME].model.name
    texts_to_embed = [c["context_text"] for c in chunks]
    log.info("  Generating embeddings (%d chunks)...", len(texts_to_embed))
    embeddings = get_embeddings_batch(texts_to_embed, model_name, mode="document")

    # Build Qdrant points
    points = []
    source_file = Path(rel_path).name
    for chunk, embedding in zip(chunks, embeddings):
        payload = {
            "text": chunk["text"],
            "source_file": source_file,
            "source_path": rel_path,
            "page": chunk["page"],
            "chunk_index": chunk["chunk_index"],
            "section": chunk["section"],
            "breadcrumb": chunk["breadcrumb"],
            "collection": COLLECTION_NAME,
            "topic": file_config["topic"],
            "doc_type": file_config["doc_type"],
            "version": file_config.get("version", ""),
        }

        point_id = generate_point_id(rel_path, chunk["page"], chunk["chunk_index"])
        points.append({"id": point_id, "vector": embedding, "payload": payload})

    log.info("  Upserting %d points to %s...", len(points), COLLECTION_NAME)
    upsert_to_qdrant(COLLECTION_NAME, points)
    return len(points)


def main():
    parser = argparse.ArgumentParser(
        description="Ingest wiki/reference PDFs into the Qdrant 'wikis' collection"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview chunks without embedding/upserting")
    args = parser.parse_args()

    log.info("Wiki Documentation Ingestion")
    log.info("Project root: %s", PROJECT_ROOT)

    cfg = COLLECTION_REGISTRY[COLLECTION_NAME]
    log.info("Collection: %s (chunk=%d, overlap=%d)", COLLECTION_NAME, cfg.chunk_config.max_chars, cfg.chunk_config.overlap_chars)

    model_name = cfg.model.name
    if not verify_services(model_name):
        if not args.dry_run:
            log.error("Services not ready. Aborting.")
            sys.exit(1)
        log.warning("Services not ready, but continuing with --dry-run")

    if not args.dry_run:
        ensure_collection_exists(COLLECTION_NAME)

    total_chunks = 0
    processed_files = 0
    start = time.time()

    log.info("=" * 60)
    log.info("Ingesting %d files into '%s'", len(WIKI_FILES), COLLECTION_NAME)
    log.info("=" * 60)

    for file_config in WIKI_FILES:
        count = ingest_file(file_config, dry_run=args.dry_run)
        total_chunks += count
        if count > 0:
            processed_files += 1

    elapsed = time.time() - start
    log.info("")
    log.info("=" * 60)
    log.info("INGESTION COMPLETE (%.1fs)", elapsed)
    log.info("=" * 60)
    log.info("  Collection: %s", COLLECTION_NAME)
    log.info("  Files processed: %d/%d", processed_files, len(WIKI_FILES))
    log.info("  Total chunks: %d", total_chunks)
    if args.dry_run:
        log.info("  (DRY RUN - no data was written)")


if __name__ == "__main__":
    main()
