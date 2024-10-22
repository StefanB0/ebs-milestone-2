from celery import shared_task
from django.core.mail import send_mail

@shared_task(bind=True, max_retries=5, default_retry_delay=600)
def c_send_mail(self, recipient, subject, message):
    send_mail(
        subject,
        message,
        None,
        recipient,
        fail_silently=False,
    )
    return {"success": True, "message": "Email sent!"}