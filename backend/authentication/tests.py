from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class AuthenticationFlowTests(APITestCase):
	client_class = APIClient

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
		self.assertIn("access", response.data)
		self.assertIn("refresh", response.data)
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
		self.assertNotEqual(user.password, self.password)
		self.assertTrue(user.check_password(self.password))

	def test_register_rejects_duplicate_username(self):
		self.create_user()

		response = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "another@example.com",
				"password": self.password,
			},
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("username", response.data)

	def test_register_rejects_duplicate_email(self):
		self.create_user()

		response = self.client.post(
			self.register_url,
			{
				"username": "another",
				"email": "student@example.com",
				"password": self.password,
			},
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("email", response.data)

	def test_register_rejects_invalid_email(self):
		response = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "not-an-email",
				"password": self.password,
			},
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("email", response.data)

	def test_register_rejects_password_shorter_than_eight_characters(self):
		response = self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "student@example.com",
				"password": "Short1!",
			},
		)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertIn("password", response.data)

	def test_register_rejects_common_password(self):
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

	def test_password_is_stored_as_a_hash(self):
		self.client.post(
			self.register_url,
			{
				"username": "student",
				"email": "student@example.com",
				"password": self.password,
			},
		)

		stored_password = User.objects.get(username="student").password

		self.assertNotEqual(stored_password, self.password)
		self.assertTrue(User.objects.get(username="student").check_password(self.password))

	def test_me_requires_authentication(self):
		response = self.client.get(self.me_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_successful_login_returns_access_and_refresh_tokens(self):
		self.create_user()
		tokens = self.login()

		self.assertTrue(tokens["access"])
		self.assertTrue(tokens["refresh"])

	def test_me_with_valid_jwt_returns_current_user(self):
		self.create_user()
		tokens = self.login()
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

		response = self.client.get(self.me_url)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["username"], "student")
		self.assertEqual(response.data["email"], "student@example.com")

	def test_login_rejects_incorrect_password(self):
		self.create_user()

		response = self.client.post(
			self.login_url,
			{"username": "student", "password": "Incorrect!Password-48"},
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_login_rejects_nonexistent_username(self):
		response = self.client.post(
			self.login_url,
			{"username": "missing", "password": self.password},
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_logout_cannot_blacklist_another_users_refresh_token(self):
		self.create_user()
		self.create_user(username="other", email="other@example.com")
		user_tokens = self.login()
		other_user_tokens = self.login(username="other")
		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {user_tokens['access']}"
		)

		response = self.client.post(
			self.logout_url,
			{"refresh": other_user_tokens["refresh"]},
		)
		refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": other_user_tokens["refresh"]},
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

	def test_refresh_returns_a_new_access_token(self):
		self.create_user()
		tokens = self.login()

		refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertIn("access", refresh_response.data)

	def test_refresh_rotation_blacklists_previous_refresh_token(self):
		self.create_user()
		tokens = self.login()

		refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)
		reuse_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)

		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertIn("refresh", refresh_response.data)
		self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_logout_blacklists_valid_refresh_token(self):
		self.create_user()
		tokens = self.login()
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
		logout_response = self.client.post(
			self.logout_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

	def test_blacklisted_refresh_token_cannot_be_used(self):
		self.create_user()
		tokens = self.login()
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
		self.client.post(self.logout_url, {"refresh": tokens["refresh"]})

		revoked_refresh_response = self.client.post(
			self.refresh_url,
			{"refresh": tokens["refresh"]},
		)
		self.assertEqual(
			revoked_refresh_response.status_code,
			status.HTTP_401_UNAUTHORIZED,
		)
