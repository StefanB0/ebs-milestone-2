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

EXPOSE 8000

ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_PASSWORD=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@admin.com

ENTRYPOINT bash -c " \
  python manage.py migrate --noinput && \
  python manage.py createsuperuser --noinput && \ 
  python manage.py runserver 0.0.0.0:8000"

# CMD [ "python",  "manage.py", "runserver", "0.0.0.0:8000"]

