"""
Pytest JSON Logging Plugin
==========================

Provides unified structured JSON logging for CI/CD integration.
Captures test events, timing, and results in machine-readable format.

Usage:
    pytest --json-log=path/to/log.jsonl
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pytest
from _pytest.config import Config
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item
from _pytest.reports import TestReport
from _pytest.runner import CallInfo


class JSONLogHandler:
    """Handler for structured JSON logging of test events."""

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_timings: dict[str, dict] = {}

        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize log file
        self._write_event({
            "event": "session_start",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "python_version": self._get_python_version(),
            "pytest_version": pytest.__version__,
        })

    def _get_python_version(self) -> str:
        """Get Python version string."""
        import sys
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _write_event(self, event: dict[str, Any]):
        """Write an event to the JSON log file (JSONL format)."""
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, default=str) + '\n')

    def log_collection_start(self):
        """Log test collection start."""
        self._write_event({
            "event": "collection_start",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
        })

    def log_collection_finish(self, items: list[Item]):
        """Log test collection finish."""
        tests = []
        for item in items:
            markers = [m.name for m in item.iter_markers()]
            tests.append({
                "nodeid": item.nodeid,
                "name": item.name,
                "path": str(item.path) if hasattr(item, 'path') else str(item.fspath),
                "markers": markers,
            })

        self._write_event({
            "event": "collection_finish",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(items),
            "tests": tests,
        })

    def log_test_start(self, item: Item):
        """Log test start."""
        nodeid = item.nodeid
        self.test_timings[nodeid] = {
            "start": time.time(),
            "setup": None,
            "call": None,
            "teardown": None,
        }

        self._write_event({
            "event": "test_start",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "nodeid": nodeid,
            "name": item.name,
            "location": {
                "file": str(item.path) if hasattr(item, 'path') else str(item.fspath),
                "line": item.reportinfo()[1] if hasattr(item, 'reportinfo') else None,
            },
        })

    def log_test_report(self, report: TestReport):
        """Log test report for each phase (setup, call, teardown)."""
        nodeid = report.nodeid
        phase = report.when  # 'setup', 'call', or 'teardown'

        # Record timing
        if nodeid in self.test_timings:
            self.test_timings[nodeid][phase] = report.duration

        event = {
            "event": f"test_{phase}",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "nodeid": nodeid,
            "phase": phase,
            "outcome": report.outcome,  # 'passed', 'failed', 'skipped'
            "duration_seconds": report.duration,
        }

        # Add failure details
        if report.failed:
            event["failure"] = {
                "longrepr": str(report.longrepr) if report.longrepr else None,
                "sections": [(name, content) for name, content in report.sections],
            }

        # Add skip reason
        if report.skipped:
            event["skip_reason"] = str(report.longrepr[2]) if report.longrepr else None

        # Add captured output
        if report.capstdout:
            event["stdout"] = report.capstdout[:5000]  # Limit size
        if report.capstderr:
            event["stderr"] = report.capstderr[:5000]

        self._write_event(event)

    def log_test_finish(self, nodeid: str, outcome: str):
        """Log test completion with full timing."""
        timing = self.test_timings.get(nodeid, {})
        total_duration = sum(v for v in timing.values() if v is not None)

        self._write_event({
            "event": "test_finish",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "nodeid": nodeid,
            "outcome": outcome,
            "duration_seconds": total_duration,
            "timing_breakdown": {
                "setup": timing.get("setup"),
                "call": timing.get("call"),
                "teardown": timing.get("teardown"),
            },
        })

    def log_session_finish(self, exitstatus: int, stats: dict[str, int]):
        """Log session completion with summary."""
        self._write_event({
            "event": "session_finish",
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "exit_status": exitstatus,
            "summary": stats,
        })


class JSONLoggingPlugin:
    """Pytest plugin for JSON structured logging."""

    def __init__(self, config: Config):
        self.config = config
        log_path = config.getoption("json_log") or config.getini("json_log")

        if log_path:
            self.handler = JSONLogHandler(Path(log_path))
            self.enabled = True
        else:
            self.handler = None
            self.enabled = False

        self._item_outcomes: dict[str, str] = {}

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, items: list[Item]):
        """Called after collection is completed."""
        if self.enabled and self.handler:
            self.handler.log_collection_finish(items)

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_logstart(self, nodeid: str, location: tuple):
        """Called at the start of each test."""
        if self.enabled and self.handler:
            # We need the item, but this hook only gets nodeid
            pass

    @pytest.hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item):
        """Called before test setup."""
        if self.enabled and self.handler:
            self.handler.log_test_start(item)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item: Item, call: CallInfo):
        """Called to create test report for each phase."""
        outcome = yield
        report: TestReport = outcome.get_result()

        if self.enabled and self.handler:
            self.handler.log_test_report(report)

            # Track final outcome
            if report.when == "call" or (report.when == "setup" and report.failed):
                self._item_outcomes[item.nodeid] = report.outcome

    @pytest.hookimpl(trylast=True)
    def pytest_runtest_teardown(self, item: Item):
        """Called after test teardown."""
        if self.enabled and self.handler:
            outcome = self._item_outcomes.get(item.nodeid, "passed")
            self.handler.log_test_finish(item.nodeid, outcome)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session, exitstatus: int):
        """Called after whole test run finished."""
        if self.enabled and self.handler:
            # Collect stats
            stats = {}
            if hasattr(session, 'testscollected'):
                stats["collected"] = session.testscollected
            if hasattr(session, 'testsfailed'):
                stats["failed"] = session.testsfailed

            # Count outcomes
            outcome_counts = {}
            for outcome in self._item_outcomes.values():
                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            stats.update(outcome_counts)

            self.handler.log_session_finish(exitstatus, stats)


def pytest_addoption(parser: Parser):
    """Add command line options."""
    group = parser.getgroup("json_logging", "JSON structured logging")
    group.addoption(
        "--json-log",
        dest="json_log",
        default=None,
        help="Path to JSON log file (JSONL format)",
    )

    parser.addini(
        "json_log",
        "Default path for JSON log file",
        default=None,
    )


def pytest_configure(config: Config):
    """Configure the plugin."""
    config.pluginmanager.register(JSONLoggingPlugin(config), "json_logging_plugin")
