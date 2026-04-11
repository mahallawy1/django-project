from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from .models import Appointment, Consultation
from .serializers import ConsultationRecordSerializer
from users.permissions import IsDoctor, IsPatient


@permission_classes([IsDoctor | IsPatient])
@api_view(['GET'])
def consultation_read(request, id):
    appointment = get_object_or_404(Appointment, pk=id)

    # Patients may only see their own appointment's consultation
    if request.user.role == 'PATIENT' and appointment.patient != request.user:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    consultation = get_object_or_404(Consultation, appointment=appointment)
    serializer = ConsultationRecordSerializer(consultation)
    return Response(serializer.data)


@permission_classes([IsDoctor])
@api_view(['POST', 'PATCH'])
def consultation_write(request, id):
    appointment = get_object_or_404(Appointment, pk=id)

    if request.method == 'POST':
        data = {**request.data, 'appointment': appointment.pk}
        serializer = ConsultationRecordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # PATCH
    consultation = get_object_or_404(Consultation, appointment=appointment)
    serializer = ConsultationRecordSerializer(consultation, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)