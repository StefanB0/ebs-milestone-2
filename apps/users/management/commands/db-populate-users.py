from typing import List

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with random users"

    def add_arguments(self, parser):
        parser.add_argument("user-nr", type=int)

    def handle(self, *args, **options):
        user_nr = options["user-nr"]
        self.create_users(user_nr)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {options['user-nr']} users "
                + f"Current database size: {User.objects.count()} users"
            )
        )

    def create_users(self, user_nr) -> List[User]:
        user_list = []
        for i in range(0, user_nr):
            ustr = "random-user" + str(i)  # random-user42
            if User.objects.filter(username=ustr).exists():
                continue

            user = User.objects.create(
                username=ustr,  # random-user42
                password=make_password("password" + str(i)),  # password42
                email=ustr + "@example.mail.com",  # random-user42@example.mail.com
                first_name=ustr + "first-name",  # random-user42first-name
                last_name=ustr + "last-name",  # random-user42last-name
            )
            user_list.append(user)
            self.stdout.write(self.style.SUCCESS("created user " + str(i + 1)))
        return user_list
