from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import base64
import os

class PasswordCategory(models.Model):
    """Categories for organizing passwords"""
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, default='lock')  # Font Awesome icon name
    color = models.CharField(max_length=20, default='#007aff')  # Default iOS blue color
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Password Categories"
        ordering = ['name']
        unique_together = ['name', 'user']
    
    def __str__(self):
        return self.name

class PasswordEntry(models.Model):
    """Main model for storing password entries"""
    TYPE_CHOICES = (
        ('password', 'Website Password'),
        ('app', 'App Password'),
        ('wifi', 'Wi-Fi Password'),
        ('card', 'Credit/Debit Card'),
        ('note', 'Secure Note'),
        ('passkey', 'Passkey'),
        ('identity', 'Identity'),
    )
    
    STRENGTH_CHOICES = (
        ('weak', 'Weak'),
        ('medium', 'Medium'),
        ('strong', 'Strong'),
        ('very_strong', 'Very Strong'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='password')
    title = models.CharField(max_length=100)
    username = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    password = models.BinaryField()  # Encrypted password stored as binary
    website_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    category = models.ForeignKey(PasswordCategory, on_delete=models.SET_NULL, null=True, blank=True)
    strength = models.CharField(max_length=20, choices=STRENGTH_CHOICES, blank=True, null=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    password_iv = models.BinaryField()  # Initialization Vector for encryption
    
    class Meta:
        verbose_name_plural = "Password Entries"
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_entry_type_display()})"
    
    def mark_as_used(self):
        """Update the last used timestamp"""
        self.last_used = timezone.now()
        self.save(update_fields=['last_used'])
    
    def generate_password(self, length=16, include_symbols=True):
        """Generate a secure random password"""
        import random
        import string
        
        chars = string.ascii_letters + string.digits
        if include_symbols:
            chars += "!@#$%^&*()-_=+[]{}|;:,.<>?"
            
        password = ''.join(random.choice(chars) for _ in range(length))
        return password
    
    @property
    def is_compromised(self):
        """Check if this password has been flagged as compromised"""
        return PasswordCompromise.objects.filter(password_entry=self).exists()
    
    @property
    def is_reused(self):
        """Check if this password is reused across multiple entries"""
        # This would require decrypting multiple passwords to check
        # For now, return False as a placeholder
        return False

class PasswordCompromise(models.Model):
    """Track compromised passwords based on breach checks"""
    password_entry = models.ForeignKey(PasswordEntry, on_delete=models.CASCADE)
    detected_date = models.DateTimeField(auto_now_add=True)
    breach_source = models.CharField(max_length=100, blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    resolved_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Compromise: {self.password_entry.title} - {self.detected_date}"
    
    def resolve(self):
        """Mark this compromise as resolved"""
        self.is_resolved = True
        self.resolved_date = timezone.now()
        self.save(update_fields=['is_resolved', 'resolved_date'])

class PasswordHistory(models.Model):
    """Track password changes for entries"""
    password_entry = models.ForeignKey(PasswordEntry, on_delete=models.CASCADE)
    previous_password = models.BinaryField()  # Encrypted previous password
    changed_date = models.DateTimeField(auto_now_add=True)
    password_iv = models.BinaryField()  # Initialization Vector for encryption
    
    class Meta:
        verbose_name_plural = "Password Histories"
        ordering = ['-changed_date']
    
    def __str__(self):
        return f"History: {self.password_entry.title} - {self.changed_date}"

class SecuritySetting(models.Model):
    """User preferences for password security"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    check_for_compromised = models.BooleanField(default=True)
    suggest_strong_passwords = models.BooleanField(default=True)
    min_password_length = models.IntegerField(default=12)
    password_require_uppercase = models.BooleanField(default=True)
    password_require_numbers = models.BooleanField(default=True)
    password_require_symbols = models.BooleanField(default=True)
    auto_fill_enabled = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Security Settings for {self.user.email}"

class PasskeyCredential(models.Model):
    """Store WebAuthn/FIDO2 passkey credentials"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    password_entry = models.ForeignKey(PasswordEntry, on_delete=models.CASCADE, related_name='passkeys')
    credential_id = models.BinaryField()
    public_key = models.BinaryField()
    sign_count = models.BigIntegerField(default=0)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Passkey: {self.password_entry.title} - {self.device_name or 'Unknown device'}"

class PasswordAccessLog(models.Model):
    """Track when passwords are accessed"""
    password_entry = models.ForeignKey(PasswordEntry, on_delete=models.CASCADE)
    access_date = models.DateTimeField(auto_now_add=True)
    access_type = models.CharField(max_length=20)  # 'view', 'copy', 'autofill'
    device_info = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-access_date']
    
    def __str__(self):
        return f"Access: {self.password_entry.title} - {self.access_date}"

class MasterPassword(models.Model):
    """Store master password hash for additional security layer"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    password_hash = models.CharField(max_length=255)  # Store the hash, not the password
    salt = models.CharField(max_length=100)
    iterations = models.IntegerField(default=100000)
    created_at = models.DateTimeField(auto_now_add=True)
    last_changed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Master Password for {self.user.email}"
