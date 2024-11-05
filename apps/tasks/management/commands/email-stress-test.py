import random

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from apps.tasks.tasks import c_send_mail

User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with random comments"

    def add_arguments(self, parser):
        parser.add_argument("email-nr", type=int)

    def handle(self, *args, **options):
        email_nr = options["email-nr"]
        user_list = User.objects.filter(username__icontains="random")
        if len(user_list) == 0:
            self.stdout.write(self.style.ERROR("No users found. Please create test users first"))
            return

        for i in range(email_nr):
            user = random.choice(user_list)
            c_send_mail.delay(
                [user.email],
                f"Email Nr {i}",
                "QWERTY-QWERTY-QWERTY-QWERTY-QWERTY\n"
                + "QWERTY-QWERTY-QWERTY-QWERTY-QWERTY\n"
                + "QWERTY-QWERTY-QWERTY-QWERTY-QWERTY\n"
                + "QWERTY-QWERTY-QWERTY-QWERTY-QWERTY\n"
                + "QWERTY-QWERTY-QWERTY-QWERTY-QWERTY\n",
            )
