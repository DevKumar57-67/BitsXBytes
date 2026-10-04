from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import RegisterSerializer


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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != status.HTTP_200_OK:
            return response

        refresh_token = response.data["refresh"]
        response.data = {"access": response.data["access"]}
        return set_refresh_cookie(response, refresh_token)


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
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