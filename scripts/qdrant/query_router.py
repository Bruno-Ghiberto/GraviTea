"""
Query Router for GRAVITEA-ERP Qdrant Pipeline
==============================================
Routes search queries to the most relevant collection(s) based on
regex pattern matching against domain-specific keywords.

No LLM dependency — pure Python regex routing.
"""

import re
from dataclasses import dataclass, field

from rag_common import ALL_COLLECTION_NAMES, COLLECTION_REGISTRY


@dataclass
class RouteTarget:
    collection: str
    filters: dict | None = None
    weight: float = 1.0


# Ordered list: first match wins (most specific rules first)
ROUTING_RULES: list[tuple[re.Pattern, list[RouteTarget]]] = [
    # --- ARCA-specific patterns ---
    (
        re.compile(r"\b(WSAA|ticket\s+de\s+acceso|login\s+ticket|TRA|CMS)\b", re.IGNORECASE),
        [
            RouteTarget("arca_api_specs", filters={"ws_name": "wsaa"}, weight=1.0),
            RouteTarget("arca_dev_guides", filters={"ws_name": "wsaa"}, weight=0.8),
        ],
    ),
    (
        re.compile(r"\b(certificado|certificate|\.crt|\.key|\.pem|clave\s+privada)\b", re.IGNORECASE),
        [
            RouteTarget("arca_setup_certs", weight=1.0),
            RouteTarget("arca_dev_guides", weight=0.5),
        ],
    ),
    (
        re.compile(r"\b(WSFEv1|FECAESolicitar|FECompUltimoAutorizado|FECAEA|FEParamGet)\b", re.IGNORECASE),
        [
            RouteTarget("arca_api_specs", filters={"ws_name": "wsfev1"}, weight=1.0),
            RouteTarget("arca_dev_guides", filters={"ws_name": "wsfev1"}, weight=0.8),
        ],
    ),
    (
        re.compile(r"\b(WSFEX|FEXAuthorize|factura\s+exportaci[oó]n)\b", re.IGNORECASE),
        [
            RouteTarget("arca_api_specs", filters={"ws_name": "wsfexv1"}, weight=1.0),
            RouteTarget("arca_dev_guides", filters={"ws_name": "wsfexv1"}, weight=0.8),
        ],
    ),
    (
        re.compile(r"\b(WSBFE|bono\s+fiscal|factura\s+bienes)\b", re.IGNORECASE),
        [
            RouteTarget("arca_api_specs", filters={"ws_name": "wsbfev1"}, weight=1.0),
            RouteTarget("arca_dev_guides", filters={"ws_name": "wsbfev1"}, weight=0.8),
        ],
    ),
    (
        re.compile(r"\b(ARCA|AFIP|factura\s+electr[oó]nica|comprobante|CAE|CAEA|CbteTipo)\b", re.IGNORECASE),
        [
            RouteTarget("arca_api_specs", weight=1.0),
            RouteTarget("arca_dev_guides", weight=0.8),
        ],
    ),
    (
        re.compile(r"\b(produccion|testing|homologaci[oó]n|TLS|cronograma)\b", re.IGNORECASE),
        [
            RouteTarget("arca_setup_certs", weight=1.0),
        ],
    ),
    # --- Wiki / reference patterns ---
    (
        re.compile(r"\b(Django|ORM|QuerySet|select_related|prefetch_related|migration|middleware)\b", re.IGNORECASE),
        [
            RouteTarget("wikis", filters={"topic": "django"}, weight=1.0),
        ],
    ),
    (
        re.compile(r"\b(JWT|RS256|JWS|JWE|claim|bearer\s+token|json\s+web\s+token)\b", re.IGNORECASE),
        [
            RouteTarget("wikis", filters={"topic": "jwt"}, weight=1.0),
        ],
    ),
    (
        re.compile(r"\b(Rust|ownership|borrow\s+checker|cargo|PyO3|lifetime|crate)\b", re.IGNORECASE),
        [
            RouteTarget("wikis", filters={"topic": "rust"}, weight=1.0),
        ],
    ),
]

DEFAULT_ROUTES = [
    RouteTarget("arca_api_specs", weight=0.8),
    RouteTarget("arca_dev_guides", weight=0.6),
    RouteTarget("wikis", weight=0.4),
]


def route_query(
    query: str,
    explicit_collection: str | None = None,
    explicit_filters: dict | None = None,
    search_all: bool = False,
) -> list[RouteTarget]:
    """Route a query to one or more collections.

    Priority:
      1. explicit_collection overrides everything (backward compat)
      2. search_all sends to every registered collection
      3. Regex routing rules (first match wins)
      4. DEFAULT_ROUTES as fallback
    """
    if explicit_collection:
        return [RouteTarget(explicit_collection, filters=explicit_filters, weight=1.0)]

    if search_all:
        return [RouteTarget(name, weight=1.0) for name in ALL_COLLECTION_NAMES]

    for pattern, targets in ROUTING_RULES:
        if pattern.search(query):
            return targets

    return DEFAULT_ROUTES
