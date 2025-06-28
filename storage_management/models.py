from django.db import models
from django.conf import settings
import boto3
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

class UserStorage(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    storage_used = models.BigIntegerField(default=0)  # in bytes
    storage_limit = models.BigIntegerField(default=5368709120)  # 5GB in bytes (default)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_usage_percentage(self):
        if self.storage_limit == 0:
            return 0
        return (self.storage_used / self.storage_limit) * 100

    def get_available_storage(self):
        return max(0, self.storage_limit - self.storage_used)

    def __str__(self):
        return f"{self.user.email}'s Storage"
    
    def update_from_subscription(self):
        """Update storage limit based on user's active subscription"""
        try:
            from payments.utils import get_user_subscription_info
            subscription_info = get_user_subscription_info(self.user)
            
            # Convert GB to bytes
            new_limit = subscription_info['storage_limit_gb'] * 1024 * 1024 * 1024
            
            if self.storage_limit != new_limit:
                self.storage_limit = new_limit
                self.save()
                return True
        except Exception as e:
            print(f"Error updating storage from subscription: {str(e)}")
        return False
    
    class Meta:
        verbose_name_plural = "User Storage"

@receiver(post_save, sender=get_user_model())
def create_user_storage(sender, instance, created, **kwargs):
    """Create UserStorage instance for new users with accurate initialization"""
    if created:
        try:
            user_storage, storage_created = UserStorage.objects.get_or_create(
                user=instance,
                defaults={
                    'storage_used': 0,  # Always start with 0 for new users
                    'storage_limit': 5368709120  # 5GB default
                }
            )
            if storage_created:
                print(f"[SIGNAL] Created UserStorage for user {instance.email} (ID: {instance.id}) with 0 bytes")
                # Don't calculate storage immediately for new users
                # Let the first file upload or manual refresh handle it
                try:
                    user_storage.update_from_subscription()
                except Exception as e:
                    print(f"[SIGNAL] Could not update subscription for {instance.email}: {e}")
            else:
                print(f"[SIGNAL] UserStorage already exists for user {instance.email} (ID: {instance.id})")
        except Exception as e:
            print(f"[SIGNAL ERROR] Failed to create UserStorage for {instance.email}: {e}")

# Signal to update storage when subscription changes
@receiver(post_save, sender='payments.Subscription')
def update_storage_on_subscription_change(sender, instance, created, **kwargs):
    """Update user storage limit when subscription status changes"""
    if instance.status == 'active':
        try:
            user_storage, storage_created = UserStorage.objects.get_or_create(user=instance.user)
            user_storage.storage_limit = instance.plan.storage_bytes
            user_storage.save()
        except Exception as e:
            print(f"Error updating storage on subscription change: {str(e)}")

class AdminAccessLog(models.Model):
    admin_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    accessed_file = models.CharField(max_length=255)
    access_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    access_type = models.CharField(max_length=50)  # e.g., 'view', 'download', 'delete'

    class Meta:
        ordering = ['-access_time']

    def __str__(self):
        return f"{self.admin_user} accessed {self.accessed_file} at {self.access_time}"
