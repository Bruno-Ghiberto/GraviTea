# Document Structure Definitions: spec-08

**Branch**: `008-acopio-new-docs` | **Date**: 2026-03-18

> This file defines the structure of the three deliverable documents.
> For a blueprint spec, "data model" = document architecture.

## 08a — ARCA Grain Integration Guide

**File**: `Docs/Project Blueprint/ARCA Grain Integration Guide.md`
**Sections**: 11 (§1 Metadata through §11 Glossary)
**Mermaid diagrams**: ≥ 3
**Tables**: ≥ 5
**Estimated length**: 400-500 lines

Key structural elements:
- Service catalog table (§2): 4 rows (WSAA, WSLPG, WSCPE, WSFEv1) × 5 columns (service, purpose, phase, prod URL, homolog URL)
- Retention tier table (§4): 4 rows (Estado 1-3 + Non-registered) × 3 columns (estado, IVA rate, Ganancias rate)
- Error handling table (§7): consolidated across all 4 services
- ADR cross-reference table (§10): 7 rows (ADR-019, 025-030)

## 08b — AI/ML Feature Roadmap

**File**: `Docs/Project Blueprint/AI-ML Feature Roadmap.md`
**Sections**: 11 (§1 Metadata through §11 ADR Cross-Reference)
**Mermaid diagrams**: ≥ 2
**Tables**: ≥ 4
**Estimated length**: 300-400 lines

Key structural elements:
- ML model catalog table (§4): 6+ rows (P3-Q1 through Q4, HLD informative, deferred CV) × 5 columns (model, input features, target, min training data, timeline)
- Training data thresholds table (§6): per-model minimum data requirements
- IoT sensor options table (§8): sensor type × protocol × use case
- ADR cross-reference table (§11): 3 rows (ADR-033, 034, 035)

## 08c — Software Requirements Specification (SRS)

**File**: `Docs/Project Blueprint/Software Requirements Specification (SRS).md`
**Sections**: 12 (§1 Metadata through §12 Appendix)
**Tables**: ≥ 6
**Estimated length**: 500-700 lines (largest document due to shall-statement tables)

Key structural elements:
- Phase 1 requirements tables (§4): 4 sub-tables (RECEPCION, CALIDAD, ALMACENAMIENTO, CUENTAS CORRIENTES)
  - Each row: ID | Description (shall) | Priority (MoSCoW) | PRD Source | Impl Spec | API Endpoint
  - Total: ≥ 20 requirement IDs, ≥ 30 shall-statements
- Phase 2 deferred stubs (§5): 4 sub-tables with reserved ID namespaces
- Interface requirements (§6): 3 sub-sections (ARCA SOAP, weighbridge hardware, REST API)
- Traceability matrix (§10): PRD story → SRS-ID → impl spec → API endpoint → test marker
- Requirement ID namespace appendix (§12): 13 prefix codes with reserved ranges

## Cross-Document References

| From | To | Reference Type |
|------|----|----------------|
| 08c §6.1 | 08a | "See ARCA Grain Integration Guide for detailed SOAP method reference" |
| 08c §4 (API endpoint column) | REST API Design v1.0 | Endpoint path references |
| 08c §10 (traceability matrix) | PRD §4, REST API v1.0 | Full traceability chain |
| 08b §7 | Roadmap §7.1/§7.4 | Phase 3 delivery sequence and triggers |
| 08b §3 | Data Model v1.0 | Concrete field references per layer |
| All three | ADR v1.0 | ADR-NNN (Title) citation format |
