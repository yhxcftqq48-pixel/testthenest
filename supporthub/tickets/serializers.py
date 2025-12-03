from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from supporthub.accounts.models import UserProfile
from supporthub.accounts.serializers import UserSerializer
from .models import Ticket


class TicketSerializer(serializers.ModelSerializer):
    requester = UserSerializer(read_only=True)
    assignee = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), required=False, allow_null=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'subject',
            'description',
            'category',
            'priority',
            'status',
            'requester',
            'assignee',
            'resolution_text',
            'due_at',
            'queue',
            'closed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['requester', 'created_at', 'updated_at', 'closed_at']

    def validate(self, attrs):
        request = self.context.get('request')
        if not request:
            return attrs

        user = request.user
        role = getattr(getattr(user, 'profile', None), 'role', UserProfile.Role.CUSTOMER)

        if self.instance:
            disallowed_for_customer = set(attrs.keys()) - {'subject', 'description'}
            if role == UserProfile.Role.CUSTOMER:
                if self.instance.requester_id != user.id:
                    raise serializers.ValidationError('You can only update your own tickets.')
                if disallowed_for_customer:
                    raise serializers.ValidationError('Customers can only edit subject or description.')
            if 'status' in attrs:
                new_status = attrs['status']
                if role not in (UserProfile.Role.AGENT, UserProfile.Role.ADMIN):
                    raise serializers.ValidationError('Only support or admin can change status.')
                if new_status == Ticket.Status.IN_PROGRESS and not attrs.get('assignee') and not self.instance.assignee:
                    raise serializers.ValidationError('Assignee required when moving ticket in progress.')
                if new_status in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED) and not attrs.get('resolution_text') and not self.instance.resolution_text:
                    raise serializers.ValidationError('Resolution text required before closing a ticket.')
        return attrs

    def create(self, validated_data):
        request = self.context['request']
        return Ticket.objects.create(
            requester=request.user,
            created_by=request.user,
            updated_by=request.user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        request = self.context['request']
        role = getattr(getattr(request.user, 'profile', None), 'role', UserProfile.Role.CUSTOMER)

        if role in (UserProfile.Role.AGENT, UserProfile.Role.ADMIN):
            if validated_data.get('status') in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED):
                validated_data.setdefault('closed_at', timezone.now())
        validated_data['updated_by'] = request.user
        return super().update(instance, validated_data)
