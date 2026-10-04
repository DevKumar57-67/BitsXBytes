from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import get_password_version


class PasswordAwareJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if validated_token.get("password_version") != get_password_version(user):
            raise AuthenticationFailed("Token is no longer valid.")
        if not user.email_verified:
            raise AuthenticationFailed("Email verification is required.")
        return user
