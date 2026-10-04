import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.core.mail import send_mail
from django.utils import timezone

from users.models import User

from .models import EmailVerificationOTP

logger = logging.getLogger(__name__)


def _send_auth_email(
    *,
    message_type: str,
    subject: str,
    message: str,
    recipient: str,
) -> bool:
    try:
        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as error:
        logger.error(
            "Failed to send %s email (exception_type=%s).",
            message_type,
            type(error).__name__,
        )
        return False

    if sent_count != 1:
        logger.error("Email backend did not send %s email.", message_type)
        return False
    return True


def issue_email_verification_otp(user: User) -> str | None:
    with transaction.atomic():
        locked_user = User._default_manager.select_for_update().get(pk=user.pk)
        if not locked_user.is_active or locked_user.email_verified:
            return None
        last_sent_at = locked_user.email_verification_last_sent_at
        now = timezone.now()
        if (
            last_sent_at is not None
            and now - last_sent_at
            < timedelta(seconds=settings.EMAIL_VERIFICATION_RESEND_INTERVAL)
        ):
            return None

        otp = f"{secrets.randbelow(1_000_000):06d}"
        EmailVerificationOTP.objects.filter(
            user=locked_user,
            is_used=False,
        ).update(is_used=True)
        EmailVerificationOTP.objects.create(
            user=locked_user,
            otp_hash=make_password(otp),
            expires_at=now
            + timedelta(seconds=settings.EMAIL_VERIFICATION_OTP_TIMEOUT),
        )
        locked_user.email_verification_last_sent_at = now
        locked_user.save(update_fields=["email_verification_last_sent_at"])
        return otp


def check_email_verification_otp(otp_hash: str, otp: str) -> bool:
    return check_password(otp, otp_hash)


def discard_email_verification_otp(user: User, otp: str) -> None:
    with transaction.atomic():
        locked_user = User._default_manager.select_for_update().get(pk=user.pk)
        otp_record = (
            EmailVerificationOTP.objects.select_for_update()
            .filter(user=locked_user, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if otp_record is None or not check_password(otp, otp_record.otp_hash):
            return

        otp_record.is_used = True
        otp_record.save(update_fields=["is_used"])
        locked_user.email_verification_last_sent_at = None
        locked_user.save(update_fields=["email_verification_last_sent_at"])


def send_verification_otp_email(recipient: str, otp: str) -> bool:
    message = (
        "Welcome to BitsXBytes.\n\n"
        "Use this 6-digit code to verify your email address within 10 minutes:\n"
        f"{otp}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    return _send_auth_email(
        message_type="verification",
        subject="Your BitsXBytes verification code",
        message=message,
        recipient=recipient,
    )


def send_password_reset_email(recipient: str, reset_url: str) -> bool:
    message = (
        "We received a request to reset your BitsXBytes password.\n\n"
        f"Use this link within {settings.PASSWORD_RESET_TIMEOUT // 60} "
        f"minutes to choose a new password:\n{reset_url}\n\n"
        "If you did not request this, you can safely ignore this email."
    )
    return _send_auth_email(
        message_type="password reset",
        subject="Reset your BitsXBytes password",
        message=message,
        recipient=recipient,
    )
