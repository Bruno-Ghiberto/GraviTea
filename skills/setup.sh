#!/bin/bash
# Setup AI Skills for GRAVITEA-ERP development
# Two-Source Merge: combines custom + marketplace skills
#
# Sources (priority order):
#   1. skills/              Custom skills (git-tracked, team-authored)     [HIGHEST]
#   2. .agents/skills/      Marketplace skills (Vercel/agentskills.io)     [LOWEST]
#
# Targets:
#   - Claude Code:    .claude/skills/ (per-skill copy)
#   - Gemini CLI:     .gemini/skills/ (per-skill copy) + GEMINI.md
#   - Codex (OpenAI): .codex/skills/ (per-skill copy) + AGENTS.md (native)
#   - GitHub Copilot: .github/copilot-instructions.md copy
#   - Cursor:         .cursor/rules/*.mdc (per-skill .mdc files)
#
# Usage:
#   ./setup.sh              # Interactive mode (select AI assistants)
#   ./setup.sh --all        # Configure all AI assistants
#   ./setup.sh --claude     # Configure only Claude Code
#   ./setup.sh --claude --codex  # Configure multiple

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CUSTOM_SOURCE="$SCRIPT_DIR"
MARKETPLACE_SOURCE="$REPO_ROOT/.agents/skills"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Selection flags
SETUP_CLAUDE=false
SETUP_GEMINI=false
SETUP_CODEX=false
SETUP_COPILOT=false
SETUP_CURSOR=false

# Tracking
CUSTOM_COUNT=0
MARKETPLACE_COUNT=0
CONFLICT_COUNT=0

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Configure AI coding assistants for GRAVITEA-ERP development."
    echo "Merges skills from two sources (priority order):"
    echo "  1. skills/              Custom skills (team-authored)        [HIGHEST]"
    echo "  2. .agents/skills/      Marketplace skills (agentskills.io)  [LOWEST]"
    echo ""
    echo "Options:"
    echo "  --all       Configure all AI assistants"
    echo "  --claude    Configure Claude Code"
    echo "  --gemini    Configure Gemini CLI"
    echo "  --codex     Configure Codex (OpenAI)"
    echo "  --copilot   Configure GitHub Copilot"
    echo "  --cursor    Configure Cursor"
    echo "  --help      Show this help message"
    echo ""
    echo "If no options provided, runs in interactive mode."
    echo ""
    echo "Examples:"
    echo "  $0                      # Interactive selection"
    echo "  $0 --all                # All AI assistants"
    echo "  $0 --claude --codex     # Only Claude and Codex"
}

show_menu() {
    echo -e "${BOLD}Which AI assistants do you use?${NC}"
    echo -e "${CYAN}(Use numbers to toggle, Enter to confirm)${NC}"
    echo ""

    local options=("Claude Code" "Gemini CLI" "Codex (OpenAI)" "GitHub Copilot" "Cursor")
    local selected=(true false false false false)  # Claude selected by default

    while true; do
        for i in "${!options[@]}"; do
            if [ "${selected[$i]}" = true ]; then
                echo -e "  ${GREEN}[x]${NC} $((i+1)). ${options[$i]}"
            else
                echo -e "  [ ] $((i+1)). ${options[$i]}"
            fi
        done
        echo ""
        echo -e "  ${YELLOW}a${NC}. Select all"
        echo -e "  ${YELLOW}n${NC}. Select none"
        echo ""
        echo -n "Toggle (1-5, a, n) or Enter to confirm: "

        read -r choice

        case $choice in
            1) selected[0]=$([ "${selected[0]}" = true ] && echo false || echo true) ;;
            2) selected[1]=$([ "${selected[1]}" = true ] && echo false || echo true) ;;
            3) selected[2]=$([ "${selected[2]}" = true ] && echo false || echo true) ;;
            4) selected[3]=$([ "${selected[3]}" = true ] && echo false || echo true) ;;
            5) selected[4]=$([ "${selected[4]}" = true ] && echo false || echo true) ;;
            a|A) selected=(true true true true true) ;;
            n|N) selected=(false false false false false) ;;
            "") break ;;
            *) echo -e "${RED}Invalid option${NC}" ;;
        esac

        # Move cursor up to redraw menu
        echo -en "\033[12A\033[J"
    done

    SETUP_CLAUDE=${selected[0]}
    SETUP_GEMINI=${selected[1]}
    SETUP_CODEX=${selected[2]}
    SETUP_COPILOT=${selected[3]}
    SETUP_CURSOR=${selected[4]}
}

# List skill directories from a source (only dirs containing SKILL.md)
list_skills() {
    local source_dir="$1"
    if [ ! -d "$source_dir" ]; then
        return
    fi
    for skill_dir in "$source_dir"/*/; do
        [ -d "$skill_dir" ] || continue
        if [ -f "$skill_dir/SKILL.md" ]; then
            basename "$skill_dir"
        fi
    done
}

# Copy skills from two sources into a target directory
# Priority: custom > marketplace (higher priority wins on name conflicts)
copy_skills_to_target() {
    local target_dir="$1"
    local agent_name="$2"
    local copied_skills=()

    # Ensure target directory exists
    mkdir -p "$target_dir"

    # Clean: remove ALL subdirectories and loose files (output dir is fully generated)
    if [ -L "$target_dir" ]; then
        # Replace broken symlink with real directory
        rm "$target_dir"
        mkdir -p "$target_dir"
    else
        rm -rf "$target_dir"
        mkdir -p "$target_dir"
    fi

    # Phase 1: Copy custom skills (priority)
    for skill_dir in "$CUSTOM_SOURCE"/*/; do
        [ -d "$skill_dir" ] || continue
        if [ -f "$skill_dir/SKILL.md" ]; then
            local skill_name
            skill_name=$(basename "$skill_dir")
            cp -r "$skill_dir" "$target_dir/$skill_name"
            copied_skills+=("$skill_name")
            CUSTOM_COUNT=$((CUSTOM_COUNT + 1))
        fi
    done

    # Phase 2: Copy marketplace skills (skip conflicts with custom)
    if [ -d "$MARKETPLACE_SOURCE" ]; then
        for skill_dir in "$MARKETPLACE_SOURCE"/*/; do
            [ -d "$skill_dir" ] || continue
            if [ -f "$skill_dir/SKILL.md" ]; then
                local skill_name
                skill_name=$(basename "$skill_dir")

                # Check for conflict with custom skill
                local is_conflict=false
                for existing in "${copied_skills[@]}"; do
                    if [ "$existing" = "$skill_name" ]; then
                        is_conflict=true
                        break
                    fi
                done

                if [ "$is_conflict" = true ]; then
                    echo -e "${YELLOW}    ! Conflict: '$skill_name' (marketplace) shadowed by custom${NC}"
                    CONFLICT_COUNT=$((CONFLICT_COUNT + 1))
                else
                    cp -r "$skill_dir" "$target_dir/$skill_name"
                    copied_skills+=("$skill_name")
                    MARKETPLACE_COUNT=$((MARKETPLACE_COUNT + 1))
                fi
            fi
        done
    fi

    echo -e "${GREEN}  + Copied ${#copied_skills[@]} skills to $agent_name${NC}"
}

# Extract description from a SKILL.md frontmatter (for Cursor .mdc files)
_extract_skill_desc() {
    local skill_file="$1"
    local desc
    # Try single-line description first
    desc=$(grep '^description:' "$skill_file" | head -1 | sed 's/^description: *//' | sed 's/^> *//' | tr -d '"')
    # If empty or just ">" (multi-line block), grab first indented continuation line
    if [ -z "$desc" ] || [ "$desc" = ">" ]; then
        desc=$(grep -A3 '^description:' "$skill_file" | grep '^  ' | head -1 | sed 's/^  *//')
    fi
    echo "${desc:-skill}"
}

# Convert a SKILL.md to a Cursor .mdc rule file
_write_cursor_mdc() {
    local skill_file="$1"
    local out_file="$2"
    local desc
    desc=$(_extract_skill_desc "$skill_file")
    {
        echo "---"
        echo "description: ${desc}"
        echo "alwaysApply: false"
        echo "---"
        echo ""
        cat "$skill_file"
    } > "$out_file"
}

setup_claude() {
    local target="$REPO_ROOT/.claude/skills"

    mkdir -p "$REPO_ROOT/.claude"
    copy_skills_to_target "$target" ".claude/skills/"

    # NOTE: CLAUDE.md is the source of truth and is NOT auto-generated.
    # Edit CLAUDE.md directly to update Claude's agent instructions.
}

setup_gemini() {
    local target="$REPO_ROOT/.gemini/skills"

    mkdir -p "$REPO_ROOT/.gemini"
    copy_skills_to_target "$target" ".gemini/skills/"

    # Copy AGENTS.md to GEMINI.md
    copy_agents_md "GEMINI.md"
}

setup_codex() {
    local target="$REPO_ROOT/.codex/skills"

    mkdir -p "$REPO_ROOT/.codex"
    copy_skills_to_target "$target" ".codex/skills/"
    echo -e "${GREEN}  + Codex uses AGENTS.md natively${NC}"
}

setup_copilot() {
    local source_file
    # Prefer CLAUDE.md (SSoT) if it exists, fall back to AGENTS.md
    if [ -f "$REPO_ROOT/CLAUDE.md" ]; then
        source_file="$REPO_ROOT/CLAUDE.md"
    elif [ -f "$REPO_ROOT/AGENTS.md" ]; then
        source_file="$REPO_ROOT/AGENTS.md"
    else
        echo -e "${YELLOW}  ! No CLAUDE.md or AGENTS.md found, skipping Copilot${NC}"
        return
    fi
    mkdir -p "$REPO_ROOT/.github"
    cp "$source_file" "$REPO_ROOT/.github/copilot-instructions.md"
    echo -e "${GREEN}  + $(basename "$source_file") -> .github/copilot-instructions.md${NC}"
}

setup_cursor() {
    local rules_dir="$REPO_ROOT/.cursor/rules"
    mkdir -p "$rules_dir"

    # Clean existing auto-generated .mdc skill rules
    find "$rules_dir" -maxdepth 1 -name "*.mdc" -delete 2>/dev/null || true

    local processed_skills=()
    local mdc_count=0

    # Phase 1: Custom skills (priority)
    for skill_dir in "$CUSTOM_SOURCE"/*/; do
        [ -d "$skill_dir" ] || continue
        [ -f "$skill_dir/SKILL.md" ] || continue
        local skill_name
        skill_name=$(basename "$skill_dir")
        _write_cursor_mdc "$skill_dir/SKILL.md" "$rules_dir/${skill_name}.mdc"
        processed_skills+=("$skill_name")
        mdc_count=$((mdc_count + 1))
    done

    # Phase 2: Marketplace skills (skip conflicts with custom)
    if [ -d "$MARKETPLACE_SOURCE" ]; then
        for skill_dir in "$MARKETPLACE_SOURCE"/*/; do
            [ -d "$skill_dir" ] || continue
            [ -f "$skill_dir/SKILL.md" ] || continue
            local skill_name
            skill_name=$(basename "$skill_dir")
            local is_conflict=false
            for existing in "${processed_skills[@]}"; do
                [ "$existing" = "$skill_name" ] && is_conflict=true && break
            done
            if [ "$is_conflict" = false ]; then
                _write_cursor_mdc "$skill_dir/SKILL.md" "$rules_dir/${skill_name}.mdc"
                processed_skills+=("$skill_name")
                mdc_count=$((mdc_count + 1))
            fi
        done
    fi

    echo -e "${GREEN}  + Converted $mdc_count skills to .cursor/rules/*.mdc${NC}"
}

copy_agents_md() {
    local target_name="$1"
    local agents_files
    local count=0

    agents_files=$(find "$REPO_ROOT" -maxdepth 3 -name "AGENTS.md" \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/.claude/skills/*" \
        -not -path "*/.codex/skills/*" \
        -not -path "*/.gemini/skills/*" \
        -not -path "*/.cursor/skills/*" \
        -not -path "*/.agents/skills/*" \
        -not -path "*/.github/skills/*" \
        2>/dev/null)

    for agents_file in $agents_files; do
        local agents_dir
        agents_dir=$(dirname "$agents_file")
        cp "$agents_file" "$agents_dir/$target_name"
        count=$((count + 1))
    done

    echo -e "${GREEN}  + Copied $count AGENTS.md -> $target_name${NC}"
}

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            SETUP_CLAUDE=true
            SETUP_GEMINI=true
            SETUP_CODEX=true
            SETUP_COPILOT=true
            SETUP_CURSOR=true
            shift
            ;;
        --claude)
            SETUP_CLAUDE=true
            shift
            ;;
        --gemini)
            SETUP_GEMINI=true
            shift
            ;;
        --codex)
            SETUP_CODEX=true
            shift
            ;;
        --copilot)
            SETUP_COPILOT=true
            shift
            ;;
        --cursor)
            SETUP_CURSOR=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# =============================================================================
# MAIN
# =============================================================================

echo "GRAVITEA-ERP AI Skills Setup"
echo "============================"
echo ""

# Count skills from both sources
CUSTOM_SKILL_COUNT=$(list_skills "$CUSTOM_SOURCE" | wc -l | tr -d ' ')
MARKETPLACE_SKILL_COUNT=0
if [ -d "$MARKETPLACE_SOURCE" ]; then
    MARKETPLACE_SKILL_COUNT=$(list_skills "$MARKETPLACE_SOURCE" | wc -l | tr -d ' ')
fi
TOTAL_SKILL_COUNT=$((CUSTOM_SKILL_COUNT + MARKETPLACE_SKILL_COUNT))

if [ "$TOTAL_SKILL_COUNT" -eq 0 ]; then
    echo -e "${RED}No skills found${NC}"
    exit 1
fi

echo -e "${BLUE}Sources:${NC}"
echo -e "  Custom (skills/):          ${BOLD}$CUSTOM_SKILL_COUNT${NC} skills"
if [ "$MARKETPLACE_SKILL_COUNT" -gt 0 ]; then
    echo -e "  Marketplace (.agents/):    ${BOLD}$MARKETPLACE_SKILL_COUNT${NC} skills"
else
    echo -e "  Marketplace (.agents/):    ${CYAN}none${NC}"
fi
echo -e "  Total:                     ${BOLD}$TOTAL_SKILL_COUNT${NC} skills"
echo ""

# Interactive mode if no flags provided
if [ "$SETUP_CLAUDE" = false ] && [ "$SETUP_GEMINI" = false ] && [ "$SETUP_CODEX" = false ] && [ "$SETUP_COPILOT" = false ] && [ "$SETUP_CURSOR" = false ]; then
    show_menu
    echo ""
fi

# Check if at least one selected
if [ "$SETUP_CLAUDE" = false ] && [ "$SETUP_GEMINI" = false ] && [ "$SETUP_CODEX" = false ] && [ "$SETUP_COPILOT" = false ] && [ "$SETUP_CURSOR" = false ]; then
    echo -e "${YELLOW}No AI assistants selected. Nothing to do.${NC}"
    exit 0
fi

# Run selected setups
STEP=1
TOTAL=0
[ "$SETUP_CLAUDE" = true ] && TOTAL=$((TOTAL + 1))
[ "$SETUP_GEMINI" = true ] && TOTAL=$((TOTAL + 1))
[ "$SETUP_CODEX" = true ] && TOTAL=$((TOTAL + 1))
[ "$SETUP_COPILOT" = true ] && TOTAL=$((TOTAL + 1))
[ "$SETUP_CURSOR" = true ] && TOTAL=$((TOTAL + 1))

if [ "$SETUP_CLAUDE" = true ]; then
    echo -e "${YELLOW}[$STEP/$TOTAL] Setting up Claude Code...${NC}"
    setup_claude
    STEP=$((STEP + 1))
fi

if [ "$SETUP_GEMINI" = true ]; then
    echo -e "${YELLOW}[$STEP/$TOTAL] Setting up Gemini CLI...${NC}"
    setup_gemini
    STEP=$((STEP + 1))
fi

if [ "$SETUP_CODEX" = true ]; then
    echo -e "${YELLOW}[$STEP/$TOTAL] Setting up Codex (OpenAI)...${NC}"
    setup_codex
    STEP=$((STEP + 1))
fi

if [ "$SETUP_COPILOT" = true ]; then
    echo -e "${YELLOW}[$STEP/$TOTAL] Setting up GitHub Copilot...${NC}"
    setup_copilot
    STEP=$((STEP + 1))
fi

if [ "$SETUP_CURSOR" = true ]; then
    echo -e "${YELLOW}[$STEP/$TOTAL] Setting up Cursor...${NC}"
    setup_cursor
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
if [ "$CONFLICT_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}Resolved $CONFLICT_COUNT name conflict(s) (custom > marketplace)${NC}"
fi
echo -e "${GREEN}Successfully configured $TOTAL_SKILL_COUNT skills!${NC}"
echo ""
echo "Configured:"
[ "$SETUP_CLAUDE" = true ] && echo "  - Claude Code:    .claude/skills/"
[ "$SETUP_CODEX" = true ] && echo "  - Codex (OpenAI): .codex/skills/ + AGENTS.md (native)"
[ "$SETUP_GEMINI" = true ] && echo "  - Gemini CLI:     .gemini/skills/ + GEMINI.md"
[ "$SETUP_COPILOT" = true ] && echo "  - GitHub Copilot: .github/copilot-instructions.md"
[ "$SETUP_CURSOR" = true ] && echo "  - Cursor:         .cursor/rules/*.mdc"
echo ""
echo -e "${BLUE}Note: Restart your AI assistant to load the skills.${NC}"
echo -e "${BLUE}      CLAUDE.md is the source of truth — edit it to update agent instructions.${NC}"
