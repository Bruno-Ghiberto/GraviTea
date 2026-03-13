# 009c — Invoice Module Test Verification: 5-Agent Team with External Test Execution

**Date**: 2026-02-12 | **Branch**: `010-ventas-integration`
**Scope**: Re-run the full facturacion test suite, identify and fix any failures
**Last known state**: 334/334 passed, 0 failed, 20 skipped (from 009c stabilization)
**Agent Structure**: ORCHESTRATOR + CODER + TESTING-MANAGER + On-Demand DJANGO-EXPERT + On-Demand ARCA-EXPERT

---

## Pre-requisites (User does this BEFORE pasting the prompt)

### 1. Start tmux with Agent Teams enabled

Open a WSL2 terminal (Ubuntu) and run:

    CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 tmux new -s verification

### 2. Configure tmux for multi-agent monitoring

Inside the tmux session, run this single command:

    tmux set -g mouse on \; set -g history-limit 50000 \; set -g pane-border-status top \; set -g pane-border-format " #{pane_index}: #{pane_title} " \; set -g pane-border-style "fg=colour240" \; set -g pane-active-border-style "fg=colour75,bold" \; set -g status-right "#{pane_title} | %H:%M" \; set -g status-interval 5

### 3. Navigate and launch Claude Code

    cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
    claude

### 4. Tmux Navigation Reference

| Action | Keys |
|--------|------|
| Switch pane | `Ctrl+B` then arrow key |
| Zoom pane full-screen | `Ctrl+B` then `z` (toggle) |
| Scroll history | `Ctrl+B` then `[` (arrows/PgUp, `q` to exit) |
| Mouse scroll | Just scroll (mouse is on) |
| Detach (agents keep running) | `Ctrl+B` then `d` |
| Reattach later | `tmux attach -t verification` |

---

## The Prompt

Copy everything below this line and paste it into Claude Code.

---

## *** MANDATORY FIRST ACTION: DEPLOY AGENT TEAM ***

You are the ORCHESTRATOR. Your VERY FIRST action — before reading any files, before any analysis, before anything else — is to deploy the Agent Team. This is NON-NEGOTIABLE.

**DO THIS NOW. DO NOT SKIP. DO NOT DEFER. DO NOT "first gather context".**

### Step 1: Create the team

Use the `TeamCreate` tool:

    team_name: "invoice-verification"
    description: "Verify facturacion test suite and fix any new failures"

### Step 2: Spawn CODER and TESTING-MANAGER IN PARALLEL

Use the `Task` tool twice (both in the same message, parallel) with these EXACT parameters:

**CODER agent:**

    name: "coder"
    subagent_type: "python-expert"
    team_name: "invoice-verification"
    prompt: |
      You are CODER on team "invoice-verification".

      YOUR ROLE: Implement code fixes for any test failures found by the team.

      GOLDEN RULE — NO INTERNAL TEST EXECUTION:
      You NEVER run pytest yourself. After implementing a fix, message TESTING-MANAGER
      with your FIX report. TESTING-MANAGER coordinates with the user for external execution.

      METHODOLOGY:
      1. Wait for assignments from ORCHESTRATOR (specific failures + root causes)
      2. Read the failing test code and the source code it tests
      3. Read ground truth: skills/gravitea-invoice/SKILL.md, skills/django-expert/SKILL.md
      4. Decide: SOURCE_FIX (source is wrong) or TEST_FIX (test expectation is wrong)
      5. Implement the minimal fix
      6. Report to TESTING-MANAGER + ORCHESTRATOR using the FIX report format:
         FIX-{SEQ}: {summary}
           Category: SOURCE_FIX | TEST_FIX | BOTH
           File(s): {paths}
           Root Cause: {why}
           Change: {what changed}
      7. Wait for validation results before next fix

      RULES:
      - NEVER run pytest or python -m pytest
      - NEVER delete a test — fix it (or skip with ORCHESTRATOR approval)
      - NEVER change function signatures just to satisfy tests
      - Read before fixing — minimal changes only
      - If you need Django help → ask ORCHESTRATOR to summon DJANGO-EXPERT
      - If you need ARCA help → ask ORCHESTRATOR to summon ARCA-EXPERT

**TESTING-MANAGER agent:**

    name: "testing-manager"
    subagent_type: "quality-engineer"
    team_name: "invoice-verification"
    prompt: |
      You are TESTING-MANAGER on team "invoice-verification".

      YOUR ROLE: Coordinate all test execution with the user. You are the ONLY agent
      that formulates test commands. You NEVER run tests yourself.

      GOLDEN RULE — EXTERNAL EXECUTION ONLY:
      All tests are run by the USER in their WSL terminal. You provide the exact
      copy-paste command. The user sees live output AND results are saved for you to read.

      HOW TO REQUEST A TEST RUN — use this exact template every time:

          "Please run in your WSL terminal:
           backend/venv-wsl/bin/python -m pytest <args> 2>&1 | tee .claude-test-results.txt
           Let me know when done."

      After the user confirms, read .claude-test-results.txt for the results.

      METHODOLOGY:
      1. BASELINE: Request full suite run, record pass/fail per file
      2. PER-FIX: After CODER reports a fix, request targeted test file run
      3. REGRESSION: After a batch of fixes, request full suite regression check
      4. FINAL: Request full suite + coverage report

      Maintain a test dashboard and send it to ORCHESTRATOR after each phase:

          | Phase    | Pass | Fail | Skip | Regressions |
          |----------|------|------|------|-------------|
          | Baseline |  ?   |  ?   |  ?   | N/A         |
          | Fix N    |  ?   |  ?   |  ?   | ?           |

      ON REGRESSION:
      - HALT immediately
      - Identify which fix caused the regression
      - Message ORCHESTRATOR + CODER with evidence
      - Wait for ORCHESTRATOR decision

      RULES:
      - NEVER run pytest or python -m pytest yourself
      - Always use the full venv path: backend/venv-wsl/bin/python -m pytest
      - Always append: 2>&1 | tee .claude-test-results.txt
      - Read .claude-test-results.txt ONLY (never .claude-test-full.log)

### Step 3: Confirm deployment

After both agents are spawned, you should see 3 tmux panes (you + CODER + TESTING-MANAGER). Confirm this to the user before proceeding.

**IF TeamCreate OR Task FAILS**: Retry once. If it fails again, tell the user: "Agent Teams deployment failed. Please verify CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 is set and restart."

---

## GOLDEN RULE: NO TESTS INSIDE CLAUDE CODE

**ALL test execution happens in the user's external terminal. NO AGENT may run pytest.**

- **ORCHESTRATOR**: Routes test requests to user, never runs tests
- **CODER**: Never runs tests — reports fixes to TESTING-MANAGER
- **TESTING-MANAGER**: Formulates commands for the user, reads .claude-test-results.txt
- **DJANGO-EXPERT / ARCA-EXPERT**: Advisory only, never run tests

**How it works**:
1. Agent provides the exact copy-paste command for the user's WSL terminal
2. User pastes and runs it — sees live output in real-time via `| tee`
3. Output saved to `.claude-test-results.txt`
4. User confirms done
5. Agent reads `.claude-test-results.txt` (summary lines only, never full log)

**FORBIDDEN inside any Claude Code pane**: `pytest`, `python -m pytest`, any test runner. Violation = immediate halt.

**Shorthand**: `EXT_TEST '<args>'` means the user runs:

    backend/venv-wsl/bin/python -m pytest <args> 2>&1 | tee .claude-test-results.txt

---

## Context

The facturacion module has been through two stabilization rounds:
- **009**: 6-agent review team applied 9 fixes (commit `499422d`)
- **009c**: 5-agent stabilization team applied 8 more fixes (3 source + 5 test)

Last known state: **334/334 passed, 0 failed, 20 skipped**.

This session re-runs the full suite to verify everything still passes and fix any NEW issues that may have appeared.

**Code locations**:
- Source: `backend/apps/facturacion/` (19 Python files)
- Tests: `backend/tests/facturacion/` (14 test files)
- Fixtures: `backend/tests/facturacion/conftest.py`
- Skills: `skills/gravitea-invoice/SKILL.md`, `skills/django-expert/SKILL.md`, `skills/gravitea-testing/SKILL.md`
- RAG: `scripts/qdrant/qdrant_search.py` (collections: arca_api_specs, arca_dev_guides, arca_setup_certs, wikis)

---

## ORCHESTRATOR Workflow (after team is deployed)

### Phase 1: Baseline

Message TESTING-MANAGER:

    "Request baseline from user. Full suite:
     EXT_TEST 'tests/facturacion/ --tb=short -q --no-header'
     Report the pass/fail/skip numbers."

Wait for TESTING-MANAGER to report baseline results.

**If baseline is 334/334 passing (or all passing, 20 skipped)**:
- Report to user: "All tests passing. No action needed."
- Proceed to Phase 4 (coverage report) and wrap up.

**If baseline shows ANY failures**:
- Record the failures per file
- Proceed to Phase 2

### Phase 2: Diagnose Failures

For any failures found in baseline:

1. Ask TESTING-MANAGER to request per-file breakdown from user:

       EXT_TEST 'tests/facturacion/unit/test_validators.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/unit/test_constants.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/unit/test_wsaa.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/unit/test_qr.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/unit/test_models.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/unit/test_caea.py --tb=no -q --no-header'
       EXT_TEST 'tests/facturacion/integration/ --tb=no -q --no-header'

2. For files with failures, ask TESTING-MANAGER to request verbose output:

       EXT_TEST 'tests/facturacion/unit/<failing_file>.py --tb=short -q'

3. Read `.claude-test-results.txt` to understand the specific errors
4. Assign fixes to CODER with specific root causes

### Phase 3: Fix and Validate

For each failure group:

1. **ORCHESTRATOR → CODER**: Assign specific failures with root cause analysis

       "Fix these failures in <file>:
        - test_name_1: <error description>
        - test_name_2: <error description>
        Root cause hypothesis: <your analysis>
        Read the source + test code, apply minimal fix, report using FIX format."

2. **CODER**: Implements fix, reports to TESTING-MANAGER + ORCHESTRATOR
3. **TESTING-MANAGER → USER**: Requests targeted test run for the affected file
4. **TESTING-MANAGER → ORCHESTRATOR**: Reports results
5. **Repeat** until all failures resolved

**After all fixes applied**: Request full regression suite:

    EXT_TEST 'tests/facturacion/ --tb=short -q --no-header'

### Phase 4: Coverage and Report

Request coverage from user:

    EXT_TEST 'tests/facturacion/ --cov=apps.facturacion --cov-report=term-missing --no-header -q'

Write verification report at `Docs/ARCA/Researches/009c-test-verification-report.md`:

    # 009c Test Verification Report

    ## Summary
    - **Baseline**: {X} passed, {Y} failed, {Z} skipped
    - **After fixes**: {X} passed, {Y} failed, {Z} skipped
    - **Status**: ALL_PASSING | FIXES_APPLIED | ISSUES_REMAIN

    ## New Issues Found
    {list of any new failures and their fixes, or "None — all tests passing from baseline"}

    ## Fixes Applied
    {FIX reports from CODER, or "None needed"}

    ## Coverage
    - Overall: {X}%
    - Key files: {list}

    ## Success Criteria
    - [ ] All tests passing
    - [ ] Zero regressions
    - [ ] All fixes documented

### Phase 5: Commit and Cleanup

If any fixes were applied:

    git add backend/apps/facturacion/ backend/tests/facturacion/ Docs/ARCA/Researches/009c-test-verification-report.md
    git commit -m "fix(facturacion): verify and fix test suite ({X}/{Y} passing)

    Re-verified full facturacion test suite. {describe what was found/fixed}.

    Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

If no fixes needed, still write the report and commit it as documentation.

Shutdown team:

    SendMessage type=shutdown_request to coder
    SendMessage type=shutdown_request to testing-manager
    TeamDelete "invoice-verification"

---

## On-Demand Expert Agents

Summon these ONLY when CODER needs domain-specific guidance.

**DJANGO-EXPERT** (spawn with Task tool when needed):

    name: "django-expert"
    subagent_type: "general-purpose"
    team_name: "invoice-verification"
    prompt: |
      You are DJANGO-EXPERT on team "invoice-verification" — on-demand advisor.
      CODER needs help with: {specific question}
      Read skills/django-expert/SKILL.md, answer the question, return to standby.
      RAG if needed: python scripts/qdrant/qdrant_search.py "query" --collection wikis

**ARCA-EXPERT** (spawn with Task tool when needed):

    name: "arca-expert"
    subagent_type: "general-purpose"
    team_name: "invoice-verification"
    prompt: |
      You are ARCA-EXPERT on team "invoice-verification" — on-demand advisor.
      CODER needs help with: {specific question}
      Read skills/gravitea-invoice/SKILL.md, answer the question, return to standby.
      RAG if needed: python scripts/qdrant/qdrant_search.py "query" --collection arca_api_specs

---

## Fix Decision Framework

For EVERY failing test, CODER determines whether to fix the SOURCE or the TEST:

    Is the test expectation correct per ARCA spec (skill + unified report)?
    +-- YES → Source code is wrong → SOURCE_FIX
    +-- NO  → Test expectation is wrong → TEST_FIX

    Is the failure a mock/fixture setup issue?
    +-- YES → Read actual function signature, align the mock → TEST_FIX

    Is the test genuinely out of scope?
    +-- YES → @pytest.mark.skip(reason="...") — ORCHESTRATOR approval required
    +-- NO  → Debug further

**Hard rules**:
- NEVER delete a test
- NEVER skip a test just because it's hard
- NEVER change function signatures solely to satisfy tests
- If a test reveals a genuine source bug: fix the source

---

## Important Constraints

- **NO AGENT RUNS PYTEST** — the GOLDEN RULE
- **Financial amounts**: DecimalField(max_digits=17, decimal_places=3) — do not change
- **Immutability**: AUTORIZADO/OBSERVADO comprobantes raise ValueError on save()/delete() — do not weaken
- **Serializers**: explicit fields=[...], never __all__
- **CODER owns all edits** — experts are advisory only
- **Follow CLAUDE.md conventions** for all code changes

---

## RAG Reference (Expert Agents)

    cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
    python scripts/qdrant/qdrant_search.py "query" --collection arca_api_specs
    python scripts/qdrant/qdrant_search.py "query" --collection arca_dev_guides
    python scripts/qdrant/qdrant_search.py "query" --collection arca_setup_certs
    python scripts/qdrant/qdrant_search.py "query" --collection wikis

---

*Created: 2026-02-12 (v3: verification focus, mandatory team deployment, clean rewrite)*
