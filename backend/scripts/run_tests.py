#!/usr/bin/env python3
"""
Gravitea ERP - Test Orchestration Script
=========================================

Cross-platform Python script for comprehensive test automation.
Handles Docker infrastructure, pytest execution, and structured logging.

Usage:
    python scripts/run_tests.py                    # Run all tests
    python scripts/run_tests.py --markers unit     # Run specific markers
    python scripts/run_tests.py --no-docker        # Skip Docker setup
    python scripts/run_tests.py --coverage-only    # Run with coverage focus
    python scripts/run_tests.py --quick            # Smoke tests only
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class TestRunConfig:
    """Configuration for a test run."""
    markers: list[str] = field(default_factory=list)
    no_docker: bool = False
    coverage_only: bool = False
    quick: bool = False
    verbose: int = 1
    parallel: bool = False
    max_workers: int = 4
    timeout: int = 300
    fail_fast: bool = False
    keep_containers: bool = False


@dataclass
class TestRunResult:
    """Result of a test run."""
    success: bool
    exit_code: int
    start_time: str
    end_time: str
    duration_seconds: float
    tests_collected: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    tests_errors: int = 0
    coverage_percent: float = 0.0
    docker_setup_time: float = 0.0
    pytest_time: float = 0.0
    output_directory: str = ""
    errors: list[str] = field(default_factory=list)


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def disable(cls):
        """Disable colors for non-TTY outputs."""
        cls.HEADER = cls.BLUE = cls.CYAN = cls.GREEN = ''
        cls.WARNING = cls.FAIL = cls.ENDC = cls.BOLD = ''


class Logger:
    """Unified logger with JSON and console output."""

    def __init__(self, output_dir: Path, verbose: int = 1):
        self.output_dir = output_dir
        self.verbose = verbose
        self.log_file = output_dir / "test_run.log"
        self.json_log_file = output_dir / "test_results.json"
        self.events: list[dict] = []

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize log file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"Test Run Log - {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")

    def _log_event(self, level: str, message: str, data: Optional[dict] = None):
        """Log an event to JSON and file."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data or {}
        }
        self.events.append(event)

        # Write to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{event['timestamp']}] [{level}] {message}\n")
            if data:
                f.write(f"  Data: {json.dumps(data, indent=2)}\n")

    def info(self, message: str, data: Optional[dict] = None):
        """Log info message."""
        self._log_event("INFO", message, data)
        if self.verbose >= 1:
            print(f"{Colors.CYAN}[INFO]{Colors.ENDC} {message}")

    def success(self, message: str, data: Optional[dict] = None):
        """Log success message."""
        self._log_event("SUCCESS", message, data)
        print(f"{Colors.GREEN}[OK]{Colors.ENDC} {message}")

    def warning(self, message: str, data: Optional[dict] = None):
        """Log warning message."""
        self._log_event("WARNING", message, data)
        print(f"{Colors.WARNING}[WARN]{Colors.ENDC} {message}")

    def error(self, message: str, data: Optional[dict] = None):
        """Log error message."""
        self._log_event("ERROR", message, data)
        print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {message}")

    def phase(self, message: str):
        """Log phase header."""
        self._log_event("PHASE", message)
        print(f"\n{Colors.HEADER}{Colors.BOLD}=== {message} ==={Colors.ENDC}")

    def save_json(self, result: TestRunResult):
        """Save complete JSON log with results."""
        output = {
            "run_info": asdict(result),
            "events": self.events
        }
        with open(self.json_log_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, default=str)


class DockerManager:
    """Manage Docker test infrastructure."""

    def __init__(self, project_root: Path, logger: Logger):
        self.project_root = project_root
        self.logger = logger
        self.compose_file = project_root / "docker-compose.test.yml"
        self.containers_started = False

    def _run_compose(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run docker-compose command."""
        cmd = ["docker", "compose", "-f", str(self.compose_file)] + list(args)
        self.logger.info(f"Running: {' '.join(cmd)}")

        return subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=check
        )

    def health_check(self, service: str, max_retries: int = 30, interval: float = 2.0) -> bool:
        """Wait for a service to become healthy."""
        self.logger.info(f"Waiting for {service} to be healthy...")

        for attempt in range(max_retries):
            try:
                result = self._run_compose("ps", service, "--format", "json", check=False)
                if result.returncode == 0 and result.stdout.strip():
                    # Parse JSON output
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            container_info = json.loads(line)
                            health = container_info.get("Health", "")
                            state = container_info.get("State", "")

                            if health == "healthy" or (state == "running" and not health):
                                self.logger.success(f"{service} is healthy")
                                return True
                            elif state == "exited":
                                self.logger.error(f"{service} has exited unexpectedly")
                                return False
            except (json.JSONDecodeError, KeyError):
                pass

            if self.logger.verbose >= 2:
                print(f"  Attempt {attempt + 1}/{max_retries}...")
            time.sleep(interval)

        self.logger.error(f"{service} failed to become healthy after {max_retries * interval}s")
        return False

    def _verify_http_endpoint(self, url: str, max_retries: int = 30, interval: float = 2.0) -> bool:
        """Verify an HTTP endpoint is responding with 200 OK."""
        import urllib.request
        import urllib.error

        self.logger.info(f"Verifying HTTP endpoint: {url}")

        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        self.logger.success(f"HTTP endpoint {url} is responding")
                        return True
            except urllib.error.URLError as e:
                if self.logger.verbose >= 2:
                    print(f"  Attempt {attempt + 1}/{max_retries}: {e.reason}")
            except Exception as e:
                if self.logger.verbose >= 2:
                    print(f"  Attempt {attempt + 1}/{max_retries}: {e}")

            time.sleep(interval)

        self.logger.error(f"HTTP endpoint {url} not responding after {max_retries * interval}s")
        return False

    def start(self) -> tuple[bool, float]:
        """Start Docker test infrastructure."""
        start_time = time.time()

        self.logger.phase("Starting Docker Infrastructure")

        if not self.compose_file.exists():
            self.logger.error(f"Compose file not found: {self.compose_file}")
            return False, 0.0

        # Pull latest images
        self.logger.info("Pulling Docker images...")
        result = self._run_compose("pull", check=False)
        if result.returncode != 0:
            self.logger.warning("Failed to pull images, using cached versions")

        # Start containers
        self.logger.info("Starting test containers...")
        result = self._run_compose("up", "-d", "--remove-orphans", check=False)
        if result.returncode != 0:
            self.logger.error(f"Failed to start containers: {result.stderr}")
            return False, time.time() - start_time

        self.containers_started = True

        # Wait for health checks - database and cache first
        core_services = ["postgres-test", "redis-test"]
        for service in core_services:
            if not self.health_check(service):
                return False, time.time() - start_time

        # Wait for web-test to be ready (depends on db/redis)
        if not self.health_check("web-test", max_retries=60, interval=2.0):
            self.logger.warning("web-test not healthy - smoke tests may fail")

        # Verify HTTP endpoint is actually responding
        if not self._verify_http_endpoint("http://localhost:8001/health/live", max_retries=30):
            self.logger.warning("Backend HTTP endpoint not responding - smoke tests may fail")

        self.logger.info("Waiting for services to stabilize...")
        time.sleep(2)

        duration = time.time() - start_time
        self.logger.success(f"Docker infrastructure ready in {duration:.1f}s")
        return True, duration

    def stop(self, remove_volumes: bool = False):
        """Stop Docker test infrastructure."""
        self.logger.phase("Stopping Docker Infrastructure")

        if not self.containers_started:
            self.logger.info("No containers to stop")
            return

        args = ["down"]
        if remove_volumes:
            args.append("-v")
        args.append("--remove-orphans")

        result = self._run_compose(*args, check=False)
        if result.returncode == 0:
            self.logger.success("Docker containers stopped")
        else:
            self.logger.warning(f"Error stopping containers: {result.stderr}")

    def logs(self, service: Optional[str] = None) -> str:
        """Get container logs."""
        args = ["logs", "--tail=100"]
        if service:
            args.append(service)

        result = self._run_compose(*args, check=False)
        return result.stdout + result.stderr


class PytestRunner:
    """Run pytest with structured output."""

    def __init__(self, project_root: Path, output_dir: Path, logger: Logger):
        self.project_root = project_root
        self.output_dir = output_dir
        self.logger = logger

    def build_command(self, config: TestRunConfig) -> list[str]:
        """Build pytest command with all options."""
        cmd = [sys.executable, "-m", "pytest"]

        # Test directory
        cmd.append("tests")

        # Output formats
        junit_path = self.output_dir / "test_results.xml"
        html_path = self.output_dir / "test_report.html"

        cmd.extend([
            f"--junitxml={junit_path}",
            f"--html={html_path}",
            "--self-contained-html",
        ])

        # Coverage configuration
        coverage_dir = self.output_dir / "coverage"
        cmd.extend([
            "--cov=apps",
            f"--cov-report=html:{coverage_dir}",
            "--cov-report=json",
            "--cov-report=term-missing",
        ])

        # Only enforce coverage threshold for full test runs (not marker-specific)
        # Unit tests alone cannot achieve 80% coverage since they don't exercise
        # views, serializers, and integration code
        is_marker_specific = bool(config.markers) or config.quick
        if not config.coverage_only and not is_marker_specific:
            cmd.append("--cov-fail-under=80")

        # Verbosity
        if config.verbose >= 2:
            cmd.append("-vv")
        elif config.verbose >= 1:
            cmd.append("-v")

        # Markers
        if config.quick:
            cmd.extend(["-m", "smoke"])
        elif config.markers:
            marker_expr = " or ".join(config.markers)
            cmd.extend(["-m", marker_expr])

        # Parallel execution
        if config.parallel:
            cmd.extend(["-n", str(config.max_workers)])

        # Timeout
        cmd.extend(["--timeout", str(config.timeout)])

        # Fail fast
        if config.fail_fast:
            cmd.append("-x")

        # Strict markers
        cmd.append("--strict-markers")

        # Color output
        cmd.append("--color=yes")

        # TB format for better error display
        cmd.append("--tb=short")

        return cmd

    def run(self, config: TestRunConfig) -> tuple[int, float, dict]:
        """Run pytest and return exit code, duration, and stats."""
        self.logger.phase("Running Tests")

        cmd = self.build_command(config)
        self.logger.info(f"Command: {' '.join(cmd)}")

        start_time = time.time()

        # Set environment variables
        env = os.environ.copy()
        env.update({
            "DJANGO_SETTINGS_MODULE": "gravitea.settings.test",
            "PYTHONPATH": str(self.project_root),
            "PYTEST_CURRENT_TEST": "1",
            "COVERAGE_FILE": str(self.output_dir / ".coverage"),
        })

        # Run pytest
        process = subprocess.Popen(
            cmd,
            cwd=self.project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Stream output in real-time
        output_lines = []
        try:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                output_lines.append(line)
        except KeyboardInterrupt:
            self.logger.warning("Test run interrupted by user")
            process.terminate()
            process.wait(timeout=10)
            raise

        process.wait()
        duration = time.time() - start_time

        # Parse results from JUnit XML
        stats = self._parse_results()

        if process.returncode == 0:
            self.logger.success(f"Tests completed in {duration:.1f}s")
        else:
            self.logger.error(f"Tests failed with exit code {process.returncode}")

        return process.returncode, duration, stats

    def _parse_results(self) -> dict:
        """Parse test results from JUnit XML."""
        junit_path = self.output_dir / "test_results.xml"
        stats = {
            "collected": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

        if not junit_path.exists():
            return stats

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_path)
            root = tree.getroot()

            # Handle both single testsuite and testsuites format
            if root.tag == "testsuites":
                for testsuite in root.findall("testsuite"):
                    stats["collected"] += int(testsuite.get("tests", 0))
                    stats["failed"] += int(testsuite.get("failures", 0))
                    stats["errors"] += int(testsuite.get("errors", 0))
                    stats["skipped"] += int(testsuite.get("skipped", 0))
            else:
                stats["collected"] = int(root.get("tests", 0))
                stats["failed"] = int(root.get("failures", 0))
                stats["errors"] = int(root.get("errors", 0))
                stats["skipped"] = int(root.get("skipped", 0))

            stats["passed"] = stats["collected"] - stats["failed"] - stats["errors"] - stats["skipped"]

        except Exception as e:
            self.logger.warning(f"Failed to parse JUnit XML: {e}")

        return stats

    def get_coverage(self) -> float:
        """Get coverage percentage from coverage.json."""
        coverage_json = self.output_dir / "coverage.json"
        if not coverage_json.exists():
            # Try alternate location
            coverage_json = self.project_root / "coverage.json"

        if coverage_json.exists():
            try:
                with open(coverage_json) as f:
                    data = json.load(f)
                    return data.get("totals", {}).get("percent_covered", 0.0)
            except Exception:
                pass

        return 0.0


class TestOrchestrator:
    """Main test orchestration class."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.output_base = self.project_root / "tests" / "Logs_report"
        self.current_run_dir: Optional[Path] = None
        self.logger: Optional[Logger] = None
        self.docker: Optional[DockerManager] = None
        self.pytest_runner: Optional[PytestRunner] = None
        self._interrupted = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signals gracefully."""
        if self._interrupted:
            print("\nForce quitting...")
            sys.exit(1)

        self._interrupted = True
        print("\n\nInterrupted. Cleaning up...")

        if self.docker:
            self.docker.stop()

        sys.exit(130)

    def _setup_output_directory(self) -> Path:
        """Create timestamped output directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = self.output_base / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        # Create symlink to latest run
        latest_link = self.output_base / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        elif latest_link.exists():
            shutil.rmtree(latest_link)

        try:
            latest_link.symlink_to(run_dir.name, target_is_directory=True)
        except OSError:
            # Symlinks may not work on Windows without admin
            pass

        return run_dir

    def run(self, config: TestRunConfig) -> TestRunResult:
        """Execute complete test run."""
        start_time = datetime.now()

        # Disable colors if not TTY
        if not sys.stdout.isatty():
            Colors.disable()

        # Setup output directory
        self.current_run_dir = self._setup_output_directory()
        self.logger = Logger(self.current_run_dir, config.verbose)

        self.logger.phase("Gravitea ERP Test Orchestrator")
        self.logger.info(f"Project root: {self.project_root}")
        self.logger.info(f"Output directory: {self.current_run_dir}")
        self.logger.info(f"Configuration: {config}")

        # Initialize result
        result = TestRunResult(
            success=False,
            exit_code=1,
            start_time=start_time.isoformat(),
            end_time="",
            duration_seconds=0.0,
            output_directory=str(self.current_run_dir),
        )

        docker_time = 0.0
        pytest_time = 0.0

        try:
            # Start Docker if needed
            if not config.no_docker:
                self.docker = DockerManager(self.project_root, self.logger)
                success, docker_time = self.docker.start()
                result.docker_setup_time = docker_time

                if not success:
                    result.errors.append("Docker infrastructure failed to start")
                    self.logger.error("Docker setup failed. Check logs above.")

                    # Save container logs for debugging
                    logs = self.docker.logs()
                    logs_file = self.current_run_dir / "docker_logs.txt"
                    with open(logs_file, 'w') as f:
                        f.write(logs)

                    raise RuntimeError("Docker infrastructure failed")

            # Run pytest
            self.pytest_runner = PytestRunner(
                self.project_root,
                self.current_run_dir,
                self.logger
            )

            exit_code, pytest_time, stats = self.pytest_runner.run(config)

            result.exit_code = exit_code
            result.pytest_time = pytest_time
            result.tests_collected = stats["collected"]
            result.tests_passed = stats["passed"]
            result.tests_failed = stats["failed"]
            result.tests_skipped = stats["skipped"]
            result.tests_errors = stats["errors"]
            result.coverage_percent = self.pytest_runner.get_coverage()
            result.success = exit_code == 0

        except KeyboardInterrupt:
            result.errors.append("Test run interrupted by user")
            result.exit_code = 130
        except Exception as e:
            self.logger.error(f"Test orchestration failed: {e}")
            result.errors.append(str(e))
            result.exit_code = 1
        finally:
            # Cleanup Docker
            if self.docker and not config.keep_containers:
                self.docker.stop(remove_volumes=True)

            # Finalize result
            end_time = datetime.now()
            result.end_time = end_time.isoformat()
            result.duration_seconds = (end_time - start_time).total_seconds()

            # Print summary
            self._print_summary(result)

            # Save JSON log
            self.logger.save_json(result)

            # Save run summary
            summary_file = self.current_run_dir / "run_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(asdict(result), f, indent=2)

        return result

    def _print_summary(self, result: TestRunResult):
        """Print test run summary."""
        self.logger.phase("Test Run Summary")

        status = f"{Colors.GREEN}PASSED{Colors.ENDC}" if result.success else f"{Colors.FAIL}FAILED{Colors.ENDC}"

        print(f"""
+------------------------------------------------------------+
|  Status: {status}
|  Duration: {result.duration_seconds:.1f}s (Docker: {result.docker_setup_time:.1f}s, Tests: {result.pytest_time:.1f}s)
|
|  Tests:
|    Collected: {result.tests_collected}
|    Passed:    {Colors.GREEN}{result.tests_passed}{Colors.ENDC}
|    Failed:    {Colors.FAIL if result.tests_failed else ''}{result.tests_failed}{Colors.ENDC if result.tests_failed else ''}
|    Skipped:   {result.tests_skipped}
|    Errors:    {Colors.FAIL if result.tests_errors else ''}{result.tests_errors}{Colors.ENDC if result.tests_errors else ''}
|
|  Coverage: {result.coverage_percent:.1f}%
|
|  Outputs:
|    {self.current_run_dir / 'test_results.xml'}
|    {self.current_run_dir / 'test_report.html'}
|    {self.current_run_dir / 'coverage/'}
+------------------------------------------------------------+
""")

        if result.errors:
            print(f"\n{Colors.FAIL}Errors:{Colors.ENDC}")
            for error in result.errors:
                print(f"  - {error}")


def parse_args() -> TestRunConfig:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Gravitea ERP Test Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_tests.py                     # Run all tests
  python scripts/run_tests.py --quick             # Run smoke tests only
  python scripts/run_tests.py -m unit integration # Run unit and integration tests
  python scripts/run_tests.py --no-docker         # Skip Docker setup
  python scripts/run_tests.py --parallel -n 4     # Run in parallel
  python scripts/run_tests.py --keep-containers   # Don't stop containers after
        """
    )

    parser.add_argument(
        "-m", "--markers",
        nargs="+",
        default=[],
        help="Pytest markers to run (e.g., unit, integration, security)"
    )
    parser.add_argument(
        "--no-docker",
        action="store_true",
        help="Skip Docker infrastructure setup"
    )
    parser.add_argument(
        "--coverage-only",
        action="store_true",
        help="Run for coverage without failing on threshold"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Run smoke tests only for quick validation"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=1,
        help="Increase verbosity (-v, -vv)"
    )
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )
    parser.add_argument(
        "-n", "--max-workers",
        type=int,
        default=4,
        help="Maximum parallel workers (default: 4)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Test timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "-x", "--fail-fast",
        action="store_true",
        help="Stop on first failure"
    )
    parser.add_argument(
        "--keep-containers",
        action="store_true",
        help="Don't stop Docker containers after tests"
    )

    args = parser.parse_args()

    return TestRunConfig(
        markers=args.markers,
        no_docker=args.no_docker,
        coverage_only=args.coverage_only,
        quick=args.quick,
        verbose=args.verbose,
        parallel=args.parallel,
        max_workers=args.max_workers,
        timeout=args.timeout,
        fail_fast=args.fail_fast,
        keep_containers=args.keep_containers,
    )


def main() -> int:
    """Main entry point."""
    config = parse_args()
    orchestrator = TestOrchestrator()
    result = orchestrator.run(config)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
