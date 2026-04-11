from datetime import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from receptionist.models import Slot

from .models import Appointment, AppointmentAudit


class IsDoctorReceptionistAdmin(BasePermission):
	def has_permission(self, request, view):
		return request.user and getattr(request.user, 'role', None) in ('DOCTOR', 'RECEPTIONIST', 'ADMIN')


def _get_appointment(appointment_id):
	return (
		Appointment.objects.select_related('patient', 'slot', 'slot__doctor', 'slot__doctor__user_id')
		.filter(id=appointment_id)
		.first()
	)


def _validate_status_payload(request, expected_status):
	payload_status = request.data.get('status')
	if payload_status and payload_status != expected_status:
		return f'status must be {expected_status}.'
	return None


def _parse_iso_date(value, field_name):
	if value in (None, ''):
		return None, None
	try:
		return datetime.strptime(value, '%Y-%m-%d').date(), None
	except (TypeError, ValueError):
		return None, f'{field_name} must be in YYYY-MM-DD format.'


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def list_appointments(request):
	status_value = request.query_params.get('status')
	from_value, from_error = _parse_iso_date(request.query_params.get('from'), 'from')
	if from_error:
		return Response({'status': 'error', 'message': from_error}, status=400)
	to_value, to_error = _parse_iso_date(request.query_params.get('to'), 'to')
	if to_error:
		return Response({'status': 'error', 'message': to_error}, status=400)

	doctor_id = request.query_params.get('doctor_id')
	patient_name = request.query_params.get('patient_name')
	appointment_id = request.query_params.get('appointment_id')

	appointments = Appointment.objects.select_related(
		'patient', 'slot', 'slot__doctor', 'slot__doctor__user_id'
	)

	if appointment_id:
		appointments = appointments.filter(id=appointment_id)

	if status_value:
		appointments = appointments.filter(status=status_value)

	if from_value:
		appointments = appointments.filter(slot__start_datetime__date__gte=from_value)

	if to_value:
		appointments = appointments.filter(slot__start_datetime__date__lte=to_value)

	if doctor_id:
		appointments = appointments.filter(slot__doctor_id=doctor_id)

	if patient_name:
		appointments = appointments.filter(
			Q(patient__first_name__icontains=patient_name)
			| Q(patient__last_name__icontains=patient_name)
			| Q(patient__username__icontains=patient_name)
		)

	appointments = appointments.order_by('slot__start_datetime')

	appointment_list = []
	for appointment in appointments:
		doctor = appointment.slot.doctor
		doctor_user = doctor.user_id
		patient = appointment.patient
		appointment_list.append(
			{
				'id': appointment.id,
				'status': appointment.status,
				'check_in_time': appointment.check_in_time,
				'created_at': appointment.created_at,
				'slot': {
					'id': appointment.slot_id,
					'start_datetime': appointment.slot.start_datetime,
					'end_datetime': appointment.slot.end_datetime,
					'doctor_id': doctor.id,
				},
				'doctor': {
					'id': doctor.id,
					'user_id': doctor_user.id,
					'name': doctor_user.get_full_name().strip() or doctor_user.username,
				},
				'patient': {
					'id': patient.id,
					'name': patient.get_full_name().strip() or patient.username,
					'email': patient.email,
				},
			}
		)

	return Response(
		{
			'status': 'success',
			'count': len(appointment_list),
			'appointments': appointment_list,
		}
	)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def confirm_appointment(request, appointment_id):
	appointment = _get_appointment(appointment_id)
	if not appointment:
		return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

	status_error = _validate_status_payload(request, Appointment.Status.CONFIRMED)
	if status_error:
		return Response({'status': 'error', 'message': status_error}, status=400)

	if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW, Appointment.Status.COMPLETED]:
		return Response({'status': 'error', 'message': 'Cannot confirm this appointment in its current state'}, status=400)

	appointment.status = Appointment.Status.CONFIRMED
	appointment.save(update_fields=['status'])

	return Response({'status': 'success', 'message': 'Appointment confirmed'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def check_in_appointment(request, appointment_id):
	appointment = _get_appointment(appointment_id)
	if not appointment:
		return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

	status_error = _validate_status_payload(request, Appointment.Status.CHECKED_IN)
	if status_error:
		return Response({'status': 'error', 'message': status_error}, status=400)

	if appointment.status not in [Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED]:
		return Response({'status': 'error', 'message': 'Only scheduled or confirmed appointments can be checked in'}, status=400)

	appointment.status = Appointment.Status.CHECKED_IN
	appointment.check_in_time = timezone.now()
	appointment.save(update_fields=['status', 'check_in_time'])

	return Response({'status': 'success', 'message': 'Patient checked in'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def no_show_appointment(request, appointment_id):
	appointment = _get_appointment(appointment_id)
	if not appointment:
		return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

	status_error = _validate_status_payload(request, Appointment.Status.NO_SHOW)
	if status_error:
		return Response({'status': 'error', 'message': status_error}, status=400)

	if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED]:
		return Response({'status': 'error', 'message': 'Cannot mark no-show for this appointment in its current state'}, status=400)

	appointment.status = Appointment.Status.NO_SHOW
	appointment.save(update_fields=['status'])

	return Response({'status': 'success', 'message': 'Appointment marked as no-show'})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def cancel_appointment(request, appointment_id):
	appointment = _get_appointment(appointment_id)
	if not appointment:
		return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

	if appointment.status not in [Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED]:
		return Response(
			{'status': 'error', 'message': 'Only requested/scheduled or confirmed appointments can be cancelled'},
			status=400,
		)

	reason = request.data.get('reason')
	if not reason:
		return Response({'status': 'error', 'message': 'reason is required'}, status=400)

	with transaction.atomic():
		slot = appointment.slot
		appointment.status = Appointment.Status.CANCELLED
		appointment.save(update_fields=['status'])

		if slot.is_booked:
			slot.is_booked = False
			slot.save(update_fields=['is_booked'])

	return Response({'status': 'success', 'message': 'Appointment cancelled', 'reason': reason})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdmin])
def reschedule_appointment(request, appointment_id):
	appointment = _get_appointment(appointment_id)
	if not appointment:
		return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

	if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED, Appointment.Status.NO_SHOW]:
		return Response({'status': 'error', 'message': 'Cannot reschedule this appointment in its current state'}, status=400)

	new_slot_id = request.data.get('new_slot_id')
	reason = request.data.get('reason')

	if not new_slot_id:
		return Response({'status': 'error', 'message': 'new_slot_id is required'}, status=400)
	if not reason:
		return Response({'status': 'error', 'message': 'reason is required'}, status=400)

	new_slot = Slot.objects.filter(id=new_slot_id).first()
	if not new_slot:
		return Response({'status': 'error', 'message': 'New slot not found'}, status=404)
	if new_slot.is_booked:
		return Response({'status': 'error', 'message': 'New slot is already booked'}, status=400)
	if new_slot.id == appointment.slot_id:
		return Response({'status': 'error', 'message': 'New slot must be different from current slot'}, status=400)

	with transaction.atomic():
		old_slot = appointment.slot
		old_start_datetime = old_slot.start_datetime

		old_slot.is_booked = False
		old_slot.save(update_fields=['is_booked'])

		new_slot.is_booked = True
		new_slot.save(update_fields=['is_booked'])

		appointment.slot = new_slot
		appointment.save(update_fields=['slot'])

		AppointmentAudit.objects.create(
			appointment=appointment,
			changed_by=request.user,
			old_start_datetime=old_start_datetime,
			new_start_datetime=new_slot.start_datetime,
			reason=reason,
		)

	return Response({'status': 'success', 'message': 'Appointment rescheduled'})
