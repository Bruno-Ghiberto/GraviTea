"""
RAG Common Library for GRAVITEA-ERP Qdrant Pipeline
====================================================
Shared infrastructure for ingestion, embedding, chunking, and Qdrant operations.
Centralizes configuration, eliminates duplication across ingest scripts, and adds
contextual chunking with breadcrumb-based structural context.

Used by: ingest_arca_qdrant.py, ingest_wikis_qdrant.py, qdrant_search.py, benchmark
"""

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import requests

# ---------------------------------------------------------------------------
# URLs & HTTP session
# ---------------------------------------------------------------------------

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://172.26.176.1:11434")

# Reuse TCP connections via keep-alive — prevents Windows ephemeral port
# exhaustion (WinError 10048) when making hundreds of Ollama embed calls.
_session = requests.Session()

log = logging.getLogger("rag")

# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelConfig:
    name: str
    dims: int
    context_window: int
    doc_prefix: str
    query_prefix: str


@dataclass(frozen=True)
class ChunkConfig:
    max_chars: int
    overlap_chars: int


@dataclass(frozen=True)
class CollectionConfig:
    name: str
    model: ModelConfig
    chunk_config: ChunkConfig
    payload_indexes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

MODELS = {
    "qwen3": ModelConfig(
        name="qwen3-embedding:4b",
        dims=2560,
        context_window=32768,
        doc_prefix="search_document: ",
        query_prefix="search_query: ",
    ),
    "nomic": ModelConfig(
        name="nomic-embed-text",
        dims=768,
        context_window=8192,
        doc_prefix="search_document: ",
        query_prefix="search_query: ",
    ),
}

# ---------------------------------------------------------------------------
# Collection registry
# ---------------------------------------------------------------------------

COLLECTION_REGISTRY: dict[str, CollectionConfig] = {
    "arca_api_specs": CollectionConfig(
        name="arca_api_specs",
        model=MODELS["qwen3"],
        chunk_config=ChunkConfig(max_chars=1200, overlap_chars=150),
        payload_indexes=("ws_name", "section", "source_file"),
    ),
    "arca_dev_guides": CollectionConfig(
        name="arca_dev_guides",
        model=MODELS["qwen3"],
        chunk_config=ChunkConfig(max_chars=1800, overlap_chars=200),
        payload_indexes=("ws_name", "section", "source_file"),
    ),
    "arca_setup_certs": CollectionConfig(
        name="arca_setup_certs",
        model=MODELS["qwen3"],
        chunk_config=ChunkConfig(max_chars=2000, overlap_chars=200),
        payload_indexes=("environment", "procedure_type", "source_file"),
    ),
    "wikis": CollectionConfig(
        name="wikis",
        model=MODELS["nomic"],
        chunk_config=ChunkConfig(max_chars=2000, overlap_chars=250),
        payload_indexes=("topic", "doc_type", "source_file"),
    ),
}

# Auto-generated reverse lookup: dims -> model name
DIMS_TO_MODEL: dict[int, str] = {m.dims: m.name for m in MODELS.values()}

ALL_COLLECTION_NAMES = list(COLLECTION_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------


def find_project_root() -> Path:
    """Walk up from this file until we find CLAUDE.md (project root marker)."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "CLAUDE.md").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Cannot find project root (CLAUDE.md marker) within 5 levels")


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------


def extract_pages(pdf_path: Path) -> list[dict]:
    """Extract text from each page of a PDF, returning list of {page, text}."""
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()
        if text and len(text) > 30:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


# ---------------------------------------------------------------------------
# Section / heading detection
# ---------------------------------------------------------------------------

_HEADING_KEYWORDS = re.compile(
    r"^(Chapter|Section|Appendix|Part|"
    r"Método|Operación|Validacion|Error|Introducción|Descripción|"
    r"Capítulo|Sección|Apéndice|Anexo)",
    re.IGNORECASE,
)


def detect_section(text: str) -> str:
    """Try to detect the section heading from a text chunk."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        line = line.strip()
        if re.match(r"^(\d+\.?\d*\.?\d*)\s+\w", line) and len(line) < 120:
            return line
        if line.isupper() and 5 < len(line) < 100:
            return line
        if _HEADING_KEYWORDS.match(line):
            return line
    return ""


# ---------------------------------------------------------------------------
# Contextual chunking — breadcrumb tracking
# ---------------------------------------------------------------------------


class HeadingTracker:
    """Maintains a chapter > section > subsection breadcrumb stack."""

    def __init__(self) -> None:
        self._stack: list[str] = []  # index 0 = deepest heading seen at depth 0, etc.

    def update(self, depth: int, heading: str) -> None:
        """Push a heading at *depth* (0=chapter, 1=section, 2=subsection).

        Truncates everything deeper than *depth* and replaces that level.
        """
        # Extend stack if needed
        while len(self._stack) <= depth:
            self._stack.append("")
        self._stack[depth] = heading
        # Drop everything below this depth
        self._stack = self._stack[: depth + 1]

    @property
    def breadcrumb(self) -> str:
        """Return 'Chapter > Section > Subsection' string, skipping blanks."""
        parts = [h for h in self._stack if h]
        return " > ".join(parts) if parts else ""


def classify_heading_depth(line: str) -> tuple[int, str] | None:
    """Classify a line as a heading and return (depth, heading_text) or None.

    Depth mapping:
      0 — chapter-level: 'Chapter N', single top-level number ('1 Introduction'),
          all-caps long titles, 'Part N', 'Appendix A'
      1 — section-level:  '1.2 Something', 'Section N', keyword-only headings
      2 — subsection-level: '1.2.3 Something' or deeper numbered headings
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 150:
        return None

    # Numbered heading: 1, 1.2, 1.2.3, ...
    m = re.match(r"^(\d+(?:\.\d+)*)\s+(.+)", stripped)
    if m:
        numbers = m.group(1)
        title = m.group(2).strip()
        dot_count = numbers.count(".")
        if dot_count == 0:
            return (0, stripped)
        elif dot_count == 1:
            return (1, stripped)
        else:
            return (2, stripped)

    # ALL-CAPS titles (chapter-level)
    if stripped.isupper() and 5 < len(stripped) < 100:
        return (0, stripped)

    # Keyword-based
    kw = re.match(
        r"^(Chapter|Part|Appendix|Capítulo|Parte|Apéndice)\b",
        stripped,
        re.IGNORECASE,
    )
    if kw:
        return (0, stripped)

    kw = re.match(
        r"^(Section|Sección|Anexo)\b",
        stripped,
        re.IGNORECASE,
    )
    if kw:
        return (1, stripped)

    # Method/Operation headings common in ARCA docs
    kw = re.match(
        r"^(Método|Operación|Validacion|Error|Introducción|Descripción)\b",
        stripped,
        re.IGNORECASE,
    )
    if kw:
        return (1, stripped)

    return None


def build_page_breadcrumbs(
    pages: list[dict], doc_title: str = ""
) -> dict[int, str]:
    """Scan all pages and return {page_num: breadcrumb_string}.

    The breadcrumb for a page is the structural context at the START of that page.
    """
    tracker = HeadingTracker()
    if doc_title:
        tracker.update(0, doc_title)

    breadcrumbs: dict[int, str] = {}
    for page_data in pages:
        page_num = page_data["page"]
        # Record the breadcrumb BEFORE scanning this page's headings
        # so the breadcrumb reflects context from previous pages
        breadcrumbs[page_num] = tracker.breadcrumb

        # Scan lines for headings and update tracker
        for raw_line in page_data["text"].split("\n"):
            result = classify_heading_depth(raw_line)
            if result:
                depth, heading = result
                tracker.update(depth, heading)
        # Update this page's breadcrumb AFTER scanning (captures same-page headings)
        breadcrumbs[page_num] = tracker.breadcrumb

    return breadcrumbs


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


def _hard_split(text: str, max_chars: int) -> list[str]:
    """Last-resort hard split by lines, then by character boundary."""
    parts: list[str] = []
    lines = text.split("\n")
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_chars:
            if current.strip():
                parts.append(current.strip())
            if len(line) > max_chars:
                for i in range(0, len(line), max_chars):
                    parts.append(line[i : i + max_chars].strip())
                current = ""
            else:
                current = line
        else:
            current += "\n" + line if current else line
    if current.strip():
        parts.append(current.strip())
    return parts


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    """Split text into overlapping chunks, respecting paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    paragraphs = re.split(r"\n{2,}", text)
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > max_chars:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            if len(sentences) == 1 and len(sentences[0]) > max_chars:
                sub_parts = _hard_split(para, max_chars)
                for sp in sub_parts:
                    if len(current_chunk) + len(sp) + 1 > max_chars:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sp
                    else:
                        current_chunk += " " + sp if current_chunk else sp
                continue
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 > max_chars:
                    if current_chunk.strip():
                        chunks.append(current_chunk.strip())
                    current_chunk = (
                        current_chunk[-overlap_chars:] + " " + sentence
                        if current_chunk
                        else sentence
                    )
                else:
                    current_chunk += " " + sentence if current_chunk else sentence
            continue

        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            overlap = (
                current_chunk[-overlap_chars:]
                if len(current_chunk) > overlap_chars
                else current_chunk
            )
            current_chunk = overlap + "\n\n" + para if overlap.strip() else para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    final: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final.append(chunk)
        else:
            final.extend(_hard_split(chunk, max_chars))
    return final


def chunk_pages(
    pages: list[dict],
    collection_name: str,
    breadcrumbs: dict[int, str] | None = None,
) -> list[dict]:
    """Chunk extracted pages using collection-specific strategy.

    Returns list of dicts with keys:
      text          — raw chunk text (stored in payload)
      context_text  — breadcrumb + raw text (used for embedding)
      page, chunk_index, section, breadcrumb
    """
    cfg = COLLECTION_REGISTRY[collection_name].chunk_config
    max_chars = cfg.max_chars
    overlap_chars = cfg.overlap_chars

    all_chunks: list[dict] = []
    for page_data in pages:
        page_num = page_data["page"]
        text = page_data["text"]
        text_chunks = chunk_text(text, max_chars, overlap_chars)
        bc = (breadcrumbs or {}).get(page_num, "")

        for i, chunk_str in enumerate(text_chunks):
            section = detect_section(chunk_str)
            # context_text: prepend breadcrumb for richer embedding
            if bc:
                context_text = f"[{bc}]\n{chunk_str}"
            else:
                context_text = chunk_str
            all_chunks.append({
                "text": chunk_str,
                "context_text": context_text,
                "page": page_num,
                "chunk_index": i,
                "section": section,
                "breadcrumb": bc,
            })

    return all_chunks


# ---------------------------------------------------------------------------
# Embedding via Ollama
# ---------------------------------------------------------------------------


def get_embedding(
    text: str, model_name: str, mode: str = "document"
) -> list[float]:
    """Generate a single embedding via Ollama.

    Args:
        text: Raw text to embed.
        model_name: Ollama model name (e.g. 'qwen3-embedding:4b').
        mode: 'document' or 'query' — determines prefix.
    """
    # Find prefix from registry
    prefix = ""
    for m in MODELS.values():
        if m.name == model_name:
            prefix = m.doc_prefix if mode == "document" else m.query_prefix
            break

    prefixed = f"{prefix}{text}"
    resp = _session.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": model_name, "input": prefixed},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    embedding = data["embeddings"][0]

    if any(x != x for x in embedding):
        raise ValueError(f"NaN detected in embedding for text: {text[:100]}...")

    return embedding


def get_embeddings_batch(
    texts: list[str], model_name: str, mode: str = "document"
) -> list[list[float]]:
    """Generate embeddings one at a time for reliability with NaN validation."""
    all_embeddings: list[list[float]] = []
    for i, text in enumerate(texts):
        embedding = get_embedding(text, model_name, mode)
        all_embeddings.append(embedding)
        if (i + 1) % 50 == 0:
            log.info("  Embedded %d/%d chunks...", i + 1, len(texts))
    return all_embeddings


# ---------------------------------------------------------------------------
# Qdrant operations
# ---------------------------------------------------------------------------


def generate_point_id(source_file: str, page: int, chunk_index: int) -> str:
    """Generate a deterministic UUID5 for deduplication."""
    key = f"{source_file}:{page}:{chunk_index}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, key))


def upsert_to_qdrant(
    collection: str, points: list[dict], batch_size: int = 50
) -> None:
    """Upsert points to Qdrant collection in batches."""
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        resp = _session.put(
            f"{QDRANT_URL}/collections/{collection}/points",
            json={"points": batch},
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("status") != "ok":
            log.error("Qdrant upsert failed: %s", result)
            raise RuntimeError(f"Qdrant upsert failed: {result}")


def search_qdrant(
    collection: str,
    query_vector: list[float],
    limit: int = 5,
    filters: dict | None = None,
) -> dict:
    """Search a Qdrant collection with optional payload filters."""
    body: dict = {
        "vector": query_vector,
        "limit": limit,
        "with_payload": True,
    }

    if filters:
        must_clauses = []
        for key, value in filters.items():
            must_clauses.append({"key": key, "match": {"value": value}})
        body["filter"] = {"must": must_clauses}

    resp = _session.post(
        f"{QDRANT_URL}/collections/{collection}/points/search",
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def ensure_collection_exists(collection_name: str) -> None:
    """Create a collection if it doesn't exist, with payload indexes from registry."""
    cfg = COLLECTION_REGISTRY.get(collection_name)
    if not cfg:
        raise ValueError(f"Unknown collection: {collection_name}")

    resp = _session.get(f"{QDRANT_URL}/collections/{collection_name}", timeout=5)
    if resp.status_code == 200:
        info = resp.json()["result"]
        log.info(
            "Collection '%s' exists (%d points)",
            collection_name,
            info.get("points_count", 0),
        )
        return

    log.info(
        "Creating collection '%s' (dims=%d, cosine)...",
        collection_name, cfg.model.dims,
    )
    resp = _session.put(
        f"{QDRANT_URL}/collections/{collection_name}",
        json={"vectors": {"size": cfg.model.dims, "distance": "Cosine"}},
        timeout=10,
    )
    resp.raise_for_status()
    log.info("Collection '%s' created.", collection_name)

    for idx_field in cfg.payload_indexes:
        resp = _session.put(
            f"{QDRANT_URL}/collections/{collection_name}/index",
            json={"field_name": idx_field, "field_schema": "keyword"},
            timeout=10,
        )
        resp.raise_for_status()
        log.info("  Index created: %s", idx_field)


def resolve_model_for_collection(collection: str) -> str:
    """Resolve the embedding model for a collection.

    Checks the registry first; falls back to querying Qdrant for vector size.
    """
    cfg = COLLECTION_REGISTRY.get(collection)
    if cfg:
        return cfg.model.name

    # Fallback: query Qdrant for vector size
    try:
        resp = _session.get(f"{QDRANT_URL}/collections/{collection}", timeout=5)
        resp.raise_for_status()
        vector_size = resp.json()["result"]["config"]["params"]["vectors"]["size"]
        model = DIMS_TO_MODEL.get(vector_size)
        if model:
            return model
    except Exception:
        pass

    log.warning("Could not resolve model for '%s', defaulting to qwen3", collection)
    return MODELS["qwen3"].name


# ---------------------------------------------------------------------------
# Service health check
# ---------------------------------------------------------------------------


def verify_services(model_name: str | None = None) -> bool:
    """Check that Qdrant and Ollama are reachable. Optionally verify a model."""
    ok = True
    try:
        r = _session.get(f"{QDRANT_URL}/collections", timeout=5)
        r.raise_for_status()
        names = [c["name"] for c in r.json()["result"]["collections"]]
        log.info("Qdrant: OK (%d collections: %s)", len(names), ", ".join(names))
    except Exception as e:
        log.error("Qdrant not reachable at %s: %s", QDRANT_URL, e)
        ok = False

    try:
        r = _session.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        if model_name:
            if any(model_name in m for m in models):
                log.info("Ollama: OK (model %s available)", model_name)
            else:
                log.error("Ollama model %s not found. Available: %s", model_name, models)
                log.error("Run: ollama pull %s", model_name)
                ok = False
        else:
            log.info("Ollama: OK (%d models)", len(models))
    except Exception as e:
        log.error("Ollama not reachable at %s: %s", OLLAMA_URL, e)
        ok = False

    return ok


# ---------------------------------------------------------------------------
# Utility: parse CLI filters
# ---------------------------------------------------------------------------


def parse_filters(filter_args: list[str] | None) -> dict | None:
    """Parse key=value filter arguments into a dict."""
    if not filter_args:
        return None
    filters: dict[str, str] = {}
    for f in filter_args:
        if "=" not in f:
            log.warning("Ignoring malformed filter '%s' (expected key=value)", f)
            continue
        key, value = f.split("=", 1)
        filters[key.strip()] = value.strip()
    return filters if filters else None
