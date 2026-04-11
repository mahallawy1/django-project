from django.urls import path

from .views import get_doctor_slots, regenerate_slots

urlpatterns = [
    path('<int:doctor_id>/slots', get_doctor_slots, name='get_doctor_slots'),
    path('<int:doctor_id>/slots/regenerate', regenerate_slots, name='regenerate_slots'),
]
