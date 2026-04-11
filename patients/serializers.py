from rest_framework import serializers
from users.models import User
from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = "__all__"
        read_only_fields = ["user"]


class patientRegSerializer(serializers.ModelSerializer):
    profile = PatientProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["username", "password", "email", "first_name", "last_name", "profile"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.PATIENT)