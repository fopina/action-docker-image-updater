FROM python:3.14-alpine AS base

# --- builder
FROM base AS builder
WORKDIR /app
WORKDIR /

COPY Pipfile.lock .
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

# --- tests

FROM builder AS tests

RUN pipenv requirements --dev > requirements.txt
RUN pip install --target=/app -r requirements.txt

ENV PYTHONPATH=/app
WORKDIR /actual
COPY entrypoint.py /actual/entrypoint.py
COPY tests /actual/tests
COPY pyproject.toml /actual/

ENTRYPOINT [ "python", "-m", "pytest", "--cov" ]

# --- main

FROM base
RUN apk add --no-cache git
COPY --from=builder /app /app
ENV PYTHONPATH=/app
COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python3", "-u", "/entrypoint.py"]
