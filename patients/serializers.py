from users.models import User
from users.serializers import UserSerializer


class patientRegSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ["username", "password", "email", "first_name", "last_name"]
        extra_kwargs = {"password": {"write_only": True}}
    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=User.Role.PATIENT)