"""
ARCA Documentation Ingestion Script for Qdrant RAG
===================================================
Thin wrapper around rag_common — keeps only the ARCA file-to-collection
mapping and orchestration logic.

Collections:
  - arca_api_specs: Technical specs, error codes, validation rules
  - arca_dev_guides: Developer manuals, code examples, workflows
  - arca_setup_certs: Certificate setup, environment procedures

Usage:
  python scripts/qdrant/ingest_arca_qdrant.py [--collection NAME] [--dry-run]
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
log = logging.getLogger("ingest-arca")

DOCS_ROOT = find_project_root() / "Docs" / "ARCA"

# ---------------------------------------------------------------------------
# File -> Collection mapping with metadata
# ---------------------------------------------------------------------------

COLLECTION_MAP: dict[str, list[dict]] = {
    "arca_api_specs": [
        {"path": "WSAA/Especificacion_Tecnica_WSAA_1.2.2.pdf", "ws_name": "wsaa", "rg_number": "", "doc_type": "technical_spec"},
        {"path": "WS factura electrónica/wsfev1-RG-4291.pdf", "ws_name": "wsfev1", "rg_number": "RG-4291", "doc_type": "technical_spec"},
        {"path": "WS factura electrónica/wsmtxca-RG-2904.pdf", "ws_name": "wsmtxca", "rg_number": "RG-2904", "doc_type": "technical_spec"},
        {"path": "WS factura electrónica/wsbfev1-RG-5427-y-2861.pdf", "ws_name": "wsbfev1", "rg_number": "RG-5427/2861", "doc_type": "technical_spec"},
        {"path": "WS factura electrónica/wsseg-RG-2668.pdf", "ws_name": "wsseg", "rg_number": "RG-2668", "doc_type": "technical_spec"},
        # Grain services
        {"path": "WS Padrón/manual_ws_sr_padron_a4_v1.3.pdf", "ws_name": "ws_sr_padron_a4", "rg_number": "", "doc_type": "technical_spec"},
        {"path": "WS Padrón/manual_ws_sr_ws_constancia_inscripcion.pdf", "ws_name": "ws_sr_constancia_inscripcion", "rg_number": "", "doc_type": "technical_spec"},
        {"path": "SIRE/SIRE-especificacion-para-emision-por-lote.pdf", "ws_name": "sire", "rg_number": "", "doc_type": "technical_spec"},
    ],
    "arca_dev_guides": [
        {"path": "WS factura electrónica/manual-desarrollador-ARCA-COMPG-v4-1.pdf", "ws_name": "wsfev1", "version": "v4.1", "doc_type": "developer_manual"},
        {"path": "WSAA/WSAAmanualDev.pdf", "ws_name": "wsaa", "version": "v20.2.19", "doc_type": "developer_manual"},
        {"path": "WS factura electrónica/WSFEX-Manualparaeldesarrollador_V3.1.1_ARCA.pdf", "ws_name": "wsfexv1", "version": "v3.1.1", "doc_type": "developer_manual"},
        {"path": "WS factura electrónica/WSBFEV1-ManualParaElDesarrollador_ARCA_V3_0.pdf", "ws_name": "wsbfev1", "version": "v3.0", "doc_type": "developer_manual"},
        {"path": "WS factura electrónica/WSSEG-ManualParaElDesarrollador_ARCA.pdf", "ws_name": "wsseg", "version": "", "doc_type": "developer_manual"},
        {"path": "WS factura electrónica/Manual_Desarrollador_WSCT_v1.6.4.pdf", "ws_name": "wsct", "version": "v1.6.4", "doc_type": "developer_manual"},
        {"path": "WS factura electrónica/Web-Service-MTXCA-v25.pdf", "ws_name": "wsmtxca", "version": "v25", "doc_type": "developer_manual"},
        # Grain services
        {"path": "WSLPG/manual_wslpg_1.24.pdf", "ws_name": "wslpg", "version": "v1.24", "doc_type": "developer_manual"},
        {"path": "WSCPE/manual-wscpe.pdf", "ws_name": "wscpe", "version": "", "doc_type": "developer_manual"},
        {"path": "SIRE/manualSIRE.pdf", "ws_name": "sire", "version": "", "doc_type": "developer_manual"},
        {"path": "SIRE/SOAP-SIRE-IVA-Manualparaeldesarrollador_V1_0_0.pdf", "ws_name": "sire_iva", "version": "v1.0.0", "doc_type": "developer_manual"},
        {"path": "SIRE/Preguntas-Frecuentes-Importacion-Lote.pdf", "ws_name": "sire", "version": "", "doc_type": "faq"},
        {"path": "WSCDC/WSCDC-manual-desarrollador-v4.pdf", "ws_name": "wscdc", "version": "v4", "doc_type": "developer_manual"},
        {"path": "Preguntas-Frecuentes-WS.pdf", "ws_name": "general", "version": "", "doc_type": "faq"},
    ],
    "arca_setup_certs": [
        {"path": "Certificados/Produccion/WSAA.ObtenerCertificado.pdf", "environment": "produccion", "procedure_type": "cert_generation"},
        {"path": "WSAA/wsaa_obtener_certificado_produccion.pdf", "environment": "produccion", "procedure_type": "cert_generation"},
        {"path": "WSAA/wsaa_asociar_certificado_a_wsn_produccion.pdf", "environment": "produccion", "procedure_type": "cert_association"},
        {"path": "Certificados/Produccion/ADMINREL.DelegarWS.pdf", "environment": "produccion", "procedure_type": "ws_delegation"},
        {"path": "Certificados/Testing/WSASS_como_adherirse.pdf", "environment": "testing", "procedure_type": "testing_enrollment"},
        {"path": "Certificados/Testing/WSASS_manual.pdf", "environment": "testing", "procedure_type": "testing_management"},
        {"path": "Arquitectura/Arquitectura - Documentación - WEB SERVICES SOAP _ ARCA.pdf", "environment": "general", "procedure_type": "architecture_overview"},
        {"path": "Cronograma TLS/Cronograma TLS - Documentación - WEB SERVICES SOAP _ ARCA.pdf", "environment": "general", "procedure_type": "tls_migration"},
    ],
}

ARCA_COLLECTIONS = list(COLLECTION_MAP.keys())


def ingest_file(collection: str, file_config: dict, dry_run: bool = False) -> int:
    """Ingest a single PDF into a Qdrant collection. Returns chunk count."""
    rel_path = file_config["path"]
    pdf_path = DOCS_ROOT / rel_path

    if not pdf_path.exists():
        log.warning("File not found: %s", pdf_path)
        return 0

    log.info("  Reading: %s", rel_path)
    pages = extract_pages(pdf_path)
    if not pages:
        log.warning("  No extractable text in %s", rel_path)
        return 0
    log.info("  Extracted %d pages with text", len(pages))

    # Build breadcrumbs using ws_name as doc title when available
    doc_title = file_config.get("ws_name", "")
    breadcrumbs = build_page_breadcrumbs(pages, doc_title=doc_title)

    # Chunk with contextual breadcrumbs
    chunks = chunk_pages(pages, collection, breadcrumbs)
    log.info("  Created %d chunks", len(chunks))

    if dry_run:
        for c in chunks[:3]:
            log.info("    [p%d] %s... (%d chars)", c["page"], c["text"][:80], len(c["text"]))
        return len(chunks)

    # Embed context_text (breadcrumb + raw) instead of raw text
    model_name = COLLECTION_REGISTRY[collection].model.name
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
            "collection": collection,
        }
        for key in ("ws_name", "rg_number", "doc_type", "version", "environment", "procedure_type"):
            if key in file_config:
                payload[key] = file_config[key]

        point_id = generate_point_id(rel_path, chunk["page"], chunk["chunk_index"])
        points.append({"id": point_id, "vector": embedding, "payload": payload})

    ensure_collection_exists(collection)
    log.info("  Upserting %d points to %s...", len(points), collection)
    upsert_to_qdrant(collection, points)
    return len(points)


def ingest_collection(collection: str, dry_run: bool = False) -> dict:
    """Ingest all files for a collection."""
    files = COLLECTION_MAP.get(collection, [])
    if not files:
        log.error("Unknown collection: %s", collection)
        return {"collection": collection, "total_chunks": 0, "files": 0}

    cfg = COLLECTION_REGISTRY[collection]
    log.info("=" * 60)
    log.info("Collection: %s (%d files)", collection, len(files))
    log.info("Chunk config: max=%d, overlap=%d", cfg.chunk_config.max_chars, cfg.chunk_config.overlap_chars)
    log.info("=" * 60)

    total_chunks = 0
    processed_files = 0
    for file_config in files:
        count = ingest_file(collection, file_config, dry_run=dry_run)
        total_chunks += count
        if count > 0:
            processed_files += 1

    log.info("-" * 40)
    log.info("Collection %s: %d chunks from %d files", collection, total_chunks, processed_files)
    return {"collection": collection, "total_chunks": total_chunks, "files": processed_files}


def main():
    parser = argparse.ArgumentParser(description="Ingest ARCA PDFs into Qdrant")
    parser.add_argument(
        "--collection",
        choices=ARCA_COLLECTIONS + ["all"],
        default="all",
        help="Which collection to ingest (default: all)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview chunks without embedding/upserting")
    args = parser.parse_args()

    log.info("ARCA Documentation Ingestion")
    log.info("Docs root: %s", DOCS_ROOT)

    model_name = COLLECTION_REGISTRY["arca_api_specs"].model.name
    if not verify_services(model_name):
        if not args.dry_run:
            log.error("Services not ready. Aborting.")
            sys.exit(1)
        log.warning("Services not ready, but continuing with --dry-run")

    collections = ARCA_COLLECTIONS if args.collection == "all" else [args.collection]

    results = []
    start = time.time()
    for collection in collections:
        result = ingest_collection(collection, dry_run=args.dry_run)
        results.append(result)

    elapsed = time.time() - start
    log.info("")
    log.info("=" * 60)
    log.info("INGESTION COMPLETE (%.1fs)", elapsed)
    log.info("=" * 60)
    total = 0
    for r in results:
        log.info("  %s: %d chunks from %d files", r["collection"], r["total_chunks"], r["files"])
        total += r["total_chunks"]
    log.info("  TOTAL: %d chunks", total)
    if args.dry_run:
        log.info("  (DRY RUN - no data was written)")


if __name__ == "__main__":
    main()
