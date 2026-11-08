# Build from the repo root: docker build -f workers/Dockerfile .
FROM ghcr.io/astral-sh/uv:0.13.4-python3.12-trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* && useradd --create-home app \
    && mkdir -p /app/data && chown app /app /app/data
USER app
WORKDIR /app
ENV UV_NO_CACHE=1 UV_COMPILE_BYTECODE=1 DATA_DIR=/app/data PATH=/app/workers/.venv/bin:$PATH
COPY --chown=app workers/pyproject.toml workers/uv.lock workers/.python-version workers/
RUN cd workers && uv sync --frozen --no-dev --no-install-project
COPY --chown=app workers/src workers/src
COPY --chown=app models models
RUN cd workers && uv sync --frozen --no-dev
CMD ["halflife", "--help"]
