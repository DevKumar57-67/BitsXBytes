from django.conf import settings
from django.db import models


class EmailVerificationOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_verification_otps",
    )
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "is_used", "expires_at"],
                name="auth_email_otp_active_idx",
            ),
        ]
