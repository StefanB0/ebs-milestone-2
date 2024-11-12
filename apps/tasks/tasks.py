from smtplib import SMTPException
from celery import shared_task
from django.contrib.auth import get_user_model

from django.db.models import Sum, F
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django_minio_backend import MinioBackend

from apps.tasks.models import Task, Attachment
from apps.tasks.serializers import TaskPreviewSerializer

User = get_user_model()


@shared_task
def prune_attachments():
    queryset = Attachment.objects.filter(status=Attachment.PENDING)
    for obj in queryset:
        if not MinioBackend().exists(obj.file.name):
            obj.delete()
        else:
            obj.status = Attachment.READY


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def c_send_mail(self, recipient, subject, message, html_message=None):
    try:
        send_mail(subject, message, None, recipient, fail_silently=False, html_message=html_message)
    except SMTPException as exc:
        raise self.retry(exc=exc)
    return {"success": True, "message": "Email sent!"}


@shared_task
def send_weekly_report():
    subject = "Weekly Report"
    users = User.objects.all()

    for user in users:
        tasks = (
            Task.objects.filter(user=user)
            .annotate(time_all=Sum("timelog__duration"))
            .order_by(F("time_all").desc(nulls_last=True))[:20]
        )
        message_html = render_to_string("tasks/tasks_email.html", {"tasks": tasks})
        serializer = TaskPreviewSerializer(tasks, many=True)
        message = "Top Tasks by time:\n"
        count = 0
        for task in serializer.data:
            count += 1
            message += f"{count}. Id: {task["id"]}, Title: {task["title"]}, Time spent: {task["time_spent"]}\n"
        c_send_mail.delay([user.email], subject, message, message_html)
