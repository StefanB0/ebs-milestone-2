from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone


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
        time_spent = sum([time_log.duration for time_log in time_logs], timezone.timedelta())
        return time_spent

    def get_comments(self):
        return Comment.objects.filter(task=self)

    def get_time_logs(self):
        return TimeLog.objects.filter(task=self)


class Comment(models.Model):
    body = models.TextField()
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.task.title + ": " + self.user.username + ": " + self.body


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

    @property
    def end_time(self):
        if self.duration is not None:
            return self.start_time + self.duration
        return None

    def save(self, *args, **kwargs):
        for time_log in TimeLog.objects.filter(task=self.task).exclude(id=self.id):
            if time_log.duration is None:
                raise Exception("Task timer is already running")
            if time_log.start_time < self.start_time and self.start_time < time_log.end_time:
                raise Exception("TimeLog overlaps with another TimeLog")

        super().save(*args, **kwargs)

    def stop(self):
        if self.duration is not None:
            raise Exception("TimeLog is already stopped")
        self.duration = timezone.now() - self.start_time
        self.save()
        return self.duration

    def user_time_last_month(user):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = TimeLog.objects.filter(task__user=user, start_time__gte=last_month, start_time__lte=timezone.now())
        logs = logs.exclude(duration=None)
        return sum([log.duration for log in logs], timezone.timedelta())

    def user_top_logs(user, limit=20):
        last_month = timezone.now() - timezone.timedelta(days=30)
        logs = (
            TimeLog.objects.filter(task__user=user, start_time__gte=last_month)
            .exclude(duration=None)
            .order_by("-duration")[:limit]
        )
        return logs
