from apps.users.models import User
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status


class TestUsers(TestCase):
    fixtures = ["fixtures/users"]

    def setUp(self) -> None:
        self.client = APIClient()
        self.test_user1 = User.objects.get(email="user1@email.com")

    def test_register(self) -> None:
        response = self.client.post(
            reverse("users-register"),
            {
                "first_name": "firstname2",
                "last_name": "lastname2",
                "email": "username2@example.mail.com",
                "username": "username2",
                "password": "testpwd2",
            },
        )
        self.assertEqual(response.status_code, 201)

        new_user = User.objects.get(username="username2")
        self.assertEqual(new_user.first_name, "firstname2")
        self.assertEqual(new_user.last_name, "lastname2")
        self.assertEqual(new_user.email, "username2@example.mail.com")
        self.assertTrue(new_user.check_password("testpwd2"))

    def test_register_repeat_email(self) -> None:
        user_data = {
            "first_name": "firstname2",
            "last_name": "lastname2",
            "email": "username2@example.mail.com",
            "username": "username2",
            "password": "testpwd2",
        }

        self.client.post(reverse("users-register"), user_data)
        response = self.client.post(reverse("users-register"), user_data)

        self.assertEqual(response.status_code, 400)

    def test_login(self) -> None:
        response = self.client.post(
            reverse("users-login"),
            {
                "email": "user1@email.com",
                "password": "testpassword",
            },
        )

        self.assertContains(response, "access", status_code=200, msg_prefix="Login failed:" + str(response.data))
        self.assertContains(response, "refresh", status_code=200)

    def test_login_user_not_found(self) -> None:
        response = self.client.post(
            reverse("users-login"),
            {
                "email": "notfound@mailmail.com",
                "password": "testpassword",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_login_wrong_password(self) -> None:
        response = self.client.post(
            reverse("users-login"),
            {
                "email": "user1@email.com",
                "password": "wrongpassword",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_login_empty_email(self) -> None:
        # log in with empty email
        response = self.client.post(
            reverse("users-login"),
            {
                "password": "testpassword",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_refresh_token(self) -> None:
        self.client.force_authenticate(user=self.test_user1)
        response = self.client.post(
            reverse("users-login"),
            {
                "email": "user1@email.com",
                "password": "testpassword",
            },
        )

        refresh_token = response.data["refresh"]
        response = self.client.post(
            reverse("users-refresh"),
            {
                "refresh": refresh_token,
            },
        )
        self.assertContains(response, "access", status_code=200)

    def test_user_list(self) -> None:
        self.client.force_authenticate(user=self.test_user1)
        response = self.client.get(reverse("users-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 6)

    def test_get_user(self) -> None:
        self.client.force_authenticate(user=self.test_user1)
        response = self.client.get(reverse("users-detail", kwargs={"pk": self.test_user1.id}))
        self.assertContains(response, "email", status_code=200)
        self.assertContains(response, "first_name")
        self.assertContains(response, "last_name")
        self.assertContains(response, "username")
        self.assertEqual(response.data["email"], self.test_user1.email)

    def test_profile_render(self) -> None:
        url = reverse("users-profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")

    def test_top_task_render(self) -> None:
        self.client.force_authenticate(user=self.test_user1)
        url = reverse("users-top-tasks", args=[1])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
