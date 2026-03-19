# Quickstart: Writing spec-08 Blueprint Documents

**Branch**: `008-acopio-new-docs` | **Date**: 2026-03-18

## Prerequisites

1. All upstream blueprints are finalized (specs 01-07)
2. ARCA docs ingested into Qdrant (`arca_api_specs`, `arca_dev_guides`, `arca_setup_certs`)
3. Docker Desktop running (for Qdrant queries)

## Writing Order

1. **08a** — ARCA Grain Integration Guide
2. **08c** — Software Requirements Specification (SRS)
3. **08b** — AI/ML Feature Roadmap

## Context Files

| File | Purpose |
|------|---------|
| `Docs/PROMPTS/spec-08-new-docs/08-specify.md` | Feature context: domain facts, FRs, ACs, target structures |
| `Docs/PROMPTS/spec-08-new-docs/08-plan.md` | Writing plan: section-by-section detail, research mapping, gates |
| `specs/008-acopio-new-docs/spec.md` | Feature specification: user stories, requirements, success criteria |
| `specs/008-acopio-new-docs/plan.md` | Implementation plan: technical context, checkpoint gates, done criteria |
| `specs/008-acopio-new-docs/research.md` | Research decisions: WSCPE method names, phase model, language |

## RAG Query Pattern

```bash
# Always use .venv/bin/python, never system python
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'your query here' -l 5

# Example queries for each document:
# 08a: WSAA auth
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA authentication TRA LoginCMS Token Sign' -l 5

# 08a: WSLPG fields
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSLPG liquidacionAutorizar XML fields codGrano' -l 5

# 08c: Romaneo workflow
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'romaneo workflow truck arrival weighing quality grading' -l 5

# 08b: ML models
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'AI ML grain storage predictive merma model' -l 5
```

## Gate Checks

Run after completing each document:

```bash
FILE="Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Gate 1 (08a)
grep -c "WSAA\|WSLPG\|WSCPE\|WSFEv1" "$FILE"           # ≥ 40
grep -c '```mermaid' "$FILE"                              # ≥ 3
grep -c "fwshomo.afip" "$FILE"                            # ≥ 1
grep -c "ADR-019\|ADR-025\|ADR-026\|ADR-027\|ADR-028\|ADR-029\|ADR-030" "$FILE"  # ≥ 7
grep -ci "TBD\|TODO\|placeholder" "$FILE"                 # = 0

FILE="Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Gate 2 (08c)
grep -c "SRS-RE\|SRS-CA\|SRS-AL\|SRS-CC" "$FILE"        # ≥ 20
grep -ci "shall" "$FILE"                                  # ≥ 30
grep -c "baud\|parity\|Modbus\|RS-232" "$FILE"           # ≥ 5
grep -ci "TBD\|TODO\|placeholder" "$FILE"                 # = 0

FILE="Docs/Project Blueprint/AI-ML Feature Roadmap.md"
# Gate 3 (08b)
grep -c "merma.*model\|price.*optim\|anomaly detection\|NLQ\|natural language" "$FILE"  # ≥ 4
grep -c "Layer 1\|Layer 2\|Layer 3\|Layer 4" "$FILE"     # ≥ 8
grep -c "ADR-033\|ADR-034\|ADR-035" "$FILE"              # ≥ 3
grep -ci "TBD\|TODO\|placeholder" "$FILE"                 # = 0
```

## Key Constraints

- No Python/SQL/shell code blocks in any document
- Mermaid diagrams and XML schema summaries are allowed
- ADR citations: always "ADR-NNN (Title)" format
- Spanish domain terms retained: romaneo, merma, liquidacion, CPE, CTG, campana, etc.
- 08b MUST use Roadmap's 3-phase model (Phase 3 = Intelligence & Scale, not Phase 4)
- 08c overwrites stale retail SRS — preserve nothing from existing file
