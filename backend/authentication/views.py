from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils import timezone
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
    ResendEmailVerificationSerializer,
    RegisterSerializer,
)
from .services import (
    check_email_verification_otp,
    discard_email_verification_otp,
    issue_email_verification_otp,
    send_password_reset_email,
    send_verification_otp_email,
)
from .models import EmailVerificationOTP

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        email_sent = send_verification_email(user)
        return Response(
            {
                "detail": (
                    "Enter the verification code sent to your email."
                    if email_sent
                    else (
                        "Your account was created, but we could not send the "
                        "verification code. Please try resending it."
                    )
                ),
                "email_sent": email_sent,
            },
            status=status.HTTP_201_CREATED,
        )


def send_verification_email(user):
    otp = issue_email_verification_otp(user)
    if otp is None:
        return False
    sent = send_verification_otp_email(user.email, otp)
    if not sent:
        discard_email_verification_otp(user, otp)
    return sent


@method_decorator(csrf_protect, name="dispatch")
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"detail": "The verification code is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User._default_manager.filter(
            email__iexact=serializer.validated_data["email"],
            is_active=True,
        ).first()
        if user is None:
            return Response(
                {"detail": "The verification code is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.email_verified:
            return Response(
                {"status": "already_verified", "detail": "Email is already verified."},
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            otp_record = (
                EmailVerificationOTP.objects.select_for_update()
                .filter(user=user, is_used=False)
                .order_by("-created_at")
                .first()
            )
            if otp_record is None or otp_record.attempts >= settings.EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS:
                if otp_record is not None:
                    otp_record.is_used = True
                    otp_record.save(update_fields=["is_used"])
                return Response(
                    {"detail": "The verification code is invalid or has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if otp_record.expires_at <= timezone.now():
                otp_record.is_used = True
                otp_record.save(update_fields=["is_used"])
                return Response(
                    {"detail": "The verification code is invalid or has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not check_email_verification_otp(
                otp_record.otp_hash,
                serializer.validated_data["otp"],
            ):
                otp_record.attempts += 1
                update_fields = ["attempts"]
                if otp_record.attempts >= settings.EMAIL_VERIFICATION_OTP_MAX_ATTEMPTS:
                    otp_record.is_used = True
                    update_fields.append("is_used")
                otp_record.save(update_fields=update_fields)
                return Response(
                    {"detail": "The verification code is invalid or has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            otp_record.is_used = True
            otp_record.save(update_fields=["is_used"])
            User._default_manager.filter(pk=user.pk, email_verified=False).update(
                email_verified=True
            )

        return Response(
            {"status": "verified", "detail": "Your email has been verified."},
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_protect, name="dispatch")
class ResendEmailVerificationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "email_verification_resend"

    def post(self, request):
        serializer = ResendEmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = User._default_manager.filter(
                email__iexact=serializer.validated_data["email"],
                email_verified=False,
                is_active=True,
            ).first()
            if user is not None:
                send_verification_email(user)

        return Response(
            {
                "detail": (
                    "If the account needs verification, a new code will be sent."
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
            send_password_reset_email(user.email, reset_url)


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