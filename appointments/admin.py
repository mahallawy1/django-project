from django.contrib import admin
from appointments.models import Appointment , Invoice
from .models import PaymentTransaction

# Register your models here.
admin.site.register(Appointment)
admin.site.register(Invoice)
admin.site.register(PaymentTransaction)