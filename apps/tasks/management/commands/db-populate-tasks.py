import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.tasks.models import Task


class Command(BaseCommand):
    help = "Populate the database with random tasks"

    def add_arguments(self, parser):
        parser.add_argument("task-nr", type=int)

    def handle(self, *args, **options):
        user_list = User.objects.filter(username__icontains="random")
        if len(user_list) == 0:
            self.stdout.write(self.style.ERROR("No users found. Please create test users first"))
            return

        self.create_tasks(options["task-nr"], user_list)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {options['task-nr']} tasks for {len(user_list)} users. "
                + f"Current database size: {User.objects.count()} users, {Task.objects.count()} tasks"
            )
        )

    def create_tasks(self, task_nr, user_list):
        for i in range(0, task_nr):
            tstr = "random-task-" + str(i)
            Task.objects.create(
                title=tstr,
                description=tstr + "-description",
                user=random.choice(user_list),
                is_completed=random.choice([True, False]),
            )
            if i % 10 == 0 and i != 0:
                self.stdout.write(self.style.SUCCESS("created tasks " + str(i - 9) + ":" + str(i)))
