from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from storage_management.utils import S3StorageManager
import math
from django.core.exceptions import ValidationError

class OCRResult(models.Model):
    file = models.ForeignKey('UserFile', on_delete=models.CASCADE)
    text_content = models.TextField(blank=True, null=True)
    processed_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    job_id = models.CharField(max_length=100, blank=True, null=True)  # Add this field

    def __str__(self):
        return f"OCR Result for {self.file.file.name}"
    

class FileCategory(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "File Categories"

# class UserFile(models.Model):
#     FILE_TYPES = (
#         ('audio', 'Audio'),
#         ('document', 'Document'),
#     )
#     user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
#     file_type = models.CharField(max_length=10, choices=FILE_TYPES)
#     file = models.FileField(upload_to='uploads/')
#     upload_date = models.DateTimeField(auto_now_add=True)
#     category = models.ForeignKey(FileCategory, on_delete=models.SET_NULL, null=True)
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

#     def __str__(self):
#         return f"{self.file_type} - {self.file.name}"
class UserFile(models.Model):
    FILE_TYPES = (
        ('document', 'Document'),
        ('image', 'Image'),
        ('audio', 'Audio'),
    )

    DOCUMENT_SIDES = (
        ('single', 'Single Side'),
        ('front', 'Front Side'), 
        ('back', 'Back Side'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file = models.FileField(upload_to='uploads/')
    upload_date = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey('FileCategory', on_delete=models.SET_NULL, null=True, blank=True)
    is_public = models.BooleanField(default=False)
    is_favorite = models.BooleanField(default=False)
    s3_key = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0)
    original_filename = models.CharField(max_length=255, blank=True)
    coins_awarded = models.BooleanField(default=False)
    pending_auto_categorization = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    locked_password = models.CharField(max_length=100, blank=True, null=True)
    document_side = models.CharField(max_length=10, choices=DOCUMENT_SIDES, default='single')
    paired_document = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='paired_with')
    document_type_name = models.CharField(max_length=100, blank=True)
    is_hidden = models.BooleanField(default=False, help_text="Hide file from normal view")
    locked_at = models.DateTimeField(blank=True, null=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='locked_files',blank=True, null=True)

    def save(self, *args, **kwargs):
        # Set S3 key if not already set
        if not self.s3_key and self.file:
            storage_manager = S3StorageManager(self.user)
            filename = self.file.name.split('/')[-1]
            self.original_filename = filename
            self.s3_key = f"{storage_manager.user_prefix}{filename}"
            
        # Update file size if file is present
        if self.file and not self.file_size:
            self.file_size = self.file.size
        
        # Set pending_auto_categorization for new document files
        is_new = not self.pk
        if is_new and self.file_type in ['document', 'image'] and not self.category:
            self.pending_auto_categorization = True
            # Set default Miscellaneous category
            misc_category, _ = FileCategory.objects.get_or_create(
                name='Miscellaneous',
                defaults={'is_default': True, 'description': 'Uncategorized files'}
            )
            self.category = misc_category
            
        super().save(*args, **kwargs)
        
        # Award coins for new file uploads (keep this logic here)
        if is_new and not self.coins_awarded and self.file_size > 0:
            self._award_upload_coins()

    def _award_upload_coins(self):
        """Award coins for file upload - separated method"""
        try:
            from coin_wallet.models import CoinWallet, CoinTransaction
            
            file_size_mb = math.ceil(self.file_size / (1024 * 1024))
            if file_size_mb < 1:
                file_size_mb = 1
            
            wallet, created = CoinWallet.objects.get_or_create(user=self.user)
            
            existing_transaction = CoinTransaction.objects.filter(
                wallet=wallet,
                transaction_type='upload',
                related_file=self
            ).exists()
            
            if not existing_transaction:
                wallet.add_coins(
                    amount=file_size_mb,
                    transaction_type='upload',
                    source=f'File upload: {self.original_filename}'
                )
                
                transaction = CoinTransaction.objects.filter(
                    wallet=wallet,
                    transaction_type='upload'
                ).latest('created_at')
                transaction.related_file = self
                transaction.save()
                
                self.coins_awarded = True
                UserFile.objects.filter(pk=self.pk).update(coins_awarded=True)
        except Exception as e:
            print(f"Error awarding coins: {str(e)}")

    def get_file_url(self):
        """Get presigned URL for file access"""
        if not self.s3_key:
            return None
            
        storage_manager = S3StorageManager(self.user)
        return storage_manager.get_file_url(self.s3_key)

    def get_download_url(self):
        """Get presigned URL for file download"""
        if not self.s3_key:
            return None
            
        storage_manager = S3StorageManager(self.user)
        return storage_manager.get_file_url(
            self.s3_key, 
            response_content_disposition=f'attachment; filename="{self.original_filename}"'
        )

    def get_file_size_display(self):
        """Return human-readable file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.2f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.2f} TB"

    def delete(self, *args, **kwargs):
        """Override delete to remove file from S3 with enhanced error handling"""
        s3_deletion_success = False
        
        # Try multiple S3 key variations to find and delete the file
        if self.s3_key or self.file:
            try:
                storage_manager = S3StorageManager(self.user)
            
                # List of possible S3 keys to try
                possible_keys = []
                
                # Add current s3_key if it exists
                if self.s3_key:
                    possible_keys.append(self.s3_key)
                
                # Add file.name if it exists and is different
                if self.file and self.file.name and self.file.name != self.s3_key:
                    possible_keys.append(self.file.name)
                
                # Add variations based on original filename
                if self.original_filename:
                    possible_keys.extend([
                        f"uploads/{self.original_filename}",
                        f"user_{self.user.id}/{self.original_filename}",
                        self.original_filename
                    ])
                
                # Remove duplicates while preserving order
                seen = set()
                unique_keys = []
                for key in possible_keys:
                    if key and key not in seen:
                        seen.add(key)
                        unique_keys.append(key)
                
                print(f"[Delete] Attempting to delete file {self.id}: {self.original_filename}")
                print(f"[Delete] Trying S3 keys: {unique_keys}")
                
                # Try each key until one succeeds
                for key in unique_keys:
                    try:
                        # First, check if file exists in S3
                        if storage_manager.file_exists(key):
                            print(f"[Delete] Found file with key: {key}")
                            storage_manager.delete_file(key)
                            print(f"[Delete] Successfully deleted file from S3: {key}")
                            s3_deletion_success = True
                            break
                        else:
                            print(f"[Delete] File not found with key: {key}")
                    except Exception as key_error:
                        print(f"[Delete] Failed to delete with key '{key}': {str(key_error)}")
                        continue
                
                if not s3_deletion_success:
                    print(f"[Delete] Warning: Could not find file in S3 with any key variation")
                    print(f"[Delete] File may have been already deleted or moved")
            
            except Exception as e:
                print(f"[Delete] Error during S3 deletion process: {str(e)}")
        
        # Always delete the database record, even if S3 deletion failed
        print(f"[Delete] Deleting database record for file {self.id}")
        super().delete(*args, **kwargs)
        
        if s3_deletion_success:
            print(f"[Delete] Successfully deleted file {self.id} from both S3 and database")
        else:
            print(f"[Delete] Deleted database record for file {self.id}, but S3 file was not found")

    def __str__(self):
        return f"{self.file_type} - {self.original_filename}"

    def get_document_pair(self):
        """Get both sides of a paired document"""
        if self.document_side == 'single':
            return {'single': self}
        
        pair = {}
        if self.document_side == 'front':
            pair['front'] = self
            pair['back'] = self.paired_document
        elif self.document_side == 'back':
            pair['back'] = self
            pair['front'] = self.paired_document
            
        return pair
    
    def has_pair(self):
        """Check if document has a paired document"""
        return self.paired_document is not None

    def is_accessible_by_user(self, user, password=None):
        """Check if user can access this file"""
        # Owner can always access
        if self.user == user:
            if self.locked and password:
                from django.contrib.auth.hashers import check_password
                return check_password(password, self.locked_password)
            elif self.locked and not password:
                return False
            return True
        
        # For public files, check if not hidden
        if self.is_public and not self.is_hidden:
            return not self.locked  # Public locked files are not accessible
        
        return False
    
    def toggle_favorite(self):
        """Toggle favorite status"""
        self.is_favorite = not self.is_favorite
        self.save(update_fields=['is_favorite'])
        return self.is_favorite
    
    def toggle_hidden(self):
        """Toggle hidden status"""
        self.is_hidden = not self.is_hidden
        self.save(update_fields=['is_hidden'])
        return self.is_hidden
    
    def lock_with_password(self, password, user=None):
        """Lock file with password"""
        if not password or len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        
        from django.contrib.auth.hashers import make_password
        from django.utils import timezone
        
        self.locked = True
        self.locked_password = make_password(password)
        self.locked_at = timezone.now()
        self.locked_by = user or self.user
        self.save(update_fields=['locked', 'locked_password', 'locked_at', 'locked_by'])
    
    def unlock_with_password(self, password):
        """Unlock file with password"""
        from django.contrib.auth.hashers import check_password
        
        if not self.locked:
            return True
        
        if check_password(password, self.locked_password):
            self.locked = False
            self.locked_password = None
            self.locked_at = None
            self.locked_by = None
            self.save(update_fields=['locked', 'locked_password', 'locked_at', 'locked_by'])
            return True
        
        return False

    class Meta:
        ordering = ['-upload_date']
        verbose_name = 'User File'
        verbose_name_plural = 'User Files'
        indexes = [
            models.Index(fields=['user', 'is_hidden']),
            models.Index(fields=['user', 'is_favorite']),
            models.Index(fields=['user', 'locked']),
        ]

class CardDetails(models.Model):
    CARD_TYPES = (
        ('credit', 'Credit Card'),
        ('debit', 'Debit Card')
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    bank_name = models.CharField(max_length=100)
    card_number = models.CharField(max_length=16)  # Will be encrypted
    card_holder = models.CharField(max_length=100)
    expiry_month = models.CharField(max_length=2)
    expiry_year = models.CharField(max_length=4)
    cvv = models.CharField(max_length=4)  # Will be encrypted
    created_at = models.DateTimeField(auto_now_add=True)
    extracted_from_doc = models.ForeignKey('UserFile', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.bank_name} - {self.card_type} (**** {self.card_number[-4:]})"

class AppSubscription(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=100)
    subscription_type = models.CharField(max_length=50)  # e.g., "Monthly", "Annual"
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    auto_renewal = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    payment_method = models.ForeignKey(CardDetails, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    extracted_from_doc = models.ForeignKey('UserFile', null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.app_name} - {self.subscription_type} ({self.status})"
    
    @property
    def current_status(self):
        from datetime import date
        today = date.today()
        
        if self.end_date < today and not self.auto_renewal:
            return 'expired'
        elif self.end_date < today and self.auto_renewal:
            # If auto-renewal is on, consider it active even after end_date
            return 'active'
        else:
            return 'active'

# For encrypting sensitive data
class EncryptedCardField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.decrypt_value(value)

    def to_python(self, value):
        if value is None:
            return value
        return self.decrypt_value(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encrypt_value(value)

    @staticmethod
    def encrypt_value(value):
        #TODO Implement encryption logic
        pass

    @staticmethod
    def decrypt_value(value):
        #TODO Implement decryption logic
        pass

class ExpiryDetails(models.Model):
    DOCUMENT_TYPE_CHOICES = (
        ('document', 'Document'),
        ('card', 'Card'),
        ('subscription', 'Subscription')
    )
    
    document = models.ForeignKey('UserFile', on_delete=models.CASCADE, null=True, blank=True)
    card = models.ForeignKey('CardDetails', on_delete=models.CASCADE, null=True, blank=True)
    subscription = models.ForeignKey('AppSubscription', on_delete=models.CASCADE, null=True, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    expiry_date = models.DateField()
    moved_to_expired = models.BooleanField(default=False)
    original_category = models.CharField(max_length=100, blank=True)
    expired_s3_key = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        if self.document:
            return f"Document Expiry: {self.document.file.name}"
        elif self.card:
            return f"Card Expiry: {self.card.card_number[-4:]}"
        else:
            return f"Subscription Expiry: {self.subscription.app_name}"

# Create the expired documents category
def create_expired_category():
    FileCategory.objects.get_or_create(
        name='EXPIRED_DOCS',
        defaults={
            'is_default': True,
            'description': 'Category for expired documents, cards, and subscriptions'
        }
    )


class OCRPreference(models.Model):
    OCR_CHOICES = (
        ('all', 'Process OCR on all files'),
        ('selected', 'Process OCR only on selected files'),
        ('none', 'Do not process OCR on any files')
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    preference = models.CharField(max_length=10, choices=OCR_CHOICES, default='all')
    
    def __str__(self):
        return f"{self.user.username}'s OCR preference: {self.get_preference_display()}"

    



locked = models.BooleanField(default=False)
locked_password = models.CharField(max_length=100, blank=True, null=True)


