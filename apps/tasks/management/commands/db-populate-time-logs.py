import random
import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.tasks.models import Task, TimeLog


class Command(BaseCommand):
    help = "Populate the database with random time logs"

    def add_arguments(self, parser):
        parser.add_argument("time-log-nr", type=int)

    def handle(self, *args, **options):
        task_list = Task.objects.filter(title__icontains="random")
        if len(task_list) == 0:
            self.stdout.write(self.style.ERROR("No tasks found. Please create some tasks first"))
            return
        self.create_time_logs(options["time-log-nr"], task_list)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {options['time-log-nr']} time logs for {len(task_list)} tasks. "
                + f"Current database size: {TimeLog.objects.count()} time logs, {Task.objects.count()} tasks"
            )
        )

    def create_time_logs(self, time_log_nr, task_list):
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
                TimeLog.objects.create(task=random.choice(task_list), start_time=start_time, duration=duration)
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
