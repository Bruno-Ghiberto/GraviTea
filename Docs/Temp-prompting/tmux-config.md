# tmux Setup Guide: Multi-Agent Implementation Session

**For**: Human operator running the 001-sal-invo-inve-backend implementation
**Read by**: YOU (not Claude Code)

---

## 1. Pre-Launch Steps

### 1.1 Set Environment Variable

```bash
#INITIATE SESSION IN ONE LINER COMMAND
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP && export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && tmux new-session -s gravitea -x 240 -y 60 && tmux set -g mouse on \; set -g history-limit 50000 \; set -g pane-border-status top \; set -g pane-border-format " #{pane_index}: #{pane_title} " \; set -g pane-border-style "fg=colour240" \; set -g pane-active-border-style "fg=colour75,bold" \; set -g status-right "#{pane_title} | %H:%M" \; set -g status-interval 5 \; set -g display-panes-time 3000 \; set -g pane-base-index 1 \; set -g base-index 1 \; set -g remain-on-exit off

# REQUIRED — enables Agent Teams multi-pane coordination
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

### 1.2 Create tmux Session

```bash
# Create named session with generous dimensions
tmux new-session -s gravitea -x 240 -y 60

# One-liner: optimal config for multi-agent team operation
tmux set -g mouse on \; set -g history-limit 50000 \; set -g pane-border-status top \; set -g pane-border-format " #{pane_index}: #{pane_title} " \; set -g pane-border-style "fg=colour240" \; set -g pane-active-border-style "fg=colour75,bold" \; set -g status-right "#{pane_title} | %H:%M" \; set -g status-interval 5 \; set -g display-panes-time 3000 \; set -g pane-base-index 1 \; set -g base-index 1 \; set -g remain-on-exit off
```

### 1.3 (Optional) Pre-Create Utility Panes

Agent Teams auto-creates panes for each spawned teammate. You only need to pre-create panes for YOUR personal use — things agents can't do (running tests, docker, manual shell).

```bash
# Split a TEST-RUNNER pane below the main pane
tmux split-window -v -t gravitea:0
tmux select-pane -t gravitea:0.1 -T "TEST-RUNNER"
tmux send-keys -t gravitea:0.1 "cd backend" Enter

# (Optional) Split a DOCKER pane
tmux split-window -h -t gravitea:0.1
tmux select-pane -t gravitea:0.2 -T "DOCKER"
tmux send-keys -t gravitea:0.2 "cd $(pwd)" Enter

# (Optional) Split a SHELL pane for ad-hoc commands
tmux split-window -v -t gravitea:0.2
tmux select-pane -t gravitea:0.3 -T "SHELL"
tmux send-keys -t gravitea:0.3 "cd $(pwd)" Enter

# Return to main pane for Claude Code
tmux select-pane -t gravitea:0.0
```

**Resulting layout** (before Claude Code spawns agents):
```
┌────────────────────────────────────┐
│  MAIN (Claude Code launches here)  │
├──────────────┬─────────────────────┤
│ TEST-RUNNER  │  DOCKER             │
│              ├─────────────────────┤
│              │  SHELL              │
└──────────────┴─────────────────────┘
```

Once Claude Code starts spawning teammates (CODER, QA-ENGINEER, SECURITY-ENGINEER, etc.), Agent Teams will auto-split additional panes for each agent.

### 1.4 Launch Claude Code

```bash
# In the MAIN pane (pane 0)
claude
```

Then type inside Claude Code:
```
/speckit.implement Read Docs/Temp-prompting/IMP-INSTR.md for orchestration context
```

---

## 2. tmux Navigation Quick Reference

| Key | Action |
|-----|--------|
| `Ctrl+B` then `arrow` | Move between panes |
| `Ctrl+B` then `z` | Zoom/unzoom current pane (fullscreen toggle) |
| `Ctrl+B` then `q` | Flash pane numbers (press number to jump) |
| `Ctrl+B` then `[` | Scroll mode (navigate with arrows, `q` to exit) |
| `Ctrl+B` then `x` | Kill current pane (with confirmation) |
| `Ctrl+B` then `!` | Break pane into its own window |
| `Ctrl+B` then `{` / `}` | Swap pane position left/right |
| `Ctrl+B` then `Space` | Cycle through pane layouts |
| `Shift+Up/Down` | Navigate Claude Code agents (in-process fallback) |

### Resize Panes

```bash
# Resize current pane (direction: -U up, -D down, -L left, -R right)
Ctrl+B then :resize-pane -D 10    # 10 rows taller
Ctrl+B then :resize-pane -R 20    # 20 cols wider
```

### Session Management

```bash
# Detach from session (keeps it running)
Ctrl+B then d

# Re-attach later
tmux attach -t gravitea

# List all sessions
tmux ls

# Kill session when done
tmux kill-session -t gravitea
```

---

## 3. Your Role During Implementation

You are the **human-in-the-loop**. Agents will ask you to do things they can't (or shouldn't) do themselves.

### 3.1 Running Tests (most frequent)

When QA-ENGINEER says "Run tests", switch to your **TEST-RUNNER** pane and execute:

```bash
# Specific test file (most common)
cd backend && pytest tests/ventas/test_cuit_validation.py -v --tb=short -q

# All ventas tests
cd backend && pytest tests/ventas/ -v --tb=short -q

# Regression check (existing 334 tests)
cd backend && pytest tests/facturacion/ -v --tb=short -q

# Full suite
cd backend && pytest --tb=short -q

# With external runner script (saves summary for agent to read)
bash ~/.claude/hooks/run-tests-external.sh "pytest tests/ventas/ -v --tb=short -q"
```

After tests complete, switch back to Claude Code pane and type: **"Tests done"** or paste the summary.

### 3.2 Running Migrations

When CODER says migrations are ready:

```bash
cd backend && python manage.py migrate
```

### 3.3 Docker Operations

When DEVOPS-ENGINEER requests, in your **DOCKER** pane:

```bash
docker compose up --build -d
docker compose logs -f backend
docker compose exec backend python manage.py migrate
docker compose ps
```

### 3.4 Qdrant RAG Queries

When ARCA-EXPERT or DJANGO-EXPERT requests, in your **SHELL** pane:

```bash
# ARCA API specs
python scripts/qdrant/qdrant_search.py -c arca_api_specs -q "FECAESolicitar request structure"

# ARCA developer guides
python scripts/qdrant/qdrant_search.py -c arca_dev_guides -q "AlicIva rate mapping"

# ARCA certificates
python scripts/qdrant/qdrant_search.py -c arca_setup_certs -q "certificate renewal"

# Django/JWT wikis
python scripts/qdrant/qdrant_search.py -c wikis -q "Django select_for_update isolation"
```

### 3.5 General Django Commands

```bash
# Check migration status
cd backend && python manage.py showmigrations ventas

# Generate OpenAPI schema
cd backend && python manage.py spectacular --file schema.yml

# Interactive shell
cd backend && python manage.py shell_plus

# Check app registration
cd backend && python manage.py check
```

---

## 4. Checkpoint Protocol

At each phase checkpoint, ORCHESTRATOR will pause and show a summary like:

```
═══════════════════════════════════════════════
CHECKPOINT: Phase 3 — US1 (MVP)
═══════════════════════════════════════════════
Tasks completed: 16/16
Tests written: T090, T091, T094
Tests executed: PENDING — please run externally
Regression: PENDING — please verify 334 tests pass
═══════════════════════════════════════════════
```

**Your response options**:
- `"Continue"` — proceed to next phase
- `"Run tests first"` — you want to verify before continuing
- `"Fix X"` — something looks wrong, describe the issue
- `"Stop"` — pause work, you'll resume later

---

## 5. Quick Reference Card

```
LAUNCH:
  export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
  tmux new-session -s gravitea
  claude
  > /speckit.implement Read Docs/Temp-prompting/IMP-INSTR.md for orchestration context

NAVIGATE PANES:     Ctrl+B → arrow
ZOOM PANE:          Ctrl+B → z
SHOW PANE NUMBERS:  Ctrl+B → q
SCROLL MODE:        Ctrl+B → [       (q to exit)
DETACH SESSION:     Ctrl+B → d
RE-ATTACH:          tmux attach -t gravitea

AGENT NAVIGATION:   Shift+Up/Down (in-process fallback)

YOUR PANES:
  TEST-RUNNER  →  pytest commands
  DOCKER       →  docker compose commands
  SHELL        →  manage.py, qdrant, ad-hoc

PHASE ORDER:
  1:Setup → 2:Foundation → 3:US1(MVP) → 4:US2 → 5:US3
  → 6:US4 → 7:US5 → 8:US6 → 9:Tests → 10:Polish
```
