import json

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Populate the database with random users"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("password", type=str)
        parser.add_argument("is_admin", type=bool)

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        is_admin = options["is_admin"]
        user_email = username + "@email.com"

        user = {
            "username": username,
            "password": password,
            "email": user_email,
            "is_admin": is_admin,
        }

        self.print_user_json(user)

    @staticmethod
    def print_user_json(user):
        user_json = {
            "model": "users.user",
            "pk": 0,
            "fields": {
                "email": user["email"],
                "first_name": user["username"],
                "last_name": user["username"],
                "username": user["username"],
                "is_superuser": user["is_admin"],
                "is_staff": user["is_admin"],
                "password": make_password(user["password"]),
            },
        }

        print(json.dumps(user_json, indent=4))