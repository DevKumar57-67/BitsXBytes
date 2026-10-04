from django.urls import path
from .views import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CsrfTokenView,
    EmailVerificationView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendEmailVerificationView,
)


urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", EmailVerificationView.as_view(), name="verify_otp"),
    path("resend-otp/", ResendEmailVerificationView.as_view(), name="resend_otp"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify_email"),
    path(
        "resend-verification/",
        ResendEmailVerificationView.as_view(),
        name="resend_verification",
    ),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
]