from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from patients.models import PatientProfile
from users.serializers import UserSerializer
from users.permissions import IsPatient
from .serializers import PatientProfileSerializer, patientRegSerializer
from django.db import transaction
from appointments.models import Appointment
from appointments.serializers import AppointmentSerializer
from receptionist.models import Slot
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
    profile = PatientProfile.objects.filter(user=request.user).first()
    if not profile:
        return Response(
            {"error": "profile not there"},
            status=status.HTTP_404_NOT_FOUND
        )
    if request.method == "GET":
        serializer = PatientProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method == "PATCH":
        serializer = PatientProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


    # #####################################
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPatient])
def book_appointment(request):
    slot_id = request.data.get("slot_id")
    if not slot_id:
        return Response(
            {"error": "plz the slot id is not inserted"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    slot = Slot.objects.filter(id=slot_id).first()
    if not slot:
        return Response(
            {"error": "sltot not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if slot.is_booked:
        return Response(
            {"error": "this slot was already booked"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ################################# overlab check for no double booking for diffrent doctor at the same time
    isoverLaped = Appointment.objects.filter(
        patient=request.user,
        slot__start_datetime=slot.start_datetime,
        ).exclude(
    status=Appointment.Status.CANCELLED
    ).exists()
    if isoverLaped:
        return Response({"error": "you already have appointment with onther doctor for the same time (you have zehaimar or what! )"},status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        slot.is_booked = True
        slot.save()
        appointment = Appointment.objects.create(
            patient=request.user,
            slot=slot,
            status=Appointment.Status.SCHEDULED,
        )
    serializer = AppointmentSerializer(appointment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPatient])
def my_appointments(request):
    appointments = Appointment.objects.filter(patient=request.user)
    serializer = AppointmentSerializer(appointments, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def appointment_detail(request, appointment_id):
    appointment = Appointment.objects.filter(
        id=appointment_id,
        patient=request.user,
    ).first()
    if not appointment:
        return Response(
            {"error": "no app for this patient"},
            status=status.HTTP_404_NOT_FOUND,
        )
    serializer = AppointmentSerializer(appointment)
    return Response(serializer.data)