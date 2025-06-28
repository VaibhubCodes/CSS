# Sparkle AI - Comprehensive Project Documentation

## 1. Project Overview

Sparkle is an advanced file management system that leverages AI technology to provide intelligent document organization, voice-assisted operations, and secure storage solutions. The system combines cloud storage with AI processing to create a smart document management experience.

## 2. Core Functionality

### 2.1 Smart Document Management
- **Multi-format Support**: Handles PDFs, images, Word files, and other common document formats
- **Automatic Categorization**: Uses AI to classify documents into 9 default categories
- **Custom Categories**: Users can create their own document categories
- **Document Expiry Tracking**: Tracks expiration dates for relevant documents
- **Smart Notifications**: Analyzes document content to provide timely alerts

### 2.2 AI-Powered Features
- **Voice Control**: Complete voice-controlled file operations interface
- **OCR Text Extraction**: Uses AWS Textract to extract text from documents
- **Smart Categorization**: Automated document classification based on content
- **Real-time Voice Assistant**: Natural language interface for file operations
- **Type-Specific Processing**:
  - Images (PNG, JPG): Synchronous OCR
  - PDFs: Asynchronous OCR processing
  - Text Files: Direct text extraction

### 2.3 Storage & Pricing
- **Tiered Storage Plans**:
  - Basic: 5GB (₹499)
  - Premium: 20GB (₹999)
  - Enterprise: 50GB (₹1999)
- **Storage Management**: Automatic tracking of user storage limits
- **Usage Analytics**: Detailed storage usage statistics

## 3. Technical Architecture

### 3.1 Backend Architecture
- **Framework**: Django 5.1.x with Django REST Framework
- **Database**: SQLite for development (as evidenced by db.sqlite3)
- **Authentication**: JWT tokens, Google OAuth integration
- **File Storage**: AWS S3 for secure cloud storage
- **OCR Processing**: AWS Textract
- **AI Processing**: OpenAI API integration
- **Payment Processing**: Razorpay integration

### 3.2 Frontend Architecture
- **Mobile Interface**: React Native (evidenced by AsyncStorage usage)
- **Voice Processing**: Client-side audio recording with server-side processing
- **File Upload**: Multi-part form data handling
- **Authentication**: Token-based authentication

## 4. Core Components

### 4.1 Voice Assistant Module (`voice_assistant/`)
The Voice Assistant module provides the AI-powered voice interface for the application.

#### Key Components:
- **VoiceInteraction Model**: Tracks user voice commands and system responses
- **Audio Processing**: Handles audio file uploads and processing
- **OpenAI Integration**: Uses OpenAI for speech-to-text and text-to-speech
- **Context Management**: Maintains context about user files for intelligent responses
- **File Operation Commands**: Processes voice commands for file operations

#### Notable Features:
- **Voice Command Processing**: Converts voice to text using OpenAI Whisper
- **Natural Language Understanding**: Interprets user intent from voice commands
- **Context-Aware Responses**: Provides responses based on user's file organization and preferences
- **Text-to-Speech**: Generates audio responses using OpenAI TTS
- **Command History**: Maintains history of user commands

### 4.2 File Management Module (`file_management/`)
The File Management module handles all aspects of document storage, categorization, and processing.

#### Key Components:
- **UserFile Model**: Core model for storing file metadata
- **FileCategory Model**: Manages file categories (both default and custom)
- **OCRResult Model**: Stores OCR processing results
- **CardDetails Model**: Stores credit/debit card information extracted from documents
- **AppSubscription Model**: Manages subscription information extracted from documents
- **ExpiryDetails Model**: Tracks document expiration dates

#### Notable Features:
- **File Upload**: Secure file upload to AWS S3
- **OCR Processing**: Text extraction from documents
- **Automatic Categorization**: AI-based document categorization
- **Card/Subscription Extraction**: Identifies payment cards and subscriptions from documents
- **File Access Control**: Controls file access with presigned URLs
- **Document Locking**: Password protection for sensitive files
- **Coin Rewards**: Awards coins for file uploads (gamification)
- **Expiry Management**: Moves expired documents to a designated category

### 4.3 Storage Management Module (`storage_management/`)
Handles storage allocation, tracking, and management for users.

#### Key Components:
- **UserStorage Model**: Tracks user storage usage and limits
- **S3StorageManager**: Utility class for S3 operations
- **AdminAccessLog**: Logs admin access to user files

#### Notable Features:
- **Storage Quota Enforcement**: Prevents uploads that would exceed user storage limits
- **Usage Statistics**: Calculates and reports storage usage metrics
- **Presigned URLs**: Generates secure, time-limited access URLs
- **File Deletion**: Securely removes files from S3 storage

### 4.4 User Management (`users/`)
Handles user authentication, registration, and profile management.

#### Key Features:
- **User Registration**: Email-based registration with OTP verification
- **Google OAuth**: Social login with Google
- **JWT Authentication**: Secure token-based authentication
- **User Profiles**: User profile management

### 4.5 Payment System (`payments/`)
Manages subscription plans and payment processing.

#### Key Features:
- **Plan Management**: Different storage tiers with corresponding pricing
- **Razorpay Integration**: Secure payment processing
- **Subscription Management**: Handles user subscriptions to storage plans

### 4.6 Frontend Components (`FE/`)
React Native components for the mobile interface.

#### Key Components:
- **SparkleChat.js**: Voice assistant interface
- **UploadItem.js**: File upload component
- **UploadingScreen.js**: Upload progress interface
- **API Services**: Centralized API communication

## 5. Database Models

### 5.1 File Management Models
- **UserFile**: Stores file metadata, including S3 key, file type, size, and category
- **FileCategory**: Defines document categories
- **OCRResult**: Stores OCR processing results and status
- **CardDetails**: Stores credit/debit card information extracted from documents
- **AppSubscription**: Tracks subscription information extracted from documents
- **ExpiryDetails**: Manages document expiration tracking

### 5.2 Storage Management Models
- **UserStorage**: Tracks user storage usage and limits
- **AdminAccessLog**: Records admin access to user files

### 5.3 Voice Assistant Models
- **VoiceInteraction**: Records voice commands and system responses

## 6. API Endpoints

### 6.1 File Management APIs
- **File Upload**: `/file_management/upload/` (POST)
- **List Files**: `/file_management/files/` (GET)
- **Process OCR**: `/file_management/ocr/process/<file_id>/` (POST)
- **Get OCR Result**: `/file_management/ocr/result/<job_id>/` (GET)
- **Delete File**: `/file_management/delete/<file_id>/` (POST)
- **Card Management**: `/file_management/api/cards/` (POST, DELETE)
- **Subscription Management**: `/file_management/api/subscriptions/` (POST, DELETE)
- **Mobile File API**: `/file_management/api/mobile/files/` (GET, POST)

### 6.2 Voice Assistant APIs
- **Assistant View**: `/voice/assistant/` (GET)
- **Process Voice**: `/voice/voice/process/` (POST)
- **Process Text Command**: `/voice/text/process/` (POST)
- **Voice Command History**: `/voice/commands/history/` (GET)
- **Command Suggestions**: `/voice/commands/suggestions/` (GET)

### 6.3 Storage Management APIs
- **Storage Info**: `/storage/info/` (GET)

### 6.4 Payment APIs
- **List Plans**: `/payment/plans/` (GET)
- **Create Subscription**: `/payment/subscribe/<plan_type>/` (POST)
- **Payment Callback**: `/payment/payment/callback/` (POST)

### 6.5 User APIs
- **Google Login**: `/auth/login/google/` (GET)
- **Sign Up**: `/auth/signup/` (POST)
- **Verify Email**: `/auth/verify-email/` (POST)

## 7. AI Integration

### 7.1 OpenAI Integration
- **Whisper Model**: Used for speech-to-text conversion
- **GPT-3.5 Turbo**: Powers the natural language understanding
- **Text-to-Speech (TTS-1)**: Generates voice responses

### 7.2 AWS Integration
- **S3**: Secure file storage
- **Textract**: OCR processing for documents
- **Presigned URLs**: Secure file access

## 8. Security Features

- **Secure File Storage**: AWS S3 with private ACLs
- **Data Isolation**: User-specific prefixes in S3
- **Token Authentication**: JWT-based authentication
- **Password Protection**: Optional document encryption
- **Presigned URLs**: Time-limited access to files
- **Payment Security**: Razorpay secure payment processing

## 9. Unique Features

- **Voice-Controlled File Management**: Natural language interface for file operations
- **Smart Document Categorization**: AI-based classification of documents
- **Card and Subscription Extraction**: Automatic extraction of payment cards and subscriptions
- **Document Expiry Tracking**: Smart handling of document expiration dates
- **Coin Rewards System**: Gamification of file uploads
- **OCR Processing**: Text extraction from various document types
- **Context-Aware Voice Assistant**: Personalized responses based on user's file organization

## 10. Implementation Details

### 10.1 File Upload Flow
1. User selects a file for upload
2. Frontend uploads file with metadata (file type, category if selected)
3. Backend validates file and checks storage quota
4. File is uploaded to S3 with user-specific prefix
5. Database record is created with file metadata and S3 key
6. If applicable, OCR processing is initiated
7. Storage usage is updated
8. Coins are awarded to the user

### 10.2 Voice Command Processing Flow
1. User speaks a command
2. Audio is recorded and sent to the server
3. OpenAI Whisper converts speech to text
4. System enhances prompt with user context (files, categories, storage)
5. OpenAI GPT model interprets the command and generates a response
6. Response is converted to speech using OpenAI TTS
7. Both text and audio responses are sent to the client
8. Command and response are logged in VoiceInteraction

### 10.3 OCR Processing Flow
1. Document is uploaded
2. If OCR is applicable, processing is initiated
3. For images, synchronous OCR is performed
4. For PDFs, asynchronous OCR job is created
5. OCR results are stored in the OCRResult model
6. Results are used for document categorization and search

### 10.4 Storage Management Flow
1. User storage is created on registration
2. Storage usage is tracked with each file operation
3. Before upload, system checks if storage quota would be exceeded
4. Storage statistics are calculated and provided to the user
5. Storage tier can be upgraded through subscription plans

## 11. Not Fully Implemented Features
Based on code analysis, these features may be partially implemented or planned:

- **File Encryption**: Code exists for card detail encryption but is marked with TODOs
- **Advanced Search**: Basic search exists but advanced search capabilities might be in progress
- **File Sharing**: Sharing API exists but might have limited functionality
- **Folder Creation**: API exists but might not be fully implemented in the UI
- **Admin Dashboard**: Admin access logging exists but a full dashboard may not be complete

## 12. Development Guidelines
The project follows these development practices:

- **Python Code Style**: PEP 8 standards
- **Django Patterns**: Django REST Framework patterns for APIs
- **API Response Format**: Consistent JSON response structures
- **S3 File Organization**: User-specific prefixes for data isolation
- **Error Handling**: Structured error responses with appropriate HTTP status codes
- **Logging**: Extensive logging for debugging and audit purposes

## 13. Deployment Requirements
The application requires:

- **Python 3.x**
- **Django 5.1.x**
- **AWS Account** with S3 and Textract access
- **OpenAI API** credentials
- **Razorpay** merchant account
- **Google OAuth** credentials
- **Environment Variables** for secret keys and configuration 