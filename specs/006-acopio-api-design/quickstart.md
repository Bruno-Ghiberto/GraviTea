# Quickstart: REST API Design — Verification Gates

**Feature**: `006-acopio-api-design`
**Deliverable**: `Docs/Project Blueprint/REST API Design.md`

## Pre-Implementation Checklist

- [ ] Upstream docs available: Data Model v1.0, HLD v1.0, ADR v1.0
- [ ] Branch `006-acopio-api-design` checked out
- [ ] RAG pipeline accessible (Qdrant running on :6333)

## Writing Execution

Single atomic Write pass. All 13 sections written together to ensure internal consistency (summary table in §13 must match endpoints in §3-§12).

## Verification Gates

Run these checks AFTER writing the document. Fix failures in-place, then re-verify.

### G1 — Version Metadata
```bash
grep 'Version 1.0' "Docs/Project Blueprint/REST API Design.md" | wc -l
# Expected: >= 2 (blockquote + table cell)
```

### G2 — Design Principles Complete
```bash
grep -c "^### " "Docs/Project Blueprint/REST API Design.md" | head -1
# Check: §2.1 through §2.8 all present (8 subsections under §2)
```

### G3 — Mermaid Diagrams
```bash
grep -c '```mermaid' "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 3 (auth flow, romaneo lifecycle, sync round-trip)
```

### G4 — Romaneo Endpoints Count
```bash
grep -c '/api/v1/acopio/romaneos' "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 11 (create, list, retrieve, patch, 6 transitions, merma-preview)
```

### G5 — Posicion Consolidada
```bash
grep -i 'posicion.consolidada' "Docs/Project Blueprint/REST API Design.md"
# Expected: match found, described as "derived view" or "computed"
```

### G6 — Encrypted CUIT Note
```bash
grep -i 'blind.index' "Docs/Project Blueprint/REST API Design.md"
# Expected: match found (HMAC-SHA256 blind index for CUIT search)
```

### G7 — Domain Error Types
```bash
grep -c 'romaneo_immutable\|invalid_state_transition\|tenant_mismatch\|tare_weight_required\|arca_unavailable' "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 5 (subset of 11 total error types)
```

### G8 — Phase 2 Blockquote
```bash
grep 'Phase 2' "Docs/Project Blueprint/REST API Design.md" | head -3
# Expected: contains "Not active in Phase 1 delivery"
```

### G9 — Endpoint Summary Table
```bash
grep -c '| .* | /api/v1/' "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 35 rows in the summary table
```

### G10 — Heading Count
```bash
grep -c "^#" "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 40
```

### G11 — No Implementation Code
```bash
grep -ciE 'import |from .* import|class .*View|class .*Serializer' "Docs/Project Blueprint/REST API Design.md"
# Expected: 0
```

### G12 — No TBD/Placeholder
```bash
grep -ci 'TBD\|to be determined\|placeholder\|TODO' "Docs/Project Blueprint/REST API Design.md"
# Expected: 0 (Phase 2 section says "Not active" not "TBD")
```

### G13 — HTTP 202 for Async Endpoints
```bash
grep -c '202' "Docs/Project Blueprint/REST API Design.md"
# Expected: >= 2 (confirmar-arribo and cerrar both return 202 Accepted)
```

## Post-Verification

When all 13 gates pass:
1. Mark tasks as complete in tasks.md
2. Save Serena memory with session status
3. Save Engram observation with deliverable summary
