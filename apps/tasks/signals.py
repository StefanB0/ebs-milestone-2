import datetime

from django.dispatch import Signal, receiver
from django.db.models.signals import post_save

from elasticsearch_dsl import connections

from config.settings import ELASTICSEARCH_DSL_HOST
from apps.tasks.documents import TaskDocument
from apps.tasks.models import Task, Comment
from apps.tasks.serializers import TaskSerializer, CommentSerializer
from apps.tasks.tasks import send_mail_wrapper
from apps.users.models import User

# Email signal
task_assigned = Signal()
task_complete = Signal()
task_undo = Signal()
task_comment = Signal()

connections.create_connection(hosts=ELASTICSEARCH_DSL_HOST)


@receiver(post_save, sender=Task)
def task_elasticsearch_handler(sender, instance, created, **kwargs):
    serializer = TaskSerializer(instance)
    task_data = serializer.data

    time_spent = 0
    if task_data["time_spent"]:
        time_string = task_data["time_spent"]
        time_datetime = datetime.datetime.strptime(time_string, "%H:%M:%S")
        time_spent = datetime.timedelta(
            hours=time_datetime.hour, minutes=time_datetime.minute, seconds=time_datetime.second
        ).total_seconds()

    comments_set = instance.comment_set.all()
    comment_serializer = CommentSerializer(comments_set, many=True)
    comments = comment_serializer.data

    task_doc = TaskDocument(
        meta={"id": task_data["id"]},
        title=task_data["title"],
        description=task_data["description"],
        user_id=str(task_data["user"]),
        is_completed=task_data["is_completed"],
        time_spent=time_spent,
        comments=comments,
    )
    task_doc.save()


@receiver(post_save, sender=Comment)
def comment_elasticsearch_handler(sender, instance, created, **kwargs):
    task_doc = TaskDocument.get(id=instance.task_id)
    comment_data = CommentSerializer(instance).data

    if task_doc:
        if "comments" not in task_doc:
            task_doc.comments = []

        task_doc_comments = task_doc.comments

        for i, task_doc_comment in enumerate(task_doc_comments):
            if task_doc_comment["id"] == comment_data["id"]:
                task_doc_comments[i] = comment_data
                break
        else:
            task_doc_comments.append(comment_data)

        task_doc.comments = task_doc_comments
        task_doc.save()


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
