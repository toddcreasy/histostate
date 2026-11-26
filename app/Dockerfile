# Image for the Hugging Face Space. scripts/deploy_space.py stages the build context and uploads it;
# the Space builds this file from that context, not from the repo root.
FROM python:3.14.5-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.11.20 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --group app --no-install-project
COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --group app
COPY app ./app
COPY models ./models

# Spaces run the container as user 1000. Gradio caches examples in /app/.gradio on Spaces,
# so /app must be writable by that user.
RUN useradd -m -u 1000 user && chown user /app
USER user

ENV PATH="/app/.venv/bin:$PATH" GRADIO_SERVER_NAME=0.0.0.0 GRADIO_SERVER_PORT=7860
EXPOSE 7860
CMD ["python", "app/app.py"]
