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

@shared_task
def c_send_mail(to, subject, body):
    # send_mail(
    #     subject,
    #     body,
    #     '<EMAIL>',
    #     to,
    #     fail_silently=False,
    # )
    return 2+2
