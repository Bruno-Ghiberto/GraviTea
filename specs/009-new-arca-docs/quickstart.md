# Quickstart: ARCA Blueprint Enrichment Execution

**Branch**: `009-new-arca-docs` | **Date**: 2026-03-18
**Purpose**: Environment setup and session-by-session workflow for executing spec-09

---

## Prerequisites

### 1. Branch Checkout

```bash
git checkout 009-new-arca-docs
git status
# Should show branch 009-new-arca-docs, clean working tree
```

### 2. Verify Qdrant & Ollama

```bash
# Check Qdrant
curl -s http://localhost:6333/healthz
# Expected: {"title":"qdrant - vector search engine","version":"..."}

# Check Ollama
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print([m['name'] for m in d['models']])"
# Expected: list including the embedding model used by RAG

# Verify ARCA collections exist
.venv/bin/python scripts/qdrant/qdrant_search.py -q 'WSAA authentication' -l 2
# Expected: results from WSAA manuals (non-empty)
```

### 3. Re-ingest if Collections Missing

```bash
# Only if collections missing or empty
.venv/bin/python scripts/qdrant/ingest_arca_qdrant.py --collection all
# Takes 15-30 minutes; watch for "INGESTION COMPLETE" message
```

---

## Session A: ARCA Guide Enrichment

**Target**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
**Duration**: Full session

### Session A Workflow

```bash
# Step 1: Enter session with full context
# Read: specs/009-new-arca-docs/spec.md (SC targets)
# Read: specs/009-new-arca-docs/plan.md (Step 1 section)
# Read: Docs/Project Blueprint/ARCA Grain Integration Guide.md (current state)

# Step 2: Run all 6 Research Tasks from research.md
# Fill findings in specs/009-new-arca-docs/research.md BEFORE editing documents

# Step 3: Edit ARCA Guide
# - Renumber §6→§10, §7→§11, §8→§12, §9→§13
# - Enrich §3 (WSAA), §4 (WSLPG), §5 (WSCPE)
# - Insert new §6 (SIRE), §7 (WSCDC), §8 (WS Padrón), §9 (Error Catalog)
# - Update §2 Service Overview table

# Step 4: Run ARCA Guide checkpoint
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Expected: 0

grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"
# Not needed in this doc, but note SISA % values for use in Session B/C

# Step 5: Commit progress
git add "Docs/Project Blueprint/ARCA Grain Integration Guide.md" \
        specs/009-new-arca-docs/research.md
git commit -m "spec-09: enrich ARCA Guide with WSCDC, SIRE, WS Padrón sections"
```

### Session A Done Criteria

- [ ] ARCA Guide has ≥8 service rows in §2 table
- [ ] ARCA Guide §3 has production + homologación cert chain tables
- [ ] ARCA Guide §4 has Form 1116-B/C field tables and SISA tier table
- [ ] ARCA Guide §5 has CPE state machine table and XML field catalog
- [ ] ARCA Guide §6 (SIRE) is written with SOAP methods + batch format
- [ ] ARCA Guide §7 (WSCDC) is written with lifecycle + SOAP methods + XML fields + error codes
- [ ] ARCA Guide §8 (WS Padrón) is written with getPersona method + SISA workflow
- [ ] ARCA Guide §9 (Error Catalog) has error codes for ≥3 services
- [ ] Zero occurrences of `descargadoDestinoCPE` in ARCA Guide
- [ ] SISA % values recorded in research.md for cross-document consistency check

---

## Session B: SRS + HLD

**Targets**:
- `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
- `Docs/Project Blueprint/High-Level Design (HLD).md`

**Entry condition**: Session A ARCA Guide checkpoint PASSED; research.md SISA % values filled.

### Session B Workflow

```bash
# Step 1: Re-read spec.md SC targets and plan.md Steps 2-3
# Bring SISA % values from research.md findings

# Step 2: Edit SRS
# - Add WSCDC requirements block (WSCDC-REQ-01 through WSCDC-REQ-03)
# - Add WS Padrón requirements block (PADRON-REQ-01 through PADRON-REQ-03)
# - Add SISA retention tier table (exact values from Session A research)
# - Resolve all ARCA TBD/TODO markers

# Step 3: Run SRS checkpoint
grep -c "WSCDC" "Docs/Project Blueprint/Software Requirements Specification (SRS).md"
# Expected: ≥1

# Step 4: Edit HLD — fix 4 method names
grep -n "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Lines: 142, 264, 341, 539 — fix each individually with Edit tool

# Step 5: Edit HLD — add WSCDC to §6 integration architecture
# Step 6: Edit HLD — add TLS version to security section

# Step 7: Run HLD checkpoint
grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0

# Step 8: Commit
git add "Docs/Project Blueprint/Software Requirements Specification (SRS).md" \
        "Docs/Project Blueprint/High-Level Design (HLD).md"
git commit -m "spec-09: add WSCDC/WS Padrón reqs to SRS; fix HLD method names + add WSCDC"
```

### Session B Done Criteria

- [ ] SRS has WSCDC requirements block with ≥1 traceable requirement ID
- [ ] SRS has WS Padrón requirements block with ≥1 traceable requirement ID
- [ ] SRS has SISA retention tier table matching ARCA Guide §6.5 values exactly
- [ ] Zero TBD/TODO markers in SRS ARCA sections
- [ ] Zero occurrences of `descargadoDestinoCPE` in HLD (all 4 fixed)
- [ ] HLD §6 mentions WSCDC in integration architecture
- [ ] HLD security section documents TLS minimum version

---

## Session C: ADR + REST API + Data Model

**Targets**:
- `Docs/Project Blueprint/Architecture Decision Records (ADR).md`
- `Docs/Project Blueprint/REST API Design.md`
- `Docs/Project Blueprint/Data Model & Domain Model.md`

**Entry condition**: Sessions A+B checkpoints PASSED.

### Session C Workflow

```bash
# Step 1: Re-read spec.md SC-007, SC-009 targets

# Step 2: Edit ADR
# - Fix ADR-027 label (SC-009)
# - Enrich ADR-007, ADR-018, ADR-027
# - Add ADR-036 (WSCDC)
# - Add ADR-037 (WS Padrón)

# Step 3: ADR checkpoints
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 1 match (SC-009)

grep -c "descargadoDestinoCPE" "Docs/Project Blueprint/Architecture Decision Records (ADR).md"
# Expected: 0

# Step 4: Edit REST API Design — add 2 endpoints
# Step 5: Edit Data Model — add CertificadoDepositoCereal entity

# Step 6: Commit
git add "Docs/Project Blueprint/Architecture Decision Records (ADR).md" \
        "Docs/Project Blueprint/REST API Design.md" \
        "Docs/Project Blueprint/Data Model & Domain Model.md"
git commit -m "spec-09: ADR-036/037 for WSCDC/WS Padrón; 2 new API endpoints; CertificadoDepositoCereal entity"
```

### Session C Done Criteria

- [ ] ADR-027 label reads "SISA-Tier Retention Calculation at WSLPG Filing Time" (exact — SC-009)
- [ ] ADR-027 content includes exact SISA tier % (matching ARCA Guide §6.5 and SRS)
- [ ] ADR-007 enriched with cert chain CA names
- [ ] ADR-018 enriched with `confirmarDescargaCPE` confirmation
- [ ] ADR-036 written with WSCDC decision, context, consequences
- [ ] ADR-037 written with WS Padrón decision, context, consequences
- [ ] REST API Design has WSCDC POST endpoint documented
- [ ] REST API Design has SISA GET endpoint documented
- [ ] Data Model has CertificadoDepositoCereal with all required fields and `tenant_id`

---

## Session D: Optional Docs + Final Verification Sweep

**Targets** (optional):
- `Docs/Project Blueprint/Roadmap.md`
- `Docs/Project Blueprint/PRD.md`
- `Docs/Project Blueprint/Product Vision & Scope.md`

**Entry condition**: Sessions A+B+C checkpoints PASSED.

### Session D Workflow

```bash
# Step 1: Optional document check
grep -n "romaneo\|ARCA\|WSCPE\|Phase 1\|MVP" "Docs/Project Blueprint/Roadmap.md" | head -10
# If ARCA/romaneo present: add one sentence about WSCDC obligation

# Step 2: Run FINAL VERIFICATION SWEEP (from plan.md "Final Verification Sweep" section)
# Run all 11 SC commands; record results

# Step 3: Final commit
git add "Docs/Project Blueprint/"
git commit -m "spec-09: final ARCA blueprint enrichment complete — all 11 SC verified"

# Step 4: Create PR
gh pr create \
  --title "spec-09: ARCA Blueprint Knowledge Update (WSCDC, SIRE, WS Padrón)" \
  --body "Enriches 9 blueprint docs with authoritative ARCA facts from RAG. Adds WSCDC, SIRE, WS Padrón sections. Fixes confirmarDescargaCPE in HLD. Adds ADR-036/037. SC-001 through SC-011 verified."
```

---

## Final Verification Commands

```bash
# Run from repo root — copy entire block to terminal

echo "=== SC-001: ≥8 services in ARCA Guide ==="
grep -ci "WSCDC\|WSCPE\|WSLPG\|SIRE IVA\|SIRE\b\|WS Padrón\|Constancia\|WSAA" \
  "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

echo "=== SC-002: Zero wrong method name ==="
grep -rl "descargadoDestinoCPE" "Docs/Project Blueprint/"
echo "(empty output = PASS)"

echo "=== SC-003: WSCDC in 5 mandatory docs ==="
for f in "ARCA Grain Integration Guide.md" "Data Model & Domain Model.md" \
         "High-Level Design (HLD).md" "Architecture Decision Records (ADR).md" \
         "Software Requirements Specification (SRS).md"; do
  count=$(grep -c "WSCDC" "Docs/Project Blueprint/$f" 2>/dev/null)
  echo "  $f: $count"
done

echo "=== SC-004: Zero TBD/TODO/approximate ==="
grep -ri "TBD\|TODO\|approximate" "Docs/Project Blueprint/" | grep -vi "^Binary" | head -10
echo "(empty output = PASS)"

echo "=== SC-005: Error code tables in ≥3 services ==="
grep -c "Error Code\|error code\|Código.*Error" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

echo "=== SC-006: TLS documented ==="
grep -ri "TLS" "Docs/Project Blueprint/"

echo "=== SC-007: SISA % consistency (manual cross-check) ==="
echo "-- ARCA Guide --"; grep -A5 "SISA.*tier\|Ganancias.*%" "Docs/Project Blueprint/ARCA Grain Integration Guide.md" | head -10
echo "-- ADR --"; grep -A3 "Ganancias.*%" "Docs/Project Blueprint/Architecture Decision Records (ADR).md" | head -5
echo "-- SRS --"; grep -A3 "Ganancias.*%" "Docs/Project Blueprint/Software Requirements Specification (SRS).md" | head -5

echo "=== SC-009: ADR-027 label exact match ==="
grep "SISA-Tier Retention Calculation at WSLPG Filing Time" \
  "Docs/Project Blueprint/Architecture Decision Records (ADR).md"

echo "=== SC-010: CA chain names in ARCA Guide ==="
grep -i "AFIPRootCA\|AC_Raiz\|Computadores" "Docs/Project Blueprint/ARCA Grain Integration Guide.md"

echo "=== SC-011: 2 new endpoints in REST API Design ==="
grep -c "wscdc\|sisa-status\|padron" "Docs/Project Blueprint/REST API Design.md"
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| RAG returns empty results | Re-run `ingest_arca_qdrant.py --collection all`; check PDF exists in `Docs/ARCA/` |
| RAG contradicts spec assumption | WSDL is authoritative for method names; update spec assumption and document in research.md |
| Can't find exact ARCA field names | Fall back to direct PDF read: `Read Docs/ARCA/WSCDC/WSCDC-manual-desarrollador-v4.pdf` |
| TBD marker found in non-ARCA section | Scope guard: do not resolve non-ARCA TBDs; note in PR description |
| SISA % values differ between SIRE and WSLPG docs | Use WSLPG (liqLiquidacionACuenta) as authoritative; note discrepancy in research.md |
