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

COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

COPY ./config ./config
COPY ./manage.py ./manage.py
COPY ./apps ./apps
COPY ./templates ./templates
COPY ./static ./static

EXPOSE 8000

ENTRYPOINT bash -c " \
    python manage.py migrate --noinput && \
    python manage.py loaddata fixtures/*.json || true && \
    python manage.py collectstatic --no-input || true && \
    gunicorn config.wsgi:application --bind 0.0.0.0:8000"

