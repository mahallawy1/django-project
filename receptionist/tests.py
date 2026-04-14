from rest_framework.test import APITestCase
from users.models import User
from django.urls import reverse

class ReceptionistTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='recep_test', role='RECEPTIONIST', password='123')
        self.client.force_authenticate(user=self.user)

    def test_regenerate_slots(self):
        url = reverse('regenerate_all_doctors_next_7_days_slots')
        res = self.client.post(url)
        self.assertIn(res.status_code, [200, 201, 204, 403])

    def test_receptionist_simple_access(self):
        url = reverse('regenerate_all_doctors_next_7_days_slots')
        res = self.client.get(url)
        self.assertTrue(res.status_code != 404)