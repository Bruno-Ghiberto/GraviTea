# Research: 015 Blueprint Documentation Overhaul

**Date**: 2026-02-21 | **Branch**: `015-blueprint-docs-overhaul`

## Research Summary

This is a documentation feature with no code changes. Technical unknowns are minimal — the codebase is the source of truth and the RESEARCHER agent will extract all facts at execution time.

## Resolved Decisions

### R-001: Metric Verification Method
- **Decision**: Use `scripts/run-tests-external.sh` and read persisted `.summary` files
- **Rationale**: Authoritative, automated, token-efficient. Eliminates stale-data risk.
- **Alternatives considered**: Manual metric snapshots (rejected — adds manual step), reading raw pytest output (rejected — token-expensive)

### R-002: Diagram Format
- **Decision**: Mermaid for all diagrams
- **Rationale**: Renderable in GitHub and Notion (the two platforms where docs are consumed). Maintainable by AI agents without external tools.
- **Alternatives considered**: ASCII art (rejected — not renderable in Notion), preserve existing format per-doc (rejected — inconsistency across docs)

### R-003: ADR Topic Selection
- **Decision**: 14-entry seed list compiled from MEMORY.md, Serena memories, and codebase analysis
- **Rationale**: Eliminates guesswork for implementing agent. Covers all major architectural decisions through Feature 014.
- **Alternatives considered**: Let implementing agent discover (rejected — risk of missing critical decisions or padding with marginal entries)

### R-004: Onboarding Environment Path
- **Decision**: Docker Compose only
- **Rationale**: Docker Compose is the canonical developer workflow. The WSL venv is an AI agent workaround, not a standard development path.
- **Alternatives considered**: Both paths documented (rejected — adds confusion for new developers), WSL venv primary (rejected — it's a workaround)

### R-005: GCP Production Documentation Depth
- **Decision**: Known service mappings + known gaps from spec 011 analysis. Undecided items marked "TBD".
- **Rationale**: User has not yet studied GCP migration in depth. Document what's known, don't speculate.
- **Alternatives considered**: Comprehensive speculative design (rejected — premature, user hasn't studied it), high-level overview only (rejected — spec 011 already produced concrete analysis worth capturing)

## No Remaining Unknowns

All NEEDS CLARIFICATION items were resolved during the `/speckit.clarify` phase. No Phase 0 research agents are needed.
