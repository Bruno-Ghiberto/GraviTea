# Acceptance Gates Contract: Roadmap.md v1.0

**Spec**: `007-acopio-roadmap`
**Deliverable**: `Docs/Project Blueprint/Roadmap.md`
**Contract type**: Grep-verifiable acceptance criteria

These gates define the "done" contract for the Roadmap blueprint document.
All 12 must pass before the spec is marked complete and the branch is merged.

---

## Gate Definitions

| Gate | Description | Test | Pass Condition |
|------|-------------|------|---------------|
| G1 | Version 1.0 metadata | `grep -c "Version 1.0"` | ≥ 2 |
| G2 | Three-phase coverage | `grep -c "Phase 1\|Phase 2\|Phase 3"` | ≥ 15 |
| G3 | MVP specs referenced | `grep -c "spec-09\|spec-10\|spec-11\|spec-12"` | ≥ 8 |
| G4 | Phase 2 specs referenced | `grep -c "spec-13\|spec-14\|spec-15\|spec-16"` | ≥ 4 |
| G5 | Mermaid diagrams present | `` grep -c '```mermaid' `` | ≥ 2 |
| G6 | Contador rural channel | `grep -ic "contador"` | ≥ 4 |
| G7 | Post-harvest switching window | `grep -ic "abril\|june\|post-harvest\|switching window"` | ≥ 2 |
| G8 | Risk register depth | `grep -c "\| R[0-9]"` | ≥ 8 |
| G9 | No unresolved placeholders | `grep -ci "TBD\|TODO"` | = 0 |
| G10 | KPI coverage | `grep -ci "KPI\|paying customer\|romaneo\|onboarding"` | ≥ 6 |
| G11 | No code blocks | `` grep -c '```python\|```sql\|```bash' `` | = 0 |
| G12 | Heading count | `grep -c "^#"` | ≥ 35 |

---

## Key Content Constraints

The document MUST contain (verified by G3/G4 + manual check):

**Phase 1 scope** — exactly these four specs:
- spec-09: Grain Reference Data → `apps/acopio/` models + fixtures
- spec-10: Romaneo Core → `apps/acopio/` + `rust/gravitea-core/src/merma.rs`
- spec-11: Storage & Position → `apps/acopio/` storage models
- spec-12: Producer Accounts → `apps/cuentas/` + encrypted CUIT + blind index

**Phase 2 trigger conditions** (all three required):
- ≥5 paying customers
- Phase 1 stable ≥60 calendar days with no P1/P2 bugs
- ≥100 romaneos processed in production

**ARCA service distinction** (critical — do not conflate):
- CPE/WSCPE = Phase 1 (grain transport certificate, initiated at romaneo)
- WSLPG = Phase 2 (liquidación primaria, Form 1116 B/C, settlement document)

**Module paths** (canonical — from spec-03 Data Model):
- Grain domain: `backend/apps/acopio/` (app_label: gravitea_acopio)
- Producer accounts: `backend/apps/cuentas/` (app_label: gravitea_cuentas)

---

## ADR Cross-References Required

The document MUST reference these ADRs in context:

| ADR | Content | Section in Roadmap |
|-----|---------|-------------------|
| ADR-027 | SISA-tier retention calculation at WSLPG filing (blocking gate) | §6.4 |
| ADR-033 | AI event log table | §7.3 |
| ADR-034 | ML scoring table | §7.3 |
| ADR-035 | AI query patterns | §7.3 |
| ADR-025 | WSAA hub-and-spoke | §6.4 |

---

## Non-Goals (explicitly excluded)

The document MUST NOT contain:

- Python code blocks (```python)
- SQL code blocks (```sql)
- Shell/bash code blocks (```bash) — grep commands in `quickstart.md` are OK,
  but must not appear in `Roadmap.md` itself
- Absolute implementation dates (e.g., "by March 15, 2026") — use T+ offsets or
  seasonal anchors (April–June)
- References to the general GRAVITEA-ERP modules (`apps/inventario/`, `apps/ventas/`,
  etc.) — the Roadmap is scoped to the acopio vertical only
