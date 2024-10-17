import logging
import math

from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User

from django.utils import timezone

logger = logging.getLogger("django")


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_completed = models.BooleanField()

    def __str__(self) -> str:  # pragma: no cover # Debug
        return self.title

    @property
    def time_spent(self):
        time_logs = self.get_time_logs().exclude(duration=None)
        time_spent = time_logs.aggregate(Sum("duration"))["duration__sum"]
        if time_spent is None:
            return timezone.timedelta()
        seconds = math.floor(time_spent.total_seconds())
        time_rounded = timezone.timedelta(seconds=seconds)
        return time_rounded

    def get_time_logs(self):
        return TimeLog.objects.filter(task=self)


class Comment(models.Model):
    body = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:  # pragma: no cover # Debug
        return self.task.title + ": " + self.user.username + ": " + self.body


class TimeLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    duration = models.DurationField(blank=True, null=True)

    def __str__(self) -> str:  # pragma: no cover # Debug
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
                raise Exception(
                    f"Task timer is already running. Task_id={self.task.id}:{time_log.task.id}, Target_duration={time_log.duration}"
                )
            if time_log.start_time < self.start_time < time_log.start_time + time_log.duration:
                raise Exception(
                    f"TimeLog overlaps with another TimeLog {time_log.id}."
                    + f"Task_id={time_log.task.id}:{self.task.id},"
                    + f"Date={time_log.start_time.date()}/{self.start_time.date()},"
                    + f"Start={time_log.start_time.time()}/{self.start_time.time()},"
                    + f"Duration={time_log.duration}/{self.duration}"
                )

        super().save(*args, **kwargs)

    def stop(self):
        if self.duration is not None:
            raise Exception("TimeLog is already stopped")
        self.duration = timezone.now() - self.start_time
        self.save()
        duration = timezone.timedelta(seconds=self.duration.total_seconds())
        return duration

    def user_time_last_month(user):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = TimeLog.objects.filter(
            task__user=user, start_time__gte=last_month, start_time__lte=timezone.now()
        ).exclude(duration=None)
        return logs.aggregate(Sum("duration"))["duration__sum"]

    def user_top_logs(user: User, limit=20):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = (
            TimeLog.objects.filter(task__user=user, start_time__gte=last_month)
            .exclude(duration=None)
            .order_by("-duration")[:limit]
        )
        return logs
