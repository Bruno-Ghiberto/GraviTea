# Quickstart: 015 Blueprint Documentation Overhaul

## Prerequisites

- Git branch: `015-blueprint-docs-overhaul`
- WSL venv available at `backend/venv-wsl/` (for RESEARCHER metrics run)
- Docker Compose services NOT required (RESEARCHER reads source files directly)

## Execution Sequence

### 1. Generate tasks

    /speckit.tasks

### 2. Spawn team and execute

    # Phase 1: RESEARCHER (blocks Phase 2)
    Spawn RESEARCHER (general-purpose, worktree)
    → Output: claudedocs/015-codebase-facts.md

    # Phase 2: WRITERs (parallel, after Phase 1)
    Spawn WRITER-A (technical-writer, worktree) — 6 technical docs
    Spawn WRITER-B (technical-writer, worktree) — 6 strategic docs
    → Output: 12 updated/created docs in Docs/Project Blueprint/

    # Phase 3: LEAD validates cross-references
    → Output: validation report

### 3. Commit

    git add Docs/Project Blueprint/ claudedocs/015-codebase-facts.md
    git commit

## Key Files

| File | Purpose |
|------|---------|
| `specs/015-blueprint-docs-overhaul/spec.md` | Feature specification (what to build) |
| `specs/015-blueprint-docs-overhaul/plan.md` | Implementation plan (how to build) |
| `Docs/Temp-prompting/015/instruction-plan.md` | Agent team design and detailed checklists |
| `claudedocs/015-codebase-facts.md` | RESEARCHER output (created during Phase 1) |
| `Docs/Project Blueprint/*.md` | Final deliverables (9 updated + 3 created) |
