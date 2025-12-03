from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class AuthenticationFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='demo',
            email='demo@example.com',
            password='testpassword',
            first_name='Demo',
            last_name='User',
        )

    def test_login_returns_token_and_user(self):
        response = self.client.post(reverse('login'), {
            'username': 'demo',
            'password': 'testpassword',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'demo')

    def test_whoami_requires_authentication(self):
        response = self.client.get(reverse('whoami'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_whoami_returns_user_after_login(self):
        login_response = self.client.post(reverse('login'), {
            'username': 'demo',
            'password': 'testpassword',
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        response = self.client.get(reverse('whoami'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'demo@example.com')

    def test_logout_revokes_token(self):
        login_response = self.client.post(reverse('login'), {
            'username': 'demo',
            'password': 'testpassword',
        })
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        logout_response = self.client.post(reverse('logout'))
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)

        whoami_response = self.client.get(reverse('whoami'))
        self.assertEqual(whoami_response.status_code, status.HTTP_401_UNAUTHORIZED)
