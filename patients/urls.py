from django.urls import path
from . import views

urlpatterns = [
    path('register', views.patient_register),
    path('me', views.patient_me),
]