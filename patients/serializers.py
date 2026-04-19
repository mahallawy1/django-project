from rest_framework import serializers
from users.models import User
from .models import PatientProfile
from django.db import transaction

class PatientProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    class Meta:
        model = PatientProfile
        fields = "__all__"
        read_only_fields = ["user"]


class patientRegSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    profile = PatientProfileSerializer()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def create(self, validated_data):
        profile_data = validated_data.pop("profile")

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                password=validated_data["password"],
                email=validated_data["email"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                role=User.Role.PATIENT,
            )
            PatientProfile.objects.create(user=user, **profile_data)

        return user

    def to_representation(self, instance):
        profile = PatientProfile.objects.get(user=instance)
        return {
            "username": instance.username,
            "email": instance.email,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "profile": PatientProfileSerializer(profile).data,
        }


class CompleteProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = [
            "date_of_birth",
            "gender",
            "phone_number",
            "height",
            "weight",
            "blood_type",
            "allergies",
        ]

    def create(self, validated_data):
        return PatientProfile.objects.create(**validated_data)