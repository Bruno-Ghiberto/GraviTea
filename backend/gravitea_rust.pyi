"""Type stubs for the gravitea_rust Rust extension module."""

def hello() -> str:
    """Return a greeting from Rust, proving the PyO3 bridge works."""
    ...

def encrypt_value(plaintext: str, key: bytes) -> str:
    """Encrypt a plaintext string using AES-256-GCM.

    Returns base64(nonce[12] || ciphertext || tag[16]).

    Raises:
        ValueError: If key is not exactly 32 bytes.
        RuntimeError: If encryption fails.
    """
    ...

def decrypt_value(encrypted: str, key: bytes) -> str:
    """Decrypt an AES-256-GCM encrypted value.

    Expects base64(nonce[12] || ciphertext || tag[16]).

    Raises:
        ValueError: If key is not exactly 32 bytes.
        RuntimeError: If decryption fails (wrong key, tampered data).
    """
    ...

def compute_blind_index(value: str, hmac_key: bytes) -> str:
    """Compute HMAC-SHA256 blind index with NFC normalisation.

    Order: NFC -> to_lowercase() -> trim() -> HMAC-SHA256 -> hex.
    Returns 64-character lowercase hex string.

    Raises:
        ValueError: If hmac_key is not exactly 32 bytes.
    """
    ...

def validate_importes(
    imp_total: str,
    imp_neto: str,
    imp_iva: str,
    imp_trib: str,
    imp_op_ex: str,
    imp_tot_conc: str,
) -> None:
    """Validate ARCA invoice amount totals with dual tolerance.

    Checks: imp_total == imp_neto + imp_iva + imp_trib + imp_op_ex + imp_tot_conc
    Tolerance: abs_tol=0.01 OR rel_tol=0.0001.

    All amounts are Decimal-as-string (str→Decimal boundary).

    Raises:
        RuntimeError: If amounts do not balance within tolerance.
    """
    ...

def calculate_iva_breakdown(items_json: str) -> str:
    """Calculate IVA breakdown from line items.

    Args:
        items_json: JSON array of {"price": str, "quantity": str, "iva_rate": str}.

    Returns:
        JSON array of {"base_imp": str, "importe": str, "iva_id": int, "iva_rate": str}.

    Raises:
        RuntimeError: If JSON is invalid or computation fails.
    """
    ...

def validate_cuit(cuit: str) -> None:
    """Validate an Argentine CUIT/CUIL using Modulo-11 algorithm.

    Args:
        cuit: 11-digit CUIT string (no hyphens).

    Raises:
        RuntimeError: If CUIT is invalid (wrong length, non-numeric, bad check digit).
    """
    ...

def aggregate_stock_levels(movements_json: str) -> str:
    """Aggregate stock movements into per-product, per-warehouse totals.

    Releases the GIL for batch processing.

    Args:
        movements_json: JSON array of {"product_id": str, "branch_id": str,
                        "quantity": str, "movement_type": str}.

    Returns:
        JSON object: {"product_id": {"branch_id": {"total": str, "reserved": str, "available": str}}}.

    Raises:
        RuntimeError: If JSON is invalid or aggregation fails.
    """
    ...

def validate_iva_breakdown(
    cbte_tipo: int,
    aliciva_json: str,
    imp_iva: str,
    imp_neto: str,
) -> None:
    """Validate IVA breakdown against comprobante type rules.

    Checks:
    - Types [1,2,3,6,7,8,51,52,53] (A/B/M): IVA required, sum(importe)==imp_iva, sum(base_imp)==imp_neto.
    - Types [11,12,13] (C): IVA prohibited.
    - Other types: IVA optional, sums validated if present.

    Args:
        cbte_tipo: ARCA comprobante type code.
        aliciva_json: JSON array of {"iva_id": int, "base_imp": str, "importe": str}.
        imp_iva: Total IVA amount as string.
        imp_neto: Total net amount as string.

    Raises:
        RuntimeError: If validation fails.
    """
    ...

def generate_csv(
    rows: list[dict[str, str]],
    headers: list[str],
) -> bytes:
    """Generate CSV bytes with UTF-8 BOM and ordered columns.

    Releases the GIL during Rust execution.

    Args:
        rows: List of dicts mapping column names to string values.
        headers: Ordered list of column names for output order.

    Returns:
        CSV file content as bytes, prefixed with UTF-8 BOM (0xEF 0xBB 0xBF).

    Raises:
        RuntimeError: If CSV serialisation fails.
    """
    ...

def generate_xlsx(
    rows: list[dict[str, str]],
    headers: list[str],
    column_widths: dict[str, float] | None = None,
) -> bytes:
    """Generate XLSX bytes with numeric detection and optional column widths.

    Releases the GIL during Rust execution.

    Args:
        rows: List of dicts mapping column names to string values.
        headers: Ordered list of column names for output order.
        column_widths: Optional dict of column name -> width in character units.
                       Orphan keys (not in headers) are silently ignored.

    Returns:
        XLSX file content as bytes (ZIP/PK signature).

    Raises:
        RuntimeError: If XLSX serialisation fails.
    """
    ...

def normalize_path(path: str) -> str:
    """Normalize URL path by replacing UUIDs and integer IDs with {id}.

    Strips query parameters, then applies 2 compiled regex patterns.
    Sub-microsecond per call — no GIL release needed.
    """
    ...

def sanitize_endpoint_label(endpoint: str) -> str:
    """Sanitize endpoint path for Prometheus metric labels.

    Applies 16 sensitive endpoint patterns + 6 fallback word-boundary
    patterns to redact passwords, tokens, secrets, and credentials.
    Sub-microsecond per call — no GIL release needed.
    """
    ...

def validate_url_safety(url: str) -> tuple[bool, str]:
    """Validate URL safety against SSRF attack vectors (Phase 1 static checks).

    Checks: scheme allowlist, credentials, IP encoding (decimal/hex/octal/
    shortened), CIDR ranges (10/8, 172.16/12, 192.168/16, 127/8, 169.254/16,
    0/8, ::1/128, fc00::/7, fe80::/10, ::ffff:0:0/96), cloud metadata IPs,
    suspicious hostname patterns (nip.io, xip.io, sslip.io, localtest.me, etc.).

    Returns:
        (is_safe, hostname): If is_safe=False, URL is definitively unsafe.
        If is_safe=True and hostname is non-empty, DNS resolution is needed.
        If is_safe=True and hostname is empty, URL is safe (direct public IP).
    """
    ...


def check_resolved_ip(ip_str: str) -> bool:
    """Check if a DNS-resolved IP address is safe (not private/metadata).

    Checks the resolved IP against all 10 CIDR private ranges and cloud
    metadata IPs. Used as Phase 2 of the SSRF validation pipeline.

    Args:
        ip_str: IP address string (IPv4 or IPv6).

    Returns:
        True if IP is safe (public), False if private/loopback/metadata.
    """
    ...


def merge_most_complete(
    server_json: str,
    client_json: str,
    metadata_fields_json: str,
) -> tuple[str, str]:
    """Merge two JSON payloads using most-complete-wins strategy.

    Compares field-by-field: strings by stripped length, arrays by length,
    objects by key count. Server wins ties. Metadata fields always use server.
    GIL NOT released (single operation).

    Args:
        server_json: JSON object string for server payload.
        client_json: JSON object string for client payload.
        metadata_fields_json: JSON array of field names to skip comparison.

    Returns:
        (merged_json, merge_log_json) tuple of JSON strings.

    Raises:
        RuntimeError: If both payloads are empty or JSON is invalid.
    """
    ...


def merge_most_complete_batch(
    pairs_json: str,
    metadata_fields_json: str,
) -> str:
    """Batch merge multiple server/client pairs with GIL released.

    Args:
        pairs_json: JSON array of {"server": {...}, "client": {...}} objects.
        metadata_fields_json: JSON array of metadata field names.

    Returns:
        JSON array of {"merged": {...}, "merge_log": {...}} objects.

    Raises:
        RuntimeError: If JSON is invalid or any merge fails.
    """
    ...


def validate_custom_fields(defs_json: str, data_json: str) -> str: ...


def build_caea_batch_request(comprobantes_json: str, caea: str, default_cuit: str) -> str:
    """Build CAEA batch det_list from JSON comprobantes via Rust serde.

    Releases the GIL during batch construction.

    Args:
        comprobantes_json: JSON array of comprobante dicts.
        caea: CAEA number string (14 digits).
        default_cuit: Fallback CUIT for CbteAsoc entries without explicit cuit.

    Returns:
        JSON array of FECAEADetRequest dicts with ARCA-compatible key names.

    Raises:
        RuntimeError: If JSON parsing or conversion fails.
    """
    ...


class GraviteaError(Exception):
    """Base error type for Rust extension errors.

    Variants:
        InvalidInput: Maps to ValueError — bad function arguments.
        CryptoError: Maps to RuntimeError — crypto operation failures.
        ComputeError: Maps to RuntimeError — fiscal compute failures.
        ExportError: Maps to RuntimeError — CSV/XLSX export failures.
        IoError: Maps to IOError — file/network I/O errors.
        SecurityError: Maps to RuntimeError — SSRF validation failures.
        SyncError: Maps to RuntimeError — sync merge failures.
    """

    ...
