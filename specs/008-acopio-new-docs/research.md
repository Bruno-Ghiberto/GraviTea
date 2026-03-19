# Research: Acopio New Blueprint Documents (08a/08b/08c)

**Branch**: `008-acopio-new-docs` | **Date**: 2026-03-18

## Summary

All research tasks were resolved during `/sc:design` (08-specify.md creation) and `/sc:improve` (coherence validation). RAG queries ran against the `acopio_research` collection (10/13 succeeded; 3 failed because `arca_api_specs`/`arca_dev_guides` collections didn't exist at the time — now freshly ingested with 10 new ARCA PDFs).

## Decisions

### D1: WSCPE Method Name Resolution

- **Decision**: Use `confirmarDescargaCPE` (from ARCA WSDL research 1.2), not `descargadoDestinoCPE` (from HLD §6.4)
- **Rationale**: The ARCA WSDL is the authoritative source for method names. The HLD used a paraphrased name. 08a must resolve this against the newly ingested `manual-wscpe.pdf` and document the correction.
- **Alternatives considered**: Keep HLD naming → rejected because it would cause integration failures against the actual WSDL.

### D2: Phase Model Alignment

- **Decision**: Use the Roadmap's 3-phase model throughout all three documents. ML features are "Phase 3", not "Phase 4".
- **Rationale**: The Roadmap v1.0 is the most recent and authoritative planning document. It consolidated PRD Phase 3 (CANJE/AGRONOMIA/OCR) + Phase 4 (AI/ML) into Roadmap Phase 2 (Advanced) + Phase 3 (Intelligence & Scale).
- **Alternatives considered**: Use HLD's 4-phase model → rejected because the Roadmap supersedes it and was specifically designed to resolve this discrepancy.

### D3: Document Language

- **Decision**: English with Spanish domain terms retained unitalicized after first use.
- **Rationale**: All existing blueprint documents (HLD, Roadmap, PRD, ADR) follow this pattern. The domain terms (romaneo, merma, liquidacion, etc.) have no adequate English translation and are the canonical terms in the Data Model.
- **Alternatives considered**: Full Spanish → rejected (team may include international members). Full English → rejected (domain terms lose precision).

### D4: 08c SRS Replacement Strategy

- **Decision**: Complete overwrite of existing SRS. Preserve nothing from the stale retail-vertical version.
- **Rationale**: The existing SRS was written for the old general-purpose ERP (ferreterias, corralones, retail PyMEs) and has zero applicability to the acopio de granos vertical. A partial update would be more error-prone than a clean rewrite.
- **Alternatives considered**: Partial update → rejected (stale content would contaminate new requirements).

### D5: ARCA RAG Collection Strategy

- **Decision**: 10 new ARCA PDFs ingested into `arca_api_specs` (3 files), `arca_dev_guides` (7 files), keeping `arca_setup_certs` unchanged.
- **Rationale**: The freshly downloaded documents (WSLPG v1.24 manual, WSCPE manual, WS Padrón, SIRE, WSCDC) provide the primary source material for 08a. Having them in Qdrant enables RAG queries during document writing.
- **Alternatives considered**: Read PDFs directly → rejected (too large for context window; RAG is more efficient).

## Unresolved Items

None. All NEEDS CLARIFICATION markers resolved.
