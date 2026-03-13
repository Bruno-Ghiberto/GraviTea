# ============================================================
# Stage 0: Rust builder — compiles gravitea-core extension
#
# NOTE: We use python:3.14.3-slim as the Rust builder base (not rust:1.85-slim-bookworm)
# because python:3.14.3-slim requires glibc >= 2.38 (Debian Trixie), while
# rust:1.85-slim-bookworm only has glibc 2.36 (Debian Bookworm). Using the
# Python image as the base ensures the compiled wheel targets cp314 and shares
# the same glibc as the runtime image.
# Rust 1.85 is installed via rustup with predictable CARGO_HOME/RUSTUP_HOME paths.
# ============================================================
FROM python:3.14.3-slim AS rust-builder

WORKDIR /build

# Install build tools for Rust compilation
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust 1.85 via rustup (minimal profile — no docs, no clippy)
# Use stable paths for CARGO_HOME and RUSTUP_HOME
ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain 1.85 --no-modify-path
ENV PATH="/usr/local/cargo/bin:${PATH}"

# Install maturin via Python 3.14's pip (pre-built wheel ~5s, not cargo install ~5min)
RUN pip install --no-cache-dir maturin==1.12.4

# Dependency caching layer:
#   Copy Cargo manifests + pyproject.toml first, then build with a minimal dummy source.
#   This layer is cached as long as Cargo.toml/Cargo.lock do not change.
COPY rust/gravitea-core/Cargo.toml rust/gravitea-core/Cargo.lock rust/gravitea-core/pyproject.toml ./
RUN mkdir src && echo 'use pyo3::prelude::*; #[pymodule] fn gravitea_rust(_m: &Bound<'"'"'_, PyModule>) -> PyResult<()> { Ok(()) }' > src/lib.rs
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/build/target,sharing=locked \
    cargo build --release --lib 2>/dev/null || true

# Build real source (fast — dependencies already compiled via cache mount)
RUN rm -rf src
COPY rust/gravitea-core/src ./src
RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/build/target,sharing=locked \
    maturin build --release --out /wheels

# ============================================================
# Stage 1: Python builder — installs Python dependencies
# ============================================================
FROM python:3.14.3-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# NOTE: build context is repo root — paths prefixed with backend/
COPY backend/requirements/base.txt backend/requirements/production.txt requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

# ============================================================
# Stage 2: Production runtime
# ============================================================
FROM python:3.14.3-slim

WORKDIR /app

# Install runtime dependencies (postgresql-client provides pg_isready + psql for bootstrap.sh)
RUN apt-get update && apt-get install -y \
    libpq5 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from Python builder
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Install compiled Rust extension wheel (the Rust compiler is NOT in this stage)
COPY --from=rust-builder /wheels/*.whl /tmp/wheels/
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Create non-root user and staticfiles directory
RUN useradd --create-home appuser && \
    mkdir -p /app/staticfiles && \
    chown -R appuser:appuser /app

# Copy application code
# NOTE: build context is repo root — copy backend/ contents into /app/
COPY --chown=appuser:appuser backend/ .

# Fix CRLF line endings from Windows and make executable
RUN sed -i 's/\r$//' scripts/bootstrap.sh && chmod +x scripts/bootstrap.sh

# Switch to non-root user
USER appuser

# Set environment for build (production settings don't require django_extensions)
ENV DJANGO_SETTINGS_MODULE=gravitea.settings.production
ENV SECRET_KEY=build-time-secret-key-only

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8080

# Health check (uses /health/live for liveness probe)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health/live')" || exit 1

# Bootstrap: wait-for-db → SQL init → migrate → exec CMD (R6)
# Strip Windows CRLF at runtime (volume mounts can reintroduce \r from host)
ENTRYPOINT ["/bin/bash", "-c", "sed -i 's/\\r$//' scripts/bootstrap.sh && exec bash scripts/bootstrap.sh \"$@\"", "--"]

# Default command (overridden by docker-compose for dev)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "gravitea.wsgi:application"]
