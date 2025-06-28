# Sparkle 

## Overview
Sparkle is an advanced file management system that leverages AI and cloud technologies to provide intelligent document organization, voice-assisted operations, and secure storage solutions.

## Features

### Smart Document Management
- Multi-format document support (PDFs, images, Word files, etc.)
- Automatic document categorization (9 default categories)
- Custom category creation
- Document expiry tracking
- Smart notifications based on document content

### Intelligent Features
- Voice-controlled file operations
- OCR text extraction using AWS Textract
- Smart document categorization
- Real-time voice assistant
- File type-specific processing:
  - Images (PNG, JPG): Synchronous OCR
  - PDFs: Asynchronous OCR
  - Text Files: Direct extraction

### Storage & Pricing
- Tiered storage plans:
  - Basic: 5GB (₹499)
  - Premium: 20GB (₹999)
  - Enterprise: 50GB (₹1999)
- Automatic storage management
- Usage tracking and analytics

## Technology Stack

### Backend
- Django 5.1.1
- Django REST Framework 3.15.0
- Python 3.x

### Cloud Services
- AWS S3 (Storage)
- AWS Textract (OCR)
- OpenAI (Voice Processing)

### Authentication
- Google OAuth
- JWT Tokens
- Email verification

### Payment
- Razorpay Integration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/sparkle.git
cd sparkle
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # For Unix
venv\Scripts\activate     # For Windows
```

3. Install dependencies:
```bash
pip install -r req.txt
```

4. Set up environment variables:
```
DJANGO_SECRET_KEY=your_secret_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
OPENAI_API_KEY=your_openai_key
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

5. Run migrations:
```bash
python manage.py migrate
```

6. Create default categories:
```bash
python manage.py setup_file_categories
```

7. Run the development server:
```bash
python manage.py runserver
```

## API Documentation
### Main API Groups
- File Management APIs
- Payment APIs
- Storage Management APIs
- User Authentication APIs
- Voice Assistant APIs
- External Service APIs

## file_management/

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Upload File | `/file_management/upload/` | POST | None | Content-Type: multipart/form-data, Authorization | `{file: binary, file_type: string}` | `{message: string, file_url: string, storage_info: object}` |
| List Files | `/file_management/files/` | GET | None | Authorization | None | `{files: array}` |
| Process OCR | `/file_management/ocr/process/<file_id>/` | POST | file_id | Authorization | None | `{status: string, job_id: string, text?: array}` |
| Get OCR Result | `/file_management/ocr/result/<job_id>/` | GET | job_id | Authorization | None | `{status: string, text: array}` |
| Delete File | `/file_management/delete/<file_id>/` | POST | file_id | Authorization, X-CSRFToken | None | `{status: string, message: string}` |
| Add Card | `/file_management/api/cards/` | POST | None | Authorization, Content-Type | `{card_type: string, bank_name: string, ...}` | `{id: number, card_details: object}` |
| Delete Card | `/file_management/api/cards/<card_id>/` | DELETE | card_id | Authorization | None | `204 No Content` |
| Extract Card | `/file_management/api/cards/extract_from_document/` | POST | None | Authorization | `{file_id: number}` | `{cards_found: array}` |
| Add Subscription | `/file_management/api/subscriptions/` | POST | None | Authorization | `{app_name: string, subscription_type: string, ...}` | `{id: number, subscription_details: object}` |
| Delete Subscription | `/file_management/api/subscriptions/<sub_id>/` | DELETE | sub_id | Authorization | None | `204 No Content` |
| Extract Subscription | `/file_management/api/subscriptions/extract_from_document/` | POST | None | Authorization | `{file_id: number}` | `{subscriptions_found: array}` |

## payments/

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| List Plans | `/payment/plans/` | GET | None | Authorization | None | `{plans: array}` |
| Create Subscription | `/payment/subscribe/<plan_type>/` | POST | plan_type | Authorization | None | `{order_id: string, amount: number, currency: string}` |
| Payment Callback | `/payment/payment/callback/` | POST | None | None | `{razorpay_payment_id: string, razorpay_order_id: string, razorpay_signature: string}` | `{status: string}` |

## storage_management/

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Get Storage Info | `/storage/info/` | GET | None | Authorization | None | `{used: string, limit: string, available: string, percentage_used: string}` |

## users/

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Google Login | `/auth/login/google/` | GET | None | None | None | Redirects to Google |
| Google Callback | `/auth/login/google/callback/` | GET | code, state | None | None | Redirects to home |
| Sign Up | `/auth/signup/` | POST | None | Content-Type | `{username: string, email: string, password: string}` | Redirects to verify-email |
| Verify Email | `/auth/verify-email/` | POST | None | Content-Type | `{otp: string}` | Redirects to login |

## voice_assistant/

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Assistant View | `/voice/assistant/` | GET | None | Authorization | None | Renders assistant.html |
| Process Voice | `/voice/voice/process/` | POST | None | Content-Type: multipart/form-data, Authorization | `{audio: binary}` | `{status: string, prompt: string, response: string, audio_url: string}` |

## External Service APIs

### AWS APIs

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| S3 Upload | AWS S3 SDK | PUT | None | AWS Auth | File binary | Upload confirmation |
| S3 Download | AWS S3 SDK | GET | None | AWS Auth | None | File binary |
| Textract Process | AWS Textract SDK | POST | None | AWS Auth | Document binary | OCR results |

### OpenAI APIs

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Transcription | OpenAI API | POST | None | OpenAI Key | Audio file | Transcribed text |
| Chat Completion | OpenAI API | POST | None | OpenAI Key | `{messages: array}` | AI response |
| Text-to-Speech | OpenAI API | POST | None | OpenAI Key | `{input: string}` | Audio file |

### Razorpay APIs

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Create Order | Razorpay SDK | POST | None | Razorpay Auth | `{amount: number, currency: string}` | Order details |
| Verify Payment | Razorpay SDK | POST | None | Razorpay Auth | Payment details | Verification result |

### Google OAuth APIs

| Description | API | Type | Params | Headers | Body | Response |
|------------|-----|------|---------|---------|------|-----------|
| Auth | Google OAuth | GET | scope, redirect_uri | None | None | Auth code |
| User Info | Google OAuth | GET | None | Bearer token | None | User profile |

Notes:
1. All internal APIs require authentication except for login/signup endpoints
2. CSRF token is required for POST operations where specified
3. External APIs are accessed through their respective SDKs
4. File operations use multipart/form-data for uploads
5. Response formats are generally JSON unless specified otherwise


## Security Features

- Secure file storage with AWS S3
- Data isolation between users
- Encrypted file storage
- CSRF protection
- Token-based authentication
- Secure payment processing

## Performance Metrics

### Target Metrics
- System uptime: > 99.9%
- Processing success rate: > 95%
- Response time: < 2 seconds

### Monitoring
- Storage utilization
- Document processing volumes
- Voice assistant usage
- Category distribution
- Payment success rates
- Error rates

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use Django's coding style for Django-specific code
- JavaScript code should follow ESLint configuration

### Git Workflow
1. Create feature branch from develop
2. Make changes and test
3. Submit pull request
4. Code review
5. Merge to develop

### Prerequisites
- Python 3.x
- PostgreSQL
- Redis (for caching)
- AWS Account
- OpenAI API access
- Razorpay account
- Google OAuth credentials


