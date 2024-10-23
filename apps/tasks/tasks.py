from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


def send_mail_wrapper(recipient, subject, message):
    if settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
        c_send_mail.delay(recipient, subject, message)
    else:
        send_mail(subject, message,None, recipient,fail_silently=False)

@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def c_send_mail(self, recipient, subject, message):
    try:
        send_mail(subject, message,None, recipient,fail_silently=False)
    except SMTPException as exc:
        raise self.retry(exc=exc)
    return {"success": True, "message": "Email sent!"}
