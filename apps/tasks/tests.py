import datetime
import logging
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle

from apps.tasks.views import TaskViewSet, CommentViewSet, TaskTimeLogViewSet, ElasticSearchViewSet, AttachmentViewSet
from config.celery import app as celery_app

from apps.tasks.models import Task, Comment, TimeLog, Attachment
from apps.tasks.serializers import TaskSerializer, CommentSerializer, TimeLogSerializer

User = get_user_model()


class TestTasks(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/timelogs"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )
        TaskViewSet.throttle_classes = []

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.comments = CommentSerializer(Comment.objects.all(), many=True).data

        self.client.force_authenticate(user=self.user)

    def test_create_task(self) -> None:
        response = self.client.post(reverse("tasks-list"), self.tasks[0])

        self.assertContains(response, "id", status_code=201)
        self.assertContains(response, "title", status_code=201)
        self.assertContains(response, "description", status_code=201)
        self.assertContains(response, "is_completed", status_code=201)
        self.assertContains(response, "user", status_code=201)
        self.assertContains(response, "time_spent", status_code=201)

    def test_get_tasks(self) -> None:
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), Task.objects.filter(user=self.user).count())
        self.assertContains(response, "id")
        self.assertContains(response, "title")

    # Get tasks for another user
    def test_get_tasks_user2(self) -> None:
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), Task.objects.filter(user=self.user2).count())

    # Check if time_spent is in response
    def test_get_tasks_check_time(self) -> None:
        response = self.client.get(reverse("tasks-list"))
        self.assertContains(response, "time_spent")

    # Check if time_spent is calculated correctly
    def test_get_tasks_calculate_time(self) -> None:
        response = self.client.get(reverse("tasks-list"))
        task3_log_set = Task.objects.get(id=3).timelog_set
        task3_time_spent = timezone.timedelta()
        for time_log in task3_log_set.all():
            task3_time_spent += time_log.duration

        r_task3 = next(task for task in response.data["results"] if task["id"] == 3)
        r_time = r_task3["time_spent"]
        r_time = datetime.datetime.strptime(r_time, "%H:%M:%S")
        r_time = timezone.timedelta(hours=r_time.hour, minutes=r_time.minute, seconds=r_time.second)
        self.assertEqual(r_time.total_seconds(), task3_time_spent.total_seconds(), str(response.data))

    # Check if time_spent is calculated correctly for task without timelogs
    def test_get_tasks_calculate_time_no_timelogs(self) -> None:
        response = self.client.get(reverse("tasks-list"))
        r_task2 = next(task for task in response.data["results"] if task["id"] == 2)
        r_time = r_task2["time_spent"]
        self.assertEqual(r_time, None)

    def test_get_user_tasks(self) -> None:
        response = self.client.get(reverse("tasks-user", kwargs={"pk": 1}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), Task.objects.filter(user=self.user).count())

    # User ID does not exist
    def test_get_user_tasks_no_user(self) -> None:
        response = self.client.get(reverse("tasks-user", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_all_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-all-tasks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), len(self.tasks))
        self.assertContains(response, "title")
        self.assertContains(response, "id")

    def test_get_task(self) -> None:
        response = self.client.get(reverse("tasks-detail", args=[1]))

        self.assertContains(response, "id", status_code=200)
        self.assertContains(response, "title")
        self.assertContains(response, "description")
        self.assertContains(response, "is_completed")
        self.assertContains(response, "user")

    # Get task that belongs to another user
    def test_get_task_foreign(self) -> None:
        response = self.client.get(reverse("tasks-detail", args=[6]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user2.id)

    # Task ID does not exist
    def test_get_task_no_task(self) -> None:
        response = self.client.get(reverse("tasks-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_completed_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-completed-tasks"))

        completed_tasks = Task.objects.filter(is_completed=True, user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), completed_tasks.count())
        self.assertEqual(response.data["results"][0]["title"], completed_tasks[0].title)
        self.assertEqual(response.data["results"][0]["id"], completed_tasks[0].id)

    def test_get_incomplete_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-incomplete-tasks"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 3)

    # Search full title
    def test_search_task(self) -> None:
        response = self.client.post(reverse("tasks-search"), {"search": "Test task 1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Test task 1")
        self.assertEqual(response.data["results"][0]["id"], 1)

    # Search partial title
    def test_search_task_partial(self) -> None:
        response = self.client.post(reverse("tasks-search"), {"search": "Finish"})
        task_nr = Task.objects.filter(title__icontains="Finish").count()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), task_nr)

    # Title does not exist
    def test_search_task_no_task(self) -> None:
        response = self.client.post(reverse("tasks-search"), {"search": "Idempotent"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_assign_task(self) -> None:
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task assigned successfully")

        self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

    # Assign task to same user
    def test_assign_task_same_user(self) -> None:
        self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user.id})
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user.id})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Task already belongs to user")

    # User does not exist
    def test_assign_task_no_user(self) -> None:
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Task does not exist
    def test_assign_task_no_task(self) -> None:
        response = self.client.patch(reverse("tasks-assign-task", args=[9999]), {"user": self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_complete_task(self) -> None:
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

    # Complete already completed task
    def test_complete_task_complete(self) -> None:
        self.client.patch(reverse("tasks-complete-task", args=[1]))
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Task already completed")

    # Complete task that does not belong to user
    def test_complete_task_foreign(self) -> None:
        response = self.client.patch(reverse("tasks-complete-task", args=[6]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

    # Task does not exist
    def test_complete_task_no_task(self) -> None:
        response = self.client.patch(reverse("tasks-complete-task", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_undo_task(self) -> None:
        response = self.client.patch(reverse("tasks-undo-task", args=[2]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task undone successfully")

    # Undo  incomplete task
    def test_undo_task_undo(self) -> None:
        self.client.patch(reverse("tasks-undo-task", args=[2]))
        response = self.client.patch(reverse("tasks-undo-task", args=[2]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Task not yet completed")

    # Complete task that does not belong to user
    def test_undo_task_foreign(self) -> None:
        response = self.client.patch(reverse("tasks-undo-task", args=[7]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task undone successfully")

    # Task does not exist
    def test_undo_task_no_task(self) -> None:
        response = self.client.patch(reverse("tasks-undo-task", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_task(self) -> None:
        response = self.client.delete(reverse("tasks-detail", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # Delete already deleted task
    def test_delete_task_delete(self) -> None:
        self.client.delete(reverse("tasks-detail", args=[1]))
        response = self.client.delete(reverse("tasks-detail", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # Delete task that does not belong to user
    def test_delete_task_foreign(self) -> None:
        response = self.client.delete(reverse("tasks-detail", args=[5]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # Task does not exist
    def test_delete_task_no_task(self) -> None:
        response = self.client.delete(reverse("tasks-detail", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_throttle(self):
        TaskViewSet.throttle_classes = [UserRateThrottle]

        response = self.client.get(reverse("tasks-detail", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for i in range(0, 10):
            self.client.get(reverse("tasks-detail", args=[1]))

        response = self.client.get(reverse("tasks-detail", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class TestComments(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/comments"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )
        CommentViewSet.throttle_classes = []

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.comments = CommentSerializer(Comment.objects.all(), many=True).data

        self.client.force_authenticate(user=self.user)

    def test_add_comment(self) -> None:
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 999", "task": 1})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertContains(response, "comment_id", status_code=201)

    # Check if comment is created
    def test_add_comment_check_created(self) -> None:
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 999", "task": 1})
        comment = Comment.objects.get(id=response.data["comment_id"])
        self.assertIsNotNone(comment)
        self.assertEqual(comment.body, "Test comment 999")

    # Task does not exist
    def test_add_comment_no_task(self) -> None:
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 000", "task": 9999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_comments(self) -> None:
        comment_nr = Task.objects.get(id=1).comments.count()
        response = self.client.get(reverse("tasks-comments", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), comment_nr)

    # Comment does not exist
    def test_get_comments_no_comment(self) -> None:
        response = self.client.get(reverse("tasks-comments", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_throttle(self):
        CommentViewSet.throttle_classes = [UserRateThrottle]

        for i in range(0, 10):
            self.client.get(reverse("tasks-comments", args=[1]))

        response = self.client.get(reverse("tasks-comments", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class TestMail(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/comments"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )
        TaskViewSet.throttle_classes = []
        CommentViewSet.throttle_classes = []

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.client.force_authenticate(user=self.user)

    def test_mail_assign_task(self) -> None:
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task assigned")

    def test_mail_complete_task(self) -> None:
        # Task with no comments
        response = self.client.patch(reverse("tasks-complete-task", args=[4]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task completed")

        # Task with comments
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if email is sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject, "Task completed")

        # Check if email is sent to comment user
        self.assertIn(self.user2.email, mail.outbox[1].to)


class TestTimeLog(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/timelogs"]

    def setUp(self):
        logging.disable(logging.CRITICAL)
        celery_app.conf.update(
            task_always_eager=True,
        )
        TaskViewSet.throttle_classes = []
        TaskTimeLogViewSet.throttle_classes = []

        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.client.force_authenticate(user=self.user)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.time_logs = TimeLogSerializer(TimeLog.objects.all(), many=True).data

        for instance in TimeLog.objects.all():
            if instance.start_time < timezone.now() - timezone.timedelta(days=30):
                difference = timezone.now() - instance.start_time - timezone.timedelta(days=1)
                offset = timezone.timedelta(days=difference.days)
                instance.start_time = instance.start_time + offset
                instance.save()

    def test_start_timer(self):
        initial_count = TimeLog.objects.count()
        initial_task_count = Task.objects.get(id=1).timelog_set.count()

        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data["message"])

        # Check if timelog is created
        self.assertEqual(TimeLog.objects.count(), initial_count + 1)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count + 1)

    # Start timer for already started task
    def test_start_timer_repeat(self):
        self.client.patch(reverse("tasks-start-timer", args=[1]))

        initial_count = TimeLog.objects.count()
        initial_task_count = Task.objects.get(id=1).timelog_set.count()

        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Task timer is already running", response.data["message"])

        # Check if timelog is not created
        self.assertEqual(TimeLog.objects.count(), initial_count)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count)

    # Start timer for task that does not belong to user
    def test_start_timer_foreign(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Task does not exist
    def test_start_timer_no_task(self):
        response = self.client.patch(reverse("tasks-start-timer", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stop_timer(self):
        task = Task.objects.get(id=5)
        TimeLog.objects.create(task=task, start_time=timezone.now() - timezone.timedelta(hours=1))

        self.assertIsNone(task.timelog_set.first().duration)

        response = self.client.patch(reverse("tasks-stop-timer", args=[5]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if timelog is stopped
        self.assertIsNotNone(task.timelog_set.first().duration)

    # Stop timer for already stopped task
    def test_stop_timer_repeat(self):
        task = Task.objects.get(id=5)
        TimeLog.objects.create(task=task, start_time=timezone.now() - timezone.timedelta(hours=1))

        self.client.patch(reverse("tasks-stop-timer", args=[5]))
        response = self.client.patch(reverse("tasks-stop-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Stop timer for task that does not belong to user
    def test_stop_timer_foreign(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(reverse("tasks-stop-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Task does not exist
    def test_stop_timer_no_task(self):
        response = self.client.patch(reverse("tasks-stop-timer", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_time_log(self):
        task = Task.objects.get(id=1)

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

    # Create timelog for task that does not belong to user
    def test_create_time_log_foreign(self):
        task = Task.objects.get(id=1)
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

    # Create timelog when another timelog is running
    def test_create_time_log_repeat(self):
        task = Task.objects.get(id=1)
        request_data = {
            "task": task.id,
            "start_time": timezone.now() - timezone.timedelta(minutes=30),
        }
        self.client.post(reverse("timelogs-list"), request_data)
        response = self.client.post(reverse("timelogs-list"), request_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # Create timelog with overlapping time
    def test_create_time_log_overlap(self):
        task = Task.objects.get(id=1)
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
    def test_create_time_log_no_task(self):
        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": 9999,
                "start_time": timezone.now() - timezone.timedelta(hours=1),
                "duration": timezone.timedelta(hours=1),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_time_logs(self):
        task = Task.objects.get(id=1)

        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), task.timelog_set.count())

    # Get timelogs for task that does not have any timelogs
    def test_get_time_logs_no_logs(self):
        task = Task.objects.get(id=8)
        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    # Get timelogs for task that does not belong to user
    def test_get_time_logs_foreign(self):
        task = Task.objects.get(id=1)
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Task not found
    def test_get_time_logs_no_task(self):
        response = self.client.get(reverse("tasks-timer-logs", args=[9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_time_logs_month(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("timelogs-last-month"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "month_time_spent")
        self.assertEqual(
            response.data["month_time_spent"].total_seconds(), timezone.timedelta(hours=2, minutes=30).total_seconds()
        )

    def test_get_top_logs(self):
        response = self.client.get(reverse("timelogs-top"), {"limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], 5)

        duration = datetime.datetime.strptime(response.data[0]["duration"], "%H:%M:%S")
        top_duration = timezone.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
        self.assertEqual(top_duration.total_seconds(), timezone.timedelta(minutes=45).total_seconds())

    # Get default limit of 20, but there are only 6 logs, 1 of them with no duration
    def test_get_top_logs_deficit(self):
        response = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5, response.data)

    # Get top logs for user that does not have any logs
    def test_get_top_logs_no_logs(self):
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0, f"{response.data}")

    # Test caching
    def test_get_top_logs_cache(self):
        # First request
        response1 = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.data), 5)

        # Second request
        response2 = self.client.get(reverse("timelogs-top"))
        TimeLog.objects.all().delete()
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data), 5)

    def test_throttle(self):
        TaskTimeLogViewSet.throttle_classes = [UserRateThrottle]
        for i in range(0, 10):
            self.client.get(reverse("timelogs-top"))

        response = self.client.get(reverse("timelogs-top"))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class TestAttachment(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        AttachmentViewSet.throttle_classes = []

        self.file_name = "test-file.jpg"
        self.file_name_no_extension = self.file_name.split(".")[0]

        self.client = APIClient()
        self.user = User.objects.get(pk=1)
        self.client.force_authenticate(user=self.user)

    def tearDown(self) -> None:
        queryset = Attachment.objects.all()
        queryset.delete()

    def test_task_attachment_creation(self):
        task = Task.objects.first()
        instance = Attachment.objects.create(task=task, file=self.file_name)

        self.assertEqual(instance.task, task)
        self.assertTrue(self.file_name_no_extension in instance.file.name, str(instance.file.name))

    def test_upload_attachment(self):
        task = Task.objects.first()
        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertContains(response, "id", status_code=status.HTTP_201_CREATED)
        self.assertContains(response, "file", status_code=status.HTTP_201_CREATED)
        self.assertEqual(response.data["task"], task.id, response.data)
        self.assertContains(response, "file_upload_url", status_code=status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Attachment.PENDING, response.data)

    def test_upload_attachment_repeat(self):
        task = Task.objects.first()
        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})
        self.assertIn(self.file_name, response.data["file"])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn(self.file_name, response.data["file"])
        self.assertIn(self.file_name_no_extension, response.data["file"])

    def test_confirm_webhook(self):
        task = Task.objects.first()
        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        instance = Attachment.objects.get(id=response.data["id"])
        self.assertEqual(instance.status, Attachment.PENDING)
        self.assertNotEqual(instance.file_upload_url, "")

        today = datetime.date.today()
        webhook_data = {
            "EventName": "s3:ObjectCreated:Put",
            "Key": f"django-media-files-bucket/task-attachments/{today.year}-{today.month}-{today.day}/{self.file_name}",
            "Records": [
                {
                    "eventTime": "2020-01-01T00:00:00.000Z",
                }
            ],
        }

        response = self.client.post(reverse("attachments-webhook"), webhook_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        instance.refresh_from_db()

        self.assertEqual(instance.status, Attachment.READY)
        self.assertEqual(instance.file_upload_url, "")

    def test_get_attachments(self):
        response = self.client.get(reverse("attachments-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

        task = Task.objects.first()
        for i in range(0, 10):
            self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        response = self.client.get(reverse("attachments-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)

    def test_get_attachment(self):
        task = Task.objects.first()
        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        attachment_id = response.data["id"]

        response = self.client.get(reverse("attachments-detail", kwargs={"pk": attachment_id}))
        self.assertContains(response, "file")
        self.assertEqual(response.data["task"], task.id, response.data)
        self.assertContains(response, "file_upload_url")
        self.assertEqual(response.data["status"], Attachment.PENDING, response.data)

    def test_get_attachment_no_attachment(self):
        response = self.client.get(reverse("attachments-detail", kwargs={"pk": 9999}))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_task_attachment(self):
        task = Task.objects.first()
        self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        response = self.client.get(reverse("attachments-task", kwargs={"pk": task.id}))
        self.assertContains(response, "file")
        self.assertEqual(response.data["results"][0]["task"], task.id, response.data)

    def test_get_attachment_task_not_exist(self):
        response = self.client.get(reverse("attachments-task", kwargs={"pk": 9999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Task not found")

    def test_delete_attachment(self):
        task = Task.objects.first()
        response = self.client.post(reverse("attachments-list"), {"file_name": self.file_name, "task": task.id})

        response = self.client.delete(reverse("attachments-detail", kwargs={"pk": response.data["id"]}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_throttle(self):
        AttachmentViewSet.throttle_classes = [UserRateThrottle]
        for i in range(0, 10):
            self.client.get(reverse("attachments-list"))

        response = self.client.get(reverse("attachments-list"))
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class TestElasticSearch(APITestCase):
    fixtures = ["fixtures/users", "fixtures/tasks", "fixtures/comments", "fixtures/tasks"]

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        ElasticSearchViewSet.throttle_classes = []

        self.client = APIClient()
        user1 = User.objects.get(pk=1)
        self.client.force_authenticate(user=user1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_no_params(self):
        response = self.client.get(reverse("elasticsearch-task"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"error": "No query was provided"}, response)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_title_param(self):
        response = self.client.get(reverse("elasticsearch-task"), {"title": "Test task"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertIn("Test task", response.data[0]["title"], response.data)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_description_param(self):
        response = self.client.get(reverse("elasticsearch-task"), {"description": "week"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_comment_body_param(self):
        response = self.client.get(reverse("elasticsearch-task"), {"comment_body": "Test comment"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_with_limit(self):
        response = self.client.get(reverse("elasticsearch-task"), {"description": "week", "limit": 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_search_multiple_params(self):
        response = self.client.get(reverse("elasticsearch-task"), {"title": "dentist", "description": "week"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_update_task(self):
        response = self.client.get(reverse("elasticsearch-task"), {"title": "cat"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 0)

        task_instance = Task.objects.first()
        task_instance.title += " test cat"
        task_instance.save()

        response = self.client.get(reverse("elasticsearch-task"), {"title": "cat"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_task_update_comment(self):
        response = self.client.get(reverse("elasticsearch-task"), {"comment_body": "spider"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 0)

        comment_instance = Comment.objects.first()
        comment_instance.body = "test spider"
        comment_instance.save()

        response = self.client.get(reverse("elasticsearch-task"), {"comment_body": "spider"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 1)

    @skipUnless(settings.ELASTICSEARCH_ACTIVE, "ElasticSearch is not active")
    def test_throttle(self):
        ElasticSearchViewSet.throttle_classes = [ScopedRateThrottle]

        self.client.get(reverse("elasticsearch-task"), {"comment_body": "spider"})
        response = self.client.get(reverse("elasticsearch-task"), {"comment_body": "spider"})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
