from django.urls import path

from .views import (
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    confirm_appointment,
    consultation_read,
    consultation_write,
    decline_appointment,
    list_appointments,
    no_show_appointment,
    reschedule_appointment,
)

urlpatterns = [
    path('', list_appointments, name='list_appointments'),
    path('<int:appointment_id>/confirm', confirm_appointment, name='confirm_appointment'),
    path('<int:appointment_id>/check-in', check_in_appointment, name='check_in_appointment'),
    path('<int:appointment_id>/decline', decline_appointment, name='decline_appointment'),
    path('<int:appointment_id>/complete', complete_appointment, name='complete_appointment'),
    path('<int:appointment_id>/no-show', no_show_appointment, name='no_show_appointment'),
    path('<int:appointment_id>/cancel', cancel_appointment, name='cancel_appointment'),
    path('<int:appointment_id>/reschedule', reschedule_appointment, name='reschedule_appointment'),
    path('<int:id>/consultation', consultation_read, name='consultation_read'),
    path('<int:id>/consultation/write', consultation_write, name='consultation_write'),
]
