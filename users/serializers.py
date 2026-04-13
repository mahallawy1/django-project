from django.contrib.auth.models import Group
from users.models import User
from rest_framework import serializers


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email", "groups", "role", "first_name", "last_name", "is_active", "password"]
        extra_kwargs = {"password": {"write_only": True}}


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ["url", "name"]