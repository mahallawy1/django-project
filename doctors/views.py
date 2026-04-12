from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsDoctor
from users.permissions import IsReceptionist
from users.permissions import IsPatient

from doctors.models import Doctor, DoctorSchedule, DoctorException
from django.db import transaction
from doctors.serializers import CreateAvailabilityRequestSerializer, PatchAvailabilityRequestSerializer, ExceptionInputSerializer
from doctors.services import replace_week_schedule, patch_schedule_days, patch_single_availability, create_exceptions


def _doctor_exists(doctor_id):
    return Doctor.objects.filter(id=doctor_id).exists()


@api_view(['GET'])
def get_all_doctors(request):
    doctors = Doctor.objects.select_related('user_id').all()

    doctor_list = [
        {
            'id': doctor.id,
            'user_id': doctor.user_id_id,
            'specialization': doctor.specialization,
            'email': doctor.user_id.email,
        }
        for doctor in doctors
    ]
    return Response({'status': 'success', 'doctors': doctor_list})


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsReceptionist])
def create_doctor_availability(request, doctor_id):
    if not _doctor_exists(doctor_id):
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    if request.method == 'DELETE':
        deleted_count, _ = DoctorSchedule.objects.filter(doctor_id=doctor_id).delete()
        if deleted_count == 0:
            return Response({'status': 'error', 'message': 'No availabilities found for this doctor'}, status=404)
        return Response({'status': 'success', 'message': 'All availabilities deleted successfully'})

    if request.method == 'GET':
        schedules = DoctorSchedule.objects.filter(doctor_id=doctor_id)
        schedule_list = [
            {
                'id': schedule.id,
                'day_of_week': schedule.day_of_week,
                'start_time': schedule.start_time,
                'end_time': schedule.end_time,
            }
            for schedule in schedules
        ]
        return Response({'status': 'success', 'availabilities': schedule_list})

    serializer = CreateAvailabilityRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    with transaction.atomic():
        replace_week_schedule(
            doctor_id=doctor_id,
            similar_weekdays=payload['similar_weekdays'],
            availability_items=payload['availability'],
        )

    return Response({'status': 'success', 'message': 'Availability created successfully'})


@api_view(['PATCH'])
@permission_classes([IsReceptionist])
def availability_detail(request, doctor_id, availability_id):
    if not _doctor_exists(doctor_id):
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    serializer = PatchAvailabilityRequestSerializer(data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    payload = serializer.validated_data

    with transaction.atomic():
        patch_schedule_days(
            doctor_id=doctor_id,
            similar_weekdays=payload.get('similar_weekdays'),
            availability_items=payload.get('availability'),
        )

        if any(field in payload for field in ('start_time', 'end_time')):
            _,  error = patch_single_availability(
                doctor_id=doctor_id,
                availability_id=availability_id,
                start_time=payload.get('start_time'),
                end_time=payload.get('end_time'),
            )
            if error:
                status_code = 404 if error == 'Availability not found' else 400
                return Response({'status': 'error', 'message': error}, status=status_code)

    return Response({'status': 'success', 'message': 'Availability updated successfully'})


@api_view(['POST'])
@permission_classes([IsReceptionist])
def create_doctor_exception(request, doctor_id):
    if not _doctor_exists(doctor_id):
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    serializer = ExceptionInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        with transaction.atomic():
            create_exceptions(doctor_id=doctor_id, exceptions_items=[serializer.validated_data])
    except ValueError as exc:
        return Response({'status': 'error', 'message': str(exc)}, status=400)

    return Response({'status': 'success', 'message': 'Exception created successfully'})


@api_view(['DELETE'])
@permission_classes([IsReceptionist])
def delete_doctor_exception(request, doctor_id, exception_id):
    if not _doctor_exists(doctor_id):
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    deleted_count, _ = DoctorException.objects.filter(id=exception_id, doctor_id=doctor_id).delete()
    if deleted_count == 0:
        return Response({'status': 'error', 'message': 'Exception not found'}, status=404)
    return Response({'status': 'success', 'message': 'Exception deleted successfully'})
        
