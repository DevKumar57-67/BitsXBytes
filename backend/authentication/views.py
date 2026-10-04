import logging
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.core import signing
from django.db import transaction
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordAwareTokenObtainPairSerializer,
    EmailVerificationSerializer,
    RegisterSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()
EMAIL_VERIFICATION_SALT = "bitsxbytes.email-verification"
EMAIL_VERIFICATION_RESEND_INTERVAL = timedelta(
    seconds=settings.EMAIL_VERIFICATION_RESEND_INTERVAL
)


def set_refresh_cookie(response, token):
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        token,
        max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )
    return response


def clear_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    deleted_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    deleted_cookie["httponly"] = True
    deleted_cookie["secure"] = settings.AUTH_COOKIE_SECURE
    return response


@method_decorator(csrf_protect, name="dispatch")
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.email_verification_last_sent_at = timezone.now()
        user.save(update_fields=["email_verification_last_sent_at"])
        send_verification_email(user)
        return Response(
            {"detail": "Check your email for a verification link."},
            status=status.HTTP_201_CREATED,
        )


def send_verification_email(user):
    sent_at = user.email_verification_last_sent_at
    if sent_at is None:
        return

    token = signing.dumps(
        {
            "user_id": user.pk,
            "email": user.email,
            "sent_at": sent_at.isoformat(),
        },
        salt=EMAIL_VERIFICATION_SALT,
    )
    verification_url = f"{settings.FRONTEND_URL}/verify-email#token={token}"
    message = (
        "Welcome to BitsXBytes.\n\n"
        "Verify your email address using this link within "
        f"{settings.EMAIL_VERIFICATION_TIMEOUT // 3600} hours:\n"
        f"{verification_url}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    try:
        send_mail(
            subject="Verify your BitsXBytes email",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    except Exception:
        logger.warning("Email verification message delivery failed.")


@method_decorator(csrf_protect, name="dispatch")
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = signing.loads(
                serializer.validated_data["token"],
                salt=EMAIL_VERIFICATION_SALT,
                max_age=settings.EMAIL_VERIFICATION_TIMEOUT,
            )
            user = User._default_manager.get(
                pk=payload["user_id"],
                email=payload["email"],
            )
            token_sent_at = payload["sent_at"]
        except (
            signing.BadSignature,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            User.DoesNotExist,
        ):
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.email_verified:
            return Response(
                {"status": "already_verified"},
                status=status.HTTP_200_OK,
            )
        sent_at = user.email_verification_last_sent_at
        if sent_at is None or sent_at.isoformat() != token_sent_at:
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        changed = User._default_manager.filter(
            pk=user.pk,
            email_verified=False,
            email_verification_last_sent_at=sent_at,
        ).update(email_verified=True)
        if not changed:
            user.refresh_from_db()
            if user.email_verified:
                return Response(
                    {"status": "already_verified"},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"detail": "This verification link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "verified"}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class ResendEmailVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification_resend"

    def post(self, request):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if isinstance(email, str) and len(email) <= 254:
            normalized_email = email.strip()
            now = timezone.now()
            eligible = User._default_manager.filter(
                email__iexact=normalized_email,
                email_verified=False,
                is_active=True,
            ).filter(
                Q(email_verification_last_sent_at__isnull=True)
                | Q(
                    email_verification_last_sent_at__lte=(
                        now - EMAIL_VERIFICATION_RESEND_INTERVAL
                    )
                )
            ).first()
            if eligible:
                updated = User._default_manager.filter(
                    pk=eligible.pk,
                    email_verified=False,
                ).filter(
                    Q(email_verification_last_sent_at__isnull=True)
                    | Q(
                        email_verification_last_sent_at__lte=(
                            now - EMAIL_VERIFICATION_RESEND_INTERVAL
                        )
                    )
                ).update(email_verification_last_sent_at=now)
                if updated:
                    eligible.email_verification_last_sent_at = now
                    send_verification_email(eligible)

        return Response(
            {
                "detail": (
                    "If the account needs verification, a verification link "
                    "will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            self._send_reset_email(serializer.validated_data["email"])

        return Response(
            {
                "detail": (
                    "If an account with that email exists, password reset "
                    "instructions have been sent."
                )
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _send_reset_email(email):
        users = User._default_manager.filter(
            email__iexact=email,
            is_active=True,
        )
        for user in users:
            if not user.has_usable_password():
                continue

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            query = urlencode({"uid": uid, "token": token})
            reset_url = f"{settings.FRONTEND_URL}/reset-password#{query}"
            message = (
                "We received a request to reset your BitsXBytes password.\n\n"
                f"Use this link within {settings.PASSWORD_RESET_TIMEOUT // 60} "
                f"minutes to choose a new password:\n{reset_url}\n\n"
                "If you did not request this, you can safely ignore this email."
            )

            try:
                send_mail(
                    subject="Reset your BitsXBytes password",
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                logger.error("Password reset email delivery failed.")


@method_decorator(csrf_protect, name="dispatch")
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "This reset link or password is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]
        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password"])
            outstanding_tokens = OutstandingToken.objects.filter(user=user)
            for outstanding in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=outstanding)

        response = Response(
            {"detail": "Your password has been reset. Please sign in."},
            status=status.HTTP_200_OK,
        )
        return clear_refresh_cookie(response)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenObtainPairView(APIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordAwareTokenObtainPairSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data

        response = Response({"access": tokens["access"]})
        return set_refresh_cookie(response, tokens["refresh"])


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh_token:
            response = Response(
                {"detail": "Refresh token is missing or invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return clear_refresh_cookie(response)

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            response = Response(
                {"detail": "Refresh token is missing or invalid."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            return clear_refresh_cookie(response)
        response_data = serializer.validated_data
        response = Response({"access": response_data["access"]})
        rotated_refresh = response_data.get("refresh")
        if rotated_refresh:
            set_refresh_cookie(response, rotated_refresh)
        return response

    def handle_exception(self, exc):
        return clear_refresh_cookie(super().handle_exception(exc))


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "username": request.user.username,
            "email": request.user.email,
        })


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh_token:
            return clear_refresh_cookie(
                Response(status=status.HTTP_205_RESET_CONTENT)
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            pass

        return clear_refresh_cookie(
            Response(status=status.HTTP_205_RESET_CONTENT)
        )