#!/usr/bin/env bash
# ================================================================
# GRAVITEA-ERP — Detached Test Runner for Claude Code Agents
# ================================================================
#
# PURPOSE
#   Runs pytest outside of Claude Code so test output doesn't
#   consume tokens. Results are written to files that agents
#   can read cheaply (~20 lines instead of ~2000).
#
# HOW IT WORKS
#   Default mode (no flags):
#     Launches pytest as an invisible background process via
#     setsid/nohup. The calling shell returns immediately.
#     Check progress via the .status file.
#
#   --visible mode:
#     Opens a NEW Windows Terminal tab where you can watch
#     pytest run in real-time. The calling shell still returns
#     immediately. Same output files are generated.
#
#   --fg mode:
#     Runs pytest in the current terminal (blocking). Useful
#     for manual debugging. If stdout is a TTY, output streams
#     to both screen and log file simultaneously.
#
# OUTPUT FILES (in Docs/Tests/)
#   {name}.status   — 1 line: RUNNING | PASSED | FAILED | ERROR
#   {name}.summary  — ~20-30 lines: counts, failures, coverage
#   {name}.log      — Full pytest output (only grep this, never cat)
#
# ================================================================
#
# USAGE FOR CLAUDE CODE AGENTS
#
#   Step 1 — Launch:
#     bash scripts/run-tests-external.sh -n myrun tests/ventas/
#     → Returns immediately with file paths
#
#   Step 2 — Poll status (1 line, ~5 tokens):
#     cat Docs/Tests/myrun.status
#     → RUNNING | PASSED | FAILED | ERROR | NO_TESTS
#
#   Step 3 — Read summary when done (~20 lines, ~100 tokens):
#     cat Docs/Tests/myrun.summary
#
#   Step 4 — Debug specific failures only if needed:
#     grep "FAILED" Docs/Tests/myrun.log
#     grep -A5 "test_specific_name" Docs/Tests/myrun.log
#
#   NEVER read the full .log file — it defeats the purpose.
#
# USAGE FOR HUMANS
#
#   Watch tests live in a new terminal tab:
#     bash scripts/run-tests-external.sh --visible -n myrun tests/
#
#   Run interactively in current terminal:
#     bash scripts/run-tests-external.sh --fg tests/ventas/
#
#   Quick smoke test (no coverage, minimal output):
#     bash scripts/run-tests-external.sh --visible -n smoke --no-cov --quiet tests/ventas/integration/test_smoke.py
#
#   Full regression:
#     bash scripts/run-tests-external.sh --visible -n full-regression tests/
#
#   Only unit tests, fail on first error:
#     bash scripts/run-tests-external.sh --visible -n units -m "unit" --fail-fast tests/
#
# ================================================================

set -euo pipefail

# ── Resolve project paths ──────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_PYTHON="$BACKEND_DIR/venv-wsl/bin/python"
OUTPUT_DIR="$PROJECT_ROOT/Docs/Tests"

# ── Defaults ───────────────────────────────────────────────────
RUN_NAME=""
MARKERS=""
FILTER=""
TEST_TARGET="tests/"
NO_COV=0
FAIL_FAST=0
QUIET=0
FOREGROUND=0
VISIBLE=0

# ── Parse arguments ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            RUN_NAME="$2"; shift 2 ;;
        -m|--markers)
            MARKERS="$2"; shift 2 ;;
        -k|--filter)
            FILTER="$2"; shift 2 ;;
        --no-cov)
            NO_COV=1; shift ;;
        --fail-fast)
            FAIL_FAST=1; shift ;;
        --quiet)
            QUIET=1; shift ;;
        --fg)
            FOREGROUND=1; shift ;;
        --visible)
            VISIBLE=1; shift ;;
        -h|--help)
            cat <<'HELP'
Usage: scripts/run-tests-external.sh [OPTIONS] [TEST_TARGET]

Runs pytest outside Claude Code. Results go to Docs/Tests/.

Execution modes:
  (default)     Invisible background process (agents use this)
  --visible     Opens a new Windows Terminal tab (humans watch live)
  --fg          Runs in current terminal, blocking (manual debug)

Options:
  -n, --name NAME      Run identifier (default: YYYYMMDD-HHMMSS)
  -m, --markers EXPR   Pytest marker expression (e.g. "unit and not docker")
  -k, --filter EXPR    Pytest -k name filter
  --no-cov             Disable coverage collection (faster)
  --fail-fast          Stop on first failure (-x)
  --quiet              Minimal output (-q -q --tb=line)
  -h, --help           Show this help

Examples (for agents — invisible background):
  scripts/run-tests-external.sh -n t025-verify tests/
  scripts/run-tests-external.sh -n ventas -m "not docker" tests/ventas/

Examples (for humans — visible terminal tab):
  scripts/run-tests-external.sh --visible -n full tests/
  scripts/run-tests-external.sh --visible -n quick --no-cov tests/ventas/

Examples (interactive — blocks current terminal):
  scripts/run-tests-external.sh --fg tests/ventas/unit/

Output files (Docs/Tests/):
  {name}.status   → RUNNING | PASSED | FAILED | ERROR | NO_TESTS
  {name}.summary  → Token-efficient ~20 line summary
  {name}.log      → Full pytest output (grep only, never cat)
HELP
            exit 0 ;;
        -*)
            echo "Error: unknown option '$1'. Use -h for help." >&2
            exit 1 ;;
        *)
            TEST_TARGET="$1"; shift ;;
    esac
done

# ── Auto-generate run name ─────────────────────────────────────
if [[ -z "$RUN_NAME" ]]; then
    RUN_NAME="$(date +%Y%m%d-%H%M%S)"
fi

# ── Ensure output directory ────────────────────────────────────
mkdir -p "$OUTPUT_DIR"

# ── Output file paths ──────────────────────────────────────────
STATUS_FILE="$OUTPUT_DIR/${RUN_NAME}.status"
SUMMARY_FILE="$OUTPUT_DIR/${RUN_NAME}.summary"
LOG_FILE="$OUTPUT_DIR/${RUN_NAME}.log"

# ── Build relaunch args (used by both detach and visible) ──────
RELAUNCH_ARGS=(--fg -n "$RUN_NAME")
[[ -n "$MARKERS" ]] && RELAUNCH_ARGS+=(-m "$MARKERS")
[[ -n "$FILTER" ]]  && RELAUNCH_ARGS+=(-k "$FILTER")
(( NO_COV ))    && RELAUNCH_ARGS+=(--no-cov)
(( FAIL_FAST )) && RELAUNCH_ARGS+=(--fail-fast)
(( QUIET ))     && RELAUNCH_ARGS+=(--quiet)
RELAUNCH_ARGS+=("$TEST_TARGET")

# ── Dispatch: visible | detached | foreground ──────────────────
if (( ! FOREGROUND )); then

    if (( VISIBLE )); then
        # ── VISIBLE MODE: open a new Windows Terminal tab ──────
        if ! command -v wt.exe &>/dev/null; then
            echo "Error: Windows Terminal (wt.exe) not found." >&2
            echo "Install from Microsoft Store or https://aka.ms/terminal" >&2
            echo "Falling back to invisible background mode." >&2
            VISIBLE=0
        fi
    fi

    if (( VISIBLE )); then
        SCRIPT_ABS="$(realpath "${BASH_SOURCE[0]}")"
        QUOTED_ARGS=$(printf '%q ' "${RELAUNCH_ARGS[@]}")

        # Write a temp launcher on Linux filesystem (no CRLF issues)
        TMPSCRIPT=$(mktemp /tmp/gravitea-rte-XXXXXX.sh)
        cat > "$TMPSCRIPT" << LAUNCHER
#!/usr/bin/env bash
echo -e "\033[96m╔══════════════════════════════════════════════╗\033[0m"
echo -e "\033[96m║   GRAVITEA Test Runner — $RUN_NAME\033[0m"
echo -e "\033[96m╚══════════════════════════════════════════════╝\033[0m"
echo ""
bash "$SCRIPT_ABS" $QUOTED_ARGS
RESULT=\$?
echo ""
if [[ \$RESULT -eq 0 ]]; then
    echo -e "\033[92m✓ All tests passed. Press Enter to close.\033[0m"
else
    echo -e "\033[91m✗ Tests had failures (exit \$RESULT). Press Enter to close.\033[0m"
fi
read -r
rm -f "$TMPSCRIPT"
LAUNCHER
        chmod +x "$TMPSCRIPT"

        # Launch new Windows Terminal tab running the launcher in WSL
        wt.exe -w 0 nt wsl.exe bash "$TMPSCRIPT" &>/dev/null &

        echo "Test run '$RUN_NAME' launched in new terminal tab"
        echo "  Status:  $STATUS_FILE"
        echo "  Summary: $SUMMARY_FILE"
        echo "  Log:     $LOG_FILE"
        exit 0
    fi

    # ── DETACHED MODE: invisible background process ────────
    setsid nohup bash "${BASH_SOURCE[0]}" "${RELAUNCH_ARGS[@]}" \
        </dev/null &>/dev/null &
    BG_PID=$!

    echo "Test run '$RUN_NAME' launched (PID: $BG_PID)"
    echo "  Status:  $STATUS_FILE"
    echo "  Summary: $SUMMARY_FILE"
    echo "  Log:     $LOG_FILE"
    exit 0
fi

# ================================================================
# FOREGROUND EXECUTION (reached via --fg, --visible tab, or direct)
# ================================================================

# ── Helper: atomic status write ────────────────────────────────
write_status() {
    echo "$1" > "${STATUS_FILE}.tmp" && mv "${STATUS_FILE}.tmp" "$STATUS_FILE"
}

# Detect if stdout is a real terminal (--visible tab or --fg in terminal)
IS_TTY=0
[[ -t 1 ]] && IS_TTY=1

# ── Validate prerequisites ─────────────────────────────────────
if [[ ! -f "$VENV_PYTHON" ]]; then
    write_status "ERROR"
    {
        echo "ERROR: WSL venv not found at $VENV_PYTHON"
        echo "Fix: cd backend && python3 -m venv venv-wsl && venv-wsl/bin/pip install -r requirements.txt"
    } > "$SUMMARY_FILE"
    (( IS_TTY )) && cat "$SUMMARY_FILE"
    exit 1
fi

if [[ ! -f "$BACKEND_DIR/pytest.ini" ]]; then
    write_status "ERROR"
    echo "ERROR: pytest.ini not found at $BACKEND_DIR/pytest.ini" > "$SUMMARY_FILE"
    (( IS_TTY )) && cat "$SUMMARY_FILE"
    exit 1
fi

# ── Mark as RUNNING ────────────────────────────────────────────
write_status "RUNNING"

# ── Record start time ──────────────────────────────────────────
START_EPOCH=$(date +%s)

# ── Write log header ───────────────────────────────────────────
{
    echo "=== GRAVITEA Test Run: $RUN_NAME ==="
    echo "Started:  $(date -Iseconds)"
    echo "Host:     $(hostname)"
    echo "Python:   $($VENV_PYTHON --version 2>&1)"
    echo "Target:   $TEST_TARGET"
    echo "Markers:  ${MARKERS:-<all>}"
    echo "Filter:   ${FILTER:-<none>}"
    echo "Coverage: $( (( NO_COV )) && echo "disabled" || echo "enabled" )"
    echo "FailFast: $( (( FAIL_FAST )) && echo "yes" || echo "no" )"
    echo "Quiet:    $( (( QUIET )) && echo "yes" || echo "no" )"
    echo "========================================"
    echo ""
} > "$LOG_FILE"

# Show header on screen if in a terminal
(( IS_TTY )) && cat "$LOG_FILE"

# ── Build pytest command ───────────────────────────────────────
PYTEST_CMD=("$VENV_PYTHON" -m pytest "$TEST_TARGET")

[[ -n "$MARKERS" ]] && PYTEST_CMD+=(-m "$MARKERS")
[[ -n "$FILTER" ]]  && PYTEST_CMD+=(-k "$FILTER")
(( NO_COV ))    && PYTEST_CMD+=(--no-cov)
(( FAIL_FAST )) && PYTEST_CMD+=(-x)
(( QUIET ))     && PYTEST_CMD+=(-q -q --tb=line --no-header)

# Log the command being run
echo "Command: ${PYTEST_CMD[*]}" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
(( IS_TTY )) && echo "Command: ${PYTEST_CMD[*]}" && echo ""

# ── Execute pytest ─────────────────────────────────────────────
cd "$BACKEND_DIR"

# Temporarily relax error handling to capture pytest exit code
set +eo pipefail

if (( IS_TTY )); then
    # Terminal mode: stream to both screen AND log file
    "${PYTEST_CMD[@]}" 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=${PIPESTATUS[0]}
else
    # Background mode: log file only (no stdout)
    "${PYTEST_CMD[@]}" >> "$LOG_FILE" 2>&1
    EXIT_CODE=$?
fi

set -eo pipefail

# ── Record timing ──────────────────────────────────────────────
END_EPOCH=$(date +%s)
DURATION=$(( END_EPOCH - START_EPOCH ))

# Append timing to log
echo "" >> "$LOG_FILE"
echo "=== Completed in ${DURATION}s (exit code: $EXIT_CODE) ===" >> "$LOG_FILE"

# ── Generate token-efficient summary ───────────────────────────
{
    echo "=== Test Summary: $RUN_NAME ==="
    echo "Duration: ${DURATION}s"
    echo "Exit:     $EXIT_CODE"
    echo "Target:   $TEST_TARGET"
    [[ -n "$MARKERS" ]] && echo "Markers:  $MARKERS"
    [[ -n "$FILTER" ]]  && echo "Filter:   $FILTER"
    echo ""

    # Extract the pytest result line (e.g. "= 334 passed, 20 skipped in 45.2s =")
    RESULT_LINE=$(tail -20 "$LOG_FILE" | grep -E "[0-9]+ passed" | tail -1 || true)
    if [[ -n "$RESULT_LINE" ]]; then
        echo "$RESULT_LINE"
        echo ""
    fi

    # Extract failed test names
    FAILED_TESTS=$(grep -E "^FAILED " "$LOG_FILE" 2>/dev/null || true)
    if [[ -n "$FAILED_TESTS" ]]; then
        FAIL_COUNT=$(echo "$FAILED_TESTS" | wc -l | tr -d ' ')
        echo "--- Failed ($FAIL_COUNT) ---"
        echo "$FAILED_TESTS"
        echo ""
    fi

    # Extract error lines
    ERROR_TESTS=$(grep -E "^ERROR " "$LOG_FILE" 2>/dev/null || true)
    if [[ -n "$ERROR_TESTS" ]]; then
        ERR_COUNT=$(echo "$ERROR_TESTS" | wc -l | tr -d ' ')
        echo "--- Errors ($ERR_COUNT) ---"
        echo "$ERROR_TESTS"
        echo ""
    fi

    # Extract coverage total line
    COV_LINE=$(grep -E "^TOTAL\s+" "$LOG_FILE" 2>/dev/null | tail -1 || true)
    if [[ -n "$COV_LINE" ]]; then
        echo "--- Coverage ---"
        echo "$COV_LINE"
        echo ""
    fi

    echo "Log: $LOG_FILE"

} > "$SUMMARY_FILE"

# ── Write final status atomically ──────────────────────────────
case $EXIT_CODE in
    0) FINAL_STATUS="PASSED" ;;
    1) FINAL_STATUS="FAILED" ;;
    2) FINAL_STATUS="INTERRUPTED" ;;
    5) FINAL_STATUS="NO_TESTS" ;;
    *) FINAL_STATUS="ERROR" ;;
esac

write_status "$FINAL_STATUS"

# Print summary to screen if in a terminal
if (( IS_TTY )); then
    echo ""
    echo "─────────────────────────────────────────"
    cat "$SUMMARY_FILE"
fi

exit $EXIT_CODE
