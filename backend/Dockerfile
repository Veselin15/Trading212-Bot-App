# ── Builder: install all wheels ───────────────────────────────────────────────
# XGBoost 2.x and LightGBM 4.x PyPI wheels require AVX2. The production home
# server (Ubuntu 26.04, modern x86_64) supports AVX2 and the trained models
# require XGBoost 2.x (pickled with that version — incompatible with 1.7.x).
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY backend/requirements.txt /tmp/backend-requirements.txt

RUN pip install --no-cache-dir --prefix=/install -r /tmp/backend-requirements.txt

# pandas-ta: install WITHOUT its declared dependencies so numba/llvmlite are
# never pulled in. pandas-ta detects the absence of numba at runtime and falls
# back to pure numpy/pandas — all indicators still work.
RUN pip install --no-cache-dir --prefix=/install tqdm \
 && pip install --no-cache-dir --prefix=/install --no-deps --pre "pandas-ta"

# ── Runtime: minimal image ────────────────────────────────────────────────────
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
# Delete any stale Python bytecode copied from Windows.
RUN sed -i 's/\r$//' /app/backend/docker-entrypoint.sh \
 && chmod +x /app/backend/docker-entrypoint.sh \
 && find /app -name "*.pyc" -delete \
 && find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

EXPOSE 8010

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
