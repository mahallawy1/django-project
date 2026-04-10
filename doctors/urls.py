from .views import set_doctor_schedule
from django.urls import path

urlpatterns = [
    path('<int:doctor_id>/availability', set_doctor_schedule, name='set_doctor_schedule'),
]