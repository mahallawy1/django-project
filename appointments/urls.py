from django.urls import path
from . import views

urlpatterns = [
    path('appointments/<int:id>/consultation', views.consultation_read, name='consultation_read'),
    path('appointments/<int:id>/consultation', views.consultation_write, name='consultation_write'),
]