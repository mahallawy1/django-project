from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class UserTests(APITestCase):
    def test_create_user(self):
        user = User.objects.create_user(username='testuser', password='password123', role='PATIENT')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.role, 'PATIENT')

    def test_user_count(self):
        initial_count = User.objects.count()
        User.objects.create_user(username='another_user', password='password123')
        self.assertEqual(User.objects.count(), initial_count + 1)