# Session: Multi-Agent Orchestration Architecture Design (2026-02-10)

## What Was Done
- Designed comprehensive multi-agent orchestration architecture for building the facturacion (invoice) backend module
- Researched 5 technologies via deep source code analysis and web research:
  1. Claude-Flow v3 (source code at C:\Users\Ghibe\Documents\Utilities Repos\claude-flow)
  2. Agent Teams (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)
  3. E2B Sandboxes (e2b.dev)
  4. Spec-Kit (source code at C:\Users\Ghibe\Documents\Utilities Repos\spec-kit)
  5. Qdrant RAG (existing infrastructure)

## Key Findings
- Claude-Flow v3: MCP server is production-ready; agent spawning/swarm features are ASPIRATIONAL (single-process only)
- Agent Teams: Real parallel sessions, filesystem-based coordination, works on Windows in in-process mode only (no Tmux split panes)
- E2B: Real Firecracker microVMs, good for sandboxed testing, overkill for local dev
- Spec-Kit: Fully installed (7 features, constitution exists), ready for 008-facturacion-backend
- Qdrant RAG: 3 collections with 2,304 chunks from 20 ARCA PDFs, qwen3-embedding:4b configured

## Architecture Decision
- Primary orchestration: Agent Teams (3 agents + lead in delegate mode)
- Knowledge layer: Qdrant RAG (all agents query ARCA docs)
- Memory layer: Claude-Flow MCP (persistent cross-session memory)
- Methodology: Spec-Kit pipeline (specify → clarify → plan → tasks → implement)
- Dropped: Tmux (Windows), E2B per-agent (overkill), Claude-Flow swarm (aspirational)

## Output
- Architecture document: claudedocs/008-multi-agent-orchestration-architecture.md
- Covers: honest assessment, pragmatic architecture, discovery phase design, Spec-Kit integration, implementation roadmap, cost analysis, risk matrix

## Next Steps
1. Run Qdrant re-ingestion pipeline for qwen3-embedding:4b (recreate → ingest → benchmark)
2. Set up Agent Teams environment
3. Execute ARCA Discovery Phase (3 agents querying RAG)
4. Run /speckit.specify for 008-facturacion-backend
5. Full Spec-Kit pipeline → Agent Teams implementation

## Facturacion Module Status
- App does NOT exist yet (greenfield)
- gravitea-invoice SKILL.md has 1,138 lines of patterns ready
- Target structure: apps/facturacion/ with arca/ subdirectory
- Models needed: Comprobante, ARCACredential, PuntoDeVenta
- Dependencies needed: zeep (SOAP), lxml, cryptography

## Technology Reference

### Agent Teams Setup
- Environment variable: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Windows: in-process mode only (no Tmux)
- Coordination: filesystem-based (shared project files)
- Recommended: 3 specialized agents + 1 lead agent

### Qdrant Collections (Current State)
- `arca_api_specs`: 1,151 chunks (5 files) - error codes, WSDL, validation rules
- `arca_dev_guides`: 1,088 chunks (7 files) - developer manuals, code examples
- `arca_setup_certs`: 65 chunks (8 files) - certificate setup, environment procedures
- Total: 2,304 points from 20 PDFs
- Embedding: qwen3-embedding:4b (2560 dims) - configured but collections need re-ingestion
- Baseline: nomic-embed-text (768 dims, 0.770 avg) - proven reliable fallback

### Spec-Kit Pipeline
- 7 features: specify, clarify, plan, tasks, implement, review, iterate
- Constitution file exists and is ready
- Target: 008-facturacion-backend specification

### Claude-Flow MCP
- Used for: persistent cross-session memory, pattern storage
- 12 GRAVITEA patterns already stored
- MCP server configured in .claude/settings.json
