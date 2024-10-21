from celery import shared_task
from django.core.mail import send_mail


@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)


@shared_task(bind=True, max_retries=5, default_retry_delay=600)
def c_send_mail(self, recipient, subject, message):
    try:
        send_mail(
            subject,
            message,
            None,  # No specific sender
            recipient,  # List of recipient emails
            fail_silently=False,
        )
        return {"success": True, "message": "Email sent!"}
    except Exception as exc:
        # Retry sending the email if an exception occurs
        raise self.retry(exc=exc)
