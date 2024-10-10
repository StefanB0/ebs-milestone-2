from django.urls import reverse
from django.core import mail
from django.contrib.auth.models import User

from rest_framework import status
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from apps.tasks.models import Task, Comment

tests = [
    {
        "title": "Test task 1",
        "description": "Test description 1",
        "is_completed": False,
    },
    {
        "title": "Test task 2",
        "description": "Test description 2",
        "is_completed": True,
    },
    {
        "title": "Test task 3",
        "description": "Test description 3",
        "is_completed": False,
    },
]

comments = [
    {
        "body": "Test comment 1",
    },
    {
        "body": "Test comment 2",
    },
]

class TestTasks(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = User.objects.create(
            email="aadmin@admin.com",
            first_name="admin",
            last_name="admin",
            username="admin",
            password="admin",
        )
        self.user2 = User.objects.create(
            email="admin2@admin.com",
            first_name="admin2",
            last_name="admin2",
            username="admin2",
            password="admin2",
        )

        for test in tests:
            test["user"] = self.user
            Task.objects.create(**test)
        for test in tests[:-1]:
            test["user"] = self.user2
            Task.objects.create(**test)

    def test_create_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-list"), tests[0])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertContains(response, "task_id", status_code=201)


    def test_get_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(tests))

        self.client.force_authenticate(user=self.user2)
        response = self.client.get(reverse("tasks-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(tests) - 1)

    def test_get_all_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-all-tasks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(tests) * 2 - 1)
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

        response = self.client.get(reverse("tasks-detail", args=[5]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.user2.id)

    def test_get_completed_tasks(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("tasks-completed-tasks"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], tests[1]["title"])
        self.assertEqual(response.data[0]["id"], self.user.id)
        self.assertContains(response, "title")
        self.assertContains(response, "id")

    def test_search_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("tasks-search"), {"search": "1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], tests[0]["title"])
        self.assertEqual(response.data[0]["id"], 1)
        self.assertContains(response, "title")
        self.assertContains(response, "id")

        response = self.client.post(reverse("tasks-search"), {"search": "Test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(tests))

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
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = User.objects.create(
            email="aadmin@admin.com",
            first_name="admin",
            last_name="admin",
            username="admin",
            password="admin",
        )
        self.user2 = User.objects.create(
            email="admin2@admin.com",
            first_name="admin2",
            last_name="admin2",
            username="admin2",
            password="admin2",
        )

        for test in tests:
            test["user"] = self.user
            Task.objects.create(**test)
            for comment in comments:
                comment["task"] = Task.objects.get(title=test["title"])
                comment["user"] = self.user2
                Comment.objects.create(**comment)

        for test in tests[:-1]:
            test["user"] = self.user2
            Task.objects.create(**test)
            comments[0]["task"] = Task.objects.get(title=test["title"], user=self.user2)
            comments[0]["user"] = self.user
            Comment.objects.create(**comments[0])

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
        response = self.client.get(reverse("tasks-comments", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(comments))

class TestMail(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        self.user = User.objects.create(
            email="aadmin@admin.com",
            first_name="admin",
            last_name="admin",
            username="admin",
            password="admin",
        )
        self.user2 = User.objects.create(
            email="admin2@admin.com",
            first_name="admin2",
            last_name="admin2",
            username="admin2",
            password="admin2",
        )

        for test in tests:
            test["user"] = self.user
            Task.objects.create(**test)

    def test_mail_assign_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-assign-task", args=[1]), {"user": self.user2.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task assigned")

    def test_mail_complete_task(self) -> None:
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Task completed")

    def test_mail_comment_complete_task(self) -> None:
        self.client.force_authenticate(user=self.user2)
        response = self.client.post(reverse("comments-list"), {"body": "Test comment 000", "task": 1})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("tasks-complete-task", args=[1]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


        # check if email is sent
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(mail.outbox[2].subject, "Task completed")

        # check if email is sent to comment user
        self.assertEqual(mail.outbox[2].to, [self.user2.email])
    