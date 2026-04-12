from django.contrib import admin
from django.urls import path, include
from users import views
from rest_framework_simplejwt.views import TokenObtainPairView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('doctors/', include('doctors.urls')),
    path('doctors/', include('receptionist.doctor_urls')),
    path('receptionist/', include('receptionist.urls')),
    path('appointments/', include('appointments.urls')),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("", include("users.urls")),
    path('patients/', include('patients.urls')),
]
