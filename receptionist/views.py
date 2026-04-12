from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from users.permissions import IsPatient, IsReceptionist

from doctors.models import Doctor, DoctorSchedule, DoctorException
from receptionist.models import Slot


def _parse_iso_date(value, field_name):
    if value in (None, ''):
        return None, None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date(), None
    except (TypeError, ValueError):
        return None, f'{field_name} must be in YYYY-MM-DD format.'


def _iter_dates(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _build_day_slots(doctor, work_date, start_time, end_time):
    if start_time >= end_time:
        return []

    session_delta = timedelta(minutes=doctor.session_duration)
    buffer_delta = timedelta(minutes=doctor.buffer_time)
    tz = timezone.get_current_timezone()

    day_start = timezone.make_aware(datetime.combine(work_date, start_time), tz)
    day_end = timezone.make_aware(datetime.combine(work_date, end_time), tz)

    generated = []
    current_start = day_start
    while current_start + session_delta <= day_end:
        slot_end = current_start + session_delta
        generated.append(
            Slot(
                doctor=doctor,
                start_datetime=current_start,
                end_datetime=slot_end,
                is_booked=False,
            )
        )
        current_start = slot_end + buffer_delta
    return generated


def _get_requested_date_range(start_raw, end_raw):
    start_date, start_error = _parse_iso_date(start_raw, 'start_date')
    if start_error:
        return None, None, start_error

    end_date, end_error = _parse_iso_date(end_raw, 'end_date')
    if end_error:
        return None, None, end_error

    if start_date is None:
        start_date = timezone.localdate()
    if end_date is None:
        end_date = start_date + timedelta(days=6)

    if end_date < start_date:
        return None, None, 'end_date must be greater than or equal to start_date.'

    return start_date, end_date, None


def _generate_slots_for_range(doctor, start_date, end_date, delete_unbooked=False):
    schedules_by_day = {
        schedule.day_of_week: schedule
        for schedule in DoctorSchedule.objects.filter(doctor_id=doctor.id)
    }
    exceptions_by_date = {
        exception.date: exception
        for exception in DoctorException.objects.filter(
            doctor_id=doctor.id,
            date__gte=start_date,
            date__lte=end_date,
        )
    }

    with transaction.atomic():
        deleted_count = 0
        if delete_unbooked:
            deleted_count, _ = Slot.objects.filter(
                doctor_id=doctor.id,
                start_datetime__date__gte=start_date,
                start_datetime__date__lte=end_date,
                is_booked=False,
            ).delete()

        new_slots = []
        for current_date in _iter_dates(start_date, end_date):
            exception_item = exceptions_by_date.get(current_date)

            if exception_item and exception_item.type == 'VACATION_DAY':
                continue

            if exception_item and exception_item.type == 'EXTRA_WORKING_DAY':
                day_start = exception_item.start_time
                day_end = exception_item.end_time
                if not day_start or not day_end:
                    continue
            else:
                schedule_day = (current_date.isoweekday() + 1) % 7
                schedule_item = schedules_by_day.get(schedule_day)
                if not schedule_item:
                    continue
                day_start = schedule_item.start_time
                day_end = schedule_item.end_time

            if not day_start or not day_end:
                continue
            new_slots.extend(_build_day_slots(doctor, current_date, day_start, day_end))

        if new_slots:
            Slot.objects.bulk_create(new_slots, ignore_conflicts=True)

    return deleted_count, len(new_slots)


def _ensure_doctor_slots_for_range(doctor, start_date, end_date):
    existing_dates = set(
        Slot.objects.filter(
            doctor_id=doctor.id,
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
        )
        .values_list('start_datetime__date', flat=True)
        .distinct()
    )

    generated_count = 0
    missing_dates_count = 0
    range_start = None

    for current_date in _iter_dates(start_date, end_date):
        if current_date in existing_dates:
            if range_start:
                _, created_count = _generate_slots_for_range(
                    doctor,
                    range_start,
                    current_date - timedelta(days=1),
                    delete_unbooked=False,
                )
                generated_count += created_count
                range_start = None
            continue

        missing_dates_count += 1
        if range_start is None:
            range_start = current_date

    if range_start:
        _, created_count = _generate_slots_for_range(
            doctor,
            range_start,
            end_date,
            delete_unbooked=False,
        )
        generated_count += created_count

    return generated_count, missing_dates_count


@api_view(['GET'])
@permission_classes([IsPatient | IsReceptionist])
def get_doctor_slots(request, doctor_id):
    doctor = Doctor.objects.filter(id=doctor_id).first()
    if not doctor:
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    start_date, end_date, date_error = _get_requested_date_range(
        request.query_params.get('start_date'),
        request.query_params.get('end_date'),
    )
    if date_error:
        return Response({'status': 'error', 'message': date_error}, status=400)

    slots = Slot.objects.filter(
        doctor_id=doctor_id,
        start_datetime__date__gte=start_date,
        start_datetime__date__lte=end_date,
    ).order_by('start_datetime')

    slot_list = [
        {
            'id': slot.id,
            'doctor_id': slot.doctor_id,
            'start_datetime': slot.start_datetime,
            'end_datetime': slot.end_datetime,
            'is_booked': slot.is_booked,
        }
        for slot in slots
    ]

    return Response(
        {
            'status': 'success',
            'message': 'Slots retrieved successfully',
            'start_date': start_date,
            'end_date': end_date,
            'count': len(slot_list),
            'slots': slot_list,
        }
    )


@api_view(['POST'])
@permission_classes([IsReceptionist])
def regenerate_slots(request, doctor_id):
    doctor = Doctor.objects.filter(id=doctor_id).first()
    if not doctor:
        return Response({'status': 'error', 'message': 'Doctor not found'}, status=404)

    start_date, end_date, date_error = _get_requested_date_range(
        request.data.get('start_date'),
        request.data.get('end_date'),
    )
    if date_error:
        return Response({'status': 'error', 'message': date_error}, status=400)

    deleted_count, generated_count = _generate_slots_for_range(
        doctor,
        start_date,
        end_date,
        delete_unbooked=True,
    )

    return Response(
        {
            'status': 'success',
            'message': 'Slots regenerated successfully',
            'start_date': start_date,
            'end_date': end_date,
            'deleted_unbooked_slots': deleted_count,
            'generated_slots': generated_count,
        }
    )


@api_view(['POST'])
@permission_classes([IsReceptionist])
def regenerate_all_doctors_next_7_days_slots(request):
    start_date = timezone.localdate()
    end_date = start_date + timedelta(days=6)

    doctors_total = 0
    doctors_skipped = 0
    doctors_regenerated = 0
    total_missing_dates = 0
    total_generated_slots = 0

    for doctor in Doctor.objects.all():
        doctors_total += 1
        generated_count, missing_dates_count = _ensure_doctor_slots_for_range(
            doctor,
            start_date,
            end_date,
        )

        total_missing_dates += missing_dates_count
        total_generated_slots += generated_count

        if missing_dates_count == 0:
            doctors_skipped += 1
        else:
            doctors_regenerated += 1

    return Response(
        {
            'status': 'success',
            'message': 'Next 7 days slots ensured for all doctors',
            'start_date': start_date,
            'end_date': end_date,
            'doctors_total': doctors_total,
            'doctors_skipped_already_had_slots': doctors_skipped,
            'doctors_regenerated_missing_slots': doctors_regenerated,
            'missing_dates_detected': total_missing_dates,
            'generated_slots': total_generated_slots,
        }
    )