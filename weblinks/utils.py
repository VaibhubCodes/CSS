# weblinks/utils.py

from django.conf import settings
from pyfcm import FCMNotification
from users.models import Device   # <<--- FIXED HERE

def send_fcm_notification(user, title, body, data=None):
    try:
        device = Device.objects.filter(user=user).latest('updated_at')
        push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        result = push_service.notify_single_device(
            registration_id=device.fcm_token,
            message_title=title,
            message_body=body,
            data_message=data or {}
        )
        return result
    except Device.DoesNotExist:
        return None
