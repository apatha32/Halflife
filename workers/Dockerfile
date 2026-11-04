# Build from the repo root: docker build -f workers/Dockerfile .
FROM ghcr.io/astral-sh/uv:0.13.4-python3.12-trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* && useradd --create-home app
WORKDIR /app
COPY workers/pyproject.toml workers/uv.lock workers/.python-version workers/
RUN cd workers && uv sync --frozen --no-dev --no-install-project
COPY workers/src workers/src
COPY models models
RUN cd workers && uv sync --frozen --no-dev && mkdir data && chown -R app /app
USER app
ENV DATA_DIR=/app/data PATH=/app/workers/.venv/bin:$PATH
CMD ["halflife", "--help"]
