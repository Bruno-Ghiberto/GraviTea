# Feature Specification: Acopio de Granos Product Vision & Scope

**Feature Branch**: `001-acopio-vision`
**Created**: 2026-03-15
**Status**: Draft
**Input**: Rewrite Product Vision & Scope from generic horizontal ERP (v0.4) to a fully committed acopio de granos vertical SaaS vision document. The rewritten document is the NORTH STAR for all downstream specs -- every PRD requirement, data model decision, and implementation spec traces its strategic justification back to this document.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Aligns Feature Work to Acopio Strategy (Priority: P1)

A developer working on any GRAVITEA-ERP feature branch opens the Product Vision & Scope document to understand why the acopio vertical was chosen, what the target user looks like, and which phase their feature belongs to. They find a clear vision statement, a committed vertical direction (no "under evaluation" hedging), a phased roadmap that locates their work, and domain-specific personas whose jobs-to-be-done justify the feature's existence.

**Why this priority**: Without strategic clarity, developers build the wrong thing. This is the root document that every downstream spec references. If a developer cannot trace their work back to this document, the feature lacks justification.

**Independent Test**: Can be fully tested by having a developer read the document and correctly identify (a) the target market, (b) the MVP scope, (c) which phase a given feature belongs to, and (d) which persona benefits from it -- without consulting any other document.

**Acceptance Scenarios**:

1. **Given** a developer reads the vision document, **When** they look for the product direction, **Then** they find an unambiguous acopio de granos commitment with zero references to generic retail (no "hardware store", "beverage distributor", "cashier", or "under evaluation")
2. **Given** a developer is assigned to work on grain quality analysis, **When** they consult the phased roadmap, **Then** they can identify which phase (1-4) the feature belongs to and which personas it serves
3. **Given** a developer needs to understand the MVP boundary, **When** they read the MVP scope section, **Then** they find the Romaneo-to-Position loop clearly defined with specific modules and acceptance criteria

---

### User Story 2 - Product Owner Makes Scope Decisions Using Market Data (Priority: P2)

The product owner uses the document to prioritize features and make scope trade-offs. They reference the competitive landscape to understand what incumbents offer (and don't), the pain point analysis to rank user needs by severity, and the TAM/SAM/SOM breakdown to justify investment in specific capabilities. Every market claim is traceable to a cited research document.

**Why this priority**: Scope decisions without market evidence lead to building features nobody needs. The document must contain enough quantified data to resolve prioritization debates without re-reading raw research.

**Independent Test**: Can be tested by presenting a scope trade-off question (e.g., "Should we build weighbridge integration before canje module?") and verifying the document provides sufficient market data, pain point severity ranking, and competitive gap analysis to make an informed decision.

**Acceptance Scenarios**:

1. **Given** the product owner reads the market sizing section, **When** they look for addressable market data, **Then** they find TAM (~1,259 enterprises, ~2,458 plants), SAM (~1,073 private acopiadores, ~1,622 plants), and SOM (Cordoba + Santa Fe initial target) with research document citations
2. **Given** the product owner evaluates a feature request, **When** they consult the competitive landscape, **Then** they find profiles of at least 6 competitors (Algoritmo, AGIS, Physis, AgroAcopio, Finnegans GO Granos, Agrosistemas) with technology stacks, client counts, strengths, and weaknesses
3. **Given** the product owner needs to understand the competitive gap, **When** they read the positioning map, **Then** they see a clear visualization showing GRAVITEA as the only solution combining cloud-native + offline-first + acopio-operational-depth

---

### User Story 3 - Go-to-Market Team Plans Sales Strategy (Priority: P3)

The GTM team reads the document to plan their initial sales approach. They find the contador rural channel strategy with the free portal flywheel mechanism, the geographic beachhead plan (Villa Maria -> Cordoba -> Pampas), specific trade events to attend with dates, the optimal switching window (April-June post-soybean harvest), and the pricing model that disrupts incumbent per-establishment pricing.

**Why this priority**: The GTM strategy determines how the product reaches its first 10-50 customers. Without a documented channel strategy, pricing model, and geographic focus, sales efforts scatter.

**Independent Test**: Can be tested by having a GTM team member create a 90-day sales plan using only the vision document, and verifying it includes specific channel actions (contador outreach), event attendance dates, pricing proposals, and geographic targeting -- without needing external research.

**Acceptance Scenarios**:

1. **Given** a GTM team member reads the channel strategy section, **When** they look for distribution channels, **Then** they find the contador rural free portal flywheel described with mechanics (5-15 clients per estudio, "invitar a tu contador" referral flow, FACPCE/CPCE event targeting)
2. **Given** a GTM team member plans event attendance, **When** they consult the trade events section, **Then** they find specific venues with dates (A Todo Trigo May 2026, Grano SAC November Rosario, Sociedad de Acopiadores de Cordoba)
3. **Given** a GTM team member prepares a pricing proposal, **When** they reference the pricing section, **Then** they find the per-seat USD-indexed model ($90/seat/month), competitive comparison vs incumbents ($500-800/month/establishment), and the free accountant portal as a distribution mechanism

---

### User Story 4 - Investor Evaluates Market Opportunity (Priority: P4)

An investor or advisor reads the document to assess the market opportunity. They find a quantified market (TAM/SAM/SOM with research citations), a clear competitive moat (offline-first + cloud + acopio-depth -- a combination no incumbent offers), a viable GTM strategy with initial traction plan, and a phased roadmap that shows how the product scales from MVP to AI-differentiated platform.

**Why this priority**: While not needed for day-to-day development, investor readiness ensures the document serves double duty as both internal alignment and external communication.

**Independent Test**: Can be tested by having someone unfamiliar with the project read the document and correctly articulate (a) the market size, (b) why incumbents are vulnerable, (c) the pricing model, and (d) the 4-phase roadmap.

**Acceptance Scenarios**:

1. **Given** an investor reads the document, **When** they look for market opportunity, **Then** they find quantified TAM/SAM/SOM with cited sources, competitive gaps, and a pricing model that shows unit economics advantage
2. **Given** an investor asks "why will you win?", **When** they read the technical differentiators and competitive positioning sections, **Then** they find the specific combination (offline-first + cloud-native + acopio-depth) that no incumbent offers, supported by competitor technology analysis showing legacy stacks (VB6, Odoo 13)

---

### User Story 5 - Downstream Spec Authors Trace Requirements (Priority: P5)

Authors of downstream specs (PRD spec-02, data model spec-03, roadmap spec-07, implementation specs 09+) reference the vision document to justify their requirements. Every PRD requirement must trace back to a vision element: a persona, a pain point, a module in the scope, or a phase in the roadmap.

**Why this priority**: Traceability prevents scope creep and ensures every spec connects to business value. Without it, specs drift from the strategic direction.

**Independent Test**: Can be tested by taking any downstream spec requirement and verifying it can be traced to a specific section of the vision document (persona, pain point, module, or phase).

**Acceptance Scenarios**:

1. **Given** a spec author writes a requirement for grain quality grading, **When** they look for the upstream justification in the vision document, **Then** they find it under the Laboratorista persona (quality grading JTBD), Pain Point #4 (producer account disputes), and MVP scope (quality analysis module in Romaneo-to-Position loop)
2. **Given** a spec author needs to justify an AI feature, **When** they reference the vision document, **Then** they find it positioned in Phase 4 of the roadmap with specific capability descriptions (model architectures, expected outcomes)

---

### Edge Cases

- What happens when the existing v0.4 document has content worth preserving? The feature branch history table (001-025) and "Ironclad" design principles MUST be preserved and adapted, not deleted.
- How does the document handle the tension between offline-first as a technical strategy and the market reality that acopio facilities are in small towns (not remote fields)? The connectivity pain point must present the nuanced data: 40.2% of rural parajes have no internet, but acopio plants are in towns with better connectivity -- brief outages during harvest are the real problem, not total absence.
- What happens when market data becomes stale? All quantified claims must cite research document IDs so readers can check the primary source for updated data. The document version and date must be prominent.
- How does the document handle the dual Cordoba advantage and risk? Villa Maria is both the geographic beachhead (direct access to Sociedad de Acopiadores) AND the epicenter of AGIS territory (direct competitor on home turf). Both facts must appear.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Document MUST contain an acopio-specific vision statement that replaces all generic retail language -- zero references to "hardware store", "beverage distributor", "cashier", or "under evaluation" may remain
- **FR-002**: Document MUST include market sizing with quantified data: TAM (~1,259 enterprises, ~2,458 plants nationwide), SAM (~1,073 private acopiadores, ~1,622 plants), SOM (Cordoba + Santa Fe initial target with specific member counts), all citing research document 6.1
- **FR-003**: Document MUST include a competitive positioning map visualizing GRAVITEA as the only solution combining cloud-native + offline-first + acopio-operational-depth, using a Mermaid diagram with axes of deployment model (desktop vs cloud) and vertical depth (generic vs acopio-specific)
- **FR-004**: Document MUST include individual profiles of at least 6 competitors (Algoritmo, AGIS, Physis, AgroAcopio, Finnegans GO Granos, Agrosistemas) with: location, founding year or history, technology stack, client count or market reach, strengths, and weaknesses. MUST also include the 4-tier market segmentation breakdown (large/medium/small-generic/small-manual)
- **FR-005**: Document MUST define 5 acopio-specific user personas with distinct jobs-to-be-done: Dueno/Gerente (remote visibility, grain position, financial control), Balancero/Recibidor (speed during harvest, offline resilience), Laboratorista (quality grading, tolerance tables, merma calculations), Administrador/Contable (regulatory compliance, tax withholdings, C-1116 forms), Contador Rural (multi-client oversight, fiscal compliance verification)
- **FR-006**: Document MUST include a value proposition canvas mapping acopiador-specific pains (regulatory burden, tax withholding complexity, inventory reconciliation, producer disputes, manual data entry, connectivity gaps) to corresponding gains (automatic compliance, real-time grain position, offline operations, dispute-preventing transparency, weighbridge integration, hybrid architecture)
- **FR-007**: Document MUST define the MVP scope as the Romaneo-to-Position loop covering: reception (truck arrival, weighbridge), quality analysis (lab grading, merma calculations), storage assignment (silo allocation), and producer account credit -- consistent with the architectural decision for Approach B
- **FR-008**: Document MUST include a module map with 8 functional areas consistent with Descripcion General del Producto.md: Recepcion (Romaneo), Almacenamiento, Calidad, Cuentas Corrientes, Liquidaciones, Facturacion, Agronomia (Insumos), Canje -- rendered as a Mermaid diagram
- **FR-009**: Document MUST include a technical differentiators section leading with offline-first architecture as the primary competitive moat, followed by: Rust acceleration (merma engine), PostgreSQL RLS multi-tenancy, ARCA direct integration, AI-ready data architecture, field-level encryption for PII
- **FR-010**: Document MUST include an AI differentiation roadmap with at least 6 capabilities from research 9.1 positioned as Phase 3-4 features: quality degradation prediction (3D-CNN + LSTM), silo assignment optimization (MILP), price forecasting (VMD-SGMD-LSTM for Matba Rofex), weighbridge fraud detection (anomaly detection), document intelligence (OCR Carta de Porte), predictive aeration scheduling (SVM-Poly)
- **FR-011**: Document MUST include a go-to-market strategy covering: contador rural channel (free portal = distribution flywheel, 5-15 acopio clients per estudio, "invitar a tu contador" referral flow, FACPCE/CPCE course targeting), geographic beachhead (Villa Maria -> Cordoba -> Pampas), trade events with specific venues and dates (A Todo Trigo May 2026, Sociedad de Acopiadores de Cordoba, Grano SAC Rosario November), and April-June switching window (post-soybean harvest)
- **FR-012**: Document MUST include a pricing strategy section with: per-seat USD-indexed model ($90/seat/month, annual discount to $75/seat), competitive comparison vs incumbents ($500-800/month/establishment), free accountant portal as distribution mechanism, and the per-seat disruption insight (small acopio with 2 users pays ~$180 vs $500+)
- **FR-013**: Document MUST include a phased roadmap overview: Phase 1 (Romaneo + Position), Phase 2 (Liquidaciones + WSLPG), Phase 3 (Canje + Agronomia), Phase 4 (AI) -- rendered as a Mermaid diagram
- **FR-014**: Document MUST include success metrics (KPIs) organized by category: Operational (harvest throughput in trucks/hour, sync latency, system uptime), Adoption (onboarding time, active user count), Business (stock discrepancy reduction %, regulatory compliance rate for CTG/LPG filings, ARPU)
- **FR-015**: Document MUST include a risk and mitigation section covering at minimum: connectivity limitations, regulatory change velocity, competitor response, adoption resistance from generational divide, data migration barrier, and the 7-in-10 implementation failure rate statistic with mitigation strategy
- **FR-016**: Document MUST preserve the existing feature branch history table (branches 001-025) showing infrastructure that carries forward into the acopio vertical
- **FR-017**: Document MUST preserve and adapt the "Ironclad" design guiding principles for the acopio context, adding at minimum: "Regulatory Automation" (automatic compliance with ARCA/SISA/CTG) and "AI-Ready Data Architecture" (structured data capture enabling future ML features)

### Key Entities

- **Vision Document**: The deliverable itself -- a self-contained strategic document (target: `Docs/Project Blueprint/Product Vision & Scope.md` v1.0) that replaces v0.4. Contains 11 major sections, at least 5 Mermaid diagrams, and all market data with research citations.
- **Competitor Profile**: Structured analysis of each competing product including location, technology stack, client reach, strengths, weaknesses, and strategic vulnerability. At least 6 profiles required covering both desktop incumbents and cloud entrants.
- **User Persona**: Named archetype representing a distinct role in acopio operations with specific jobs-to-be-done, pain points, and success criteria. 5 personas required spanning operational, administrative, and advisory roles.
- **Market Segment**: A tier in the 4-level market segmentation (large enterprise, medium specialized, small generic-ERP, small manual/Excel) with estimated percentage of total acopiadores and current software solution patterns.
- **Phased Roadmap**: A 4-phase product development plan where each phase builds on the previous, with clear scope boundaries and feature groupings. Phase 1 is the MVP (Romaneo-to-Position loop).
- **Module**: A functional area of the product (8 total from Descripcion General) that maps to specific acopio operations. Each module has defined scope, phase assignment, and persona relevance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Document is self-contained -- a reader unfamiliar with the project can understand the market opportunity, product direction, and competitive positioning without consulting any other document
- **SC-002**: 100% of market size claims (TAM/SAM/SOM figures, competitor data, pain point statistics) include research document citations traceable to specific research reports
- **SC-003**: Zero instances of generic retail language remain ("hardware store", "beverage distributor", "cashier", "under evaluation") -- verifiable by full-text search
- **SC-004**: All 5 downstream spec authors (spec-02 PRD, spec-03 data model, spec-07 roadmap, spec-09+ implementation) can trace every requirement back to a specific section of this document (persona, pain point, module, or phase)
- **SC-005**: The competitive positioning section clearly demonstrates GRAVITEA's unique market position (cloud-native + offline-first + acopio-depth) as a combination no existing competitor offers -- verifiable by checking each competitor profile against these three axes
- **SC-006**: A GTM team member can produce a 90-day sales action plan (target accounts, channel tactics, event calendar, pricing proposals) using only the information in this document
- **SC-007**: The document contains at least 5 Mermaid diagrams (competitive positioning, module map, operational flow, persona hierarchy, phased roadmap) that render correctly in standard Markdown viewers
- **SC-008**: Module definitions are consistent with `Docs/Project Blueprint/Descripcion General del Producto.md` -- verifiable by cross-referencing module names, scope boundaries, and operational flows
- **SC-009**: Feature branch history table preserves all 25 existing branches (001-025) with accurate descriptions of the infrastructure they contribute to the acopio vertical

## Assumptions

- The acopio de granos vertical pivot is a final, committed decision -- not subject to further evaluation or reversal. The document declares this as definitive direction.
- Market data from research documents (4.1, 4.2, 4.3, 6.1, 6.2, 6.3, 9.1) is current as of the research date and sufficiently accurate for strategic planning.
- The Descripcion General del Producto.md already contains the authoritative module map and operational flow; the vision document adapts and presents this in strategic context rather than redefining it.
- The existing feature branch history (001-025) represents infrastructure that carries forward into the acopio vertical and should not be deprecated or removed.
- The pricing model ($90/seat/month USD-indexed) represents the current business panel consensus and may be refined during go-to-market execution, but serves as the strategic baseline for the vision document.
- The 4-phase roadmap (Romaneo+Position -> Liquidaciones+WSLPG -> Canje+Agronomia -> AI) is the agreed development sequence and aligns with architectural decisions already made (Approach B).
