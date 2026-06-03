# syntax=docker/dockerfile:1

# ── Builder: compile wheels when needed ───────────────────────────────────────
FROM python:3.12-slim AS builder

# g++ and cmake are required for building lightgbm / xgboost from source.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ cmake make \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/requirements.txt /tmp/backend-requirements.txt

# ── Step 1: install everything except ML packages using pre-built wheels ───────
# lightgbm, xgboost, scikit-learn, and pandas-ta are held back and compiled
# from source below so that AVX2 instructions are not baked in.
RUN grep -vE "^(xgboost|lightgbm|scikit-learn|pandas-ta)" /tmp/backend-requirements.txt \
        > /tmp/base-requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r /tmp/base-requirements.txt \
    && pip install --no-cache-dir --prefix=/install numpy pandas yfinance

# ── Step 2: source-build ML packages with AVX disabled ────────────────────────
# The PyPI wheels for lightgbm ≥ 3 and xgboost ≥ 2 embed AVX2 instructions that
# cause SIGILL (exit 132) on CPUs without AVX support (e.g. Pentium 4, older
# Celerons, many home-server / NAS boards).  Building from source with these
# CFLAGS restricts code generation to SSE2 + SSE3 only, which every x86_64 CPU
# since 2003 supports.
ENV CFLAGS="-O2 -msse2 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2"
ENV CXXFLAGS="-O2 -msse2 -mno-sse4.1 -mno-sse4.2 -mno-avx -mno-avx2"

# scikit-learn (dependency of both xgboost and lightgbm)
RUN pip install --no-cache-dir --prefix=/install \
    --no-binary scikit-learn \
    "scikit-learn>=1.3.0"

# lightgbm — build from source so the AVX2 code paths are never compiled in
RUN pip install --no-cache-dir --prefix=/install \
    --no-binary lightgbm \
    "lightgbm>=4.0.0"

# xgboost — build from source for the same reason
RUN pip install --no-cache-dir --prefix=/install \
    --no-binary xgboost \
    "xgboost>=2.0.0"

# pandas-ta is pure Python + numpy; pin below 0.4.0 to avoid the numba/llvmlite
# dependency that 0.4.x introduced — llvmlite ships an AVX2-compiled LLVM binary
# that SIGILLs on CPUs without AVX support (e.g. Pentium 4, older home servers).
RUN pip install --no-cache-dir --prefix=/install "pandas-ta>=0.3.14b,<0.4.0"

# ── Runtime: minimal image for home-server / Watchtower pulls ─────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local
COPY backend/ /app/backend/
COPY Server-App/ /app/Server-App/

RUN chmod +x /app/backend/docker-entrypoint.sh

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
