from smtplib import SMTPException

from django.core.mail import send_mail
from django.conf import settings

from celery import shared_task
from celery.schedules import crontab

from apps.tasks.models import Task
from apps.tasks.serializers import TaskPreviewSerializer
from apps.users.models import User
from config.celery import app


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every Monday morning at 7:30 a.m UTC.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1), send_weekly_report.s(), name="Weekly Task Report"
    )


def send_mail_wrapper(recipient, subject, message):
    if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
        c_send_mail.delay(recipient, subject, message)
    else:
        send_mail(subject, message, None, recipient, fail_silently=False)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def c_send_mail(self, recipient, subject, message):
    try:
        send_mail(subject, message, None, recipient, fail_silently=False)
    except SMTPException as exc:
        raise self.retry(exc=exc)
    return {"success": True, "message": "Email sent!"}


@shared_task
def send_weekly_report():
    subject = "Weekly Report"
    users = User.objects.all()

    for user in users:
        tasks = Task.objects.filter(user=user).order_by("timelog__duration")[:20]
        serializer = TaskPreviewSerializer(tasks, many=True)
        message = "Top Tasks by time:\n"
        count = 0
        for task in serializer.data:
            count += 1
            message += f"{count}. Id: {task["id"]}, Title: {task["title"]}, Time spent: {task["time_spent"]}\n"
        send_mail_wrapper([user.email], subject, message)
