from django.urls import path
from .views import (
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    CsrfTokenView,
    LogoutView,
    MeView,
    RegisterView,
)


urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CookieTokenObtainPairView.as_view(), name="login"),
    path("refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("logout/", LogoutView.as_view(), name="logout"),
]