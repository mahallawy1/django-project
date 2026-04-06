from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'PATIENT'
        DOCTOR = 'DOCTOR'
        RECEPTIONIST = 'RECEPTIONIST'
        ADMIN = 'ADMIN'

    role = models.CharField(
        max_length=12,
        choices=Role.choices,
        default=Role.PATIENT,
    )
