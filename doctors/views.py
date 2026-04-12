from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from doctors.models import Doctor, DoctorSchedule, DoctorException
from django.db import transaction
from doctors.serializers import CreateAvailabilityRequestSerializer, PatchAvailabilityRequestSerializer, ExceptionInputSerializer
from doctors.services import replace_week_schedule, patch_schedule_days, patch_single_availability, create_exceptions
from users.permissions import IsDoctor


def _get_current_doctor(request):
    if not request.user or not request.user.is_authenticated:
        return None
    return Doctor.objects.filter(user_id=request.user).select_related('user_id').first()


def _parse_iso_date(value):
    if value in (None, ''):
        return None, None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date(), None
    except (TypeError, ValueError):
        return None, 'date must be in YYYY-MM-DD format.'


def _date_to_schedule_day(work_date):
    return (work_date.isoweekday() + 1) % 7


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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDoctor])
def get_doctor_me(request):
    doctor = _get_current_doctor(request)
    if not doctor:
        return Response({'status': 'error', 'message': 'Doctor profile not found'}, status=404)

    user = doctor.user_id
    return Response(
        {
            'status': 'success',
            'doctor': {
                'id': doctor.id,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'specialization': doctor.specialization,
                'session_duration': doctor.session_duration,
                'buffer_time': doctor.buffer_time,
            },
        }
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDoctor])
def get_doctor_schedule_me(request):
    doctor = _get_current_doctor(request)
    if not doctor:
        return Response({'status': 'error', 'message': 'Doctor profile not found'}, status=404)

    date_value, date_error = _parse_iso_date(request.query_params.get('date'))
    if date_error:
        return Response({'status': 'error', 'message': date_error}, status=400)

    if date_value:
        exception_item = DoctorException.objects.filter(
            doctor_id=doctor.id, date=date_value
        ).first()

        schedule_day = _date_to_schedule_day(date_value)
        schedule_item = DoctorSchedule.objects.filter(
            doctor_id=doctor.id, day_of_week=schedule_day
        ).first()

        if exception_item and exception_item.type == 'VACATION_DAY':
            availability = None
        elif exception_item and exception_item.type == 'EXTRA_WORKING_DAY':
            availability = {
                'start_time': exception_item.start_time,
                'end_time': exception_item.end_time,
            }
        elif schedule_item:
            availability = {
                'start_time': schedule_item.start_time,
                'end_time': schedule_item.end_time,
            }
        else:
            availability = None

        return Response(
            {
                'status': 'success',
                'date': date_value,
                'availability': availability,
                'exception': (
                    {
                        'id': exception_item.id,
                        'type': exception_item.type,
                        'start_time': exception_item.start_time,
                        'end_time': exception_item.end_time,
                    }
                    if exception_item
                    else None
                ),
            }
        )

    schedules = DoctorSchedule.objects.filter(doctor_id=doctor.id).order_by('day_of_week')
    exceptions = DoctorException.objects.filter(doctor_id=doctor.id).order_by('date')

    schedule_list = [
        {
            'id': schedule.id,
            'day_of_week': schedule.day_of_week,
            'start_time': schedule.start_time,
            'end_time': schedule.end_time,
        }
        for schedule in schedules
    ]
    exception_list = [
        {
            'id': exception.id,
            'date': exception.date,
            'type': exception.type,
            'start_time': exception.start_time,
            'end_time': exception.end_time,
        }
        for exception in exceptions
    ]

    return Response(
        {
            'status': 'success',
            'schedules': schedule_list,
            'exceptions': exception_list,
        }
    )


@api_view(['GET', 'POST', 'DELETE'])
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
            _, error = patch_single_availability(
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
def delete_doctor_exception(request, doctor_id, exception_id):
    if not _doctor_exists(doctor_id):
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    deleted_count, _ = DoctorException.objects.filter(id=exception_id, doctor_id=doctor_id).delete()
    if deleted_count == 0:
        return Response({'status': 'error', 'message': 'Exception not found'}, status=404)
    return Response({'status': 'success', 'message': 'Exception deleted successfully'})
        
