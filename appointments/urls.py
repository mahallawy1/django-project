from django.urls import path

from .views import (
    analytics_export,
    appointment_analytics,
    today_status_analytics,
    appointment_detail,
    cancel_appointment,
    check_in_appointment,
    complete_appointment,
    confirm_appointment,
    consultation_read,
    consultation_write,
    decline_appointment,
    list_appointments,
    no_show_appointment,
    reschedule_history,
    reschedule_appointment,
    today_queue,
)

urlpatterns = [
    path('', list_appointments, name='list_appointments'),
    path('analytics', appointment_analytics, name='appointment_analytics'),
    path('analytics/today-status', today_status_analytics, name='today_status_analytics'),
    path('analytics/export', analytics_export, name='analytics_export'),
    path('<int:appointment_id>', appointment_detail, name='appointment_detail'),
    path('queue/today', today_queue, name='today_queue'),
    path('<int:appointment_id>/confirm', confirm_appointment, name='confirm_appointment'),
    path('<int:appointment_id>/check-in', check_in_appointment, name='check_in_appointment'),
    path('<int:appointment_id>/decline', decline_appointment, name='decline_appointment'),
    path('<int:appointment_id>/complete', complete_appointment, name='complete_appointment'),
    path('<int:appointment_id>/no-show', no_show_appointment, name='no_show_appointment'),
    path('<int:appointment_id>/cancel', cancel_appointment, name='cancel_appointment'),
    path('<int:appointment_id>/reschedule', reschedule_appointment, name='reschedule_appointment'),
    path('<int:appointment_id>/reschedule-history', reschedule_history, name='reschedule_history'),
    path('<int:id>/consultation', consultation_read, name='consultation_read'),
    path('<int:id>/consultation/write', consultation_write, name='consultation_write'),
]