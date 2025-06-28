from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class SubscriptionPlan(models.Model):
    """
    Admin-managed subscription plans with full customization
    """
    name = models.CharField(max_length=100, help_text="Display name for the plan")
    plan_code = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Unique identifier for the plan (e.g., 'basic', 'premium')"
    )
    description = models.TextField(blank=True, help_text="Plan description")
    
    # Pricing
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in INR"
    )
    
    # Storage
    storage_gb = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Storage limit in GB"
    )
    
    # Features
    is_sparkle = models.BooleanField(
        default=False,
        help_text="Enable sparkle/premium features (false for basic plans)"
    )
    
    # Plan Features (JSON field for flexibility)
    features = models.JSONField(
        default=list,
        help_text="List of features for this plan (JSON array)"
    )
    
    # Plan settings
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this plan is available for purchase"
    )
    
    sort_order = models.IntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    
    # Duration settings
    duration_days = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Plan validity in days"
    )
    
    # Admin settings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} - ₹{self.price}"
    
    @property
    def storage_bytes(self):
        """Convert GB to bytes for storage calculations"""
        return self.storage_gb * 1024 * 1024 * 1024
    
    @property
    def price_paise(self):
        """Convert price to paise for Razorpay"""
        return int(self.price * 100)

class Subscription(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(
        SubscriptionPlan, 
        on_delete=models.PROTECT,  # Prevent deletion of plans with active subscriptions
        help_text="Selected subscription plan"
    )
    
    # Legacy plan code field for backward compatibility
    legacy_plan = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="Legacy plan identifier (for migration)"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment details
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    
    # Subscription details
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    valid_till = models.DateTimeField(null=True, blank=True)
    
    # Pricing snapshot (to maintain historical pricing)
    paid_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=0,
        help_text="Amount paid for this subscription"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"
    
    @property
    def is_sparkle_subscription(self):
        """Check if this subscription has sparkle features"""
        return self.plan.is_sparkle if self.plan else False

class PaymentTransaction(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.user.email} - {self.amount} {self.currency}"
