from django.db import models

# Create your models here.
class Doctor(models.Model):
    user_id = models.IntegerField(unique_primary_key=True)
    specialization = models.CharField(max_length=100)
    session_duration = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')])
    buffer_time = models.IntegerField(choices=[(5, '5 minutes'), (10, '10 minutes')])

    def __str__(self):
        return self.name
    
class DoctorSchedule(models.Model):
    id = models.AutoField(primary_key=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    day_of_week = models.IntegerChoices(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.name} - {self.date} {self.start_time} to {self.end_time}"
    

class DoctorException(models.Model):
    id = models.AutoField(primary_key=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    type = models.CharField(choices=[('VACATION', 'Vacation'), ('EXTRA_WORKING_DAY', 'Extra Working Day')], max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.doctor.name} - {self.date} {self.start_time} to {self.end_time}"
    

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
        return f"{self.doctor.name} - {self.date} {self.start_datetime} to {self.end_datetime} - {'Booked' if self.is_booked else 'Available'}"