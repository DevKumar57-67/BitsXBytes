from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()


class AuthenticationFlowTests(APITestCase):
	client_class = APIClient

	def setUp(self):
		self.register_url = reverse("register")
		self.login_url = reverse("login")
		self.refresh_url = reverse("token_refresh")
		self.me_url = reverse("me")
		self.logout_url = reverse("logout")
		self.password_reset_url = reverse("password_reset")
		self.password_reset_confirm_url = reverse("password_reset_confirm")
		self.verify_email_url = reverse("verify_email")
		self.resend_verification_url = reverse("resend_verification")
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
		self.assertNotIn("refresh", response.data)
		refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
		self.assertTrue(refresh_cookie["httponly"])
		self.assertEqual(refresh_cookie["samesite"], settings.AUTH_COOKIE_SAMESITE)
		self.assertEqual(refresh_cookie["path"], settings.AUTH_REFRESH_COOKIE_PATH)
		self.assertEqual(
			bool(refresh_cookie["secure"]),
			settings.AUTH_COOKIE_SECURE,
		)
		return {
			"access": response.data["access"],
			"refresh": refresh_cookie.value,
		}

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

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_registration_sends_link_and_creates_unverified_user(self):
		response = self.client.post(
			self.register_url,
			{
				"username": "newstudent",
				"email": "newstudent@example.com",
				"password": self.password,
			},
		)
		user = User.objects.get(username="newstudent")

		self.assertEqual(response.status_code, status.HTTP_201_CREATED)
		self.assertFalse(user.email_verified)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, [user.email])
		self.assertIn("/verify-email#token=", mail.outbox[0].body)

	def verification_token_from_email(self):
		link = next(
			word
			for word in mail.outbox[-1].body.split()
			if "/verify-email#token=" in word
		)
		return parse_qs(urlsplit(link).fragment)["token"][0]

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_verification_token_verifies_account_and_replay_is_safe(self):
		self.client.post(
			self.register_url,
			{
				"username": "newstudent",
				"email": "newstudent@example.com",
				"password": self.password,
			},
		)
		token = self.verification_token_from_email()

		response = self.client.post(self.verify_email_url, {"token": token})
		replay = self.client.post(self.verify_email_url, {"token": token})

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["status"], "verified")
		self.assertTrue(User.objects.get(username="newstudent").email_verified)
		self.assertEqual(replay.status_code, status.HTTP_200_OK)
		self.assertEqual(replay.data["status"], "already_verified")
		login = self.client.post(
			self.login_url,
			{"username": "newstudent", "password": self.password},
		)
		self.assertEqual(login.status_code, status.HTTP_200_OK)

	def test_verification_rejects_invalid_and_expired_tokens(self):
		invalid = self.client.post(self.verify_email_url, {"token": "invalid"})
		self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_verification_rejects_expired_token(self):
		self.client.post(
			self.register_url,
			{
				"username": "newstudent",
				"email": "newstudent@example.com",
				"password": self.password,
			},
		)
		token = self.verification_token_from_email()

		with override_settings(EMAIL_VERIFICATION_TIMEOUT=-1):
			response = self.client.post(self.verify_email_url, {"token": token})

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertFalse(User.objects.get(username="newstudent").email_verified)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_resending_invalidates_previous_verification_token(self):
		self.client.post(
			self.register_url,
			{
				"username": "newstudent",
				"email": "newstudent@example.com",
				"password": self.password,
			},
		)
		old_token = self.verification_token_from_email()
		user = User.objects.get(username="newstudent")
		user.email_verification_last_sent_at = timezone.now() - timedelta(minutes=2)
		user.save(update_fields=["email_verification_last_sent_at"])

		self.client.post(self.resend_verification_url, {"email": user.email})
		new_token = self.verification_token_from_email()
		old_response = self.client.post(
			self.verify_email_url,
			{"token": old_token},
		)
		new_response = self.client.post(
			self.verify_email_url,
			{"token": new_token},
		)

		self.assertEqual(len(mail.outbox), 2)
		self.assertEqual(old_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(new_response.data["status"], "verified")

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_resend_response_is_generic_and_account_interval_limits_email(self):
		user = self.create_user()
		user.email_verified = False
		user.email_verification_last_sent_at = timezone.now()
		user.save(update_fields=["email_verified", "email_verification_last_sent_at"])

		existing = self.client.post(
			self.resend_verification_url,
			{"email": user.email},
		)
		unknown = self.client.post(
			self.resend_verification_url,
			{"email": "missing@example.com"},
		)

		self.assertEqual(existing.status_code, status.HTTP_200_OK)
		self.assertEqual(unknown.status_code, status.HTTP_200_OK)
		self.assertEqual(existing.data, unknown.data)
		self.assertEqual(len(mail.outbox), 0)

	def test_login_rejects_unverified_user_and_allows_verified_user(self):
		user = self.create_user()
		user.email_verified = False
		user.save(update_fields=["email_verified"])

		rejected = self.client.post(
			self.login_url,
			{"username": "student", "password": self.password},
		)
		self.assertEqual(rejected.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn("verify your email", str(rejected.data).lower())
		self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, rejected.cookies)

		user.email_verified = True
		user.save(update_fields=["email_verified"])
		accepted = self.client.post(
			self.login_url,
			{"username": "student", "password": self.password},
		)
		self.assertEqual(accepted.status_code, status.HTTP_200_OK)

	def test_unverified_user_cannot_use_previously_issued_access_token(self):
		user = self.create_user()
		tokens = self.login()
		user.email_verified = False
		user.save(update_fields=["email_verified"])
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

		response = self.client.get(self.me_url)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_verification_endpoints_require_csrf(self):
		client = APIClient(enforce_csrf_checks=True)
		for url, data in (
			(self.verify_email_url, {"token": "invalid"}),
			(self.resend_verification_url, {"email": "student@example.com"}),
		):
			response = client.post(url, data)
			self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

	def test_successful_login_returns_access_and_sets_httponly_refresh_cookie(self):
		self.create_user()
		tokens = self.login()

		self.assertTrue(tokens["access"])
		self.assertTrue(tokens["refresh"])

	@override_settings(AUTH_COOKIE_SECURE=True, AUTH_COOKIE_SAMESITE="None")
	def test_cross_site_production_cookie_is_secure(self):
		self.create_user()

		self.login()

		refresh_cookie = self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
		self.assertTrue(refresh_cookie["secure"])
		self.assertEqual(refresh_cookie["samesite"], "None")

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

	def test_logout_only_blacklists_the_refresh_cookie_not_a_body_token(self):
		self.create_user()
		self.create_user(username="other", email="other@example.com")
		user_tokens = self.login()
		other_user_tokens = self.login(username="other")
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = user_tokens["refresh"]

		response = self.client.post(
			self.logout_url,
			{"refresh": other_user_tokens["refresh"]},
		)
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = other_user_tokens["refresh"]
		refresh_response = self.client.post(
			self.refresh_url,
		)

		self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

	def test_refresh_returns_a_new_access_token(self):
		self.create_user()
		self.login()

		refresh_response = self.client.post(self.refresh_url, {})
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertIn("access", refresh_response.data)
		self.assertNotIn("refresh", refresh_response.data)
		self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, refresh_response.cookies)

	def test_expired_access_token_can_be_replaced_from_refresh_cookie(self):
		self.create_user()
		tokens = self.login()
		expired_access = AccessToken(tokens["access"])
		expired_access.set_exp(lifetime=timedelta(seconds=-1))
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_access}")

		expired_me_response = self.client.get(self.me_url)
		refresh_response = self.client.post(self.refresh_url, {})
		self.client.credentials(
			HTTP_AUTHORIZATION=f"Bearer {refresh_response.data['access']}"
		)
		refreshed_me_response = self.client.get(self.me_url)

		self.assertEqual(expired_me_response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertEqual(refreshed_me_response.status_code, status.HTTP_200_OK)

	def test_refresh_rotation_blacklists_previous_refresh_token(self):
		self.create_user()
		tokens = self.login()

		refresh_response = self.client.post(self.refresh_url, {})
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = tokens["refresh"]
		reuse_response = self.client.post(self.refresh_url, {})

		self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
		self.assertNotIn("refresh", refresh_response.data)
		self.assertEqual(reuse_response.status_code, status.HTTP_401_UNAUTHORIZED)

	def test_logout_blacklists_valid_refresh_token(self):
		self.create_user()
		self.login()
		logout_response = self.client.post(self.logout_url, {})
		self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)
		self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, logout_response.cookies)
		self.assertEqual(
			int(logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"]),
			0,
		)
		self.assertTrue(
			logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["httponly"]
		)
		self.assertEqual(
			bool(logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["secure"]),
			settings.AUTH_COOKIE_SECURE,
		)

	def test_blacklisted_refresh_token_cannot_be_used(self):
		self.create_user()
		tokens = self.login()
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
		self.client.post(self.logout_url, {})
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = tokens["refresh"]

		revoked_refresh_response = self.client.post(self.refresh_url, {})
		self.assertEqual(
			revoked_refresh_response.status_code,
			status.HTTP_401_UNAUTHORIZED,
		)

	def test_invalid_refresh_cookie_is_cleared(self):
		response = self.client.post(
			self.refresh_url,
			HTTP_COOKIE=f"{settings.AUTH_REFRESH_COOKIE_NAME}=invalid",
		)

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)
		self.assertEqual(
			int(response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["max-age"]),
			0,
		)

	def test_expired_refresh_cookie_is_cleared(self):
		self.create_user()
		tokens = self.login()
		expired_refresh = RefreshToken(tokens["refresh"])
		expired_refresh.set_exp(lifetime=timedelta(seconds=-1))
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = str(expired_refresh)

		response = self.client.post(self.refresh_url, {})

		self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_request_sends_link_for_existing_user(self):
		user = self.create_user()

		response = self.client.post(
			self.password_reset_url,
			{"email": user.email},
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(
			response.data,
			{
				"detail": (
					"If an account with that email exists, password reset "
					"instructions have been sent."
				)
			},
		)
		self.assertEqual(len(mail.outbox), 1)
		self.assertEqual(mail.outbox[0].to, [user.email])
		self.assertIn("/reset-password#uid=", mail.outbox[0].body)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_link_from_reset_email_completes_password_reset(self):
		user = self.create_user()
		self.client.post(self.password_reset_url, {"email": user.email})
		reset_link = next(
			word for word in mail.outbox[0].body.split() if "/reset-password#" in word
		)
		params = parse_qs(urlsplit(reset_link).fragment)
		new_password = "New-S3cure!Raven-Tree-592"

		response = self.client.post(
			self.password_reset_confirm_url,
			{
				"uid": params["uid"][0],
				"token": params["token"][0],
				"new_password": new_password,
				"confirm_password": new_password,
			},
		)

		user.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(user.check_password(new_password))
		self.assertNotIn(params["token"][0], str(response.data))

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_response_is_same_for_existing_and_unknown_email(self):
		self.create_user()
		existing_response = self.client.post(
			self.password_reset_url,
			{"email": "student@example.com"},
		)
		unknown_response = self.client.post(
			self.password_reset_url,
			{"email": "missing@example.com"},
		)

		self.assertEqual(existing_response.status_code, status.HTTP_200_OK)
		self.assertEqual(unknown_response.status_code, status.HTTP_200_OK)
		self.assertEqual(existing_response.data, unknown_response.data)
		self.assertEqual(len(mail.outbox), 1)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_request_malformed_email_is_generic(self):
		response = self.client.post(
			self.password_reset_url,
			{"email": "not-an-email"},
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(mail.outbox), 0)

	@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
	def test_password_reset_skips_inactive_and_unusable_password_accounts(self):
		inactive = self.create_user()
		inactive.is_active = False
		inactive.save(update_fields=["is_active"])
		unusable = self.create_user(username="unusable", email="unusable@example.com")
		unusable.set_unusable_password()
		unusable.save(update_fields=["password"])

		for email in (inactive.email, unusable.email):
			response = self.client.post(self.password_reset_url, {"email": email})
			self.assertEqual(response.status_code, status.HTTP_200_OK)

		self.assertEqual(len(mail.outbox), 0)

	def password_reset_data(self, user, password="New-S3cure!Raven-Tree-592"):
		return {
			"uid": urlsafe_base64_encode(force_bytes(user.pk)),
			"token": default_token_generator.make_token(user),
			"new_password": password,
			"confirm_password": password,
		}

	def test_password_reset_changes_password_and_token_cannot_be_reused(self):
		user = self.create_user()
		data = self.password_reset_data(user)

		response = self.client.post(self.password_reset_confirm_url, data)
		reuse_response = self.client.post(self.password_reset_confirm_url, data)

		user.refresh_from_db()
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertTrue(user.check_password(data["new_password"]))
		self.assertEqual(reuse_response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(
			reuse_response.data["detail"],
			"This reset link or password is invalid.",
		)

	def test_password_reset_rejects_mismatched_confirmation(self):
		user = self.create_user()
		data = self.password_reset_data(user)
		data["confirm_password"] = "Different-S3cure!Raven-592"

		response = self.client.post(self.password_reset_confirm_url, data)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["detail"], "This reset link or password is invalid.")

	def test_password_reset_rejects_invalid_uid_and_token(self):
		user = self.create_user()
		for data in (
			{
				**self.password_reset_data(user),
				"uid": "not-a-valid-user-id",
			},
			{
				**self.password_reset_data(user),
				"token": "invalid-token",
			},
		):
			response = self.client.post(self.password_reset_confirm_url, data)
			self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
			self.assertEqual(response.data["detail"], "This reset link or password is invalid.")

	def test_password_reset_rejects_expired_token(self):
		user = self.create_user()
		data = self.password_reset_data(user)
		with override_settings(PASSWORD_RESET_TIMEOUT=-1):
			response = self.client.post(self.password_reset_confirm_url, data)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["detail"], "This reset link or password is invalid.")

	def test_password_reset_applies_django_password_validators(self):
		user = self.create_user()
		data = self.password_reset_data(user, password="password")

		response = self.client.post(self.password_reset_confirm_url, data)

		self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
		self.assertEqual(response.data["detail"], "This reset link or password is invalid.")
		user.refresh_from_db()
		self.assertTrue(user.check_password(self.password))

	def test_password_reset_blacklists_existing_refresh_tokens(self):
		user = self.create_user()
		tokens = self.login()
		data = self.password_reset_data(user)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
		authenticated_before_reset = self.client.get(self.me_url)

		reset_response = self.client.post(self.password_reset_confirm_url, data)
		self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = tokens["refresh"]
		refresh_response = self.client.post(self.refresh_url, {})
		authenticated_after_reset = self.client.get(self.me_url)

		self.assertEqual(authenticated_before_reset.status_code, status.HTTP_200_OK)
		self.assertEqual(reset_response.status_code, status.HTTP_200_OK)
		self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
		self.assertEqual(
			authenticated_after_reset.status_code,
			status.HTTP_401_UNAUTHORIZED,
		)
		self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, reset_response.cookies)


class AuthenticationCsrfTests(APITestCase):
	def setUp(self):
		self.client = APIClient(enforce_csrf_checks=True)
		self.user = User.objects.create_user(
			username="csrf-student",
			email="csrf-student@example.com",
			password="S3cure!Raven-Tree-419",
		)

	def test_login_requires_csrf_token(self):
		response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "S3cure!Raven-Tree-419"},
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_registration_requires_csrf_token(self):
		response = self.client.post(
			reverse("register"),
			{
				"username": "blocked-registration",
				"email": "blocked@example.com",
				"password": "S3cure!Raven-Tree-419",
			},
		)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

	def test_password_reset_endpoints_require_csrf_token(self):
		request_response = self.client.post(
			reverse("password_reset"),
			{"email": self.user.email},
		)
		confirm_response = self.client.post(
			reverse("password_reset_confirm"),
			{
				"uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
				"token": default_token_generator.make_token(self.user),
				"new_password": "New-S3cure!Raven-Tree-592",
				"confirm_password": "New-S3cure!Raven-Tree-592",
			},
		)

		self.assertEqual(request_response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(confirm_response.status_code, status.HTTP_403_FORBIDDEN)

	def test_logout_requires_csrf_token(self):
		csrf_response = self.client.get(reverse("csrf"))
		login_response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "S3cure!Raven-Tree-419"},
			HTTP_X_CSRFTOKEN=csrf_response.data["csrfToken"],
		)
		logout_response = self.client.post(reverse("logout"))

		self.assertEqual(login_response.status_code, status.HTTP_200_OK)
		self.assertEqual(logout_response.status_code, status.HTTP_403_FORBIDDEN)

	def test_csrf_endpoint_allows_login_with_csrf_token(self):
		csrf_response = self.client.get(reverse("csrf"))
		response = self.client.post(
			reverse("login"),
			{"username": self.user.username, "password": "S3cure!Raven-Tree-419"},
			HTTP_X_CSRFTOKEN=csrf_response.data["csrfToken"],
		)

		self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertNotIn("refresh", response.data)
