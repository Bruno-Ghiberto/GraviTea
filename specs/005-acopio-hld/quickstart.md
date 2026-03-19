# Quickstart: Accepting and Verifying the HLD Document

**Feature**: 005-acopio-hld
**Date**: 2026-03-17
**Deliverable**: `Docs/Project Blueprint/High-Level Design (HLD).md`

This guide describes how to verify that the completed HLD document satisfies all 12 done
criteria. Run these commands from the repository root after implementation.

---

## Prerequisites

The file must exist:

```bash
test -f "Docs/Project Blueprint/High-Level Design (HLD).md" && echo "EXISTS" || echo "MISSING"
```

---

## Verification Scenarios

### SC-0501 — Developer finds responsible app in ≤2 minutes

Open `Docs/Project Blueprint/High-Level Design (HLD).md`, navigate to §5 Component Overview.
Look up the `Romaneo` entity. You should immediately see it listed under `apps/acopio`.

**Acceptance**: The entity name appears in the `apps/acopio` subsection with related entities
`QualityAnalysis`, `MermaCalculation`, `CPE`, `WeighbridgeDevice` also listed.

```bash
grep "Romaneo" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1 match in the apps/acopio section
```

---

### SC-0502 — CAEA legal constraint is unambiguous

Navigate to §6.5 (CAEA). The constraint on offline invoicing must be explicit.

```bash
grep "CAEA codes MUST be obtained before" "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥1 match
```

---

### SC-0503 — All 5 conflict resolution strategies locatable in ≤30 seconds

Navigate to §8.4 using the table of contents. The conflict resolution table must show all 5
strategy names with target data types.

```bash
grep "server_wins\|last_write_wins\|additive\|most_complete_wins\|server_assigns_final" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 5 matches (one per strategy)
```

---

### SC-0504 — Romaneo flow has exactly 10 steps

Navigate to §9.1. Count the numbered steps in the step list below the sequence diagram.

```bash
grep -c "^| [0-9]\+ " "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥10 (10 romaneo steps + other tables)

# Verify the step text for key steps:
grep "peso_bruto\|merma_calculate\|peso_tara\|boleta" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥4 matches
```

---

### SC-0505 — New team member self-test (manual verification)

Read sections 3, 5, 6, 8, 10, and 12 of the HLD only. Without consulting any other document,
verify you can answer:

1. Name all 4 ARCA external services. → WSAA, WSLPG, WSCPE, WSFEv1
2. Name the 3 tenant isolation layers. → ORM TenantBoundManager, PostgreSQL RLS, IDOR/JWT validation
3. Name the 4 AI/ML data layers. → Operational, Behavioural, Quality History, Physical State (IoT)

---

### SC-0506 — Zero hedging language

```bash
grep -i "TBD\|TODO\|FIXME\|possibly\|might consider" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: 0 matches (empty output)
```

---

### SC-0507 — All Mermaid diagrams render without syntax errors

Open the file in a Mermaid-capable renderer (GitHub, VS Code with Mermaid plugin, or
`mmdc` CLI). Verify the following diagrams render correctly:

| Diagram | Section | Type |
|---------|---------|------|
| C4 Level 1 System Context | §3.1 | `graph TD` |
| C4 Level 2 Container Architecture | §4.1 | `graph TD` with subgraph |
| Defense-in-Depth Security | §10.1 | `graph TD` |
| WSAA Authentication Flow | §6.2 | `sequenceDiagram` |
| Romaneo Reception Flow | §9.1 | `sequenceDiagram` |
| Fiscal Authorization Flow | §9.2 | `flowchart TD` |
| Production Deployment Topology | §11.3 | `graph TD` |

```bash
grep -c '```mermaid' "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥6 (7 diagrams total)
```

---

### SC-0508 — ADR cross-reference table covers all 8 categories

Navigate to §13. Verify the technology cross-reference table contains all 8 ADR categories.

```bash
grep "Infrastructure\|Data Architecture\|Grain Domain\|Security\|Fiscal Integration" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥5 distinct category names

grep "Offline.*Sync\|Performance\|AI/ML Readiness" \
  "Docs/Project Blueprint/High-Level Design (HLD).md"
# Expected: ≥3 distinct category names
```

---

## Full Gate Verification (all at once)

Run this script from repo root to verify all done criteria in one pass:

```bash
#!/usr/bin/env bash
HLD="Docs/Project Blueprint/High-Level Design (HLD).md"
PASS=0
FAIL=0

check() {
  local desc="$1"
  local cmd="$2"
  local expected="$3"
  local result
  result=$(eval "$cmd" 2>/dev/null)
  if [[ "$result" == "$expected" || ( "$expected" == ">0" && -n "$result" ) ]]; then
    echo "✓ $desc"
    ((PASS++))
  else
    echo "✗ $desc (expected: $expected, got: $result)"
    ((FAIL++))
  fi
}

check "File exists"                     "test -f '$HLD' && echo EXISTS" "EXISTS"
check "Version 1.0 present"             "grep -c 'Version 1.0' '$HLD'"  ">0"
check "CAEA legal constraint present"   "grep -c 'CAEA codes MUST be obtained before' '$HLD'" ">0"
check "Benchmark × values present"      "grep -c '8\.7×\|8\.8×\|4\.4×' '$HLD'" ">0"
check "Phase 2 annotations present"     "grep -c 'Phase 2' '$HLD'"  ">0"
check "Conflict strategies present (5)" "grep -c 'server_wins\|last_write_wins\|additive\|most_complete_wins\|server_assigns_final' '$HLD'" ">0"
check "RLS session variable present"    "grep -c 'SET LOCAL app.current_tenant_id' '$HLD'" ">0"
check "44% connectivity statistic"      "grep -c '44%' '$HLD'"  ">0"
check "KYASERV named"                   "grep -c 'KYASERV' '$HLD'" ">0"
check "IoT anchor field named"          "grep -c 'environment_sensor_id' '$HLD'" ">0"
check "Zero hedging language"           "grep -ic 'TBD\|TODO\|FIXME\|possibly\|might consider' '$HLD'" "0"
check "≥6 Mermaid diagrams"             "[ \$(grep -c '\`\`\`mermaid' '$HLD') -ge 6 ] && echo OK" "OK"
check "≥40 headings"                    "[ \$(grep -c '^## \|^### ' '$HLD') -ge 40 ] && echo OK" "OK"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]] && echo "ALL CHECKS PASSED" || echo "FAILURES DETECTED — fix before committing"
```

---

## What to Check Manually

These require a human reader; they cannot be automated with grep:

1. **Mermaid syntax**: Each diagram must render without parse errors. Test by pasting into
   [mermaid.live](https://mermaid.live) or checking GitHub preview.

2. **10-step romaneo flow completeness**: The step list below §9.1 diagram must have exactly 10
   entries and each must name the responsible component.

3. **Section completeness**: Scan the table of contents. Every section from §1 to §13 must be
   present with subsections.

4. **Self-contained readability**: A developer unfamiliar with the codebase should be able to
   understand the container architecture, ARCA integration constraints, and security model from
   the HLD alone without consulting specs 01–04.
