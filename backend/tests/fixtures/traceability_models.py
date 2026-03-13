"""
Test traceability models.

Provides data structures for:
- Requirement-to-test mapping (FR-030)
- Coverage reporting (FR-031)
- Test-to-spec linkage
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RequirementTestMapping:
    """Model for requirement-to-test traceability (FR-030, FR-031)."""

    requirement_id: str  # e.g., 'FR-001'
    requirement_text: str
    test_files: List[str]
    test_functions: List[str]
    coverage_status: str  # 'covered', 'partial', 'uncovered'
    priority: str = "medium"  # 'high', 'medium', 'low'
    category: str = ""  # 'security', 'docker', 'load', 'fuzz', etc.

    @property
    def is_covered(self) -> bool:
        """Check if requirement is fully covered."""
        return self.coverage_status == "covered"

    def __repr__(self) -> str:
        return (
            f"RequirementTestMapping(id={self.requirement_id}, "
            f"status={self.coverage_status}, "
            f"tests={len(self.test_functions)})"
        )


@dataclass
class TraceabilityMatrix:
    """Complete traceability matrix."""

    mappings: List[RequirementTestMapping] = field(default_factory=list)
    spec_version: str = "005-debug-testing-docker"
    generated_at: str = ""

    @property
    def total_requirements(self) -> int:
        """Total number of requirements."""
        return len(self.mappings)

    @property
    def covered_requirements(self) -> int:
        """Number of fully covered requirements."""
        return sum(1 for m in self.mappings if m.coverage_status == "covered")

    @property
    def partial_requirements(self) -> int:
        """Number of partially covered requirements."""
        return sum(1 for m in self.mappings if m.coverage_status == "partial")

    @property
    def uncovered_requirements(self) -> int:
        """Number of uncovered requirements."""
        return sum(1 for m in self.mappings if m.coverage_status == "uncovered")

    @property
    def coverage_percentage(self) -> float:
        """Calculate coverage percentage."""
        if self.total_requirements == 0:
            return 0.0
        return (self.covered_requirements / self.total_requirements) * 100

    def is_complete(self) -> bool:
        """FR-030: All requirements must have associated tests."""
        return self.uncovered_requirements == 0

    def get_by_category(self, category: str) -> List[RequirementTestMapping]:
        """Get requirements by category."""
        return [m for m in self.mappings if m.category == category]

    def get_uncovered(self) -> List[RequirementTestMapping]:
        """Get list of uncovered requirements."""
        return [m for m in self.mappings if m.coverage_status == "uncovered"]

    def __repr__(self) -> str:
        return (
            f"TraceabilityMatrix(total={self.total_requirements}, "
            f"covered={self.covered_requirements}, "
            f"partial={self.partial_requirements}, "
            f"uncovered={self.uncovered_requirements}, "
            f"coverage={self.coverage_percentage:.1f}%)"
        )


# ==============================================================
# Requirement-to-Test Mapping for Spec 005
# ==============================================================

REQUIREMENT_TEST_MAP: Dict[str, Dict] = {
    # Security Requirements (US1)
    "FR-001": {
        "text": "System MUST reject JWTs with alg:none attack vector",
        "tests": ["tests/security/test_jwt_attacks.py::test_alg_none_rejected"],
        "category": "security",
        "priority": "high",
    },
    "FR-002": {
        "text": "System MUST reject JWTs with algorithm confusion attacks",
        "tests": ["tests/security/test_jwt_attacks.py::test_alg_confusion_rejected"],
        "category": "security",
        "priority": "high",
    },
    "FR-003": {
        "text": "System MUST enforce rate limiting with progressive lockout",
        "tests": [
            "tests/security/test_rate_limiting.py::test_progressive_lockout_5_failures",
            "tests/security/test_rate_limiting.py::test_progressive_lockout_10_failures",
        ],
        "category": "security",
        "priority": "high",
    },
    "FR-004": {
        "text": "System MUST return 429 with accurate Retry-After header",
        "tests": ["tests/security/test_rate_limiting.py::test_retry_after_header_accuracy"],
        "category": "security",
        "priority": "high",
    },
    "FR-005": {
        "text": "System MUST encrypt sensitive tenant data at rest using AES-256-GCM",
        "tests": [
            "tests/security/test_encryption.py::test_data_at_rest_encrypted",
            "tests/security/test_encryption.py::test_aes_256_gcm_algorithm",
        ],
        "category": "security",
        "priority": "high",
    },
    "FR-006": {
        "text": "System MUST enforce tenant isolation at database query level",
        "tests": [
            "tests/security/test_tenant_isolation.py::test_cross_tenant_api_access_blocked",
            "tests/security/test_tenant_isolation.py::test_cross_tenant_orm_query_filtered",
            "tests/security/test_tenant_isolation.py::test_fk_manipulation_blocked",
        ],
        "category": "security",
        "priority": "high",
    },
    "FR-007": {
        "text": "System MUST validate all input against OWASP injection patterns",
        "tests": ["tests/security/test_owasp.py::test_owasp_injection_blocked"],
        "category": "security",
        "priority": "high",
    },
    # Coverage Requirements (US2)
    "FR-008": {
        "text": "Auth module MUST have 95%+ coverage",
        "tests": ["tests/auth/"],
        "category": "coverage",
        "priority": "high",
    },
    "FR-009": {
        "text": "Core module MUST have 95%+ coverage",
        "tests": ["tests/core/"],
        "category": "coverage",
        "priority": "high",
    },
    "FR-010": {
        "text": "Inventario module MUST have 95%+ coverage",
        "tests": ["tests/inventario/"],
        "category": "coverage",
        "priority": "high",
    },
    "FR-011": {
        "text": "Sync module MUST have 95%+ coverage",
        "tests": ["tests/sync/"],
        "category": "coverage",
        "priority": "high",
    },
    "FR-012": {
        "text": "Integration tests MUST cover all critical paths",
        "tests": ["tests/integration/"],
        "category": "coverage",
        "priority": "high",
    },
    # Docker Requirements (US3)
    "FR-013": {
        "text": "Services MUST expose /health/live and /health/ready endpoints",
        "tests": ["tests/docker/test_health_checks.py::test_health_endpoints_exist"],
        "category": "docker",
        "priority": "high",
    },
    "FR-014": {
        "text": "Health checks MUST respond within 5 seconds",
        "tests": ["tests/docker/test_health_checks.py::test_health_check_response_time"],
        "category": "docker",
        "priority": "high",
    },
    "FR-015": {
        "text": "Services MUST support graceful shutdown with 30-second drain",
        "tests": ["tests/docker/test_graceful_shutdown.py::test_graceful_shutdown"],
        "category": "docker",
        "priority": "high",
    },
    "FR-016": {
        "text": "Docker Compose MUST implement three-network topology",
        "tests": ["tests/docker/test_network_topology.py::test_network_topology"],
        "category": "docker",
        "priority": "medium",
    },
    "FR-017": {
        "text": "Database connections MUST use CONN_MAX_AGE=0 for Cloud Run",
        "tests": ["tests/docker/test_database_connections.py::test_conn_max_age_zero"],
        "category": "docker",
        "priority": "high",
    },
    "FR-018": {
        "text": "Observability stack MUST be testable in isolation",
        "tests": ["tests/docker/test_observability.py::test_observability_stack"],
        "category": "docker",
        "priority": "medium",
    },
    # Property-Based Testing Requirements (US4)
    "FR-019": {
        "text": "Inventory boundary tests with Hypothesis",
        "tests": ["tests/property/test_inventory_boundaries.py"],
        "category": "property",
        "priority": "medium",
    },
    "FR-020": {
        "text": "Price calculation invariant tests",
        "tests": ["tests/property/test_price_invariants.py"],
        "category": "property",
        "priority": "medium",
    },
    "FR-021": {
        "text": "Tenant isolation property tests",
        "tests": ["tests/property/test_tenant_properties.py"],
        "category": "property",
        "priority": "medium",
    },
    # Load Testing Requirements (US5)
    "FR-022": {
        "text": "Baseline load: 100 users, p95 < 500ms",
        "tests": ["tests/load/locustfile.py::BaselineUser"],
        "category": "load",
        "priority": "high",
    },
    "FR-023": {
        "text": "Peak load: 500 users, <1% error rate",
        "tests": ["tests/load/locustfile.py::PeakUser"],
        "category": "load",
        "priority": "high",
    },
    "FR-024": {
        "text": "Sustained load: 10 minutes, stable memory",
        "tests": ["tests/load/locustfile.py::SustainedUser"],
        "category": "load",
        "priority": "medium",
    },
    # Fuzzing Requirements (US6)
    "FR-025": {
        "text": "All endpoints MUST pass Schemathesis fuzzing",
        "tests": ["tests/fuzz/test_api_fuzzing.py"],
        "category": "fuzz",
        "priority": "high",
    },
    "FR-026": {
        "text": "No 500 errors from any valid OpenAPI input",
        "tests": ["tests/fuzz/test_api_fuzzing.py::test_no_server_errors"],
        "category": "fuzz",
        "priority": "high",
    },
    "FR-027": {
        "text": "Error responses MUST match defined schema",
        "tests": ["tests/fuzz/test_api_fuzzing.py::test_error_schema_compliance"],
        "category": "fuzz",
        "priority": "medium",
    },
    # Traceability Requirements (US7)
    "FR-028": {
        "text": "All requirements MUST have associated tests",
        "tests": ["tests/traceability/test_traceability.py::test_all_requirements_covered"],
        "category": "traceability",
        "priority": "high",
    },
    "FR-029": {
        "text": "Coverage report MUST map tests to requirements",
        "tests": ["tests/traceability/test_traceability.py::test_coverage_report_generated"],
        "category": "traceability",
        "priority": "medium",
    },
}


def build_traceability_matrix() -> TraceabilityMatrix:
    """Build the traceability matrix from the requirement map."""
    from datetime import datetime

    mappings = []
    for req_id, data in REQUIREMENT_TEST_MAP.items():
        mapping = RequirementTestMapping(
            requirement_id=req_id,
            requirement_text=data["text"],
            test_files=[t.split("::")[0] for t in data["tests"]],
            test_functions=data["tests"],
            coverage_status="uncovered",  # Will be updated by actual test runs
            priority=data["priority"],
            category=data["category"],
        )
        mappings.append(mapping)

    matrix = TraceabilityMatrix(
        mappings=mappings,
        spec_version="005-debug-testing-docker",
        generated_at=datetime.utcnow().isoformat(),
    )
    return matrix
