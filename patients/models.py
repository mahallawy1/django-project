from django.db import models
from django.conf import settings

class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        limit_choices_to={'role': 'PATIENT'},
    )
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=[('MALE', 'Male'), ('FEMALE', 'Female')])
    phone_number = models.CharField(max_length=15)
    height = models.IntegerField()
    weight = models.IntegerField()
    blood_type = models.CharField(max_length=3, blank=True)
    allergies = models.TextField(blank=True)