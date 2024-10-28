from django.dispatch import Signal, receiver

from apps.tasks.tasks import send_mail_wrapper
from apps.users.models import User


# Email signal
task_assigned = Signal()
task_complete = Signal()
task_undo = Signal()
task_comment = Signal()


@receiver(task_assigned)
def task_assigned_handler(sender, **kwargs):
    user = kwargs["user"]
    task = kwargs["task"]
    recipient = [user.email]
    subject = "Task assigned"
    message = f"Task [{task.title}] has been assigned to you"
    send_mail_wrapper(recipient, subject, message)


@receiver(task_complete)
def task_complete_handler(sender, **kwargs):
    task = kwargs["task"]
    users = User.objects.filter(comment__task=task).distinct()
    users |= User.objects.filter(task=task).distinct()

    recipient = [user.email for user in users]
    subject = "Task completed"
    message = f"Task [{task.title}] has been completed"
    send_mail_wrapper(recipient, subject, message)


@receiver(task_undo)
def task_undo_handler(sender, **kwargs):
    task = kwargs["task"]
    users = User.objects.filter(comment__task=task).distinct()
    users |= User.objects.filter(task=task).distinct()

    recipient = [user.email for user in users]
    subject = "Task marked incomplete"
    message = f"Task [{task.title}] has been marked incomplete"
    send_mail_wrapper(recipient, subject, message)


@receiver(task_comment)
def task_comment_handler(sender, **kwargs):
    user = kwargs["user"]
    task = kwargs["task"]
    comment = kwargs["comment"]
    recipient = [user.email]
    subject = "Task comment"
    message = f"Task [{task.title}] has received a comment:\n\t{comment.body}"
    send_mail_wrapper(recipient, subject, message)
