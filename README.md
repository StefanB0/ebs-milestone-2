# ebs-milestone-2

## Developer guide

Build image

```sh
docker build -t ebs-milestone-2 .
```

Run container interactive mode

```sh
docker run --rm -it ebs-milestone-2 bash
```

Run container as server 

```sh
docker run --rm -it -p 8000:8000 ebs-milestone-2
```

Run docker compose

```shell
docker compose up -d --build --wait
```

Start celery
```shell
docker run -d -p 5672:5672 rabbitmq
celery -A config worker -l INFO --pool=solo
```

## Testing

Run Tests, before running tests be sure to start celery and the rabbitmq container from docker compose.
```shell
docker compose up -d mailhog-mock rabbitmq-broker minio
celery -A config worker -l INFO --pool=solo
```

```shell
python manage.py test
```

Run coverage
```shell
coverage run --source='.' manage.py test && coverage report
coverage run --source='.' manage.py test && coverage html
```