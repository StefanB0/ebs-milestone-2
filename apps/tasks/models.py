import logging
import math

from django.db import models
from django.db.models import Sum
from apps.users.models import User

from django.utils import timezone

from apps.tasks.tasks import c_send_mail

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
        if self.user == new_user:
            return "Cannot assign same user"
        self.user = new_user
        self.save()

        c_send_mail.delay([new_user.email], "Task assigned", f"Task [{self.title}] has been assigned to you")
        return None

    def complete_task(self):
        if self.is_completed:
            return "Task already completed"

        self.is_completed = True
        self.save()

        c_send_mail.delay(
            [self.user.email],
            "Task completed",
            f"Task [{self.title}] has been completed",
        )

        comments = Comment.objects.filter(task=self)
        emails = [comment.user.email for comment in comments]
        c_send_mail.delay(
            emails,
            "Task completed",
            f"Task [{self.title}] has been completed",
        )

        return "Task completed successfully"

    def undo_task(self):
        if not self.is_completed:
            return "Task not completed"

        self.is_completed = False
        self.save()

        c_send_mail.delay(
            [self.user.email],
            "Task marked incomplete",
            f"Task [{self.title}] has been marked as incomplete",
        )

        comments = Comment.objects.filter(task=self)
        emails = [comment.user.email for comment in comments]
        c_send_mail.delay(
            emails,
            "Task marked incomplete",
            f"Task [{self.title}] has been marked as incomplete",
        )

        return "Task marked incomplete"

    def start_timer(self):
        try:
            TimeLog.objects.create(task=self, start_time=timezone.now())
        except Exception as e:
            error = str(e)
            return error.split(".")[0]
        return None

    def stop_timer(self):
        time_log = TimeLog.objects.filter(task=self).latest("start_time")
        try:
            time_log.stop()
        except Exception as e:
            error = str(e)
            return error.split(".")[0]
        return None

    def notify_comment(self):
        c_send_mail.delay(
            [self.user.email],
            "Comment added",
            f"Comment added to task [{self.title}]",
        )


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

    def save(self, *args, **kwargs):
        for time_log in TimeLog.objects.filter(task=self.task).exclude(id=self.id):
            if time_log.duration is None:
                raise Exception(
                    f"Task timer is already running. Task_id={self.task.id}:{time_log.task.id}, Target_duration={time_log.duration}"
                )
            if self.duration:
                duration_rounded = math.floor(self.duration.total_seconds())
                self.duration = timezone.timedelta(seconds=duration_rounded)
            if time_log.start_time < self.start_time < time_log.start_time + time_log.duration:
                raise Exception(
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
            raise Exception("TimeLog is already stopped")
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
