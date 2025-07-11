# weblinks/tasks.py

from celery import shared_task
from django.utils import timezone
from .models import Meeting, Notification
from .utils import send_fcm_notification

@shared_task
def send_meeting_reminder(meeting_id):
    try:
        meeting = Meeting.objects.get(pk=meeting_id)
        if meeting.start_time > timezone.now():
            notif = Notification.objects.create(
                user=meeting.user,
                notif_type='meeting_upcoming',
                message=f"⏰ Your meeting “{meeting.meeting_name}” starts in 10 minutes."
            )
            # Send FCM push
            send_fcm_notification(
                meeting.user,
                "Meeting Starting Soon",
                f"Your meeting '{meeting.meeting_name}' starts in 10 minutes.",
                data={"type": "meeting_upcoming", "meeting_id": meeting.id, "notif_id": notif.id}
            )
    except Meeting.DoesNotExist:
        pass
