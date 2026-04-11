from .views import (
    create_doctor_availability,
    availability_detail,
    create_doctor_exception,
    delete_doctor_exception,
)
from django.urls import path

urlpatterns = [
    path('<int:doctor_id>/availability', create_doctor_availability, name='create_doctor_availability'),
    path('<int:doctor_id>/availability/<int:availability_id>', availability_detail, name='availability_detail'),
    path('<int:doctor_id>/exceptions', create_doctor_exception, name='create_doctor_exception'),
    path('<int:doctor_id>/exceptions/<int:exception_id>', delete_doctor_exception, name='delete_doctor_exception'),
]
