# Deep Research Prompt: Argentine Vertical SaaS Niche Discovery

> **How to use this file**: Copy the content below the `---` line and paste it verbatim into any LLM with web search capability (Perplexity, ChatGPT with search, Gemini with grounding, Claude with search, etc.). Run one phase at a time for best results, or provide the full document to a model capable of long-context deep research.

---

## CONTEXT (read before starting)

I am a 4-person software startup (2 developers) building a vertical SaaS ERP system targeting the Argentine SME market. We are **pivoting from a generic ERP** to a **niche-specific ERP** focused on one industry sector in Argentina.

### Our existing platform (production-ready, March 2026)

**Core stack**: Python 3.14.3, Django 5.2.x, Django REST Framework 3.15, PostgreSQL 18.1, Redis 7.x, Docker Compose.

**Backend modules already implemented**:
- **Multi-tenant isolation**: Defense-in-Depth — TenantBoundManager + PostgreSQL Row Level Security + IDOR validation. Complete tenant data isolation.
- **Authentication**: JWT RS256 with custom tenant claims, 3-tier rate limiting, Argon2 password hashing, RBAC.
- **Inventory (INVENTARIO)**: Products (encrypted barcodes), StockMovement (immutable ledger), Categories, Suppliers (encrypted PII), PriceLists.
- **Sales (VENTAS)**: Customers, SaleOrders (DRAFT→CONFIRMED→INVOICED), SaleOrderItems, nested routing.
- **Electronic invoicing (FACTURACION ARCA)**: WSAA + WSFEv1, CAE lifecycle, CAEA offline batching, fiscal QR codes, immutable Comprobantes. Facturas A/B/C/M fully implemented.
- **Offline-first sync**: Push/Pull APIs, SyncSession with vector clocks, PendingOperation, server-side conflict resolution (most_complete_wins strategy).
- **Encryption**: AES-256-GCM field-level encryption for PII, HMAC-SHA256 blind index search.
- **Tenant customization**: Custom fields (6 types: text, integer, decimal, boolean, date, select), module config, business templates.
- **Observability**: Prometheus + Grafana + Jaeger + Loki, OpenTelemetry distributed tracing, 11-file instrumentation stack.
- **Purchases (COMPRAS)**: Supplier model + API contract defined; purchase workflow pending.
- **Reports (REPORTES)**: API contract defined; Rust export engine (CSV/XLSX) built; implementation pending.

**Rust/PyO3 acceleration layer** (9 native modules, 2-9x speedups over Python):
- `crypto.rs`: AES-256-GCM encryption/decryption (8.7x speedup)
- `compute.rs`: IVA validation/calculation (4.4x), CUIT validation (3.1x), stock aggregation (2.1x)
- `export.rs`: CSV (UTF-8 BOM, RFC 4180) and XLSX generation with Python fallback
- `observability.rs`: Prometheus label sanitization (2.6x)
- `security.rs`: SSRF URL validation pipeline (83-entry adversarial corpus)
- `sync.rs`: JSON merge engine for offline conflict resolution
- `arca.rs`: CAEA batch construction for bulk ARCA invoicing
- `validation.rs`: Custom field type validation (6 types)

**API maturity**: 9 OpenAPI contracts, 79 paths, 154 schemas, 137 operations — all auto-generated from DRF Spectacular.

**Frontend prototype**: Next.js 16.1.6 (App Router) + TypeScript strict + shadcn/ui — 9 routes, 52 source files (dev environment only; not production-ready).

**Quality**: 2,500+ automated tests (backend + 131 Rust integration tests), 0 regressions across all modules.

### What this means for niche selection

The platform is a **reusable foundation** — multi-tenant auth, inventory, sales, ARCA invoicing, offline sync, encryption, and Rust acceleration are already built. The niche-specific gap is the additional domain logic, regulatory integrations, and workflows that differentiate one industry from another. The right niche **maximizes reuse** of what we already have while adding a **defensible moat** (regulatory compliance, domain expertise, or workflow lock-in) that generic competitors cannot easily replicate.

### Constraints

- Our team can sustain **1 niche deeply** — we cannot serve multiple industries simultaneously.
- We need to reach **first paying customers within 6 months** of committing to a niche.
- We are based in Argentina and can do **in-person customer discovery** anywhere in the country.
- We have **no external funding** — revenue must come before any significant hiring.

---

## RESEARCH OBJECTIVE

**Do NOT start with a shortlist of niches.** Instead, systematically discover which Argentine SME industry segments are the best candidates for a vertical SaaS ERP built on our platform.

Your goal is to identify and recommend **the single best niche** for us to pursue over the next 2 years. The research should flow in three phases:

1. **PHASE 1 — Market Landscape Scan**: Survey the Argentine SME landscape to identify candidate niches
2. **PHASE 2 — Deep Dive**: Research the top 5-7 candidates in depth
3. **PHASE 3 — Comparative Analysis & Recommendation**: Score, compare, and recommend one niche

Use real data where possible (cite sources). When exact data is unavailable for Argentina, use Latin American proxies and flag them.

---

## PHASE 1: MARKET LANDSCAPE SCAN

Objective: Cast a wide net across Argentine SME sectors to identify **10-15 candidate niches** that could benefit from a vertical SaaS ERP with our platform capabilities.

### 1.1 — Industry Sector Survey

Research the Argentine SME landscape and identify industry sectors where:

1. **Businesses are numerous enough** to sustain a SaaS business (ideally >2,000 establishments in the target segment)
2. **Current software is weak** — the sector is dominated by desktop legacy software, Excel/WhatsApp workflows, or expensive enterprise tools with no affordable mid-market alternative
3. **Regulatory requirements create switching costs** — ARCA, SENASA, ANMAT, RUCA, or other government agencies mandate electronic documents, traceability, or reporting that create a compliance moat
4. **Our existing modules map naturally** — the sector needs inventory + sales + invoicing + some form of offline/field operation (i.e., our platform covers a significant chunk of the business need)
5. **Willingness to pay** — the sector can afford $100-2,000 USD/month for management software

Consider (but do not limit yourself to) these economic sectors:
- Agriculture and agroindustry (not just farming — processing, storage, distribution, inputs)
- Food and beverage value chain (production, distribution, wholesale, retail)
- Construction materials and supplies
- Meat, dairy, and cold chain
- Wholesale and distribution (any vertical)
- Health and pharmaceuticals (farmacias, droguerías, laboratorios)
- Automotive parts and accessories
- Industrial supplies and manufacturing inputs
- Fishing and seafood
- Wine and beverage production
- Textile and garment manufacturing
- Veterinary and animal health
- Waste management and recycling
- Logistics and freight
- Any other sector you discover during research

### 1.2 — Platform Fit Filter

For each candidate niche discovered in 1.1, quickly assess:

| Filter Criterion | Question |
|-----------------|----------|
| **TAM** | How many businesses operate in this segment in Argentina? |
| **Software gap** | What do they currently use? Is it modern cloud SaaS, legacy desktop, or nothing? |
| **Regulatory moat** | Does the sector have mandatory electronic compliance beyond standard ARCA invoicing? |
| **Platform reuse** | What percentage of our existing modules (auth, inventory, sales, ARCA, sync, encryption, customization) would this niche actually use? |
| **Offline relevance** | Does this niche have field/mobile/disconnected operations where offline-first sync is a real advantage? |
| **ARPU estimate** | What would businesses in this niche realistically pay per month for a vertical SaaS tool? |
| **GTM access** | Is there a clear trade association, trade show, or community where we can reach prospects? |

### 1.3 — Shortlist Output

Based on 1.1 and 1.2, produce a ranked table of 10-15 candidate niches. For each, provide:
- Sector name (in Spanish as used in Argentina)
- Estimated number of businesses
- Current software status (legacy/mixed/modern)
- Key regulatory body beyond ARCA (if any)
- Platform reuse estimate (high/medium/low)
- One-line rationale for inclusion

Then **select the top 5-7** for deep research in Phase 2. Explain why the others were eliminated.

---

## PHASE 2: DEEP DIVE (for top 5-7 candidates from Phase 1)

For each candidate that survived the Phase 1 filter, research the following dimensions in depth. Structure your output as one section per niche.

### 2.1 — Market Size & Structure

1. How many businesses operate in this segment in Argentina? Break down by size if possible (micro <5 employees, small 5-50, medium 50-200). Source INDEC, Ministerio de Producción, sector cámaras, or AFIP registration data.
2. Geographic concentration — which provinces or regions have the highest density?
3. Average annual revenue for a small/medium business in this segment.
4. Typical operational profile: number of employees, number of locations, daily transaction volume, number of SKUs or units managed.
5. Growth trend — is this sector expanding, stable, or declining in Argentina?

### 2.2 — Regulatory Environment

1. What ARCA electronic documents are mandatory for this sector beyond standard invoicing (Facturas A/B/C)? List specific document types, web services, and regulatory resolutions.
2. What sector-specific agencies regulate this industry? (SENASA, ANMAT, RUCA, INAES, ENACOM, provincial agencies, etc.) What electronic systems do they mandate?
3. How frequently do these regulations change? Is the compliance burden increasing or stable?
4. What penalties exist for non-compliance with electronic document requirements?
5. Are there upcoming regulatory changes (announced or anticipated) that would create urgency for software adoption?

### 2.3 — Software Landscape

1. What software solutions currently serve this sector in Argentina? For each: name, year founded, delivery model (desktop/cloud/mobile), pricing if known, known weaknesses, estimated market share.
2. Is there any modern (post-2020), cloud-native, mobile-capable solution specifically targeting this sector in Argentina?
3. What are the most common complaints from business owners about their current software? Search Capterra, Mercadolibre, Facebook groups, sector-specific forums.
4. What is the dominant "non-software" workflow? (Excel, WhatsApp, paper, accountant handles it, etc.)
5. Is there a clear mid-market gap? (Enterprise solutions like SAP too expensive, and small solutions too limited for compliance)

### 2.4 — Customer Acquisition

1. What trade associations (cámaras) represent businesses in this sector? Are they active? Do they organize events?
2. What trade shows or industry events exist where software could be demonstrated?
3. How do businesses in this sector typically discover and buy software? (Direct sales, accountant referral, word of mouth, online search, brand/supplier recommendation)
4. What is the typical software budget? (USD/month)
5. What is the realistic sales cycle length for a new software vendor?
6. Who makes the purchasing decision? (Owner, accountant, operations manager, IT, external consultant)

### 2.5 — Key Operational Pain Points

1. What are the top 3 operational workflows that cause the most friction or financial loss in this sector?
2. Which of these workflows are currently managed with paper, Excel, or WhatsApp?
3. Is there a specific "nightmare scenario" (regulatory penalty, lost inventory, fraud, data loss) that drives software adoption?
4. What is the single most compelling "demo moment" — the feature that would make a prospect say "I need this now"?

### 2.6 — Platform Fit Analysis

Answer these knowing our existing platform capabilities:

1. What percentage of this niche's core ERP needs are covered by our existing modules? List what's covered and what's not.
2. What are the 3-5 **niche-specific modules** that would need to be built from scratch? Estimate complexity (small: <2 weeks, medium: 2-6 weeks, large: 6+ weeks) for each.
3. Which of our Rust acceleration modules would provide measurable value in this niche? Be specific about the workflow.
4. Does our offline-first sync architecture address a real pain point, or is it unnecessary?
5. Does our ARCA invoicing (Facturas A/B/C/M, CAE, CAEA) cover the sector's main compliance need, or are additional AFIP/agency integrations required? If so, what's the integration surface (REST API, SOAP, XML upload, manual portal)?
6. Does our field-level encryption or tenant customization provide a differentiator in this sector?

---

## PHASE 3: COMPARATIVE ANALYSIS & RECOMMENDATION

After completing Phase 2 for all top candidates, produce the following structured comparison.

### 3.1 — Market Attractiveness Scorecard

Score each candidate niche 1-5 on each dimension. Include brief justification for each score.

| Dimension | Niche A | Niche B | Niche C | ... |
|-----------|---------|---------|---------|-----|
| Total Addressable Market (TAM) | | | | |
| ARPU potential (USD/month) | | | | |
| Regulatory switching cost / moat | | | | |
| Underserved by existing software | | | | |
| GTM speed (months to first 10 clients) | | | | |
| Customer concentration risk | | | | |
| Offline-first architecture fit | | | | |
| Existing codebase reuse (%) | | | | |
| Rust acceleration relevance | | | | |
| **TOTAL** | | | | |

> **Scoring notes**:
> - **Existing codebase reuse**: Score 5 = >70% of niche needs are covered by our existing modules; Score 1 = <30% covered, extensive new development required.
> - **Rust acceleration relevance**: Score 5 = heavy computational bottlenecks (batch processing, complex validation, high-volume export) where Rust speedups provide competitive advantage; Score 1 = simple CRUD workflows where acceleration is irrelevant.
> - **Regulatory moat**: Score 5 = mandatory compliance with sector-specific agencies creates high switching costs; Score 1 = only standard ARCA invoicing needed, any competitor can match.

### 3.2 — Regulatory Risk Assessment

For each candidate niche:
- The 1-2 mandatory compliance features that are non-negotiable (without which the software cannot be sold)
- The regulatory body responsible and how frequently they change requirements
- Whether our existing ARCA integration covers the main compliance need or new agency integrations are required

> **Our existing ARCA coverage**: Facturas A/B/C/M (WSFEv1), CAE online, CAEA offline batching, fiscal QR codes, WSAA certificate authentication, CUIT validation, IVA breakdown calculation/validation. Any niche requiring *only* standard ARCA invoicing has zero incremental regulatory work.

### 3.3 — Competitive Landscape Summary

For each candidate niche:
- The dominant incumbent (name, weakness, estimated market share)
- Whether any VC-backed or well-funded startup is attacking this market in Argentina
- The most common "switching trigger" — what makes a customer leave their current solution?

### 3.4 — Go-to-Market Strategy

For each candidate niche:
- The primary acquisition channel for the first 10 customers
- The most powerful demo moment (what feature makes a prospect say "I need this now")
- Whether a freemium, free-trial, or direct-sales model is most viable
- Estimated time from "niche committed" to "first paying customer"

### 3.5 — Build Effort Estimate

For each candidate niche:
- Estimated % of new code needed beyond our platform
- List of niche-specific modules to build, with complexity (small/medium/large)
- Estimated calendar time for 2 developers to reach a sellable MVP for this niche
- Which Rust modules provide the most leverage

### 3.6 — Final Recommendation

Based on all of the above, which **single niche** would you recommend for a 4-person startup (2 developers) as their primary market in Argentina?

Justify with:
- The **3 strongest reasons** for this choice
- The **2 biggest risks** to watch
- The **earliest validation milestone** (what would confirm the bet is correct within 90 days)
- A **suggested first customer profile** (size, location, current software, why they'd switch)

Also provide your **#2 and #3 alternatives** with a brief explanation of why they rank lower but remain viable fallbacks.

---

## RESEARCH GUIDELINES

- **Prioritize Argentine sources**: INDEC, ARCA, SENASA, Bolsa de Cereales de Buenos Aires, Ministerio de Economía, Ministerio de Producción. Use `.gob.ar` domains preferentially.
- **Date filter**: Prioritize sources from 2023 onwards. Argentina's regulatory landscape changes rapidly. The current date is **March 2026**.
- **Flag uncertainty**: If data is estimated or extrapolated, say so explicitly. Distinguish between hard data and informed estimates.
- **Currency**: When citing revenue/pricing, provide both ARS and USD equivalent at the time of the source.
- **Software research**: For competitor software, check: Capterra Latin America, Softonic Argentina, GetApp, Mercadolibre (software category), and social media groups.
- **Depth over breadth**: In Phase 2, it is better to deeply research 5 niches than superficially cover 7.
- **Platform context**: When assessing software gaps and competitive positioning, reference our existing capabilities listed in the CONTEXT section. Do not recommend features we already have as "must-build" items.
- **Vertical SaaS benchmarks**: Where possible, cite successful vertical SaaS plays in other Latin American or emerging markets as comparables (e.g., Treinta for tiendas in LATAM, Nuvemshop for e-commerce, Toast for restaurants in US, Procore for construction, etc.).
- **Be contrarian**: Do not default to the most obvious niches. Some of the best vertical SaaS opportunities are in unglamorous sectors that larger players ignore. Actively search for non-obvious candidates.
- **Challenge assumptions**: If a niche looks perfect on paper but has a hidden structural problem (e.g., extremely price-sensitive customers, entrenched free government software, fragmented beyond reach), flag it.

---

*Updated: 2026-03-01 | Project: GRAVITEA-ERP vertical SaaS pivot analysis (ADR-016) | Team: 4 (2 devs) | Platform: 25 features implemented, 9 Rust modules, 137 API operations*
