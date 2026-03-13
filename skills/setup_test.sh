#!/bin/bash
# Unit tests for setup.sh (two-source merge)
# Run: ./skills/setup_test.sh
#
# shellcheck disable=SC2317
# Reason: Test functions are discovered and called dynamically via declare -F

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="$SCRIPT_DIR/setup.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test environment
TEST_DIR=""

# =============================================================================
# TEST FRAMEWORK
# =============================================================================

setup_test_env() {
    TEST_DIR=$(mktemp -d)

    # Create mock repo structure with TWO skill sources
    # Source 1: Custom skills (skills/)
    mkdir -p "$TEST_DIR/skills/typescript"
    mkdir -p "$TEST_DIR/skills/react-19"
    mkdir -p "$TEST_DIR/api"
    mkdir -p "$TEST_DIR/ui"
    mkdir -p "$TEST_DIR/.github"

    # Create mock SKILL.md files for custom skills
    echo "---
name: typescript
description: TypeScript skill
---
# TypeScript Skill" > "$TEST_DIR/skills/typescript/SKILL.md"

    echo "---
name: react-19
description: React 19 skill
---
# React 19 Skill" > "$TEST_DIR/skills/react-19/SKILL.md"

    # Source 2: Marketplace skills (.agents/skills/)
    mkdir -p "$TEST_DIR/.agents/skills/vercel-perf"
    mkdir -p "$TEST_DIR/.agents/skills/vercel-perf/rules"

    echo "---
name: vercel-perf
description: Vercel performance skill
---
# Vercel Perf" > "$TEST_DIR/.agents/skills/vercel-perf/SKILL.md"

    echo "# Full Vercel Perf Guide" > "$TEST_DIR/.agents/skills/vercel-perf/AGENTS.md"
    echo "# Rule 1" > "$TEST_DIR/.agents/skills/vercel-perf/rules/rule-1.md"

    # Create mock AGENTS.md files
    echo "# Root AGENTS" > "$TEST_DIR/AGENTS.md"
    echo "# API AGENTS" > "$TEST_DIR/api/AGENTS.md"
    echo "# UI AGENTS" > "$TEST_DIR/ui/AGENTS.md"

    # Copy setup.sh to test dir
    cp "$SETUP_SCRIPT" "$TEST_DIR/skills/setup.sh"
}

teardown_test_env() {
    if [ -n "$TEST_DIR" ] && [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
    fi
}

run_setup() {
    (cd "$TEST_DIR/skills" && bash setup.sh "$@" 2>&1)
}

# Assertions return 0 on success, 1 on failure
assert_equals() {
    local expected="$1" actual="$2" message="$3"
    if [ "$expected" = "$actual" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    Expected: $expected"
    echo "    Actual:   $actual"
    return 1
}

assert_contains() {
    local haystack="$1" needle="$2" message="$3"
    if echo "$haystack" | grep -q -F -- "$needle"; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    String not found: $needle"
    return 1
}

assert_file_exists() {
    local file="$1" message="$2"
    if [ -f "$file" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    File not found: $file"
    return 1
}

assert_file_not_exists() {
    local file="$1" message="$2"
    if [ ! -f "$file" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    File should not exist: $file"
    return 1
}

assert_dir_exists() {
    local dir="$1" message="$2"
    if [ -d "$dir" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    Directory not found: $dir"
    return 1
}

assert_dir_not_exists() {
    local dir="$1" message="$2"
    if [ ! -d "$dir" ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: $message${NC}"
    echo "    Directory should not exist: $dir"
    return 1
}

# =============================================================================
# TESTS: FLAG PARSING
# =============================================================================

test_flag_help_shows_usage() {
    local output
    output=$(run_setup --help)
    assert_contains "$output" "Usage:" "Help should show usage" && \
    assert_contains "$output" "--all" "Help should mention --all flag" && \
    assert_contains "$output" "--claude" "Help should mention --claude flag" && \
    assert_contains "$output" "--cursor" "Help should mention --cursor flag" && \
    assert_contains "$output" "Marketplace" "Help should mention marketplace"
}

test_flag_unknown_reports_error() {
    local output
    output=$(run_setup --unknown 2>&1) || true
    assert_contains "$output" "Unknown option" "Should report unknown option"
}

test_flag_all_configures_everything() {
    local output
    output=$(run_setup --all)
    assert_contains "$output" "Claude Code" "Should setup Claude" && \
    assert_contains "$output" "Gemini CLI" "Should setup Gemini" && \
    assert_contains "$output" "Codex" "Should setup Codex" && \
    assert_contains "$output" "Copilot" "Should setup Copilot" && \
    assert_contains "$output" "Cursor" "Should setup Cursor"
}

test_flag_single_claude() {
    local output
    output=$(run_setup --claude)
    assert_contains "$output" "Claude Code" "Should setup Claude" && \
    assert_contains "$output" "[1/1]" "Should show 1/1 steps"
}

test_flag_multiple_combined() {
    local output
    output=$(run_setup --claude --codex)
    assert_contains "$output" "[1/2]" "Should show step 1/2" && \
    assert_contains "$output" "[2/2]" "Should show step 2/2"
}

# =============================================================================
# TESTS: TWO-SOURCE MERGE (per-skill copy)
# =============================================================================

test_merge_claude_has_custom_skills() {
    run_setup --claude > /dev/null
    assert_dir_exists "$TEST_DIR/.claude/skills/typescript" "Custom typescript skill should exist" && \
    assert_dir_exists "$TEST_DIR/.claude/skills/react-19" "Custom react-19 skill should exist"
}

test_merge_claude_has_marketplace_skills() {
    run_setup --claude > /dev/null
    assert_dir_exists "$TEST_DIR/.claude/skills/vercel-perf" "Marketplace vercel-perf skill should exist"
}

test_merge_marketplace_subdirs_preserved() {
    run_setup --claude > /dev/null
    assert_file_exists "$TEST_DIR/.claude/skills/vercel-perf/SKILL.md" "SKILL.md should exist" && \
    assert_file_exists "$TEST_DIR/.claude/skills/vercel-perf/AGENTS.md" "AGENTS.md should exist" && \
    assert_file_exists "$TEST_DIR/.claude/skills/vercel-perf/rules/rule-1.md" "rules/ should be preserved"
}

test_merge_gemini_has_both_sources() {
    run_setup --gemini > /dev/null
    assert_dir_exists "$TEST_DIR/.gemini/skills/typescript" "Custom skill in gemini" && \
    assert_dir_exists "$TEST_DIR/.gemini/skills/vercel-perf" "Marketplace skill in gemini"
}

test_merge_codex_has_both_sources() {
    run_setup --codex > /dev/null
    assert_dir_exists "$TEST_DIR/.codex/skills/typescript" "Custom skill in codex" && \
    assert_dir_exists "$TEST_DIR/.codex/skills/vercel-perf" "Marketplace skill in codex"
}

test_merge_no_symlinks_created() {
    run_setup --claude > /dev/null
    # The target should be a real directory, not a symlink
    if [ -L "$TEST_DIR/.claude/skills" ]; then
        echo -e "${RED}  FAIL: .claude/skills should not be a symlink${NC}"
        return 1
    fi
    return 0
}

# =============================================================================
# TESTS: CONFLICT RESOLUTION
# =============================================================================

test_conflict_custom_wins() {
    # Create a marketplace skill with same name as custom skill
    mkdir -p "$TEST_DIR/.agents/skills/typescript"
    echo "---
name: typescript
description: Marketplace typescript
---
# MARKETPLACE VERSION" > "$TEST_DIR/.agents/skills/typescript/SKILL.md"

    run_setup --claude > /dev/null

    # Custom version should win
    local content
    content=$(cat "$TEST_DIR/.claude/skills/typescript/SKILL.md")
    assert_contains "$content" "TypeScript Skill" "Custom version should win over marketplace"
}

test_conflict_warning_displayed() {
    # Create a marketplace skill with same name as custom skill
    mkdir -p "$TEST_DIR/.agents/skills/typescript"
    echo "---
name: typescript
description: Marketplace typescript
---
# MARKETPLACE VERSION" > "$TEST_DIR/.agents/skills/typescript/SKILL.md"

    local output
    output=$(run_setup --claude)
    assert_contains "$output" "Conflict" "Should warn about conflict"
}

# =============================================================================
# TESTS: AGENTS.md COPYING
# =============================================================================

test_copy_claude_agents_md() {
    run_setup --claude > /dev/null
    # CLAUDE.md is the SSoT and is NOT generated by setup.sh --claude.
    # Instead, verify .claude/skills/ was populated from both sources.
    assert_dir_exists "$TEST_DIR/.claude/skills/typescript" "Custom skill should be in .claude/skills" && \
    assert_dir_exists "$TEST_DIR/.claude/skills/vercel-perf" "Marketplace skill should be in .claude/skills"
}

test_copy_gemini_agents_md() {
    run_setup --gemini > /dev/null
    assert_file_exists "$TEST_DIR/GEMINI.md" "Root GEMINI.md should exist" && \
    assert_file_exists "$TEST_DIR/api/GEMINI.md" "api/GEMINI.md should exist" && \
    assert_file_exists "$TEST_DIR/ui/GEMINI.md" "ui/GEMINI.md should exist"
}

test_copy_copilot_to_github() {
    run_setup --copilot > /dev/null
    assert_file_exists "$TEST_DIR/.github/copilot-instructions.md" "Copilot instructions should exist"
}

test_copy_agents_md_excludes_output_dirs() {
    run_setup --claude > /dev/null
    # The marketplace AGENTS.md inside .claude/skills/vercel-perf/ should NOT
    # have generated a CLAUDE.md next to it (it's in an output directory)
    assert_file_not_exists "$TEST_DIR/.claude/skills/vercel-perf/CLAUDE.md" \
        "Should not copy AGENTS.md inside output skill directories"
}

test_copy_content_matches_source() {
    # CLAUDE.md is no longer generated from AGENTS.md (it's the SSoT).
    # Verify GEMINI.md content matches AGENTS.md instead.
    run_setup --gemini > /dev/null
    local source_content target_content
    source_content=$(cat "$TEST_DIR/AGENTS.md")
    target_content=$(cat "$TEST_DIR/GEMINI.md")
    assert_equals "$source_content" "$target_content" "GEMINI.md content should match AGENTS.md"
}

# =============================================================================
# TESTS: DIRECTORY CREATION
# =============================================================================

test_dir_claude_created() {
    rm -rf "$TEST_DIR/.claude"
    run_setup --claude > /dev/null
    assert_dir_exists "$TEST_DIR/.claude" ".claude directory should be created"
}

test_dir_gemini_created() {
    rm -rf "$TEST_DIR/.gemini"
    run_setup --gemini > /dev/null
    assert_dir_exists "$TEST_DIR/.gemini" ".gemini directory should be created"
}

test_dir_codex_created() {
    rm -rf "$TEST_DIR/.codex"
    run_setup --codex > /dev/null
    assert_dir_exists "$TEST_DIR/.codex" ".codex directory should be created"
}

# =============================================================================
# TESTS: IDEMPOTENCY
# =============================================================================

test_idempotent_multiple_runs() {
    run_setup --claude > /dev/null
    run_setup --claude > /dev/null
    assert_dir_exists "$TEST_DIR/.claude/skills/typescript" "Custom skill should exist after second run" && \
    assert_dir_exists "$TEST_DIR/.claude/skills/vercel-perf" "Marketplace skill should exist after second run"
}

test_idempotent_no_stale_skills() {
    # Run once with marketplace skill
    run_setup --claude > /dev/null
    assert_dir_exists "$TEST_DIR/.claude/skills/vercel-perf" "Should exist after first run"

    # Remove marketplace skill from source
    rm -rf "$TEST_DIR/.agents/skills/vercel-perf"

    # Run again - stale skill should be cleaned
    run_setup --claude > /dev/null
    assert_dir_not_exists "$TEST_DIR/.claude/skills/vercel-perf" "Stale marketplace skill should be removed"
}

# =============================================================================
# TESTS: NO MARKETPLACE SOURCE
# =============================================================================

test_no_marketplace_dir_works() {
    rm -rf "$TEST_DIR/.agents"
    local output
    output=$(run_setup --claude)
    assert_contains "$output" "none" "Should show no marketplace skills" && \
    assert_dir_exists "$TEST_DIR/.claude/skills/typescript" "Custom skills still work"
}

# =============================================================================
# TESTS: SOURCE COUNTING
# =============================================================================

test_source_counts_displayed() {
    local output
    output=$(run_setup --claude)
    assert_contains "$output" "Custom" "Should show custom source" && \
    assert_contains "$output" "Marketplace" "Should show marketplace source"
}

# =============================================================================
# TESTS: CURSOR (.mdc generation)
# =============================================================================

test_cursor_creates_mdc_files() {
    run_setup --cursor > /dev/null
    local mdc_count
    mdc_count=$(find "$TEST_DIR/.cursor/rules" -maxdepth 1 -name "*.mdc" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$mdc_count" -gt 0 ]; then
        return 0
    fi
    echo -e "${RED}  FAIL: No .mdc files created in .cursor/rules/${NC}"
    return 1
}

test_cursor_has_custom_skill_mdc() {
    run_setup --cursor > /dev/null
    assert_file_exists "$TEST_DIR/.cursor/rules/typescript.mdc" "Custom skill should have .mdc file"
}

test_cursor_has_marketplace_skill_mdc() {
    run_setup --cursor > /dev/null
    assert_file_exists "$TEST_DIR/.cursor/rules/vercel-perf.mdc" "Marketplace skill should have .mdc file"
}

test_cursor_mdc_has_frontmatter() {
    run_setup --cursor > /dev/null
    local content
    content=$(cat "$TEST_DIR/.cursor/rules/typescript.mdc")
    assert_contains "$content" "description:" "mdc should have description frontmatter" && \
    assert_contains "$content" "alwaysApply:" "mdc should have alwaysApply frontmatter"
}

test_cursor_custom_wins_over_marketplace() {
    # Create marketplace skill with same name as custom
    mkdir -p "$TEST_DIR/.agents/skills/typescript"
    echo "---
name: typescript
description: Marketplace typescript
---
# MARKETPLACE VERSION" > "$TEST_DIR/.agents/skills/typescript/SKILL.md"

    run_setup --cursor > /dev/null

    local content
    content=$(cat "$TEST_DIR/.cursor/rules/typescript.mdc")
    assert_contains "$content" "TypeScript Skill" "Custom should win over marketplace in .mdc"
}

test_cursor_dir_created() {
    rm -rf "$TEST_DIR/.cursor"
    run_setup --cursor > /dev/null
    assert_dir_exists "$TEST_DIR/.cursor/rules" ".cursor/rules directory should be created"
}

# =============================================================================
# TEST RUNNER (autodiscovery)
# =============================================================================

run_all_tests() {
    local test_functions current_section=""

    # Discover all test_* functions
    test_functions=$(declare -F | awk '{print $3}' | grep '^test_' | sort)

    for test_func in $test_functions; do
        # Extract section from function name (e.g., test_flag_* -> "Flag")
        local section
        section=$(echo "$test_func" | sed 's/^test_//' | cut -d'_' -f1)
        section="$(echo "${section:0:1}" | tr '[:lower:]' '[:upper:]')${section:1}"

        # Print section header if changed
        if [ "$section" != "$current_section" ]; then
            [ -n "$current_section" ] && echo ""
            echo -e "${YELLOW}${section} tests:${NC}"
            current_section="$section"
        fi

        # Convert function name to readable test name
        local test_name
        test_name=$(echo "$test_func" | sed 's/^test_//' | tr '_' ' ')

        TESTS_RUN=$((TESTS_RUN + 1))
        echo -n "  $test_name... "

        setup_test_env

        if $test_func; then
            echo -e "${GREEN}PASS${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi

        teardown_test_env
    done
}

# =============================================================================
# MAIN
# =============================================================================

echo ""
echo "Running setup.sh unit tests (two-source merge)"
echo "==============================================="
echo ""

run_all_tests

echo ""
echo "================================================"
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All $TESTS_RUN tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$TESTS_FAILED of $TESTS_RUN tests failed${NC}"
    exit 1
fi
