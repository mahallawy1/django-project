from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from users import views
from rest_framework_simplejwt.views import TokenObtainPairView

router = routers.DefaultRouter()
router.register(r"users", views.UserViewSet)
router.register(r"groups", views.GroupViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("", include(router.urls)),
    path('api/token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
]
