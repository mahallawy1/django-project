from django.db import models

# Create your models here.
class Doctor(models.Model):
    user_id = models.ForeignKey('users.User', on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100)
    session_duration = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')])
    buffer_time = models.IntegerField(choices=[(5, '5 minutes'), (10, '10 minutes')])

    def __str__(self):
        full_name = self.user_id.get_full_name().strip()
        return full_name or self.user_id.username
    
class DoctorSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        SATURDAY = 0, 'Saturday'
        SUNDAY = 1, 'Sunday'
        MONDAY = 2, 'Monday'
        TUESDAY = 3, 'Tuesday'
        WEDNESDAY = 4, 'Wednesday'
        THURSDAY = 5, 'Thursday'
        FRIDAY = 6, 'Friday'

    id = models.AutoField(primary_key=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'day_of_week'], name='unique_doctor_day_schedule')
        ]

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time} to {self.end_time}"
    

class DoctorException(models.Model):
    id = models.AutoField(primary_key=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    type = models.CharField(
        choices=[
            ('VACATION_DAY', 'Vacation Day'),
            ('EXTRA_WORKING_DAY', 'Extra Working Day'),
        ],
        max_length=20
    )
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'date'], name='unique_doctor_exception_date')
        ]

    def __str__(self):
        return f"{self.doctor} - {self.date}"
    

class Slot(models.Model):
    id = models.AutoField(primary_key=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'start_datetime'], name='unique_doctor_slot')
        ]

    def __str__(self):
        status = 'Booked' if self.is_booked else 'Available'
        return f"{self.doctor} - {self.start_datetime} to {self.end_datetime} - {status}"
