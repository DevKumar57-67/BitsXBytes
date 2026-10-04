import hashlib
import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate(self, attrs):
        user = User(username=attrs.get("username"), email=attrs.get("email"))
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        user.email_verified = False
        user.save(update_fields=["email_verified"])
        return user


def get_password_version(user):
    return hmac.new(
        settings.SECRET_KEY.encode(),
        user.password.encode(),
        hashlib.sha256,
    ).hexdigest()


class PasswordAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.email_verified:
            raise AuthenticationFailed(
                "Verify your email address before signing in."
            )
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["password_version"] = get_password_version(user)
        return token


class EmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    otp = serializers.RegexField(regex=r"^\d{6}$", max_length=6, min_length=6)


class ResendEmailVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254, trim_whitespace=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    confirm_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        user = self._get_user(attrs["uid"])
        if (
            user is None
            or not user.is_active
            or not default_token_generator.check_token(user, attrs["token"])
        ):
            raise serializers.ValidationError(
                {"token": "This reset link is invalid or has expired."}
            )

        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"new_password": error.messages}
            ) from error

        attrs["user"] = user
        return attrs

    @staticmethod
    def _get_user(uid):
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            return User._default_manager.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None