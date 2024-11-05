FROM python:3.12 AS build

WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create true
RUN poetry config virtualenvs.in-project true

COPY pyproject.toml /app/pyproject.toml
COPY poetry.lock /app/poetry.lock

RUN poetry install --only=main

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY ./config ./config
COPY ./manage.py ./manage.py
COPY ./apps ./apps
COPY ./templates ./templates
COPY ./static ./static

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=5s --retries=30 CMD curl -f http://localhost:8000/common/health || exit 1

ENTRYPOINT bash -c " \
    python manage.py migrate --noinput && \
    python manage.py collectstatic --no-input || true && \
    python manage.py search_index --rebuild -f || true && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000"

