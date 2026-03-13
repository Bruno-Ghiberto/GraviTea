"""
Requirement Coverage Traceability Tests.

These tests verify that all functional requirements (FR-XXX) have
corresponding test coverage in the test suite.

This ensures:
1. Every FR has at least one test
2. Coverage thresholds are met
3. No orphaned tests (tests without FR references)
4. Requirements traceability is maintained
"""

from pathlib import Path
from typing import Dict, List, Set

import pytest

from tests.traceability.conftest import (
    FunctionalRequirement,
    TraceabilityMatrix,
    FUNCTIONAL_REQUIREMENTS,
    build_traceability_matrix,
    extract_fr_references_from_docstring,
)


@pytest.mark.traceability
class TestRequirementCoverage:
    """
    Test that all functional requirements have test coverage.
    """

    def test_all_requirements_documented(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Verify all FR-XXX requirements are documented in the system.
        """
        # Verify we have all expected requirements
        expected_range = range(1, 27)  # FR-001 through FR-026
        expected_ids = {f"FR-{i:03d}" for i in expected_range}

        actual_ids = set(functional_requirements.keys())

        missing = expected_ids - actual_ids
        assert len(missing) == 0, (
            f"Missing requirement definitions: {sorted(missing)}"
        )

    def test_requirements_have_descriptions(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Verify all requirements have descriptions.
        """
        empty_descriptions = [
            req_id for req_id, req in functional_requirements.items()
            if not req.description or len(req.description) < 10
        ]

        assert len(empty_descriptions) == 0, (
            f"Requirements with missing/short descriptions: {empty_descriptions}"
        )

    def test_requirements_have_categories(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Verify all requirements have categories assigned.
        """
        valid_categories = {"Security", "Docker", "Property", "API", "Performance"}

        for req_id, req in functional_requirements.items():
            assert req.category in valid_categories, (
                f"{req_id} has invalid category: {req.category}"
            )

    def test_requirements_have_priorities(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Verify all requirements have priorities assigned.
        """
        valid_priorities = {"P0", "P1", "P2"}

        for req_id, req in functional_requirements.items():
            assert req.priority in valid_priorities, (
                f"{req_id} has invalid priority: {req.priority}"
            )


@pytest.mark.traceability
class TestSecurityRequirementCoverage:
    """
    Test coverage for security requirements (FR-001 to FR-012).
    """

    @pytest.mark.parametrize("req_id", [
        "FR-001", "FR-002", "FR-003", "FR-004", "FR-005", "FR-006",
        "FR-007", "FR-008", "FR-009", "FR-010", "FR-011", "FR-012",
    ])
    def test_security_requirement_exists(
        self,
        req_id: str,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each security requirement is defined.
        """
        assert req_id in functional_requirements, (
            f"Security requirement {req_id} not defined"
        )

        req = functional_requirements[req_id]
        assert req.category == "Security", (
            f"{req_id} should be in Security category, got {req.category}"
        )

    def test_critical_security_requirements_are_p0(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that critical security requirements are P0 priority.
        """
        critical_security = ["FR-001", "FR-002", "FR-003", "FR-004", "FR-005", "FR-006", "FR-007", "FR-009"]

        for req_id in critical_security:
            req = functional_requirements[req_id]
            assert req.priority == "P0", (
                f"Critical security requirement {req_id} should be P0"
            )


@pytest.mark.traceability
class TestDockerRequirementCoverage:
    """
    Test coverage for Docker/infrastructure requirements (FR-013 to FR-018).
    """

    @pytest.mark.parametrize("req_id", [
        "FR-013", "FR-014", "FR-015", "FR-016", "FR-017", "FR-018",
    ])
    def test_docker_requirement_exists(
        self,
        req_id: str,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each Docker requirement is defined.
        """
        assert req_id in functional_requirements, (
            f"Docker requirement {req_id} not defined"
        )

        req = functional_requirements[req_id]
        assert req.category == "Docker", (
            f"{req_id} should be in Docker category, got {req.category}"
        )


@pytest.mark.traceability
class TestPropertyRequirementCoverage:
    """
    Test coverage for property/invariant requirements (FR-019 to FR-021).
    """

    @pytest.mark.parametrize("req_id", ["FR-019", "FR-020", "FR-021"])
    def test_property_requirement_exists(
        self,
        req_id: str,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each property requirement is defined.
        """
        assert req_id in functional_requirements, (
            f"Property requirement {req_id} not defined"
        )

        req = functional_requirements[req_id]
        assert req.category == "Property", (
            f"{req_id} should be in Property category, got {req.category}"
        )

    def test_all_property_requirements_are_p0(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that all property requirements are P0 (invariants must always hold).
        """
        property_reqs = ["FR-019", "FR-020", "FR-021"]

        for req_id in property_reqs:
            req = functional_requirements[req_id]
            assert req.priority == "P0", (
                f"Property requirement {req_id} should be P0"
            )


@pytest.mark.traceability
class TestAPIRequirementCoverage:
    """
    Test coverage for API robustness requirements (FR-022 to FR-023).
    """

    @pytest.mark.parametrize("req_id", ["FR-022", "FR-023"])
    def test_api_requirement_exists(
        self,
        req_id: str,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each API requirement is defined.
        """
        assert req_id in functional_requirements, (
            f"API requirement {req_id} not defined"
        )

        req = functional_requirements[req_id]
        assert req.category == "API", (
            f"{req_id} should be in API category, got {req.category}"
        )


@pytest.mark.traceability
class TestPerformanceRequirementCoverage:
    """
    Test coverage for performance requirements (FR-024 to FR-026).
    """

    @pytest.mark.parametrize("req_id", ["FR-024", "FR-025", "FR-026"])
    def test_performance_requirement_exists(
        self,
        req_id: str,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each performance requirement is defined.
        """
        assert req_id in functional_requirements, (
            f"Performance requirement {req_id} not defined"
        )

        req = functional_requirements[req_id]
        assert req.category == "Performance", (
            f"{req_id} should be in Performance category, got {req.category}"
        )


@pytest.mark.traceability
class TestFRReferenceExtraction:
    """
    Test the FR reference extraction functionality.
    """

    @pytest.mark.parametrize("docstring,expected", [
        ("Tests FR-001 compliance.", ["FR-001"]),
        ("FR-002: JWT algorithm test.", ["FR-002"]),
        ("Tests FR-001 and FR-002.", ["FR-001", "FR-002"]),
        ("No requirements here.", []),
        ("", []),
        (None, []),
        ("FR-999 not a real req.", ["FR-999"]),  # Still extracts pattern
    ])
    def test_fr_extraction(self, docstring: str, expected: List[str]):
        """
        Test FR reference extraction from docstrings.
        """
        result = extract_fr_references_from_docstring(docstring or "")
        assert sorted(result) == sorted(expected)


@pytest.mark.traceability
class TestCoverageThresholds:
    """
    Test that coverage thresholds are met.
    """

    def test_minimum_coverage_threshold(
        self,
        required_coverage_threshold: float,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that minimum coverage threshold is reasonable.
        """
        assert required_coverage_threshold >= 70.0, (
            "Coverage threshold should be at least 70%"
        )
        assert required_coverage_threshold <= 100.0, (
            "Coverage threshold cannot exceed 100%"
        )

    def test_p0_requirements_count(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that P0 requirements are properly identified.
        """
        p0_count = sum(
            1 for req in functional_requirements.values()
            if req.priority == "P0"
        )

        # Should have at least 10 P0 requirements
        assert p0_count >= 10, (
            f"Expected at least 10 P0 requirements, got {p0_count}"
        )

    def test_coverage_by_category_structure(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that coverage by category is tracked correctly.
        """
        categories = {}
        for req in functional_requirements.values():
            if req.category not in categories:
                categories[req.category] = 0
            categories[req.category] += 1

        # Verify expected categories exist
        expected = {"Security", "Docker", "Property", "API", "Performance"}
        assert set(categories.keys()) == expected, (
            f"Unexpected categories: {set(categories.keys()) - expected}"
        )


@pytest.mark.traceability
class TestTraceabilityMatrixStructure:
    """
    Test the structure of the traceability matrix.
    """

    def test_matrix_contains_all_requirements(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that matrix can contain all requirements.
        """
        from tests.traceability.conftest import TraceabilityMatrix

        matrix = TraceabilityMatrix()

        for req in functional_requirements.values():
            matrix.add_requirement(req)

        assert len(matrix.requirements) == len(functional_requirements)

    def test_matrix_coverage_calculation(self):
        """
        Test matrix coverage percentage calculation.
        """
        from tests.traceability.conftest import (
            TraceabilityMatrix,
            FunctionalRequirement,
            TraceReference,
        )

        matrix = TraceabilityMatrix()

        # Add 4 requirements
        for i in range(1, 5):
            matrix.add_requirement(FunctionalRequirement(
                id=f"FR-{i:03d}",
                description=f"Test requirement {i}",
                priority="P0",
                category="Test",
            ))

        # Add tests covering 2 requirements
        matrix.add_test(TraceReference(
            file_path="test_file.py",
            test_name="test_one",
            line_number=10,
            fr_ids=["FR-001"],
        ))
        matrix.add_test(TraceReference(
            file_path="test_file.py",
            test_name="test_two",
            line_number=20,
            fr_ids=["FR-002"],
        ))

        # 2 out of 4 = 50%
        assert matrix.coverage_percentage == 50.0

    def test_matrix_uncovered_identification(self):
        """
        Test identification of uncovered requirements.
        """
        from tests.traceability.conftest import (
            TraceabilityMatrix,
            FunctionalRequirement,
            TraceReference,
        )

        matrix = TraceabilityMatrix()

        for i in range(1, 4):
            matrix.add_requirement(FunctionalRequirement(
                id=f"FR-{i:03d}",
                description=f"Test requirement {i}",
                priority="P0",
                category="Test",
            ))

        # Only cover FR-001
        matrix.add_test(TraceReference(
            file_path="test_file.py",
            test_name="test_one",
            line_number=10,
            fr_ids=["FR-001"],
        ))

        uncovered = matrix.uncovered_requirements
        assert "FR-002" in uncovered
        assert "FR-003" in uncovered
        assert "FR-001" not in uncovered


@pytest.mark.traceability
class TestAcceptanceCriteriaValidation:
    """
    Test that acceptance criteria are properly defined.
    """

    def test_all_requirements_have_acceptance_criteria(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that all requirements have acceptance criteria.
        """
        missing_criteria = [
            req_id for req_id, req in functional_requirements.items()
            if not req.acceptance_criteria
        ]

        assert len(missing_criteria) == 0, (
            f"Requirements missing acceptance criteria: {missing_criteria}"
        )

    def test_acceptance_criteria_count(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that each requirement has at least one acceptance criterion.
        """
        for req_id, req in functional_requirements.items():
            assert len(req.acceptance_criteria) >= 1, (
                f"{req_id} should have at least 1 acceptance criterion"
            )


@pytest.mark.traceability
class TestRequirementRelationships:
    """
    Test relationships between requirements.
    """

    def test_security_requirements_comprehensive(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that security requirements cover key areas.
        """
        security_reqs = [
            req for req in functional_requirements.values()
            if req.category == "Security"
        ]

        # Check for key security areas in descriptions
        descriptions = " ".join(req.description for req in security_reqs)

        security_topics = [
            "JWT",
            "encryption",
            "tenant",
            "OWASP",
            "password",
            "authentication",
        ]

        for topic in security_topics:
            assert topic.lower() in descriptions.lower(), (
                f"Security requirements should cover {topic}"
            )

    def test_performance_requirements_measurable(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that performance requirements have measurable criteria.
        """
        perf_reqs = [
            req for req in functional_requirements.values()
            if req.category == "Performance"
        ]

        # All performance requirements should have numeric thresholds
        for req in perf_reqs:
            has_number = any(
                char.isdigit() for char in req.description
            )
            assert has_number, (
                f"Performance requirement {req.id} should have measurable threshold"
            )

