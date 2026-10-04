import logging
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
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
    RegisterSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


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