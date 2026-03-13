"""
Query Expander for GRAVITEA-ERP Qdrant Pipeline
================================================
Enriches search queries by expanding domain-specific acronyms and
generating bilingual variants (Spanish/English).

No LLM dependency — pure Python dictionary lookups.
"""

import re


# Domain acronym -> expansion (added to query, not replacing)
SYNONYM_MAP: dict[str, str] = {
    "CAE": "Codigo de Autorizacion Electronico",
    "CAEA": "Codigo de Autorizacion Electronico Anticipado",
    "CUIT": "Clave Unica de Identificacion Tributaria",
    "WSAA": "Web Service de Autenticacion y Autorizacion",
    "WSFEv1": "Web Service Facturacion Electronica version 1",
    "WSFEX": "Web Service Facturacion Exportacion",
    "WSBFE": "Web Service Bienes Fiscales Electronicos",
    "WSMTXCA": "Web Service Mercado Interno con Detalle",
    "TRA": "Ticket de Requerimiento de Acceso",
    "CMS": "Cryptographic Message Syntax",
    "IVA": "Impuesto al Valor Agregado",
    "ORM": "Object Relational Mapping",
    "DRF": "Django REST Framework",
    "JWT": "JSON Web Token",
    "JWS": "JSON Web Signature",
    "RS256": "RSA Signature with SHA-256",
    "PII": "Personally Identifiable Information",
    "RLS": "Row Level Security",
    "PyO3": "Python bindings for Rust",
    "SOAP": "Simple Object Access Protocol",
}

# Precompile patterns: match whole words only, case-insensitive
_ACRONYM_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(rf"\b{re.escape(acr)}\b", re.IGNORECASE), expansion)
    for acr, expansion in SYNONYM_MAP.items()
]


def expand_query(query: str) -> str:
    """Append acronym expansions to the query.

    Does NOT replace the original terms — only adds context.
    Returns the original query if no acronyms match.
    """
    expansions: list[str] = []
    for pattern, expansion in _ACRONYM_PATTERNS:
        if pattern.search(query):
            # Only add if the expansion isn't already in the query
            if expansion.lower() not in query.lower():
                expansions.append(expansion)

    if not expansions:
        return query

    return f"{query} ({'; '.join(expansions)})"


# Bilingual swap pairs for optional multi-variant generation
_BILINGUAL_SWAPS: list[tuple[str, str]] = [
    ("factura electronica", "electronic invoice"),
    ("comprobante", "voucher"),
    ("certificado", "certificate"),
    ("autorizacion", "authorization"),
    ("error", "error"),  # same in both
    ("parametro", "parameter"),
    ("obligatorio", "required"),
    ("validacion", "validation"),
]


def generate_query_variants(query: str, max_variants: int = 2) -> list[str]:
    """Generate bilingual variants of the query.

    Returns [original, variant1, ...] up to max_variants+1 total.
    """
    variants = [query]
    query_lower = query.lower()

    for es, en in _BILINGUAL_SWAPS:
        if len(variants) > max_variants:
            break
        if es in query_lower:
            variant = re.sub(re.escape(es), en, query_lower, flags=re.IGNORECASE)
            if variant != query_lower:
                variants.append(variant)
        elif en in query_lower:
            variant = re.sub(re.escape(en), es, query_lower, flags=re.IGNORECASE)
            if variant != query_lower:
                variants.append(variant)

    return variants[: max_variants + 1]
