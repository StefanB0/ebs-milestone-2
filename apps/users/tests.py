from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


class TestUsers(TestCase):
    fixtures = ["users"]

    def setUp(self) -> None:
        self.client = APIClient()
        # check data in fixture json file
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
