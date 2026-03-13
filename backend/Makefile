# Gravitea ERP - Test Automation Makefile
# ==========================================
# Cross-platform test orchestration via Python script
#
# Usage:
#   make test           - Run all tests with Docker
#   make test-quick     - Run smoke tests only
#   make test-unit      - Run unit tests only
#   make test-parallel  - Run tests in parallel
#   make clean          - Clean test artifacts

.PHONY: test test-quick test-unit test-integration test-security test-load test-fuzz test-property test-parallel test-coverage test-no-docker clean help

# Default Python interpreter
PYTHON ?= python

# Test orchestrator script
ORCHESTRATOR = scripts/run_tests.py

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Gravitea ERP Test Orchestration"
	@echo "================================"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "  DAILY DEVELOPMENT:"
	@echo "    make test-unit      - Unit tests only, no Docker (~1-2 min)"
	@echo "    make test-quick     - Smoke tests only (~30 sec)"
	@echo ""
	@echo "  FULL VALIDATION:"
	@echo "    make test           - Full test suite with Docker"
	@echo "    make test-parallel  - Full suite with 4 parallel workers"
	@echo "    make test-coverage  - Focus on coverage metrics"
	@echo ""
	@echo "  SPECIALIZED TESTS:"
	@echo "    make test-integration - Integration tests (database/API)"
	@echo "    make test-security    - Security tests (OWASP, JWT, etc.)"
	@echo "    make test-load        - Load tests (Locust)"
	@echo "    make test-fuzz        - API fuzzing tests (Schemathesis)"
	@echo "    make test-property    - Property-based tests (Hypothesis)"
	@echo ""
	@echo "  UTILITIES:"
	@echo "    make test-no-docker - All tests without Docker setup"
	@echo "    make clean          - Clean test artifacts and caches"
	@echo "    make help           - Show this help message"
	@echo ""
	@echo "Advanced usage:"
	@echo "  $(PYTHON) $(ORCHESTRATOR) --help"
	@echo ""
	@echo "Examples:"
	@echo "  $(PYTHON) $(ORCHESTRATOR) -m unit integration"
	@echo "  $(PYTHON) $(ORCHESTRATOR) --parallel -n 8"
	@echo "  $(PYTHON) $(ORCHESTRATOR) -x --fail-fast"

test:
	$(PYTHON) $(ORCHESTRATOR)

test-quick:
	$(PYTHON) $(ORCHESTRATOR) --quick

test-unit:
	$(PYTHON) $(ORCHESTRATOR) --no-docker -m unit

test-integration:
	$(PYTHON) $(ORCHESTRATOR) -m integration

test-security:
	$(PYTHON) $(ORCHESTRATOR) -m security

test-load:
	$(PYTHON) $(ORCHESTRATOR) -m load

test-fuzz:
	$(PYTHON) $(ORCHESTRATOR) -m fuzz

test-property:
	$(PYTHON) $(ORCHESTRATOR) -m property

test-parallel:
	$(PYTHON) $(ORCHESTRATOR) --parallel -n 4

test-coverage:
	$(PYTHON) $(ORCHESTRATOR) --coverage-only

test-no-docker:
	$(PYTHON) $(ORCHESTRATOR) --no-docker

clean:
	@echo "Cleaning test artifacts..."
	@rm -rf tests/Logs_report/*/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@rm -rf coverage.json
	@rm -rf .pytest_cache/
	@rm -rf **/__pycache__/
	@echo "Clean complete."
