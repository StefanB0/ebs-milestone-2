from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone

# Create your models here.


class Task(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_completed = models.BooleanField()

    def __str__(self) -> str:
        return self.title

    @property
    def time_spent(self):
        time_spent = timezone.timedelta()
        for time_log in self.get_time_logs():
            time_spent += time_log.duration
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
