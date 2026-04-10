from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED'
        CONFIRMED = 'CONFIRMED'
        CHECKED_IN = 'CHECKED_IN'
        COMPLETED = 'COMPLETED'
        CANCELLED = 'CANCELLED'
        NO_SHOW = 'NO_SHOW'

    id = models.AutoField(primary_key=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    check_in_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slot = models.OneToOneField(
        'doctors.Slot',
        on_delete=models.PROTECT,
        related_name='appointment',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': 'PATIENT'},
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['slot'],
                name='unique_slot',
            )
        ]


    def __str__(self):
        return f"Appointment #{self.pk} — {self.patient} with Dr. {self.slot.doctor} at {self.slot.start_datetime}"


class AppointmentAudit(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='audit_logs',
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointment_changes',
    )
    old_start_datetime = models.DateTimeField()
    new_start_datetime = models.DateTimeField()
    reason = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def clean(self):
        if (
            self.old_start_datetime
            and self.new_start_datetime
            and self.old_start_datetime == self.new_start_datetime
        ):
            raise ValidationError(
                {'new_start_datetime': 'New start datetime must differ from old start datetime.'}
            )



class Consultation(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='consultation',
    )
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    tests = models.TextField(blank=True)
    prescription = models.TextField(blank=True)


class Invoice(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='invoice',
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
