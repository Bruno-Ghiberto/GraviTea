# Speckit Context Prompts — Acopio ERP Pivot

## DOMAIN KNOWLEDGE PROTOCOL (read this FIRST)

All domain knowledge for this project lives in 30 research
documents ingested into the Qdrant RAG pipeline.

**RULE: NEVER read full research PDFs or Markdown files directly.**
Use the RAG pipeline to query specific information:

```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "your query" -l 5
```

This saves thousands of tokens per session. Full file reads
are a LAST RESORT when RAG results are insufficient.

For programmatic/agent consumption, add `--json`:
```bash
.venv/bin/python scripts/qdrant/qdrant_search.py -q "your query" -l 5 --json
```

## System Overview

This folder contains **context prompt files** that feed into
speckit commands. Each spec is a self-contained unit of work
with rich domain context drawn from the research corpus.

The workflow file `workflow-GRA.txt` is the AUTHORITATIVE
execution reference. This README is the INDEX and REFERENCE.

## How It Works

Each spec goes through a CREATE -> REFINE -> GENERATE cycle:

```
For each context file (specify, plan, implement):

  /sc:design   ->  CREATE the context file (XX-specify.md, etc.)
  /sc:improve  ->  REFINE for coherence with specs + blueprints
  /speckit.*   ->  GENERATE the artifact (spec.md, plan.md, tasks.md)
```

Full pipeline per spec (11 steps):

```
Phase 0: /sc:load engram and serena
Phase A: /sc:design   -> XX-specify.md     (create)
         /sc:improve  -> XX-specify.md     (refine)
         /speckit.specify                  (generate spec.md)
         /speckit.clarify                  (resolve ambiguities)
Phase B: /sc:design   -> XX-plan.md        (create)
         /sc:improve  -> XX-plan.md        (refine)
         /speckit.plan                     (generate plan.md)
         /speckit.tasks                    (generate tasks.md)
Phase C: /speckit.analyze                  (quality gate)
Phase D: /sc:design   -> XX-implement.md   (create + agents/*.md)
Phase E: /speckit.implement               (execute)
```

See `workflow-GRA.txt` for the complete command templates.

### Artifacts Output

Speckit artifacts are generated in the project root:

```
specs/
  001-vision/          spec.md, plan.md, tasks.md
  002-prd/             spec.md, plan.md, tasks.md
  003-data-model/      spec.md, plan.md, tasks.md
  ...
```

Deliverables (actual documents/code) go to their final locations:
- Blueprint docs -> `Docs/Project Blueprint/`
- Django models  -> `backend/apps/acopio/`
- Rust modules   -> `rust/gravitea-core/src/`

### Context File Structure

| File | Created by | Fed to | Purpose |
|------|-----------|--------|---------|
| `XX-specify.md` | `/sc:design` | `/speckit.specify` | WHAT: requirements, research inputs, acceptance criteria |
| `XX-plan.md` | `/sc:design` | `/speckit.plan` | HOW: execution order, files, patterns, checkpoints |
| `XX-implement.md` | `/sc:design` | `/speckit.implement` | EXECUTE: code, testing protocol, done criteria |
| `agents/AX-name.md` | `/sc:design` | Agent Teams | Per-agent instruction files (impl specs 09+ only) |

### Research Inputs Template

Every context file MUST include this section:

```markdown
## Research Inputs

### RAG Queries (run these FIRST — do NOT read full files)
- "query 1 for qdrant"
- "query 2 for qdrant"

### Source Documents (for reference only — prefer RAG)
- `Docs/Researches/Markdown/X.X Document Name.md`
  Relevant sections: [specific section names]

### Critical Domain Facts (minimum context)
- Fact 1
- Fact 2
```

## Spec Catalog

### Wave 1: Strategic Foundation

| Spec | Name | Type | Deliverable | Research |
|------|------|------|-------------|---------|
| 01 | Product Vision & Scope | Blueprint | `Docs/Project Blueprint/Product Vision & Scope.md` | 4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 9.1 |
| 02 | PRD | Blueprint | `Docs/Project Blueprint/PRD.md` | 2.1-2.6, 8.1-8.4, 1.1-1.6, 3.1-3.2 |

### Wave 2: Technical Core

| Spec | Name | Type | Deliverable | Research |
|------|------|------|-------------|---------|
| 03 | Data Model & Domain Model | Blueprint | `Docs/Project Blueprint/Data Model & Domain Model.md` | 8.x, 2.x, 7.x, 1.1-1.3, 9.1 |
| 04 | Architecture Decision Records | Blueprint | `Docs/Project Blueprint/Architecture Decision Records (ADR).md` | 9.1, brainstorm decisions |

### Wave 3: Architecture & Design

| Spec | Name | Type | Deliverable | Research |
|------|------|------|-------------|---------|
| 05 | High-Level Design | Blueprint | `Docs/Project Blueprint/High-Level Design (HLD).md` | 5.1, 5.2, 9.1, 10.1, 3.1 |
| 06 | REST API Design | Blueprint | `Docs/Project Blueprint/REST API Design.md` | 8.3, 8.4, 5.1, 2.1 |

### Wave 4: Planning & Reference

| Spec | Name | Type | Deliverable | Research |
|------|------|------|-------------|---------|
| 07 | Roadmap | Blueprint | `Docs/Project Blueprint/Roadmap.md` | All (synthesis) |
| 08a | ARCA Grain Integration Guide | Blueprint (NEW) | `Docs/Project Blueprint/ARCA Grain Integration Guide.md` | 1.x, 5.x, 10.1 |
| 08b | AI/ML Feature Roadmap | Blueprint (NEW) | `Docs/Project Blueprint/AI-ML Feature Roadmap.md` | 9.1 |
| 08c | SRS | Blueprint | `Docs/Project Blueprint/Software Requirements Specification (SRS).md` | Derived from spec-02 |

### Wave 5: ARCA Knowledge Update

| Spec | Name | Type | Deliverable | Research |
|------|------|------|-------------|---------|
| 09 | New ARCA Docs — Blueprint Knowledge Update | Blueprint Update | In-place enrichment of 9 existing `Docs/Project Blueprint/` docs | arca_api_specs, arca_dev_guides, arca_setup_certs |

### Wave 6: MVP Implementation

| Spec | Name | Type | Deliverable | Research | Agents |
|------|------|------|-------------|---------|--------|
| 10 | Grain Reference Data | Impl | `backend/apps/acopio/` models + fixtures | 8.1, 2.2, 2.5, 2.6 | A1-A4 |
| 11 | Romaneo Core | Impl | `backend/apps/acopio/` + `rust/gravitea-core/src/merma.rs` | 2.1, 2.2, 2.5, 8.3 | A1-A6 |
| 12 | Storage & Position | Impl | `backend/apps/acopio/` storage models | 2.1, 9.1 | A1-A3 |
| 13 | Producer Accounts | Impl | `backend/apps/cuentas/` | 2.3, 2.4 | A1-A4 |

### Wave 7: Phase 2 (future)

| Spec | Name | Type | Research |
|------|------|------|---------|
| 14 | Agronomia Adaptation | Impl | existing codebase |
| 15 | WSLPG Integration | Impl | 5.1, 1.3, 8.4 |
| 16 | Reports | Impl | 7.1, 7.2 |
| 17 | Canje | Impl | 2.4 |

## Dependency Graph

```
spec-01 (Vision)
  |
  v
spec-02 (PRD) --------+-----------+
  |                    |           |
  v                    v           v
spec-03 (Data Model)  spec-07   spec-08a/b/c
  |         |         (Roadmap)  (New Docs)
  |         |                       ^
  v         v                       |
spec-04    spec-05 (HLD) ----------+
(ADR)       |
  ^         v
  |    spec-06 (API)
  |         ^
  +---------+
  |
  +---> spec-09 (New ARCA Docs — Blueprint Update) [Wave 5]
              |
              v
  +---> spec-10 (Grain Ref) ----> spec-11 (Romaneo)
  |           |                       |
  |           v                       v
  |      spec-12 (Storage)      spec-13 (Accounts)
  |
  +---> spec-14 (Agronomia)  [Wave 7]
  +---> spec-15 (WSLPG)      [Wave 7]
```

Key dependency rules:
- spec-03 depends on spec-01 AND spec-02
- spec-04 depends on spec-02 AND spec-03
- spec-05 depends on spec-03 AND spec-04
- spec-06 depends on spec-03 AND spec-05
- spec-09 depends on ALL of spec-01 through spec-08 (enrichment pass)
- ALL impl specs (10+) depend on spec-09 (ARCA enrichment must be complete first)
- ALL impl specs (10+) depend on spec-03

## Research Document Index

30 Markdown files ingested into Qdrant (auto-routed by query).
1 additional PDF-only doc (5.2) not in RAG — read manually if needed.

All paths relative to project root.

### Regulatory (1.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 1.1 | `Docs/Researches/Markdown/1.1 Carta de Porte Electronica (CTG) -- Complete Lifecycle.md` | CPE lifecycle, CTG codes, confirmation flow |
| 1.2 | `Docs/Researches/Markdown/1.2 AFIP Web Service WSCPE -- Technical Specification.md` | WSCPE SOAP endpoints, XML schemas |
| 1.3 | `Docs/Researches/Markdown/1.3 Liquidacion Primaria de Granos -- Form 1116 B and C.md` | Form 1116 B/C field structure |
| 1.4 | `Docs/Researches/Markdown/1.4 Registro de Operadores de Granos and Withholding Tax Regime.md` | SISA, withholding tiers |
| 1.5 | `Docs/Researches/Markdown/1.5 Provincial Tax Obligations for Grain Operations.md` | IIBB rates by province |
| 1.6 | `Docs/Researches/Markdown/1.6 Ley de Granos, Warrants, and Storage Legal Framework.md` | Legal framework, storage obligations |

### Operations (2.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 2.1 | `Docs/Researches/Markdown/2.1 Day-to-Day Operations of an Acopiador.md` | Full romaneo workflow, 10 steps |
| 2.2 | `Docs/Researches/Markdown/2.2 Grain Quality Management Standards.md` | Quality params per grain, grades |
| 2.3 | `Docs/Researches/Markdown/2.3 Producer Current Accounts (Cuentas Corrientes de Productores).md` | Cuenta corriente structure, balances |
| 2.4 | `Docs/Researches/Markdown/2.4 Grain Pricing, Contracts, and Market Mechanisms.md` | Pricing, forward contracts, canje |
| 2.5 | `Docs/Researches/Markdown/2.5 Merma (Grain Loss) Calculations and Tolerance Tables.md` | Sequential merma formulas |
| 2.6 | `Docs/Researches/Markdown/2.6 Campaign Year Management.md` | Campaign lifecycle, segregation |

### Hardware (3.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 3.1 | `Docs/Researches/Markdown/3.1 Weighbridge Integration Standards.md` | Scale protocols, calibration |
| 3.2 | `Docs/Researches/Markdown/3.2 Grain Moisture Meters and Lab Equipment.md` | Lab equipment APIs |

### Market (4.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 4.1 | `Docs/Researches/Markdown/4.1 Comprehensive Acopio Software Market Map.md` | All competitors |
| 4.2 | `Docs/Researches/Markdown/4.2 AGIS-AmericaGIS Deep Competitive Analysis.md` | Main competitor |
| 4.3 | `Docs/Researches/Markdown/4.3 Acopiador Pain Points and Technology Adoption.md` | User needs |

### Technical API (5.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 5.1 | `Docs/Researches/Markdown/5.1 WSLPG -- Technical API Documentation.md` | SOAP endpoints, XML fields |
| 5.2 | `Docs/Researches/PDF/5.2 ARCA Grain Services Integration Architecture.pdf` | Service map (**PDF only — not in RAG**) |

### Market/GTM (6.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 6.1 | `Docs/Researches/Markdown/6.1 Market Sizing -- Geographic Distribution of Acopiadores.md` | Geographic distribution |
| 6.2 | `Docs/Researches/Markdown/6.2 Accountant (Contador Rural) Channel Strategy.md` | Contador rural GTM |
| 6.3 | `Docs/Researches/Markdown/6.3 Trade Associations and Industry Events.md` | Expoagro, etc. |

### Accounting (7.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 7.1 | `Docs/Researches/Markdown/7.1 Chart of Accounts for Acopio Operations.md` | COA structure |
| 7.2 | `Docs/Researches/Markdown/7.2 Grain Inventory Valuation Methods.md` | FIFO, WAC, market |
| 7.3 | `Docs/Researches/Markdown/7.3 Withholding Tax Calculations for Grain Operations.md` | IVA, Ganancias, IIBB |

### Data Model (8.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 8.1 | `Docs/Researches/Markdown/8.1 Grain Types and Quality Parameter Reference Data.md` | Grain codes, params |
| 8.2 | `Docs/Researches/Markdown/8.2 CTG Document Structure and State Machine.md` | CTG states, fields |
| 8.3 | `Docs/Researches/Markdown/8.3 Romaneo (Weighing Ticket) and Reception Document Structure.md` | Complete field spec |
| 8.4 | `Docs/Researches/Markdown/8.4 Form 1116 B-C Field Structure for Data Model Design.md` | WSLPG XML fields |

### AI/ML (9.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 9.1 | `Docs/Researches/Markdown/9.1 AI-ML Applications for Grain Storage Operations.md` | Full AI roadmap |

### Open Source (10.x)

| ID | Full Path | Key Content |
|----|-----------|-------------|
| 10.1 | `Docs/Researches/Markdown/10.1 Existing Open-Source ARCA Grain Integration Code.md` | Reference implementations |

## RAG Quick Reference

```bash
# Auto-routed search (default — usually correct):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "your query" -l 5

# Search specific collection:
.venv/bin/python scripts/qdrant/qdrant_search.py -q "query" -c acopio_research -l 5

# Search all collections:
.venv/bin/python scripts/qdrant/qdrant_search.py -q "query" --all -l 3

# Literal search (no query expansion):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "Form 1116-C" --no-expand -l 5

# JSON output (for agents/programmatic use):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "query" -l 5 --json

# Save output to file (for batch/background use):
.venv/bin/python scripts/qdrant/qdrant_search.py -q "query" -l 5 -o Docs/RAG_results/filename.txt
```

### Batch Search (run all queries for a spec at once)

Create a queries file (one query per line, # for comments) and run:

```bash
# Run batch — saves each result to Docs/RAG_results/NN_query.txt:
.venv/bin/python scripts/qdrant/qdrant_batch_search.py -f queries.txt -l 5

# Or pass queries directly:
.venv/bin/python scripts/qdrant/qdrant_batch_search.py \
    -q "query one" -q "query two" -q "query three" \
    -c acopio_research -l 5

# Custom output directory:
.venv/bin/python scripts/qdrant/qdrant_batch_search.py -f queries.txt -o Docs/RAG_results -l 5

# JSON format:
.venv/bin/python scripts/qdrant/qdrant_batch_search.py -f queries.txt --json
```

Output: numbered files like `01_query_name.txt` + `_index.txt` summary.
Claude Code should run this as a background task, then read result files as needed.

### Suggested Queries by Spec

```bash
# spec-01 (Vision):
-q "acopio software market competitors AGIS"
-q "acopiador pain points technology adoption"
-q "market sizing geographic distribution acopiadores"

# spec-02 (PRD):
-q "romaneo workflow steps truck arrival"
-q "grain quality parameters humidity moisture"
-q "producer current account balance structure"

# spec-03 (Data Model):
-q "romaneo data fields ERP capture"
-q "merma calculation formula sequential"
-q "grain types quality parameters reference"
-q "Form 1116-C XML field types lengths"
-q "producer cuenta corriente grain balance"

# spec-04 (ADR):
-q "AI ready data architecture grain ERP"
-q "dual inventory grain discrete SKU"

# spec-05 (HLD):
-q "WSLPG SOAP endpoint authentication"
-q "ARCA grain services architecture"
-q "AI ML grain storage applications"

# spec-06 (API Design):
-q "romaneo API endpoint structure"
-q "grain liquidation API fields"

# spec-09 (New ARCA Docs — Blueprint Update):
-q "WSAA TRA loginTicketRequest XML schema component structure"
-q "WSAA certificate generation CSR distinguished name fields production"
-q "WSCPE confirmarDescargaCPE método SOAP parámetros XML"
-q "CPE estado carátula pendiente autorizado rechazado máquina estados"
-q "WSCPE error código retorno rechazo descripción tabla"
-q "WSLPG autorizarLiquidacionPrimaria método parámetros XML campo"
-q "WSLPG Form 1116 B C campo longitud tipo XML schema"
-q "WSLPG retención IVA ganancias SISA porcentaje cálculo"
-q "SIRE retención IVA ganancias cálculo tasa porcentaje tabla"
-q "SIRE emitir retención SOAP método parámetros comprobante"
-q "SIRE importación lote batch archivo formato estructura"
-q "WSCDC constancia depósito cereal método SOAP nombre parámetro"
-q "WSCDC informar depósito acopio cereal campo XML schema"
-q "WS padrón A4 getPersona CUIT método respuesta campo"
-q "SISA operadores granos inscripción padrón consulta online"
-q "acopiadores obligaciones fiscales ARCA RG resolución granos"
-q "TLS cronograma versión mínima ARCA transición protocolo"

# spec-10 (Grain Reference):
-q "grain types codes ARCA humidity base"
-q "tolerance tables bonification rebaja"
-q "campaign year management agricultural"

# spec-11 (Romaneo Core):
-q "romaneo peso bruto tara neto conforme"
-q "merma zarandeo secado manipuleo volatil"
-q "quality grading grade 1 2 3 fuera estandar"

# spec-13 (Accounts):
-q "producer current account movements"
-q "canje grain barter supplies"
-q "grain pricing contracts market mechanisms"
```

## Conventions

### Blueprint vs Implementation Specs

| Aspect | Blueprint (01-08) | Blueprint Update (09) | Implementation (10+) |
|--------|-------------------|-----------------------|---------------------|
| Deliverable | New `.md` doc | In-place enrichment of existing `.md` docs | Django models, Rust code, tests |
| Agent Teams | No — single author | No — single author | Yes — tmux multi-pane |
| `agents/` folder | Not needed | Not needed | Required |
| Testing | Document review | Acceptance gate checks | `scripts/run-tests-external.sh` |

### Cross-Reference Chain

```
Research Docs -> Blueprint Specs -> Implementation Specs -> Agent Files
  (domain)       (requirements)       (technical)          (execution)
```

Blueprint specs reference research docs as INPUT.
Implementation specs reference blueprint specs as REQUIREMENTS.
Agent files reference implementation specs as AUTHORITY.

### Re-execution Rule

If a spec's dependency changes materially (e.g., spec-02 PRD
is rewritten), downstream specs that depend on it should be
re-evaluated. At minimum, re-run `/sc:improve` on their
context files to check coherence with the updated upstream spec.
