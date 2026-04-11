from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response

from doctors.models import Doctor, DoctorSchedule, DoctorException
from django.utils.dateparse import parse_time
from django.db import transaction
from datetime import time
from django.utils import timezone

# Create your views here.
@api_view(['GET'])
def get_all_doctors(request):
    doctors = Doctor.objects.all()
    doctor_list = []
    for doctor in doctors:
        doctor_list.append({
            'user_id': doctor.user_id,
            'specialization': doctor.specialization,
            'email': doctor.email,
            'phone_number': doctor.phone_number
        })
    return Response({'status': 'success', 'doctors': doctor_list})



@api_view(['POST', 'PATCH', 'DELETE'])
def set_doctor_schedule(request, doctor_id):
    return Response({'status': 'error', 'message': 'Deprecated endpoint'}, status=410)


WEEKDAY_DAYS = [1, 2, 3, 4, 5]


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ('true', '1', 'yes'):
            return True
        if lowered in ('false', '0', 'no'):
            return False
    return None


def _normalize_exception_type(raw_type):
    if raw_type in ('VACATION', 'VACATION_DAY', 'DAY_OFF'):
        return 'VACATION'
    if raw_type in ('EXTRA_WORKING_DAY', 'WORKING_DAY'):
        return 'EXTRA_WORKING_DAY'
    return None


def _parse_availability_item(item, require_day=True):
    if not isinstance(item, dict):
        return None, 'Each availability item must be an object'

    start_raw = item.get('start_time', item.get('start'))
    end_raw = item.get('end_time', item.get('end'))
    if start_raw is None or end_raw is None:
        return None, 'Each availability item must include start_time and end_time'

    start_time = parse_time(str(start_raw))
    end_time = parse_time(str(end_raw))
    if not start_time or not end_time:
        return None, 'Invalid start_time or end_time format. Use HH:MM'
    if start_time >= end_time:
        return None, 'start_time must be earlier than end_time'

    day_of_week = item.get('day_of_week')
    if require_day:
        try:
            day_of_week = int(day_of_week)
        except (TypeError, ValueError):
            return None, 'day_of_week must be an integer'
    elif day_of_week is not None:
        try:
            day_of_week = int(day_of_week)
        except (TypeError, ValueError):
            return None, 'day_of_week must be an integer'

    return {'day_of_week': day_of_week, 'start_time': start_time, 'end_time': end_time}, None


def _add_exceptions_for_doctor(doctor_id, exceptions_payload):
    if exceptions_payload is None:
        return None
    if not isinstance(exceptions_payload, list):
        return 'exceptions must be an array'

    for exception_item in exceptions_payload:
        if not isinstance(exception_item, dict):
            return 'Each exception item must be an object'
        date_value = exception_item.get('date')
        if not date_value:
            return 'Exception date is required'

        normalized_type = _normalize_exception_type(exception_item.get('type'))
        if not normalized_type:
            return 'Exception type must be DAY_OFF, WORKING_DAY, VACATION, or EXTRA_WORKING_DAY'

        start_raw = exception_item.get('start_time', exception_item.get('start'))
        end_raw = exception_item.get('end_time', exception_item.get('end'))
        start_time = parse_time(str(start_raw)) if start_raw else None
        end_time = parse_time(str(end_raw)) if end_raw else None

        if normalized_type == 'EXTRA_WORKING_DAY':
            if not start_time or not end_time:
                return 'WORKING_DAY requires start/end time'
            if start_time >= end_time:
                return 'Exception start_time must be earlier than end_time'
        else:
            if start_time and end_time and start_time >= end_time:
                return 'Exception start_time must be earlier than end_time'
            start_time = start_time or time(0, 0)
            end_time = end_time or time(0, 0)

        DoctorException.objects.create(
            doctor_id=doctor_id,
            date=date_value,
            type=normalized_type,
            start_time=start_time,
            end_time=end_time
        )
    return None


@api_view(['POST'])
def create_doctor_availability(request, doctor_id):
    if not Doctor.objects.filter(id=doctor_id).exists():
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    data = request.data
    availability = data.get('availability')
    similar_weekdays_raw = data.get('similar_weekdays')
    similar_weekdays = _parse_bool(similar_weekdays_raw)
    exceptions = data.get('exceptions')

    if similar_weekdays is None:
        return Response({'status': 'error', 'message': 'similar_weekdays is required for POST'}, status=400)
    if not isinstance(availability, list) or len(availability) == 0:
        return Response({'status': 'error', 'message': 'availability is required for POST'}, status=400)

    try:
        with transaction.atomic():
            DoctorSchedule.objects.filter(doctor_id=doctor_id).delete()

            if similar_weekdays:
                if len(availability) != 1:
                    return Response({'status': 'error', 'message': 'When similar_weekdays is true, provide exactly one availability item'}, status=400)
                parsed_item, error = _parse_availability_item(availability[0], require_day=False)
                if error:
                    return Response({'status': 'error', 'message': error}, status=400)

                for day in WEEKDAY_DAYS:
                    DoctorSchedule.objects.create(
                        doctor_id=doctor_id,
                        day_of_week=day,
                        start_time=parsed_item['start_time'],
                        end_time=parsed_item['end_time']
                    )
            else:
                parsed_items = []
                for item in availability:
                    parsed_item, error = _parse_availability_item(item, require_day=True)
                    if error:
                        return Response({'status': 'error', 'message': error}, status=400)
                    if parsed_item['day_of_week'] not in WEEKDAY_DAYS:
                        return Response({'status': 'error', 'message': 'day_of_week must be one of 1,2,3,4,5 when similar_weekdays is false'}, status=400)
                    parsed_items.append(parsed_item)

                unique_days = {item['day_of_week'] for item in parsed_items}
                if len(parsed_items) != 5 or unique_days != set(WEEKDAY_DAYS):
                    return Response({'status': 'error', 'message': 'When similar_weekdays is false, provide exactly days 1,2,3,4,5 once each'}, status=400)

                for item in parsed_items:
                    DoctorSchedule.objects.create(
                        doctor_id=doctor_id,
                        day_of_week=item['day_of_week'],
                        start_time=item['start_time'],
                        end_time=item['end_time']
                    )

            error = _add_exceptions_for_doctor(doctor_id, exceptions)
            if error:
                return Response({'status': 'error', 'message': error}, status=400)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)

    return Response({'status': 'success', 'message': 'Availability created successfully'})


@api_view(['PATCH', 'DELETE'])
def availability_detail(request, doctor_id, availability_id):
    if not Doctor.objects.filter(id=doctor_id).exists():
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    if request.method == 'DELETE':
        deleted_count, _ = DoctorSchedule.objects.filter(id=availability_id, doctor_id=doctor_id).delete()
        if deleted_count == 0:
            return Response({'status': 'error', 'message': 'Availability not found'}, status=404)
        return Response({'status': 'success', 'message': 'Availability deleted successfully'})

    data = request.data
    availability = data.get('availability')
    similar_weekdays_raw = data.get('similar_weekdays')
    similar_weekdays = _parse_bool(similar_weekdays_raw) if similar_weekdays_raw is not None else None
    exceptions = data.get('exceptions')

    direct_fields = any(field in data for field in ('day_of_week', 'start_time', 'end_time', 'start', 'end'))
    if availability is None and similar_weekdays is None and exceptions is None and not direct_fields:
        return Response({'status': 'error', 'message': 'Provide at least one field to update'}, status=400)

    if similar_weekdays is not None and availability is None:
        return Response({'status': 'error', 'message': 'availability is required when similar_weekdays is provided'}, status=400)

    try:
        with transaction.atomic():
            if availability is not None:
                if not isinstance(availability, list) or len(availability) == 0:
                    return Response({'status': 'error', 'message': 'availability must be a non-empty array'}, status=400)

                if similar_weekdays is True:
                    if len(availability) != 1:
                        return Response({'status': 'error', 'message': 'When similar_weekdays is true, provide exactly one availability item'}, status=400)
                    parsed_item, error = _parse_availability_item(availability[0], require_day=False)
                    if error:
                        return Response({'status': 'error', 'message': error}, status=400)

                    DoctorSchedule.objects.filter(doctor_id=doctor_id, day_of_week__in=WEEKDAY_DAYS).delete()
                    for day in WEEKDAY_DAYS:
                        DoctorSchedule.objects.create(
                            doctor_id=doctor_id,
                            day_of_week=day,
                            start_time=parsed_item['start_time'],
                            end_time=parsed_item['end_time']
                        )
                else:
                    for item in availability:
                        parsed_item, error = _parse_availability_item(item, require_day=True)
                        if error:
                            return Response({'status': 'error', 'message': error}, status=400)
                        if parsed_item['day_of_week'] not in WEEKDAY_DAYS:
                            return Response({'status': 'error', 'message': 'day_of_week must be one of 1,2,3,4,5'}, status=400)

                        DoctorSchedule.objects.update_or_create(
                            doctor_id=doctor_id,
                            day_of_week=parsed_item['day_of_week'],
                            defaults={
                                'start_time': parsed_item['start_time'],
                                'end_time': parsed_item['end_time'],
                            }
                        )

            if direct_fields:
                schedule = DoctorSchedule.objects.filter(id=availability_id, doctor_id=doctor_id).first()
                if not schedule:
                    return Response({'status': 'error', 'message': 'Availability not found'}, status=404)

                day_of_week = schedule.day_of_week
                if 'day_of_week' in data:
                    try:
                        day_of_week = int(data.get('day_of_week'))
                    except (TypeError, ValueError):
                        return Response({'status': 'error', 'message': 'day_of_week must be an integer'}, status=400)
                    if day_of_week not in WEEKDAY_DAYS:
                        return Response({'status': 'error', 'message': 'day_of_week must be one of 1,2,3,4,5'}, status=400)

                start_raw = data.get('start_time', data.get('start'))
                end_raw = data.get('end_time', data.get('end'))
                start_time = parse_time(str(start_raw)) if start_raw is not None else schedule.start_time
                end_time = parse_time(str(end_raw)) if end_raw is not None else schedule.end_time

                if (start_raw is not None and not start_time) or (end_raw is not None and not end_time):
                    return Response({'status': 'error', 'message': 'Invalid start_time or end_time format. Use HH:MM'}, status=400)
                if start_time >= end_time:
                    return Response({'status': 'error', 'message': 'start_time must be earlier than end_time'}, status=400)

                schedule.day_of_week = day_of_week
                schedule.start_time = start_time
                schedule.end_time = end_time
                schedule.save()

            error = _add_exceptions_for_doctor(doctor_id, exceptions)
            if error:
                return Response({'status': 'error', 'message': error}, status=400)
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)

    return Response({'status': 'success', 'message': 'Availability updated successfully'})


@api_view(['POST'])
def create_doctor_exception(request, doctor_id):
    if not Doctor.objects.filter(id=doctor_id).exists():
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    error = _add_exceptions_for_doctor(doctor_id, [request.data])
    if error:
        return Response({'status': 'error', 'message': error}, status=400)

    return Response({'status': 'success', 'message': 'Exception created successfully'})


@api_view(['DELETE'])
def delete_doctor_exception(request, doctor_id, exception_id):
    if not Doctor.objects.filter(id=doctor_id).exists():
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    deleted_count, _ = DoctorException.objects.filter(id=exception_id, doctor_id=doctor_id).delete()
    if deleted_count == 0:
        return Response({'status': 'error', 'message': 'Exception not found'}, status=404)
    return Response({'status': 'success', 'message': 'Exception deleted successfully'})
        
