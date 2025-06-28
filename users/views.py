from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import login
from django.urls import reverse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import CustomUser
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import (
    UserSerializer, UserRegistrationSerializer, EmailVerificationSerializer,
    PasswordChangeSerializer, CustomTokenObtainPairSerializer, GoogleAuthSerializer, GoogleMobileAuthSerializer
)
from .forms import CustomUserCreationForm, OTPVerificationForm
from .utils import generate_otp, send_verification_email, store_otp, verify_otp
from django.views.decorators.http import require_http_methods
from rest_framework_simplejwt.tokens import RefreshToken
import json
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

def google_login(request):
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=[
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
        ],
    )
    
    flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
    )

    request.session['google_oauth_state'] = state
    return redirect(authorization_url)

def google_callback(request):
    state = request.session['google_oauth_state']
    
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=[
            'https://www.googleapis.com/auth/userinfo.profile',
            'https://www.googleapis.com/auth/userinfo.email',
        ],
        state=state,
    )
    
    flow.redirect_uri = request.build_absolute_uri(reverse('google_callback'))

    flow.fetch_token(authorization_response=request.build_absolute_uri())

    credentials = flow.credentials
    service = build('oauth2', 'v2', credentials=credentials)
    user_info = service.userinfo().get().execute()

    # Get or create user
    try:
        user = CustomUser.objects.get(email=user_info['email'])
    except CustomUser.DoesNotExist:
        user = CustomUser.objects.create_user(
            username=user_info['email'],
            email=user_info['email'],
            google_id=user_info['id'],
            profile_picture=user_info.get('picture', ''),
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', '')
        )

    login(request, user)
    return redirect('home')

@require_http_methods(["GET", "POST"])
def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User won't be active until email is verified
            user.save()
            
            # Generate and send OTP
            otp = generate_otp()
            store_otp(user.email, otp)
            send_verification_email(user.email, otp)
            
            # Store user_id in session for verification
            request.session['verification_user_id'] = user.id
            
            return redirect('verify_email')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})


@require_http_methods(["GET", "POST"])
def verify_email(request):
    user_id = request.session.get('verification_user_id')
    if not user_id:
        return redirect('signup')
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('signup')

    if request.method == 'POST':
        if 'resend' in request.POST:
            # Handle resend OTP
            otp = generate_otp()
            store_otp(user.email, otp)
            send_verification_email(user.email, otp)
            messages.success(request, 'New verification code sent!')
            return redirect('verify_email')
            
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            
            if verify_otp(user.email, otp):
                user.is_active = True
                user.save()
                login(request, user)
                messages.success(request, 'Email verified successfully!')
                
                # Clear verification session data
                del request.session['verification_user_id']
                request.session.modified = True
                
                return redirect('file_list')
            else:
                messages.error(request, 'Invalid verification code')
    else:
        form = OTPVerificationForm()
    
    return render(request, 'registration/verify_email.html', {
        'form': form,
        'email': user.email
    })


User = get_user_model()

def get_tokens_for_user(user):
    """Generate JWT tokens for any user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

class UserViewSet(viewsets.ModelViewSet):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({'message': 'Password updated successfully'})
            return Response({'error': 'Invalid old password'}, 
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Handle user registration with email verification"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        otp = generate_otp()
        store_otp(user.email, otp)
        send_verification_email(user.email, otp)
        
        return Response({
            'message': 'Registration successful. Please verify your email.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """Verify email with OTP and return JWT tokens"""
    serializer = EmailVerificationSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']
        
        if verify_otp(email, otp):
            try:
                user = User.objects.get(email=email)
                user.is_active = True
                user.save()
                
                # Generate tokens after verification
                tokens = get_tokens_for_user(user)
                return Response({
                    'message': 'Email verified successfully',
                    'tokens': tokens,
                    'user': UserSerializer(user).data
                })
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'error': 'Invalid OTP'
        }, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth(request):
    """Handle Google OAuth authentication and return JWT tokens"""
    serializer = GoogleAuthSerializer(data=request.data)
    if serializer.is_valid():
        try:
            code = serializer.validated_data['code']
            
            # Initialize Google OAuth flow
            flow = Flow.from_client_config(
                client_config={
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=['https://www.googleapis.com/auth/userinfo.profile',
                        'https://www.googleapis.com/auth/userinfo.email']
            )
            
            # Exchange auth code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info from Google
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            # Get or create user
            user, created = User.objects.get_or_create(
                email=user_info['email'],
                defaults={
                    'username': user_info['email'],
                    'google_id': user_info['id'],
                    'first_name': user_info.get('given_name', ''),
                    'last_name': user_info.get('family_name', ''),
                    'profile_picture': user_info.get('picture', ''),
                    'is_active': True  # Google users are pre-verified
                }
            )
            
            # Generate tokens
            tokens = get_tokens_for_user(user)
            
            return Response({
                'message': 'Google authentication successful',
                'tokens': tokens,
                'user': UserSerializer(user).data,
                'is_new_user': created
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    """Resend verification email with new OTP"""
    email = request.data.get('email')
    try:
        user = User.objects.get(email=email)
        if not user.is_active:
            otp = generate_otp()
            store_otp(email, otp)
            send_verification_email(email, otp)
            return Response({
                'message': 'Verification email sent successfully'
            })
        return Response({
            'error': 'User is already verified'
        }, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)




# Update the signup view to return JSON
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_signup(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        otp = generate_otp()
        store_otp(user.email, otp)
        send_verification_email(user.email, otp)
        
        return Response({
            'success': True,
            'message': 'Registration successful. Please verify your email.',
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Add mobile verify email
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_verify_email(request):
    email = request.data.get('email')
    otp = request.data.get('otp')
    
    if not email or not otp:
        return Response({
            'success': False,
            'error': 'Email and OTP are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if verify_otp(email, otp):
        try:
            user = CustomUser.objects.get(email=email)
            user.is_active = True
            user.save()
            
            # Generate tokens for mobile
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Email verified successfully',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': UserSerializer(user).data
            })
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'success': False,
        'error': 'Invalid OTP'
    }, status=status.HTTP_400_BAD_REQUEST)


from .utils import EmailOrUsernameModelBackend 
from django.contrib.auth.backends import ModelBackend
auth = EmailOrUsernameModelBackend()

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_login(request):
    """Handle mobile login and return JWT tokens"""
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not password:
        return Response({
            'success': False,
            'error': 'Password is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Allow login with either username or email
    if email and not username:
        try:
            user = User.objects.get(email=email)
            username = user.username
        except User.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User with this email does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate the user
    user = auth.authenticate(request,username=username, password=password)
    if user is not None:
        if not user.is_active:
            return Response({
                'success': False,
                'error': 'Please verify your email first'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }
        })
    else:
        return Response({
            'success': False,
            'error': 'Invalid credentials'
        }, status=status.HTTP_400_BAD_REQUEST)
    

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_register(request):
    """Simplified registration for mobile app"""
    # Extract registration data
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    confirm_password = request.data.get('confirm_password', password)
    
    # Validate data
    if not all([username, email, password]):
        return Response({
            'success': False,
            'error': 'Username, email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    if password != confirm_password:
        return Response({
            'success': False,
            'error': 'Passwords do not match'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check for existing user
    if User.objects.filter(username=username).exists():
        return Response({
            'success': False,
            'error': 'Username already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    if User.objects.filter(email=email).exists():
        return Response({
            'success': False,
            'error': 'Email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create user
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Option 1: Auto-activate for mobile
        user.is_active = True
        user.save()
        
        # Option 2: Or keep email verification (comment above and uncomment below)
        # user.is_active = False
        # user.save()
        # otp = generate_otp()
        # store_otp(email, otp)
        # send_verification_email(email, otp)
        
        # Generate tokens if auto-activated
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def mobile_token_refresh(request):
    """Refresh access token using refresh token"""
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'success': False,
            'error': 'Refresh token is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        # Get user from token
        user_id = refresh.payload.get('user_id')
        user = User.objects.get(id=user_id)
        
        return Response({
            'success': True,
            'tokens': {
                'refresh': str(refresh),
                'access': access_token
            },
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Invalid or expired refresh token'
        }, status=status.HTTP_400_BAD_REQUEST)
    

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_mobile_auth(request):
    """Handle Google Sign-in for mobile apps using ID tokens"""
    serializer = GoogleMobileAuthSerializer(data=request.data)
    if serializer.is_valid():
        try:
            id_token_str = serializer.validated_data['id_token']
            device_type = serializer.validated_data.get('device_type', 'android')
            
            # Verify the ID token
            client_id = settings.GOOGLE_MOBILE_CLIENT_ID
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                client_id
            )
            
            # Verify issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')
                
            # Get or create user
            user, created = User.objects.get_or_create(
                email=idinfo['email'],
                defaults={
                    'username': idinfo['email'],
                    'google_id': idinfo['sub'],  # Use sub as google_id
                    'first_name': idinfo.get('given_name', ''),
                    'last_name': idinfo.get('family_name', ''),
                    'profile_picture': idinfo.get('picture', ''),
                    'is_active': True  # Google-authenticated users are pre-verified
                }
            )
            
            # Generate JWT tokens
            tokens = get_tokens_for_user(user)
            
            return Response({
                'success': True,
                'message': 'Google authentication successful',
                'tokens': tokens,
                'user': UserSerializer(user).data,
                'is_new_user': created
            })
            
        except ValueError as e:
            # Invalid token
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Authentication failed'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

