from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=True)
    email_verification_last_sent_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.username