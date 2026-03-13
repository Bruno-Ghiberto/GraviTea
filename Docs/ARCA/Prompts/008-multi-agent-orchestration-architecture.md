# 008: Multi-Agent Orchestration Architecture for Invoice Backend

> **Document Type**: Systems Architecture Design
> **Date**: 2026-02-10 (Updated: 2026-02-10 - WSL2+Tmux revision)
> **Author**: Claude Opus 4.6 (Systems Architect)
> **Status**: REVISED - WSL2 multi-pane architecture enabled
> **Feature**: `008-facturacion-backend` (next Spec-Kit feature number)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Honesty Assessment: What Actually Works](#2-honesty-assessment)
3. [Recommended Architecture (Pragmatic)](#3-recommended-architecture)
4. [What Changed: WSL2 Unlocks Tmux Multi-Pane](#4-wsl2-tmux-upgrade)
5. [RAG-First ARCA Discovery Phase](#5-rag-first-arca-discovery-phase)
6. [Spec-Kit Integration Pipeline](#6-spec-kit-integration-pipeline)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Environment Setup Protocol](#8-environment-setup-protocol)
9. [Cost Analysis](#9-cost-analysis)
10. [Risk Matrix](#10-risk-matrix)
11. [Decision Log](#11-decision-log)

---

## 1. Executive Summary

### Goal
Build the `apps/facturacion/` backend module for GRAVITEA-ERP using multi-agent orchestration to accelerate development. The module integrates with Argentina's ARCA (ex-AFIP) electronic invoicing system via SOAP web services (WSAA + WSFEv1).

### Current State
- **Facturacion app**: Does NOT exist yet (greenfield)
- **Documentation**: Comprehensive `gravitea-invoice` SKILL.md (1,138 lines of patterns)
- **ARCA docs**: 20 PDFs ingested into Qdrant RAG (2,304 chunks across 3 collections)
- **Embedding model**: `qwen3-embedding:4b` (2560 dims, +4.1% vs baseline)
- **Spec-Kit**: Installed with constitution and 7 prior features (001-007)
- **Infrastructure**: Django 5.2, PostgreSQL 18.1 + RLS, Redis, Docker Compose

### The Core Insight

After deep research into each proposed technology, **the honest truth is**:

| Technology | Advertised | Reality | Verdict |
|-----------|-----------|---------|---------|
| Agent Teams | Visual multi-pane swarm | Real parallel agent sessions with filesystem coordination | **Production-ready, use it** |
| E2B Sandboxes | Isolated execution per agent | Real Firecracker microVMs, but overkill for Django dev | **Use for test execution only** |
| Tmux split panes | Visual swarm monitoring | Full split-pane mode available on WSL2 with Tmux installed | **NOW VIABLE - use it** |
| Qdrant RAG | Semantic ARCA doc search | Working well with qwen3-embedding:4b | **Ready to use** |

**Recommended approach**: Agent Teams with Tmux split-pane mode on WSL2 (primary orchestration) + Qdrant RAG (ARCA knowledge) + Spec-Kit (methodology). E2B optional for test isolation.

---

## 2. Honesty Assessment: What Actually Works {#2-honesty-assessment}

### 2.1 Agent Teams - Honest Status

**Research source**: Official Anthropic docs + community reverse engineering (Feb 2026)

#### What It Actually Does
- Spawns **full independent Claude Code sessions** (not lightweight threads)
- Filesystem-based coordination: `~/.claude/teams/{team-name}/config.json`
- Shared task list with file-locking for concurrency
- Peer-to-peer messaging via JSON mailboxes
- Two display modes: **in-process** (navigate with Shift+Up/Down) or **split panes** (Tmux/iTerm2)

#### Critical Limitations for Your Setup
- **Windows**: Split-pane mode NOT supported. You get in-process mode only
- **No session resumption**: Can't `/resume` teammates after restart
- **File conflict danger**: Two agents editing same file causes overwrites
- **Token cost**: ~4x a single session for a 3-agent team
- **Lead drift**: Lead sometimes starts implementing instead of delegating (use delegate mode)

**Verdict**: Production-ready for parallel task execution. Use delegate mode. Partition file ownership across agents.

### 2.2 E2B Sandboxes - Honest Status

**Research source**: Official docs, GitHub repos, pricing pages

#### What It Actually Does
- Firecracker microVMs (~150ms boot, hardware-level isolation)
- Full Linux sandbox with pip, apt, npm support
- Python SDK + MCP server available
- Can run Django + pytest in isolation
- $100 free credit (Hobby tier), ~$0.05/hr per sandbox

#### Practical Fit for GRAVITEA-ERP
- **Good for**: Running pytest suites, validating migrations, security testing
- **Overkill for**: Local development (you have Docker Compose)
- **Requires**: Custom template with Python 3.14.3+ Django 5.2 + PostgreSQL client
- **Limitation**: 10-20 GiB disk, 8 GiB RAM max, Linux only
- **MCP server**: Jupyter-focused, not full terminal proxy

**Verdict**: Optional enhancement. Useful for isolated test execution but not essential for building the invoice module. Add it later as a safety layer.

### 2.3 Tmux on WSL2 - NOW AVAILABLE

With the move to Claude Code on WSL2, Tmux split-pane mode is fully available:

- **Tmux**: Already installed on WSL2 (Linux 6.6.87.2-microsoft-standard-WSL2)
- **Agent Teams split-pane mode**: Each agent gets its own Tmux pane - visible simultaneously
- **Navigation**: Switch between panes with `Ctrl+B` then arrow keys (standard Tmux)
- **Advantage over in-process**: See all agents working in real-time, no Shift+Up/Down switching

#### How Agent Teams Uses Tmux

When `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set and Tmux is detected, Agent Teams:
1. Creates a new Tmux session (or uses the current one)
2. Splits the terminal into panes - one per agent
3. Each pane runs an independent Claude Code session
4. Agents coordinate via filesystem-based JSON mailboxes
5. You see all agents working simultaneously in their panes

#### Tmux Pane Layout for 3-Agent Team

```
┌─────────────────────────┬─────────────────────────┐
│                         │                         │
│     LEAD AGENT          │     ARCHITECT           │
│     (Delegate Mode)     │     (Models, Schema)    │
│                         │                         │
│  Coordinates tasks      │  Reads specs, queries   │
│  Monitors progress      │  Qdrant RAG, designs    │
│  Synthesizes output     │  data layer             │
│                         │                         │
├─────────────────────────┼─────────────────────────┤
│                         │                         │
│     CODER               │     REVIEWER            │
│     (ARCA Clients)      │     (Tests, Security)   │
│                         │                         │
│  Implements wsaa.py,    │  Writes pytest tests,   │
│  wsfe.py, services,     │  validates security,    │
│  views, serializers     │  checks tenant isolation│
│                         │                         │
└─────────────────────────┴─────────────────────────┘
```

#### Essential Tmux Commands

```bash
# Navigation between agent panes
Ctrl+B → arrow key    # Switch to adjacent pane
Ctrl+B → q            # Show pane numbers, then press number
Ctrl+B → z            # Zoom into current pane (toggle fullscreen)

# Session management
Ctrl+B → d            # Detach from session (agents keep running)
tmux attach -t <name> # Reattach to session

# Monitoring
Ctrl+B → [            # Enter scroll mode in a pane (q to exit)
```

**Verdict**: Fully viable. Tmux split-pane mode gives real-time visibility into all agents, which is a significant improvement over in-process mode.

### 2.4 Qdrant RAG - Honest Status

- 3 collections ingested: `arca_api_specs` (1,151), `arca_dev_guides` (1,088), `arca_setup_certs` (65)
- Model: `qwen3-embedding:4b` (2560 dims, 0.802 avg score, +4.1% vs baseline)
- Docker container running, MCP server configured
- Payload indexes on ws_name, section, source_file, environment, procedure_type

**Verdict**: Fully operational. Agents query via `scripts/qdrant_search.py` CLI tool (no Qdrant MCP server required).

---

## 3. Recommended Architecture (Pragmatic) {#3-recommended-architecture}

Based on the honest assessment, here's the production architecture with WSL2 + Tmux:

```
┌──────────────────────────── TMUX SESSION (WSL2) ───────────────────────┐
│                                                                         │
│  ┌─────────────────────────────┬───────────────────────────────────┐   │
│  │   PANE 0: LEAD AGENT        │   PANE 1: ARCHITECT              │   │
│  │   (Delegate Mode)           │   (Models, Schema, Data Layer)   │   │
│  │                             │                                   │   │
│  │ • Coordinates tasks         │ • Owns: models.py, constants.py, │   │
│  │ • Monitors all panes        │   migrations/, data-model.md     │   │
│  │ • Synthesizes output        │ • Queries: arca_api_specs        │   │
│  │ • Distributes from tasks.md │ • Designs: DB schema, FKs, idx  │   │
│  ├─────────────────────────────┼───────────────────────────────────┤   │
│  │   PANE 2: CODER             │   PANE 3: REVIEWER               │   │
│  │   (ARCA Clients, API)       │   (Tests, Security, QR)          │   │
│  │                             │                                   │   │
│  │ • Owns: arca/*.py,          │ • Owns: tests/facturacion/*.py,  │   │
│  │   services.py, views.py,    │   validators.py, qr.py           │   │
│  │   serializers.py, urls.py   │ • Reviews: tenant isolation,     │   │
│  │ • Queries: arca_dev_guides  │   encrypted keys, immutability   │   │
│  └─────────────────────────────┴───────────────────────────────────┘   │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │              SHARED INFRASTRUCTURE (all agents access)        │     │
│  │  • Qdrant CLI → scripts/qdrant_search.py (3 collections)    │     │
│  │  • Filesystem → /mnt/c/.../GRAVITEA-ERP (shared codebase)   │     │
│  │  • JSON mailboxes → ~/.claude/teams/invoice-team/            │     │
│  │  • Serena memories → .serena/memories/ (persistence)         │     │
│  │  • Ollama → qwen3-embedding:4b @ 172.26.176.1:11434         │     │
│  └───────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Architecture Layers

#### Layer 1: Orchestration (Agent Teams + Tmux Split Panes)
- **Mechanism**: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- **Display**: Tmux split-pane mode (WSL2) - 4 visible panes, one per agent
- **Lead behavior**: Delegate mode (Shift+Tab) to prevent lead from coding
- **Team size**: 4 agents (Lead + Architect + Coder + Reviewer) in 2x2 Tmux grid
- **Communication**: JSON mailboxes at `~/.claude/teams/invoice-team/`
- **Navigation**: `Ctrl+B` + arrow keys to switch between agent panes
- **Monitoring**: All agents visible simultaneously - watch progress in real time

#### Layer 2: Knowledge (Qdrant RAG)
- **Access**: All agents query via `python scripts/qdrant_search.py` (Bash tool, no MCP needed)
- **Collections**: `arca_api_specs`, `arca_dev_guides`, `arca_setup_certs`
- **Query pattern**: Agents query ARCA docs when encountering domain-specific questions
- **Embedding**: `qwen3-embedding:4b` (2560 dims), prefix added automatically by CLI tool
- **Example queries**:
  ```bash
  python scripts/qdrant_search.py --query "FECAESolicitar parametros" --collection arca_api_specs
  python scripts/qdrant_search.py --query "WSAA ticket de acceso" --collection arca_dev_guides
  python scripts/qdrant_search.py --query "certificado produccion" --collection arca_setup_certs
  ```

#### Layer 3: Memory (Serena + Git)
- **Access**: All agents share the `.serena/memories/` directory and git history
- **Usage**: Persistent cross-session memory for architectural decisions
- **Backend**: Markdown files in `.serena/memories/` (already 60+ memories from prior sessions)
- **Pattern**: Store important decisions as memory files, committed to git for persistence

#### Layer 4: Methodology (Spec-Kit)
- **Workflow**: specify → clarify → plan → tasks → implement
- **Feature number**: `008-facturacion-backend`
- **Integration**: Tasks from `specs/008-facturacion-backend/tasks.md` feed into Agent Teams task list

### 3.2 Agent Roles and File Ownership

**Critical**: Partition file ownership to prevent overwrite conflicts.

| Agent | Role | Files Owned | RAG Access |
|-------|------|-------------|------------|
| **Lead** | Coordination, task management, delegate mode | None (coordination only) | All collections |
| **Architect** | Models, migrations, constants, data layer | `models.py`, `constants.py`, `migrations/`, `data-model.md` | `arca_api_specs` |
| **Coder** | ARCA clients, services, views, serializers | `arca/*.py`, `services.py`, `views.py`, `serializers.py`, `urls.py` | `arca_dev_guides`, `arca_api_specs` |
| **Reviewer** | Tests, security review, documentation | `tests/facturacion/*.py`, `validators.py`, `qr.py` | `arca_setup_certs` |

### 3.3 What Was Dropped and Why

| Feature | Why Dropped |
|---------|-------------|
| E2B per-agent sandboxes | Overkill; agents share local filesystem safely via ownership partitioning |
| Hive Mind consensus | Agent Teams uses simpler task claims via JSON mailboxes |
| Byzantine fault tolerance | Unnecessary; 3-4 trusted agents don't need Byzantine protection |

---

## 4. What Changed: WSL2 Unlocks Tmux Multi-Pane {#4-wsl2-tmux-upgrade}

The previous version of this document listed Tmux as "not viable on your platform" because development was on Windows. With the move to **Claude Code on WSL2**, the full split-pane experience is now available.

### What's Now Possible (was blocked, now unlocked)

| Feature | Before (Windows) | Now (WSL2) |
|---------|-------------------|------------|
| Tmux split panes | Not supported | Full support - 2x2 grid, 4 agents visible |
| Real-time monitoring | Shift+Up/Down switching (clunky) | All panes visible simultaneously |
| Session persistence | Agent Teams only | Tmux sessions survive detach/reattach |
| Background execution | Must keep terminal open | `Ctrl+B d` detach, agents keep running |

### Complete Tmux Setup for Agent Teams (WSL2)

#### Step 1: Verify Tmux is available
```bash
tmux -V
# Expected: tmux 3.x (already installed on WSL2)
```

#### Step 2: Create a named session for the facturacion team
```bash
# Start a new Tmux session named "facturacion"
tmux new-session -s facturacion

# Inside the session, set the Agent Teams env var
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```

#### Step 3: Launch Claude Code (Agent Teams auto-detects Tmux)
```bash
# From inside the Tmux session
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
```

When you request a team, Agent Teams will automatically:
1. Detect the Tmux session
2. Split the window into panes (one per agent)
3. Start independent Claude Code sessions in each pane

#### Step 4: Request the team in Claude Code
```
"Create a team called invoice-team with 3 agents:
- architect: Owns models.py, constants.py, migrations/
- coder: Owns arca/*.py, services.py, views.py, serializers.py, urls.py
- reviewer: Owns tests/facturacion/*.py, validators.py, qr.py

Use delegate mode. I want to see each agent in its own Tmux pane.
All agents can query Qdrant via: python scripts/qdrant_search.py --query '...' --collection arca_api_specs"
```

#### Tmux Navigation Cheat Sheet

```
Pane Navigation:
  Ctrl+B → ↑↓←→     Switch between agent panes
  Ctrl+B → q         Show pane numbers (press number to jump)
  Ctrl+B → z         Toggle zoom on current pane (fullscreen one agent)
  Ctrl+B → !         Break pane into its own window (for deep focus)

Session Management:
  Ctrl+B → d         Detach (agents keep running in background!)
  tmux attach -t facturacion   Reattach to see agents working
  tmux ls            List all sessions

Monitoring:
  Ctrl+B → [         Enter scroll mode (navigate history, q to exit)
  Ctrl+B → :         Command mode (e.g., "capture-pane -p" to dump output)

Layout:
  Ctrl+B → space     Cycle through pane layouts (even-horizontal, tiled, etc.)
  Ctrl+B → M-1       Even horizontal split
  Ctrl+B → M-2       Even vertical split
  Ctrl+B → M-5       Tiled layout (best for 4 agents)
```

#### Advanced: Custom Tmux Config for Agent Work

Add to `~/.tmux.conf` for a better multi-agent experience:
```bash
# Visual feedback for active pane
tmux set -g pane-active-border-style 'fg=green,bold'
tmux set -g pane-border-style 'fg=grey'

# Show pane titles (agent names)
tmux set -g pane-border-status top
tmux set -g pane-border-format " #{pane_index}: #{pane_title} "

# Mouse support for clicking between panes
tmux set -g mouse on

# Increase scrollback buffer (agents produce lots of output)
tmux set -g history-limit 50000

# Status bar showing session info
tmux set -g status-right '#[fg=green]#{session_name} #[fg=white]| #[fg=yellow]%H:%M'
```

### What's Still Aspirational (Future Enhancements)

| Feature | Status | When to Revisit |
|---------|--------|-----------------|
| E2B sandbox per agent | Optional, not essential | When needing isolated test execution |
| Agent Teams session resumption | Not supported yet | When Anthropic adds `/resume` for team members |
| Cross-agent file editing | Dangerous (overwrites) | When Agent Teams adds file locking |
| 5+ agent teams | Possible but expensive (token cost) | When token costs decrease significantly |

---

## 5. Operations Manual: Complete Step-by-Step Guide {#5-operations-manual}

This section is the single reference for running the entire multi-agent workflow. Follow these steps in order.

---

### PHASE 0: Environment Boot (10 min)

#### 0.1 — Start infrastructure services

Open a terminal in WSL2 and verify all services are running:

```bash
# Verify Docker is running (Qdrant lives here)
docker ps --format "table {{.Names}}\t{{.Status}}" | head -10

# If Qdrant is not running, start it
docker start qdrant 2>/dev/null || \
  docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
    -v /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP/.qdrant_storage:/qdrant/storage \
    qdrant/qdrant

# Verify Qdrant has ARCA collections
curl -s http://localhost:6333/collections | python3 -c "
import sys, json
data = json.load(sys.stdin)
for c in data['result']['collections']:
    if c['name'].startswith('arca_'):
        print(f\"  {c['name']}: OK\")
" 2>/dev/null || echo "Qdrant: NOT READY - check Docker"

# Verify Ollama embedding model
curl -s http://172.26.176.1:11434/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
found = [m['name'] for m in data.get('models',[]) if 'qwen3-embedding' in m['name']]
print(f\"  Ollama: {found[0] if found else 'qwen3-embedding NOT FOUND - run: ollama pull qwen3-embedding:4b'}\")
" 2>/dev/null || echo "Ollama: NOT RUNNING"
```

If Qdrant collections are empty (0 chunks), re-ingest:
```bash
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
python scripts/recreate_qdrant_collections_api.py   # Recreate with 2560 dims
python scripts/ingest_arca_qdrant.py --collection all  # Ingest 20 PDFs → 2,304 chunks
```

#### 0.2 — Set up Agent Teams environment variable

```bash
# Add to ~/.bashrc for persistence across sessions
echo 'export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1' >> ~/.bashrc
source ~/.bashrc

# Verify
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# Expected: 1
```

#### 0.3 — Start a named Tmux session

```bash
# Create the session you'll use for all multi-agent work
tmux new-session -s gravitea

# You're now INSIDE the Tmux session.
# Everything below happens inside this session.
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
```

#### 0.4 — Create the feature branch

```bash
git checkout -b 008-facturacion-backend
```

---

### PHASE 1: ARCA Discovery via 3-Researcher RAG Swarm (30 min)

**Goal**: Use 3 researcher agents (one per Qdrant collection) + 1 orchestrator to query all ARCA documentation and produce a unified technical report. This report becomes direct input for `/speckit.specify`.

**Architecture**: Each researcher owns a single Qdrant collection and runs ~10 targeted queries via the `scripts/qdrant_search.py` CLI tool. The orchestrator waits for all 3 to finish, then synthesizes their findings into one 8-domain report.

**Prerequisite**: The CLI search tool must exist at `scripts/qdrant_search.py`. It wraps Qdrant vector search with qwen3-embedding:4b embeddings via Ollama. No Qdrant MCP server is needed.

#### 1.1 — Set up 4 Tmux panes manually

Create the pane layout before launching any agents:

```bash
# Inside your existing Tmux session (gravitea)
# Split into 4 panes in a 2x2 grid:

# Split horizontally
tmux split-window -h

# Split each half vertically
tmux select-pane -t 0
tmux split-window -v
tmux select-pane -t 2
tmux split-window -v

# Apply tiled layout for even sizing
tmux select-layout tiled

# Rename panes for clarity (optional, shows in border if configured)
tmux select-pane -t 0 -T "ORCHESTRATOR"
tmux select-pane -t 1 -T "R1-API-SPECS"
tmux select-pane -t 2 -T "R2-DEV-GUIDES"
tmux select-pane -t 3 -T "R3-SETUP-CERTS"
```

What you'll see:

```
┌──────────────────────┬──────────────────────┐
│ 0: ORCHESTRATOR      │ 1: R1-API-SPECS      │
│ (waits, then synth.) │ (claude + prompt)     │
├──────────────────────┼──────────────────────┤
│ 2: R2-DEV-GUIDES     │ 3: R3-SETUP-CERTS    │
│ (claude + prompt)    │ (claude + prompt)     │
└──────────────────────┴──────────────────────┘
```

#### 1.2 — Launch 3 researcher agents (one per pane)

Navigate to each researcher pane (`Ctrl+B → arrow key`) and launch Claude Code with the appropriate prompt. Start all 3 researchers first; the orchestrator runs after they finish.

**Pane 1 — Researcher 1: API Specs** (`arca_api_specs`, 1,151 chunks)

```bash
# In pane 1
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
```

Paste this prompt into the Claude Code session:

```
You are Researcher 1 (API Specs). Your job is to search the ARCA API
documentation in Qdrant and write a comprehensive findings file.

COLLECTION: arca_api_specs (1,151 chunks — WSFEv1 method specs, field
definitions, error codes, enumerations)

SEARCH TOOL: Use Bash to run:
python scripts/qdrant_search.py --query "YOUR QUERY" --collection arca_api_specs --limit 5

You can add filters: --filter ws_name=wsfev1

RUN THESE 10 QUERIES (one at a time, read each result carefully):
1. "WSFEv1 methods FECAESolicitar FECompUltimoAutorizado"
2. "FECAESolicitar request response mandatory fields"
3. "FECompUltimoAutorizado get last authorized invoice number"
4. "CbteTipo comprobante types factura A B C M codes"
5. "DocTipo document types buyer identification CUIT"
6. "CondicionIVA IVA condition codes responsable inscripto"
7. "ImpTotal amount validation equation ImpNeto ImpTrib"
8. "WSFEv1 error codes validation errors"
9. "FEParamGetTiposCbte FEParamGetTiposDoc parameter methods"
10. "FECAESolicitar CbteFch FchServDesde FchServHasta date fields"

After running all queries, synthesize the results into a structured
markdown file covering:
- WSFEv1 method catalog (name, purpose, key params)
- FECAESolicitar request/response structure (all mandatory fields)
- FECompUltimoAutorizado usage pattern
- CbteTipo enumeration (all codes with descriptions)
- DocTipo enumeration
- CondicionIVA enumeration
- Amount validation equation (ImpTotal = ...)
- Error code catalog (code → meaning)

Write your findings to: claudedocs/arca-discovery-01-api-specs.md
Include the Qdrant score for each source so the orchestrator can
assess confidence.
```

**Pane 2 — Researcher 2: Dev Guides** (`arca_dev_guides`, 1,088 chunks)

```bash
# In pane 2
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
```

Paste this prompt:

```
You are Researcher 2 (Dev Guides). Your job is to search the ARCA
developer guides in Qdrant and write a comprehensive findings file.

COLLECTION: arca_dev_guides (1,088 chunks — authentication flows,
implementation guides, regulations, code examples)

SEARCH TOOL: Use Bash to run:
python scripts/qdrant_search.py --query "YOUR QUERY" --collection arca_dev_guides --limit 5

RUN THESE 10 QUERIES (one at a time, read each result carefully):
1. "WSAA authentication flow ticket de acceso TRA"
2. "TRA XML generation service destination unique ID"
3. "CMS PKCS7 signing certificate private key LoginCms"
4. "LoginCms SOAP request response Token Sign expiration"
5. "Token Sign caching strategy 12 hour expiration"
6. "invoice issuance workflow authorization CAE lifecycle"
7. "CAE vs CAEA authorization modes differences"
8. "QR code fiscal RG 4291 base64 JSON format"
9. "code examples SOAP client implementation Python"
10. "RG 4291 RG 5427 electronic invoice regulations"

After running all queries, synthesize the results into a structured
markdown file covering:
- WSAA authentication flow (step-by-step)
- TRA XML structure and generation
- CMS/PKCS#7 signing process
- LoginCms call and Token+Sign response
- Token caching strategy and expiration
- CAE lifecycle (request → authorize → store)
- CAE vs CAEA modes
- QR code generation requirements (RG 4291)
- Relevant code patterns and implementation notes

Write your findings to: claudedocs/arca-discovery-02-dev-guides.md
Include the Qdrant score for each source so the orchestrator can
assess confidence.
```

**Pane 3 — Researcher 3: Setup & Certs** (`arca_setup_certs`, 65 chunks)

```bash
# In pane 3
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
```

Paste this prompt:

```
You are Researcher 3 (Setup & Certs). Your job is to search the ARCA
certificate and setup documentation in Qdrant.

COLLECTION: arca_setup_certs (65 chunks — certificate procedures,
environment configuration, WSASS subscription)

SEARCH TOOL: Use Bash to run:
python scripts/qdrant_search.py --query "YOUR QUERY" --collection arca_setup_certs --limit 5

You can add filters: --filter environment=produccion

RUN THESE 8 QUERIES (one at a time, read each result carefully):
1. "WSASS enrollment subscribe web service testing"
2. "certificate management digital certificate generation"
3. "production certificates obtener certificado produccion"
4. "certificate web service association bind cert to WS"
5. "delegation autorizar otro CUIT certificate delegation"
6. "ARCA architecture endpoints homologacion produccion URLs"
7. "TLS requirements minimum version migration timeline"
8. "WSAA WSFE endpoint URLs testing production environments"

After running all queries, synthesize the results into a structured
markdown file covering:
- WSASS enrollment process for testing environment
- Certificate generation procedure (homologacion + produccion)
- Certificate-to-web-service association
- Delegation (using certs on behalf of another CUIT)
- Environment endpoints (all WSAA + WSFEv1 URLs)
- TLS requirements and migration notes
- Architecture overview

Write your findings to: claudedocs/arca-discovery-03-setup-certs.md
Include the Qdrant score for each source so the orchestrator can
assess confidence.
```

#### 1.3 — Monitor researchers in Tmux

While the 3 researchers work in parallel:

| Action | Tmux Command |
|--------|-------------|
| Switch between panes | `Ctrl+B → arrow key` |
| Zoom into one researcher | `Ctrl+B → z` (toggle) |
| Check scroll history | `Ctrl+B → [` then scroll, `q` to exit |
| Detach (researchers keep running) | `Ctrl+B → d` |
| Reattach | `tmux attach -t gravitea` |

**Estimated time**: ~10-15 min per researcher (limited by Ollama embedding speed).

#### 1.4 — How agents query Qdrant (via CLI, not MCP)

There is no Qdrant MCP server. Agents search via the `scripts/qdrant_search.py` CLI tool using Bash.

**Basic search** (what the agent runs in its Bash tool):
```bash
python scripts/qdrant_search.py \
  --query "FECAESolicitar campos obligatorios" \
  --collection arca_api_specs \
  --limit 5
```

**Filtered search** (narrowing to a specific web service):
```bash
python scripts/qdrant_search.py \
  --query "error codes validation" \
  --collection arca_api_specs \
  --limit 10 \
  --filter ws_name=wsfev1
```

**Output format** (what the agent sees):
```
=== Qdrant Search Results ===
Collection: arca_api_specs
Query: FECAESolicitar campos obligatorios
Results: 5

--- Result 1 (score: 0.8523) ---
Source: wsfev1_manual_v3.pdf
Page: 42
Section: 4.1.1 FECAESolicitar
Text:
El método FECAESolicitar permite solicitar la autorización de comprobantes
electrónicos. Los campos obligatorios son: CbteTipo, PtoVta, CbteDesde...

--- Result 2 (score: 0.8104) ---
...
```

#### 1.5 — RAG collection reference

| Collection | Chunks | Focus | Good Queries |
|-----------|--------|-------|-------------|
| `arca_api_specs` | 1,151 | Method signatures, field specs, error codes, enumerations | `FECAESolicitar`, `CbteTipo`, `error code`, `ImpTotal` |
| `arca_dev_guides` | 1,088 | Auth flows, implementation guides, regulations, code examples | `WSAA`, `LoginCms`, `TRA`, `token sign`, `RG 4291` |
| `arca_setup_certs` | 65 | Certificate setup, environment config, WSASS subscription | `certificado produccion`, `homologacion`, `WSASS` |

The `search_query: ` prefix is added automatically by the CLI tool — agents just provide natural language queries.

#### 1.6 — Orchestrator: synthesize findings

Once all 3 researchers have written their files, switch to **pane 0** (orchestrator) and launch Claude Code:

```bash
# In pane 0
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
```

Paste this prompt:

```
You are the Orchestrator. Three researcher agents have queried ARCA
documentation in Qdrant and produced findings files. Your job is to
synthesize their work into a single unified technical report.

READ THESE INPUT FILES:
1. @Docs/ARCA/Researches/arca-discovery-01-api-specs.md
2. @Docs/ARCA/Researches/arca-discovery-02-dev-guides.md
3. @Docs/ARCA/Researches/arca-discovery-03-setup-certs.md
4. skills/gravitea-invoice/SKILL.md (existing implementation patterns)

PRODUCE A UNIFIED REPORT covering these 8 domains:

1. WSAA Authentication
   - Complete auth flow (TRA → CMS sign → LoginCms → Token+Sign)
   - Token caching strategy (TTL, per-tenant isolation)
   - Certificate requirements per environment

2. WSFEv1 Invoice Issuance
   - Method catalog (FECAESolicitar, FECompUltimoAutorizado, FEParamGet*)
   - FECAESolicitar request structure (all mandatory fields)
   - Response handling and CAE extraction

3. Comprobante Types
   - CbteTipo enumeration (all codes with descriptions)
   - DocTipo enumeration
   - CondicionIVA enumeration and seller/buyer matrix
   - MonedaTipo codes

4. Error Handling
   - Error code catalog from WSFEv1
   - Common validation errors and their causes
   - Retry vs fatal error classification

5. Amount Validation
   - ImpTotal equation (all component fields)
   - Decimal precision requirements
   - Rounding rules

6. Certificates & Environments
   - Homologacion vs produccion setup
   - WSASS enrollment
   - Certificate generation and association
   - All endpoint URLs (WSAA + WSFEv1 per environment)

7. CAE Lifecycle
   - CAE request → authorization → storage flow
   - CAE vs CAEA comparison
   - Expiration and fiscal QR (RG 4291)

8. Gaps & Confidence Assessment
   - What was well-covered (high Qdrant scores)
   - What had weak coverage (low scores or missing)
   - Recommendations for manual verification

OUTPUT FILE: claudedocs/arca-discovery-unified-report.md

FORMAT: Use markdown headers for each domain, include source references,
and flag any contradictions between researchers. Include some mermaid charts inside the .md file, they might come in handy. This report will be the primary input context for /speckit.specify.
```

#### 1.7 — Review findings and commit checkpoint

Once the orchestrator finishes, verify all output files exist:

```bash
# Check all discovery outputs
ls -la claudedocs/arca-discovery-0*.md
ls -la claudedocs/arca-discovery-unified-report.md

# Quick quality check on the unified report
wc -l claudedocs/arca-discovery-unified-report.md
# Expected: 200+ lines

# Spot-check coverage of key domains
grep -c "WSAA\|WSFEv1\|CbteTipo\|ImpTotal\|CAE\|certificado\|error" \
  claudedocs/arca-discovery-unified-report.md
```

Commit the discovery as a checkpoint:
```bash
git add claudedocs/arca-discovery-*.md scripts/qdrant_search.py
git commit -m "Phase 1: ARCA discovery findings from 3-researcher RAG swarm

- R1: API specs (WSFEv1 methods, types, errors)
- R2: Dev guides (WSAA auth, CAE lifecycle, QR codes)
- R3: Setup/certs (environments, certificates, WSASS)
- Orchestrator: unified 8-domain report for speckit.specify"
```

---

### PHASE 2: Spec-Kit Pipeline — specify → clarify → plan → tasks (25 min)

**Goal**: Transform discovery findings into a formal specification, implementation plan, and task list using the Spec-Kit workflow.

#### 2.1 — Run /speckit.specify

Start a fresh Claude Code session (single agent, not a team):

```bash
claude
```

Then paste this prompt:

```
/speckit.specify

Build the electronic invoicing backend module (facturacion) for GRAVITEA-ERP
that integrates with Argentina's ARCA (ex-AFIP) system. The module must:

1. Authenticate with ARCA via WSAA (certificate-based TRA/LoginCms flow)
   with Redis-cached Token+Sign pairs (11-hour TTL per tenant)

2. Issue electronic invoices via WSFEv1 SOAP API supporting comprobante
   types A, B, C, and M (determined by seller/buyer IVA condition matrix)

3. Support the full CAE lifecycle: FECompUltimoAutorizado (get next number),
   FECAESolicitar (request authorization), and proper error handling with
   ARCA error codes

4. Store authorized invoices in an immutable ledger (append-only Comprobante
   model with TenantBoundModel isolation)

5. Generate ARCA-compliant fiscal QR codes for printed invoices per
   RG 4291 requirements

6. Support multi-tenant credential management with encrypted private keys
   (AES-256-GCM via existing EncryptedTextField)

7. Handle both homologacion (testing) and produccion (live) ARCA environments
   with certificate chain validation

Context: See @Docs/ARCA/Researches/arca-discovery-unified-report.md for the complete
ARCA technical report (8 domains, sourced from 3 Qdrant collections).
Also reference skills/gravitea-invoice/SKILL.md for implementation patterns.
```

**Output**: `specs/008-facturacion-backend/spec.md`

#### 2.2 — Run /speckit.clarify (if needed)

```
/speckit.clarify
```

This resolves any `[NEEDS CLARIFICATION]` markers. The agent may ask you questions or query Qdrant RAG for domain-specific answers.

#### 2.3 — Run /speckit.plan

```
/speckit.plan Django 5.2 + DRF + PostgreSQL 18.1 + zeep (SOAP) + cryptography (AES-256-GCM)
```

**Output**: `specs/008-facturacion-backend/plan.md`, `research.md`, `data-model.md`, `contracts/`

#### 2.4 — Run /speckit.tasks

```
/speckit.tasks
```

**Output**: `specs/invoice-backend-developement/tasks.md` with phased task breakdown. Tasks marked `[P]` can run in parallel.

#### 2.5 — Run /speckit.analyze (quality gate)

```
/speckit.analyze
```

This validates cross-artifact consistency between spec.md, plan.md, and tasks.md. Fix any issues before proceeding.

#### 2.6 — Commit the spec artifacts

```bash
git add specs/invoice-backend-developement/
git commit -m "Phase 1-4: Spec-Kit pipeline complete for facturacion backend"
```

---

### PHASE 3: Multi-Agent Implementation via Tmux (2-3 hours)

**Goal**: Use a 4-agent team (Lead + Architect + Coder + Reviewer) in Tmux split panes to implement the facturacion module in parallel.

#### 3.1 — Start Claude Code inside Tmux

Make sure you're in the Tmux session:
```bash
# If detached, reattach
tmux attach -t gravitea

# Navigate to project root
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP

# Launch Claude Code
claude
```

#### 3.2 — Request the implementation team

Paste this prompt:

```
Create a team called "invoice-impl" with 3 worker agents.
Spawn each worker with the specified subagent_type for specialized expertise.

TASK SOURCE: Read specs/invoice-backend-developement/tasks.md for the full
62-task breakdown across 10 phases. Each agent is assigned specific task IDs
from that file. Follow the task descriptions exactly as written there.

SKILL REFERENCE: All agents must follow skills/gravitea-invoice/SKILL.md
patterns exactly. REVIEWER also follows skills/gravitea-testing/SKILL.md.

STRICT FILE OWNERSHIP — agents ONLY edit files in their list.
To request a change in another agent's file, message the Lead.

ARCHITECT agent (subagent_type: system-architect):
  Owns:
    backend/apps/facturacion/__init__.py
    backend/apps/facturacion/apps.py
    backend/apps/facturacion/constants.py
    backend/apps/facturacion/models.py
    backend/apps/facturacion/arca/exceptions.py
    backend/apps/facturacion/migrations/
    backend/database/sql/facturacion_rls.sql
    backend/requirements/base.txt            (add zeep dependency only)
    backend/gravitea/settings/base.py        (register app in INSTALLED_APPS only)
  Tasks: T001, T002, T003, T004, T005, T006, T007, T008, T009, T010, T011,
         T023 (system check in apps.py), T031 (resolver in constants.py)
  RAG: python scripts/qdrant_search.py --collection arca_api_specs --query "..."

CODER agent (subagent_type: backend-architect):
  Owns:
    backend/apps/facturacion/arca/__init__.py
    backend/apps/facturacion/arca/wsaa.py
    backend/apps/facturacion/arca/wsfe.py
    backend/apps/facturacion/arca/caea.py
    backend/apps/facturacion/services.py
    backend/apps/facturacion/views.py
    backend/apps/facturacion/serializers.py
    backend/apps/facturacion/urls.py
    backend/apps/facturacion/schema.py
    backend/apps/facturacion/metrics.py
    backend/gravitea/urls.py                 (wire facturacion URL config only)
  Tasks: T013, T014, T015, T016, T017,
         T019, T020, T021, T022 (US3 credential API),
         T026, T027, T028 (US1 WSAA auth + caching inside wsaa.py + facade),
         T035, T036, T037, T038, T039, T040, T041 (US2 CAE issuance),
         T044 (US5 QR endpoint on views.py),
         T047, T048 (US6 NC/ND service + serializer),
         T049, T050, T051, T052, T053 (US7 CAEA),
         T053a (services.py recovery implementation only),
         T054, T055, T056 (Phase 10 metrics + schema)
  RAG: python scripts/qdrant_search.py --collection arca_dev_guides --query "..."
       python scripts/qdrant_search.py --collection arca_api_specs --query "..."

REVIEWER agent (subagent_type: quality-engineer):
  Owns:
    backend/apps/facturacion/validators.py
    backend/apps/facturacion/qr.py
    backend/tests/facturacion/               (all files under unit/ and integration/)
  Tasks: T012 (test infrastructure + conftest.py),
         T018 (US3 model tests), T024, T025 (US1 WSAA tests),
         T029, T030 (US4 validation tests), T032 (validators.py),
         T033, T034 (US2 model + API tests),
         T042 (US5 QR tests), T043 (qr.py implementation),
         T045, T046 (US6 CbteAsoc tests + validator),
         T049a, T049b (US7 CAEA tests),
         T053a (test part in tests/facturacion/unit/test_models.py only),
         T057, T058 (Phase 10 homologation integration tests),
         T059 (end-to-end quickstart validation)
  RAG: python scripts/qdrant_search.py --collection arca_api_specs --query "..."
       python scripts/qdrant_search.py --collection arca_dev_guides --query "..."

LEAD ORCHESTRATION — Assign tasks following this phase order:

  1. Phase 1 (T001-T004): ARCHITECT scaffolds the app. Others wait.
  2. Phase 2 (T005-T017): All agents work in parallel:
     - ARCHITECT: T005, T006, T007, T008, T009, T010, T011
     - CODER: T013, T015, T016, T017 (wait for T007 before T015-T017)
     - CODER: T014 (wire main urlconf, after T013)
     - REVIEWER: T012 (test infra — can start immediately)
     Phase 2 MUST fully complete before any user story work begins.
  3. After Phase 2 — two parallel tracks:
     Track A (critical path): Phase 3 (US3) → Phase 4 (US1) → Phase 6 (US2)
     Track B (independent):   Phase 5 (US4) — runs in parallel with Track A
     Assign ARCHITECT T031 (Track B) and T023 (Track A) when ready.
  4. After US2 completes — Phase 7/8/9 (US5, US6, US7) can start in parallel.
  5. Phase 10 (T053a-T059): Polish after all user stories complete.

COORDINATION RULES:
- DO NOT edit files outside your ownership. Message the Lead for cross-agent changes.
- ARCHITECT finishes constants.py (T005) + models.py (T007) + migration (T008-T011) FIRST.
- CODER can start arca/wsaa.py (T026) before models.py is done (no model dependency).
- CODER waits for models.py (T007) before serializers.py, views.py, and services.py.
- REVIEWER can start test infrastructure (T012) and qr.py (T043) immediately.
- REVIEWER must wait for constants.py (T005) before validators.py (T032).
- Test directory uses unit/ and integration/ subdirectories:
    tests/facturacion/unit/        (test_models.py, test_validators.py, test_constants.py,
                                    test_wsaa.py, test_qr.py, test_caea.py)
    tests/facturacion/integration/ (test_api.py, test_wsaa_homo.py, test_wsfe_homo.py)
- Comprobante immutability: save() raises ValueError for AUTORIZADO or OBSERVADO.
  delete() always raises ValueError. DRAFT and RECHAZADO are mutable.
- All agents: query Qdrant RAG when you need ARCA-specific details.
  Use: python scripts/qdrant_search.py --query "..." --collection <collection_name>
```

#### 3.3 — What you'll see in Tmux

```
┌──────────────────────────────┬──────────────────────────────┐
│ PANE 0: LEAD                 │ PANE 1: ARCHITECT            │
│                              │                              │
│ You're here, monitoring.     │ Phase 1: T001-T004 setup     │
│ Agents send you status       │ Phase 2: T005 constants,     │
│ messages as they work.       │   T006 exceptions,           │
│ Assign tasks by phase.       │   T007 all 7 models,         │
│                              │   T008-T011 migration+RLS    │
│ Switch panes: Ctrl+B → ←→↑↓ │                              │
│ Zoom a pane:  Ctrl+B → z    │ Querying arca_api_specs for  │
│ Detach:       Ctrl+B → d    │ CbteTipo enumerations...     │
├──────────────────────────────┼──────────────────────────────┤
│ PANE 2: CODER                │ PANE 3: REVIEWER             │
│                              │                              │
│ Phase 2: T013 urls.py setup  │ T012: test infra + conftest  │
│ Can start arca/wsaa.py       │ (can start immediately)      │
│ (T026) before models done    │                              │
│ Waits for T007 before        │ Starting qr.py (T043)...     │
│ serializers/views/services   │ Waits for T005 before        │
│                              │ validators.py (T032)         │
└──────────────────────────────┴──────────────────────────────┘
```

#### 3.4 — Monitoring the team

While agents work, you can:

| Action | Tmux Command |
|--------|-------------|
| See all 4 panes at once | Default view (tiled layout) |
| Focus on one agent | `Ctrl+B → z` (zoom toggle) |
| Check agent output history | `Ctrl+B → [` then scroll up, `q` to exit |
| Walk away safely | `Ctrl+B → d` (detach — agents keep running) |
| Come back | `tmux attach -t gravitea` |
| Kill a stuck agent pane | `Ctrl+B → x` then confirm `y` |
| Rebalance pane layout | `Ctrl+B → space` (cycles layouts) |
| Tiled 2x2 layout | `Ctrl+B → M-5` |

#### 3.5 — Handling dependencies between agents

The implementation has a phased dependency chain based on tasks.md:

```
Phase 1-2: FOUNDATION (all agents contribute)
ARCHITECT: T005 constants → T006 exceptions → T007 models → T008-T011 migration+RLS
CODER:     T013 urls.py (no deps) ──► T015-T017 PuntoDeVenta API (waits for T007)
REVIEWER:  T012 test infra (no deps)
         │
         ▼ (Phase 2 complete — Lead announces checkpoint)
         │
    ┌────┴───────────────────────┐
    ▼                            ▼
  TRACK A (critical path)      TRACK B (parallel)
  US3 → US1 → US2              US4 (validation)
  CODER: serializers, views,   ARCHITECT: T031 (resolver)
         wsaa, wsfe, services   REVIEWER: T029-T030 (tests),
  REVIEWER: tests per story              T032 (validators.py)
         │
         ▼ (US2 complete)
    ┌────┼────────┐
    ▼    ▼        ▼
  US5  US6      US7
  (QR) (NC/ND)  (CAEA)  ← all three can run in parallel
```

**What to do when an agent is blocked:**
1. Check the Lead pane for coordination messages
2. If Architect is slow on models.py, Coder can start `arca/wsaa.py` (T026 — no model dependency)
3. Reviewer can start test infrastructure (T012) and `qr.py` (T043) immediately
4. Reviewer must wait for constants.py (T005) before `validators.py` (T032)

#### 3.6 — Checkpoint commits during implementation

Periodically (every 30 min or after a major component completes):

```bash
# Switch to a pane with shell access or open a new Tmux window
# Ctrl+B → c  (new window)
# Ctrl+B → n  (switch windows)

cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
git add backend/apps/facturacion/ backend/tests/facturacion/ backend/database/sql/facturacion_rls.sql
git commit -m "WIP: facturacion module - models and constants complete"
```

---

### PHASE 4: Validation and Integration (30 min)

**Goal**: Run tests, fix failures, and verify the module integrates with the existing codebase.

#### 4.1 — Run the test suite

```bash
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP/backend

# Run facturacion tests
pytest tests/facturacion/ -v

# Run security tests (tenant isolation, encryption)
pytest -m "security" -v

# Run full suite to check for regressions
pytest --tb=short
```

#### 4.2 — Verify Django integration

```bash
# Check for migration issues
python manage.py makemigrations --check --dry-run

# Run system checks
python manage.py check

# Verify the app is registered correctly
python manage.py showmigrations facturacion
```

#### 4.3 — Final commit

```bash
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
git add backend/apps/facturacion/ backend/tests/facturacion/ backend/database/sql/ backend/gravitea/settings/ backend/gravitea/urls.py backend/requirements/base.txt
git commit -m "feat: complete facturacion backend module with ARCA integration

- WSAA authentication (TRA gen, CMS signing, token caching)
- WSFEv1 invoice issuance (CAE lifecycle)
- Immutable Comprobante model with tenant isolation
- Fiscal QR code generation (RG 4291)
- Multi-tenant encrypted credentials
- Full test coverage"
```

---

### PHASE 5: Troubleshooting

#### Agent pane is stuck / unresponsive
```bash
# Zoom into the pane
Ctrl+B → z
# If no activity, kill it
Ctrl+B → x → y
# Manually do that agent's remaining work in your Lead pane
```

#### RAG queries return irrelevant results
```bash
# Add payload filters to narrow results:
python scripts/qdrant_search.py --query "FECAESolicitar" \
  --collection arca_api_specs --filter ws_name=wsfev1

# Try different query phrasing:
python scripts/qdrant_search.py --query "campos obligatorios solicitar CAE" \
  --collection arca_api_specs --limit 10
```

#### File conflict between agents
```bash
# Check git status for conflicts
git status
git diff

# The ownership rules should prevent this, but if it happens:
# 1. Check which agent owns the file (see section 3.2)
# 2. Keep that agent's version
# 3. Have the other agent redo their work in their own files
```

#### Tmux session crashed
```bash
# List sessions
tmux ls

# If the session died, agents are gone. Start fresh:
tmux new-session -s gravitea
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
claude
# Re-request the team, picking up from the last git commit
```

#### Agent Teams not splitting into panes
```bash
# Verify you're inside a Tmux session
echo $TMUX
# Should print something like: /tmp/tmux-1000/default,12345,0

# If empty, you're NOT in Tmux. Start one:
tmux new-session -s gravitea

# Verify env var
echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS
# Must be: 1
```

#### Spec-Kit command not found
```
# Spec-Kit commands are Claude Code slash commands, not bash commands.
# They must be typed inside a Claude Code session:
claude
# Then type: /speckit.specify ...
```

---

### Quick Reference Card

```
FULL WORKFLOW IN ORDER:
━━━━━━━━━━━━━━━━━━━━━

0. BOOT
   docker start qdrant
   export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
   tmux new-session -s gravitea
   cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP
   git checkout -b 008-facturacion-backend

1. DISCOVER (3 researchers + orchestrator, ~30 min)
   Open 4 Tmux panes. Launch claude in panes 1-3 with researcher prompts.
   R1→arca_api_specs  R2→arca_dev_guides  R3→arca_setup_certs
   After R1-R3 finish, launch orchestrator in pane 0 to synthesize.
   Output: claudedocs/arca-discovery-{01,02,03}-*.md + unified-report.md
   git commit checkpoint

2. SPECIFY (single agent, ~25 min)
   claude → /speckit.specify → /speckit.clarify → /speckit.plan → /speckit.tasks → /speckit.analyze
   Output: specs/008-facturacion-backend/{spec,plan,tasks}.md
   git commit checkpoint

3. IMPLEMENT (multi-agent in Tmux, ~2-3 hours)
   claude → request "invoice-impl" team with file ownership
   Architect: models, constants, migrations
   Coder: ARCA clients, services, views
   Reviewer: validators, QR, tests
   git commit checkpoints every 30 min

4. VALIDATE (single agent, ~30 min)
   pytest tests/facturacion/ -v
   pytest -m "security" -v
   python manage.py check
   git commit final

TMUX CHEAT SHEET:
  Ctrl+B ←→↑↓  Switch panes     Ctrl+B z   Zoom pane
  Ctrl+B d      Detach           Ctrl+B [   Scroll history
  Ctrl+B q      Show pane #s     Ctrl+B M-5 Tiled layout
  tmux attach -t gravitea        Reattach
```

---

## 8. Environment Setup Protocol {#8-environment-setup-protocol}

### 8.1 Prerequisites Checklist (WSL2)

```
[Required - Core]
□ Claude Code installed and authenticated on WSL2
□ Tmux installed (verify: tmux -V)
□ CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 set in environment
□ Git on feature/inventory-backend or 008-facturacion-backend branch
□ Python 3.14.3virtual environment active
□ Django project runnable (manage.py check passes)

[Required - RAG]
□ Docker Desktop running (WSL2 backend)
□ Qdrant container running (port 6333)
□ Ollama running with qwen3-embedding:4b (port 11434)
□ Qdrant collections populated (2,304 chunks across 3 collections)
□ scripts/qdrant_search.py exists and works (verify: python scripts/qdrant_search.py --query test --collection arca_api_specs --limit 1)

[Optional - E2B]
□ E2B account created at e2b.dev
□ E2B_API_KEY environment variable set
□ E2B MCP server installed: npm install -g @e2b/mcp-server

```

### 8.2 MCP Server Configuration (WSL2)

Your `~/.claude/settings.json` should include:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Agents query Qdrant via `scripts/qdrant_search.py` (no MCP server needed):

```bash
# Verify the search tool works:
python scripts/qdrant_search.py --query "FECAESolicitar" --collection arca_api_specs --limit 2
```

### 8.3 Optional E2B Setup

If you want sandboxed test execution later:

```bash
# Install E2B MCP server
npm install -g @e2b/mcp-server

# Set API key
export E2B_API_KEY="e2b_your_key_here"

# Add to .claude/settings.json mcpServers:
# "e2b": {
#   "command": "npx",
#   "args": ["-y", "@e2b/mcp-server"],
#   "env": { "E2B_API_KEY": "e2b_your_key_here" }
# }

# Verify
npx @e2b/mcp-server --version
```

### 8.4 Verification Commands (WSL2 Bash)

```bash
#!/bin/bash
echo "=== Service Verification (WSL2) ==="

# Tmux
if command -v tmux &>/dev/null; then
    echo -e "\033[32mTmux: OK ($(tmux -V))\033[0m"
else
    echo -e "\033[31mTmux: FAIL (not installed)\033[0m"
fi

# Qdrant
if curl -s http://localhost:6333/collections | grep -q "arca_"; then
    COLS=$(curl -s http://localhost:6333/collections | python3 -c "import sys,json; print(len([c for c in json.load(sys.stdin)['result']['collections'] if c['name'].startswith('arca_')]))")
    echo -e "\033[32mQdrant: OK ($COLS arca collections)\033[0m"
else
    echo -e "\033[31mQdrant: FAIL (not running or no arca collections)\033[0m"
fi

# Ollama
if curl -s http://172.26.176.1:11434/api/tags | grep -q "qwen3-embedding"; then
    echo -e "\033[32mOllama: OK (qwen3-embedding found)\033[0m"
else
    echo -e "\033[33mOllama: WARN (qwen3-embedding not found)\033[0m"
fi

# Django
if cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP/backend && python manage.py check 2>/dev/null; then
    echo -e "\033[32mDjango: OK\033[0m"
else
    echo -e "\033[31mDjango: FAIL\033[0m"
fi

# Agent Teams env
if [ "$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS" = "1" ]; then
    echo -e "\033[32mAgent Teams: OK (enabled)\033[0m"
else
    echo -e "\033[33mAgent Teams: DISABLED (set CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)\033[0m"
fi

# Tmux session check
if tmux has-session -t facturacion 2>/dev/null; then
    echo -e "\033[32mTmux session 'facturacion': ACTIVE\033[0m"
else
    echo -e "\033[33mTmux session 'facturacion': NOT STARTED (run: tmux new-session -s facturacion)\033[0m"
fi
```

---

## 9. Cost Analysis {#9-cost-analysis}

### 9.1 Token Cost Estimates

| Phase | Agents | Est. Tokens | Est. Cost (Opus 4.6) |
|-------|--------|-------------|---------------------|
| Discovery Swarm (3R + 1O) | 4 | ~500K | ~$8-12 |
| Spec-Kit Pipeline | 1 | ~200K | ~$3-5 |
| Implementation Team | 4 | ~1.2M | ~$18-30 |
| Validation & Polish | 1 | ~150K | ~$2-4 |
| **Total** | - | **~1.95M** | **~$29-49** |

**Note**: The Discovery phase uses 4 independent sessions (3 researchers + 1 orchestrator). Using Sonnet 4.5 or Haiku 4.5 for researchers reduces cost significantly.

### 9.2 Model Optimization Strategy

```
Lead Agent: Opus 4.6 (needs strategic reasoning)
Architect: Opus 4.6 (needs architectural design capability)
Coder: Sonnet 4.5 (code generation is strong on Sonnet)
Reviewer: Sonnet 4.5 (code review works well on Sonnet)
Discovery Researchers: Haiku 4.5 (RAG queries + summarization)
```

This mixed-model approach can reduce total cost by ~40-60%.

### 9.3 E2B Cost (If Used)

| Scenario | Cost |
|----------|------|
| 10 pytest runs × 5 min each | ~$0.08 |
| Monthly dev usage | ~$2-5 |
| Free credit available | $100 |

E2B cost is negligible compared to LLM token costs.

---

## 10. Risk Matrix {#10-risk-matrix}

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Agent Teams file conflicts | High | Medium | Strict file ownership partitioning |
| RAG returns irrelevant ARCA info | Medium | Low | Use payload filters (ws_name, section) |
| Lead agent starts coding (not delegating) | Medium | Medium | Use delegate mode (Shift+Tab) |
| Token budget exceeded | Medium | Medium | Use Sonnet for workers, set max turns |
| ARCA SOAP complexity > expected | Low | High | gravitea-invoice SKILL has patterns |
| Agent Teams experimental instability | Low | High | Save frequently, manual fallback ready |
| Context window overflow per agent | Medium | Medium | Each agent starts fresh, task-scoped |
| Discovery swarm produces low-quality findings | Low | Medium | Orchestrator cross-checks 3 sources; manual review of unified report |

### Mitigation: Manual Fallback Plan

If Agent Teams proves unstable, the entire workflow can be executed with a single Claude Code session:

```
Single-Agent Fallback:
1. Run /speckit.specify with discovery findings (manually gathered)
2. Run /speckit.plan → /speckit.tasks
3. Run /speckit.implement (single agent, sequential execution)
4. Use Task tool for sub-agent spawning (lighter than Agent Teams)
```

---

## 11. Decision Log {#11-decision-log}

| Decision | Chosen | Rejected | Rationale |
|----------|--------|----------|-----------|
| Primary orchestration | Agent Teams + Tmux | In-process mode | WSL2 unlocks split-pane - see all agents simultaneously |
| RAG model | qwen3-embedding:4b | nomic, bge-m3, arctic, gemma | Benchmarked winner at +4.1% |
| Methodology | Spec-Kit | Ad-hoc implementation | Proven pipeline with 7 prior features |
| E2B usage | Optional (test only) | Per-agent sandboxes | Overkill for local dev; useful for test isolation |
| Memory layer | Serena memories + git | External memory servers | Already have 60+ memory files, zero additional overhead |
| Discovery phase | 3 researchers + orchestrator | 2-researcher design | One agent per collection maximizes coverage; orchestrator synthesizes |
| RAG access | CLI tool (qdrant_search.py) | Qdrant MCP server | No Qdrant MCP exists; CLI via Bash works from any agent |
| Team size | 4 (Lead + 3 workers) | 5+ agents | Token cost scales; 4 covers all roles in 2x2 Tmux grid |
| Worker model | Sonnet 4.5 | Opus for all | Cost optimization; Sonnet handles code well |
| Platform | WSL2 (Linux) | Windows native | Tmux support, better CLI experience, native Claude Code |

---

## Appendix A: Existing Spec-Kit Features

```
specs/
├── 001-backend-core/           ✅ Complete
├── 002-backend-stabilization/  ✅ Complete
├── 003-api-contracts-hardening/ ✅ Complete
├── 004-observability-metrics/  ✅ Complete
├── 005-debug-testing-docker/   ✅ Complete
├── 006-debug-hardening/        ✅ Complete
├── 007-test-hardening/         ✅ Complete
└── 008-facturacion-backend/    ⏳ Next (this document)
```

## Appendix B: ARCA Documentation Inventory

| Collection | Documents | Chunks | Key Content |
|-----------|-----------|--------|-------------|
| `arca_api_specs` | WSFEv1 Manual v3.0, MTXCA v25, WSBFEV1 v3.0, WSFEX v3.1.1, Architecture | 1,151 | Method signatures, field specs, error codes |
| `arca_dev_guides` | WSCT v1.6.4, WSSEG v0.9, WSAA Spec v1.2.2, RG 4291/5427/2904/2668 | 1,088 | Implementation guides, auth flows, regulations |
| `arca_setup_certs` | Cert procedures (3), WSASS docs (2), Cert chains (3) | 65 | Certificate setup, environment config |

## Appendix C: Module Structure (Target)

```
backend/apps/facturacion/
├── __init__.py
├── apps.py                     # FacuracionConfig
├── migrations/
│   └── __init__.py
├── models.py                   # Comprobante, ARCACredential, PuntoDeVenta
├── constants.py                # CbteTipo, DocTipo, CondicionIVA, MonedaTipo
├── validators.py               # Amount validation, CUIT validation
├── qr.py                       # Fiscal QR code generation (RG 4291)
├── services.py                 # InvoiceService orchestration
├── serializers.py              # DRF serializers
├── views.py                    # API ViewSets
├── urls.py                     # URL routing
├── permissions.py              # Custom DRF permissions
├── schema.py                   # drf-spectacular schema extensions
├── checks.py                   # NTP sync system check
└── arca/
    ├── __init__.py
    ├── wsaa.py                 # WSAAClient (TRA, LoginCms, caching)
    ├── wsfe.py                 # WSFEv1Client (FECAESolicitar, etc.)
    └── auth_cache.py           # Redis Token+Sign cache (11hr TTL)

tests/facturacion/
├── __init__.py
├── test_wsaa.py                # TRA gen, signing, token caching
├── test_wsfe.py                # Invoice flow, error handling
├── test_amount_validation.py   # Decimal precision, rounding
├── test_qr.py                  # QR code content validation
├── test_comprobante_models.py  # Immutability, tenant isolation
├── test_invoice_api.py         # API endpoints, permissions
└── conftest.py                 # Facturacion-specific fixtures
```

## Appendix D: Quick Command Reference (WSL2 + Tmux)

```bash
# === SETUP: Tmux + Agent Teams ===
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
tmux new-session -s facturacion
cd /mnt/c/Users/Ghibe/Documents/Gravitea/GRAVITEA-ERP

# === PHASE 1: Discovery (4 Tmux panes) ===
# Split into 4 panes: tmux split-window -h && ... (see section 1.1)
# Pane 1: claude → R1 prompt (arca_api_specs, 10 queries)
# Pane 2: claude → R2 prompt (arca_dev_guides, 10 queries)
# Pane 3: claude → R3 prompt (arca_setup_certs, 8 queries)
# Wait for R1-R3 → Pane 0: claude → Orchestrator prompt (synthesize)

# === TMUX NAVIGATION (while agents work) ===
# Ctrl+B → arrow key    Switch between agent panes
# Ctrl+B → z            Zoom into one agent (toggle)
# Ctrl+B → q            Show pane numbers
# Ctrl+B → d            Detach (agents keep running!)
# tmux attach -t facturacion   Reattach

# === PHASE 1-4: Spec-Kit (single agent session) ===
# /speckit.specify "Build electronic invoicing..."
# /speckit.clarify
# /speckit.plan "Django 5.2 + DRF + PostgreSQL + zeep"
# /speckit.tasks
# /speckit.analyze

# === PHASE 5: Implementation (Agent Teams with Tmux panes) ===
# In Claude Code:
# "Create invoice-team with architect, coder, reviewer.
#  Use delegate mode. Tmux split-pane display.
#  File ownership: architect=models, coder=arca clients, reviewer=tests."

# === VERIFICATION ===
cd backend
python manage.py check
pytest tests/facturacion/ -v
pytest -m "security" -v
```

---

*Generated by Claude Opus 4.6 | 2026-02-10 (WSL2+Tmux revision)*
*Based on Spec-Kit, E2B docs, and Agent Teams documentation*
