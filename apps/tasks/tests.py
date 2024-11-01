import datetime
import logging

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from config.celery import app as celery_app

from apps.users.models import User
from apps.tasks.models import Task, Comment, TimeLog, TaskAttachment
from apps.tasks.serializers import TaskSerializer, CommentSerializer, TimeLogSerializer


class TestTasks(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/timelogs"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.comments = CommentSerializer(Comment.objects.all(), many=True).data

    def test_create_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-list"), self.tasks[0])

        self.assertContains(response, "id", status_code=201)
        self.assertContains(response, "title", status_code=201)
        self.assertContains(response, "description", status_code=201)
        self.assertContains(response, "is_completed", status_code=201)
        self.assertContains(response, "user", status_code=201)
        self.assertContains(response, "time_spent", status_code=201)

    def test_get_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-list"))

        # Base usage
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Task.objects.filter(user=self.user).count())
        self.assertContains(response, "id")
        self.assertContains(response, "title")

        # Get tasks for another user
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Task.objects.filter(user=self.user2).count())

        # Check if time_spent is in response
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-list"))
        self.assertContains(response, "time_spent")

        # Check if time_spent is calculated correctly
        task3_log_set = Task.objects.get(id=3).timelog_set
        task3_time_spent = timezone.timedelta()
        for time_log in task3_log_set.all():
            task3_time_spent += time_log.duration

        r_time = response.data[2]["time_spent"]
        r_time = datetime.datetime.strptime(r_time, "%H:%M:%S")
        r_time = timezone.timedelta(hours=r_time.hour, minutes=r_time.minute, seconds=r_time.second)
        self.assertEqual(r_time.total_seconds(), task3_time_spent.total_seconds())

        # Check if time_spent is calculated correctly for task without timelogs
        r_time = response.data[1]["time_spent"]
        # r_time = datetime.datetime.strptime(r_time, "%H:%M:%S")
        # r_time = timezone.timedelta(hours=r_time.hour, minutes=r_time.minute, seconds=r_time.second)
        self.assertEqual(r_time, None)

    def test_get_user_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-user", kwargs={"pk": 1}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Task.objects.filter(user=self.user).count())

        # User ID does not exist
        response = self.client.get(reverse("tasks-user", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-all-tasks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(self.tasks))
        self.assertContains(response, "title")
        self.assertContains(response, "id")

    def test_get_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-detail", args=[1]))

        self.assertContains(response, "id", status_code=200)
        self.assertContains(response, "title")
        self.assertContains(response, "description")
        self.assertContains(response, "is_completed")
        self.assertContains(response, "user")

        # Get task that belongs to another user
        response = self.client.get(reverse("tasks-detail", args=[6]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user2.id)

        # Task ID does not exist
        response = self.client.get(reverse("tasks-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_completed_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-completed-tasks"))

        completed_tasks = Task.objects.filter(is_completed=True, user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), completed_tasks.count())
        self.assertEqual(response.data[0]["title"], self.tasks[1]["title"])
        self.assertEqual(response.data[0]["id"], completed_tasks[0].id)
        self.assertContains(response, "title")
        self.assertContains(response, "id")

    def test_get_incomplete_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-incomplete-tasks"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_search_task(self) -> None:
        # Search full title
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-search"), {"search": "Test task 1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.tasks[0]["title"])
        self.assertEqual(response.data[0]["id"], 1)
        self.assertContains(response, "title")
        self.assertContains(response, "id")

        # Search partial title
        response = self.client.post(reverse("tasks-search"), {"search": "Finish"})
        task_nr = Task.objects.filter(title__icontains="Finish").count()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), task_nr)

        # Title does not exist
        response = self.client.post(reverse("tasks-search"), {"search": "Idempotent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_assign_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task assigned successfully")

        self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        # test_assign_task_same_user
        self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user.id})
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Task already belongs to user")

        # User does not exist
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Task does not exist
        response = self.client.patch(reverse("tasks-assign-task", args=[9999]), {"user": self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

        # complete already completed task
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Task already completed")

        # complete task that does not belong to user
        response = self.client.patch(reverse("tasks-complete-task", args=[6]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

        # Task does not exist
        response = self.client.patch(reverse("tasks-complete-task", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("tasks-detail", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # delete already deleted task
        response = self.client.delete(reverse("tasks-detail", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # delete task that does not belong to user
        response = self.client.delete(reverse("tasks-detail", args=[5]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Task does not exist
        response = self.client.delete(reverse("tasks-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestComments(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/comments"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.comments = CommentSerializer(Comment.objects.all(), many=True).data

    def test_add_comment(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 999", "task": 1})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertContains(response, "comment_id", status_code=201)

        # check if comment is created
        comment = Comment.objects.get(id=response.data["comment_id"])
        self.assertIsNotNone(comment)
        self.assertEqual(comment.body, "Test comment 999")

        # Task does not exist
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 000", "task": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_comments(self) -> None:
        self.client.force_authenticate(user=self.user)
        comment_nr = Task.objects.get(id=1).comments.count()
        response = self.client.get(reverse("tasks-comments", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), comment_nr)

        # Comment does not exist
        response = self.client.get(reverse("tasks-comments", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestMail(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/comments"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

    def test_mail_assign_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task assigned")

    def test_mail_complete_task(self) -> None:
        # Task with no comments
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[4]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task completed")

        # Task with comments
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject, "Task completed")

        # check if email is sent to comment user
        self.assertIn(self.user2.email, mail.outbox[1].to)


class TestTimeLog(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/timelogs"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.time_logs = TimeLogSerializer(TimeLog.objects.all(), many=True).data

    def test_start_timer(self) -> None:
        initial_count = TimeLog.objects.count()
        initial_task_count = Task.objects.get(id=1).timelog_set.count()

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data["message"])

        # check if timelog is created
        self.assertEqual(TimeLog.objects.count(), initial_count + 1)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count + 1)

        # start timer for already started task
        initial_count = TimeLog.objects.count()
        initial_task_count = Task.objects.get(id=1).timelog_set.count()

        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Task timer is already running", response.data["message"])

        # check if timelog is not created
        self.assertEqual(TimeLog.objects.count(), initial_count)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count)

        # start timer for task that does not belong to user
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Task does not exist
        response = self.client.patch(reverse("tasks-start-timer", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stop_timer(self) -> None:
        task = Task.objects.get(id=5)
        TimeLog.objects.create(task=task, start_time=timezone.now() - timezone.timedelta(hours=1))

        self.assertIsNone(task.timelog_set.first().duration)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-stop-timer", args=[5]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if timelog is stopped
        self.assertIsNotNone(task.timelog_set.first().duration)

        # stop timer for already stopped task
        response = self.client.patch(reverse("tasks-stop-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # stop timer for task that does not belong to user
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(reverse("tasks-stop-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Task does not exist
        response = self.client.patch(reverse("tasks-stop-timer", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_time_log(self) -> None:
        task = Task.objects.get(id=1)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() - timezone.timedelta(hours=1),
                "duration": timezone.timedelta(hours=1),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # check if timelog is created
        self.assertIsNotNone(TimeLog.objects.get(id=response.data["time_log_id"]).duration)

        # create timelog for task that does not belong to user
        self.client.force_authenticate(user=self.user2)

        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() + timezone.timedelta(hours=1),
                "duration": timezone.timedelta(hours=1),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # create timelog when another timelog is running
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() - timezone.timedelta(minutes=30),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # create timelog with overlapping time
        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() - timezone.timedelta(hours=3),
                "duration": timezone.timedelta(minutes=45),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() - timezone.timedelta(hours=2, minutes=30),
                "duration": timezone.timedelta(minutes=45),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Task does not exist
        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": 9999,
                "start_time": timezone.now() - timezone.timedelta(hours=1),
                "duration": timezone.timedelta(hours=1),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_time_logs(self) -> None:
        task = Task.objects.get(id=1)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), task.timelog_set.count())

        # get timelogs for task that does not have any timelogs
        task = Task.objects.get(id=8)
        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # get timelogs for task that does not belong to user
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Task not found
        response = self.client.get(reverse("tasks-timer-logs", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_time_logs_month(self) -> None:
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("timelogs-last-month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "month_time_spent")
        self.assertEqual(
            response.data["month_time_spent"].total_seconds(), timezone.timedelta(hours=2, minutes=30).total_seconds()
        )

    def test_get_top_logs(self) -> None:
        self.client.force_authenticate(user=self.user)

        # get top 2 logs
        response = self.client.get(reverse("timelogs-top"), {"limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], 5)

        duration = datetime.datetime.strptime(response.data[0]["duration"], "%H:%M:%S")
        top_duration = timezone.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
        self.assertEqual(top_duration.total_seconds(), timezone.timedelta(minutes=45).total_seconds())

        # get default limit of 20, but there are only 6 logs, 1 of them with no duration

        response = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

        # get top logs for user that does not have any logs
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0, f"{response.data}")

        # test caching
        self.client.force_authenticate(user=self.user)

        # first request
        response1 = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.data), 5)
        # second request
        response2 = self.client.get(reverse("timelogs-top"))
        TimeLog.objects.all().delete()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data), 5)


class TestMinIO(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks"]

    def setUp(self) -> None:
        self.mock_photo_prefix = "static/mock/"
        self.photos = ["Duck_" + str(i) + ".png" for i in range(1, 10)]

        logging.disable(logging.CRITICAL)
        self.client = APIClient()
        self.user = User.objects.get(pk=1)
        self.tasks = TaskSerializer(Task.objects.all(), many=True).data

    def test_task_attachment_creation(self):
        self.client.force_authenticate(user=self.user)

        task = Task.objects.first()
        file = SimpleUploadedFile(self.mock_photo_prefix + self.photos[0], b"file_content", content_type="image/png")
        attachment = TaskAttachment.objects.create(task=task, file=file)

        # Assertions
        self.assertEqual(attachment.task, task)
        self.assertTrue(self.photos[0].split(".")[0] in attachment.file.name, str(attachment.file.name))

    def test_upload_attachment(self):
        self.client.force_authenticate(user=self.user)

        task = Task.objects.first()
        url = f"/tasks/{task.id}/upload_attachment/"
        file = SimpleUploadedFile(self.photos[0], b"file_content", content_type="image/png")
        response = self.client.post(url, {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("attach_id", response.data)
        self.assertIn("task_id:", response.data)

    def test_get_attachments(self):
        self.client.force_authenticate(user=self.user)

        task = Task.objects.first()
        TaskAttachment.objects.create(
            task=task, file=SimpleUploadedFile(self.photos[1], b"file_content", content_type="image/png")
        )

        url = f"/tasks/{task.id}/attachments/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
