import csv
import requests
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime, timedelta
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from xhtml2pdf import pisa
from .models import Invoice, PaymentTransaction
import urllib.parse


from doctors.models import Doctor
from receptionist.models import Slot
from users.permissions import IsDoctor, IsPatient, IsReceptionist, IsAdmin

from .models import Appointment, AppointmentAudit, Consultation, Invoice, PaymentTransaction
from .serializers import ConsultationSerializer, InvoiceSerializer, PaymentTransactionSerializer


class IsDoctorReceptionistAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and getattr(request.user, 'role', None) in ('DOCTOR', 'RECEPTIONIST', 'ADMIN')

class IsDoctorReceptionistAdminPatient(BasePermission):
    def has_permission(self, request, view):
        return request.user and getattr(request.user, 'role', None) in ('DOCTOR', 'RECEPTIONIST', 'ADMIN', 'PATIENT')

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
@permission_classes([IsAdmin])
def appointment_analytics(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=6)

    counts = (
        Appointment.objects
        .filter(slot__start_datetime__date__gte=start_date, slot__start_datetime__date__lte=today)
        .values(date=TruncDate('slot__start_datetime'))
        .annotate(total=Count('id'))
        .order_by('date')
    )

    counts_by_date = {row['date']: row['total'] for row in counts}
    data = [
        {'date': (start_date + timedelta(days=i)).isoformat(), 'total': counts_by_date.get(start_date + timedelta(days=i), 0)}
        for i in range(7)
    ]

    return Response({'status': 'success', 'data': data})


@api_view(['GET'])
@permission_classes([IsAdmin])
def today_status_analytics(request):
    today = timezone.now().date()

    counts = (
        Appointment.objects
        .filter(slot__start_datetime__date=today)
        .values('status')
        .annotate(total=Count('id'))
    )

    total = sum(row['total'] for row in counts)

    data = [
        {
            'status': row['status'],
            'total': row['total'],
            'percentage': round(row['total'] / total * 100, 2) if total else 0,
        }
        for row in counts
    ]

    return Response({'status': 'success', 'date': today.isoformat(), 'total': total, 'data': data})


@api_view(['GET'])
@permission_classes([IsAdmin])
def analytics_export(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=6)

    daily_counts = (
        Appointment.objects
        .filter(slot__start_datetime__date__gte=start_date, slot__start_datetime__date__lte=today)
        .values(date=TruncDate('slot__start_datetime'))
        .annotate(total=Count('id'))
    )
    daily_by_date = {row['date']: row['total'] for row in daily_counts}

    status_counts = (
        Appointment.objects
        .filter(slot__start_datetime__date=today)
        .values('status')
        .annotate(total=Count('id'))
    )
    status_total = sum(row['total'] for row in status_counts)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="appointments_analytics_{today.isoformat()}.csv"'

    writer = csv.writer(response)

    writer.writerow(['date', 'total_appointments'])
    for i in range(7):
        day = start_date + timedelta(days=i)
        writer.writerow(['\t' + day.isoformat(), daily_by_date.get(day, 0)])

    writer.writerow([])

    writer.writerow(['status', 'total', 'percentage'])
    for row in status_counts:
        pct = round(row['total'] / status_total * 100, 2) if status_total else 0
        writer.writerow([row['status'], row['total'], pct])

    return response


@api_view(['GET'])
def appointment_detail(request, appointment_id):
    if not appointment_id:
        return Response({'status': 'error', 'message': 'appointment_id is required'}, status=400)

    appointment = _get_appointment(appointment_id)
    if not appointment:
        return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

    doctor = appointment.slot.doctor
    doctor_user = doctor.user_id
    patient = appointment.patient

    data = {
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

    return Response({'status': 'success', 'appointment': data})


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
        if appointment.slot is None:
            continue
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

    return Response({'status': 'success', 'count': len(appointment_list), 'appointments': appointment_list})


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
    appointment.check_in_time = appointment.slot.start_datetime
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
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdminPatient])
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
        appointment.slot = None
        appointment.save(update_fields=['slot'])    

    return Response({'status': 'success', 'message': 'Appointment cancelled', 'reason': reason})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctorReceptionistAdminPatient])
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reschedule_history(request, appointment_id):
    appointment = _get_appointment(appointment_id)
    if not appointment:
        return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

    user_role = getattr(request.user, 'role', None)
    is_owner = appointment.patient_id == request.user.id
    is_staff = user_role in ('DOCTOR', 'RECEPTIONIST', 'ADMIN')

    if not is_owner and not is_staff:
        return Response({'status': 'error', 'message': 'Not allowed to view this resource'}, status=403)

    if user_role == 'DOCTOR':
        doctor = Doctor.objects.filter(user_id=request.user).first()
        if not doctor or appointment.slot.doctor_id != doctor.id:
            return Response({'status': 'error', 'message': 'Not allowed to view this resource'}, status=403)

    audits = (
        AppointmentAudit.objects.select_related('changed_by')
        .filter(appointment_id=appointment_id)
        .order_by('-timestamp')
    )

    history = []
    for audit in audits:
        actor = audit.changed_by
        history.append(
            {
                'old_start_datetime': audit.old_start_datetime,
                'new_start_datetime': audit.new_start_datetime,
                'changed_by': {
                    'id': actor.id if actor else None,
                    'name': (actor.get_full_name().strip() or actor.username) if actor else None,
                    'role': getattr(actor, 'role', None) if actor else None,
                },
                'reason': audit.reason,
                'timestamp': audit.timestamp,
            }
        )

    return Response({'status': 'success', 'count': len(history), 'history': history})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDoctor | IsReceptionist])
def today_queue(request):
    doctor_id = request.query_params.get('doctor_id')
    date_raw = request.query_params.get('date')

    queue_date, date_error = _parse_iso_date(date_raw, 'date')
    if date_error:
        return Response({'status': 'error', 'message': date_error}, status=400)
    if queue_date is None:
        queue_date = timezone.localdate()

    if request.user.role == 'DOCTOR':
        doctor = Doctor.objects.filter(user_id=request.user).first()
        if not doctor:
            return Response({'status': 'error', 'message': 'Doctor profile not found'}, status=404)

        if doctor_id and str(doctor.id) != str(doctor_id):
            return Response({'status': 'error', 'message': 'Not allowed to view another doctor queue'}, status=403)
        doctor_id = doctor.id

    if not doctor_id:
        return Response({'status': 'error', 'message': 'doctor_id is required'}, status=400)

    appointments = (
        Appointment.objects.select_related('patient', 'slot', 'slot__doctor', 'slot__doctor__user_id')
        .filter(
            slot__doctor_id=doctor_id,
            slot__start_datetime__date=queue_date,
            status__in=[
                # Appointment.Status.SCHEDULED,
                Appointment.Status.CONFIRMED,
                Appointment.Status.CHECKED_IN,
            ],
        )
        .order_by('check_in_time', 'slot__start_datetime')
    )

    now = timezone.now()
    queue_items = []
    for appointment in appointments:
        check_in_time = appointment.check_in_time
        waiting_minutes = None
        if check_in_time and appointment.status == Appointment.Status.CHECKED_IN:
            delta = now - check_in_time
            waiting_minutes = max(int(delta.total_seconds() // 60), 0)

        patient = appointment.patient
        queue_items.append(
            {
                'appointment_id': appointment.id,
                'status': appointment.status,
                'check_in_time': check_in_time,
                'waiting_time_minutes': waiting_minutes,
                'scheduled_start_datetime': appointment.slot.start_datetime,
                'scheduled_end_datetime': appointment.slot.end_datetime,
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
            'doctor_id': int(doctor_id),
            'date': queue_date,
            'count': len(queue_items),
            'queue': queue_items,
        }
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctor])
def decline_appointment(request, appointment_id):
    appointment = _get_appointment(appointment_id)
    if not appointment:
        return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

    if appointment.slot.doctor.user_id_id != request.user.id:
        return Response({'status': 'error', 'message': 'Not allowed to decline this appointment'}, status=403)

    if appointment.status != Appointment.Status.SCHEDULED:
        return Response({'status': 'error', 'message': 'Only requested/scheduled appointments can be declined'}, status=400)

    reason = request.data.get('reason')
    if not reason:
        return Response({'status': 'error', 'message': 'reason is required'}, status=400)

    with transaction.atomic():
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=['status'])

        if appointment.slot.is_booked:
            appointment.slot.is_booked = False
            appointment.slot.save(update_fields=['is_booked'])

    return Response({'status': 'success', 'message': 'Appointment declined', 'reason': reason})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsDoctor])
def complete_appointment(request, appointment_id):
    appointment = _get_appointment(appointment_id)
    if not appointment:
        return Response({'status': 'error', 'message': 'Appointment not found'}, status=404)

    if appointment.slot.doctor.user_id_id != request.user.id:
        return Response({'status': 'error', 'message': 'Not allowed to complete this appointment'}, status=403)

    status_error = _validate_status_payload(request, Appointment.Status.COMPLETED)
    if status_error:
        return Response({'status': 'error', 'message': status_error}, status=400)

    if appointment.status in [Appointment.Status.CANCELLED, Appointment.Status.NO_SHOW]:
        return Response({'status': 'error', 'message': 'Cannot complete this appointment in its current state'}, status=400)

    if not Consultation.objects.filter(appointment=appointment).exists():
        return Response(
            {'status': 'error', 'message': 'Consultation record is required before completing appointment'},
            status=400,
        )

    appointment.status = Appointment.Status.COMPLETED
    appointment.save(update_fields=['status'])
    return Response({'status': 'success', 'message': 'Appointment marked as completed'})


@api_view(['GET'])
@permission_classes([IsDoctor | IsPatient])
def consultation_read(request, id):
    appointment = get_object_or_404(Appointment, pk=id)

    if request.user.role == 'PATIENT' and appointment.patient != request.user:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    consultation = get_object_or_404(Consultation, appointment=appointment)
    serializer = ConsultationSerializer(consultation)
    return Response(serializer.data)


@api_view(['POST', 'PATCH'])
@permission_classes([IsDoctor])
def consultation_write(request, id):
    appointment = get_object_or_404(Appointment, pk=id)

    if request.method == 'POST':
        data = {**request.data, 'appointment': appointment.pk}
        serializer = ConsultationSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # PATCH
    consultation = get_object_or_404(Consultation, appointment=appointment)
    serializer = ConsultationSerializer(consultation, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)



def _resolve_public_base_url(request):
    configured_base_url = getattr(settings, 'KASHIER_BASE_URL', '').strip()
    if configured_base_url:
        parsed_url = urllib.parse.urlparse(configured_base_url)
        if parsed_url.scheme in ('http', 'https') and parsed_url.netloc:
            return configured_base_url.rstrip('/')

    host = request.get_host()
    scheme = 'https' if host.endswith('ngrok-free.dev') else request.scheme
    return f"{scheme}://{host}".rstrip('/')



@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def payment_callback(request):
    data = request.GET if request.method == 'GET' else request.POST
    
    payment_status = data.get('paymentStatus')
    merchant_order_id = data.get('merchantOrderId')
    transaction_id = data.get('transactionId') 
    kashier_order_id = data.get('orderId') 

    if payment_status == 'SUCCESS' and merchant_order_id:
        try:
            invoice_id = merchant_order_id.replace('INV-', '')
            invoice = Invoice.objects.get(id=invoice_id)
            
            with transaction.atomic():
                if invoice.status != Invoice.Status.PAID:
                    invoice.status = Invoice.Status.PAID
                    invoice.save()

                PaymentTransaction.objects.get_or_create(
                    transaction_id=transaction_id,
                    defaults={
                        'invoice': invoice,
                        'amount': invoice.amount,
                        'payment_method': 'ONLINE',
                        'status': 'SUCCESS',
                        'kashier_order_id': kashier_order_id 
                    }
                )
            
            print(f"Success: Invoice {invoice_id} paid. OrderID: {kashier_order_id}")
            return HttpResponse(f"""
                <h1>Payment Successful</h1>
                <p>Transaction ID: {transaction_id}</p>
                <p><a href='/appointments/invoice/{invoice.id}/pdf/'>Click here to download your Invoice (PDF)</a></p>
                <br>
                <a href='/'>Back to Website</a>
            """)
            
        except Invoice.DoesNotExist:
            print(f"Error: Invoice {merchant_order_id} not found in database")
            return HttpResponse("<h1>Payment Error</h1><p>Invoice not found.</p><a href='/'>Back</a>")
    
    print(f"Payment Failed or Cancelled. Status: {payment_status}")
    return HttpResponse("<h1>Payment Failed</h1><a href='/'>Back</a>")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_payment(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    method = request.data.get('method')

    if invoice.status == Invoice.Status.PAID:
        return Response({'error': 'Invoice already paid'}, status=400)

    if method == 'CASH':
        with transaction.atomic():
            PaymentTransaction.objects.create(
                invoice=invoice,
                amount=invoice.amount,
                payment_method='CASH',
                status='SUCCESS'
            )
            invoice.status = Invoice.Status.PAID
            invoice.save()
        return Response({'status': 'success', 'message': 'Cash payment recorded successfully'})

    elif method == 'ONLINE':
        order_id = f"INV-{invoice.id}"
        amount = "{:.2f}".format(float(invoice.amount))
        currency = "EGP"

        base_url = _resolve_public_base_url(request)
        redirect_url = f"{base_url}/appointments/payment/callback/"

        api_url = "https://test-api.kashier.io/v3/payment/sessions"
        
        expiry_time = now() + timedelta(hours=1)
        expire_at_str = expiry_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        payload = {
            "merchantId": settings.KASHIER_MERCHANT_ID,
            "order": order_id,
            "amount": amount,
            "currency": currency,
            "merchantRedirect": redirect_url,
            "expireAt": expire_at_str,
            "display": "ar",
            "type": "one-time",
            "customer": {
            "email": getattr(invoice.appointment.patient, 'email', 'customer@example.com'),
            "reference": str(invoice.appointment.patient.id)
        }
        }

        headers = {
            "Authorization": settings.KASHIER_SECRET_KEY.strip(),
            "api-key": getattr(settings, 'KASHIER_API_KEY', '').strip(), 
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)
            response_data = response.json()
            
            if response.status_code in [200, 201] and "sessionUrl" in response_data:
                return Response({
                    'status': 'success',
                    'payment_url': response_data['sessionUrl'],
                    'order_id': order_id,
                    'merchant_redirect_url': redirect_url,
                })
            else:
                return Response({
                    'error': 'Kashier API Error',
                    'details': response_data
                }, status=400)
                
        except Exception as e:
            return Response({'error': str(e)}, status=500)

@csrf_exempt
def kashier_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            event_type = data.get('event')
            payload = data.get('data', {})

            if event_type == 'payment_status' and payload.get('status') == 'SUCCESS':
                merchant_order_id = payload.get('merchantOrderId')
                transaction_id = payload.get('transactionId')
                
                if merchant_order_id:
                    invoice_id = merchant_order_id.replace('INV-', '')
                    try:
                        invoice = Invoice.objects.get(id=invoice_id)
                        
                        with transaction.atomic():
                            if invoice.status != Invoice.Status.PAID:
                                invoice.status = Invoice.Status.PAID
                                invoice.save()

                            PaymentTransaction.objects.get_or_create(
                                transaction_id=transaction_id,
                                defaults={
                                    'invoice': invoice,
                                    'amount': invoice.amount,
                                    'payment_method': 'ONLINE',
                                    'status': 'SUCCESS'
                                }
                            )
                        print(f"Webhook: DB updated for Order {merchant_order_id}")
                    except Invoice.DoesNotExist:
                        pass

            return HttpResponse(status=200)
        except Exception as e:
            return HttpResponse(status=400)
    return HttpResponse(status=405)

@api_view(['POST'])
@permission_classes([IsAdmin])
def refund_payment(request, invoice_id):

    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    if invoice.status != Invoice.Status.PAID:
        return Response({'error': 'Refund failed. Only PAID invoices can be refunded.'}, status=400)

    last_txn = PaymentTransaction.objects.filter(invoice=invoice, status='SUCCESS').last()
    
    if not last_txn:
        return Response({'error': 'No successful transaction record found for this invoice.'}, status=404)

    target_id = last_txn.kashier_order_id or last_txn.transaction_id
    
    if not target_id:
        return Response({'error': 'No Kashier Order ID or Transaction ID found to process refund.'}, status=400)

    api_url = f"https://test-fep.kashier.io/v3/orders/{target_id}"
    
    headers = {
        "Authorization": settings.KASHIER_SECRET_KEY.strip(),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "apiOperation": "REFUND",
        "reason": "Customer requested refund",
        "transaction": {
            "amount": float(invoice.amount)
        }
    }

    try:
        response = requests.put(api_url, json=payload, headers=headers)
        
        if not response.text:
            return Response({'error': 'Empty response from Kashier'}, status=500)

        response_data = response.json()

        if response.status_code in [200, 201] and response_data.get('status') == 'SUCCESS':
            
            with transaction.atomic():
                invoice.status = Invoice.Status.CANCELLED
                invoice.save()
                
                new_txn_id = response_data.get('response', {}).get('transactionId', f'REF-TX-{target_id}')
                PaymentTransaction.objects.create(
                    invoice=invoice,
                    amount=invoice.amount,
                    payment_method='ONLINE',
                    transaction_id=new_txn_id,
                    kashier_order_id=target_id,
                    status='SUCCESS'
                )
            
            return Response({
                'status': 'success', 
                'message': 'Payment refunded successfully via Kashier.'
            })
        else:
            return Response({
                'error': 'Kashier API rejected the refund.',
                'details': response_data
            }, status=response.status_code)

    except Exception as e:
        return Response({'error': f"Internal Server Error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated]) 
def download_invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    user = request.user

    if hasattr(user, 'role') and user.role == 'PATIENT':
        if invoice.appointment.patient.id != user.id:
            return HttpResponseForbidden("Access Denied: You can only view your own invoices.")
    elif hasattr(user, 'role') and user.role == 'DOCTOR':
        if invoice.appointment.slot.doctor.user != user:
            return HttpResponseForbidden("Access Denied: This invoice belongs to another doctor's patient.")

    template_path = 'invoices/invoice_template.html'
    context = {
        'invoice': invoice,
        'today': datetime.now(),
    }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.id}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
        
    return response