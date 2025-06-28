import random
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def send_verification_email(email, otp):
    """Send verification email with OTP"""
    subject = 'Verify Your Email'
    message = f'Your verification OTP is: {otp}'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)

def store_otp(email, otp):
    """Store OTP in cache for verification"""
    cache_key = f'email_otp_{email}'
    cache.set(cache_key, otp, timeout=300)  # OTP valid for 5 minutes

def verify_otp(email, otp):
    """Verify the OTP for given email"""
    cache_key = f'email_otp_{email}'
    stored_otp = cache.get(cache_key)
    return stored_otp == otp


# Add to users/utils.py

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom auth backend that allows login using either username or email
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find a user matching either username or email
            user = User.objects.get(
                Q(username=username) | Q(email=username)
            )
            
            # Check the password
            if user.check_password(password):
                return user
                
        except User.DoesNotExist:
            return None
            
        return None

