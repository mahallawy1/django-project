from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from users import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

users_router = routers.DefaultRouter()
users_router.register(r"users", views.UserViewSet)
users_router.register(r"groups", views.GroupViewSet)

urlpatterns = [
    path("", include(users_router.urls)),
    path('auth/login', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout', views.LogoutView.as_view(), name='logout'),
]
