---
name: skill-creator
description: >
  Creates new AI agent skills following the Gravitea Agent Skills spec.
  Trigger: When user asks to create a new skill, add agent instructions, or document patterns for AI.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

# Skill Creator

This skill guides the creation of new AI agent skills for GRAVITEA-ERP.

## When to Create a Skill

Create a skill when:
- A pattern is used repeatedly and AI needs guidance
- Project-specific conventions differ from generic best practices
- Complex workflows need step-by-step instructions
- Decision trees help AI choose the right approach
- Security-critical patterns need enforcement

**Don't create a skill when:**
- Documentation already exists (create a reference instead)
- Pattern is trivial or self-explanatory
- It's a one-off task

---

## Skill Structure

```
skills/{skill-name}/
├── SKILL.md              # Required - main skill file
├── assets/               # Optional - templates, schemas, examples
│   ├── template.py
│   └── schema.json
└── references/           # Optional - links to local docs
    └── docs.md           # Points to Docs/Project Blueprint/*.md
```

---

## SKILL.md Template

```markdown
---
name: {skill-name}
description: >
  {One-line description of what this skill does}.
  Trigger: {When the AI should load this skill}.
license: MIT
metadata:
  author: gravitea-team
  version: "1.0"
---

## When to Use

{Bullet points of when to use this skill}

## Critical Patterns

{The most important rules - what AI MUST know}

## Code Examples

{Minimal, focused examples}

## Decision Tree

```text
Question?
|-- Option A? -> Action A
|-- Option B? -> Action B
+-- Default -> Action C
```

## Commands

```bash
{Common commands}
```

## Resources

- **Templates**: See [assets/](assets/) for {description}
- **Documentation**: See [references/](references/) for local docs
```

---

## Naming Conventions

| Type | Pattern | Examples |
|------|---------|----------|
| Core component | `gravitea-{component}` | `gravitea-auth`, `gravitea-tenant`, `gravitea-sync` |
| Infrastructure | `gravitea-{infra}` | `gravitea-observability`, `gravitea-encryption` |
| Testing | `gravitea-testing` | Testing patterns and fixtures |
| Framework | `{technology}-expert` | `django-expert` |
| Workflow | `{action}-{target}` | `skill-creator` |

---

## Decision: assets/ vs references/

```
Need code templates?        → assets/
Need JSON schemas?          → assets/
Need example configs?       → assets/
Link to existing docs?      → references/
Link to Project Blueprint?  → references/ (with local path)
```

**Key Rule**: `references/` should point to LOCAL files (`Docs/Project Blueprint/*.md`), not web URLs.

---

## Decision: Gravitea-Specific vs Generic

```
Patterns apply to ANY Django project?  → Generic skill (e.g., django-expert)
Patterns are Gravitea-specific?        → gravitea-{name} skill
Generic skill needs Gravitea context?  → Add references/ pointing to Gravitea docs
```

---

## Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Skill identifier (lowercase, hyphens) |
| `description` | Yes | What + Trigger in one block |
| `license` | Yes | Always `MIT` for Gravitea |
| `metadata.author` | Yes | `gravitea-team` |
| `metadata.version` | Yes | Semantic version as string |

---

## Content Guidelines

### DO
- Start with the most critical patterns
- Use tables for decision trees
- Keep code examples minimal and focused
- Include Commands section with copy-paste commands
- Add Developer Checklist for validation
- Include security considerations where relevant

### DON'T
- Add Keywords section (agent searches frontmatter, not body)
- Duplicate content from existing docs (reference instead)
- Include lengthy explanations (link to docs)
- Add troubleshooting sections (keep focused)
- Use web URLs in references (use local paths)

---

## Registering the Skill

After creating the skill, update `AGENTS.md`:

1. Add to **Available Skills** table:
```markdown
| `{skill-name}` | {Description} | {Trigger} |
```

2. Add to **Auto-Invoke Rules** if applicable:
```markdown
| `{file-pattern}` | {Action} | `{skill-name}` | {Why} |
```

3. Update **Directory Structure** if new folder created

---

## Gravitea-Specific Patterns

When creating skills for GRAVITEA-ERP, ensure they cover:

### Security (Defense in Depth)
```
Layer 1: Application (Managers, Middleware)
Layer 2: Database (PostgreSQL RLS)
Layer 3: Validation (IDOR checks, claim validation)
```

### Multi-Tenancy
- Always use `TenantBoundModel` for tenant data
- Validate ForeignKeys for same-tenant
- Never leak tenant info in errors

### Testing
- Include test patterns with appropriate markers
- Add security test examples
- Reference `gravitea-testing` skill

---

## Checklist Before Creating

- [ ] Skill doesn't already exist (check `skills/`)
- [ ] Pattern is reusable (not one-off)
- [ ] Name follows conventions
- [ ] Frontmatter is complete (description includes trigger keywords)
- [ ] Critical patterns are clear
- [ ] Code examples are minimal
- [ ] Commands section exists
- [ ] Security considerations included (if applicable)
- [ ] Added to AGENTS.md Available Skills table
- [ ] Added to AGENTS.md Auto-Invoke Rules (if applicable)

---

## Resources

- **Template**: See [assets/skill-template.md](assets/skill-template.md) for SKILL.md template
- **Existing Skills**: See `skills/` directory for examples
- **AGENTS.md**: See root `AGENTS.md` for registration

---

*Last updated: 2026-01-20*
*Standard: Gravitea Agent Skills v1.0*
