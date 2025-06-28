from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import viewsets, status, generics, mixins
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny # AllowAny for dev endpoints
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied # For master password check

from .models import (
    PasswordCategory,
    PasswordEntry,
    PasswordCompromise,
    PasswordHistory,
    SecuritySetting,
    PasskeyCredential,
    PasswordAccessLog,
    MasterPassword
)
from .serializers import (
    PasswordCategorySerializer,
    PasswordEntrySerializer,
    PasswordHistorySerializer,
    SecuritySettingSerializer,
    MasterPasswordSerializer,
    PasswordVerificationSerializer
    # PasswordEntryFilterSerializer is used by MobilePasswordEntryView, ensure it's imported if needed elsewhere
)
from .utils import PasswordEncryption, PasswordSecurity, verify_master_password, create_master_password_hash

import uuid
import json
import logging
import base64
import os
import secrets
# from cryptography.fernet import Fernet # Not used directly here
# from cryptography.hazmat.primitives import hashes # Not used directly here
# from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC # Not used directly here
from django.contrib.auth import get_user_model # For dev endpoints
from django.db import IntegrityError, transaction # For signals if any

logger = logging.getLogger(__name__)

# Master password session key
MASTER_PASSWORD_SESSION_KEY = 'master_password_verified'
MASTER_PASSWORD_TIMEOUT = 15 * 60  # 15 minutes in seconds

# Helper to get client IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Helper to log password access
def log_password_access(password_entry, request, access_type='view'):
    """Log when a password is accessed"""
    PasswordAccessLog.objects.create(
        password_entry=password_entry,
        access_type=access_type,
        device_info=request.META.get('HTTP_USER_AGENT', ''),
        ip_address=get_client_ip(request)
    )
    
    # Also update the last_used timestamp
    password_entry.mark_as_used()

@method_decorator(csrf_exempt, name='dispatch')
class MasterPasswordStatusView(APIView):
    """
    Check if a master password is set for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        is_set = MasterPassword.objects.filter(user=request.user).exists()
        return Response({'is_set': is_set})

@method_decorator(csrf_exempt, name='dispatch')
class VerifyMasterPasswordView(APIView):
    """
    Verify the master password and store verification in session
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordVerificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            request.session[MASTER_PASSWORD_SESSION_KEY] = True
            request.session['verified_master_password'] = request.data.get('master_password')
            request.session['master_password_verified_at'] = timezone.now().timestamp()
            request.session.modified = True  # ✅ ADD THIS

            return Response({
                'success': True,
                'message': 'Master password verified.',
                'valid_until': int((timezone.now().timestamp() + MASTER_PASSWORD_TIMEOUT) * 1000)
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class MasterPasswordView(APIView):
    """
    Set up or change the master password
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = MasterPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            result = serializer.save() # result is {'success': True, 'created': created}
            if result.get('created'):
                message = 'Master password set up successfully.'
            else:
                message = 'Master password changed successfully.'
            return Response({'success': True, 'message': message, 'created': result.get('created')})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class PasswordCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for password categories
    """
    serializer_class = PasswordCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only categories for the current user"""
        return PasswordCategory.objects.filter(user=self.request.user)

    def perform_create(self, serializer): # Added to ensure user is set on category creation
        serializer.save(user=self.request.user)


@method_decorator(csrf_exempt, name='dispatch')
class PasswordEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for password entries (Authenticated)
    """
    serializer_class = PasswordEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = PasswordEntry.objects.filter(user=user).select_related('category')

        category_id = self.request.query_params.get('category')
        entry_type = self.request.query_params.get('type')
        favorites_only = self.request.query_params.get('favorites')
        search_query = self.request.query_params.get('q')

        if category_id:
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except ValueError:
                pass

        if entry_type in dict(PasswordEntry.TYPE_CHOICES):
            queryset = queryset.filter(entry_type=entry_type)

        if str(favorites_only).lower() == 'true':
            queryset = queryset.filter(is_favorite=True)

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(website_url__icontains=search_query) |
                Q(notes__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        return queryset.order_by('-updated_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request = self.request
        verified = request.session.get(MASTER_PASSWORD_SESSION_KEY, False)
        verified_at = request.session.get('master_password_verified_at', 0)
        current_time = timezone.now().timestamp()

        context['master_password_verified_session'] = False

        if verified and (current_time - verified_at) < MASTER_PASSWORD_TIMEOUT:
            master_password = request.session.get('verified_master_password') or request.headers.get('X-Master-Password')
            if master_password:
                context['master_password_verified_session'] = True
                context['master_password'] = master_password
                logger.debug(f"✅ get_serializer_context: Using verified master password for {request.user.email}")
            else:
                logger.warning("⚠️ No master password found in session or headers.")
        else:
            logger.info(f"⛔ Master password session expired or not verified for {request.user.email}")

        return context

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        log_password_access(instance, request, 'view')

        context = self.get_serializer_context()
        master_password = context.get('master_password')

        logger.debug(f"🔐 get_password_decrypted: {master_password} for user {request.user.email}")

        context['request'] = request
        serializer = PasswordEntrySerializer(instance, context=context)
        return Response(serializer.data)

    def perform_create(self, serializer):
        user = self.request.user
        if not MasterPassword.objects.filter(user=user).exists():
            raise PermissionDenied("Master password not set up. Please set it first.")

        context = self.get_serializer_context()
        if 'master_password' not in context:
            logger.warning(f"⚠️ Missing master_password in context during create for user {user.email}")
        serializer.save(user=user)

    @action(detail=True, methods=['post'])
    def copy_password(self, request, pk=None):
        password_entry = self.get_object()
        context = self.get_serializer_context()

        if not context.get('master_password_verified_session'):
            return Response(
                {'error': 'Master password verification required or session expired.'},
                status=status.HTTP_403_FORBIDDEN
            )

        log_password_access(password_entry, request, 'copy')

        # Add decrypted password when decryption is implemented
        return Response({
            'success': True,
            'message': 'Password copied.',
            'password_placeholder': '********'
        })

    @action(detail=False, methods=['get'])
    def compromised(self, request):
        entries = PasswordEntry.objects.filter(
            user=request.user,
            passwordcompromise__is_resolved=False
        ).distinct()
        serializer = self.get_serializer(entries, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def generate_password(self, request, pk=None):
        length = int(request.data.get('length', 16))
        uppercase = request.data.get('uppercase', True)
        numbers = request.data.get('numbers', True)
        symbols = request.data.get('symbols', True)

        password = PasswordSecurity.generate_secure_password(
            length=max(8, min(length, 64)),
            uppercase=uppercase,
            numbers=numbers,
            symbols=symbols
        )

        return Response({
            'password': password,
            'strength': PasswordSecurity.check_password_strength(password)[0]
        })

    @action(detail=True, methods=['post'])
    def check_compromised(self, request, pk=None):
        password_entry = self.get_object()
        plain_password = request.data.get('password', '')

        if not plain_password:
            return Response({'error': 'Password is required.'}, status=status.HTTP_400_BAD_REQUEST)

        is_compromised, count = PasswordSecurity.check_haveibeenpwned(plain_password)

        if is_compromised is None:
            return Response({'error': 'HIBP check failed.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if is_compromised:
            PasswordCompromise.objects.get_or_create(
                password_entry=password_entry,
                defaults={'breach_source': 'HaveIBeenPwned', 'is_resolved': False}
            )
            return Response({
                'is_compromised': True,
                'count': count,
                'message': f'Found in {count} breaches.'
            })

        return Response({'is_compromised': False, 'message': 'Not found in known breaches.'})

@method_decorator(csrf_exempt, name='dispatch')
class SecuritySettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = SecuritySettingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        settings, created = SecuritySetting.objects.get_or_create(user=self.request.user)
        return settings

@method_decorator(csrf_exempt, name='dispatch')
class PasswordHistoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PasswordHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        password_entry_id = self.kwargs.get('password_entry_id')
        if not password_entry_id:
            return PasswordHistory.objects.none()
        return PasswordHistory.objects.filter(
            password_entry__user=self.request.user,
            password_entry__id=password_entry_id
        )

@method_decorator(csrf_exempt, name='dispatch')
class MobilePasswordEntryView(APIView):
    """
    Mobile API endpoint for password entries.
    Handles GET (list with filters) and POST (create).
    """
    permission_classes = [IsAuthenticated] # Ensures user is authenticated
    
    def get(self, request, format=None):
        user = request.user
        entries = PasswordEntry.objects.filter(user=user).select_related('category')

        # --- Filtering Logic (from original code) ---
        category_id_str = request.query_params.get('category', None)
        entry_type = request.query_params.get('type', None)
        favorites_only_str = request.query_params.get('favorites', 'false') # Default to false string
        search_query = request.query_params.get('search', '') # Default to empty string
        sort_by = request.query_params.get('sort', '-updated_at')

        if category_id_str:
            try:
                category_id = int(category_id_str)
                entries = entries.filter(category_id=category_id)
            except ValueError:
                logger.warning(f"User {user.id} provided non-integer category ID: {category_id_str}")
        
        if entry_type and entry_type in [choice[0] for choice in PasswordEntry.TYPE_CHOICES]:
            entries = entries.filter(entry_type=entry_type)
        elif entry_type:
            logger.warning(f"User {user.id} provided invalid entry_type: {entry_type}")

        if str(favorites_only_str).lower() == 'true':
            entries = entries.filter(is_favorite=True)

        if search_query and len(search_query.strip()) > 0:
            entries = entries.filter(
                Q(title__icontains=search_query) |
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(website_url__icontains=search_query) |
                Q(notes__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )

        valid_sort_fields = ['title', '-title', 'updated_at', '-updated_at', 'created_at', '-created_at', 'last_used', '-last_used', 'strength', '-strength']
        if sort_by in valid_sort_fields:
            entries = entries.order_by(sort_by)
        else:
            entries = entries.order_by('-updated_at')

        serializer = PasswordEntrySerializer(entries, many=True, context={'request': request})
        return Response(serializer.data)
    
    def post(self, request, format=None):
        user = request.user
        if not MasterPassword.objects.filter(user=user).exists():
            return Response(
                {"error": "Master password not set up. Please set up your master password before creating entries."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Session validation
        verified = request.session.get(MASTER_PASSWORD_SESSION_KEY, False)
        verified_at = request.session.get('master_password_verified_at', 0)
        current_time = timezone.now().timestamp()

        if not verified or (current_time - verified_at) > MASTER_PASSWORD_TIMEOUT:
            return Response(
                {"error": "Master password session expired or not verified."},
                status=status.HTTP_403_FORBIDDEN
            )

        master_password = request.session.get('verified_master_password')
        if not master_password:
            return Response(
                {"error": "Master password is missing from session."},
                status=status.HTTP_403_FORBIDDEN
            )

        logger.info(f"🔐 Creating password entry for user {user.email} with verified master password context.")

        serializer = PasswordEntrySerializer(
            data=request.data,
            context={'request': request, 'master_password': master_password}
        )

        if serializer.is_valid():
            try:
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"❌ Error saving password entry for user {user.id}: {e}")
                return Response(
                    {"error": "Failed to save password entry due to an internal error."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# --- Web UI Views ---
@csrf_exempt # For AJAX from templates
@login_required # Ensures user is logged in for web views
def password_dashboard(request):
    total_passwords = PasswordEntry.objects.filter(user=request.user).count()
    compromised_passwords = PasswordEntry.objects.filter(
        user=request.user, passwordcompromise__is_resolved=False
    ).distinct().count()
    reused_passwords = 0 # Placeholder
    categories = PasswordCategory.objects.filter(user=request.user)
    type_counts = {
        tc[0]: PasswordEntry.objects.filter(user=request.user, entry_type=tc[0]).count()
        for tc in PasswordEntry.TYPE_CHOICES
    }
    context = {
        'total_passwords': total_passwords,
        'compromised_passwords': compromised_passwords,
        'reused_passwords': reused_passwords,
        'categories': categories,
        'type_counts': type_counts,
        'password_types': PasswordEntry.TYPE_CHOICES
    }
    return render(request, 'password_management/dashboard.html', context)

@csrf_exempt
@login_required
def password_list(request):
    user = request.user
    entries = PasswordEntry.objects.filter(user=user).select_related('category')
    category_id_str = request.GET.get('category')
    entry_type = request.GET.get('type')
    search_query = request.GET.get('q')
    current_category_id = None

    if category_id_str:
        try:
            current_category_id = int(category_id_str)
            entries = entries.filter(category_id=current_category_id)
        except ValueError:
            current_category_id = None

    if entry_type and entry_type in [choice[0] for choice in PasswordEntry.TYPE_CHOICES]:
        entries = entries.filter(entry_type=entry_type)

    if search_query:
        entries = entries.filter(
            Q(title__icontains=search_query) | Q(username__icontains=search_query) |
            Q(email__icontains=search_query) | Q(website_url__icontains=search_query) |
            Q(notes__icontains=search_query) | Q(category__name__icontains=search_query)
        )
    
    categories_for_user = PasswordCategory.objects.filter(user=user).distinct().order_by('name')
    context = {
        'entries': entries.order_by('-updated_at'),
        'categories': categories_for_user,
        'password_types': PasswordEntry.TYPE_CHOICES,
        'current_category': str(current_category_id) if current_category_id is not None else '',
        'current_type': entry_type or '',
        'search_query': search_query or '',
    }
    return render(request, 'password_management/password_list.html', context)

@csrf_exempt
@login_required
def password_detail(request, password_id):
    password_entry = get_object_or_404(PasswordEntry, id=password_id, user=request.user)
    log_password_access(password_entry, request, 'view')
    return render(request, 'password_management/password_detail.html', {'password': password_entry})

@csrf_exempt
@login_required
def password_security(request):
    compromised_passwords = PasswordEntry.objects.filter(
        user=request.user, passwordcompromise__is_resolved=False
    ).distinct()
    weak_passwords = PasswordEntry.objects.filter(user=request.user, strength='weak')
    context = {
        'compromised_passwords': compromised_passwords,
        'weak_passwords': weak_passwords,
    }
    return render(request, 'password_management/security.html', context)

@csrf_exempt
@login_required
def password_settings(request):
    settings_obj, created = SecuritySetting.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        settings_obj.check_for_compromised = request.POST.get('check_for_compromised') == 'on'
        settings_obj.suggest_strong_passwords = request.POST.get('suggest_strong_passwords') == 'on'
        settings_obj.min_password_length = int(request.POST.get('min_password_length', 12))
        settings_obj.password_require_uppercase = request.POST.get('password_require_uppercase') == 'on'
        settings_obj.password_require_numbers = request.POST.get('password_require_numbers') == 'on'
        settings_obj.password_require_symbols = request.POST.get('password_require_symbols') == 'on'
        settings_obj.auto_fill_enabled = request.POST.get('auto_fill_enabled') == 'on'
        settings_obj.save()
        from django.contrib import messages
        messages.success(request, 'Security settings updated successfully!')
    context = {'settings': settings_obj}
    return render(request, 'password_management/settings.html', context)

# --- Signal Handler ---
from django.db.models.signals import post_save
from django.dispatch import receiver
# User model is already imported via get_user_model()

def get_default_categories(user):
    """Create default categories for a new user"""
    defaults = [
        {'name': 'Website Logins', 'icon': 'globe', 'color': 'primary'},  # Blue
        {'name': 'Financial', 'icon': 'credit-card', 'color': 'success'},  # Green
        {'name': 'Work', 'icon': 'briefcase', 'color': 'info'},  # Light blue
        {'name': 'Personal', 'icon': 'user', 'color': 'danger'},  # Red
        {'name': 'Social Media', 'icon': 'users', 'color': 'purple'},  # Purple (custom)
        {'name': 'Email', 'icon': 'envelope', 'color': 'warning'},  # Yellow/Orange
        {'name': 'Shopping', 'icon': 'shopping-cart', 'color': 'secondary'},  # Gray
        {'name': 'Entertainment', 'icon': 'film', 'color': 'dark'},  # Dark gray/black
    ]
    
    for default in defaults:
        PasswordCategory.objects.get_or_create(
            user=user,
            name=default['name'],
            defaults={
                'icon': default['icon'],
                'color': default['color']
            }
        )

@receiver(post_save, sender=get_user_model())
def create_user_password_defaults(sender, instance, created, **kwargs):
    if created:
        get_default_categories(instance)
        SecuritySetting.objects.get_or_create(user=instance) # Use get_or_create for robustness

# --- API Endpoints for Password Creation (Authenticated and Dev/Test) ---
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # This is the primary authenticated creation endpoint
def create_password(request):
    user = request.user
    if not MasterPassword.objects.filter(user=user).exists():
        return Response(
            {'success': False, 'error': "Master password not set up. Please set it up first."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Placeholder master password context for deferred encryption fix
    master_password_context = {'master_password': 'secure_placeholder'}
    logger.warning("create_password: Using insecure placeholder for master_password. Encryption will not use user's actual master password.")

    serializer = PasswordEntrySerializer(
        data=request.data,
        context={'request': request, **master_password_context}
    )
    if serializer.is_valid():
        password_entry = serializer.save() # User is automatically set by serializer or perform_create
        return Response(
            {'success': True, 'message': 'Password created successfully', 'id': password_entry.id},
            status=status.HTTP_201_CREATED
        )
    return Response(
        {'success': False, 'error': serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny]) # Kept AllowAny but added master password check for authenticated user
def web_create_password(request):
    """Web endpoint to create a password.
       If authenticated, checks for user's master password.
       If unauthenticated, uses fallback user logic (INSECURE FOR PRODUCTION).
    """
    User = get_user_model()
    target_user = None
    is_fallback_user_flow = False

    if request.user.is_authenticated:
        target_user = request.user
    else:
        is_fallback_user_flow = True
        logger.warning("web_create_password: Unauthenticated request. Using fallback user. THIS IS INSECURE FOR PRODUCTION.")
        target_user = User.objects.first()
        if not target_user:
            logger.info("web_create_password: No fallback user found, creating demo_user.")
            target_user = User.objects.create_user(
                username='demo_user_web_create', # Unique username
                email='demo_web_create@example.com',
                password='password123'
            )
        request.user = target_user # For serializer context

    # Check/Create MasterPassword for the target_user
    mp_record, mp_created = MasterPassword.objects.get_or_create(
        user=target_user,
        defaults={ # Only used if creating a new MasterPassword for the fallback user
            'password_hash': create_master_password_hash('dev_default_master_web')[0],
            'salt': create_master_password_hash('dev_default_master_web')[1],
            'iterations': create_master_password_hash('dev_default_master_web')[2]
        }
    )
    if mp_created and is_fallback_user_flow:
        logger.info(f"web_create_password: Created default MasterPassword for fallback user {target_user.username}")
    elif not MasterPassword.objects.filter(user=target_user).exists() and not is_fallback_user_flow:
        # This case should ideally not be hit if authenticated user must have master password
        logger.error(f"web_create_password: Authenticated user {target_user.username} has no master password. This indicates a flow issue.")
        return Response(
            {'success': False, 'error': "Master password not set up for the authenticated user."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    master_password_context = {'master_password': 'secure_placeholder'} # Placeholder for deferred encryption
    if is_fallback_user_flow:
        logger.warning("web_create_password (fallback flow): Using insecure placeholder for master_password context.")
    else:
        logger.warning("web_create_password (authenticated flow): Using insecure placeholder for master_password context. Encryption will not use user's actual master password.")

    serializer = PasswordEntrySerializer(
        data=request.data, context={'request': request, **master_password_context}
    )
    if serializer.is_valid():
        try:
            password_entry = serializer.save()
            message = 'Password created successfully'
            if is_fallback_user_flow:
                message += ' (using fallback user in dev mode)'
            return Response(
                {'success': True, 'message': message, 'id': password_entry.id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"web_create_password: Error saving password entry: {e}")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logger.error(f"web_create_password: Serializer validation errors: {serializer.errors}")
        return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny]) # Kept AllowAny for its specific dev/test purpose
def mobile_create_password(request):
    """
    Mobile endpoint to create a password without explicit client authentication
    - FOR DEVELOPMENT/TESTING PURPOSES ONLY.
    - THIS IS HIGHLY INSECURE AND SHOULD NOT BE USED IN PRODUCTION.
    - It will use the first available user in the database or create a 'demo_user_mobile_test'.
    - It also uses a PLACEHOLDER for master password encryption.
    """
    logger.critical("CRITICAL WARNING: mobile_create_password (unauthenticated dev endpoint) is being used. This uses placeholder encryption. FOR DEVELOPMENT/TESTING ONLY.")
    
    User = get_user_model()
    user_for_entry = User.objects.first()
    if not user_for_entry:
        logger.info("mobile_create_password: No users found, creating 'demo_user_mobile_test'.")
        user_for_entry = User.objects.create_user(
            username='demo_user_mobile_test',
            email='demo_mobile_test@example.com',
            password='password123'
        )
    request.user = user_for_entry # Set for serializer context

    # Ensure MasterPassword exists for this test user, create if not
    # This uses a default password for the master password itself for dev ease
    mp_hash_components = create_master_password_hash('dev_default_master_for_mobile_test')
    mp_record, mp_created = MasterPassword.objects.get_or_create(
        user=user_for_entry,
        defaults={
            'password_hash': mp_hash_components[0],
            'salt': mp_hash_components[1],
            'iterations': mp_hash_components[2]
        }
    )
    if mp_created:
        logger.info(f"mobile_create_password: Created default MasterPassword for test user {user_for_entry.username}")

    # PLACEHOLDER for master password context. Actual encryption fix is deferred.
    master_password_context = {'master_password': 'secure_placeholder'}
    logger.warning("mobile_create_password: Using insecure placeholder for master_password context. Encryption will not use user's actual master password.")

    data_for_serializer = request.data.copy()
    data_for_serializer.setdefault('title', 'Mobile Test Entry - Unauth')
    data_for_serializer.setdefault('entry_type', 'password')
    if 'password' not in data_for_serializer or not data_for_serializer['password']:
        data_for_serializer['password'] = 'TestPassword123Unauth!'

    serializer = PasswordEntrySerializer(
        data=data_for_serializer, context={'request': request, **master_password_context}
    )
    if serializer.is_valid():
        try:
            password_entry = serializer.save() 
            return Response(
                {'success': True, 'message': 'Password created successfully (UNAUTHENTICATED TESTING MODE)', 'id': password_entry.id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"mobile_create_password: Error saving password entry: {e}")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        logger.error(f"mobile_create_password: Serializer validation errors: {serializer.errors}")
        return Response({'success': False, 'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny]) 
def generate_password_api(request):
    length = int(request.data.get('length', 16))
    uppercase = request.data.get('uppercase', True)
    numbers = request.data.get('numbers', True)
    symbols = request.data.get('symbols', True)
    length = max(8, min(length, 64))
    password = PasswordSecurity.generate_secure_password(
        length=length, uppercase=uppercase, numbers=numbers, symbols=symbols
    )
    return Response({
        'success': True, 'password': password,
        'strength': PasswordSecurity.check_password_strength(password)[0]
    })

@csrf_exempt
@api_view(['POST'])
@permission_classes([])  # Explicitly disable authentication requirements
def mobile_create_password(request):
    """Mobile endpoint to create a password without authentication - for testing purposes only"""
    # Debug logging
    print("Mobile password create request data:", request.data)
    
    # For mobile interface, we need to get a valid user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # For development/testing only: get the first user as a fallback
    # In production, this should require proper authentication using JWT
    try:
        user = User.objects.first()
        if not user:
            return Response(
                {'success': False, 'error': 'No user found in the system'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        print(f"User setup error: {str(e)}")
        return Response(
            {'success': False, 'error': f'User setup error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Assign user to request
    request.user = user
    
    # Directly create a password entry without using the serializer
    try:
        # Get password from request
        password = request.data.get('password')
        if not password:
            return Response(
                {'success': False, 'error': 'Password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create master password if it doesn't exist
        from .models import MasterPassword
        try:
            mp_record = MasterPassword.objects.get(user=user)
        except MasterPassword.DoesNotExist:
            # Create a default master password
            from .utils import create_master_password_hash
            password_hash, salt, iterations = create_master_password_hash('default_master_password')
            mp_record = MasterPassword.objects.create(
                user=user,
                password_hash=password_hash,
                salt=salt,
                iterations=iterations
            )
        
        # Generate encryption key
        from .utils import PasswordEncryption
        key = PasswordEncryption.generate_key(
            'secure_placeholder',
            mp_record.salt,
            mp_record.iterations
        )
        
        # Encrypt the password
        encrypted_data, iv = PasswordEncryption.encrypt(password, key)
        
        # Calculate password strength
        from .utils import PasswordSecurity
        strength, _ = PasswordSecurity.check_password_strength(password)
        
        # Create the entry with required fields
        from .models import PasswordEntry
        entry = PasswordEntry.objects.create(
            user=user,
            title=request.data.get('title', 'Default Title'),
            entry_type=request.data.get('entry_type', 'password'),
            username=request.data.get('username', ''),
            email=request.data.get('email', ''),
            website_url=request.data.get('website_url', ''),
            notes=request.data.get('notes', ''),
            is_favorite=request.data.get('is_favorite', False),
            password=encrypted_data,
            password_iv=iv,
            strength=strength
        )
        
        # Return success
        return Response(
            {'success': True, 'message': 'Password created successfully', 'id': entry.id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        print(f"Mobile direct creation error: {str(e)}")
        return Response(
            {'success': False, 'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def has_master_password(request):
    """Check whether the current user has set up a master password"""
    try:
        MasterPassword.objects.get(user=request.user)
        return Response({'has_master_password': True})
    except MasterPassword.DoesNotExist:
        return Response({'has_master_password': False})

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_password_decryption(request, entry_id):
    try:
        entry = PasswordEntry.objects.get(id=entry_id, user=request.user)
    except PasswordEntry.DoesNotExist:
        return Response({'error': 'Entry not found'}, status=404)

    # Get master password from session
    master_password = request.session.get('verified_master_password')
    if not master_password:
        return Response({'error': 'Master password not verified in session'}, status=403)

    try:
        mp_record = MasterPassword.objects.get(user=request.user)
        key = PasswordEncryption.generate_key(master_password, mp_record.salt, mp_record.iterations)
        decrypted = PasswordEncryption.decrypt(entry.password, key, entry.password_iv)
        return Response({
            'id': str(entry.id),
            'title': entry.title,
            'password_decrypted': decrypted
        })
    except Exception as e:
        return Response({'error': f'Failed to decrypt: {str(e)}'}, status=500)

