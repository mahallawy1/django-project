from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from users.models import User
from doctors.models import Doctor
from receptionist.models import Slot
from appointments.models import Appointment

class AppointmentTests(APITestCase):
    def setUp(self):
        self.doc_user = User.objects.create_user(username='doc1', role='DOCTOR', password='123')
        self.patient = User.objects.create_user(username='p1', role='PATIENT', password='123')
        self.admin = User.objects.create_user(username='admin', role='ADMIN', password='123')
        
        self.doctor = Doctor.objects.create(
            user_id=self.doc_user, 
            specialization='General', 
            session_duration=30,
            buffer_time=10
        )
        
        self.slot = Slot.objects.create(
            doctor=self.doctor,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, minutes=30),
            is_booked=False
        )
        
        self.app = Appointment.objects.create(
            patient=self.patient,
            slot=self.slot,
            status='SCHEDULED'
        )
        self.client = APIClient()

    def test_list_access(self):
        self.client.force_authenticate(user=self.doc_user)
        res = self.client.get('/appointments/')
        self.assertEqual(res.status_code, 200)

    def test_admin_see_all(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/appointments/')
        self.assertEqual(res.status_code, 200)

    def test_confirm_flow(self):
        self.client.force_authenticate(user=self.doc_user)
        res = self.client.patch(f'/appointments/{self.app.id}/confirm', {'status': 'CONFIRMED'})
        self.assertEqual(res.status_code, 200)

    def test_cancel_slot_release(self):
        self.client.force_authenticate(user=self.patient)
        self.slot.is_booked = True
        self.slot.save()
        res = self.client.patch(f'/appointments/{self.app.id}/cancel', {'reason': 'personal'})
        self.slot.refresh_from_db()
        self.assertFalse(self.slot.is_booked)

    def test_cancel_no_reason(self):
        self.client.force_authenticate(user=self.patient)
        res = self.client.patch(f'/appointments/{self.app.id}/cancel', {})
        self.assertEqual(res.status_code, 400)

    def test_analytics_admin_only(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/appointments/analytics') 
        self.assertEqual(res.status_code, 200)

    def test_analytics_forbidden(self):
        self.client.force_authenticate(user=self.patient)
        res = self.client.get('/appointments/analytics')
        self.assertEqual(res.status_code, 403)

    def test_check_in(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(f'/appointments/{self.app.id}/check-in', {'status': 'CHECKED_IN'})
        self.assertEqual(res.status_code, 200)

    def test_complete_fail_no_consult(self):
        self.app.status = 'CHECKED_IN'
        self.app.save()
        self.client.force_authenticate(user=self.doc_user)
        res = self.client.patch(f'/appointments/{self.app.id}/complete', {'status': 'COMPLETED'})
        self.assertEqual(res.status_code, 400)

    def test_no_show(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(f'/appointments/{self.app.id}/no-show', {'status': 'NO_SHOW'})
        self.assertEqual(res.status_code, 200)

    def test_app_detail(self):
        self.client.force_authenticate(user=self.patient)
        res = self.client.get(f'/appointments/{self.app.id}') 
        self.assertEqual(res.status_code, 200)

    def test_export_csv(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/appointments/analytics/export')
        self.assertEqual(res.status_code, 200)

    def test_unauthenticated_list(self):
        res = self.client.get('/appointments/')
        self.assertEqual(res.status_code, 401)

    def test_not_found_detail(self):
        self.client.force_authenticate(user=self.patient) 
        res = self.client.get('/appointments/9999')
        self.assertEqual(res.status_code, 404)

    def test_invalid_confirm_status(self):
        self.client.force_authenticate(user=self.doc_user)
        res = self.client.patch(f'/appointments/{self.app.id}/confirm', {'status': 'INVALID'})
        self.assertEqual(res.status_code, 400)