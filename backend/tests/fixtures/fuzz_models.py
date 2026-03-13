"""
API fuzzing test models.

Provides test data for:
- OpenAPI schema compliance (FR-027)
- Input validation fuzzing (FR-028)
- Error handling consistency (FR-029)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class FuzzingResult:
    """Model for API fuzzing results (FR-027, FR-028, FR-029)."""

    endpoint: str
    method: str
    input_payload: dict
    response_status: int
    response_body: Optional[dict] = None
    is_server_error: bool = False
    schema_valid: bool = True
    error_message_quality: str = "clear"  # 'clear', 'vague', 'missing'
    response_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def passes_requirements(self) -> bool:
        """Check all fuzzing requirements."""
        return (
            not self.is_server_error  # FR-028: No 500 errors
            and self.schema_valid  # FR-029: Responses match schema
            and self.error_message_quality != "missing"  # FR-029: Clear error messages
        )

    def __repr__(self) -> str:
        return (
            f"FuzzingResult(endpoint={self.endpoint}, "
            f"method={self.method}, "
            f"status={self.response_status}, "
            f"passes={self.passes_requirements()})"
        )


@dataclass
class FuzzingReport:
    """Aggregated fuzzing report."""

    total_requests: int = 0
    server_errors: int = 0
    schema_violations: int = 0
    vague_error_messages: int = 0
    endpoints_tested: List[str] = field(default_factory=list)
    unique_issues: List[str] = field(default_factory=list)
    results: List[FuzzingResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def server_error_rate(self) -> float:
        """Calculate server error rate."""
        return self.server_errors / self.total_requests if self.total_requests > 0 else 0

    @property
    def schema_violation_rate(self) -> float:
        """Calculate schema violation rate."""
        return self.schema_violations / self.total_requests if self.total_requests > 0 else 0

    def is_passing(self) -> bool:
        """FR-028: No 500 Internal Server Errors."""
        return self.server_errors == 0

    def add_result(self, result: FuzzingResult) -> None:
        """Add a fuzzing result to the report."""
        self.total_requests += 1
        self.results.append(result)

        if result.is_server_error:
            self.server_errors += 1

        if not result.schema_valid:
            self.schema_violations += 1

        if result.error_message_quality in ["vague", "missing"]:
            self.vague_error_messages += 1

        if result.endpoint not in self.endpoints_tested:
            self.endpoints_tested.append(result.endpoint)

    def __repr__(self) -> str:
        return (
            f"FuzzingReport(requests={self.total_requests}, "
            f"errors={self.server_errors}, "
            f"schema_violations={self.schema_violations}, "
            f"passing={self.is_passing()})"
        )


# ==============================================================
# Schemathesis Configuration
# ==============================================================


@dataclass
class SchemathesisConfig:
    """Configuration for Schemathesis fuzzing."""

    openapi_path: str
    base_url: str
    max_examples: int = 100
    max_response_time_ms: int = 5000
    stateful_testing: bool = True
    workers: int = 4
    checks: List[str] = field(
        default_factory=lambda: [
            "not_a_server_error",
            "status_code_conformance",
            "content_type_conformance",
            "response_schema_conformance",
        ]
    )


DEFAULT_SCHEMATHESIS_CONFIG = SchemathesisConfig(
    openapi_path="/api/schema/",
    base_url="http://localhost:8001",
    max_examples=100,
    max_response_time_ms=5000,
    stateful_testing=True,
    workers=4,
)


# ==============================================================
# Fuzz Target Endpoints
# ==============================================================

FUZZ_TARGET_ENDPOINTS = [
    {
        "path": "/api/v1/auth/token/",
        "methods": ["POST"],
        "priority": "high",
        "description": "Authentication endpoint - critical security target",
    },
    {
        "path": "/api/v1/inventario/products/",
        "methods": ["GET", "POST"],
        "priority": "high",
        "description": "Product CRUD - main business endpoint",
    },
    {
        "path": "/api/v1/inventario/products/{id}/",
        "methods": ["GET", "PUT", "PATCH", "DELETE"],
        "priority": "medium",
        "description": "Single product operations",
    },
    {
        "path": "/api/v1/inventario/stock/",
        "methods": ["GET", "POST"],
        "priority": "high",
        "description": "Stock management - business critical",
    },
    {
        "path": "/api/v1/sync/sessions/",
        "methods": ["GET", "POST"],
        "priority": "medium",
        "description": "Sync session management",
    },
    {
        "path": "/api/v1/auth/users/",
        "methods": ["GET", "POST"],
        "priority": "high",
        "description": "User management - security sensitive",
    },
]


# ==============================================================
# Edge Case Payloads for Fuzzing
# ==============================================================

EDGE_CASE_PAYLOADS: Dict[str, List] = {
    "string_field": [
        "",  # Empty string
        " " * 100,  # Whitespace only
        "a" * 10000,  # Very long string
        "\x00",  # Null byte
        "\n\r\t",  # Control characters
        "🚀💰🎉",  # Emojis
        "<script>alert('xss')</script>",  # XSS attempt
        "'; DROP TABLE users; --",  # SQL injection
        "${7*7}",  # Template injection
        "{{7*7}}",  # SSTI
    ],
    "integer_field": [
        0,
        -1,
        2147483647,  # Max int32
        -2147483648,  # Min int32
        9223372036854775807,  # Max int64
        "not_an_integer",
        1.5,  # Float where int expected
        None,
    ],
    "decimal_field": [
        "0.00",
        "-0.001",
        "99999999999999.999",  # Max allowed
        "100000000000000.000",  # Exceeds max
        "NaN",
        "Infinity",
        "-Infinity",
        "not_a_number",
    ],
    "uuid_field": [
        "00000000-0000-0000-0000-000000000000",  # Nil UUID
        "not-a-valid-uuid",
        "12345678-1234-1234-1234-123456789012",  # Valid format
        "",  # Empty
        "12345678123412341234123456789012",  # No dashes
    ],
    "boolean_field": [
        True,
        False,
        "true",
        "false",
        "yes",
        "no",
        1,
        0,
        "not_a_boolean",
        None,
    ],
    "array_field": [
        [],  # Empty array
        [None] * 1000,  # Large array of nulls
        [{}] * 100,  # Array of empty objects
        "not_an_array",
        {"not": "array"},
    ],
    "email_field": [
        "valid@example.com",
        "invalid-email",
        "@no-local.com",
        "no-domain@",
        "a" * 255 + "@test.com",  # Very long email
        "test@" + "a" * 255 + ".com",  # Very long domain
        "",
    ],
}


# ==============================================================
# Expected Error Response Format
# ==============================================================


@dataclass
class ExpectedErrorResponse:
    """Expected error response format for validation."""

    min_status_code: int
    max_status_code: int
    required_fields: List[str]
    forbidden_fields: List[str]


EXPECTED_ERROR_FORMATS = {
    "validation_error": ExpectedErrorResponse(
        min_status_code=400,
        max_status_code=422,
        required_fields=["detail"],
        forbidden_fields=["traceback", "stack_trace", "exception"],
    ),
    "authentication_error": ExpectedErrorResponse(
        min_status_code=401,
        max_status_code=401,
        required_fields=["detail"],
        forbidden_fields=["traceback", "password", "secret"],
    ),
    "authorization_error": ExpectedErrorResponse(
        min_status_code=403,
        max_status_code=403,
        required_fields=["detail"],
        forbidden_fields=["traceback", "internal_id"],
    ),
    "not_found_error": ExpectedErrorResponse(
        min_status_code=404,
        max_status_code=404,
        required_fields=["detail"],
        forbidden_fields=["traceback", "query", "sql"],
    ),
    "rate_limit_error": ExpectedErrorResponse(
        min_status_code=429,
        max_status_code=429,
        required_fields=["detail", "retry_after"],
        forbidden_fields=["traceback"],
    ),
}
