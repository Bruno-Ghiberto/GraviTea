# Feature Specification: Rust Toolchain Bootstrap

**Feature Branch**: `017-rust-bootstrap`
**Created**: 2026-02-25
**Status**: Draft
**Input**: Bootstrap the Rust/PyO3/Maturin build toolchain as a foundation layer for accelerating CPU-bound backend operations. This spec delivers zero business logic — only infrastructure that enables 8 subsequent Rust acceleration specs (SPEC-018 through SPEC-025).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Builds and Imports the Rust Extension (Priority: P1)

A backend developer runs a single build command and immediately imports the compiled Rust extension module into their Python environment. The developer receives confirmation that the Rust-to-Python bridge is functional through a hello-world function call, proving the entire toolchain pipeline works end-to-end.

**Why this priority**: Without a working build-and-import pipeline, no subsequent Rust acceleration feature can be developed. This is the single gating dependency for the entire Rust initiative.

**Independent Test**: Can be fully tested by running the build command in a local development environment and calling the hello function from Python. Delivers immediate value by confirming the PyO3 bridge is functional.

**Acceptance Scenarios**:

1. **Given** a developer has the Rust toolchain and Maturin installed, **When** they run the build command from the Rust project directory, **Then** a Python-compatible extension module is produced and installed into the active virtual environment within 60 seconds.
2. **Given** the Rust extension is installed in the Python environment, **When** a Python script imports the extension module and calls the hello function, **Then** it receives the expected string response without errors.
3. **Given** the Rust extension is installed, **When** the developer runs the existing backend test suite, **Then** all pre-existing tests continue to pass with zero regressions.

---

### User Story 2 - Backend Runs Without the Rust Extension Installed (Priority: P1)

A backend developer or deployment environment that does not have the Rust toolchain installed can still run the Django backend normally. The system gracefully detects the absence of the Rust extension and continues operating using pure Python implementations.

**Why this priority**: The fallback pattern is a foundational architectural decision. If the Rust extension becomes a hard dependency, it breaks all existing development workflows, CI pipelines, and deployment environments that haven't adopted Rust yet.

**Independent Test**: Can be tested by deliberately uninstalling or never installing the Rust extension, then starting the Django server and running the test suite. The backend must function identically.

**Acceptance Scenarios**:

1. **Given** the Rust extension is NOT installed in the Python environment, **When** a Python module attempts to import it using the standard fallback pattern, **Then** the import failure is silently caught and a fallback flag is set to indicate Rust is unavailable.
2. **Given** the fallback flag indicates Rust is unavailable, **When** any accelerated function is called, **Then** the pure Python implementation executes instead, producing identical results.
3. **Given** the Rust extension was previously installed and is then removed, **When** the backend restarts, **Then** it detects the absence and falls back gracefully without errors or warnings in standard operation logs.

---

### User Story 3 - Docker Image Includes the Compiled Rust Extension (Priority: P2)

A DevOps engineer builds the Docker production image. The build process compiles the Rust source code, packages it into a Python wheel, and installs it into the runtime container — all within the existing Docker build pipeline. The final image does not contain the Rust compiler, only the compiled extension.

**Why this priority**: Docker is the production deployment mechanism. Without Docker integration, the Rust extension only works in local development. However, this can follow the local build pipeline since Docker is a packaging concern.

**Independent Test**: Can be tested by running the Docker build command and then executing the hello function inside the running container. The production image size should not increase by more than 15 MB from the compiled extension.

**Acceptance Scenarios**:

1. **Given** the Docker build configuration includes the Rust builder stage, **When** the full Docker image is built, **Then** the build completes successfully and the Rust extension is available inside the container.
2. **Given** a running Docker container from the built image, **When** a Python script inside the container imports the Rust extension, **Then** the import succeeds and the hello function returns the expected response.
3. **Given** the Docker build configuration includes dependency caching, **When** only Rust source code changes (not dependencies), **Then** the rebuild completes in under 60 seconds by reusing cached dependency compilation.
4. **Given** the existing Docker services (database, cache, backend), **When** the updated Docker configuration is deployed, **Then** all existing services start and operate normally with zero configuration changes required.

---

### User Story 4 - Developer Receives Autocomplete for Rust Functions (Priority: P3)

A backend developer opens their IDE and begins writing Python code that calls Rust functions. The IDE provides type hints, argument suggestions, and return type information for all functions exposed by the Rust extension, improving developer experience and reducing errors.

**Why this priority**: Type stubs improve developer ergonomics but are not required for the extension to function. This can be added after the core pipeline works.

**Independent Test**: Can be tested by opening a Python file in an IDE with type checking enabled and verifying that the Rust extension's functions show correct type information.

**Acceptance Scenarios**:

1. **Given** the type stub file exists alongside the Rust extension, **When** a developer imports the extension in their IDE, **Then** the IDE displays the hello function with its return type annotation.
2. **Given** the type stub declares function signatures, **When** a static type checker validates code that calls the Rust extension, **Then** no type errors are reported for correct usage.

---

### User Story 5 - Shared Error Mapping Provides Consistent Python Exceptions (Priority: P2)

When future Rust functions encounter errors (invalid input, cryptographic failures, I/O errors), they raise standard Python exceptions that the Django backend can catch and handle using existing error handling patterns. The error mapping is defined once in a shared module and reused by all subsequent Rust acceleration specs.

**Why this priority**: The error mapping establishes the convention for all future Rust code. Getting it right in the bootstrap spec prevents inconsistent error handling across 8 subsequent specs.

**Independent Test**: Can be tested by calling Rust functions with deliberately invalid inputs and verifying the correct Python exception type is raised with a meaningful error message.

**Acceptance Scenarios**:

1. **Given** a Rust function receives invalid input, **When** it returns an error, **Then** Python receives a ValueError with a descriptive message.
2. **Given** a Rust function encounters an internal processing error, **When** it returns an error, **Then** Python receives a RuntimeError with a descriptive message.
3. **Given** a Rust function encounters a file system error, **When** it returns an error, **Then** Python receives an IOError with a descriptive message.

---

### Edge Cases

- What happens when the Rust extension is compiled for a different Python version than the one running? The import should fail with a clear error message from Python's extension module loader, triggering the fallback pattern.
- What happens when the Rust extension is compiled for Linux but attempted to load on Windows (or vice versa)? The import should fail gracefully, triggering the fallback pattern.
- What happens when the Docker build runs on a different CPU architecture (ARM vs x86_64)? The Rust builder stage must compile for the target architecture of the runtime image.
- What happens when the dependency lock file is out of sync with the dependency manifest? The build should fail fast with a clear error, rather than producing a subtly broken wheel.
- What happens when the developer has an outdated build tool version? The build configuration version constraint should cause the build to fail with a version mismatch error.
- What happens when the Rust source has a compilation error? The build command should surface the compiler error message directly to the developer, not wrap it in an opaque build error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a Rust project structure within the repository that compiles into a Python-importable extension module.
- **FR-002**: System MUST include a build configuration that produces a shared library compatible with the project's Python version (3.12+).
- **FR-003**: System MUST include a build backend configuration that enables building distributable wheels.
- **FR-004**: System MUST expose at least one trivial function (hello) from Rust to Python that returns a known string, proving the full pipeline works.
- **FR-005**: System MUST include a shared error mapping module that converts Rust error types to standard Python exceptions (ValueError, RuntimeError, IOError).
- **FR-006**: System MUST provide a type stub file that declares the public API of the Rust extension for IDE autocomplete and static analysis.
- **FR-007**: System MUST establish a Python fallback pattern where the Rust extension is an optional import — the backend functions identically without it installed.
- **FR-008**: System MUST integrate the Rust compilation into the Docker build pipeline as a separate builder stage that produces a wheel, without including the Rust compiler in the final runtime image.
- **FR-009**: System MUST implement Docker dependency caching so that dependency compilation is cached separately from source compilation, reducing incremental build times.
- **FR-010**: System MUST commit the dependency lock file to version control for reproducible builds across all environments.
- **FR-011**: System MUST include at least one Rust-native test that validates the hello function and error mapping without requiring Python.
- **FR-012**: System MUST include at least one Python integration test that validates importing the Rust extension and calling the hello function.
- **FR-013**: System MUST ensure all existing backend tests continue to pass after the Rust toolchain is added (zero regressions).
- **FR-014**: System MUST document the developer workflow for building, testing, and iterating on Rust code within the project.

### Key Entities

- **Rust Extension Module**: The compiled shared library (gravitea_rust) that exposes Rust functions to Python via bindings. It is the primary artifact produced by the build pipeline.
- **Build Configuration**: The set of configuration files that define how the Rust source is compiled, linked, and packaged into a distributable wheel.
- **Error Mapping**: A shared Rust module that defines a structured error type and converts each variant to the appropriate Python exception type.
- **Type Stub**: A Python interface declaration file that describes the public API of the Rust extension for use by IDEs and static type checkers.
- **Docker Builder Stage**: A build stage in the Docker multi-stage pipeline that compiles Rust source into a wheel, separate from the Python runtime stage.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can build and import the Rust extension in under 60 seconds on first build, and under 30 seconds on subsequent builds with cached dependencies.
- **SC-002**: The hello function called from Python returns the expected greeting string with 100% reliability across 1000 consecutive calls.
- **SC-003**: The backend starts and serves requests identically whether the Rust extension is installed or not — zero behavioral difference for existing functionality.
- **SC-004**: The Docker image builds successfully with the Rust builder stage, and the final runtime image size increases by no more than 15 MB from the compiled extension.
- **SC-005**: All pre-existing backend tests (2,200+) continue to pass after the Rust toolchain is added, with zero regressions.
- **SC-006**: Incremental Docker builds (source change only, dependencies unchanged) complete in under 60 seconds by leveraging dependency caching.
- **SC-007**: The Rust-native test suite passes with at least 3 test cases covering: hello function, error mapping to Python exceptions, and module initialization.
- **SC-008**: The Python integration test suite passes with at least 2 test cases covering: successful import with function call, and graceful fallback when extension is unavailable.
- **SC-009**: The type stub file enables IDE autocomplete — a static type checker reports zero errors when the extension's public API is used correctly.
- **SC-010**: Developer documentation covers the complete workflow (install toolchain, build, test, iterate) in a single page readable in under 5 minutes.

## Assumptions

- Developers who need to modify Rust code will install the Rust toolchain. Developers who only work on Python code do not need Rust installed — the fallback pattern handles this.
- Rust compilation on Windows uses WSL2. Direct Windows compilation is not required for this spec — Docker and WSL2 produce Linux binaries which is the deployment target.
- The Rust project starts as a single crate. Future specs may split into multiple crates if the codebase grows, but that decision is deferred.
- The build tool versions (PyO3 0.28+, Maturin 1.12+) are stable and compatible with the target Python version (3.12+).
- The development environment uses Docker Desktop with WSL2 integration for container builds.
- CI pipeline configuration is optional in this spec. If not configured, it will be addressed in a follow-up.

## Scope Boundaries

### In Scope

- Rust project structure and build configuration
- Module entry point with hello function
- Shared error mapping (Rust errors to Python exceptions)
- Python type stub
- Python fallback pattern (try/except import convention)
- Docker multi-stage build integration with dependency caching
- Rust-native tests
- Python integration tests
- Developer workflow documentation

### Out of Scope

- Any business logic in Rust (crypto, fiscal compute, export, observability, SSRF, sync, ARCA batch, custom fields)
- Modifications to any existing Python module (the fallback pattern is demonstrated but not wired in)
- Frontend changes
- Performance benchmarks or benchmark framework setup
- Multi-platform wheel distribution (Windows, macOS)
- Free-threaded Python support
- Multiple Rust crates / Cargo workspace
- Blueprint document updates
- Constitution amendments
