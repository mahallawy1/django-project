from django.db import IntegrityError

from doctors.models import DoctorException, DoctorSchedule

WEEKDAY_DAYS = [1, 2, 3, 4, 5]


def _create_schedule_rows(doctor_id, days, start_time, end_time):
    DoctorSchedule.objects.bulk_create(
        [
            DoctorSchedule(
                doctor_id=doctor_id,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time,
            )
            for day in days
        ]
    )


def replace_week_schedule(doctor_id, similar_weekdays, availability_items):
    DoctorSchedule.objects.filter(doctor_id=doctor_id).delete()
    if similar_weekdays:
        item = availability_items[0]
        _create_schedule_rows(doctor_id, WEEKDAY_DAYS, item['start_time'], item['end_time'])
    else:
        for item in availability_items:
            DoctorSchedule.objects.create(
                doctor_id=doctor_id,
                day_of_week=item['day_of_week'],
                start_time=item['start_time'],
                end_time=item['end_time'],
            )


def patch_schedule_days(doctor_id, similar_weekdays=None, availability_items=None):
    if availability_items is None:
        return

    if similar_weekdays:
        item = availability_items[0]
        DoctorSchedule.objects.filter(doctor_id=doctor_id, day_of_week__in=WEEKDAY_DAYS).delete()
        _create_schedule_rows(doctor_id, WEEKDAY_DAYS, item['start_time'], item['end_time'])
        return

    for item in availability_items:
        DoctorSchedule.objects.update_or_create(
            doctor_id=doctor_id,
            day_of_week=item['day_of_week'],
            defaults={'start_time': item['start_time'], 'end_time': item['end_time']},
        )


def patch_single_availability(doctor_id, availability_id, start_time=None, end_time=None):
    schedule = DoctorSchedule.objects.filter(id=availability_id, doctor_id=doctor_id).first()
    if not schedule:
        return None, 'Availability not found'

    if start_time is not None:
        schedule.start_time = start_time
    if end_time is not None:
        schedule.end_time = end_time

    if schedule.start_time >= schedule.end_time:
        return None, 'start_time must be earlier than end_time'

    try:
        schedule.save()
    except IntegrityError:
        return None, 'A schedule for this day already exists'

    return schedule, None


def create_exceptions(doctor_id, exceptions_items):
    if not exceptions_items:
        return

    exception_dates = [item['date'] for item in exceptions_items]
    if len(set(exception_dates)) != len(exception_dates):
        raise ValueError('Duplicate exception dates in request. Update the existing exception instead of creating another one.')

    existing_dates = set(
        DoctorException.objects.filter(doctor_id=doctor_id, date__in=exception_dates).values_list('date', flat=True)
    )
    if existing_dates:
        existing_date = min(existing_dates).isoformat()
        raise ValueError(f'An exception already exists on {existing_date}. Update it instead of creating another one.')

    try:
        for item in exceptions_items:
            DoctorException.objects.create(
                doctor_id=doctor_id,
                date=item['date'],
                type=item['type'],
                start_time=item.get('start_time'),
                end_time=item.get('end_time'),
            )
    except IntegrityError:
        raise ValueError('An exception for this date already exists. Update it instead of creating another one.')
