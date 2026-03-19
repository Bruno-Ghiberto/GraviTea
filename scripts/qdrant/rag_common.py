"""
RAG Common Library for GRAVITEA-ERP Qdrant Pipeline
====================================================
Shared infrastructure for ingestion, embedding, chunking, and Qdrant operations.
Centralizes configuration, eliminates duplication across ingest scripts, and adds
contextual chunking with breadcrumb-based structural context.

Used by: ingest_arca_qdrant.py, ingest_wikis_qdrant.py, ingest_acopio_research.py,
         qdrant_search.py, benchmark
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
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

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
    "acopio_research": CollectionConfig(
        name="acopio_research",
        model=MODELS["qwen3"],
        chunk_config=ChunkConfig(max_chars=2000, overlap_chars=250),
        payload_indexes=("topic", "subtopic", "priority", "source_file"),
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
# Markdown text extraction
# ---------------------------------------------------------------------------

_MD_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def extract_markdown_sections(md_path: Path) -> list[dict]:
    """Extract sections from a markdown file, splitting at heading boundaries.

    Returns list of dicts:
      heading    — the heading text (without ``#`` prefix)
      depth      — 1 for ``#``, 2 for ``##``, 3 for ``###``, 4 for ``####``
      text       — body text under the heading (excluding the heading line itself)
      line_start — 1-based line number where the section starts (heading line)
      line_end   — 1-based line number where the section ends (inclusive)
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        log.warning("Cannot read markdown file %s: %s", md_path, exc)
        return []

    if not content.strip():
        log.warning("Empty markdown file: %s", md_path)
        return []

    lines = content.split("\n")
    sections: list[dict] = []

    # Find all heading positions
    heading_positions: list[tuple[int, int, str]] = []  # (line_idx, depth, heading_text)
    for idx, line in enumerate(lines):
        m = _MD_HEADING_RE.match(line)
        if m:
            depth = len(m.group(1))
            heading_text = m.group(2).strip()
            heading_positions.append((idx, depth, heading_text))

    if not heading_positions:
        # No headings — treat entire file as a single section
        full_text = content.strip()
        if full_text:
            sections.append({
                "heading": "",
                "depth": 0,
                "text": full_text,
                "line_start": 1,
                "line_end": len(lines),
            })
        return sections

    # If there is content before the first heading, capture it as a preamble section
    first_heading_idx = heading_positions[0][0]
    if first_heading_idx > 0:
        preamble = "\n".join(lines[:first_heading_idx]).strip()
        if preamble:
            sections.append({
                "heading": "",
                "depth": 0,
                "text": preamble,
                "line_start": 1,
                "line_end": first_heading_idx,
            })

    # Build sections from heading positions
    for i, (line_idx, depth, heading_text) in enumerate(heading_positions):
        # Section body runs from line after heading to line before next heading (or EOF)
        body_start = line_idx + 1
        if i + 1 < len(heading_positions):
            body_end = heading_positions[i + 1][0]
        else:
            body_end = len(lines)

        body = "\n".join(lines[body_start:body_end]).strip()
        sections.append({
            "heading": heading_text,
            "depth": depth,
            "text": body,
            "line_start": line_idx + 1,  # 1-based
            "line_end": body_end,         # 1-based (inclusive of last body line)
        })

    return sections


def build_markdown_breadcrumbs(sections: list[dict]) -> dict[int, str]:
    """Build breadcrumb strings from a heading hierarchy.

    Uses the heading depth (1-4) to maintain a stack: depth 1 maps to
    tracker depth 0, depth 2 to tracker depth 1, etc.

    Returns ``{section_index: "H1 Title > H2 Title > H3 Title"}``.
    """
    tracker = HeadingTracker()
    breadcrumbs: dict[int, str] = {}

    for idx, section in enumerate(sections):
        depth = section["depth"]
        heading = section["heading"]

        if depth > 0 and heading:
            # Map markdown depth (1-4) to HeadingTracker depth (0-3)
            tracker.update(depth - 1, heading)

        breadcrumbs[idx] = tracker.breadcrumb

    return breadcrumbs


def chunk_markdown_sections(
    sections: list[dict],
    collection_name: str,
    breadcrumbs: dict[int, str] | None = None,
) -> list[dict]:
    """Chunk markdown sections using collection-specific strategy.

    Small sections (< 200 chars) are merged with the next adjacent section
    at the same or lower depth to avoid overly-tiny chunks.

    Returns list of dicts with keys:
      text, context_text, page (always 0), chunk_index, section, breadcrumb
    """
    cfg = COLLECTION_REGISTRY[collection_name].chunk_config
    max_chars = cfg.max_chars
    overlap_chars = cfg.overlap_chars

    # Phase 1: merge small sections into adjacent siblings
    merged: list[tuple[int, dict]] = []  # (original_index, section_dict)
    i = 0
    while i < len(sections):
        section = sections[i]
        text = section["text"]

        # Merge small sections forward into the next section at same or lower depth
        if len(text) < 200 and i + 1 < len(sections):
            next_section = sections[i + 1]
            if next_section["depth"] >= section["depth"] or section["depth"] == 0:
                # Prepend heading context when merging
                prefix = f"## {section['heading']}\n\n" if section["heading"] else ""
                combined_text = f"{prefix}{text}\n\n{next_section['text']}"
                combined = {
                    "heading": next_section["heading"] or section["heading"],
                    "depth": next_section["depth"] if next_section["depth"] > 0 else section["depth"],
                    "text": combined_text,
                    "line_start": section["line_start"],
                    "line_end": next_section["line_end"],
                }
                merged.append((i + 1, combined))
                i += 2
                continue

        merged.append((i, section))
        i += 1

    # Phase 2: chunk each (possibly merged) section
    all_chunks: list[dict] = []
    global_chunk_idx = 0

    for orig_idx, section in merged:
        text = section["text"]
        heading = section["heading"]
        bc = (breadcrumbs or {}).get(orig_idx, "")

        if not text.strip():
            continue

        if len(text) <= max_chars:
            text_chunks = [text]
        else:
            text_chunks = chunk_text(text, max_chars, overlap_chars)

        for chunk_str in text_chunks:
            # Build context_text with breadcrumb prepended
            if bc:
                context_text = f"[{bc}]\n{chunk_str}"
            else:
                context_text = chunk_str

            all_chunks.append({
                "text": chunk_str,
                "context_text": context_text,
                "page": 0,
                "chunk_index": global_chunk_idx,
                "section": heading,
                "breadcrumb": bc,
            })
            global_chunk_idx += 1

    return all_chunks


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
