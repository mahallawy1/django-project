from django.urls import reverse
from rest_framework.test import APITestCase
from users.models import User
from doctors.models import Doctor

class DoctorTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='doc_test', role='DOCTOR', password='123')
        self.doctor = Doctor.objects.create(
            user_id=self.user, 
            specialization='Cardiology', 
            session_duration=30,
            buffer_time=10
        )
        self.client.force_authenticate(user=self.user)

    def test_doctor_list(self):
        url = reverse('get_all_doctors')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_doctor_me(self):
        url = reverse('get_doctor_me')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)

    def test_doctor_schedule_me(self):
        url = reverse('get_doctor_schedule_me')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)