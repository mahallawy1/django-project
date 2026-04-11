from django.contrib import admin

from doctors.models import Doctor, DoctorException, DoctorSchedule

# Register your models here.
admin.site.register(Doctor)
admin.site.register(DoctorSchedule)
admin.site.register(DoctorException)
