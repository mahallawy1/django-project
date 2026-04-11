from django.contrib import admin

from doctors.models import Doctor, DoctorException, DoctorSchedule, Slot

# Register your models here.
admin.site.register(Doctor)
admin.site.register(DoctorSchedule)
admin.site.register(DoctorException)
admin.site.register(Slot)