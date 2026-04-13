from .views import (
    get_doctor_me,
    get_doctor_schedule_me,
    create_doctor_availability,
    availability_detail,
    create_doctor_exception,
    delete_doctor_exception,
    get_all_doctors,
    create_doctor,
)
from django.urls import path

urlpatterns = [
    path('', get_all_doctors, name='get_all_doctors'),
    path('me', get_doctor_me, name='get_doctor_me'),
    path('me/schedule', get_doctor_schedule_me, name='get_doctor_schedule_me'),
    path('<int:doctor_id>/availability', create_doctor_availability, name='create_doctor_availability'),
    path('<int:doctor_id>/availability/<int:availability_id>', availability_detail, name='availability_detail'),
    path('<int:doctor_id>/exceptions', create_doctor_exception, name='create_doctor_exception'),
    path('<int:doctor_id>/exceptions/<int:exception_id>', delete_doctor_exception, name='delete_doctor_exception'),
    path('create', create_doctor, name='create_doctor'),
]
