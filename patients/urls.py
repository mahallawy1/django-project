from django.urls import path
from . import views

urlpatterns = [
    path('register', views.patient_register),
    path('me', views.patient_me),
    path('appointments', views.book_appointment),
    path('appointments/me', views.my_appointments),
    path('appointments/<int:appointment_id>', views.appointment_detail),
    path('<int:patient_id>', views.get_patient_by_id),
]