from .models import SubscriptionPlan, Subscription
from storage_management.models import UserStorage
from django.utils import timezone

def get_user_subscription_info(user):
    """
    Get comprehensive subscription information for a user
    """
    try:
        # Get active subscription
        subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()
        
        if not subscription:
            return {
                'has_subscription': False,
                'is_sparkle': False,
                'plan_name': None,
                'storage_limit_gb': 5,  # Default
                'expires_at': None
            }
        
        return {
            'has_subscription': True,
            'is_sparkle': subscription.plan.is_sparkle,
            'plan_name': subscription.plan.name,
            'plan_code': subscription.plan.plan_code,
            'storage_limit_gb': subscription.plan.storage_gb,
            'expires_at': subscription.valid_till,
            'subscription_id': subscription.id
        }
    except Exception as e:
        # Fallback to basic plan info
        return {
            'has_subscription': False,
            'is_sparkle': False,
            'plan_name': None,
            'storage_limit_gb': 5,
            'expires_at': None,
            'error': str(e)
        }

def update_user_storage_from_subscription(user):
    """
    Update user's storage limit based on their active subscription
    """
    subscription_info = get_user_subscription_info(user)
    
    try:
        user_storage, created = UserStorage.objects.get_or_create(user=user)
        
        # Convert GB to bytes
        storage_limit_bytes = subscription_info['storage_limit_gb'] * 1024 * 1024 * 1024
        
        if user_storage.storage_limit != storage_limit_bytes:
            user_storage.storage_limit = storage_limit_bytes
            user_storage.save()
            
        return True
    except Exception as e:
        print(f"Error updating user storage: {str(e)}")
        return False

def check_subscription_validity(user):
    """
    Check if user's subscription is still valid and update status if needed
    """
    try:
        subscription = Subscription.objects.filter(
            user=user,
            status='active'
        ).first()
        
        if subscription and subscription.valid_till:
            if timezone.now() > subscription.valid_till:
                # Subscription expired
                subscription.status = 'expired'
                subscription.save()
                
                # Reset to basic storage limit
                update_user_storage_from_subscription(user)
                
                return False
        
        return True
    except Exception as e:
        print(f"Error checking subscription validity: {str(e)}")
        return False