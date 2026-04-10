from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from users.serializers import UserSerializer
from users.permissions import IsPatient
from .serializers import patientRegSerializer

# Create your views here.
# sign up for pationt
@api_view(["POST"])
@permission_classes([AllowAny])
def patient_register(request):
    serializer = patientRegSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#  ########################################

# to update pationt profile as "/me"
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated, IsPatient])
def patient_me(request):
    if request.method == "GET":
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = UserSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)