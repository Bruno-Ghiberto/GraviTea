# Quickstart: Verify Roadmap.md v1.0

**Branch**: `007-acopio-roadmap`
**Purpose**: Verify all 12 acceptance gates on the completed Roadmap document.
**Run from**: Project root (`/home/brunoghiberto/Documents/Projects/GraviTea/`)

---

## Prerequisites

The document must exist at:
```
Docs/Project Blueprint/Roadmap.md
```

All 12 gates below must pass before marking spec-07 complete.

---

## Gate Verification (run all 12)

```bash
TARGET="Docs/Project Blueprint/Roadmap.md"

echo "=== GATE G1: Version 1.0 metadata (≥2 occurrences) ==="
COUNT=$(grep -c "Version 1.0" "$TARGET")
echo "Found: $COUNT (need ≥2)"
[ "$COUNT" -ge 2 ] && echo "G1: PASS" || echo "G1: FAIL"

echo ""
echo "=== GATE G2: Three phases coverage (≥15 occurrences) ==="
COUNT=$(grep -c "Phase 1\|Phase 2\|Phase 3" "$TARGET")
echo "Found: $COUNT (need ≥15)"
[ "$COUNT" -ge 15 ] && echo "G2: PASS" || echo "G2: FAIL"

echo ""
echo "=== GATE G3: All MVP specs referenced (≥8 occurrences) ==="
COUNT=$(grep -c "spec-09\|spec-10\|spec-11\|spec-12" "$TARGET")
echo "Found: $COUNT (need ≥8)"
[ "$COUNT" -ge 8 ] && echo "G3: PASS" || echo "G3: FAIL"

echo ""
echo "=== GATE G4: Phase 2 specs referenced (≥4 occurrences) ==="
COUNT=$(grep -c "spec-13\|spec-14\|spec-15\|spec-16" "$TARGET")
echo "Found: $COUNT (need ≥4)"
[ "$COUNT" -ge 4 ] && echo "G4: PASS" || echo "G4: FAIL"

echo ""
echo "=== GATE G5: Mermaid diagrams (≥2) ==="
COUNT=$(grep -c '```mermaid' "$TARGET")
echo "Found: $COUNT (need ≥2)"
[ "$COUNT" -ge 2 ] && echo "G5: PASS" || echo "G5: FAIL"

echo ""
echo "=== GATE G6: Contador rural GTM (≥4 occurrences) ==="
COUNT=$(grep -ic "contador" "$TARGET")
echo "Found: $COUNT (need ≥4)"
[ "$COUNT" -ge 4 ] && echo "G6: PASS" || echo "G6: FAIL"

echo ""
echo "=== GATE G7: Post-harvest switching window (≥2 occurrences) ==="
COUNT=$(grep -ic "abril\|june\|post-harvest\|switching window\|cosecha\|post-soja" "$TARGET")
echo "Found: $COUNT (need ≥2)"
[ "$COUNT" -ge 2 ] && echo "G7: PASS" || echo "G7: FAIL"

echo ""
echo "=== GATE G8: Risk register depth (≥8 risk rows) ==="
COUNT=$(grep -c "| R[0-9]" "$TARGET")
echo "Found: $COUNT (need ≥8)"
[ "$COUNT" -ge 8 ] && echo "G8: PASS" || echo "G8: FAIL"

echo ""
echo "=== GATE G9: No TBD/TODO placeholders (must be 0) ==="
COUNT=$(grep -ci "TBD\|TODO" "$TARGET")
echo "Found: $COUNT (need 0)"
[ "$COUNT" -eq 0 ] && echo "G9: PASS" || echo "G9: FAIL"

echo ""
echo "=== GATE G10: KPI coverage (≥6 mentions) ==="
COUNT=$(grep -ci "KPI\|paying customer\|romaneo\|onboarding\|contador enroll" "$TARGET")
echo "Found: $COUNT (need ≥6)"
[ "$COUNT" -ge 6 ] && echo "G10: PASS" || echo "G10: FAIL"

echo ""
echo "=== GATE G11: No code blocks (Python/SQL/bash must be 0) ==="
COUNT=$(grep -c '```python\|```sql\|```bash' "$TARGET")
echo "Found: $COUNT (need 0)"
[ "$COUNT" -eq 0 ] && echo "G11: PASS" || echo "G11: FAIL"

echo ""
echo "=== GATE G12: Section headings count (≥35) ==="
COUNT=$(grep -c "^#" "$TARGET")
echo "Found: $COUNT (need ≥35)"
[ "$COUNT" -ge 35 ] && echo "G12: PASS" || echo "G12: FAIL"

echo ""
echo "=== ALL GATES SUMMARY ==="
```

---

## Manual Review Gate (G7 — Executive Summary Quality)

After all grep gates pass, manually verify:

**Read §2 Executive Summary and confirm it answers all four questions:**

1. What is GraviTea Acopio ERP? (cloud-native, offline-first, Argentine acopiadores)
2. Why now? (AGIS VB6/.NET gap, ARCA regulatory velocity, post-harvest window, generational shift)
3. What is the execution plan? (3 phases, Phase 1 in T+16 weeks, 4 implementation specs)
4. How does GTM work? (contador rural flywheel, April–June switching window)

An advisor unfamiliar with the prior specs must be able to read §2 + §3 and answer all
four questions without consulting any other document.

---

## Line Count Reference

The completed document should fall in this range:
```bash
wc -l "Docs/Project Blueprint/Roadmap.md"
# Expected: ~530 lines (actual v1.0: 527 lines)
```

---

## Completion Action

When all 12 gates pass:

1. Update `specs/007-acopio-roadmap/spec.md` status from `Draft` to `Complete`
2. Save Serena memory: `session-[date]-spec07-roadmap-complete`
3. Commit on `007-acopio-roadmap` branch:
   ```bash
   git add "Docs/Project Blueprint/Roadmap.md" specs/007-acopio-roadmap/
   git commit -m "docs: add Roadmap.md v1.0 (spec-07)"
   ```
