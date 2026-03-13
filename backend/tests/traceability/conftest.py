"""
Traceability Testing Fixtures and Configuration.

Provides fixtures and utilities for verifying FR requirement test coverage.

T032: Added logging for exception handlers to aid debugging.
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pytest

# Configure logging for traceability module
logger = logging.getLogger(__name__)


@dataclass
class FunctionalRequirement:
    """Represents a functional requirement from the specification."""

    id: str
    description: str
    priority: str
    category: str
    acceptance_criteria: List[str] = field(default_factory=list)
    test_coverage: List[str] = field(default_factory=list)

    @property
    def is_covered(self) -> bool:
        """Check if requirement has test coverage."""
        return len(self.test_coverage) > 0

    @property
    def coverage_count(self) -> int:
        """Return number of tests covering this requirement."""
        return len(self.test_coverage)


@dataclass
class TraceReference:
    """Reference to a test covering a requirement.

    Note: Named TraceReference (not TestReference) to avoid pytest collection.
    Pytest collects classes starting with 'Test' as test classes.
    """

    file_path: str
    test_name: str
    line_number: int
    fr_ids: List[str]

    @property
    def full_path(self) -> str:
        """Return full test path."""
        return f"{self.file_path}::{self.test_name}"


@dataclass
class TraceabilityMatrix:
    """Traceability matrix linking requirements to tests."""

    requirements: Dict[str, FunctionalRequirement] = field(default_factory=dict)
    tests: List[TraceReference] = field(default_factory=list)

    def add_requirement(self, req: FunctionalRequirement) -> None:
        """Add a requirement to the matrix."""
        self.requirements[req.id] = req

    def add_test(self, test: TraceReference) -> None:
        """Add a test reference and link to requirements."""
        self.tests.append(test)

        for fr_id in test.fr_ids:
            if fr_id in self.requirements:
                self.requirements[fr_id].test_coverage.append(test.full_path)

    @property
    def covered_requirements(self) -> List[str]:
        """Return list of covered requirement IDs."""
        return [
            req_id for req_id, req in self.requirements.items()
            if req.is_covered
        ]

    @property
    def uncovered_requirements(self) -> List[str]:
        """Return list of uncovered requirement IDs."""
        return [
            req_id for req_id, req in self.requirements.items()
            if not req.is_covered
        ]

    @property
    def coverage_percentage(self) -> float:
        """Calculate coverage percentage."""
        if not self.requirements:
            return 0.0
        return len(self.covered_requirements) / len(self.requirements) * 100

    def get_coverage_by_category(self) -> Dict[str, Tuple[int, int]]:
        """Get coverage by category (covered, total)."""
        categories: Dict[str, Tuple[int, int]] = {}

        for req in self.requirements.values():
            if req.category not in categories:
                categories[req.category] = (0, 0)

            covered, total = categories[req.category]
            total += 1
            if req.is_covered:
                covered += 1
            categories[req.category] = (covered, total)

        return categories


# Define all functional requirements from spec
FUNCTIONAL_REQUIREMENTS = {
    # Security Requirements (FR-001 to FR-012)
    "FR-001": FunctionalRequirement(
        id="FR-001",
        description="JWT tokens MUST expire within 1 hour",
        priority="P0",
        category="Security",
        acceptance_criteria=["Token expiration verified", "Refresh token flow works"],
    ),
    "FR-002": FunctionalRequirement(
        id="FR-002",
        description="JWT tokens MUST use RS256 algorithm",
        priority="P0",
        category="Security",
        acceptance_criteria=["RS256 signing verified", "Invalid algorithms rejected"],
    ),
    "FR-003": FunctionalRequirement(
        id="FR-003",
        description="Rate limiting MUST be enforced on authentication endpoints",
        priority="P0",
        category="Security",
        acceptance_criteria=["Rate limits enforced", "429 responses returned"],
    ),
    "FR-004": FunctionalRequirement(
        id="FR-004",
        description="All sensitive data MUST use AES-256 encryption at rest",
        priority="P0",
        category="Security",
        acceptance_criteria=["AES-256 encryption verified", "Key rotation supported"],
    ),
    "FR-005": FunctionalRequirement(
        id="FR-005",
        description="Tenant isolation MUST prevent cross-tenant data access",
        priority="P0",
        category="Security",
        acceptance_criteria=["Cross-tenant queries blocked", "Isolation verified"],
    ),
    "FR-006": FunctionalRequirement(
        id="FR-006",
        description="OWASP Top 10 vulnerabilities MUST be addressed",
        priority="P0",
        category="Security",
        acceptance_criteria=["SQL injection prevented", "XSS prevented", "CSRF protected"],
    ),
    "FR-007": FunctionalRequirement(
        id="FR-007",
        description="Password hashing MUST use Argon2id with secure parameters",
        priority="P0",
        category="Security",
        acceptance_criteria=["Argon2id verified", "Parameters within spec"],
    ),
    "FR-008": FunctionalRequirement(
        id="FR-008",
        description="API keys MUST be hashed before storage",
        priority="P1",
        category="Security",
        acceptance_criteria=["Keys hashed", "Comparison secure"],
    ),
    "FR-009": FunctionalRequirement(
        id="FR-009",
        description="All API endpoints MUST require authentication",
        priority="P0",
        category="Security",
        acceptance_criteria=["Unauthenticated requests blocked", "Token validation works"],
    ),
    "FR-010": FunctionalRequirement(
        id="FR-010",
        description="Session management MUST include secure cookie attributes",
        priority="P1",
        category="Security",
        acceptance_criteria=["HttpOnly set", "Secure set", "SameSite configured"],
    ),
    "FR-011": FunctionalRequirement(
        id="FR-011",
        description="CORS MUST be properly configured",
        priority="P1",
        category="Security",
        acceptance_criteria=["Origins validated", "Credentials handled"],
    ),
    "FR-012": FunctionalRequirement(
        id="FR-012",
        description="Security headers MUST be set on all responses",
        priority="P1",
        category="Security",
        acceptance_criteria=["CSP set", "X-Frame-Options set", "HSTS configured"],
    ),

    # Docker/Infrastructure Requirements (FR-013 to FR-018)
    "FR-013": FunctionalRequirement(
        id="FR-013",
        description="Health check endpoint MUST respond within 200ms",
        priority="P0",
        category="Docker",
        acceptance_criteria=["Response time < 200ms", "Status 200 returned"],
    ),
    "FR-014": FunctionalRequirement(
        id="FR-014",
        description="Readiness probe MUST check database connectivity",
        priority="P0",
        category="Docker",
        acceptance_criteria=["DB connection verified", "Failure detection works"],
    ),
    "FR-015": FunctionalRequirement(
        id="FR-015",
        description="Graceful shutdown MUST complete within 30 seconds",
        priority="P1",
        category="Docker",
        acceptance_criteria=["SIGTERM handled", "Connections drained"],
    ),
    "FR-016": FunctionalRequirement(
        id="FR-016",
        description="Docker network topology MUST isolate services",
        priority="P1",
        category="Docker",
        acceptance_criteria=["Networks defined", "Services isolated"],
    ),
    "FR-017": FunctionalRequirement(
        id="FR-017",
        description="Database connections MUST use CONN_MAX_AGE=0 for containers",
        priority="P1",
        category="Docker",
        acceptance_criteria=["Connection pooling configured", "No stale connections"],
    ),
    "FR-018": FunctionalRequirement(
        id="FR-018",
        description="Observability stack MUST be integrated",
        priority="P1",
        category="Docker",
        acceptance_criteria=["Prometheus metrics exposed", "Logs structured"],
    ),

    # Property/Invariant Requirements (FR-019 to FR-021)
    "FR-019": FunctionalRequirement(
        id="FR-019",
        description="Inventory quantities MUST remain non-negative",
        priority="P0",
        category="Property",
        acceptance_criteria=["Constraint enforced", "Negative values rejected"],
    ),
    "FR-020": FunctionalRequirement(
        id="FR-020",
        description="Prices MUST maintain mathematical consistency",
        priority="P0",
        category="Property",
        acceptance_criteria=["Calculations accurate", "Precision maintained"],
    ),
    "FR-021": FunctionalRequirement(
        id="FR-021",
        description="Tenant ID MUST be consistently applied to all operations",
        priority="P0",
        category="Property",
        acceptance_criteria=["ID propagated", "Isolation maintained"],
    ),

    # API Robustness Requirements (FR-022 to FR-023)
    "FR-022": FunctionalRequirement(
        id="FR-022",
        description="API MUST reject malformed input with appropriate error codes",
        priority="P0",
        category="API",
        acceptance_criteria=["400 for bad requests", "422 for validation errors"],
    ),
    "FR-023": FunctionalRequirement(
        id="FR-023",
        description="API MUST sanitize all inputs to prevent injection attacks",
        priority="P0",
        category="API",
        acceptance_criteria=["SQL injection prevented", "XSS sanitized"],
    ),

    # Performance Requirements (FR-024 to FR-026)
    "FR-024": FunctionalRequirement(
        id="FR-024",
        description="System MUST handle 100 concurrent users with p95 latency < 500ms",
        priority="P0",
        category="Performance",
        acceptance_criteria=["p95 < 500ms", "100 users supported"],
    ),
    "FR-025": FunctionalRequirement(
        id="FR-025",
        description="System MUST handle peak traffic (500 users) with <1% error rate",
        priority="P1",
        category="Performance",
        acceptance_criteria=["Error rate < 1%", "500 users supported"],
    ),
    "FR-026": FunctionalRequirement(
        id="FR-026",
        description="System MUST maintain stable performance over 10-minute periods",
        priority="P1",
        category="Performance",
        acceptance_criteria=["No degradation", "Stability maintained"],
    ),
}


def extract_fr_references_from_docstring(docstring: str) -> List[str]:
    """Extract FR-XXX references from a docstring."""
    if not docstring:
        return []

    # Match FR-XXX patterns
    pattern = r'FR-(\d{3})'
    matches = re.findall(pattern, docstring)

    return [f"FR-{match}" for match in matches]


def extract_fr_references_from_file(file_path: Path) -> List[TraceReference]:
    """Extract test references and FR links from a Python test file."""
    references = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if it's a test function
                if node.name.startswith('test_'):
                    docstring = ast.get_docstring(node)
                    fr_ids = extract_fr_references_from_docstring(docstring or "")

                    # Also check class docstring if inside a class
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            for child in parent.body:
                                if child is node:
                                    class_docstring = ast.get_docstring(parent)
                                    class_fr_ids = extract_fr_references_from_docstring(
                                        class_docstring or ""
                                    )
                                    fr_ids.extend(class_fr_ids)
                                    break

                    if fr_ids:
                        references.append(TraceReference(
                            file_path=str(file_path),
                            test_name=node.name,
                            line_number=node.lineno,
                            fr_ids=list(set(fr_ids)),  # Dedupe
                        ))

    except SyntaxError as e:
        # T032: Log syntax errors instead of silently ignoring
        logger.warning(
            "Syntax error parsing file %s at line %d: %s",
            file_path,
            e.lineno or 0,
            str(e)
        )
    except FileNotFoundError as e:
        # T032: Log file not found errors
        logger.warning("File not found during FR extraction: %s", file_path)
    except Exception as e:
        # T032: Log unexpected errors with full context
        logger.error(
            "Unexpected error extracting FR references from %s: %s",
            file_path,
            str(e),
            exc_info=True
        )

    return references


def scan_test_directory(test_dir: Path) -> List[TraceReference]:
    """Scan a test directory for FR references."""
    all_references = []

    for path in test_dir.rglob('test_*.py'):
        references = extract_fr_references_from_file(path)
        all_references.extend(references)

    return all_references


def build_traceability_matrix(test_dir: Path) -> TraceabilityMatrix:
    """Build a complete traceability matrix."""
    matrix = TraceabilityMatrix()

    # Add all requirements
    for req in FUNCTIONAL_REQUIREMENTS.values():
        matrix.add_requirement(req)

    # Scan for tests
    references = scan_test_directory(test_dir)

    for ref in references:
        matrix.add_test(ref)

    return matrix


@pytest.fixture
def traceability_matrix(request) -> TraceabilityMatrix:
    """Provide traceability matrix for tests."""
    # Get the test directory
    test_dir = Path(request.config.rootdir) / "tests"

    return build_traceability_matrix(test_dir)


@pytest.fixture
def functional_requirements() -> Dict[str, FunctionalRequirement]:
    """Provide functional requirements dictionary."""
    return FUNCTIONAL_REQUIREMENTS.copy()


@pytest.fixture
def required_coverage_threshold() -> float:
    """Return the required coverage threshold percentage."""
    return 80.0  # 80% coverage required

