from django.urls import path
from .views import (
    list_appointments,
    cancel_appointment,
    check_in_appointment,
    confirm_appointment,
    no_show_appointment,
    reschedule_appointment,
    consultation_read,
    consultation_write,
)

urlpatterns = [
    path('', list_appointments, name='list_appointments'),
    path('<int:appointment_id>/confirm', confirm_appointment, name='confirm_appointment'),
    path('<int:appointment_id>/check-in', check_in_appointment, name='check_in_appointment'),
    path('<int:appointment_id>/no-show', no_show_appointment, name='no_show_appointment'),
    path('<int:appointment_id>/cancel', cancel_appointment, name='cancel_appointment'),
    path('<int:appointment_id>/reschedule', reschedule_appointment, name='reschedule_appointment'),
    path('<int:id>/consultation', consultation_read, name='consultation_read'),
    path('<int:id>/consultation', consultation_write, name='consultation_write'),
]
