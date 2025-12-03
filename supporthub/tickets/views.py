from rest_framework import permissions, viewsets

from supporthub.accounts.models import UserProfile
from .models import Ticket
from .serializers import TicketSerializer


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    queryset = Ticket.objects.select_related('requester__profile', 'assignee__profile')
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'put']

    def get_queryset(self):
        user = self.request.user
        role = getattr(getattr(user, 'profile', None), 'role', UserProfile.Role.CUSTOMER)
        if role in (UserProfile.Role.AGENT, UserProfile.Role.ADMIN):
            return self.queryset
        return self.queryset.filter(requester=user)

    def perform_create(self, serializer):
        serializer.save(requester=self.request.user, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
