FROM python:3.13-alpine AS base

# --- builder
FROM base AS builder
WORKDIR /app
WORKDIR /

COPY Pipfile.lock .
RUN pip install pipenv
RUN pipenv requirements > requirements.txt
RUN pip install --target=/app -r requirements.txt

# --- main

FROM base
RUN apk add --no-cache git
COPY --from=builder /app /app
ENV PYTHONPATH=/app
COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python3", "-u", "/entrypoint.py"]
