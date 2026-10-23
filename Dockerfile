# Runtime image for training on AWS Batch GPU instances. Nextflow runs one training run per container.
# The Linux torch wheels in uv.lock bundle the CUDA libraries; the host AMI supplies the NVIDIA driver.
FROM python:3.14.5-slim-trixie

# Nextflow reads task metrics with ps, which slim images lack.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev
COPY scripts ./scripts

ENV PATH="/app/.venv/bin:$PATH"
