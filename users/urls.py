from django.urls import path, include
from rest_framework import routers
from users import views
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers import CustomTokenObtainPairSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

users_router = routers.DefaultRouter()
users_router.register(r"users", views.UserViewSet)
users_router.register(r"groups", views.GroupViewSet)

urlpatterns = [
    path("", include(users_router.urls)),
    path('auth/login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout', views.LogoutView.as_view(), name='logout'),
]
