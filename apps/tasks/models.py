import logging
import math

from django.db import models
from django.db.models import Sum
from django.utils import timezone

from django_minio_backend import MinioBackend, iso_date_prefix

from apps.tasks.exceptions import TimeLogError
from apps.tasks.signals import task_assigned, task_complete
from apps.users.models import User


logger = logging.getLogger(__name__)


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_completed = models.BooleanField()

    def __str__(self) -> str:
        return self.title

    @property
    def time_spent(self):
        time_logs = self.get_time_logs().exclude(duration=None)
        time_spent = time_logs.aggregate(Sum("duration"))["duration__sum"]
        return time_spent

    def get_time_logs(self):
        return self.timelog_set.all()

    def assign_user(self, new_user):
        self.user = new_user
        self.save()

        task_assigned.send(sender=self.__class__, user=new_user, task=self)
        return

    def complete_task(self):
        if self.is_completed:
            return "Task already completed"

        self.is_completed = True
        self.save()

        users = User.objects.filter(comment__task=self).distinct()
        users |= User.objects.filter(task=self).distinct()

        task_complete.send(sender=self.__class__, users=users, task=self)

        return "Task completed successfully"

    def undo_task(self):
        if not self.is_completed:
            return "Task not completed"

        self.is_completed = False
        self.save()

        users = User.objects.filter(comment__task=self).distinct()
        users |= User.objects.filter(task=self).distinct()

        task_complete.send(sender=self.__class__, users=users, task=self)

        return "Task marked incomplete"

    def start_timer(self):
        try:
            TimeLog.objects.create(task=self, start_time=timezone.now())
        except TimeLogError as e:
            error = str(e)
            return error.split(".")[0]
        return None

    def stop_timer(self):
        time_log = TimeLog.objects.filter(task=self).latest("start_time")
        try:
            time_log.stop()
        except TimeLogError as e:
            error = str(e)
            return error.split(".")[0]
        return None


class Comment(models.Model):
    body = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.task.title + ": " + self.user.username + ": " + self.body


class TaskAttachment(models.Model):
    file = models.FileField(
        verbose_name="Task Photo",
        storage=MinioBackend(bucket_name="django-media-files-bucket"),
        upload_to=iso_date_prefix,
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.task.title + ": Attachment"


class TimeLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    duration = models.DurationField(blank=True, null=True)

    def __str__(self) -> str:
        return (
            "id="
            + str(self.id)
            + " task="
            + str(self.task.id)
            + " start_time="
            + str(self.start_time)
            + " duration="
            + str(self.duration)
        )

    def save(self, *args, **kwargs):
        for time_log in TimeLog.objects.filter(task=self.task).exclude(id=self.id):
            if time_log.duration is None:
                raise TimeLogError(
                    f"Task timer is already running. Task_id={self.task.id}:{time_log.task.id}, Target_duration={time_log.duration}"
                )
            if self.duration:
                duration_rounded = math.floor(self.duration.total_seconds())
                self.duration = timezone.timedelta(seconds=duration_rounded)
            if time_log.start_time < self.start_time < time_log.start_time + time_log.duration:
                raise TimeLogError(
                    "TimeLog overlaps with another timeLog."
                    + f"Conflict_id={time_log.id}."
                    + f"Task_id={time_log.task.id}:{self.task.id},"
                    + f"Date={time_log.start_time.date()}/{self.start_time.date()},"
                    + f"Start={time_log.start_time.time()}/{self.start_time.time()},"
                    + f"Duration={time_log.duration}/{self.duration}"
                )

        super().save(*args, **kwargs)

    def stop(self):
        if self.duration is not None:
            raise TimeLogError("TimeLog is already stopped")
        self.duration = timezone.now() - self.start_time
        self.save()
        return self.duration

    @staticmethod
    def user_time_last_month(user):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = TimeLog.objects.filter(
            task__user=user, start_time__gte=last_month, start_time__lte=timezone.now()
        ).exclude(duration=None)
        return logs.aggregate(Sum("duration"))["duration__sum"]

    @staticmethod
    def user_top_logs(user: User, limit=20):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = (
            TimeLog.objects.filter(task__user=user, start_time__gte=last_month)
            .exclude(duration=None)
            .order_by("-duration")[:limit]
        )
        return logs
