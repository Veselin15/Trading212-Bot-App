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

# ── Step 2: ML packages pinned to last versions with SSE2-only PyPI wheels ─────
# xgboost 2.x and lightgbm 4.x embed AVX2 instructions in their PyPI wheels
# (SIGILL / exit 132 on CPUs without AVX — Pentium 4, older Celerons, etc.).
# xgboost 1.7.x and lightgbm 3.3.x were the last releases whose manylinux wheels
# used SSE2-only code paths and run on any x86_64 CPU.
# scikit-learn uses runtime-dispatch numpy so any recent version is fine.
RUN pip install --no-cache-dir --prefix=/install "scikit-learn>=1.3.0"
RUN pip install --no-cache-dir --prefix=/install "xgboost==1.7.6"
RUN pip install --no-cache-dir --prefix=/install "lightgbm==3.3.5"

# pandas-ta: install WITHOUT its declared dependencies so numba/llvmlite are never
# pulled in.  pandas-ta 0.4.x lists numba as a hard dep, but numba requires
# llvmlite whose PyPI wheel embeds an AVX2-compiled LLVM binary that SIGILLs on
# CPUs without AVX (e.g. Pentium 4).  At runtime pandas-ta detects the absence of
# numba and falls back to pure numpy/pandas — all indicators still work, just
# without JIT acceleration.  numpy, pandas and tqdm (its real runtime deps) are
# already installed above.
RUN pip install --no-cache-dir --prefix=/install tqdm \
 && pip install --no-cache-dir --prefix=/install --no-deps --pre "pandas-ta"

# ── Runtime: minimal image for home-server / Watchtower pulls ─────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /install /usr/local
COPY backend/ /app/backend/
COPY Server-App/ /app/Server-App/

# Strip Windows line-endings from the entrypoint and make it executable.
# Delete any stale Python bytecode copied from Windows — a .pyc compiled before
# a name was added to a module causes ImportError even though the .py is correct.
RUN sed -i 's/\r$//' /app/backend/docker-entrypoint.sh \
 && chmod +x /app/backend/docker-entrypoint.sh \
 && find /app -name "*.pyc" -delete \
 && find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
