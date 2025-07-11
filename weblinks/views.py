from rest_framework import viewsets, permissions
from .models import WebLink, Meeting
from .serializers import WebLinkSerializer, MeetingSerializer
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response

class WebLinkViewSet(viewsets.ModelViewSet):
    serializer_class = WebLinkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WebLink.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeetingViewSet(viewsets.ModelViewSet):
    serializer_class = MeetingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Meeting.objects.filter(user=self.request.user).order_by('start_time')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "data": serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.now()
        meetings = Meeting.objects.filter(user=request.user, start_time__gte=now).order_by('start_time')
        serializer = self.get_serializer(meetings, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def past(self, request):
        now = timezone.now()
        meetings = Meeting.objects.filter(user=request.user, end_time__lt=now).order_by('-start_time')
        serializer = self.get_serializer(meetings, many=True)
        return Response(serializer.data)


# weblinks/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import WebLink, Meeting, Notification
from .serializers import WebLinkSerializer, MeetingSerializer, NotificationSerializer

class WebLinkViewSet(viewsets.ModelViewSet):
    # … existing code …

    def perform_create(self, serializer):
        link = serializer.save(user=self.request.user)
        Notification.objects.create(
            user       = self.request.user,
            notif_type = 'weblink',
            message    = f"New bookmark added: {link.link_name}",
        )

# weblinks/views.py
from datetime import timedelta
from .tasks import send_meeting_reminder

class MeetingViewSet(viewsets.ModelViewSet):
    # … existing code …

    def perform_create(self, serializer):
        meeting = serializer.save(user=self.request.user)
        Notification.objects.create(
            user=self.request.user,
            notif_type='meeting',
            message=f"Meeting scheduled: {meeting.meeting_name} @ {meeting.start_time:%b %d, %H:%M}"
        )
        eta = meeting.start_time - timedelta(minutes=10)
        if eta > timezone.now():
            send_meeting_reminder.apply_async(
                args=[meeting.id],
                eta=eta
            )

# weblinks/views.py
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset         = Notification.objects.none()  # get_queryset overrides
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'success': True})