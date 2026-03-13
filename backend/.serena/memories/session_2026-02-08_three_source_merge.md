# Session 2026-02-08: Three-Source Merge & Claude-Flow Integration

## What Was Done

### 1. Reinstalled Vercel Marketplace Skill
- Downloaded `vercel-react-best-practices` from `vercel-labs/agent-skills` GitHub repo
- Placed in `.agents/skills/vercel-react-best-practices/` (63 files: 4 root + 59 rules)
- Propagated via `setup.sh --all`

### 2. Three-Source Merge Implementation
- Upgraded `skills/setup.sh` from two-source to three-source merge
- New source: `.frameworks/skills/` for framework skills (Claude-Flow, etc.)
- Priority cascade: Custom > Marketplace > Framework
- Added Phase 3 to `copy_skills_to_target()` for framework skill copying
- Updated help text, source counting, conflict messages, AGENTS.md exclusions
- Added `.frameworks/skills/*` to `copy_agents_md()` exclusion list

### 3. Test Suite Expansion
- Upgraded `skills/setup_test.sh` from 25 to 33 tests
- Added framework mock to `setup_test_env()` (swarm-orchestration skill)
- 8 new `test_threesource_*` tests covering:
  - Framework skills present in output
  - All three sources merged together
  - Custom wins over framework (priority)
  - Marketplace wins over framework (priority)
  - Framework conflict warning displayed
  - No framework dir backward compatibility
  - Stale framework skills cleaned on removal
  - Framework counts displayed in output

### 4. Claude-Flow Skills Deployed
- Copied 37 Claude-Flow skills from cloned repo into `.frameworks/skills/`
- Total: 11 custom + 1 marketplace + 37 framework = 49 skills
- All detected by Claude Code immediately

### 5. Claude-Flow MCP Server Registered
- `claude mcp add claude-flow -- npx claude-flow@v3alpha mcp start`
- Added to project-level config (`.claude.json`)
- Requires Claude Code restart to activate

## Key Decisions
- `.frameworks/skills/` chosen over mixing into `.agents/skills/` (separation of concerns)
- Skills-only integration (agents/commands managed separately, different levels)
- Don't run `claude-flow init` in GRAVITEA-ERP (preserves existing CLAUDE.md)
- SuperClaude agents at user-level (~/.claude/agents/), Claude-Flow agents at project-level

## Architecture After Session
```
Sources:
  skills/              → 11 custom skills    [HIGHEST priority]
  .agents/skills/      → 1 marketplace skill [MEDIUM priority]
  .frameworks/skills/  → 37 framework skills [LOWEST priority]

Output:
  .claude/skills/  → 49 skills (merged)
  .codex/skills/   → 49 skills (merged)
  .gemini/skills/  → 49 skills (merged)
```

## Files Modified
- `skills/setup.sh` - Three-source merge logic
- `skills/setup_test.sh` - 8 new tests (33 total)

## Coexistence: SuperClaude + Claude-Flow
- Skills: Managed by setup.sh three-source merge (no conflict)
- Agents: SuperClaude=user-level, Claude-Flow=project-level (no conflict)
- Commands: SuperClaude=`sc/` namespace, Claude-Flow=own subdirs (no conflict)
- MCP: Both add entries additively to settings.json (no conflict)
- CLAUDE.md: Owned by setup.sh/AGENTS.md (don't run claude-flow init)
