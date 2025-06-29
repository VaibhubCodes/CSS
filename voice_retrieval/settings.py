from pathlib import Path
from datetime import timedelta
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-v+=uzudxlo$65o^#749*won*j=l2&fktec9oy2z0h=hfw@xb(i'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['10.0.2.2','127.0.0.1','54.86.91.25','*','44.205.255.170']

CSRF_TRUSTED_ORIGINS = ['http://localhost:8000']  # Since we're not using CSRF
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = None

CORS_ALLOW_ALL_ORIGINS = True  # For development, restrict for production
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',
    'file_management',
    'users',
    'social_django',
    'payments',
    'storage_management',
    'voice_assistant',
    'password_management',
    'coin_wallet',
    'weblinks',
    'coupons',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'voice_retrieval.middleware.MobileAPICsrfExemptMiddleware',
    'voice_retrieval.middleware.MobileAuthenticationMiddleware',
]

ROOT_URLCONF = 'voice_retrieval.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
             BASE_DIR / 'templates',
             BASE_DIR / 'password_management' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'voice_retrieval.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        },
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


import os

AWS_LOGGING = True
AWS_ACCESS_KEY_ID = 'AKIAV6DXFJCNG7PHYF5S'
AWS_SECRET_ACCESS_KEY = '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'
AWS_STORAGE_BUCKET_NAME = 'voice-documents-bucket'
AWS_S3_REGION_NAME = 'us-east-1'  
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

AWS_S3_SIGNATURE_NAME = 's3v4' 
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_S3_VERITY = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400  # 25MB
FILE_UPLOAD_TEMP_DIR = '/tmp'
DATA_UPLOAD_MAX_MEMORY_SIZE = 26214400
# Static files (CSS, JavaScript, Images)
# STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Media files (user uploads)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STORAGES = {
    "default":{
        "BACKEND":"storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles":{
        "BACKEND":"django.contrib.staticfiles.storage.StaticFilesStorage"
    }
}
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

OPENSEARCH_HOST = 'search-sparkle-yazcqkfkheq6kkk4g2dg6ykype.aos.us-east-1.on.aws'
OPENSEARCH_PORT = 443 

OPENAI_API_KEY = "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"
RAZORPAY_KEY_ID = 'rzp_test_GY4iJFc1dQJzvQ'
RAZORPAY_KEY_SECRET = 'Jwb2JZb3lsJnzrCUROE92mF8'

# Authentication settings
AUTH_USER_MODEL = 'users.CustomUser'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# Google OAuth2 settings
# GOOGLE_OAUTH2_CLIENT_SECRETS_JSON = os.path.join(BASE_DIR, 'client_secrets.json')
GOOGLE_OAUTH_REDIRECT_URI = 'http://127.0.0.1:8000/oauth2callback/'
GOOGLE_OAUTH2_SECRET = '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'
GOOGLE_CLIENT_SECRET = GOOGLE_OAUTH2_SECRET
GOOGLE_CLIENT_ID = "450349180485-qf6n4i6udsit4ftgrcch03qusvums09a.apps.googleusercontent.com"

# Separate mobile client ID (you need to create this in Google Cloud Console)
GOOGLE_MOBILE_CLIENT_ID = ""  # Add your mobile client ID here

# Social Auth settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = GOOGLE_CLIENT_ID
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = GOOGLE_CLIENT_SECRET

# Google OAuth scopes
GOOGLE_OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
]

REQUIRED_PACKAGES = [
    'google-auth-oauthlib',
    'google-auth',
    'google-api-python-client',
]

AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_DEFAULT_ACL = 'private'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'sanskar.works.2004@gmail.com'
EMAIL_HOST_PASSWORD = 'iufl twna hqdg sxnb'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Cache settings for OTP storage
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        # Commenting out session authentication since it enforces CSRF
        # 'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    },
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'voice_retrieval.utils.custom_exception_handler',
}


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Swagger settings
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}


AUTHENTICATION_BACKENDS = [
    'users.utils.EmailOrUsernameModelBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Subscription Plans Configuration
SUBSCRIPTION_PLANS = {
    'DEFAULT_STORAGE_GB': 5,
    'SPARKLE_FEATURES': [
        'advanced_analytics',
        'detailed_optimization',
        'extended_history',
        'priority_support'
    ]
}
