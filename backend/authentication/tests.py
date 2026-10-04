from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthenticationFlowTests(APITestCase):
	def setUp(self):
		self.register_url = reverse("register")
		self.login_url = reverse("login")
		self.refresh_url = reverse("token_refresh")
		self.me_url = reverse("me")
		self.logout_url = reverse("logout")
		self.password = "S3cure!Raven-Tree-419"

	def create_user(self, username="student", email="student@example.com"):
		return User.objects.create_user(
			username=username,
			email=email,
			password=self.password,
		)

	def login(self, username="student"):
		response = self.client.post(
			self.login_url,
			{"username": username, "password": self.password},
		)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		return response.data

	def test_register_creates_user_without_returning_password(self):
		response = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "student@example.com",
				"password": self.password,
			},
		)

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertNotIn("password", response.data)
		user = User.objects.get(username="student")
		self.assertTrue(user.check_password(self.password))

	def test_register_rejects_duplicate_username_and_email(self):
		self.create_user()

		duplicate_username = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "different@example.com",
				"password": self.password,
			},
		)
		duplicate_email = self.client.post(
			self.register_url,
			{
				"username": "different",
				"email": "student@example.com",
				"password": self.password,
			},
		)

		self.assertEqual(duplicate_username.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(duplicate_email.status_code, status.HTTP_400_BAD_REQUEST)

	def test_register_applies_django_password_validators(self):
		response = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "student@example.com",
				"password": "password",
			},
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("password", response.data)

	def test_login_and_authenticated_profile(self):
		self.create_user()
		tokens = self.login()
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

		response = self.client.get(self.me_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["username"], "student")
		self.assertEqual(response.data["email"], "student@example.com")

	def test_refresh_and_logout_revoke_refresh_token(self):
		self.create_user()
		tokens = self.login()

		refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertIn("access", refresh_response.data)

		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
		logout_response = self.client.post(
			self.logout_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

		revoked_refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(
			revoked_refresh_response.status_code,
			status.HTTP_401_UNAUTHORIZED,
		)
