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
