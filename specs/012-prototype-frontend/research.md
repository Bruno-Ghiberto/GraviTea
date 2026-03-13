# Research: Prototype Frontend for Backend API Testing

**Branch**: `012-prototype-frontend` | **Date**: 2026-02-17

## Phase 0 Research Summary

No NEEDS CLARIFICATION items existed in the Technical Context — the brainstorming session (pre-specify) resolved all technology decisions. This research.md documents those decisions for traceability.

## Decision 1: Framework — Next.js 15 (App Router)

**Decision**: Next.js 15 with App Router and TypeScript strict mode.

**Rationale**: The prototype needs a React-based framework to share patterns with the planned production frontend. Next.js provides file-based routing (reduces boilerplate), built-in API route support (unused here but useful for future proxy), standalone Docker output mode (small images), and the widest ecosystem compatibility with shadcn/ui. App Router is the current default in Next.js 15.

**Alternatives considered**:
- **Vite + React Router**: Simpler, but lacks built-in routing conventions and standalone Docker output mode. Would require manual setup for features Next.js provides out-of-the-box.
- **Electron**: User's planned production platform, but overkill for a prototype. Adds native packaging complexity without benefit for API testing. The prototype runs in-browser only.
- **Plain HTML + fetch**: Fastest to build but unmaintainable. No component reuse, no type safety, no state management.

## Decision 2: UI Library — shadcn/ui + Tailwind CSS 4

**Decision**: shadcn/ui components with Tailwind CSS 4 for styling.

**Rationale**: shadcn/ui provides copy-paste components (not a dependency — code lives in the project). This means zero version lock-in, full customization, and components that work with Tailwind CSS out-of-the-box. Tailwind CSS 4 is the current stable release with improved performance.

**Alternatives considered**:
- **MUI (Material UI)**: Heavy bundle size (~200KB+), opinionated styling that conflicts with Tailwind, complex theming.
- **Ant Design**: Enterprise-focused but very heavy, Chinese documentation bias, not Tailwind-compatible.
- **Raw Tailwind (no component library)**: Too slow for prototype — we'd rebuild table, dialog, form components from scratch.

## Decision 3: Data Fetching — TanStack Query v5

**Decision**: TanStack Query v5 for server state management.

**Rationale**: Provides automatic caching, background refetching, loading/error states, and mutation support. Eliminates the need for manual `useState`/`useEffect` patterns for API calls. Plays well with the "Load More" cursor pagination pattern (infinite queries).

**Alternatives considered**:
- **SWR**: Simpler but lacks mutation support and infinite query patterns needed for cursor pagination.
- **Plain fetch + useState**: Works but produces repetitive boilerplate across 62 endpoints. Every component would need manual loading/error/data state management.

## Decision 4: Auth Storage — In-Memory Only

**Decision**: JWT tokens stored in React Context (memory only). No localStorage, no sessionStorage, no cookies.

**Rationale**: Spec FR-020 mandates "tokens in memory only — no persistent storage of credentials." React Context provides component-tree access without persistence. Tokens are lost on page refresh (acceptable for a developer testing tool).

**Alternatives considered**:
- **localStorage**: Persists across refreshes but violates FR-020 and is vulnerable to XSS.
- **HttpOnly cookies**: Secure but requires backend proxy setup (adds complexity for a prototype).

## Decision 5: Docker Strategy — Next.js Standalone Output

**Decision**: Multi-stage Dockerfile using Next.js `output: 'standalone'` for minimal image size.

**Rationale**: Standalone output produces a self-contained server without `node_modules`, resulting in images under 200MB (per SC-008). Multi-stage build keeps build tools out of the final image.

## No Further Research Needed

All technology choices are resolved. No external documentation lookup or best-practices research is required — the stack is well-established and the prototype scope is deliberately minimal.
