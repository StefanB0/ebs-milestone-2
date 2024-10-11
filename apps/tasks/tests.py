from django.contrib.auth.models import User
from django.urls import reverse
from django.core import mail
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.tasks.models import Task, Comment, TimeLog
from apps.tasks.serializers import TaskSerializer, CommentSerializer, TimeLogSerializer


class TestTasks(APITestCase):
    fixtures = ["users", "tasks"]

    def setUp(self) -> None:
        self.client = APIClient()

        self.user = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)

        self.tasks = TaskSerializer(Task.objects.all(), many=True).data
        self.comments = CommentSerializer(Comment.objects.all(), many=True).data

    def test_create_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-list"), self.tasks[0])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertContains(response, "task_id", status_code=201)

    def test_get_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Task.objects.filter(user=self.user).count())

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Task.objects.filter(user=self.user2).count())

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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "id")
        self.assertContains(response, "title")
        self.assertContains(response, "description")
        self.assertContains(response, "is_completed")
        self.assertContains(response, "user")

        response = self.client.get(reverse("tasks-detail", args=[6]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user2.id)

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

    def test_search_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-search"), {"search": "Test task 1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], self.tasks[0]["title"])
        self.assertEqual(response.data[0]["id"], 1)
        self.assertContains(response, "title")
        self.assertContains(response, "id")

        response = self.client.post(reverse("tasks-search"), {"search": "Finish"})
        task_nr = Task.objects.filter(title__icontains="Finish").count()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), task_nr)

    def test_assign_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task assigned successfully")

        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        # test_assign_task_same_user
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task assigned successfully")

    def test_complete_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

        # complete already completed task
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

        # complete task that does not belong to user
        response = self.client.patch(reverse("tasks-complete-task", args=[5]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Task completed successfully")

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


class TestComments(APITestCase):
    fixtures = ["users", "tasks", "comments"]

    def setUp(self) -> None:
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

    def test_get_comments(self) -> None:
        self.client.force_authenticate(user=self.user)
        comment_nr = Task.objects.get(id=1).comment_set.count()
        response = self.client.get(reverse("tasks-comments", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), comment_nr)


class TestMail(APITestCase):
    fixtures = ["users", "tasks", "comments"]

    def setUp(self) -> None:
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
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[4]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task completed")

    def test_mail_comment_complete_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[2].subject, "Task completed")

        # check if email is sent to comment user
        self.assertEqual(mail.outbox[2].to, [self.user2.email])


class TestTimeLog(APITestCase):
    fixtures = ["users", "tasks", "timelogs"]

    def setUp(self) -> None:
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if timelog is created
        self.assertEqual(TimeLog.objects.count(), initial_count + 1)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count + 1)

        # start timer for already started task
        initial_count = TimeLog.objects.count()
        initial_task_count = Task.objects.get(id=1).timelog_set.count()

        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["message"], "Task timer is already running")

        # check if timelog is not created
        self.assertEqual(TimeLog.objects.count(), initial_count)
        self.assertEqual(Task.objects.get(id=1).timelog_set.count(), initial_task_count)

        # start timer for task that does not belong to user
        self.client.force_authenticate(user=self.user2)
        response = self.client.patch(reverse("tasks-start-timer", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

    def create_time_log(self) -> None:
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

        response = self.client.post(
            reverse("timelogs-list"),
            {
                "task": task.id,
                "start_time": timezone.now() - timezone.timedelta(minutes=30),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def get_time_logs(self) -> None:
        task = Task.objects.get(id=1)
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))
        print(response.status_code)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), task.timelog_set.count())

        # get timelogs for task that does not belong to user
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(reverse("tasks-timer-logs", args=[task.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(True, False)
