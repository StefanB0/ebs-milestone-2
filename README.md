# ebs-milestone-2

## Local dev

1. Install pipx `python -m pip install --user pipx`

2. Create virtual environment `python -m venv .venv`

3. Activate virtual environment (On windows) `source .venv/Scripts/activate`

4. Install poetry `pipx install poetry`

5. Install dependencies `poetry install`

6. Install pre-commit hooks `pre-commit install`

## Docker

1. Build image `docker build -t ebs-milestone-2 .`

2. Run docker compose `docker compose up -d --build --wait`


## Testing

Start celery 

```shell
docker compose up -d --build celery
```

Run tests locally (some are skipped)
```shell
python manage.py test
```

Run tests in docker.
```shell
docker compose up -d --build --wait
```

```shell
docker compose exec app python manage.py test
```

Run coverage
```shell
coverage run --source='.' manage.py test && coverage report
```

```shell
coverage run --source='.' manage.py test && coverage html
```
