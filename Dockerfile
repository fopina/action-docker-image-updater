FROM python:3.15.2-alpine AS base
RUN pip install --no-cache-dir uv

# --- builder
FROM base AS builder
WORKDIR /src
COPY pyproject.toml uv.lock README.md ./
COPY entrypoint.py ./
RUN uv pip install --system --target=/app .

# --- tests

FROM builder AS tests

RUN uv sync --dev

ENV PYTHONPATH=/app
WORKDIR /actual
COPY entrypoint.py /actual/entrypoint.py
COPY tests /actual/tests
COPY pyproject.toml /actual/

ENTRYPOINT [ "uv", "run", "--project", "/src", "python", "-m", "pytest", "--cov" ]

# --- main

FROM base
RUN apk add --no-cache git
COPY --from=builder /app /app
ENV PYTHONPATH=/app
COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python3", "-u", "/entrypoint.py"]
