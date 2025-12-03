from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from supporthub.accounts.models import UserProfile
from .models import Ticket


class TicketPermissionsTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(username='customer', password='pass123', email='customer@example.com')
        self.agent = User.objects.create_user(username='agent', password='pass123', email='agent@example.com')
        self.agent.profile.role = UserProfile.Role.AGENT
        self.agent.profile.save()

    def test_customer_creates_ticket(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(reverse('ticket-list'), {
            'subject': 'VPN down',
            'description': 'Cannot connect to VPN',
            'priority': Ticket.Priority.HIGH,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['requester']['id'], self.customer.id)
        self.assertEqual(response.data['status'], Ticket.Status.OPEN)

    def test_customer_sees_only_own_tickets(self):
        Ticket.objects.create(subject='A', description='A', requester=self.customer, created_by=self.customer, updated_by=self.customer)
        Ticket.objects.create(subject='B', description='B', requester=self.agent, created_by=self.agent, updated_by=self.agent)

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(reverse('ticket-list'))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['requester']['id'], self.customer.id)

    def test_agent_sees_all_tickets(self):
        Ticket.objects.create(subject='A', description='A', requester=self.customer, created_by=self.customer, updated_by=self.customer)
        Ticket.objects.create(subject='B', description='B', requester=self.agent, created_by=self.agent, updated_by=self.agent)

        self.client.force_authenticate(user=self.agent)
        response = self.client.get(reverse('ticket-list'))
        self.assertEqual(len(response.data), 2)

    def test_customer_cannot_change_status(self):
        ticket = Ticket.objects.create(subject='A', description='A', requester=self.customer, created_by=self.customer, updated_by=self.customer)

        self.client.force_authenticate(user=self.customer)
        response = self.client.patch(reverse('ticket-detail', args=[ticket.id]), {'status': Ticket.Status.RESOLVED})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agent_can_progress_ticket(self):
        ticket = Ticket.objects.create(subject='A', description='A', requester=self.customer, created_by=self.customer, updated_by=self.customer)

        self.client.force_authenticate(user=self.agent)
        response = self.client.patch(reverse('ticket-detail', args=[ticket.id]), {
            'status': Ticket.Status.IN_PROGRESS,
            'assignee': self.agent.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)
        self.assertEqual(ticket.assignee, self.agent)
