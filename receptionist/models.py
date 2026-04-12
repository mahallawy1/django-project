from django.db import models

# Create your models here.


class Slot(models.Model):
	id = models.AutoField(primary_key=True)
	doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE)
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
