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

Run coverage
```shell
coverage run --source='.' manage.py test && coverage report
```