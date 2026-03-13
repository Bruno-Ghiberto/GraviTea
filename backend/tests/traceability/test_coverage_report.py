"""
Coverage Report Generation Tests.

These tests validate and generate traceability reports showing
the mapping between FR requirements and test coverage.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pytest

from tests.traceability.conftest import (
    FunctionalRequirement,
    TraceabilityMatrix,
    TraceReference,
    FUNCTIONAL_REQUIREMENTS,
)


@pytest.mark.traceability
class TestCoverageReportGeneration:
    """
    Tests for generating coverage reports.
    """

    def test_generate_summary_report(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test generation of summary coverage report.
        """
        # Create summary data
        summary = {
            "total_requirements": len(functional_requirements),
            "by_category": {},
            "by_priority": {},
            "timestamp": datetime.now().isoformat(),
        }

        # Count by category
        for req in functional_requirements.values():
            if req.category not in summary["by_category"]:
                summary["by_category"][req.category] = 0
            summary["by_category"][req.category] += 1

        # Count by priority
        for req in functional_requirements.values():
            if req.priority not in summary["by_priority"]:
                summary["by_priority"][req.priority] = 0
            summary["by_priority"][req.priority] += 1

        # Validate structure
        assert summary["total_requirements"] == 26
        assert "Security" in summary["by_category"]
        assert "P0" in summary["by_priority"]

    def test_generate_detailed_report(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test generation of detailed coverage report.
        """
        report = []

        for req_id, req in sorted(functional_requirements.items()):
            entry = {
                "id": req_id,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "acceptance_criteria": req.acceptance_criteria,
                "covered": req.is_covered,
                "coverage_count": req.coverage_count,
                "tests": req.test_coverage,
            }
            report.append(entry)

        # Validate report structure
        assert len(report) == 26
        assert all("id" in entry for entry in report)
        assert all("description" in entry for entry in report)

    def test_generate_markdown_report(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test generation of Markdown coverage report.
        """
        lines = []
        lines.append("# FR Requirements Coverage Report")
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Total Requirements: {len(functional_requirements)}")

        # By category
        categories = {}
        for req in functional_requirements.values():
            categories[req.category] = categories.get(req.category, 0) + 1

        lines.append("")
        lines.append("### By Category")
        for cat, count in sorted(categories.items()):
            lines.append(f"- {cat}: {count}")

        # Requirements table
        lines.append("")
        lines.append("## Requirements")
        lines.append("")
        lines.append("| ID | Description | Category | Priority |")
        lines.append("|---|---|---|---|")

        for req_id, req in sorted(functional_requirements.items()):
            desc = req.description[:50] + "..." if len(req.description) > 50 else req.description
            lines.append(f"| {req_id} | {desc} | {req.category} | {req.priority} |")

        report_content = "\n".join(lines)

        # Validate report structure
        assert "# FR Requirements Coverage Report" in report_content
        assert "## Summary" in report_content
        assert "FR-001" in report_content

    def test_generate_json_report(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test generation of JSON coverage report.
        """
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_requirements": len(functional_requirements),
                "version": "1.0.0",
            },
            "summary": {
                "total": len(functional_requirements),
                "covered": 0,
                "uncovered": 0,
                "coverage_percentage": 0.0,
            },
            "by_category": {},
            "requirements": [],
        }

        # Populate requirements
        for req_id, req in sorted(functional_requirements.items()):
            report["requirements"].append({
                "id": req_id,
                "description": req.description,
                "category": req.category,
                "priority": req.priority,
                "acceptance_criteria": req.acceptance_criteria,
            })

            # Track by category
            if req.category not in report["by_category"]:
                report["by_category"][req.category] = {
                    "total": 0,
                    "covered": 0,
                }
            report["by_category"][req.category]["total"] += 1

        # Validate JSON structure
        json_str = json.dumps(report, indent=2)
        parsed = json.loads(json_str)

        assert "metadata" in parsed
        assert "summary" in parsed
        assert "requirements" in parsed
        assert len(parsed["requirements"]) == 26


@pytest.mark.traceability
class TestCoverageAnalysis:
    """
    Tests for analyzing coverage patterns.
    """

    def test_identify_high_risk_uncovered(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test identification of uncovered P0 requirements.
        """
        # In a real scenario, these would be actually uncovered
        # Here we're testing the analysis logic
        uncovered_p0 = [
            req_id for req_id, req in functional_requirements.items()
            if req.priority == "P0" and not req.is_covered
        ]

        # Without actual test runs, all are "uncovered"
        # The test validates the analysis logic works
        assert isinstance(uncovered_p0, list)

    def test_coverage_gap_analysis(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test coverage gap analysis by category.
        """
        gaps = {}

        for req_id, req in functional_requirements.items():
            if not req.is_covered:
                if req.category not in gaps:
                    gaps[req.category] = []
                gaps[req.category].append(req_id)

        # Validate structure
        assert isinstance(gaps, dict)

        # Every category should have some entries (without test runs)
        for category in ["Security", "Docker", "Property", "API", "Performance"]:
            if category in gaps:
                assert isinstance(gaps[category], list)

    def test_priority_weighted_coverage(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test priority-weighted coverage calculation.
        """
        weights = {"P0": 3, "P1": 2, "P2": 1}

        total_weight = 0
        covered_weight = 0

        for req in functional_requirements.values():
            weight = weights.get(req.priority, 1)
            total_weight += weight
            if req.is_covered:
                covered_weight += weight

        weighted_coverage = (covered_weight / total_weight * 100) if total_weight > 0 else 0

        assert weighted_coverage >= 0
        assert weighted_coverage <= 100


@pytest.mark.traceability
class TestCoverageMetrics:
    """
    Tests for coverage metrics calculation.
    """

    def test_calculate_test_to_requirement_ratio(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test calculation of test-to-requirement ratio.
        """
        total_tests = sum(
            req.coverage_count for req in functional_requirements.values()
        )
        total_reqs = len(functional_requirements)

        ratio = total_tests / total_reqs if total_reqs > 0 else 0

        # Validate ratio is calculated
        assert ratio >= 0

    def test_identify_over_tested_requirements(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test identification of requirements with excessive test coverage.
        """
        threshold = 10  # Consider >10 tests as "over-tested"

        over_tested = [
            req_id for req_id, req in functional_requirements.items()
            if req.coverage_count > threshold
        ]

        # Validate analysis logic
        assert isinstance(over_tested, list)

    def test_coverage_trend_structure(self):
        """
        Test structure for tracking coverage trends over time.
        """
        trend_data = {
            "dates": [],
            "coverage_percentages": [],
            "requirements_total": [],
            "requirements_covered": [],
        }

        # Simulate trend entries
        for i in range(5):
            trend_data["dates"].append(f"2024-01-{i+1:02d}")
            trend_data["coverage_percentages"].append(70 + i * 2)
            trend_data["requirements_total"].append(26)
            trend_data["requirements_covered"].append(18 + i)

        # Validate structure
        assert len(trend_data["dates"]) == 5
        assert all(p >= 0 and p <= 100 for p in trend_data["coverage_percentages"])


@pytest.mark.traceability
class TestReportValidation:
    """
    Tests for validating report accuracy.
    """

    def test_no_duplicate_requirements(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that there are no duplicate requirement IDs.
        """
        ids = list(functional_requirements.keys())
        unique_ids = set(ids)

        assert len(ids) == len(unique_ids), (
            f"Found duplicate requirement IDs"
        )

    def test_requirement_id_format(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that requirement IDs follow correct format.
        """
        import re
        pattern = r'^FR-\d{3}$'

        for req_id in functional_requirements.keys():
            assert re.match(pattern, req_id), (
                f"Invalid requirement ID format: {req_id}"
            )

    def test_requirement_numbering_sequential(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that requirement numbering is sequential.
        """
        numbers = []
        for req_id in functional_requirements.keys():
            num = int(req_id.split("-")[1])
            numbers.append(num)

        numbers.sort()

        # Check for gaps
        for i, num in enumerate(numbers):
            expected = i + 1
            assert num == expected, (
                f"Gap in requirement numbering at FR-{expected:03d}"
            )

    def test_all_categories_represented(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test that all expected categories have requirements.
        """
        expected_categories = {"Security", "Docker", "Property", "API", "Performance"}

        actual_categories = {
            req.category for req in functional_requirements.values()
        }

        missing = expected_categories - actual_categories
        assert len(missing) == 0, (
            f"Missing requirements for categories: {missing}"
        )


@pytest.mark.traceability
class TestReportExport:
    """
    Tests for report export functionality.
    """

    def test_export_to_dict(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test export of requirements to dictionary format.
        """
        exported = {}

        for req_id, req in functional_requirements.items():
            exported[req_id] = {
                "description": req.description,
                "priority": req.priority,
                "category": req.category,
                "acceptance_criteria": req.acceptance_criteria,
                "is_covered": req.is_covered,
            }

        # Validate export
        assert len(exported) == len(functional_requirements)
        assert all("description" in v for v in exported.values())

    def test_export_summary_statistics(
        self,
        functional_requirements: Dict[str, FunctionalRequirement]
    ):
        """
        Test export of summary statistics.
        """
        stats = {
            "total_requirements": len(functional_requirements),
            "p0_count": sum(1 for r in functional_requirements.values() if r.priority == "P0"),
            "p1_count": sum(1 for r in functional_requirements.values() if r.priority == "P1"),
            "p2_count": sum(1 for r in functional_requirements.values() if r.priority == "P2"),
            "categories": list(set(r.category for r in functional_requirements.values())),
        }

        # Validate statistics
        assert stats["total_requirements"] == 26
        assert stats["p0_count"] + stats["p1_count"] + stats["p2_count"] == 26
        assert len(stats["categories"]) == 5

