import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.tasks.models import Task, Comment

User = get_user_model()


class Command(BaseCommand):
    help = "Populate the database with random comments"

    def add_arguments(self, parser):
        parser.add_argument("comment-nr", type=int)

    def handle(self, *args, **options):
        user_list = User.objects.filter(username__icontains="random")
        if len(user_list) == 0:
            self.stdout.write(self.style.ERROR("No users found. Please create test users first"))
            return

        task_list = Task.objects.filter(title__icontains="random")
        if len(task_list) == 0:
            self.stdout.write(self.style.ERROR("No tasks found. Please create test tasks"))
            return

        self.create_comments(options["comment-nr"], user_list, task_list)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {options['comment-nr']} comments for {len(user_list)} users "
                + f"and {len(task_list)} tasks. "
                + f"Current database size: {Comment.objects.count()} comments, {Task.objects.count()} tasks, "
                + f"{User.objects.count()} users."
            )
        )

    def create_comments(self, comment_nr, user_list, task_list):
        for i in range(0, comment_nr + 1):
            cstr = "random-comment-" + str(i)
            Comment.objects.create(body=cstr, task=random.choice(task_list), user=random.choice(user_list))
            if i % 10 == 0 and i != 0:
                self.stdout.write(self.style.SUCCESS("created comments " + str(i - 9) + ":" + str(i)))
            elif i == comment_nr:
                self.stdout.write(self.style.SUCCESS("created comments " + str(i - (i % 10) + 1) + ":" + str(i)))
