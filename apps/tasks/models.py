import hashlib
import logging
import math

from datetime import timedelta, date, datetime

from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from django_minio_backend import MinioBackend
from django.conf import settings


from apps.tasks.exceptions import TimeLogError

User = get_user_model()
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
        time_logs = self.timelog_set.all().exclude(duration=None)
        time_spent = time_logs.aggregate(Sum("duration"))["duration__sum"]
        return time_spent

    def assign_user(self, new_user):
        self.user = new_user
        self.save()
        return

    def complete_task(self):
        self.is_completed = True
        self.save()

    def undo_task(self):
        self.is_completed = False
        self.save()

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
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.task.title + ": " + self.user.username + ": " + self.body


class TaskAttachment(models.Model):
    file = models.FileField(
        verbose_name="Task Attachment",
        upload_to="task-attachments/%Y-%m-%d/",  # This controls the upload path
    )
    file_upload_url = models.CharField(max_length=1000)
    task = models.ForeignKey("Task", on_delete=models.CASCADE)
    status = models.CharField(default="pending")

    def save(self, *args, **kwargs):
        if not self.pk:
            client = MinioBackend().client
            today = date.today()
            file_path = f"task-attachments/{today.year}-{today.month}-{today.day}/{self.file.name}"

            # MinioBackend().exists(file_path)
            if TaskAttachment.objects.filter(file=file_path).exists():
                hash_object = hashlib.md5(f"{self.file.name}{datetime.now().isoformat()}".encode())
                hash_suffix = hash_object.hexdigest()[:8]
                path, ext = file_path.rsplit(".", 1)
                file_path = path + "_" + hash_suffix + "." + ext

            self.file = file_path
            self.file_upload_url = client.presigned_put_object(
                bucket_name=settings.MINIO_MEDIA_FILES_BUCKET, object_name=file_path, expires=timedelta(hours=1)
            )

        super().save(*args, **kwargs)

    # def get_put_url(self):
    #     today = date.today()
    #
    #     return MinioBackend().client.presigned_put_object(
    #         bucket_name=settings.MINIO_MEDIA_FILES_BUCKET,
    #         object_name=f"task-attachments/{today.year}-%{today.month}-{today.day}/{self.file.name}",
    #         expires=timedelta(hours=1),
    #     )


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
