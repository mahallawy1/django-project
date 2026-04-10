from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response

from doctors.models import Doctor, DoctorSchedule, DoctorException
from django.utils.dateparse import parse_time
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



@api_view(['POST'])
def set_doctor_schedule(request, doctor_id):
    """
    Set the availability schedule for a doctor.
    Expects a JSON payload with the following structure:
    {
        "doctor_id": 1,
        "equal": "true", # or "false" to indicate if the schedule is the same for all days
        "availability": [
            {
                "day_of_week": "0", # 0 for Saturday, 1 for Sunday, ..., 6 for Friday
                "start_time": "09:00",
                "end_time": "17:00"
            },
            {
                "day_of_week": "1",
                "start_time": "10:00",
                "end_time": "16:00"
            },
            ...
        ],
        "exceptions": [
            {
                "date": "2024-12-25",
                "type": "VACATION_DAY" # or "EXTRA_WORKING_DAY"
                "start_time": "", # Optional, required if type is "EXTRA_WORKING_DAY"
                "end_time": "" # Optional, required if type is "EXTRA_WORKING_DAY"
            }
        ]
    }
            
    """
    try:
        data = request.data
        doctor_id = data.get('doctor_id')
        equal = data.get('equal') == 'true'
        availability = data.get('availability', [])
        exceptions = data.get('exceptions', [])
        
        # Clear existing schedules if equal is True
        if equal:
            DoctorSchedule.objects.filter(doctor_id=doctor_id).delete()
        
        # Add new schedules
        for availability_item in availability:
            DoctorSchedule.objects.create(
                doctor_id=doctor_id,
                day_of_week=int(availability_item['day_of_week']),
                start_time=parse_time(availability_item['start_time']),
                end_time=parse_time(availability_item['end_time'])
            )
        
        # Add exceptions
        for exception_item in exceptions:
            DoctorException.objects.create(
                doctor_id=doctor_id,
                date=exception_item['date'],
                type=exception_item['type'],
                start_time=parse_time(exception_item.get('start_time')) if exception_item.get('start_time') else None,
                end_time=parse_time(exception_item.get('end_time')) if exception_item.get('end_time') else None
            )
        
        return Response({'status': 'success', 'message': 'Schedule updated successfully'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)
    