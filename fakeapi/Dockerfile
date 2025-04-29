FROM ghcr.io/astral-sh/uv:debian

COPY . /app

WORKDIR /app

RUN uv sync --locked
ENV PATH="/app/.venv/bin:$PATH"

CMD ["fastapi", "run", "main.py", "--port", "80"]
