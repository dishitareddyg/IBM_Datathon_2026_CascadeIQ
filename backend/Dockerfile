# ---------------------------------------------------------------------------
# CascadeIQ Backend – Dockerfile
# ---------------------------------------------------------------------------
# Multi-stage build for a lean production image.
#
# Compatibility
# -------------
# • Development laptops (x86_64 / arm64)
# • Red Hat OpenShift on IBM LinuxONE (s390x)
#   – Uses python:3.11-slim which is available for s390x from Docker Hub.
#   – Runs as non-root user (UID 1001) for OpenShift compatibility.
#   – No hard-coded UIDs to avoid conflicts with OpenShift arbitrary-UID policy.
#
# Build
# -----
#   docker build -t cascadeiq-backend .
#
# Run
# ---
#   docker run -p 8000:8000 --env-file .env cascadeiq-backend
# ---------------------------------------------------------------------------

# ---- Builder stage --------------------------------------------------------
FROM python:3.11-slim AS builder

# System packages required by geopandas / osmnx (GDAL, libspatialindex)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgdal-dev \
        libspatialindex-dev \
        libgeos-dev \
        libproj-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python dependencies into a prefix we can copy later
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Runtime stage --------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime system libraries (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal32 \
        libspatialindex7 \
        libgeos-c1v5 \
        libproj25 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create a non-root user that also works under OpenShift arbitrary-UID policy.
# OpenShift ignores the UID in the image and assigns one from the project
# namespace range, so we grant group write permissions to /app instead.
RUN groupadd -r cascadeiq && \
    useradd -r -g cascadeiq -u 1001 cascadeiq && \
    mkdir -p /app && \
    chown -R cascadeiq:cascadeiq /app

WORKDIR /app

# Copy application source
COPY --chown=cascadeiq:cascadeiq . .

# OpenShift requires directories to be group-writable (arbitrary UID)
RUN chmod -R g=u /app

USER 1001

EXPOSE 8000

# Health check – polls the /health endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the server
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
