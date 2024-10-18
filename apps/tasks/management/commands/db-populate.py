import random
import datetime
from typing import List

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.tasks.models import Task, Comment, TimeLog


class Command(BaseCommand):
    help = "Populate the database with random data"

    def add_arguments(self, parser):
        parser.add_argument("task-nr", type=int)
        parser.add_argument("comment-nr", type=int)
        parser.add_argument("time-log-nr", type=int)

    def handle(self, *args, **options):
        user_nr = min(options["task-nr"], 10)
        user_list = self.create_users(user_nr)
        self.create_tasks(options["task-nr"], user_list)
        self.create_comments(options["comment-nr"], user_list)
        self.create_time_logs(options["time-log-nr"])

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {options['task-nr']} tasks, {options['comment-nr']} comments and \
{options['time-log-nr']} time logs for {user_nr} users. Current database size: {User.objects.count()} \
users, {Task.objects.count()} tasks, {Comment.objects.count()} comments, {TimeLog.objects.count()} time logs")
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

    def create_comments(self, comment_nr, user_list):
        tasks = Task.objects.all()
        for i in range(0, comment_nr):
            cstr = "random-comment-" + str(i)
            Comment.objects.create(body=cstr, task=random.choice(tasks), user=random.choice(user_list))
            if i % 10 == 0 and i != 0:
                self.stdout.write(self.style.SUCCESS("created comments " + str(i - 9) + ":" + str(i)))

    def create_time_logs(self, time_log_nr):
        tasks = Task.objects.all()
        start_time_base = timezone.now() - timezone.timedelta(days=40)
        # set start_time_base to the beginning of the month
        start_time_base = timezone.datetime(
            start_time_base.year, start_time_base.month, start_time_base.day, 0, 0, 0, 0, start_time_base.tzinfo
        )

        random.seed(datetime.datetime.now().timestamp())
        failed_logs = 0
        counter = 0
        while time_log_nr > 0:
            day = random.randint(0, 40)
            hour = random.randint(8, 20)
            minute = random.randint(0, 12) * 5
            offset = timezone.timedelta(days=day, hours=hour, minutes=minute)
            start_time = start_time_base + offset
            duration = timezone.timedelta(minutes=random.randint(5, 120))

            try:
                TimeLog.objects.create(task=random.choice(tasks), start_time=start_time, duration=duration)
            except Exception:
                # self.stdout.write(
                #     self.style.ERROR("Failed to create time log " + str(time_log_nr) + " because {" + e.__str__() + "}")
                # )
                failed_logs += 1
            else:
                time_log_nr -= 1
                counter += 1
                if counter % 10 == 0:
                    self.stdout.write(
                        self.style.SUCCESS("Successfully created time logs " + str(counter - 9) + ":" + str(counter))
                    )

        self.stdout.write(self.style.ERROR(f"Failed to make {failed_logs} time logs because of time overlap"))
